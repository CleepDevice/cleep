#!/usr/bin/env python
# -*- coding: utf-8 -*

import logging
import sys
import sentry_sdk as Sentry
from sentry_sdk.integrations.excepthook import ExcepthookIntegration
import platform
import traceback

class CrashReport():
    """
    Crash report class
    """

    def __init__(self, token, product, product_version, libs_version={}, debug=False, forced=False):
        """
        Constructor

        Args:
            token (string): crash report service token (like sentry dsn)
            product (string): product name
            product_version (string): product version
            libs_version (dict): important libraries versions
            debug (bool): debug flag
            forced (bool): used by system to force crash report deactivation
        """
        #logger
        self.logger = logging.getLogger(self.__class__.__name__)
        if debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.WARN)

        #members
        self.__forced = forced
        self.__extra = libs_version
        self.__enabled = False
        self.__token = token

        #disable crash report if necessary
        if self.__forced or not token:
            self.disable()

        #fill metadata collection
        self.__extra['platform'] = platform.platform()
        self.__extra['product'] = product
        self.__extra['product_version'] = product_version
        try:
            #append more metadata for raspberry
            import raspiot.libs.internals.tools as Tools
            infos = Tools.raspberry_pi_infos()
            self.__extra['raspberrypi_model'] = infos[u'model']
            self.__extra['raspberrypi_revision'] = infos['revision']
            self.__extra['raspberrypi_pcbrevision'] = infos['pcbrevision']
        except:
            self.logger.debug('Application is not running on a reaspberry pi')
        
        #create and configure raven client
        Sentry.init(
            dsn=self.__token,
            attach_stacktrace=True,
            before_send=self.__filter_exception,
            integrations=[ExcepthookIntegration(always_run=True)],
        )

    def __filter_exception(self, event, hint):
        """
        Callback used to filter sent exceptions
        """
        if 'exc_info' in hint:
            exc_type, exc_value, tb = hint["exc_info"]
            if type(exc_value).__name__ in (u'KeyboardInterrupt', u'zmq.error.ZMQError', u'AssertionError', u'ForcedException'):
                self.logger.debug('Exception "%s" filtered' % type(exc_value).__name__)
                return None

        return event

    def is_enabled(self):
        """
        Returns True if crash report is enabled

        Returns:
            bool: True if enabled
        """
        return self.__enabled

    def enable(self):
        """
        Enable crash report
        """
        self.logger.debug('Crash report is enabled')
        self.__enabled = True

    def disable(self):
        """
        Disable crash report
        """
        self.logger.debug('Crash report is disabled')
        self.__enabled = False

    def report_exception(self, extra=None):
        """
        Exception handler that report crashes. It automatically include stack trace

        Args:
            extra (dict): extra metadata to post with the report
        """
        if self.__enabled:
            self.logger.debug('Send crash report')
            with Sentry.push_scope() as scope:
                self.__set_extra(scope, extra)
                Sentry.capture_exception()

    def manual_report(self, message, extra=None):
        """
        Report manually a crash report dumping current stack trace to report error

        Args:
            message (string): message to attach to crash report
            extra (dict): extra metadata to post with the report
        """
        if self.__enabled:
            self.logger.debug('Send manual report')
            with Sentry.push_scope() as scope:
                self.__set_extra(scope, extra)
                Sentry.capture_message(message)

    def __set_extra(self, scope, more_extra={}):
        """
        Set extra data to specified Sentry scope (typically )

        Args:
            scope: Sentry scope
        """
        for key, value in self.__extra.items():
            scope.set_extra(key, value)
        if isinstance(more_extra, dict) and more_extra:
            for key, value in more_extra.items():
                scope.set_extra(key, value)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s.%(funcName)s +%(lineno)s: %(levelname)-8s [%(process)d] %(message)s')

    #test crash report
    dsn = 'https://67a672c8a4124ba1a11dfcaf37910a30@sentry.io/1773136'
    cr = CrashReport(dsn, 'Test', '0.0.0', debug=True)
    cr.enable()

    #test local catched exception
    try:
        raise Exception('My custom exception')
    except:
        cr.report_exception()
    print('Done')

    #try main exception
    1/0

    print('Done')

