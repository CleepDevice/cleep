#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from raspiot.utils import InvalidParameter, MissingParameter, NoResponse, InvalidModule, CommandError, NoCityFound
from raspiot.raspiot import RaspIotModule
import raspiot
from datetime import datetime
import time
from raspiot.libs.internals.task import Task
from astral import Astral, GoogleGeocoder, AstralError
import psutil
import time
import io
import uuid
import socket
import iso3166
from zipfile import ZipFile, ZIP_DEFLATED
from tempfile import NamedTemporaryFile
from raspiot.libs.internals.console import Console, EndlessConsole
from raspiot.libs.configs.fstab import Fstab
from raspiot.libs.configs.hostname import Hostname
from raspiot.libs.configs.raspiotconf import RaspiotConf
from raspiot.libs.internals.install import Install
from raspiot.libs.configs.modulesjson import ModulesJson
import raspiot.libs.internals.tools as Tools
from raspiot.libs.internals.github import Github
from raspiot import __version__ as VERSION


__all__ = [u'System']


class System(RaspIotModule):
    """
    Helps controlling the system device (halt, reboot) and monitoring it
    """
    MODULE_AUTHOR = u'Cleep'
    MODULE_VERSION = u'1.0.0'
    MODULE_PRICE = 0
    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Helps controlling and monitoring the device'
    MODULE_LOCKED = True
    MODULE_TAGS = [u'system', u'troubleshoot', u'locale', u'hostname']
    MODULE_COUNTRY = u''
    MODULE_URLINFO = None
    MODULE_URLHELP = None
    MODULE_URLBUGS = None
    MODULE_URLSITE = None

    MODULE_CONFIG_FILE = u'system.conf'

    #TODO get log file path from bin/raspiot
    LOG_FILE = u'/var/log/raspiot.log'

    DEFAULT_CONFIG = {
        u'city': None,
        u'country': u'',
        u'alpha2': u'',
        u'monitoring': False,
        u'device_uuid': str(uuid.uuid4()),
        u'ssl': False,
        u'auth': False,
        u'rpcport': 80,
        u'eventsnotrendered': [],
        u'lastupdate': None,
        u'lastcheckraspiot': None,
        u'lastcheckmodules': None,
        u'lastraspiotinstallstdout': u'',
        u'lastraspiotinstallstderr': u'',
        u'raspiotupdateenabled': True,
        u'modulesupdateenabled': True,
        u'lastraspiotupdate': None,
        u'raspiotupdateavailable': False,
        u'modulesupdateavailable': False,
        u'crashreport': True
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
        self.time_task = None
        self.sunset = None
        self.sunrise = None
        self.__clock_uuid = None
        self.__monitor_cpu_uuid = None
        self.__monitor_memory_uuid = None
        self.__monitoring_cpu_task = None
        self.__monitoring_memory_task = None
        self.__monitoring_disks_task = None
        self.__process = None
        self.__need_restart = False
        self.__need_reboot = False
        self.hostname = Hostname(self.cleep_filesystem)
        self.modules_json = ModulesJson(self.cleep_filesystem)
        self.__updating_modules = []
        self.__modules = {}
        self.__raspiot_update = {
            u'asset': None,
            u'checksum': None
        }

        #events
        self.systemTimeNow = self._get_event(u'system.time.now')
        self.systemTimeSunrise = self._get_event(u'system.time.sunrise')
        self.systemTimeSunset = self._get_event(u'system.time.sunset')
        self.systemSystemHalt = self._get_event(u'system.system.halt')
        self.systemSystemReboot = self._get_event(u'system.system.reboot')
        self.systemSystemRestart = self._get_event(u'system.system.restart')
        self.systemMonitoringCpu = self._get_event(u'system.monitoring.cpu')
        self.systemMonitoringMemory = self._get_event(u'system.monitoring.memory')
        self.systemAlertMemory = self._get_event(u'system.alert.memory')
        self.systemAlertDisk = self._get_event(u'system.alert.disk')
        self.alertEmailSend = self._get_event(u'alert.email.send')
        self.systemModuleInstall = self._get_event(u'system.module.install')
        self.systemModuleUninstall = self._get_event(u'system.module.uninstall')
        self.systemModuleUpdate = self._get_event(u'system.module.update')

    def _configure(self):
        """
        Configure module
        """
        #configure crash report
        self.__configure_crash_report(self._get_config_field(u'crashreport'))

        #sunset and sunrise times are volatile and computed automatically at each time event

        #launch time task
        self.time_task = Task(60.0, self.__time_task, self.logger)
        self.time_task.start()

        #init first cpu percent for current process
        self.__process = psutil.Process(os.getpid())
        self.__process.cpu_percent()

        #add clock device if not already added
        if self._get_device_count()!=4:
            self.logger.debug(u'Add default devices')
            #add fake clock device
            clock = {
                u'type': u'clock',
                u'name': u'Clock'
            }
            self._add_device(clock)

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
            if devices[uuid][u'type']==u'clock':
                self.__clock_uuid = uuid
            elif devices[uuid][u'type']==u'monitorcpu':
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
        #stop time task
        if self.time_task:
            self.time_task.stop()

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

    def __get_location_infos(self, city, country):
        """
        Get location infos

        Params:
            city (string): city name
            country (string): city country

        Returns:
            astral.Location: astral location (from geocoder function) (location.name=city, location.region=country)

        Exceptions:
            Exception: if error occured, new exception is raise in generic one with appropriate message
        """
        try:
            a = Astral(GoogleGeocoder)

            #search location info
            pattern = city
            if country and len(country)>0:
                pattern = u'%s,%s' % (city, country)
            return a.geocoder[pattern]

        except AstralError as e:
            self.logger.debug('Exception during Astral request: %s' % str(e))
            if e.message and e.message.find(u'Unable to locate')>=0:
                raise NoCityFound()
            else:
                raise Exception(e.message)

    def __get_country_alpha2(self, country):
        """
        Return alpha2 country code useful for flag

        Args:
            country (string): country
        """
        if country.upper() in iso3166.countries_by_name.keys():
            c = iso3166.countries_by_name[country.upper()]
            return c.alpha2.lower()

        return None

    def __update_sun_times(self):
        """
        Update sun times

        Return:
            bool: True if data updated, False otherwise
        """
        #reset sunset and sunrise
        self.sunset = None
        self.sunrise = None

        #update sun times if possible
        config = self._get_config()
        if u'city' in config and config[u'city'] and u'country' in config:
            self.logger.debug('Update sun times')
            try:
                location = self.__get_location_infos(config[u'city'], config[u'country'])
                self.sunset = location.sunset()
                self.sunrise = location.sunrise()
                self.logger.debug('Found sunset=%s sunrise=%s' % (self.sunset, self.sunrise))

            except Exception as e:
                self.logger.warning('Unable to refresh suntimes (%s)' % str(e))
                return False

        return True

    def __save_sun_times(self, location):
        """
        Save sun times
    
        Args:
            location (astral.Location): data from astral/geocoder request
        """
        if isinstance(location, astral.Location):
            self.sunset = location.sun()[u'sunset']
            self.sunrise = location.sun()[u'sunrise']

    def __format_time(self, now=None):
        """
        Return current time object

        Returns:
            dict: time data
        """
        #current time
        if not now:
            now = int(time.time())
        dt = datetime.fromtimestamp(now)
        weekday = dt.weekday()
        if weekday==0:
            weekday_literal = u'monday'
        elif weekday==1:
            weekday_literal = u'tuesday'
        elif weekday==2:
            weekday_literal = u'wednesday'
        elif weekday==3:
            weekday_literal = u'thursday'
        elif weekday==4:
            weekday_literal = u'friday'
        elif weekday==5:
            weekday_literal = u'saturday'
        elif weekday==6:
            weekday_literal = u'sunday'

        #sunset and sunrise
        sunset = None
        if self.sunset:
            sunset = time.mktime(self.sunset.timetuple())
        sunrise = None
        if self.sunrise:
            sunrise = time.mktime(self.sunrise.timetuple())

        return {
            u'time': now,
            u'year': dt.year,
            u'month': dt.month,
            u'day': dt.day,
            u'hour': dt.hour,
            u'minute': dt.minute,
            u'weekday': weekday,
            u'weekday_literal': weekday_literal,
            u'sunset': sunset,
            u'sunrise': sunrise
        }

    def __time_task(self):
        """
        Time task: send time event every minutes. It also accomplishes somes other tasks like:
         - sunset/sunrise computations every day at midnight
         - send sunset/sunrise events
         - system monitoring data purge
        """
        now = int(time.time())
        now_formatted = self.__format_time()

        #send now event
        self.systemTimeNow.send(params=now_formatted, device_id=self.__clock_uuid)
        self.systemTimeNow.render([u'sound', u'display'], params=now_formatted)

        #update sun times
        refresh_sun_times = False
        if now_formatted[u'hour']==0 and now_formatted[u'minute']==0:
            #daily sun times refresh
            refresh_sun_times = True
        elif self.sunset is None or self.sunrise is None:
            #handle last update failure
            refresh_sun_times = True
        if refresh_sun_times:
            self.__update_sun_times()

        #send sunset event
        if self.sunset:
            if self.sunset.hour==now_formatted[u'hour'] and self.sunset.minute==now_formatted[u'minute']:
                #sunset time
                self.systemTimeSunset.send(device_id=self.__clock_uuid)
                self.systemTimeSunset.render([u'display', u'sound'], params=self.__clock_uuid)

        #send sunrise event
        if self.sunrise:
            if self.sunrise.hour==now_formatted[u'hour'] and self.sunrise.minute==now_formatted[u'minute']:
                #sunrise time
                self.systemTimeSunrise.send(device_id=self.__clock_uuid)
                self.systemTimeSunrise.render([u'display', u'sound'], self.__clock_uuid)

        #daily data cleanup
        if now_formatted[u'hour']==0 and now_formatted[u'minute']==0 and self.is_module_loaded(u'database'):
            self.__purge_cpu_data()
            self.__purge_memory_data()

    def get_module_config(self):
        """
        Return full module configuration

        Returns:
            dict: configuration
        """
        config = self._get_config()

        out = {}
        out[u'sun'] = self.get_sun()
        out[u'city'] = self.get_city()
        out[u'monitoring'] = self.get_monitoring()
        out[u'uptime'] = self.get_uptime()
        out[u'needrestart'] = self.__need_restart
        out[u'needreboot'] = self.__need_reboot
        out[u'hostname'] = self.get_hostname()
        out[u'eventsnotrendered'] = self.get_events_not_rendered()
        out[u'lastcheckraspiot'] = config[u'lastcheckraspiot']
        out[u'lastcheckmodules'] = config[u'lastcheckmodules']
        out[u'raspiotupdateenabled'] = config[u'raspiotupdateenabled']
        out[u'modulesupdateenabled'] = config[u'modulesupdateenabled']
        out[u'lastraspiotinstallstdout'] = config[u'lastraspiotinstallstdout']
        out[u'lastraspiotinstallstderr'] = config[u'lastraspiotinstallstderr']
        out[u'lastraspiotupdate'] = config[u'lastraspiotupdate']
        out[u'raspiotupdateavailable'] = config[u'raspiotupdateavailable']
        out[u'modulesupdateavailable'] = config[u'modulesupdateavailable']
        out[u'crashreport'] = config[u'crashreport']
        out[u'version'] = VERSION

        return out

    def get_module_devices(self):
        """
        Return clock and system as system devices

        Returns:
            dict: devices
        """
        devices = super(System, self).get_module_devices()
        
        for uuid in devices:
            if devices[uuid][u'type']==u'clock':
                data = self.get_time()
                devices[uuid].update(data)

            elif devices[uuid][u'type']==u'monitor':
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
            #a module requests a raspiot restart
            if u'force' in event[u'params'].keys() and event[u'params'][u'force']:
                #automatic restart requested
                self.restart()
            else:
                #manual restart
                self.__need_restart = True

        #handle reboot event
        elif event[u'event'].endswith('system.needreboot'):
            #a module requests a reboot
            if u'force' in event[u'params'].keys() and event[u'params'][u'force']:
                #automatic reboot requested
                self.reboot_system()
            else:
                #manual reboot
                self.__need_reboot = True

        #handle time event to trigger updates check
        if event[u'event']==u'system.time.now' and event[u'params'][u'hour']==12 and event[u'params'][u'minute']==0:
            #check updates at noon
            self.check_raspiot_updates()
            self.check_modules_updates()

            #and perform updates if allowed
            #TODO
            config = self._get_config()
            if config[u'raspiotupdateenabled']:
                pass
            if config[u'modulesupdateenabled']:
                pass

    def get_time(self):
        """
        Return current time

        Returns:
            dict: time data
        """
        return self.__format_time()

    def get_sun(self):
        """
        Return sunset and sunrise timestamps

        Returns:
            dict: sunset and sunrise timestamps
        """
        sunset = None
        if self.sunset:
            sunset = int(time.mktime(self.sunset.timetuple()))
        sunrise = None
        if self.sunrise:
            sunrise = int(time.mktime(self.sunrise.timetuple()))

        return {
            u'sunset': sunset,
            u'sunrise': sunrise
        }

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

    def get_city(self):
        """
        Return configured city

        Returns:
            dict: city and country infos
        """
        config = self._get_config()

        return {
            u'city': config[u'city'],
            u'country': config[u'country'],
            u'alpha2': config[u'alpha2']
        }

    def set_city(self, city, country):
        """
        Set city name

        Params:
            city (string): closest city name
            country (string): country name (optionnal)
        
        Returns:
            bool: True if city configured

        Raises:
            CommandError
        """
        if city is None or len(city)==0:
            raise MissingParameter(u'City parameter is missing')

        #search city and find if result found (try 3 times because geocoder returns exception sometimes :S)
        for i in range(3):
            try:
                #get location infos
                location = self.__get_location_infos(city, country)
                alpha2 = self.__get_country_alpha2(country)
                self.logger.debug(u'location: %s' % location)
                self.logger.debug(u'alpha2: %s' % alpha2)

                #save city and country
                config = {
                    u'city': location.name,
                    u'country': location.region,
                    u'alpha2': alpha2
                }
                if not self._update_config(config):
                    raise CommandError(u'Unable to save configuration')

                #update sun times
                self.__update_sun_times()

                #process terminated, quit now
                return True

            except NoCityFound:
                #no city found, it happens sometimes with geocoder ?!? so give it a new try
                pass

            except Exception as e:
                #unexpected exception
                self.crash_report.report_exception()
                raise e

        #if we reach this part of code, it means process was unable to find suitable city
        #so raise an exception
        raise Exception(u'Unable to find city. Please specify a more important city.')

    def reboot_system(self):
        """
        Reboot system
        """
        console = Console()

        #send event
        self.systemSystemReboot.send()

        #and reboot system
        console.command_delayed(u'reboot', 5.0)

    def halt_system(self):
        """
        Halt system
        """
        console = Console()

        #send event
        self.systemSystemHalt.send()

        #and reboot system
        console.command_delayed(u'halt', 5.0)

    def restart(self):
        """
        Restart raspiot
        """
        console = Console()

        #send event
        self.systemSystemRestart.send()

        #and restart raspiot
        console.command_delayed(u'/etc/raspiot/raspiot_helper.sh restart', 3.0)

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
        
        #send process status to ui
        self.systemModuleInstall.send(params=status)

        #save last stdout/stderr from install
        if status[u'status'] in (Install.STATUS_DONE, Install.STATUS_ERROR):
            self._update_config({
                u'lastraspiotinstallstdout': status[u'stdout'],
                u'lastraspiotinstallstderr': status[u'stderr']
            })

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

        #launch uninstallation
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
                #TODO check version with modules.json => need to create lib to handle modules.json first
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
        #TODO

    def update_raspiot(self):
        """
        Update raspiot
        """
        #TODO

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

    def __is_interface_wired(self, interface):
        """
        Return True if interface is wireless

        Params:
            interface (string): interface name
        """
        console = Console()
        res = console.command(u'/sbin/iwconfig %s 2>&1' % interface)
        if res['error'] or res[u'killed'] or len(res[u'stdout'])==0:
            return False

        if res[u'stdout'][0].lower().find(u'no wireless')==-1:
            return False

        return True

    def get_network_infos(self):
        """
        Return network infos

        Returns:
            dict: network infos::
                {
                    '<interface>': {
                        'interface':<interface name (string)>,
                        'ip': <ip address (string)>,
                        'mac': <interface mac address (string)>,
                        'wired': <interface type ('wired', 'wifi')> 
                    },
                    ...
                }
        """
        nets = psutil.net_if_addrs()
        infos = {}

        for interface in nets:
            #drop local interface
            if interface==u'lo':
                continue

            #read infos
            ip = None
            mac = None
            for snic in nets[interface]:
                if snic.family==2:
                    ip = snic.address
                elif snic.family==17:
                    mac = snic.address

            #save infos
            infos[interface] = {
                u'ip': ip,
                u'mac': mac,
                u'interface': interface,
                u'wired': self.__is_interface_wired(interface)
            }

        return infos

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
            fd = io.open(self.LOG_FILE, u'r', encoding=u'utf-8')
            lines = fd.read()
            fd.close()

        return lines

    def set_module_debug(self, module, debug):
        """
        Set module debug flag

        Args:
            module (string): module name
            debug (bool): debug flag
        """
        if module is None or len(module)==0:
            raise MissingParameter(u'Module parameter is missing')
        if debug is None:
            raise MissingParameter(u'Debug parameter is missing')

        #save log level in conf file
        conf = RaspiotConf(self.cleep_filesystem)
        if debug:
            conf.enable_module_debug(module)
        else:
            conf.disable_module_debug(module)

        #set debug on module
        resp = self.send_command(u'set_debug', module, {u'debug':debug})
        if not resp:
            self.logger.error(u'No response')
            raise CommandError(u'No response')
        elif resp[u'error']:
            self.logger.error(u'Unable to set debug on module %s: %s' % (module, resp[u'message']))
            raise CommandError(u'Update debug failed')

    def set_hostname(self, hostname):
        """
        Set raspi hostname

        Args:
            hostname (string): hostname

        Return:
            bool: True if hostname saved successfully, False otherwise
        """
        self.hostname.set_hostname(hostname)

    def get_hostname(self):
        """
        Return raspi hostname

        Returns:
            string: raspi hostname
        """
        return self.hostname.get_hostname()

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


