#!/usr/bin/env python
# -*- coding: utf-8 -*-

import raspiot.libs.internals.tools as tools
import os
import logging

class TestLib():
    """
    Instanciate TestLib to enable some features to be able to run tests on a library for Cleep
    """

    def __init__(self):
        """
        Constructor
        """
        tools.install_trace_logging_level()
