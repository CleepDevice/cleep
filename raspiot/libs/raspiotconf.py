#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import InvalidParameter, MissingParameter
import unittest
from ConfigParser import SafeConfigParser
import ast
import os

class RaspiotConf():
    """
    Helper class to update and read values from /etc/raspiot/raspiot.conf file
    """

    CONF = '/etc/raspiot/raspiot.conf'

    def __open(self):
        """
        Open config file
        @return ConfigParser instance (ConfigParser)
        @raise Exception if file doesn't exist
        """
        self.__conf = SafeConfigParser()
        if not os.path.exists(self.CONF):
            raise Exception('Config file "%s" does not exist' % self.CONF)
        self.__conf.read(self.CONF)

        return self.__conf

    def __close(self, write=False):
        """
        Close everything and write new content if specified
        @param write: write new content if set to True
        """
        if self.__conf and write: 
            self.__conf.write(open(self.CONF, 'w'))

    def check(self):
        """
        Check configuration file content
        @return True if file is conform, False otherwise
        @raise Exception if file content is malformed
        """
        conf = self.__open()
        if not conf.has_section('general') or not conf.has_section('rpc') or not conf.has_section('debug'):
            raise Exception('Config file "%s" is malformed' % self.CONF)
        if not conf.has_option('general', 'modules'):
            raise Exception('Config file "%s" is malformed' % self.CONF)
        if not conf.has_option('rpc', 'rpc_host') or not conf.has_option('rpc', 'rpc_port') or not conf.has_option('rpc', 'rpc_cert') or not conf.has_option('rpc', 'rpc_key'):
            raise Exception('Config file "%s" is malformed' % self.CONF)
        if not conf.has_option('debug', 'debug_enabled') or not conf.has_option('debug', 'debug_modules'):
            raise Exception('Config file "%s" is malformed' % self.CONF)

        return True

    def as_dict(self):
        """
        Return all config content as dict
        @return config content (dict)
        """
        conf = self.__open()
        config = {}

        for section in conf.sections():
            config[section] = {}
            for option, val in conf.items(section):
                config[section][option] = ast.literal_eval(val)

        return config

    def get_global_debug(self):
        """
        Get global debug status
        @return global debug status (bool)
        """
        conf = self.__open()
        debug = conf.getboolean('debug', 'debug_enabled')
        self.__close()
        return debug

    def set_global_debug(self, debug):
        """
        Set global debug status
        @param debug: new debug status (bool)
        """
        if debug is None:
            raise MissingParameter('Debug parameter is missing')
        if debug not in (True, False):
            raise InvalidParameter('Debug parameter is invalid')

        conf = self.__open()
        conf.set('debug', 'debug_enabled', str(debug))
        self.__close(True)

    def install_module(self, module):
        """
        Add module to list of modules to load at startup
        @param module: module name to load (string)
        @return True if module installed
        @raise InvalidParameter
        """
        conf = self.__open()
        
        #check if module isn't already installed
        modules = ast.literal_eval(conf.get('general', 'modules'))
        if module in modules:
            raise InvalidParameter('Module %s is already installed' % module)

        #install module
        modules.append(module)
        conf.set('general', 'modules', str(modules))
        self.__close(True)

        return True

    def uninstall_module(self, module):
        """
        Remove module from list of loaded modules
        @param module: module name to uninstall
        @return True if module uninstalled
        @raise InvalidParameter
        """
        conf = self.__open()
        
        #check if module is installed
        modules = ast.literal_eval(conf.get('general', 'modules'))
        if module not in modules:
            raise InvalidParameter('Unable to uninstall not installed module %s' % module)

        #uninstall module
        modules.remove(module)
        conf.set('general', 'modules', str(modules))
        self.__close(True)

        return True

    def module_is_installed(self, module):
        """
        Return True if specified module is installed
        @param module: module name to check
        @return True if module is installed
        """
        conf = self.__open()

        modules = ast.literal_eval(conf.get('general', 'modules'))
        return module in modules


    def enable_module_debug(self, module):
        """
        Enable module debug
        @param module: module name to debug
        @return True if module debug enabled
        """
        conf = self.__open()
        
        #check if module is in debug list
        modules = ast.literal_eval(conf.get('debug', 'debug_modules'))
        if module in modules:
            #module already in debug list
            return True

        #add module to debug list
        modules.append(module)
        conf.set('debug', 'debug_modules', str(modules))
        self.__close(True)

        return True

    def disable_module_debug(self, module):
        """
        Disable module debug
        @param module: module name to disable
        @return True if module debug disabled
        """
        conf = self.__open()
        
        #check if module is in debug list
        modules = ast.literal_eval(conf.get('debug', 'debug_modules'))
        if module not in modules:
            #module not in debug list
            return True

        #remove module from debug list
        modules.remove(module)
        conf.set('debug', 'debug_modules', str(modules))
        self.__close(True)

        return True

    def module_is_debugged(self, module):
        """
        Return True if module debug is enabled
        @param module: module name to check
        @return True if module debug is enabled, False if disabled
        """
        conf = self.__open()

        modules = ast.literal_eval(conf.get('debug', 'debug_modules'))
        return module in modules

    def set_rpc_config(self, host, port):
        """
        Set rpc configuration
        @param host: rpc server host value
        @param port: rpc server port value
        @return True if rpc config saved
        """
        conf = self.__open()

        conf.set('rpc', 'rpc_host', host)
        conf.set('rpc', 'rpc_port', str(port))
        self.__close(True)

        return True

    def get_rpc_config(self):
        """
        Get rpc configuration
        @return rpc host and port values (tuple)
        """
        conf = self.__open()

        rpc = (conf.get('rpc', 'rpc_host'), conf.getint('rpc', 'rpc_port'))
        return rpc

    def set_rpc_security(self, cert, key):
        """
        Set rpc security configuration
        @param cert: certificate file path
        @param key: key file path
        @return True if values saved successfully
        """
        conf = self.__open()

        conf.set('rpc', 'rpc_cert', cert)
        conf.set('rpc', 'rpc_key', key)
        self.__close(True)

        return True

    def get_rpc_security(self):
        """
        Get rpc security configuration
        @return cert and key values (tuple)
        """
        conf = self.__open()

        rpc = (conf.get('rpc', 'rpc_cert'), conf.get('rpc', 'rpc_key'))
        return rpc




