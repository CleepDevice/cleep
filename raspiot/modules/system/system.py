#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from raspiot.utils import InvalidParameter, MissingParameter, NoResponse, InvalidModule, CommandError
from raspiot.raspiot import RaspIotModule
from raspiot.libs.internals.task import Task
import raspiot
from datetime import datetime
import time
import psutil
import time
import uuid
import socket
from zipfile import ZipFile, ZIP_DEFLATED
from tempfile import NamedTemporaryFile
from raspiot.libs.internals.console import Console, EndlessConsole
from raspiot.libs.configs.fstab import Fstab
from raspiot.libs.configs.raspiotconf import RaspiotConf
from raspiot.libs.internals.install import Install
from raspiot.libs.internals.installraspiot import InstallRaspiot
from raspiot.libs.configs.modulesjson import ModulesJson
import raspiot.libs.internals.tools as Tools
from raspiot.libs.internals.github import Github
from raspiot import __version__ as VERSION
from raspiot.libs.internals.raspiotbackup import RaspiotBackup


__all__ = [u'System']


class System(RaspIotModule):
    """
    Helps controlling the system device (halt, reboot) and monitoring it
    """
    MODULE_AUTHOR = u'Cleep'
    MODULE_VERSION = u'1.0.0'
    MODULE_PRICE = 0
    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Helps updating, controlling and monitoring the device'
    MODULE_LOCKED = True
    MODULE_TAGS = [u'troubleshoot', u'locale', u'events', u'monitoring', u'update', u'log']
    MODULE_COUNTRY = u''
    MODULE_URLINFO = None
    MODULE_URLHELP = None
    MODULE_URLBUGS = None
    MODULE_URLSITE = None

    MODULE_CONFIG_FILE = u'system.conf'

    #TODO get log file path from bin/raspiot
    LOG_FILE = u'/var/log/raspiot.log'

    DEFAULT_CONFIG = {
        u'monitoring': False,
        u'device_uuid': str(uuid.uuid4()),
        u'ssl': False,
        u'auth': False,
        u'rpcport': 80,
        u'eventsnotrendered': [],
        u'crashreport': True,

        u'lastcheckraspiot': None,
        u'lastcheckmodules': None,
        u'raspiotupdateenabled': True,
        u'modulesupdateenabled': True,
        u'raspiotupdateavailable': False,
        u'modulesupdateavailable': False,
        u'lastraspiotupdate': {
            u'status': None,
            u'time': 0,
            u'stdout': [],
            u'stderr': []
        },
        u'lastmodulesinstalls' : {},
        u'raspiotbackupdelay': 15
    }

    MONITORING_CPU_DELAY = 60.0 #1 minute
    MONITORING_MEMORY_DELAY = 300.0 #5 minutes
    MONITORING_DISKS_DELAY = 21600 #6 hours

    THRESHOLD_MEMORY = 80.0
    THRESHOLD_DISK_SYSTEM = 80.0
    THRESHOLD_DISK_EXTERNAL = 90.0

    RASPIOT_GITHUB_OWNER = u'tangb'
    RASPIOT_GITHUB_REPO = u'raspiot'

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): flag to set debug level to logger
        """
        RaspIotModule.__init__(self, bootstrap, debug_enabled)

        #members
        self.events_factory = bootstrap[u'events_factory']
        self.__monitor_cpu_uuid = None
        self.__monitor_memory_uuid = None
        self.__monitoring_cpu_task = None
        self.__monitoring_memory_task = None
        self.__monitoring_disks_task = None
        self.__process = None
        self.__need_restart = False
        self.__need_reboot = False
        self.modules_json = ModulesJson(self.cleep_filesystem)
        self.__updating_modules = []
        self.__modules = {}
        self.__raspiot_update = {
            u'package': None,
            u'checksum': None
        } 
        self.raspiot_update_pending = False
        self.raspiot_backup = RaspiotBackup(self.cleep_filesystem, self.crash_report)
        self.raspiot_backup_delay = None

        #events
        self.systemSystemHalt = self._get_event(u'system.system.halt')
        self.systemSystemReboot = self._get_event(u'system.system.reboot')
        self.systemSystemRestart = self._get_event(u'system.system.restart')
        self.systemNeedRestart = self._get_event(u'system.system.needrestart')
        self.systemMonitoringCpu = self._get_event(u'system.monitoring.cpu')
        self.systemMonitoringMemory = self._get_event(u'system.monitoring.memory')
        self.systemAlertMemory = self._get_event(u'system.alert.memory')
        self.systemAlertDisk = self._get_event(u'system.alert.disk')
        self.alertEmailSend = self._get_event(u'alert.email.send')
        self.systemModuleInstall = self._get_event(u'system.module.install')
        self.systemModuleUninstall = self._get_event(u'system.module.uninstall')
        self.systemModuleUpdate = self._get_event(u'system.module.update')
        self.systemRaspiotUpdate = self._get_event(u'system.raspiot.update')

    def _configure(self):
        """
        Configure module
        """
        #set members
        self.raspiot_backup_delay = self._get_config_field(u'raspiotbackupdelay')

        #configure crash report
        self.__configure_crash_report(self._get_config_field(u'crashreport'))

        #init first cpu percent for current process
        self.__process = psutil.Process(os.getpid())
        self.__process.cpu_percent()

        #add devices if they are not already added
        if self._get_device_count()<3:
            self.logger.debug(u'Add default devices (device count=%d)' % self._get_device_count())

            #add fake monitor device (used to have a device on dashboard)
            monitor = {
                u'type': u'monitor',
                u'name': u'System monitor'
            }
            self._add_device(monitor)

            #add fake monitor cpu device (used to save cpu data into database and has no widget)
            monitor = {
                u'type': u'monitorcpu',
                u'name': u'Cpu monitor'
            }
            self._add_device(monitor)

            #add fake monitor memory device (used to save cpu data into database and has no widget)
            monitor = {
                u'type': u'monitormemory',
                u'name': u'Memory monitor'
            }
            self._add_device(monitor)

        #store device uuids for events
        devices = self.get_module_devices()
        for uuid in devices:
            if devices[uuid][u'type']==u'monitorcpu':
                self.__monitor_cpu_uuid = uuid
            elif devices[uuid][u'type']==u'monitormemory':
                self.__monitor_memory_uuid = uuid

        #launch monitoring thread
        self.__start_monitoring_threads()

        #download modules.json file if not exists
        if not self.modules_json.exists():
            self.logger.info(u'Download latest modules.json file from raspiot repository')
            self.modules_json.update()

    def _stop(self):
        """
        Stop module
        """
        #stop monitoring task
        self.__stop_monitoring_threads()

    def __configure_crash_report(self, enable):
        """
        Configure crash report

        Args:
            enable (bool): True to enable crash report
        """
        #configure crash report
        if enable:
            self.crash_report.enable()
        else:
            self.crash_report.disable()

        if not self.crash_report.is_enabled():
            self.logger.info(u'Crash report is disabled')

    def get_module_config(self):
        """
        Return full module configuration

        Returns:
            dict: configuration
        """
        config = self._get_config()
        raspiot = RaspiotConf(self.cleep_filesystem)

        out = {}
        out[u'monitoring'] = self.get_monitoring()
        out[u'uptime'] = self.get_uptime()
        out[u'needrestart'] = self.__need_restart
        out[u'needreboot'] = self.__need_reboot
        out[u'crashreport'] = config[u'crashreport']
        out[u'version'] = VERSION
        out[u'eventsnotrendered'] = self.get_events_not_rendered()
        out[u'debug'] = {
            u'system': raspiot.is_system_debugged(),
            u'trace': raspiot.is_trace_enabled()
        }
        out[u'raspiotbackupdelay'] = self.raspiot_backup_delay

        #update related values
        out[u'lastcheckraspiot'] = config[u'lastcheckraspiot']
        out[u'lastcheckmodules'] = config[u'lastcheckmodules']
        out[u'raspiotupdateenabled'] = config[u'raspiotupdateenabled']
        out[u'modulesupdateenabled'] = config[u'modulesupdateenabled']
        out[u'raspiotupdateavailable'] = config[u'raspiotupdateavailable']
        out[u'modulesupdateavailable'] = config[u'modulesupdateavailable']
        out[u'lastraspiotupdate'] = config[u'lastraspiotupdate']
        out[u'lastmodulesinstalls'] = config[u'lastmodulesinstalls']
        out[u'raspiotupdatepending'] = self.raspiot_update_pending

        return out

    def get_module_devices(self):
        """
        Return system devices

        Returns:
            dict: devices
        """
        devices = super(System, self).get_module_devices()
        
        for uuid in devices:
            if devices[uuid][u'type']==u'monitor':
                data = {}
                data[u'uptime'] = self.get_uptime()
                data[u'cpu'] = self.get_cpu_usage()
                data[u'memory'] = self.get_memory_usage()
                devices[uuid].update(data)

        return devices

    def event_received(self, event):
        """
        Watch for specific event

        Args:
            event (MessageRequest): event data
        """
        #handle restart event
        if event[u'event'].endswith('system.needrestart'):
            self.__need_restart = True

        #handle reboot event
        elif event[u'event'].endswith('system.needreboot'):
            self.__need_reboot = True

        if event[u'event']==u'system.time.now':
            #update
            if event[u'params'][u'hour']==12 and event[u'params'][u'minute']==0:
                #check updates at noon
                self.check_raspiot_updates()
                self.check_modules_updates()

                #and perform updates if allowed
                config = self._get_config()
                if config[u'raspiotupdateenabled'] is True and self.raspiot_update_pending is False and config[u'raspiotupdateavailable'] is True:
                    self.update_raspiot()
                if config[u'modulesupdateenabled'] is True:
                    #TODO update modules that need to be updated
                    pass

            #backup
            if not event[u'params'][u'minute'] % self.raspiot_backup_delay:
                self.backup_raspiot_config()

    def set_monitoring(self, monitoring):
        """
        Set monitoring flag
        
        Params:
            monitoring (bool): monitoring flag
        """
        if monitoring is None:
            raise MissingParameter(u'Monitoring parameter missing')

        if not self._set_config_field(u'monitoring', monitoring):
            raise CommandError(u'Unable to save configuration')

    def get_monitoring(self):
        """
        Return monitoring configuration

        Returns:
            dict: monitoring configuration
        """
        return self._get_config_field(u'monitoring')

    def reboot_system(self, delay=5.0):
        """
        Reboot system
        """
        #backup configuration
        self.backup_raspiot_config()

        #send event
        self.systemSystemReboot.send()

        #and reboot system
        console = Console()
        console.command_delayed(u'reboot', delay)

    def halt_system(self, delay=5.0):
        """
        Halt system
        """
        #backup configuration
        self.backup_raspiot_config()

        #send event
        self.systemSystemHalt.send()

        #and reboot system
        console = Console()
        console.command_delayed(u'halt', delay)

    def restart(self, delay=3.0):
        """
        Restart raspiot
        """
        #backup configuration
        self.backup_raspiot_config()

        #send event
        self.systemSystemRestart.send()

        #and restart raspiot
        console = Console()
        console.command_delayed(u'/etc/raspiot/raspiot_helper.sh restart', delay)

    def __get_module_infos(self, module):
        """
        Return module infos from modules.json file

        Args:
            module (string): module name

        Return:
            dict: module infos
        """
        #get modules.json content
        modules_json = self.modules_json.get_json()

        #check module presence in modules.json file
        if module not in modules_json[u'list']:
            self.logger.error(u'Module "%s" not found in modules list' % module)
            raise CommandError(u'Module "%s" not found in modules list' % module)

        module_infos = modules_json[u'list'][module]
        self.logger.debug('Module infos: %s' % module_infos)

        return module_infos

    def __module_install_callback(self, status):
        """
        Module install callback

        Args:
            status (dict): process status {stdout (list), stderr (list), status (int), module (string)}
        """
        self.logger.debug(u'Module install callback status: %s' % status)
        
        #send process status
        self.systemModuleInstall.send(params=status)

        #save last stdout/stderr from install
        if status[u'status'] in (Install.STATUS_DONE, Install.STATUS_ERROR):
            lastmodulesinstalls = self._get_config_field(u'lastmodulesinstalls')
            lastmodulesinstalls[status[u'module']] = {
                u'status': status[u'status'],
                u'time': int(time.time()),
                u'stdout': status[u'stdout'],
                u'stderr': status[u'stderr']
            }
            self._set_config_field(u'lastmodulesinstalls', lastmodulesinstalls)

        #handle end of process to trigger restart
        if status[u'status']==Install.STATUS_DONE:
            #need to restart
            self.__need_restart = True

            #update raspiot.conf
            raspiot = RaspiotConf(self.cleep_filesystem)
            return raspiot.install_module(status[u'module'])

    def install_module(self, module):
        """
        Install specified module

        Params:
            module (string): module name to install

        Returns:
            bool: True if module installed
        """
        #check params
        if module is None or len(module)==0:
            raise MissingParameter(u'Parameter "module" is missing')

        #get module infos
        infos = self.__get_module_infos(module)

        #launch installation (non blocking)
        install = Install(self.cleep_filesystem, self.__module_install_callback)
        install.install_module(module, infos)

        return True

    def __module_uninstall_callback(self, status):
        """
        Module uninstall callback

        Args:
            status (dict): process status {stdout (list), stderr (list), status (int), module (string)}
        """
        self.logger.debug(u'Module uninstall callback status: %s' % status)
        
        #send process status to ui
        self.systemModuleUninstall.send(params=status)

        #handle end of process to trigger restart
        if status[u'status']==Install.STATUS_DONE:
            self.__need_restart = True

            #update raspiot.conf
            raspiot = RaspiotConf(self.cleep_filesystem)
            return raspiot.uninstall_module(status[u'module'])

    def uninstall_module(self, module):
        """
        Uninstall specified module

        Params:
            module (string): module name to install

        Returns:
            bool: True if module uninstalled
        """
        #check params
        if module is None or len(module)==0:
            raise MissingParameter(u'Parameter "module" is missing')

        #launch uninstallation
        install = Install(self.cleep_filesystem, self.__module_uninstall_callback)
        install.uninstall_module(module)

        return True

    def __module_update_callback(self, status):
        """
        Module update callback

        Args:
            status (dict): process status {stdout (list), stderr (list), status (int), module (string)}
        """
        self.logger.debug(u'Module update callback status: %s' % status)
        
        #send process status to ui
        self.systemModuleUpdate.send(params=status)

        #save last stdout/stderr from install
        if status[u'status'] in (Install.STATUS_DONE, Install.STATUS_ERROR):
            lastmodulesinstalls = self._get_config_field(u'lastmodulesinstalls')
            lastmodulesinstalls[status[u'module']] = {
                u'status': status[u'status'],
                u'time': int(time.time()),
                u'stdout': status[u'stdout'],
                u'stderr': status[u'stderr']
            }
            self._set_config_field(u'lastmodulesinstalls', lastmodulesinstalls)

        #handle end of process to trigger restart
        if status[u'status']==Install.STATUS_DONE:
            self.__need_restart = True

            #update raspiot.conf adding module to updated ones
            raspiot = RaspiotConf(self.cleep_filesystem)
            return raspiot.update_module(status[u'module'])

    def update_module(self, module):
        """
        Update specified module

        Params:
            module (string): module name to install

        Returns:
            bool: True if module uninstalled
        """
        #check params
        if module is None or len(module)==0:
            raise MissingParameter(u'Parameter "module" is missing')

        #get module infos
        infos = self.__get_module_infos(module)

        #launch module update
        install = Install(self.cleep_filesystem, self.__module_update_callback)
        install.update_module(module, infos)

        return True

    def set_automatic_update(self, raspiot_update_enabled, modules_update_enabled):
        """
        Set automatic update values

        Args:
            raspiot_update_enabled (bool): enable raspiot automatic update
            modules_update_enabled (bool): enable modules automatic update
        """
        if not isinstance(raspiot_update_enabled, bool):
            raise InvalidParameter('Parameter "raspiot_update_enabled" is invalid')
        if not isinstance(modules_update_enabled, bool):
            raise InvalidParameter('Parameter "modules_update_enabled" is invalid')

        return self._update_config({
            u'raspiotupdateenabled': raspiot_update_enabled,
            u'modulesupdateenabled': modules_update_enabled
        })

    def __get_modules(self):
        """
        Get modules from inventory if necessary

        Return:
            dict: modules dict as returned by inventory
        """
        if len(self.__modules)==0:
            #retrieve modules from inventory
            resp = self.send_command(u'get_modules', u'inventory')
            if not resp or resp[u'error']:
                raise CommandError(u'Unable to get modules list from inventory')
            self.__modules = resp[u'data']

            #iterate over modules
            modules_to_delete = []
            for module in self.__modules:
                #locked module needs to be removed from list (system module updated by raspiot)
                #like not installed modules
                if self.__modules[module][u'locked'] or not self.__modules[module][u'installed']:
                    modules_to_delete.append(module)
                
                #append updatable/updating flags
                self.__modules[module][u'updatable'] = None
                self.__modules[module][u'updating'] = module in self.__updating_modules

            #remove system modules
            for module in modules_to_delete:
                self.__modules.pop(module)
            #self.logger.debug(u'Modules list: %s' % self.__modules)

        return self.__modules

    def check_modules_updates(self):
        """
        Check for modules updates.

        Return:
            dict: last update infos::
                {
                    updateavailable (bool): True if update available
                    lastcheckraspiot (int): last raspiot update check timestamp
                    lastcheckmodules (int): last modules update check timestamp
                }
        """
        #get modules list from inventory
        modules = self.__get_modules()

        #update latest modules.json file
        self.modules_json.update()
        remote_modules_json = self.modules_json.get_json()

        #check downloaded file validity
        if u'list' not in remote_modules_json or u'update' not in remote_modules_json:
            #invalid modules.json
            self.logger.error(u'Invalid modules.json file downloaded, unable to update modules')
            raise CommandError(u'Invalid modules.json file downloaded, unable to update modules')

        #load local modules.json file
        local_modules_json = None
        if self.modules_json.exists():
            #local file exists, load its content
            local_modules_json = self.modules_json.get_json()

        #check if new modules.json file version available
        if local_modules_json is None or remote_modules_json[u'update']>local_modules_json[u'update']:
            #file isn't existing yet or updated, overwrite local one
            self.logger.debug(u'Save new modules.json file: %s' % remote_modules_json)
            self.cleep_filesystem.write_json(MODULES_JSON, remote_modules_json)
            local_modules_json = remote_modules_json

        #check for modules updates available
        update_available = False
        for module in modules:
            current_version = modules[module][u'version']
            if module in local_modules_json[u'list']:
                new_version = local_modules_json[u'list'][module][u'version']
                if Tools.compare_versions(current_version, new_version):
                    #new version available for current module
                    self.logger.info('New version available for module "%s" (%s->%s)' % (module, current_version, new_version))
                    modules[module][u'updatable'] = True
                    update_available = True

                else:
                    self.logger.debug('No new version available for module "%s" (%s->%s)' % (module, current_version, new_version))

        #update config
        config = {
            u'modulesupdateavailable': update_available,
            u'lastcheckmodules': int(time.time())
        }
        self._update_config(config)

        return {
            u'updateavailable': update_available,
            u'lastcheckmodules': config[u'lastcheckmodules'],
        }

    def check_raspiot_updates(self):
        """
        Check for available raspiot updates

        Return:
            dict: last update infos::
                {
                    updateavailable (bool): True if update available
                    lastcheckraspiot (int): last raspiot update check timestamp
                    lastcheckmodules (int): last modules update check timestamp
                }
        """
        #init
        update_available = False
        self.__raspiot_update[u'package'] = None
        self.__raspiot_update[u'checksum'] = None

        try:
            github = Github()
            releases = github.get_releases(self.RASPIOT_GITHUB_OWNER, self.RASPIOT_GITHUB_REPO, only_latest=True)
            if len(releases)==1:
                #get latest version available
                version = github.get_release_version(releases[0])
                self.logger.debug('Compare version: (online)%s!=(installed)%s' % (version, VERSION))
                if version!=VERSION:
                    #new version available, trigger update
                    assets = github.get_release_assets_infos(releases[0])

                    #search for deb file
                    for asset in assets:
                        if asset[u'name'].startswith(u'raspiot_') and asset[u'name'].endswith('.zip'):
                            self.logger.debug(u'Found raspiot package asset: %s' % asset)
                            self.__raspiot_update[u'package'] = asset
                            break

                    #search for checksum file
                    if self.__raspiot_update[u'package'] is not None:
                        package_name = os.path.splitext(self.__raspiot_update[u'package'][u'name'])[0]
                        checksum_name = u'%s.%s' % (package_name, u'sha256')
                        self.logger.debug(u'Checksum filename to search: %s' % checksum_name)
                        for asset in assets:
                            if asset[u'name']==checksum_name:
                                self.logger.debug(u'Found checksum asset: %s' % asset)
                                self.__raspiot_update[u'checksum'] = asset
                                break

                    if self.__raspiot_update[u'package'] and self.__raspiot_update[u'checksum']:
                        self.logger.debug(u'Update and checksum found, can trigger update')
                        self.logger.debug(u'raspiot_update: %s' % self.__raspiot_update)
                        update_available = True

            else:
                #no release found
                self.logger.warning(u'No release found during check')

        except:
            self.logger.exception(u'Error occured during updates checking:')
            self.crash_report.report_exception()
            raise Exception(u'Error occured during raspiot update check')

        #update config
        config = {
            u'raspiotupdateavailable': update_available,
            u'lastcheckraspiot': int(time.time())
        }
        self._update_config(config)

        return {
            u'updateavailable': update_available,
            u'lastcheckraspiot': config[u'lastcheckraspiot']
        }

    def __update_raspiot_callback(self, status):
        """
        Raspiot update callback

        Args:
            status (dict): update status
        """
        self.logger.debug(u'Raspiot update callback status: %s' % status)

        #send process status (only status)
        self.systemRaspiotUpdate.send(params={u'status':status[u'status']})

        #save final status when update terminated (successfully or not)
        if status[u'status']>=InstallRaspiot.STATUS_UPDATED:
            self.logger.debug(u'Store update result in config file')
            stdout = []
            stderr = []

            #prescript
            try:
                if status[u'prescript'][u'returncode'] is not None:
                    stdout += [u'Pre-script output:']
                    if len(status[u'prescript'][u'stdout'])>0:
                        stdout += [u' '*4 + line for line in status[u'prescript'][u'stdout']]
                    else:
                        stdout += [u' '*4 + u'No output']
                    stdout += [u'', u'Pre-script return code: %s' % status[u'prescript'][u'returncode']]
                    stderr += [u'Pre-script errors']
                    if len(status[u'prescript'][u'stderr'])>0:
                        stderr += [u' '*4 + line for line in status[u'prescript'][u'stderr']]
                    else:
                        stderr += [u' '*4 + u'No error']
                else:
                    stdout += [u'No pre-script found']
            except:
                self.logger.exception(u'Error saving prescript output:')
                self.crash_report.report_exception()

            #deb
            try:
                if status[u'deb'][u'returncode'] is not None:
                    stdout += [u'', u'Package output:']
                    if len(status[u'deb'][u'stdout'])>0:
                        stdout += [u' '*4 + line for line in status[u'deb'][u'stdout']]
                    else:
                        stdout += [u' '*4 + u'No output']
                    stdout += [u'', u'Package return code: %s' % status[u'deb'][u'returncode']]
                    #stderr merge to stdout because dpkg and pip put some info on stderr
                else:
                    stdout += [u'', u'No package found']
            except:
                self.logger.exception(u'Error saving deb output:')
                self.crash_report.report_exception()

            #postscript
            try:
                if status[u'postscript'][u'returncode'] is not None:
                    stdout += [u'', u'Post-script output:']
                    if len(status[u'postscript'][u'stdout'])>0:
                        stdout += [u' '*4 + line for line in status[u'postscript'][u'stdout']]
                    else:
                        stdout += [u' '*4 + u'No output']
                    stdout += [u'', u'Post-script return code: %s' % status[u'postscript'][u'returncode']]
                    stderr += [u'', u'Post-script errors:']
                    if len(status[u'postscript'][u'stderr'])>0:
                        stderr += [u' '*4 + line for line in status[u'postscript'][u'stderr']]
                    else:
                        stderr += [u' '*4 + u'No error']
                else:
                    stdout += [u'', u'No post-script found']
            except:
                self.logger.exception(u'Error saving postscript output:')
                self.crash_report.report_exception()

            #save update status
            self._update_config({
                u'raspiotupdateavailable': False,
                u'lastraspiotupdate': {
                    u'status': status[u'status'],
                    u'time': int(time.time()),
                    u'stdout': stdout,
                    u'stderr': stderr
                }
            })
    
        #handle end of successful process to trigger restart
        if status[u'status']==InstallRaspiot.STATUS_UPDATED:
            #need to reboot
            #TODO reboot automatically instead ?
            self.raspiot_update_pending = True
            self.__need_reboot = True

    def update_raspiot(self):
        """
        Update raspiot
        """
        #check params
        if not self.__raspiot_update[u'package'] or not self.__raspiot_update[u'checksum']:
            #user trigger raspiot update and there is no update infos. Check again
            self.logger.debug('Raspiot update trigger while there is no update infos, check again')
            res = self.check_raspiot_updates()
            if not res[u'updateavailable']:
                #there is really no update available
                raise CommandError(u'No raspiot update available')
            else:
                self.logger.debug('Finally an update is available, process it')

        #launch install
        package_url = self.__raspiot_update[u'package'][u'url']
        checksum_url = self.__raspiot_update[u'checksum'][u'url']
        self.logger.debug('Update raspiot, package url: %s' % package_url)
        self.logger.debug('Update raspiot, checksum url: %s' % checksum_url)
        update = InstallRaspiot(package_url, checksum_url, self.__update_raspiot_callback, self.cleep_filesystem)
        update.start()

        return True

    def get_memory_usage(self):
        """
        Return system memory usage

        Returns:
            dict: memory usage::
                {
                    'total': <total memory in bytes (int)>',
                    'available':<available memory in bytes (int)>,
                    'available_hr':<human readble available memory (string)>,
                    'raspiot': <raspiot process memory in bytes (float)>
                }
        """
        system = psutil.virtual_memory()
        raspiot = self.__process.memory_info()[0]
        return {
            u'total': system.total,
            #u'total_hr': Tools.hr_bytes(system.total),
            u'available': system.available,
            u'available_hr': Tools.hr_bytes(system.available),
            #u'used_percent': system.percent,
            u'raspiot': raspiot,
            #u'raspiot_hr': Tools.hr_bytes(raspiot),
            #u'others': system.total - system.available - raspiot
        }

    def get_cpu_usage(self):
        """
        Return system cpu usage

        Returns:
            dict: cpu usage::
                {
                    'system': <system cpu usage percentage (float)>,
                    'raspiot': <raspiot cpu usage percentage (float>)>
                }
        """
        system = psutil.cpu_percent()
        if system>100.0:
            system = 100.0
        raspiot = self.__process.cpu_percent()
        if raspiot>100.0:
            raspiot = 100.0
        return {
            u'system': system,
            u'raspiot': raspiot
        }

    def get_uptime(self):
        """
        Return system uptime (in seconds)

        Returns:
            int: uptime
        """
        uptime = int(time.time() - psutil.boot_time())
        return {
            u'uptime': uptime,
            u'uptime_hr': Tools.hr_uptime(uptime)
        }

    def __start_monitoring_threads(self):
        """
        Start monitoring threads
        """
        self.__monitoring_cpu_task = Task(self.MONITORING_CPU_DELAY, self.__monitoring_cpu_thread, self.logger)
        self.__monitoring_cpu_task.start()
        self.__monitoring_memory_task = Task(self.MONITORING_MEMORY_DELAY, self.__monitoring_memory_thread, self.logger)
        self.__monitoring_memory_task.start()
        self.__monitoring_disks_task = Task(self.MONITORING_DISKS_DELAY, self.__monitoring_disks_thread, self.logger)
        self.__monitoring_disks_task.start()

    def __stop_monitoring_threads(self):
        """
        Stop monitoring threads
        """
        if self.__monitoring_cpu_task is not None:
            self.__monitoring_cpu_task.stop()
        if self.__monitoring_memory_task is not None:
            self.__monitoring_memory_task.stop()
        if self.__monitoring_disks_task is not None:
            self.__monitoring_disks_task.stop()

    def __monitoring_cpu_thread(self):
        """
        Read cpu usage 
        """
        config = self._get_config()

        #send event if monitoring activated
        if config[u'monitoring']:
            self.systemMonitoringCpu.send(params=self.get_cpu_usage(), device_id=self.__monitor_cpu_uuid)

    def __monitoring_memory_thread(self):
        """
        Read memory usage
        Send alert if threshold reached
        """
        config = self._get_config()
        memory = self.get_memory_usage()

        #detect memory leak
        percent = (float(memory[u'total'])-float(memory[u'available']))/float(memory[u'total'])*100.0
        if percent>=self.THRESHOLD_MEMORY:
            self.systemAlertMemory.send(params={u'percent':percent, u'threshold':self.THRESHOLD_MEMORY})

        #send event if monitoring activated
        if config[u'monitoring']:
            self.systemMonitoringMemory.send(params=memory, device_id=self.__monitor_memory_uuid)

    def __monitoring_disks_thread(self):
        """
        Read disks usage
        Only used to send alert when threshold reached
        """
        disks = self.get_filesystem_infos()
        for disk in disks:
            if disk[u'mounted']:
                if disk[u'mountpoint']==u'/' and disk[u'percent']>=self.THRESHOLD_DISK_SYSTEM:
                    self.systemAlertDisk.send(params={u'percent':disk[u'percent'], u'threshold':self.THRESHOLD_DISK_SYSTEM, u'mountpoint':disk[u'mountpoint']})

                elif disk[u'mountpoint'] not in (u'/', u'/boot') and disk[u'percent']>=self.THRESHOLD_DISK_EXTERNAL:
                    self.systemAlertDisk.send(params={u'percent':disk[u'percent'], u'threshold':self.THRESHOLD_DIST_EXTERNAL, u'mountpoint':disk[u'mountpoint']})

    def get_filesystem_infos(self):
        """
        Return filesystem infos (all values are in octets)

        Returns:
            list: list of devices available with some informations::
                [
                    {
                        'device': <device path /dev/XXX (string)>
                        'uuid': <device uuid like found in blkid (string)>,
                        'system': <system partition (bool)>,
                        'mountpoint': <mountpoint (string)>
                        'mounted': <partition is mounted (bool)>,
                        'mounttype': <partition type (string)>,
                        'options': <mountpoint options (string)>,
                        'total': <partition total space in octets (number)>,
                        'used': <partition used space in octets (number)>,
                        'free': <partition free space in octets (number)>,
                        'percent': <partition used space in percentage (number)>
                    },
                    ...
                ]
        """
        #get mounted partitions and all devices
        fstab = Fstab(self.cleep_filesystem)
        mounted_partitions = fstab.get_mountpoints()
        self.logger.debug(u'mounted_partitions=%s' % mounted_partitions)
        all_devices = fstab.get_all_devices()
        self.logger.debug(u'all_devices=%s' % all_devices)

        #build output
        fsinfos = []
        for device in all_devices:
            #check if partition is mounted
            mounted = {u'mounted':False, u'mountpoint':u'', u'mounttype':'-', u'options':'', u'uuid':None}
            system = False
            for partition in mounted_partitions:
                if mounted_partitions[partition][u'device']==device:
                    mounted[u'mounted'] = True
                    mounted[u'mountpoint'] = mounted_partitions[partition][u'mountpoint']
                    mounted[u'device'] = mounted_partitions[partition][u'device']
                    mounted[u'uuid'] = mounted_partitions[partition][u'uuid']
                    mounted[u'mounttype'] = mounted_partitions[partition][u'mounttype']
                    mounted[u'options'] = mounted_partitions[partition][u'options']
                    if mounted_partitions[partition][u'mountpoint'] in (u'/', u'/boot'):
                        system = True

            #get mounted partition usage
            usage = {u'total':0, u'used':0, u'free':0, u'percent':0.0}
            if mounted[u'mounted']:
                sdiskusage = psutil.disk_usage(mounted[u'mountpoint'])
                self.logger.debug(u'diskusage for %s: %s' % (device, sdiskusage));
                usage[u'total'] = sdiskusage.total
                usage[u'used'] = sdiskusage.used
                usage[u'free'] = sdiskusage.free
                usage[u'percent'] = sdiskusage.percent

            #fill infos
            fsinfos.append({
                u'device': device,
                u'uuid': mounted[u'uuid'],
                u'system': system,
                u'mountpoint': mounted[u'mountpoint'],
                u'mounted': mounted[u'mounted'],
                u'mounttype': mounted[u'mounttype'],
                u'options': mounted[u'options'],
                u'total': usage[u'total'],
                u'used': usage[u'used'],
                u'free': usage[u'free'],
                u'percent': usage[u'percent']
            })

        self.logger.debug(u'Filesystem infos: %s' % fsinfos)
        return fsinfos

    def __purge_cpu_data(self):
        """
        Purge cpu data (keep 1 week)
        """
        params = {
            u'uuid': self.__monitor_cpu_uuid,
            u'timestamp_until': int(time.time()) - 604800
        }

        try:
            self.send_command(u'purge_data', u'database', params, 10.0)

        except InvalidModule:
            #database module not loaded, drop
            pass

        except NoResponse:
            self.logger.warning(u'Unable to purge CPU usage from database')

        except:
            self.logger.exception(u'Unable to purge CPU usage from database:')
            self.crash_report.report_exception()

    def __purge_memory_data(self):
        """
        Purge memory data (keep 1 month)
        """
        params = {
            u'uuid': self.__monitor_memory_uuid,
            u'timestamp_until': int(time.time()) - 2592000
        }

        try:
            self.send_command(u'purge_data', u'database', params, 10.0)

        except InvalidModule:
            #database module not loaded, drop
            pass

        except NoResponse:
            self.logger.warning(u'Unable to purge memory usage from database')

        except:
            self.logger.exception(u'Unable to purge memory usage from database:')
            self.crash_report.report_exception()

    def download_logs(self):
        """
        Download logs file

        Returns:
            string: script full path

        Raises:
            Exception: if error occured
        """
        if os.path.exists(self.LOG_FILE):
            #log file exists

            #zip it
            fd = NamedTemporaryFile(delete=False)
            log_filename = fd.name
            self.logger.debug(u'Zipped log filename: %s' % log_filename)
            archive = ZipFile(fd, u'w', ZIP_DEFLATED)
            archive.write(self.LOG_FILE, u'raspiot.log')
            archive.close()

            now = datetime.now()
            filename = u'raspiot_%d%02d%02d_%02d%02d%02d.zip' % (now.year, now.month, now.day, now.hour, now.minute, now.second)

            return {
                u'filepath': log_filename,
                u'filename': filename
            }

        else:
            #file doesn't exist, raise exception
            raise Exception(u'Logs file doesn\'t exist')

    def get_logs(self):
        """
        Return logs file content
        """
        lines = []
        if os.path.exists(self.LOG_FILE):
            lines = self.cleep_filesystem.read_data(self.LOG_FILE)

        return lines

    def set_trace(self, trace):
        """
        Set trace (full debug)

        Args:
            trace (bool): enable trace
        """
        if trace is None:
            raise MissingParameter(u'Parameter "trace" is missing')

        #save log level in conf file
        conf = RaspiotConf(self.cleep_filesystem)
        if trace:
            conf.enable_trace()
        else:
            conf.disable_trace()

        #send event raspiot needs to be restarted
        self.__need_restart = True
        self.systemNeedRestart.send()

    def set_system_debug(self, debug):
        """
        Set debug on all system modules

        Args:
            debug (bool): enable debug
        """
        if debug is None:
            raise MissingParameter(u'Parameter "debug" is missing')

        conf = RaspiotConf(self.cleep_filesystem)
        if debug:
            self.events_factory.logger.setLevel(logging.DEBUG)
            self.cleep_filesystem.logger.setLevel(logging.DEBUG)

            conf.enable_system_debug()
        else:
            self.events_factory.logger.setLevel(logging.INFO)
            self.cleep_filesystem.logger.setLevel(logging.INFO)

            conf.disable_system_debug()

    def set_module_debug(self, module, debug):
        """
        Set module debug flag

        Args:
            module (string): module name
            debug (bool): enable debug
        """
        if module is None or len(module)==0:
            raise MissingParameter(u'Parameter "module" is missing')
        if debug is None:
            raise MissingParameter(u'Parameter "debug" is missing')

        #save log level in conf file
        conf = RaspiotConf(self.cleep_filesystem)
        if debug:
            conf.enable_module_debug(module)
        else:
            conf.disable_module_debug(module)

        #set debug on module
        if module==u'rpc':
            #specific command for rpcserver
            resp = self.send_command(u'set_rpc_debug', u'inventory', {u'debug':debug})
        else:
            resp = self.send_command(u'set_debug', module, {u'debug':debug})

        #process command response
        if not resp:
            self.logger.error(u'No response')
            raise CommandError(u'No response from "%s" module' % module)
        elif resp[u'error']:
            self.logger.error(u'Unable to set debug on module %s: %s' % (module, resp[u'message']))
            raise CommandError(u'Update debug failed')

    def __update_events_not_rendered_in_factory(self):
        """
        Update events factory with list of events to not render
        """
        self.events_factory.update_events_not_rendered(self.get_events_not_rendered())

    def set_event_not_rendered(self, renderer, event, disabled):
        """
        Set event not rendered

        Args:
            renderer (string): renderer name
            event (string): event name
            value (bool): enable/disable value

        Return:
            list: list of events not rendered
        """
        if renderer is None or len(renderer)==0:
            raise MissingParameter(u'Renderer parameter is missing')
        if event is None or len(event)==0:
            raise MissingParameter(u'Event parameter is missing')
        if disabled is None:
            raise MissingParameter(u'Disabled parameter is missing')
        if not isinstance(disabled, bool):
            raise InvalidParameter(u'Disabled parameter is invalid, must be bool')

        events_not_rendered = self._get_config_field(u'eventsnotrendered')
        key = '%s__%s' % (renderer, event)
        if key in events_not_rendered and not disabled:
            #enable renderer event
            events_not_rendered.remove(key)
        else:
            #disable renderer event
            events_not_rendered.append(key)
        if not self._set_config_field(u'eventsnotrendered', events_not_rendered):
            raise CommandError(u'Unable to save configuration')

        #configure events factory with new events to not render
        self.__update_events_not_rendered_in_factory()

        return self.get_events_not_rendered()

    def get_events_not_rendered(self):
        """
        Return list of not rendered events

        Return:
            list: list of events to not render::
                [
                    {
                        event (string): event name,
                        renderer (string): renderer name
                    },
                    ...
                ]
        """
        config = self._get_config()

        #split items to get renderer and event splitted
        events_not_rendered = []
        for item in config[u'eventsnotrendered']:
            (renderer, event) = item.split(u'__')
            events_not_rendered.append({
                u'renderer': renderer,
                u'event': event
            })

        return events_not_rendered

    def set_crash_report(self, enable):
        """
        Enable or disable crash report

        Args:
            enable (bool): True to enable crash report

        Returns:
            bool: True if crash report status updated

        Raises:
            CommandError if error occured
        """
        if enable is None:
            raise MissingParameter(u'Parameter "enable" is missing')

        #save config
        if not self._set_config_field(u'crashreport', enable):
            raise CommandError(u'Unable to save crash report value')
            
        #configure crash report
        self.__configure_crash_report(enable)

        return True

    def backup_raspiot_config(self):
        """
        Backup raspiot configuration files on filesystem

        Returns:
            bool: True if backup successful
        """
        self.logger.debug(u'Backup raspiot configuration')
        return self.raspiot_backup.backup()

    def set_raspiot_backup_delay(self, delay):
        """
        Set raspiot backup delay

        Args:
            minute (int): delay in minutes (5..60)
        """
        #check params
        if delay is None:
            raise MissingParameter(u'Parameter "delay" must be specified')
        if delay<5 or delay>60:
            raise MissingParameter(u'Parameter "delay" must be 0..60')

        res = self._set_config_field(u'raspiotbackupdelay', delay)
        if res:
            self.raspiot_backup_delay = delay

        return res

