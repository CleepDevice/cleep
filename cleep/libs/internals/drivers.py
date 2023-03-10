#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
import copy
from cleep.libs.drivers.driver import Driver
from cleep.exception import InvalidParameter, MissingParameter


class Drivers:
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

        # members
        # compute dict of driver types
        self.drivers = {}
        for member in dir(Driver):
            if member.startswith("DRIVER_"):
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
            raise MissingParameter('Parameter "driver" is missing')
        if driver.name is None or len(driver.name) == 0:
            raise InvalidParameter("Driver name is missing")
        if driver.type not in self.drivers:
            raise InvalidParameter(
                'Driver must be one of existing driver type (found "%s")' % driver.type
            )

        self.logger.info(
            '%s driver "%s" registered' % (driver.type.capitalize(), driver.name)
        )
        self.drivers[driver.type][driver.name] = driver

    def unregister(self, driver):
        """
        Unregister specified driver

        Args:
            driver (Driver): driver instance
        """
        if driver is None:
            raise InvalidParameter('Parameter "driver" is invalid')
        found_driver = self.get_driver(driver.type, driver.name)
        if not found_driver:
            raise InvalidParameter('Driver not found')

        self.logger.info(f'Unregister driver "{driver.name}"')
        del self.drivers[driver.type][driver.name]

    def get_all_drivers(self):
        """
        Return all drivers

        Returns:
            dict: map of drivers
        """
        return copy.copy(self.drivers)

    def get_drivers(self, driver_type):
        """
        Return drives for specified type

        Args:
            driver_type (string): driver type (see Driver.DRIVER_XXX values)

        Returns:
            dict: drivers configuration
        """
        if driver_type is None or len(driver_type) == 0:
            raise MissingParameter('Parameter "driver_type" is missing')
        if driver_type not in self.drivers:
            raise InvalidParameter(
                'Driver must be one of existing driver type (found "%s")' % driver_type
            )

        return copy.copy(self.drivers[driver_type])

    def get_driver(self, driver_type, driver_name):
        """
        Return specified driver instance

        Args:
            driver_type (string): driver type (see Driver.DRIVER_XXX values)
            driver_name (string): driver name

        Returns:
            Driver: driver instance or None if no driver found

        Raises:
            InvalidParameter: if one of function parameter is invalid
            MissingParameter: if one of function parameter is missing
        """
        if driver_type is None or len(driver_type) == 0:
            raise MissingParameter('Parameter "driver_type" is missing')
        if driver_type not in self.drivers:
            raise InvalidParameter(
                'Driver must be one of existing driver type (found "%s")' % driver_type
            )
        if driver_name is None or len(driver_name) == 0:
            raise MissingParameter('Parameter "driver_name" is missing')

        return (
            self.drivers[driver_type][driver_name]
            if driver_name in self.drivers[driver_type]
            else None
        )