class RaspiotConfTests(unittest.TestCase):
    def setUp(self):
        #fake conf file
        conf = SafeConfigParser()
        conf.add_section('general')
        conf.set('general', 'modules', str([]))
        conf.add_section('rpc')
        conf.set('rpc', 'rpc_host', '0.0.0.0')
        conf.set('rpc', 'rpc_port', '80')
        conf.set('rpc', 'rpc_cert', '')
        conf.set('rpc', 'rpc_key', '')
        conf.add_section('debug')
        conf.set('debug', 'debug_enabled', 'False')
        conf.set('debug', 'debug_modules', str([]))
        conf.write(open('/tmp/raspiot.fake.conf', 'w'))
        
        self.rc = RaspiotConf()
        self.rc.CONF = '/tmp/raspiot.fake.conf'

    def test_get_global_debug(self):
        self.assertFalse(self.rc.get_global_debug())

    def test_update_global_debug(self):
        self.rc.set_global_debug(True)
        self.assertTrue(self.rc.get_global_debug())

    def test_install_module(self):
        self.assertTrue(self.rc.install_module('newmodule'))
        self.assertTrue(self.rc.module_is_installed('newmodule'))

    def test_install_already_installed_module(self):
        self.rc.install_module('newmodule')
        self.assertTrue(self.rc.module_is_installed('newmodule'))
        self.assertRaises(InvalidParameter, self.rc.install_module, 'newmodule')

    def test_uninstall_module(self):
        self.rc.install_module('mymodule')
        self.assertTrue(self.rc.module_is_installed('mymodule'))
        self.assertTrue(self.rc.uninstall_module('mymodule'))
        self.assertFalse(self.rc.module_is_installed('mymodule'))

    def test_uninstall_unknown_module(self):
        self.rc.install_module('mymodule1')
        self.rc.install_module('mymodule2')
        self.assertRaises(InvalidParameter, self.rc.uninstall_module, 'mymodule3')
        self.assertFalse(self.rc.module_is_installed('mymodule3'))

    def test_enable_module_debug(self):
        self.assertTrue(self.rc.enable_module_debug('mymodule'))
        self.assertTrue(self.rc.module_is_debugged('mymodule'))

    def test_disable_module_debug(self):
        self.rc.enable_module_debug('mymodule')
        self.assertTrue(self.rc.disable_module_debug('mymodule'))
        self.assertFalse(self.rc.module_is_debugged('mymodule'))

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

