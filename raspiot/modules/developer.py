#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
from threading import Thread
from raspiot.raspiot import RaspIotModule
from raspiot.libs.task import Task
from raspiot.libs.console import Console

__all__ = ['Developer']


class Developer(RaspIotModule):
    """
    Developer module: this module is dedicated only for developers.
    It allows implements and configures pyremotedev in raspiot ()

    Note:
        https://github.com/tangb/pyremotedev
    """

    MODULE_CONFIG_FILE = u'developer.conf'
    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Help you to develop on Raspiot framework.'
    MODULE_LOCKED = False
    MODULE_TAGS = [u'developer', u'python', u'raspiot']
    MODULE_COUNTRY = None
    MODULE_LINK = u'https://github.com/tangb/Raspiot/wiki/Developer'

    RASPIOT_PROFILE = """[raspiot]
raspiot/ = /usr/share/pyshared/raspiot/$_$/usr/lib/python2.7/dist-packages/raspiot/
bin/ = /usr/bin/$_$
log_file_path = /var/log/raspiot.log
html/ = /opt/raspiot/html/$_$"""
    RASPIOT_PROFILE_FILE = u'/root/.local/share/pyremotedev/slave.conf'

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): flag to set debug level to logger
        """
        #init
        RaspIotModule.__init__(self, bootstrap, debug_enabled)

        #members
        self.__developer_uuid = None
        self.console = Console()
        self.pyremotedev_is_running = False
        self.status_task = None

        #events
        self.pyremotedevStartedEvent = self._get_event('developer.pyremotedev.started')
        self.pyremotedevStoppedEvent = self._get_event('developer.pyremotedev.stopped')

    def _configure(self):
        """
        Configure module
        """
        #add dummy device
        self.logger.debug('device_count=%d' % self._get_device_count())
        if self._get_device_count()==0:
            self.logger.debug(u'Add default devices')
            developer = {
                u'type': 'developer',
                u'name': 'Developer'
            }
            data = self._add_device(developer)

        #store device uuids for events
        devices = self.get_module_devices()
        self.logger.debug('devices: %s' % devices)
        for uuid in devices:
            if devices[uuid][u'type']==u'developer':
                self.__developer_uuid = uuid

        #write default pyremotedev profile
        if not os.path.exists(self.RASPIOT_PROFILE_FILE):
            try:
                fd = open(self.RASPIOT_PROFILE_FILE, 'w')
                fd.write(self.RASPIOT_PROFILE)
                fd.close()
            except:
                self.logger.exception(u'Unable to create raspiot profile for pyremotedev:')

        #start pyremotedev status task
        self.status_task = Task(15.0, self.status_pyremotedev, self.logger)
        self.status_task.start()

    def get_module_devices(self):
        """
        Return module devices
        """
        devices = super(Developer, self).get_module_devices()
        data = {
            u'running': self.pyremotedev_is_running
        }
        self.__developer_uuid = devices.keys()[0]
        devices[self.__developer_uuid].update(data)

        return devices

    def _stop(self):
        """
        Custom stop: stop pyremotedev thread
        """
        if self.status_task:
            self.status_task.stop()

    def restart_raspiot(self):
        """
        Restart raspiot
        """
        self.send_command(u'restart', u'system')

    def start_pyremotedev(self):
        """
        Start pyremotedev task
        """
        res = self.console.command(u'/usr/sbin/service pyremotedev start')
        if not res[u'error'] and not res[u'killed']:
            #no problem
            self.pyremotedev_is_running = True
            self.logger.info('Pyremotedev started')
            return True

        else:
            #unable to stop pyremotedev
            self.logger.error(u'Unable to start pyremotedev: %s' % u' '.join(res[u'stdout']).join(res[u'stderr']))
            self.pyremotedev_is_running = False
            return False

    def stop_pyremotedev(self):
        """
        Stop pyremotedev process
        """
        res = self.console.command(u'/usr/sbin/service pyremotedev stop')
        if not res[u'error'] and not res[u'killed']:
            #no problem
            self.pyremotedev_is_running = False
            self.logger.info('Pyremotedev stopped')
            return True

        else:
            #unable to stop pyremotedev
            self.logger.error(u'Unable to stop pyremotedev: %s' % u' '.join(res[u'stdout']).join(res[u'stderr']))
            self.pyremotedev_is_running = False
            return False

    def status_pyremotedev(self):
        """
        Get pyremotedev status
        """
        res = self.console.command(u'/usr/sbin/service pyremotedev status')
        if not res[u'error'] and not res[u'killed']:
            output = u''.join(res[u'stdout'])
            if output.find(u'pyremotedev is running')>=0:
                #pyremotedev is running
                if not self.pyremotedev_is_running:
                    #send is running event
                    self.pyremotedevStartedEvent.send(to=u'rpc', device_id=self.__developer_uuid)
                self.pyremotedev_is_running = True

            else:
                #pyremotedev is not running
                if self.pyremotedev_is_running:
                    #send is not running event
                    self.pyremotedevStoppedEvent.send(to=u'rpc', device_id=self.__developer_uuid)
                self.pyremotedev_is_running = False
              
        
