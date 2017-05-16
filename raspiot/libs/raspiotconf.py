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
        
        Returns:
            ConfigParser: ConfigParser instance

        Raises:
            Exception: if file doesn't exist
        """
        self.__conf = SafeConfigParser()
        if not os.path.exists(self.CONF):
            raise Exception('Config file "%s" does not exist' % self.CONF)
        self.__conf.read(self.CONF)

        return self.__conf

    def __close(self, write=False):
        """
        Close everything and write new content if specified

        Args:
            write (bool): write new content if set to True
        """
        if self.__conf and write: 
            self.__conf.write(open(self.CONF, 'w'))

    def check(self):
        """
        Check configuration file content
        
        Returns:
            bool: True if file is conform, False otherwise

        Raises:
            Exception: if file content is malformed
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

        Returns:
            dict: config content
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

        Returns:
            bool: global debug status
        """
        conf = self.__open()
        debug = conf.getboolean('debug', 'debug_enabled')
        self.__close()
        return debug

    def set_global_debug(self, debug):
        """
        Set global debug status

        Args:
            debug (bool): new debug status
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

        Args:
            module (string): module name to load

        Returns:
            bool: True if module installed

        Raises:
            InvalidParameter
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

        Args:
            module (string): module name to uninstall
        
        Returns:
            bool: True if module uninstalled

        Raises:
            InvalidParameter
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
        
        Args:
            module (string): module name to check

        Returns:
            bool: True if module is installed
        """
        conf = self.__open()

        modules = ast.literal_eval(conf.get('general', 'modules'))
        return module in modules


    def enable_module_debug(self, module):
        """
        Enable module debug

        Args:
            module (string): module name to debug

        Returns:
            bool: True if module debug enabled
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

        Args:
            module (string): module name to disable
                             
        Returns:
            bool: True if module debug disabled
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

        Args:
            module (string): module name to check

        Returns:
            bool: True if module debug is enabled, False if disabled
        """
        conf = self.__open()

        modules = ast.literal_eval(conf.get('debug', 'debug_modules'))
        return module in modules

    def set_rpc_config(self, host, port):
        """
        Set rpc configuration

        Args:
            host (string): rpc server host value
            port (int): rpc server port value

        Returns:
            bool: True if rpc config saved
        """
        conf = self.__open()

        conf.set('rpc', 'rpc_host', host)
        conf.set('rpc', 'rpc_port', str(port))
        self.__close(True)

        return True

    def get_rpc_config(self):
        """
        Get rpc configuration

        Returns:
            tuple: rpc host and port values
                (
                    host (string),
                    port (int)
                )
        """
        conf = self.__open()

        rpc = (conf.get('rpc', 'rpc_host'), conf.getint('rpc', 'rpc_port'))
        return rpc

    def set_rpc_security(self, cert, key):
        """
        Set rpc security configuration

        Args:
            cert (string): certificate file path
            key (string): key file path

        Returns:
            bool: True if values saved successfully
        """
        conf = self.__open()

        conf.set('rpc', 'rpc_cert', cert)
        conf.set('rpc', 'rpc_key', key)
        self.__close(True)

        return True

    def get_rpc_security(self):
        """
        Get rpc security configuration

        Returns:
            tuple: cert and key values
                (
                    cert,
                    key
                )
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

    def tearDown(self):
        os.remove('/tmp/raspiot.fake.conf')

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

