#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
from threading import Thread
from raspiot.raspiot import RaspIotModule
from pyremotedev import pyremotedev

__all__ = ['Developer']


class PyRemoteDevTask(Thread):
    """
    Pyremotedev task thread
    """

    def __init__(self, logger, profile):
        """
        Constructor

        Args:
            logger (Logger): logger instance
            profile (dict): pyremotedev profile dictionnary
        """
        Thread.__init__(self)

        #members
        self.profile = profile
        self.logger = logger
        self.running = True

    def stop(self):
        """
        Stop process
        """
        self.running = False

    def run(self):
        """
        Task process
        """
        slave = None
        try:
            #start pyremotedev
            slave = pyremotedev.PyRemoteDevSlave(self.profile, debug=True)
            slave.start()

            while self.running:
                time.sleep(0.25)

        except:
            self.logger.exception(u'Exception occured during pyremotedev execution:')

        finally:
            self.logger.info(u'Stopping pyremotedev task')
            slave.stop()

        slave.join()

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
    MODULE_URL = u'https://github.com/tangb/Raspiot/wiki/Developer'
    MODULE_TAGS = [u'developer', u'python', u'raspiot']
    MODULE_COUNTRY = None
    MODULE_LINK = u'https://github.com/tangb/Raspiot/wiki/Bulksms'

    PROFILE = {
        u'raspiot/': {
            u'dest': u'/usr/share/pyshared/raspiot/',
            u'link': u'/usr/lib/python2.7/dist-packages/raspiot/'
        },
        u'html/': {
            u'dest': u'/opt/raspiot/',
            u'link': None
        },
        u'bin/': {
            u'dest': u'usr/bin/',
            u'link': None
        }
    }

    def __init__(self, bus, debug_enabled, join_event):
        """
        Constructor

        Args:
            bus (MessageBus): MessageBus instance
            debug_enabled (bool): flag to set debug level to logger
        """
        #init
        RaspIotModule.__init__(self, bus, debug_enabled, join_event)

        #members
        self.__pyremotedev_task = None
        self.__developer_uuid = None

    def _configure(self):
        """
        Configure module
        """
        #add dummy device
        if self._get_device_count()==0:
            self.logger.debug(u'Add default devices')
            developer = {
                u'type': 'developer',
                u'name': 'Developer'
            }
            self._add_device(developer)

        #store device uuids for events
        devices = self.get_module_devices()
        for uuid in devices:
            if devices[uuid][u'type']==u'developer':
                self.__developer_uuid = uuid

        #start pyremotedev daemon
        self.__start_pyremotedev()

    def _stop(self):
        """
        Custom stop: stop pyremotedev thread
        """
        self.__stop_pyremotedev()

    def restart_raspiot(self):
        """
        Restart raspiot
        """
        self.send_command(u'restart', u'system')

    def __start_pyremotedev(self):
        """
        Start pyremotedev task
        """
        self.__pyremotedev_task = PyRemoteDevTask(self.logger, self.PROFILE)
        self.__pyremotedev_task.start()

    def __stop_pyremotedev(self):
        """
        Stop pyremotedev task
        """
        if self.__pyremotedev_task:
            self.__pyremotedev_task.stop()


