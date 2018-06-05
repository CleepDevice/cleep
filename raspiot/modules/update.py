#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
import time
import json
from raspiot.raspiot import RaspIotModule
from raspiot.modules.system import MODULES_JSON
from raspiot.libs.download import Download
from raspiot.libs.install import Install
from raspiot.libs.github import Github
from raspiot import __version__ as VERSION
from raspiot.libs.task import BackgroundTask
from raspiot.utils import CommandError, InvalidParameter

__all__ = [u'Update']


class Update(RaspIotModule):
    """
    Handle device and modules updates
    """
    MODULE_AUTHOR = u'Cleep'
    MODULE_VERSION = u'1.0.0'
    MODULE_PRICE = 0
    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Keep your device up-to-date with automatic updates'
    MODULE_LOCKED = True
    MODULE_TAGS = [u'update', u'raspiot']
    MODULE_COUNTRY = None
    MODULE_URLINFO = None
    MODULE_URLHELP = None
    MODULE_URLSITE = None
    MODULE_URLBUGS = None

    MODULE_CONFIG_FILE = u'update.conf'
    DEFAULT_CONFIG = {
        u'lastupdate': None,
        u'lastcheckraspiot': None,
        u'lastcheckmodules': None,
        u'laststdout': u'',
        u'laststderr': u'',
        u'raspiotupdate': True,
        u'modulesupdate': True,
        u'status': 0 #STATUS_IDLE
    }

    RASPIOT_GITHUB_OWNER = u'tangb'
    RASPIOT_GITHUB_REPO = u'raspiot'
    RASPIOT_MODULES_JSON = u'https://raw.githubusercontent.com/tangb/raspiot/master/modules.json'

    STATUS_IDLE = 0
    STATUS_DOWNLOADING = 1
    STATUS_DOWNLOADING_ERROR = 2
    STATUS_DOWNLOADING_ERROR_INVALIDSIZE = 3
    STATUS_DOWNLOADING_ERROR_BADCHECKSUM = 4
    STATUS_INSTALLING = 5
    STATUS_INSTALLING_ERROR = 6
    STATUS_INSTALLING_DONE = 7
    STATUS_CANCELED = 8
    STATUS_COMPLETED = 9
    STATUS_ERROR = 10

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): flag to set debug level to logger
        """
        RaspIotModule.__init__(self, bootstrap, debug_enabled)

        #members
        self.__raspiot_update = {
            u'asset': None,
            u'checksum': None
        }
        self.status = {
            u'status': self.STATUS_IDLE,
            u'downloadfilesize': 0,
            u'downloadpercent': 0,
        }
        self.__update_task = None
        self.__modules = {}
        self.__updating_modules = []

        #events
        self.updateStatusUpdate = self._get_event(u'update.status.update')
        self.systemSystemNeedrestart = self._get_event(u'system.system.needrestart')

    def _configure(self):
        """
        Configure module
        """
        #reset update
        self.__reset_update(self.STATUS_IDLE)

        #download modules.json file if not exists
        if not os.path.exists(MODULES_JSON):
            try:
                self.logger.info(u'Download latest modules.json file from raspiot repository')
                modules_json = self.__download_latest_modules_json()
                if modules_json:
                    self.cleep_filesystem.write_json(MODULES_JSON, modules_json)
            except:
                self.logger.exception(u'File modules.json download failed:')

        #start update task
        self.__update_task = BackgroundTask(self.__update_raspiot, self.logger, pause=10.0)
        self.__update_task.start()

    def _stop(self):
        """
        Stop module
        """
        if self.__update_task:
            self.__update_task.stop()

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
                #TODO check version with modules.json => need to create lib to handle modules.json first
                self.__modules[module][u'updatable'] = None
                self.__modules[module][u'updating'] = module in self.__updating_modules

            #remove system modules
            for module in modules_to_delete:
                self.__modules.pop(module)
            #self.logger.debug(u'Modules list: %s' % self.__modules)

        return self.__modules

    def __download_callback(self, status, filesize, percent):
        """
        Download callback
        """
        #update status
        self.logger.debug('Download callback: %s %s %s' % (status, filesize, percent))
        if status in (Download.STATUS_DOWNLOADING, Download.STATUS_DOWNLOADING_NOSIZE):
            self.status[u'status'] = self.STATUS_DOWNLOADING
        elif status==Download.STATUS_ERROR:
            self.status[u'status'] = self.STATUS_DOWNLOADING_ERROR
        elif status==Download.STATUS_ERROR_INVALIDSIZE:
            self.status[u'status'] = self.STATUS_DOWNLOADING_ERROR_INVALIDSIZE
        elif status==Download.STATUS_ERROR_BADCHECKSUM:
            self.status[u'status'] = self.STATUS_DOWNLOADING_ERROR_BADCHECKSUM
        self.status[u'downloadfilesize'] = filesize
        self.status[u'downloadpercent'] = percent

        #send event to update ui
        self.updateStatusUpdate.send(params=self.get_status(), to=u'rpc')

    def __install_callback(self, status):
        """
        Install callback
        """
        #update status
        self.logger.debug('Install callback: %s' % status)
        if status[u'status']==Install.STATUS_PROCESSING:
            self.status[u'status'] = self.STATUS_INSTALLING
        elif status[u'status']==Install.STATUS_ERROR:
            self.status[u'status'] = self.STATUS_INSTALLING_ERROR
        elif status[u'status']==Install.STATUS_DONE:
            self.status[u'status'] = self.STATUS_INSTALLING_DONE

        #update last stdout/stderr
        if status[u'status'] in (Install.STATUS_ERROR, Install.STATUS_DONE):
            config = self._get_config()
            config[u'laststdout'] = status[u'stdout']
            config[u'laststderr'] = status[u'stderr']
            self._save_config(config)

        #send event to update ui
        self.updateStatusUpdate.send(params=self.get_status(), to=u'rpc')

    def __reset_update(self, status=None):
        """
        Reset all update members

        Args:
            status (int): current status (use STATUS_XXX)
        """
        self.__raspiot_update = {
            u'asset': None,
            u'checksum': None
        }
        if status is None:
            status = self.status
        self.status = {
            u'status': status,
            u'downloadfilesize': 0,
            u'downloadpercent': 0
        }
        self.__downloader = None
        self.__installer = None
        self.__canceled = False

        #send event to update ui
        self.updateStatusUpdate.send(params=self.get_status(), to=u'rpc')

    def get_full_status(self):
        """
        Return full status including config
        Module does not return its config due to size of stdout/stderr

        Return:
            dict: current status::
                {
                    status (string)
                    downloadfilesize (int)
                    downloadpercent (int)
                    laststdout (list)
                    laststderr (list)
                    lastupdate (int)
                    lastcheckraspiot (int)
                    lastcheckmodules (int)
                    version (string)
                }
        """
        config = self._get_config()
        status = self.status.copy()
        status[u'version'] = VERSION
        status[u'modules'] = self.__get_modules()
        status.update(config)

        return status

    def get_status(self):
        """
        Return light status

        Return:
            dict: current status::
                {
                    status (string)
                    download_filesize (int)
                    download_percent (int)
                }
        """
        return self.status

    def cancel(self):
        """
        Cancel current update
        """
        self.logger.debug(u'Cancel requested')
        self.__canceled = True
        if self.__raspiot_update[u'asset'] and self.__raspiot_update[u'checksum']:
            if self.__installer is not None:
                self.logger.debug(u'Cancel installer')
                self.__installer.cancel()
            elif self.__downloader is not None:
                self.logger.debug(u'Cancel downloader')
                self.__downloader.cancel()
            else:
                self.logger.debug(u'Nothing to cancel. Maybe too soon?')

    def set_automatic_update(self, raspiot_update, modules_update):
        """
        Set automatic update values

        Args:
            raspiot_update (bool): enable raspiot automatic update
            modules_update (bool): enable modules automatic update
        """
        if not isinstance(raspiot_update, bool):
            raise InvalidParameter('Parameter "raspiot_update" is invalid')
        if not isinstance(modules_update, bool):
            raise InvalidParameter('Parameter "modules_update" is invalid')

        config = self._get_config()
        config[u'raspiotupdate'] = raspiot_update
        config[u'modulesupdate'] = modules_update

        if self._save_config(config):
            return True

        return False

    def __update_raspiot(self):
        """
        Update raspiot task
        """
        try:
            if self.__raspiot_update[u'asset'] and self.__raspiot_update[u'checksum']:
                #new update available

                #get checksum key
                self.__downloader = Download(self.cleep_filesystem, self.__download_callback)
                checksum_content = self.__downloader.download_file(self.__raspiot_update[u'checksum'][u'url'])
                self.logger.debug('Checksum file content: %s' % checksum_content)
                checksum, _ = checksum_content.split()
                self.logger.debug(u'Checksum: %s' % checksum)

                #check cancel
                if self.__canceled:
                    self.logger.debug('Installation canceled')
                    self.__reset_update(self.STATUS_CANCELED)
                    return
            
                #download update
                deb_file = self.__downloader.download_file_advanced(self.__raspiot_update[u'asset'][u'url'], check_sha256=checksum)
                if deb_file is None:
                    if self.__canceled:
                        #download canceled
                        self.logger.info(u'Download canceled by user')
                        self.__reset_update(self.STATUS_CANCELED)
                    else:
                        #download failed, status updated in download callback so nothing else to do here
                        self.logger.error(u'Update download failed')
                        self.__reset_update()

                else:
                    #install deb file
                    self.__installer = Install(self.__install_callback, blocking=True)
                    if not self.__installer.install_deb(deb_file):
                        if self.__canceled:
                            #installation canceled
                            self.logger.info(u'Installation canceled by user')
                            self.__reset_update(self.STATUS_CANCELED)
                        else:
                            #installation failed, status updated in install callback so nothing else to do here
                            self.logger.error(u'Update installation failed')
                            self.__reset_update()

                    else:
                        #installation succeed
                        self._config[u'lastupdate'] = int(time.time())
                        self._save_config(self._config)
                        self.logger.info(u'Update processed succesfully')

                        #reset update process
                        self.__reset_update(self.STATUS_COMPLETED)
    
                        #send event to request restart
                        self.systemSystemNeedrestart.send(params={u'force':True}, to=u'system')
    
        except:
            #exception occured
            self.logger.exception('Exception occured during raspiot update:')
            #prevent from infinite update attempts
            self.__reset_update(self.STATUS_ERROR)

    def __download_latest_modules_json(self):
        """
        Download latest version of modules.json file and copy it to expected place

        Return:
            string: content of modules.json as string or None if error occured
        """
        download = Download(self.cleep_filesystem)
        raw = download.download_file(self.RASPIOT_MODULES_JSON)
        
        return raw

    def __is_new_module_version_available(self, module, old_version, new_version):
        """
        Compare specified version and return True if new version is greater than old one

        Args:
            module (string): module name
            old_version (string): old version (or current module version)
            new_version (string): new version (or version found in downloaded modules.json)

        Return:
            bool: True if new version available
        """
        #check versions
        try:
            old_vers = tuple(map(int, (old_version.split(u'.'))))
            if len(old_vers)!=3:
                raise Exception('Invalid version format for "%s"' % old_version)
        except:
            self.logger.exception(u'Invalid version format, only 3 digits format allowed:')
            return False
        try:
            new_vers = tuple(map(int, (new_version.split(u'.'))))
            if len(new_vers)!=3:
                raise Exception('Invalid version format for "%s"' % new_version)
        except:
            self.logger.exception(u'Invalid version format, only 3 digits format allowed:')
            return False

        #compare version
        if old_vers<new_vers:
            return True

        return False

    def __module_install_callback(self, status, module):
        """
        Module installation

        Args:
            module (string): module name
            status (int): install status
        """
        #update status
        self.logger.debug('Module install callback: %s' % status)
        if status[u'status']==Install.STATUS_PROCESSING:
            status = self.STATUS_INSTALLING
        elif status[u'status']==Install.STATUS_ERROR:
            status = self.STATUS_INSTALLING_ERROR
        elif status[u'status']==Install.STATUS_DONE:
            status = self.STATUS_INSTALLING_DONE

        #send event to update ui
        params = {
            u'module': module,
            u'status': status
        }
        self.updateStatusUpdate.send(params=params, to=u'rpc')

    def check_modules_updates(self):
        """
        Check for modules updates. Update updatable flag of modules that have update available
        Please use get_full_status to get updated modules list

        Return:
            dict: dict of modules with updatable flag updated
        """
        #update last check for raspiot
        self._config[u'lastcheckmodules'] = int(time.time())
        self._save_config(self._config)

        #get modules list from inventory
        modules = self.__get_modules()

        #download latest modules.json file
        raw = self.__download_latest_modules_json()
        remote_modules_json = json.loads(raw)

        #check downloaded file validity
        if u'list' not in remote_modules_json or u'update' not in remote_modules_json:
            #invalid modules.json
            self.logger.error(u'Invalid modules.json file downloaded, unable to update modules')
            raise CommandError(u'Invalid modules.json file downloaded, unable to update modules')

        #load local modules.json file
        local_modules_json = None
        if os.path.exists(MODULES_JSON):
            #local file exists, load its content
            local_modules_json = self.cleep_filesystem.read_json(MODULES_JSON)

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
                if self.__is_new_module_version_available(module, current_version, new_version):
                    #new version available for current module
                    self.logger.info('New version available for module "%s" (%s->%s)' % (module, current_version, new_version))
                    modules[module][u'updatable'] = new_version
                    update_available = True

                else:
                    self.logger.debug('No new version available for module "%s" (%s->%s)' % (module, current_version, new_version))

        return update_available

    def update_module(self, module):
        """
        Update specified module installing new version after uninstall succeed.

        Note:
            Install is launched automatically after module is uninstalled (see in event_received)

        Return:
            bool: True if no error occured
        """
        #check parameters
        if module is None or len(module)==0:
            raise MissingParameter('Parameter module is missing')
        if module in self.__updating_modules:
            raise InvalidParameter('Module %s is already updating' % module)

        #launch module uninstall first
        #ui should handle rpc events to follow uninstallation progress
        resp = self.send_command(u'uninstall_module', u'system', {u'module': module, u'update_process': True})
        self.logger.debug(u'Module "%s" uninstall response: %s' % (module, resp))
        if resp[u'error']:
            raise Exception(resp[u'message'])

        #add module to updating list
        self.__updating_modules.append(module)

        return True

    def check_raspiot_updates(self):
        """
        Check for available raspiot updates

        Return:
            bool: True if updates available
        """
        #update last check for raspiot
        self._config[u'lastcheckraspiot'] = int(time.time())
        self._save_config(self._config)
    
        update_available = False
        try:
            github = Github()
            releases = github.get_releases(self.RASPIOT_GITHUB_OWNER, self.RASPIOT_GITHUB_REPO)
            if len(releases)==1:
                #get latest version available
                version = github.get_release_version(releases[0])
                if version!=VERSION:
                    #new version available, trigger update
                    assets = github.get_release_assets_infos(releases[0])

                    #search for deb file
                    for asset in assets:
                        if asset[u'name'].find(u'.deb')!=-1:
                            self.logger.info(u'Found deb asset: %s' % asset)
                            self.__raspiot_update[u'asset'] = asset
                            break

                    #search for checksum file
                    if self.__raspiot_update[u'asset'] is not None:
                        deb_name = os.path.splitext(self.__raspiot_update[u'asset'][u'name'])[0]
                        checksum_name = u'%s.%s' % (deb_name, u'sha256')
                        self.logger.debug(u'Checksum filename to search: %s' % checksum_name)
                        for asset in assets:
                            if asset[u'name']==checksum_name:
                                self.logger.info(u'Found checksum asset: %s' % asset)
                                self.__raspiot_update[u'checksum'] = asset
                                break

                    if self.__raspiot_update[u'asset'] and self.__raspiot_update[u'checksum']:
                        self.logger.debug(u'Update and checksum found, can trigger update')
                        update_available = True

            else:
                #no release found
                self.logger.warning(u'No release found during check')

        except:
            self.logger.exception(u'Error occured during updates checking:')

        return update_available

    def event_received(self, event):
        """
        Event received
        """
        #handle time event to trigger updates check
        if event[u'event']==u'system.time.now' and event[u'params'][u'hour']==12 and event[u'params'][u'minute']==0:
            #check updates at noon

            #raspiot updates
            config = self._get_config()
            if config[u'raspiotupdate']:
                self.check_raspiot_updates()

            #modules updates
            if config[u'modulesupdate']:
                self.check_modules_updates()

        #handle module uninstall event during update
        elif event[u'event']==u'system.module.uninstall' and event[u'params'][u'module'] in self.__updating_modules:
            self.logger.debug(u'Module "%s" update detected (uninstall part)' % event[u'params'][u'module'])
            #check module uninstall status
            if event[u'params'][u'status']==Install.STATUS_DONE:
                #module uninstalled, continue installing it
                resp = self.send_command(u'install_module', u'system', {u'module': event[u'params'][u'module'], u'update_process': True})
                self.logger.info(u'Module "%s" update: uninstallation terminated, installing new version' % (event[u'params'][u'module']))

            elif event[u'params'][u'status'] in (Install.STATUS_ERROR, Install.STATUS_CANCELED):
                #error occured during module uninstall, remove it from updating list
                self.logger.error(u'Module "%s" update: error occured during uninstall.' % event[u'params'][u'module'])
                self.__updating_modules.remove(event[u'params'][u'module'])

            else:
                self.logger.debug('Module "%s" uninstall not terminated (status=%s)' % (event[u'params'][u'module'], event[u'params'][u'status']))

        #handle module install event during update
        elif event[u'event']==u'system.module.install' and event[u'params'][u'module'] in self.__updating_modules:
            self.logger.debug(u'Module "%s" update detected (install part)' % event[u'params'][u'module'])
            #check module install status
            if event[u'params'][u'status']==Install.STATUS_DONE:
                #module installed, end of update, remove it from updating list
                self.logger.info(u'Module "%s" update: update terminated successfully' % (event[u'params'][u'module']))
                self.__updating_modules.remove(event[u'params'][u'module'])

            elif event[u'params'][u'status'] in (Install.STATUS_ERROR, Install.STATUS_CANCELED):
                #error occured during module install, remove it from updating list
                self.logger.error(u'Module "%s" update: error occured during installation.' % event[u'params'][u'module'])
                self.__updating_modules.remove(event[u'params'][u'module'])

            else:
                self.logger.debug('Module "%s" uninstall not terminated (status=%s)' % (event[u'params'][u'module'], event[u'params'][u'status']))

