#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from cleepconf import CleepConf
from cleep.libs.internals.cleepfilesystem import CleepFilesystem
from cleep.libs.internals.download import Download
from cleep.exception import MissingParameter, InvalidParameter, CommandError
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from pprint import pprint
import io
from unittest.mock import Mock
from configparser import ConfigParser
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()


class CleepConfTests(unittest.TestCase):

    FILE_NAME = 'cleep.conf'

    def setUp(self):
        TestLib()
        logging.basicConfig(level=LOG_LEVEL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.path = os.path.join(os.getcwd(), self.FILE_NAME)
        logging.debug('Using conf file "%s"' % self.path)

        #fake conf file
        conf = ConfigParser()
        conf.add_section('general')
        conf.set('general', 'modules', str([]))
        conf.set('general', 'updated', str([]))
        conf.add_section('rpc')
        conf.set('rpc', 'rpc_host', '0.0.0.0')
        conf.set('rpc', 'rpc_port', '80')
        conf.set('rpc', 'rpc_cert', '')
        conf.set('rpc', 'rpc_key', '')
        conf.add_section('debug')
        conf.set('debug', 'trace_enabled', u'False')
        conf.set('debug', 'debug_core', u'False')
        conf.set('debug', 'debug_modules', str([]))
        with open(self.FILE_NAME, 'w') as fp:
            conf.write(fp)
        
        rc = CleepConf
        rc.CONF = self.FILE_NAME
        self.rc = rc((self.fs))

    def tearDown(self):
        if os.path.exists('%s' % self.FILE_NAME):
            os.remove('%s' % self.FILE_NAME)

    def test_enable_trace(self):
        self.rc.enable_trace()
        self.assertTrue(self.rc.is_trace_enabled())

    def test_disable_trace(self):
        self.rc.disable_trace()
        self.assertFalse(self.rc.is_trace_enabled())

    def test_enable_core_debug(self):
        self.rc.enable_core_debug()
        self.assertTrue(self.rc.is_core_debugged())

    def test_disable_core_debug(self):
        self.rc.disable_core_debug()
        self.assertFalse(self.rc.is_core_debugged())

    def test_check(self):
        self.assertIsNone(self.rc.check())

    def test_check_without_file(self):
        os.remove('%s' % self.FILE_NAME)
        self.assertIsNone(self.rc.check())

    def test_install_module(self):
        self.assertTrue(self.rc.install_module('newmodule'))
        self.assertTrue(self.rc.is_module_installed('newmodule'))

    def test_install_already_installed_module(self):
        self.rc.install_module('newmodule')
        self.assertTrue(self.rc.is_module_installed('newmodule'))
        self.assertTrue(self.rc.install_module('newmodule'))

    def test_uninstall_module(self):
        self.rc.install_module('mymodule')
        self.assertTrue(self.rc.is_module_installed('mymodule'))
        self.assertTrue(self.rc.uninstall_module('mymodule'))
        self.assertFalse(self.rc.is_module_installed('mymodule'))

    def test_uninstall_unknown_module(self):
        self.rc.install_module('mymodule1')
        self.rc.install_module('mymodule2')
        self.assertFalse(self.rc.uninstall_module('mymodule3'))
        self.assertFalse(self.rc.is_module_installed('mymodule3'))

    def test_update_module(self):
        self.rc.install_module('mymodule1')
        self.assertTrue(self.rc.update_module('mymodule1'))
        self.assertTrue(self.rc.is_module_updated('mymodule1'))

    def test_update_module_already_updated_module(self):
        self.rc.install_module('mymodule1')
        self.rc.update_module('mymodule1')
        self.assertTrue(self.rc.update_module('mymodule1'))

    def test_clear_updated_modules(self):
        self.rc.install_module('mymodule1')
        self.rc.install_module('mymodule2')
        self.rc.update_module('mymodule1')
        self.rc.update_module('mymodule2')
        self.rc.clear_updated_modules()
        self.assertFalse(self.rc.is_module_updated('mymodule1'))
        self.assertFalse(self.rc.is_module_updated('mymodule2'))

    def test_update_module_unknown_module(self):
        self.assertFalse(self.rc.update_module('mymodule2'))

    def test_enable_module_debug(self):
        self.rc.install_module('mymodule')
        self.assertTrue(self.rc.enable_module_debug('mymodule'))
        self.assertTrue(self.rc.is_module_debugged('mymodule'))

    def test_disable_module_debug(self):
        self.rc.install_module('mymodule')
        self.rc.enable_module_debug('mymodule')
        self.assertTrue(self.rc.disable_module_debug('mymodule'))
        self.assertFalse(self.rc.is_module_debugged('mymodule'))

    def test_disable_module_debug_not_debugged_module(self):
        self.assertFalse(self.rc.disable_module_debug('mymodule'))
        self.assertFalse(self.rc.is_module_debugged('mymodule'))

    def test_enable_module_debug_already_debugged(self):
        self.rc.install_module('mymodule')
        self.rc.enable_module_debug('mymodule')
        self.assertTrue(self.rc.enable_module_debug('mymodule'))
    
    def test_enable_module_debug_not_installed_module(self):
        self.assertFalse(self.rc.enable_module_debug('mymodule'))

    def test_rpc_get_config(self):
        rpc = self.rc.get_rpc_config()
        self.assertIsInstance(rpc, tuple)
        self.assertEqual(rpc[0], '0.0.0.0')
        self.assertEqual(rpc[1], 80)
       
    def test_rpc_set_config(self):
        self.assertTrue(self.rc.set_rpc_config('localhost', 9000))
        rpc = self.rc.get_rpc_config()
        self.assertEqual(rpc[0], 'localhost')
        self.assertEqual(rpc[1], 9000)

    def test_rpc_get_security(self):
        rpc = self.rc.get_rpc_security()
        self.assertIsInstance(rpc, tuple)
        self.assertEqual(rpc[0], '')
        self.assertEqual(rpc[1], '')
       
    def test_rpc_set_security(self):
        self.assertTrue(self.rc.set_rpc_security('mycert.crt', 'mykey.key'))
        rpc = self.rc.get_rpc_security()
        self.assertEqual(rpc[0], 'mycert.crt')
        self.assertEqual(rpc[1], 'mykey.key')

    def test_config_as_dict(self):
        self.assertIsInstance(self.rc.as_dict(), dict)

if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_cleepconf.py; coverage report -m -i
    unittest.main()
