#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import InvalidParameter, MissingParameter
from ConfigParser import SafeConfigParser
import ast
import io
import os
import codecs
import time

class RaspiotConf():
    """
    Helper class to update and read values from /etc/raspiot/raspiot.conf file
    """

    CONF = u'/etc/raspiot/raspiot.conf'

    DEFAULT_CONFIG = {
        u'general': {
            u'modules': [],
            u'updated': []
        },
        u'rpc': {
            u'rpc_host': u'0.0.0.0',
            u'rpc_port': 80,
            u'rpc_cert': u'',
            u'rpc_key': u''
        },
        u'debug': {
            u'debug_enabled': False,
            u'debug_modules': []
        }
    }

    def __init__(self, cleep_filesystem):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
        """
        #members
        self.cleep_filesystem = cleep_filesystem

    def __open(self):
        """
        Open config file
        
        Returns:
            ConfigParser: ConfigParser instance

        Raises:
            Exception: if file doesn't exist
        """
        #init conf reader
        self.__conf = SafeConfigParser()
        if not os.path.exists(self.CONF):
            #create empty file
            fd = self.cleep_filesystem.open(self.CONF, u'w')
            fd.write(u'')
            self.cleep_filesystem.close(fd)
            time.sleep(0.10)
        
        #load conf content
        fd = self.cleep_filesystem.open(self.CONF, u'r')
        self.__conf.readfp(fd)
        self.cleep_filesystem.close(fd)

        return self.__conf

    def __close(self, write=False):
        """
        Close everything and write new content if forced
        """
        if self.__conf and write:
            #workaround for unicode writing http://bugs.python.org/msg187829
            f = self.cleep_filesystem.open(self.CONF, u'w')
            self.__conf.write(f.buffer)
            self.cleep_filesystem.close(f)
            #self.__conf.write(codecs.open(self.CONF, u'w', u'utf-8'))

    def check(self):
        """
        Check configuration file content, adding missing section or options
        
        Returns:
            bool: always return True
        """
        config = self.__open()
        updated = False

        #merge with default config
        for section in self.DEFAULT_CONFIG.keys():
            #fix missing section
            if not config.has_section(section):
                config.add_section(section)
                updated = True

            #fix missing section keys
            for key in self.DEFAULT_CONFIG[section].keys():
                if not config.has_option(section, key):
                    config.set(section, key, unicode(self.DEFAULT_CONFIG[section][key]))
                    updated = True

        #write changes to filesystem
        self.__close(updated)

        return True

    def as_dict(self):
        """
        Return all config content as dict

        Returns:
            dict: config content
        """
        conf = self.__open()
        self.__close()
        config = {}

        for section in conf.sections():
            config[section] = {}
            for option, val in conf.items(section):
                try:
                    config[section][option] = ast.literal_eval(val)
                except:
                    #unable to eval option, consider it as a string
                    config[section][option] = u'%s' % val

        return config

    def get_global_debug(self):
        """
        Get global debug status

        Returns:
            bool: global debug status
        """
        conf = self.__open()
        self.__close()
        debug = conf.getboolean(u'debug', u'debug_enabled')
        return debug

    def set_global_debug(self, debug):
        """
        Set global debug status

        Args:
            debug (bool): new debug status
        """
        if debug is None:
            raise MissingParameter(u'Debug parameter is missing')
        if debug not in (True, False):
            raise InvalidParameter(u'Debug parameter is invalid')

        conf = self.__open()
        conf.set(u'debug', u'debug_enabled', unicode(debug))
        self.__close(True)

    def install_module(self, module):
        """
        Add module to list of modules to load at startup

        Args:
            module (string): module name to load

        Returns:
            bool: True if module installed
        """
        conf = self.__open()
        
        #check if module isn't already installed
        modules = ast.literal_eval(conf.get(u'general', u'modules'))
        if module in modules:
            return False

        #install module
        modules.append(module)
        conf.set(u'general', u'modules', unicode(modules))
        self.__close(True)

        return True

    def uninstall_module(self, module):
        """
        Remove module from list of loaded modules

        Args:
            module (string): module name to uninstall
        
        Returns:
            bool: True if module uninstalled
        """
        conf = self.__open()
        
        #check if module is installed
        modules = ast.literal_eval(conf.get(u'general', u'modules'))
        if module not in modules:
            return False

        #uninstall module
        modules.remove(module)
        conf.set(u'general', u'modules', unicode(modules))
        self.__close(True)

        return True

    def update_module(self, module):
        """
        Add module name in updated config list item

        Args:
            module (string): module name to set as updated

        Returns:
            bool: True if operation succeed
        """
        conf = self.__open()

        #check if module installed
        modules = ast.literal_eval(conf.get(u'general', u'modules'))
        if module not in modules:
            return False

        #update module
        updated = ast.literal_eval(conf.get(u'general', u'updated'))
        updated.append(module)
        conf.set(u'general', u'updated', unicode(updated))
        self.__close(True)

        return True

    def clear_updated_modules(self):
        """
        Erase updated module list from config
        """
        conf = self.__open()

        #clear list content
        updated = ast.literal_eval(conf.get(u'general', u'updated'))
        updated[:] = []
        conf.set(u'general', u'updated', unicode(updated))
        self.__close(True)

    def is_module_installed(self, module):
        """
        Return True if specified module is installed
        
        Args:
            module (string): module name to check

        Returns:
            bool: True if module is installed
        """
        conf = self.__open()
        self.__close()
        modules = ast.literal_eval(conf.get(u'general', u'modules'))

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
        modules = ast.literal_eval(conf.get(u'debug', u'debug_modules'))
        if module in modules:
            #module already in debug list
            return True

        #add module to debug list
        modules.append(module)
        conf.set(u'debug', u'debug_modules', unicode(modules))
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
        modules = ast.literal_eval(conf.get(u'debug', u'debug_modules'))
        if module not in modules:
            #module not in debug list
            return True

        #remove module from debug list
        modules.remove(module)
        conf.set(u'debug', u'debug_modules', unicode(modules))
        self.__close(True)

        return True

    def is_module_debugged(self, module):
        """
        Return True if module debug is enabled

        Args:
            module (string): module name to check

        Returns:
            bool: True if module debug is enabled, False if disabled
        """
        conf = self.__open()
        self.__close()
        modules = ast.literal_eval(conf.get(u'debug', u'debug_modules'))

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

        conf.set(u'rpc', u'rpc_host', host)
        conf.set(u'rpc', u'rpc_port', unicode(port))
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
        self.__close()
        rpc = (conf.get(u'rpc', u'rpc_host'), conf.getint(u'rpc', u'rpc_port'))

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

        conf.set(u'rpc', u'rpc_cert', cert)
        conf.set(u'rpc', u'rpc_key', key)
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
        self.__close()
        rpc = (conf.get(u'rpc', u'rpc_cert'), conf.get(u'rpc', u'rpc_key'))

        return rpc


