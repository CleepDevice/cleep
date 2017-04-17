#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from utils import InvalidParameter
from raspiot import RaspIotMod
from datetime import datetime
import time
from libs.task import Task
from astral import Astral, GoogleGeocoder, AstralError
import psutil
import time
from libs.console import Console
from libs.fstab import Fstab

__all__ = ['System']



class System(RaspIotMod):

    MODULE_CONFIG_FILE = 'system.conf'
    MODULE_DEPS = []

    DEFAULT_CONFIG = {
        'city': None,
        'monitoring': False
    }

    MONITORING_CPU_DELAY = 60.0 #1 minute
    MONITORING_MEMORY_DELAY = 300.0 #5 minutes
    MONITORING_DISKS_DELAY = 21600 #6 hours

    THRESHOLD_MEMORY = 80.0
    THRESHOLD_DISK_SYSTEM = 80.0
    THRESHOLD_DISK_EXTERNAL = 90.0

    def __init__(self, bus, debug_enabled):
        """
        Constructor
        @param bus: bus instance
        @param debug_enabled: debug status
        """
        RaspIotMod.__init__(self, bus, debug_enabled)

        #members
        self.time_task = None
        self.sunset = time.mktime(datetime.min.timetuple())
        self.sunrise = time.mktime(datetime.min.timetuple())
        self.__clock_uuid = None
        self.__monitor_cpu_uuid = None
        self.__monitor_memory_uuid = None
        self.__monitoring_cpu_task = None
        self.__monitoring_memory_task = None
        self.__monitoring_disks_task = None
        self.__process = None

    def _start(self):
        """
        Start module
        """
        #compute sun times
        self.__compute_sun()

        #launch time task
        self.time_task = Task(60.0, self.__send_time_event)
        self.time_task.start()

        #init first cpu percent for current process
        self.__process = psutil.Process(os.getpid())
        self.__process.cpu_percent()

        #add clock device if not already added
        if self._get_device_count()==0:
            self.logger.debug('Add default devices')
            #add fake clock device
            clock = {
                'type': 'clock',
                'name': 'Clock'
            }
            self._add_device(clock)

            #add fake monitor device (used to have a device on dashboard)
            monitor = {
                'type': 'monitor',
                'name': 'System monitor'
            }
            self._add_device(monitor)

            #add fake monitor cpu device (used to save cpu data into database and has no widget)
            monitor = {
                'type': 'monitorcpu',
                'name': 'Cpu monitor'
            }
            self._add_device(monitor)

            #add fake monitor memory device (used to save cpu data into database and has no widget)
            monitor = {
                'type': 'monitormemory',
                'name': 'Memory monitor'
            }
            self._add_device(monitor)

        #store device uuids for events
        devices = self.get_module_devices()
        for uuid in devices:
            if devices[uuid]['type']=='clock':
                self.__clock_uuid = uuid
            elif devices[uuid]['type']=='monitor':
                self.__monitor_uuid = uuid
            elif devices[uuid]['type']=='monitorcpu':
                self.__monitor_cpu_uuid = uuid
            elif devices[uuid]['type']=='monitormemory':
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

    def __search_city(self, city):
        """
        Search for specified city
        @return astral location (from geocoder function)
        """
        try:
            a = Astral(GoogleGeocoder)
            return a.geocoder[city]
        except AstralError as e:
            if e.message and e.message.find('Unable to locate')>=0:
                raise Exception('Unable to find city. Please specify a bigger city.')
            else:
                raise Exception(e.message)

    def __compute_sun(self, city=None):
        """
        Compute sunset/sunrise times
        """
        self.logger.debug('Compute sunset/sunrise')

        #force city from configurated one if city not specified
        if not city:
            if self._config.has_key('city') and self._config['city'] is not None:
                city = self._config['city']
            else:
                #no city available
                city = None
                
        if city:
            loc = self.__search_city(city)
            sun = loc.sun()
            self.sunset = sun['sunset']
            self.sunrise = sun['sunrise']
            self.logger.debug('Sunset:%d:%d sunrise:%d:%d' % (self.sunset.hour, self.sunset.minute, self.sunrise.hour, self.sunrise.minute))
            
        else:
            self.sunset = None
            self.sunrise = None
            self.logger.warning('No city configured, only current time will be returned')

    def __format_time(self, now=None):
        """
        Return current time object
        """
        #current time
        if not now:
            now = int(time.time())
        dt = datetime.fromtimestamp(now)
        weekday = dt.weekday()
        if weekday==0:
            weekday_literal = 'monday'
        elif weekday==1:
            weekday_literal = 'tuesday'
        elif weekday==2:
            weekday_literal = 'wednesday'
        elif weekday==3:
            weekday_literal = 'thursday'
        elif weekday==4:
            weekday_literal = 'friday'
        elif weekday==5:
            weekday_literal = 'saturday'
        elif weekday==6:
            weekday_literal = 'sunday'

        #sunset and sunrise
        sunset = None
        if self.sunset:
            sunset = time.mktime(self.sunset.timetuple())
        sunrise = None
        if self.sunrise:
            sunrise = time.mktime(self.sunrise.timetuple())

        return {
            'time': now,
            'year': dt.year,
            'month': dt.month,
            'day': dt.day,
            'hour': dt.hour,
            'minute': dt.minute,
            'weekday': weekday,
            'weekday_literal': weekday_literal,
            'sunset': sunset,
            'sunrise': sunrise
        }

    def __send_time_event(self):
        """
        Send time event every minute
        Send sunset/sunrise
        """
        now = int(time.time())
        now_formatted = self.__format_time()

        #push now event
        self.send_event('system.time.now', now_formatted, self.__clock_uuid)

        #handle sunset
        if self.sunset:
            if self.sunset.hour==now_formatted['hour'] and self.sunset.minute==now_formatted['minute']:
                #sunset time
                self.send_event('system.time.sunset', None, self.__clock_uuid)

        #handle sunrise
        if self.sunrise:
            if self.sunrise.hour==now_formatted['hour'] and self.sunrise.minute==now_formatted['minute']:
                #sunrise time
                self.send_event('system.time.sunrise', None, self.__clock_uuid)

        #compute some stuff at midnight
        if now_formatted['hour']==0 and now_formatted['minute']==0:
            #compute sunset/sunrise at midnight
            self.__compute_sun()
            #purge data
            if self.is_module_loaded('database'):
                self.__purge_cpu_data()
                self.__purge_memory_data()

    def get_module_config(self):
        """
        Return full module configuration
        """
        config = {}
        config['sun'] = self.get_sun()
        config['city'] = self.get_city()
        config['monitoring'] = self.get_monitoring()
        #append current monitoring values
        config['uptime'] = self.get_uptime()
        return config

    def get_module_devices(self):
        """
        Return clock as system device
        """
        devices = super(System, self).get_module_devices()
        
        for uuid in devices:
            if devices[uuid]['type']=='clock':
                data = self.get_time()
                devices[uuid].update(data)
            elif devices[uuid]['type']=='monitor':
                data = {}
                data['uptime'] = self.get_uptime()
                data['cpu'] = self.get_cpu_usage()
                data['memory'] = self.get_memory_usage()
                devices[uuid].update(data)

        return devices

    def get_time(self):
        """
        Return current time
        """
        return self.__format_time()

    def get_sun(self):
        """
        Return sunset and sunrise timestamps
        """
        sunset = None
        if self.sunset:
            sunset = int(time.mktime(self.sunset.timetuple()))
        sunrise = None
        if self.sunrise:
            sunrise = int(time.mktime(self.sunrise.timetuple()))
        return {
            'sunset': sunset,
            'sunrise': sunrise
        }

    def get_monitoring(self):
        """
        Return monitoring configuration
        """
        return self._config['monitoring']

    def get_city(self):
        """
        Return configured city
        """
        return self._config['city']

    def set_city(self, city):
        """
        Set city name
        @param city: closest city name
        """
        if city is None:
            raise InvalidParameter('City parameter is missing')

        #compute sunset/sunrise
        self.__compute_sun(city)
        
        #save city (exception raised before if error occured)
        config = self._get_config()
        config['city'] = city
        self._save_config(config)

        return self.get_sun()

    def reboot_system(self):
        """
        Reboot system
        @return None
        """
        console = Console()

        #send event
        self.send_event('system.action.reboot')

        #wait few seconds
        time.sleep(2.0)

        #and reboot system
        console.execute('reboot')

    def halt_system(self):
        """
        Halt system
        @return None
        """
        console = Console()

        #send event
        self.send_event('system.action.halt')

        #wait few seconds
        time.sleep(2.0)

        #and reboot system
        console.execute('halt')

    def get_memory_usage(self):
        """
        Return system memory usage
        @return memory usage :
            dict(
                'total': <total memory in bytes (int)>',
                'available':<available memory in bytes (int)>,
                'available_hr':<human readble available memory (string)>,
                'raspiot': <raspiot process memory in bytes (float)>
            )
        """
        system = psutil.virtual_memory()
        raspiot = self.__process.memory_info()[0]
        return {
            'total': system.total,
            #'total_hr': self.__hr_bytes(system.total),
            'available': system.available,
            'available_hr': self.__hr_bytes(system.available),
            #'used_percent': system.percent,
            'raspiot': raspiot,
            #'raspiot_hr': self.__hr_bytes(raspiot),
            #'others': system.total - system.available - raspiot
        }

    def get_cpu_usage(self):
        """
        Return system cpu usage
        @return cpu usage :
            dict(
                'system': <system cpu usage percentage (float)>,
                'raspiot': <raspiot cpu usage percentage (float>)>
            )
        """
        system = psutil.cpu_percent()
        if system>100.0:
            system = 100.0
        raspiot = self.__process.cpu_percent()
        if raspiot>100.0:
            raspiot = 100.0
        return {
            'system': system,
            'raspiot': raspiot
        }

    def get_uptime(self):
        """
        Return system uptime (in seconds)
        @return int
        """
        uptime = int(time.time() - psutil.boot_time())
        return {
            'uptime': uptime,
            'uptime_hr': self.__hr_uptime(uptime)
        }

    def __is_interface_wired(self, interface):
        """
        Return True if interface is wireless
        """
        console = Console()
        res = console.command('iwconfig %s 2>&1' % interface)
        if res['error'] or res['killed'] or len(res['output'])==0:
            return False

        if res['output'][0].lower().find('no wireless')==-1:
            return False

        return True

    def get_network_infos(self):
        """
        Return network infos
        @return network infos:
            dict(
                '<interface>': dict(
                    'interface':<interface name (string)>,
                    'ip': <ip address (string)>,
                    'mac': <interface mac address (string)>,
                    'wired': <interface type ('wired', 'wifi')> 
                ),
                ...
            )
        """
        nets = psutil.net_if_addrs()
        infos = {}

        for interface in nets:
            #drop local interface
            if interface=='lo':
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
                'ip': ip,
                'mac': mac,
                'interface': interface,
                'wired': self.__is_interface_wired(interface)
            }

        return infos

    def __start_monitoring_threads(self):
        """
        Start monitoring threads
        """
        self.__monitoring_cpu_task = Task(self.MONITORING_CPU_DELAY, self.__monitoring_cpu_thread)
        self.__monitoring_cpu_task.start()
        self.__monitoring_memory_task = Task(self.MONITORING_MEMORY_DELAY, self.__monitoring_memory_thread)
        self.__monitoring_memory_task.start()
        self.__monitoring_disks_task = Task(self.MONITORING_DISKS_DELAY, self.__monitoring_disks_thread)
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
        if config['monitoring']:
            self.send_event('system.monitoring.cpu', self.get_cpu_usage(), self.__monitor_cpu_uuid)

    def __monitoring_memory_thread(self):
        """
        Read memory usage
        Send alert if threshold reached
        """
        config = self._get_config()
        memory = self.get_memory_usage()

        #detect memory leak
        percent = float(memory['available'])/float(memory['total'])*100.0
        if percent>=self.THRESHOLD_MEMORY:
            self.send_event('system.alert.memory', {'percent':percent, 'threshold':self.THRESHOLD_MEMORY})

        #send event if monitoring activated
        if config['monitoring']:
            self.send_event('system.monitoring.memory', memory, self.__monitor_memory_uuid)

    def __monitoring_disks_thread(self):
        """
        Read disks usage
        Only used to send alert when threshold reached
        """
        disks = self.get_filesystem_infos()
        for disk in disks:
            if disk['mounted']:
                if disk['mountpoint']=='/' and disk['percent']>=self.THRESHOLD_DISK_SYSTEM:
                    self.send_event('system.alert.disk', {'percent':disk['percent'], 'threshold':self.THRESHOLD_DISK_SYSTEM, 'mountpoint':disk['mountpoint']})

                elif disk['mountpoint'] not in ('/', '/boot') and disk['percent']>=self.THRESHOLD_DISK_EXTERNAL:
                    self.send_event('system.alert.disk', {'percent':disk['percent'], 'threshold':self.THRESHOLD_DIST_EXTERNAL, 'mountpoint':disk['mountpoint']})

    def __hr_bytes(self, n):
        """
        Human readable bytes value
        @see http://code.activestate.com/recipes/578019
        """
        symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
        prefix = {}

        for i, s in enumerate(symbols):
            prefix[s] = 1 << (i + 1) * 10

        for s in reversed(symbols):
            if n >= prefix[s]:
                value = float(n) / prefix[s]
                return '%.1f%s' % (value, s)

        return "%sB" % n

    def __hr_uptime(self, uptime):
        """
        Human readable uptime (in days/hours/minutes/seconds)
        @see http://unix.stackexchange.com/a/27014
        @param uptime: uptime value (int)
        @return human readable string (string)
        """
        #get values
        days = uptime / 60 / 60 / 24
        hours = uptime / 60 / 60 % 24
        minutes = uptime / 60 % 60

        return '%dd %dh %dm' % (days, hours, minutes)

    def get_filesystem_infos(self):
        """
        Return filesystem infos (all values are in octets)
        @return list of device available with those informations:
            list(dict(
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
            ), ...)
        """
        #get mounted partitions and all devices
        fstab = Fstab()
        mounted_partitions = fstab.get_mountpoints()
        self.logger.debug('mounted_partitions=%s' % mounted_partitions)
        all_devices = fstab.get_all_devices()
        self.logger.debug('all_devices=%s' % all_devices)

        #build output
        fsinfos = []
        for device in all_devices:
            #check if partition is mounted
            mounted = {'mounted':False, 'mountpoint':'', 'mounttype':'-', 'options':'', 'uuid':None}
            system = False
            for partition in mounted_partitions:
                if mounted_partitions[partition]['device']==device:
                    mounted['mounted'] = True
                    mounted['mountpoint'] = mounted_partitions[partition]['mountpoint']
                    mounted['device'] = mounted_partitions[partition]['device']
                    mounted['uuid'] = mounted_partitions[partition]['uuid']
                    mounted['mounttype'] = mounted_partitions[partition]['mounttype']
                    mounted['options'] = mounted_partitions[partition]['options']
                    if mounted_partitions[partition]['mountpoint'] in ('/', '/boot'):
                        system = True

            #get mounted partition usage
            usage = {'total':0, 'used':0, 'free':0, 'percent':0.0}
            if mounted['mounted']:
                sdiskusage = psutil.disk_usage(mounted['mountpoint'])
                self.logger.debug('diskusage for %s: %s' % (device, sdiskusage));
                usage['total'] = sdiskusage.total
                usage['used'] = sdiskusage.used
                usage['free'] = sdiskusage.free
                usage['percent'] = sdiskusage.percent

            #fill infos
            fsinfos.append({
                'device': device,
                'uuid': mounted['uuid'],
                'system': system,
                'mountpoint': mounted['mountpoint'],
                'mounted': mounted['mounted'],
                'mounttype': mounted['mounttype'],
                'options': mounted['options'],
                'total': usage['total'],
                'used': usage['used'],
                'free': usage['free'],
                'percent': usage['percent']
            })

        self.logger.debug('Filesystem infos: %s' % fsinfos)
        return fsinfos

    def __purge_cpu_data(self):
        """
        Purge cpu data (keep 1 week)
        """
        params = {
            'uuid': self.__monitor_cpu_uuid,
            'timestamp_until': int(time.time()) - 604800
        }
        try:
            self.send_command('purge_data', 'database', params, 10.0)
        except NoResponse:
            self.logger.warning('Unable to purge CPU usage from database')

    def __purge_memory_data(self):
        """
        Purge memory data (keep 1 month)
        """
        params = {
            'uuid': self.__monitor_memory_uuid,
            'timestamp_until': int(time.time()) - 2592000
        }
        try:
            self.send_command('purge_data', 'database', params, 10.0)
        except NoResponse:
            self.logger.warning('Unable to purge memory usage from database')

