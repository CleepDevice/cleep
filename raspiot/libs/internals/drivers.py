#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
from raspiot.libs.drivers.driver import Driver
from raspiot.utils import InvalidParameter, MissingParameter

class Drivers():
    """
    Drivers handler
    """

    def __init__(self, debug_enabled):
        """
        Constructor

        Args:
            debug_enabled (bool): debug enabled
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        if debug_enabled:
            self.logger.setLevel(logging.DEBUG)

        #members
        self.drivers = {}
        for member in dir(Driver):
            if member.startswith(u'DRIVER_'):
                self.drivers[getattr(Driver, member)] = {}

    def register(self, driver):
        """
        Register specified driver

        Args:
            driver (Driver): Driver instance

        Raises:
            InvalidParameter: if a parameter is invalid
            MissingParameter: if a parameter is missing
        """
        if driver is None:
            raise MissingParameter(u'Parameter "driver" is missing')
        if driver.name is None or len(driver.name)==0:
            raise MissingParameter(u'Driver name is missing')
        if driver.type not in self.drivers:
            raise InvalidParameter(u'Driver must be one of existing driver type (found "%s")' % driver.type)

        self.logger.info(u'%s driver "%s" registered' % (driver.type.capitalize(), driver.name))
        self.drivers[driver.type][driver.name] = driver

    def get_drivers(self, driver_type):
        """
        Return drives for specified type

        Args:
            driver_type (string): driver type (see Driver.DRIVER_XXX values)

        Returns:
            dict: drivers configuration
        """
        if driver_type is None or len(driver_type)==0:
            raise MissingParameter(u'Parameter "driver_type" is missing')
        if driver_type not in self.drivers:
            raise InvalidParameter(u'Driver must be one of existing driver type (found "%s")' % driver.type)

        return self.drivers[driver_type]

