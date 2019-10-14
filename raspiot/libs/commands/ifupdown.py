#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import logging
import time
from raspiot.libs.internals.console import Console

class Ifupdown(Console):
    """
    Command /sbin/ifup /sbin/ifdown.
    It also uses /sbin/ip command
    """

    def __init__(self):
        """
        Constructor
        """
        Console.__init__(self)

        #members
        self.logger = logging.getLogger(self.__class__.__name__)
        self.ip = u'/sbin/ip'
        self.ifup = u'/sbin/ifup'
        self.ifdown = u'/sbin/ifdown'

    def stop_interface(self, interface):
        """
        Stop specified interface

        Args:
            interface (string): interface to restart

        Result:
            bool: True if command succeed (but maybe not connected!)
        """
        res = self.command(u'%s %s' % (self.ifdown, interface), timeout=60.0)
        if self.get_last_return_code()!=0:
            self.logger.error(u'Unable to ifdown interface %s: %s' % (interface, res))
            return False

        return True

    def start_interface(self, interface):
        """
        Start specified interface

        Args:
            interface (string): interface to restart

        Result:
            bool: True if command succeed (but maybe not connected!)
        """
        res = self.command(u'%s %s' % (self.ifup, interface), timeout=60.0)
        if self.get_last_return_code()!=0:
            self.logger.error(u'Unable to ifup interface %s: %s' % (interface, res))
            return False

        return True

    def restart_interface(self, interface):
        """
        Restart specified interface

        Args:
            interface (string): interface to restart

        Result:
            bool: True if command succeed (but maybe not connected!)
        """
        #stop interface
        if not self.stop_interface(interface):
            return False

        #pause
        time.sleep(0.5)

        #start interface
        if not self.start_interface(interface):
            return False

        return True
