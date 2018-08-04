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
        To report manually something uses <CrashReport instance>.manual_report() specifiying a message
        Unhandled exceptions are reported automatically (if enabled!)
    """

    def __init__(self, product, product_version, libs_version={}, debug=False):
        #logger
        self.logger = logging.getLogger(self.__class__.__name__)
        if debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.WARN)

        #members
        self.extra = libs_version
        self.extra['platform'] = platform.platform()
        self.extra['product'] = product
        self.extra['product_version'] = product_version
        self.enabled = False
        self.__handler = None

        #create and configure raven client
        self.client = Client(
            dsn='https://8e703f88899c42c18b8466c44b612472:3dfcd33abfda47c99768d43ce668d258@sentry.io/213385',
            ignore_exceptions=[u'KeyboardInterrupt', u'zmq.error.ZMQError', u'AssertionError'],
            tags=self.extra
        )
        self.report_exception = self.__unbinded_report_exception
        sys.excepthook = self.__crash_report

    def __unbinded_report_exception(self):
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
        return self.enabled

    def enable(self):
        """
        Enable crash report
        """
        self.logger.debug('Crash report is enabled')
        self.enabled = True

        #bind report_exception
        #self.report_exception = self.client.captureException
        self.report_exception = self.__binded_report_exception

    def disable(self):
        """
        Disable crash report
        """
        self.logger.debug('Crash report is disabled')
        self.enabled = False

        #unbind report exception
        self.report_exception = self.__unbinded_report_exception

    def __crash_report(self, type, value, tb):
        """
        Exception handler that report crashes
        """
        message = u'\n'.join(traceback.format_tb(tb))
        message += '\n%s %s' % (str(type), value)
        #self.logger.fatal(message)
        if self.enabled:
            self.client.captureException((type, value, tb), extra=self.extra)

    def manual_report(self, message, extra=None):
        """
        Report manually a crash report dumping current stack trace to report thx to raven

        Args:
            message (string): message to attach to crash report
            extra (dict): extra metadata to post with the report (stack...)
        """
        if self.enabled:
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
