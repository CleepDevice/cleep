#!/usr/bin/env python
# -*- coding: utf-8 -*

from raspiot.libs.internals.crashreport import CrashReport
import logging

class DummyCrashReport(CrashReport):
    def __init__(self):
        self.enabled = True

    def is_enabled(self):
        return self.enabled

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def manual_report(self, message, extra=None):
        pass

    def report_exception(self, *args, **kwargs):
        pass

    def get_logging_handler(self, level=logging.ERROR):
        return None

