#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging

class Driver():
    """
    Base driver class
    """

    #driver types
    DRIVER_AUDIO = u'audio'

    def __init__(self, driver_type, driver_name, config):
        """
        Constructor

        Args:
            driver_type (string): driver type. Must be one of available DRIVER_XXX types
            driver_name (string): driver name.
            config (dict): driver configuration.
        """
        self.type = driver_type
        self.name = driver_name

        #check driver configuration
        self._check_configuration(config)

        #inject config values as driver members
        for key,value in config.items():
            setattr(self, key, value)

    def _check_configuration(self, config):
        """
        Check driver configuration

        Raises:
            NotImplementedError: when function is not implemented
        """
        raise NotImplementedError(u'Function "_check_configuration" must be implemented in "%s"' % self.__class__.__name__)

