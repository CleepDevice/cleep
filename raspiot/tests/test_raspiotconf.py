#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import InvalidParameter, MissingParameter
from raspiot.libs.raspiotconf import RaspiotConf
import unittest
from ConfigParser import SafeConfigParser
import os


class RaspiotConfTests(unittest.TestCase):

    def setUp(self):
        #fake conf file
        conf = SafeConfigParser()
        conf.add_section('general')
        conf.set('general', 'modules', unicode([]))
        conf.add_section('rpc')
        conf.set('rpc', 'rpc_host', '0.0.0.0')
        conf.set('rpc', 'rpc_port', '80')
        conf.set('rpc', 'rpc_cert', '')
        conf.set('rpc', 'rpc_key', '')
        conf.add_section('debug')
        conf.set('debug', 'debug_enabled', 'False')
        conf.set('debug', 'debug_modules', unicode([]))
        conf.write(open('raspiot.fake.conf', 'w'))
        
        self.rc = RaspiotConf()
        self.rc.CONF = 'raspiot.fake.conf'

    def tearDown(self):
        os.remove('raspiot.fake.conf')

    def test_get_global_debug(self):
        self.assertFalse(self.rc.get_global_debug())

    def test_update_global_debug(self):
        self.rc.set_global_debug(True)
        self.assertTrue(self.rc.get_global_debug())

    def test_install_module(self):
        self.assertTrue(self.rc.install_module('newmodule'))
        self.assertTrue(self.rc.is_module_installed('newmodule'))

    def test_install_already_installed_module(self):
        self.rc.install_module('newmodule')
        self.assertTrue(self.rc.is_module_installed('newmodule'))
        self.assertRaises(InvalidParameter, self.rc.install_module, 'newmodule')

    def test_uninstall_module(self):
        self.rc.install_module('mymodule')
        self.assertTrue(self.rc.is_module_installed('mymodule'))
        self.assertTrue(self.rc.uninstall_module('mymodule'))
        self.assertFalse(self.rc.is_module_installed('mymodule'))

    def test_uninstall_unknown_module(self):
        self.rc.install_module('mymodule1')
        self.rc.install_module('mymodule2')
        self.assertRaises(InvalidParameter, self.rc.uninstall_module, 'mymodule3')
        self.assertFalse(self.rc.is_module_installed('mymodule3'))

    def test_enable_module_debug(self):
        self.assertTrue(self.rc.enable_module_debug('mymodule'))
        self.assertTrue(self.rc.is_module_debugged('mymodule'))

    def test_disable_module_debug(self):
        self.rc.enable_module_debug('mymodule')
        self.assertTrue(self.rc.disable_module_debug('mymodule'))
        self.assertFalse(self.rc.is_module_debugged('mymodule'))

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

