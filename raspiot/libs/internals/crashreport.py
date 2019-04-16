#!/usr/bin/env python
# -*- coding: utf-8 -*

import logging
import sys
from raven import Client
from raven.handlers.logging import SentryHandler
import platform
import traceback


class CrashReport():
    """
    Crash report class
    Use Sentry (Raven) to send crash reports.

    Usage:
        To report specific exception, simply use <CrashReport instance>.report_exception() function (without params)
        To report manually something uses <CrashReport instance>.manual_report() specifiying a message and extra infos
        Unhandled exceptions are reported automatically (if enabled!)
    """

    def __init__(self, sentry_dsn, product, product_version, libs_version={}, debug=False, forced=False):
        """
        Constructor

        Args:
            sentry_dsn (string): sentry DSN
            product (string): product name
            product_version (string): product version
            libs_version (dict): dict of libraries with their version
            debug (bool): enable debug on this library (default False)
            forced (bool): used by system to force crash report deactivation
        """
        #logger
        self.logger = logging.getLogger(self.__class__.__name__)
        if debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)

        #members
        self.libs_version = libs_version
        self.extra = libs_version
        self.product = product
        self.product_version = product_version
        self.extra['platform'] = platform.platform()
        self.extra['product'] = product
        self.extra['product_version'] = product_version
        self.__forced = forced
        self.__enabled = True
        self.report_exception = self.__binded_report_exception
        if self.__forced or sentry_dsn in (None, u''):
            self.disable()
        self.__handler = None

        #create and configure raven client
        self.client = Client(
            dsn = sentry_dsn,
            ignore_exceptions = [u'KeyboardInterrupt', u'zmq.error.ZMQError', u'AssertionError', u'ForcedException'],
            tags = self.extra
        )
        #sys.excepthook = self.__crash_report

    def __unbinded_report_exception(self, *argv, **kwargs):
        """
        Unbinded report exception when sentry is disabled
        """
        pass

    def __binded_report_exception(self, *args, **kwargs):
        """
        Binded report exception when sentry is enabled
        """
        self.client.captureException(args=args, kwargs=kwargs, extra=self.extra)

    def is_enabled(self):
        """
        Return True if crash report enabled

        Returns:
            bool: True is enabled
        """
        return self.__enabled

    def enable(self):
        """
        Enable crash report
        """
        #avoid enabling again if forced by system
        if self.__forced:
            self.logger.info(u'Unable to enable crash report because system disabled it for current execution')
            return

        self.logger.debug('Crash report is enabled')
        self.__enabled = True

        #bind report_exception
        self.report_exception = self.__binded_report_exception

    def disable(self):
        """
        Disable crash report
        """
        self.logger.debug('Crash report is disabled')
        self.__enabled = False

        #unbind report exception
        self.report_exception = self.__unbinded_report_exception

    def crash_report(self, exc_type, exc_value, exc_traceback):
        """
        Exception handler that report crashes
        """
        #message = u'\n'.join(traceback.format_tb(tb))
        #message += '\n%s %s' % (str(type), value)
        #self.logger.fatal(message)
        if self.__enabled:
            self.client.captureException((exc_type, exc_value, exc_traceback), extra=self.extra)

    def manual_report(self, message, extra=None):
        """
        Report manually a crash report dumping current stack trace to report thx to raven

        Args:
            message (string): message to attach to crash report
            extra (dict): extra metadata to post with the report (stack...)
        """
        if self.__enabled:
            self.client.capture(u'raven.events.Message', message=message, stack=True, extra=extra)

    def get_logging_handler(self, level=logging.ERROR):
        """
        Return sentry logging handler

        Args:
            level (int): logging level (see logging.XXX)

        Returns:
            SentryHandler: sentry logging handler
        """
        if self.__handler is None:
            self.__handler = SentryHandler(self.client)
            self.__handler.setLevel(logging.ERROR)

        return self.__handler


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s.%(funcName)s +%(lineno)s: %(levelname)-8s [%(process)d] %(message)s')

    #test crash report
    cr = CrashReport('Test', '0.0.0')
    cr.disable()
    #cr.enable()

    #test local catched exception
    try:
        raise Exception('My custom exception')
    except:
        cr.report_exception()
        pass

    #try main exception
    1/0

    print('Done')
