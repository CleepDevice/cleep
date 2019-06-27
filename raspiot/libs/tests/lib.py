#!/usr/bin/env python
# -*- coding: utf-8 -*-

import raspiot.libs.internals.tools as tools
import os
import logging

class Lib():
    """
    Create lib to be able to run tests on a Cleep library
    """

    def __init__(self):
        """
        Constructor
        """
        tools.install_trace_logging_level()

