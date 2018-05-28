#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from raspiot.utils import InvalidParameter, MissingParameter, NoResponse, InvalidModule, CommandError, NoCityFound
from raspiot.raspiot import RaspIotModule
import raspiot
from datetime import datetime
import time
from raspiot.libs.task import Task
from astral import Astral, GoogleGeocoder, AstralError
import psutil
import time
from raspiot.libs.console import Console, EndlessConsole
from raspiot.libs.fstab import Fstab
from raspiot.libs.hostname import Hostname
from raspiot.libs.raspiotconf import RaspiotConf
from raspiot.libs.download import Download
import io
import uuid
import socket
import iso3166
import threading
import tempfile
from zipfile import ZipFile
import inspect


__all__ = [u'System']

MODULES_JSON = u'/etc/raspiot/modules.json'
PATH_FRONTEND = u'/opt/raspiot/html'
PATH_INSTALL = u'/etc/raspiot/install/'
FRONTEND_DIR = u'frontend/'
BACKEND_DIR = u'backend/'

class UninstallModule(threading.Thread):
    """
    Uninstall module in background task
    """
    STATUS_IDLE = 0
    STATUS_UNINSTALLING = 1
    STATUS_UNINSTALLED = 2
    STATUS_CANCELED = 3
    STATUS_ERROR_INTERNAL = 4
    STATUS_ERROR_PREUNINST = 5
    STATUS_ERROR_REMOVE = 6
    STATUS_ERROR_POSTUNINST = 7

    def __init__(self, module, module_infos, cleep_filesystem):
        """
        Constructor

        Args:
            module (string): module name to install
            module_infos (dict): all module infos from modules.json file
            cleep_filesystem (CleepFilesystem): CleepFilesystem singleton
        """
        threading.Thread.__init__(self)
        threading.Thread.daemon = True

        #logger   
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)

        #members
        self.status = self.STATUS_IDLE
        self.raspiot_path = os.path.dirname(inspect.getfile(RaspIotModule))
        self.running = True
        self.module = module
        self.module_infos = module_infos
        self.infos = module_infos
        self.cleep_filesystem = cleep_filesystem
        self.__script_running = True
        self.__script_return_code = 0
        self.__pre_script_execution = False
        self.__pre_script_outputs = {u'stdout': [], u'stderr':[]}
        self.__post_script_outputs = {u'stdout': [], u'stderr':[]}

    def get_status(self):
        """
        Return current status

        Return:
            int: see STATUS_XXX for available codes
        """
        return self.status

    def __script_callback(self, stdout, stderr):
        """
        Get stdout/stderr from script execution

        Args:
            stdout (string): stdout line
            stderr (string): stderr line
        """
        if self.__pre_script_execution:
            if stdout:
                self.__pre_script_outputs[u'stdout'].append(stdout)
            if stderr:
                self.__pre_script_outputs['stderr'].append(stderr)

        elif self.__post_script_execution:
            if stdout:
                self.__post_script_outputs[u'stdout'].append(stdout)
            if stderr:
                self.__post_script_outputs[u'stderr'].append(stderr)

    def __script_terminated_callback(self, return_code, killed):
        """
        Get infos when script is terminated

        Note:
            see http://www.tldp.org/LDP/abs/html/exitcodes.html for return codes

        Args:
            return_code (int): script return code
            killed (bool): True if script killed, False otherwise
        """
        if killed:
            self.__script_return_code = 130
        else:
            self.__script_return_code = return_code

    def __execute_script(self, script):
        """
        Execute specified script

        Args:
            script (string): script path

        Return
        """
        #init
        self.logger.debug(u'Executing %s script' % path)
        console = EndlessConsole(path, self.__script_callback, self.__script_terminated_callback)
        out = False

        #launch script execution
        console.start()

        #monitor end of script execution
        while self.__script_running:
            #pause
            time.sleep(0.25)

        #check script result
        if self.__script_return_code==0:
            out = True

        return out

    def start(self):
        """
        Run install
        """
        #init
        self.logger.info(u'Start module "%s" uninstallation' % self.module)
        self.status = self.STATUS_UNINSTALLING
        error = False
        module_log = None
        preuninst_sh = None
        postuninst_sh = None

        try:
            #pre uninstallation script
            try:
                preuninst_sh = os.path.join(os.path.join(PATH_INSTALL, u'%s_preuninst.sh' % self.module))
                if os.path.exists(preuninst_sh):
                    self.__script_running = True
                    self.__execute_script(preuninst_sh)

            except Exception as e:
                self.logger.exception(u'Exception occured during preuninst.sh script execution of module "%s"' % self.module)
                self.status = self.STATUS_ERROR_PREUNINST
                raise Exception()

            #remove all installed files
            try:
                module_log = os.path.join(PATH_INSTALL, u'%s.log' % self.module)
                self.logger.debug(u'Open install log file "%s"' % module_log)
                install_log = self.cleep_filesystem.open(module_log, u'r')
                lines = install_log.readlines()
                self.cleep_filesystem.close(install_log)
                for line in lines:
                    if not self.cleep_filesystem.rm(line.strip()):
                        self.logger.warning(u'File "%s" was not removed during "%s" module uninstallation' % (line, self.module))

            except:
                self.logger.exception(u'Exception occured during "%s" files module uninstallation' % self.module)
                self.status = self.STATUS_ERROR_REMOVE
                raise Exception()

            #post uninstallation script
            try:
                postuninst_sh = os.path.join(os.path.join(PATH_INSTALL, u'%s_postuninst.sh' % self.module))
                if os.path.exists(postuninst_sh):
                    self.__script_running = True
                    self.__execute_script(postuninst_sh)

            except Exception as e:
                self.logger.exception(u'Exception occured during postuninst.sh script execution of module "%s"' % self.module)
                self.status = self.STATUS_ERROR_POSTUNINST
                raise Exception()

        except:
            #local exception raised, invalid state :S
            error = True

        finally:
            #clean stuff
            try:
                if module_log:
                    self.cleep_filesystem.rm(module_log)
                if preuninst_sh:
                    self.cleep_filesystem.rm(preuninst_sh)
                if postuninst_sh:
                    self.cleep_filesystem.rm(postuninst_sh)
            except:
                self.logger.exception(u'Exception during install cleaning:')

            if error:
                #error occured
                self.logger.debug('Error occured during "%s" module uninstallation')
                if self.status==self.STATUS_UNINSTALLING:
                    self.status = self.STATUS_ERROR_INTERNAL
            else:
                #install terminated successfully
                self.status = self.STATUS_UNINSTALLED

        self.logger.info(u'Module "%s" uninstallation terminated (success: %s)' % (self.module, not error))


