from raspiot.libs.internals.crashreport import CrashReport
from raspiot.eventsFactory import EventsFactory
from raspiot.formattersFactory import FormattersFactory
from raspiot.libs.internals.cleepfilesystem import CleepFilesystem
from raspiot.utils import NoResponse
from raspiot import bus
from raspiot.events import event
import raspiot.libs.internals.tools as tools
from threading import Event
import os
import logging
import types

class Lib():
    """
    Create lib to be able to run tests on a Cleep library
    """

    def __init__(self):
        """
        Constructor
        """
        tools.install_trace_logging_level()