class InstallModule(threading.Thread):
    """
    Install module in background task
    """
    
    STATUS_IDLE = 0
    STATUS_INSTALLING = 1
    STATUS_INSTALLED = 2
    STATUS_CANCELED = 3
    STATUS_ERROR_INTERNAL = 4
    STATUS_ERROR_DOWNLOAD = 5
    STATUS_ERROR_EXTRACT = 6
    STATUS_ERROR_PREINST = 7
    STATUS_ERROR_COPY = 8
    STATUS_ERROR_POSTINST = 9

    def __init__(self, module, module_infos, cleep_filesystem):
        """
        Constructor

        Args:
            module (string): module name to install
            module_infos (dict): all module infos from modules.json file
            cleep_filesystem (CleepFilesystem): CleepFilesystem singleton
        """
        threading.Thread.__init__(self)
        threading.Thread.daemon = True

        #logger
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)

        #members
        self.status = self.STATUS_IDLE
        self.raspiot_path = os.path.dirname(inspect.getfile(RaspIotModule))
        self.running = True
        self.module = module
        self.module_infos = module_infos
        self.infos = module_infos
        self.cleep_filesystem = cleep_filesystem
        self.__script_running = True
        self.__script_return_code = 0
        self.__pre_script_execution = False
        self.__pre_script_outputs = {u'stdout': [], u'stderr':[]}
        self.__post_script_outputs = {u'stdout': [], u'stderr':[]}

        #make sure install log path exists
        if not os.path.exists(PATH_INSTALL):
            self.cleep_filesystem.mkdir(PATH_INSTALL, True)

    def cancel(self):
        """
        Cancel installation
        """
        self.logger.info(u'Module "%s" installation canceled' % self.module)
        self.running = False

    def get_status(self):
        """
        Return current status

        Return:
            int: see STATUS_XXX for available codes
        """
        return self.status

    def __script_callback(self, stdout, stderr):
        """
        Get stdout/stderr from script execution

        Args:
            stdout (string): stdout line
            stderr (string): stderr line
        """
        if self.__pre_script_execution:
            if stdout:
                self.__pre_script_outputs[u'stdout'].append(stdout)
            if stderr:
                self.__pre_script_outputs['stderr'].append(stderr)

        elif self.__post_script_execution:
            if stdout:
                self.__post_script_outputs[u'stdout'].append(stdout)
            if stderr:
                self.__post_script_outputs[u'stderr'].append(stderr)

    def __script_terminated_callback(self, return_code, killed):
        """
        Get infos when script is terminated

        Note:
            see http://www.tldp.org/LDP/abs/html/exitcodes.html for return codes

        Args:
            return_code (int): script return code
            killed (bool): True if script killed, False otherwise
        """
        if killed:
            self.__script_return_code = 130
        else:
            self.__script_return_code = return_code

    def __execute_script(self, script):
        """
        Execute specified script

        Args:
            script (string): script path

        Return
        """
        #init
        self.logger.debug(u'Executing %s script' % path)
        console = EndlessConsole(path, self.__script_callback, self.__script_terminated_callback)
        out = False

        #launch script execution
        console.start()

        #monitor end of script execution
        while self.__script_running:
            #handle installation canceling
            if not self.running:
                #kill process
                console.kill()
                #set output value and stop statement
                out = False
                break
            
            #pause
            time.sleep(0.25)

        #check script result
        if self.__script_return_code==0:
            out = True

        return out

    def start(self):
        """
        Run install
        """
        #init
        self.logger.info(u'Start module "%s" installation' % self.module)
        self.status = self.STATUS_INSTALLING
        error = False
        install_log = None
        extract_path = None
        archive_path = None

        try:
            #open file for writing installed files
            path = os.path.join(PATH_INSTALL, u'%s.log' % self.module)
            self.logger.debug(u'Create install log file "%s"' % path)
            try:
                install_log = self.cleep_filesystem.open(path, u'w')
            except:
                self.logger.exception(u'Exception occured during install log init "%s":' % path)
                self.status = self.STATUS_ERROR_INTERNAL
                raise Exception()

            #canceled ?
            if not self.running:
                raise Exception()

            #download module package
            self.logger.debug(u'Download file "%s"' % self.infos[u'download'])
            try:
                download = Download(self.cleep_filesystem)
                archive_path = download.download_file_advanced(self.infos[u'download'], check_sha256=self.infos[u'sha256'])
                if archive_path is None:
                    download_status = download.get_status()
                    if download_status==download.STATUS_ERROR:
                        self.error = u'Error during "%s" download: internal error' % self.infos[u'download']
                    if download_status==download.STATUS_ERROR_INVALIDSIZE:
                        self.error = u'Error during "%s" download: invalid filesize' % self.infos[u'download']
                    elif download_status==download.STATUS_ERROR_BADCHECKSUM:
                        self.error = u'Error during "%s" download: invalid checksum' % self.infos[u'download']
                    else:
                        self.error = u'Error during "%s" download: unknown error' % self.infos[u'download']
    
                    self.logger.error(error)
                    self.status = self.STATUS_ERROR_DOWNLOAD
                    raise Exception()

            except:
                self.logger.exception(u'Exception occured during module "%s" package download "%s"' % (self.module, self.infos[u'download']))
                self.status = self.STATUS_ERROR_DOWNLOAD
                raise Exception()

            #canceled ?
            if not self.running:
                raise Exception()

            #extract archive
            self.logger.debug('Extracting archive "%s"' % archive_path)
            try:
                zipfile = ZipFile(archive_path, u'r')
                extract_path = tempfile.mkdtemp()
                zipfile.extractall(extract_path)
                zipfile.close()

            except:
                self.logger.exception(u'Error decompressing module "%s" package "%s" in "%s":' % (self.module, archive_path, extract_path))
                self.status = self.STATUS_ERROR_EXTRACT
                raise Exception()

            #canceled ?
            if not self.running:
                raise Exception()

            #copy uninstall scripts to install path
            src_path = os.path.join(extract_path, u'preuninst.sh')
            dst_path = os.path.join(PATH_INSTALL, u'%s_preuninst.sh' % self.module)
            if os.path.exists(src_path):
                self.cleep_filesystem.copy(src_path, dst_path)
            src_path = os.path.join(extract_path, u'postuninst.sh')
            dst_path = os.path.join(PATH_INSTALL, u'%s_postuninst.sh' % self.module)
            if os.path.exists(src_path):
                self.cleep_filesystem.copy(src_path, dst_path)

            #pre installation script
            try:
                path = os.path.join(extract_path, u'preinst.sh')
                if os.path.exists(path):
                    self.__script_running = True
                    self.__execute_script(path)

            except Exception as e:
                self.logger.exception(u'Exception occured during preinst.sh script execution of module "%s"' % self.module)
                self.status = self.STATUS_ERROR_PREINST
                raise Exception()

            #canceled ?
            if not self.running:
                raise Exception()

            #copy module files
            try:
                #list archive files
                archive_files = []
                for directory, _, files in os.walk(extract_path):
                    for filename in files:
                        full_path = os.path.join(directory, filename)
                        rel_path = full_path.replace(extract_path, u'')
                        if rel_path[0]==u'/':
                            rel_path = rel_path[1:]
                        archive_files.append(rel_path)
                self.logger.debug(u'archive_files: %s' % archive_files)

                #canceled ?
                if not self.running:
                    raise Exception()
    
                #process them according to their directory
                for f in archive_files:
                    if f.startswith(u'back/'):
                        #copy python files
                        src_path = os.path.join(extract_path, f)
                        dst_path = os.path.join(self.raspiot_path, f).replace(u'back/', u'')
                        self.logger.debug('src=%s dst=%s' % (src_path, dst_path))
                        self.cleep_filesystem.mkdir(os.path.dirname(dst_path))
                        if not self.cleep_filesystem.copy(src_path, dst_path):
                            raise Exception()

                        #keep track of copied file for uninstall
                        install_log.write(u'%s\n' % dst_path)
                        install_log.flush()

                    elif f.startswith(FRONTEND_DIR):
                        #copy ui files
                        src_path = os.path.join(extract_path, f)
                        dst_path = os.path.join(PATH_FRONTEND, f).replace(FRONTEND_DIR, u'')
                        self.logger.debug('src=%s dst=%s' % (src_path, dst_path))
                        self.cleep_filesystem.mkdir(os.path.dirname(dst_path))
                        if not self.cleep_filesystem.copy(src_path, dst_path):
                            raise Exception()

                        #keep track of copied file for uninstall
                        install_log.write(u'%s\n' % dst_path)
                        install_log.flush()

                    else:
                        #drop file
                        self.logger.debug(u'Drop archive file: %s' % f)
                
                    #canceled ?
                    if not self.running:
                        raise Exception(u'canceled')

            except Exception as e:
                if e.message!=u'canceled':
                    self.logger.exception(u'Exception occured during module "%s" files copy:' % self.module)
                    self.status = self.STATUS_ERROR_COPY
                raise Exception()

            #post installation script
            try:
                path = os.path.join(extract_path, u'postinst.sh')
                if os.path.exists(path):
                    self.__script_running = True
                    self.__execute_script(path)
            except:
                self.logger.exception(u'Exception occured during postinst.sh script execution of module "%s"' % self.module)
                self.status = self.STATUS_ERROR_POSTINST
                raise Exception()
                    
            #canceled ?
            if not self.running:
                raise Exception(u'canceled')

        except:
            #local exception raised, revert installation
            error = True

        finally:
            #clean stuff
            try:
                if install_log:
                    self.cleep_filesystem.close(install_log)
                if extract_path:
                    self.cleep_filesystem.rmdir(extract_path)
                if archive_path:
                    self.cleep_filesystem.rm(archive_path)
            except:
                self.logger.exception(u'Exception during install cleaning:')

            if self.running==False:
                #installation canceled
                self.status = self.STATUS_CANCELED

            elif error:
                #error occured, revert installation
                self.logger.debug('Error occured during install, revert installed files')
                if self.status==self.STATUS_INSTALLING:
                    self.status = self.STATUS_ERROR_INTERNAL
                
                #remove installed files
                try:
                    fd = self.cleep_filesystem.open(install_log, u'r')
                    lines = fd.readlines()
                    for line in lines:
                        self.cleep_filesystem.rm(line.strip())
                except:
                    self.logger.exception(u'Unable to revert "%s" module installation:' % self.module)

            else:
                #install terminated successfully
                self.status = self.STATUS_INSTALLED

        self.logger.info(u'Module "%s" installation terminated (success: %s)' % (self.module, not error))



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
        u'rpc_port': 80,
        u'eventsnotrendered': []
    }

    MONITORING_CPU_DELAY = 60.0 #1 minute
    MONITORING_MEMORY_DELAY = 300.0 #5 minutes
    MONITORING_DISKS_DELAY = 21600 #6 hours

    THRESHOLD_MEMORY = 80.0
    THRESHOLD_DISK_SYSTEM = 80.0
    THRESHOLD_DISK_EXTERNAL = 90.0

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): flag to set debug level to logger
        """
        RaspIotModule.__init__(self, bootstrap, debug_enabled)

        self.logger.setLevel(logging.DEBUG)

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

    def _configure(self):
        """
        Configure module
        """
        #sunset and sunrise times are volatile and computed automacically at each time event

        #launch time task
        self.time_task = Task(60.0, self.__time_task, self.logger)
        self.time_task.start()

        #init first cpu percent for current process
        self.__process = psutil.Process(os.getpid())
        self.__process.cpu_percent()

        #add clock device if not already added
        if self._get_device_count()==0:
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

    def _stop(self):
        """
        Stop module
        """
        #stop time task
        if self.time_task:
            self.time_task.stop()

        #stop monitoring task
        self.__stop_monitoring_threads()

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
        self.logger.debug('Update sun times')
        #reset sunset and sunrise
        self.sunset = None
        self.sunrise = None

        #update sun times if possible
        if self._config.has_key(u'city') and self._config[u'city'] and self._config.has_key(u'country'):
            try:
                location = self.__get_location_infos(self._config[u'city'], self._config[u'country'])
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
        config = {}
        config[u'sun'] = self.get_sun()
        config[u'city'] = self.get_city()
        config[u'monitoring'] = self.get_monitoring()
        config[u'uptime'] = self.get_uptime()
        config[u'needrestart'] = self.__need_restart
        config[u'needreboot'] = self.__need_reboot
        config[u'hostname'] = self.get_hostname()
        config[u'eventsnotrendered'] = self.get_events_not_rendered()

        return config

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
        if event[u'event'].endswith('system.needrestart'):
            #a module requests a raspiot restart
            if u'force' in event[u'params'].keys() and event[u'params'][u'force']:
                #automatic restart requested
                self.restart()
            else:
                #manual restart
                self.__need_restart = True

        elif event[u'event'].endswith('system.needreboot'):
            #a module requests a reboot
            if u'force' in event[u'params'].keys() and event[u'params'][u'force']:
                #automatic reboot requested
                self.reboot_system()
            else:
                #manual reboot
                self.__need_reboot = True

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

        config = self._get_config()
        config[u'monitoring'] = monitoring
        if self._save_config(config) is None:
            raise CommandError(u'Unable to save configuration')

    def get_monitoring(self):
        """
        Return monitoring configuration

        Returns:
            dict: monitoring configuration
        """
        return self._config[u'monitoring']

    def get_city(self):
        """
        Return configured city

        Returns:
            dict: city and country infos
        """
        return {
            u'city': self._config[u'city'],
            u'country': self._config[u'country'],
            u'alpha2': self._config[u'alpha2']
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

        #search city and find if result found (try 3 times beacause geocoder returns exception sometimes :S)
        for i in range(3):
            try:
                #get location infos
                location = self.__get_location_infos(city, country)
                alpha2 = self.__get_country_alpha2(country)
                self.logger.debug(u'location: %s' % location)
                self.logger.debug(u'alpha2: %s' % alpha2)

                #save city and country
                config = self._get_config()
                config[u'city'] = location.name
                config[u'country'] = location.region
                config[u'alpha2'] = alpha2
                if self._save_config(config) is None:
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
        self.logger.debug('Load modules.json file from "%s"' % MODULES_JSON)
        modules_json = self.cleep_filesystem.read_json(MODULES_JSON)

        if u'list' not in modules_json:
            self.logger.fatal(u'Invalid modules.json file')
            raise Exception('Invalid modules.json')

        if module not in modules_json[u'list']:
            self.logger.error(u'Module "%s" not found in modules list' % module)
            raise CommandError(u'Module "%s" not found in modules list' % module)

        module_infos = modules_json[u'list'][module]
        self.logger.debug('Module infos: %s' % module_infos)

        return module_infos

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

        #launch installation
        install = InstallModule(module, infos, self.cleep_filesystem)
        install.start()

        #wait for end of installation
        #TODO use event to free request, thread is already developed
        while install.get_status()==install.STATUS_INSTALLING:
            time.sleep(0.25)

        #check install status
        if install.get_status()==install.STATUS_INSTALLED:
            self.__need_restart = True
            #update raspiot.conf
            raspiot = RaspiotConf(self.cleep_filesystem)
            return raspiot.install_module(module)

        return False

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

        #get module infos
        infos = self.__get_module_infos(module)

        #launch uninstallation
        uninstall = UninstallModule(module, infos, self.cleep_filesystem)
        uninstall.start()

        #wait for end of installation
        while uninstall.get_status()==uninstall.STATUS_UNINSTALLING:
            time.sleep(0.25)

        #check uinstall status
        #TODO use event to free request, thread is already developed
        if uninstall.get_status()==uninstall.STATUS_UNINSTALLED:
            self.__need_restart = True
            #update raspiot.conf
            raspiot = RaspiotConf(self.cleep_filesystem)
            return raspiot.uninstall_module(module)

        return False

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
            #u'total_hr': self.__hr_bytes(system.total),
            u'available': system.available,
            u'available_hr': self.__hr_bytes(system.available),
            #u'used_percent': system.percent,
            u'raspiot': raspiot,
            #u'raspiot_hr': self.__hr_bytes(raspiot),
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
            u'uptime_hr': self.__hr_uptime(uptime)
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

    def __hr_bytes(self, n):
        """
        Human readable bytes value

        Note:
            http://code.activestate.com/recipes/578019

        Params: 
            n (int): bytes

        Returns:
            string: human readable bytes value
        """
        symbols = (u'K', u'M', u'G', u'T', u'P', u'E', u'Z', u'Y')
        prefix = {}

        for i, s in enumerate(symbols):
            prefix[s] = 1 << (i + 1) * 10

        for s in reversed(symbols):
            if n >= prefix[s]:
                value = float(n) / prefix[s]
                return u'%.1f%s' % (value, s)

        return u'%sB' % n

    def __hr_uptime(self, uptime):
        """
        Human readable uptime (in days/hours/minutes/seconds)

        Note:
            http://unix.stackexchange.com/a/27014

        Params:
            uptime (int): uptime value

        Returns:
            string: human readable string
        """
        #get values
        days = uptime / 60 / 60 / 24
        hours = uptime / 60 / 60 % 24
        minutes = uptime / 60 % 60

        return u'%dd %dh %dm' % (days, hours, minutes)

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
            return self.LOG_FILE
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

        config = self._get_config()
        key = '%s__%s' % (renderer, event)
        if key in config[u'eventsnotrendered'] and not disabled:
            #enable renderer event
            config[u'eventsnotrendered'].remove(key)
        else:
            #disable renderer event
            config[u'eventsnotrendered'].append(key)
        if self._save_config(config) is None:
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

