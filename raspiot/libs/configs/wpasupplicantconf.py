#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.exception import InvalidParameter, MissingParameter, CommandError
from raspiot.libs.configs.config import Config
from raspiot.libs.internals.console import Console
import logging
import os
import re
import io
import time

class WpaSupplicantConf(Config):
    """
    Helper class to update and read /etc/wpa_supplicant/wpa_supplicant.conf file
    This class is not thread safe due to self.CONF that can modified on the fly

    Infos:
        https://w1.fi/cgit/hostap/plain/wpa_supplicant/wpa_supplicant.conf
    """

    DEFAULT_CONF = u'/etc/wpa_supplicant/wpa_supplicant.conf'
    CONF = DEFAULT_CONF
    WPASUPPLICANT_DIR = u'/etc/wpa_supplicant'

    ENCRYPTION_TYPE_WPA = u'wpa'
    ENCRYPTION_TYPE_WPA2 = u'wpa2'
    ENCRYPTION_TYPE_WEP = u'wep'
    ENCRYPTION_TYPE_UNSECURED = u'unsecured'
    ENCRYPTION_TYPE_UNKNOWN = u'unknown'
    ENCRYPTION_TYPES = [ENCRYPTION_TYPE_WPA, ENCRYPTION_TYPE_WPA2, ENCRYPTION_TYPE_WEP, ENCRYPTION_TYPE_UNSECURED, ENCRYPTION_TYPE_UNKNOWN]

    COUNTRIES_ISO3166 = u'/usr/share/zoneinfo/iso3166.tab'

    def __init__(self, cleep_filesystem, backup=True):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
            backup (bool): backup file
        """
        #config file may vary that's why None is specified as config filepath in constructor
        Config.__init__(self, cleep_filesystem, None, None, backup)

        #logger
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)

        #members
        self.cleep_filesystem = cleep_filesystem
        self.__groups = {}
        self.__country_codes = None

    def __load_country_codes(self):
        """
        Load country codes based on local files
        """
        self.logger.trace(u'Opening countries file "%s"' % self.COUNTRIES_ISO3166)
        if os.path.exists(self.COUNTRIES_ISO3166):
            lines = self.cleep_filesystem.read_data(self.COUNTRIES_ISO3166)
            self.logger.trace('COUNTRIES_ISO3166 contains %s lines' % len(lines))

            if not lines:
                self.logger.error(u'Unable to get countries, countries file "%s" is empty')
                self.__country_codes = {}
                return

            self.__country_codes = {}
            for line in lines:
                if line.startswith(u'#'):
                    continue
                (code, country) = line.split(None, 1)
                self.__country_codes[country.strip().lower()] = code

        else:
            #no iso3166 file, set to empty dict
            self.logger.warning('Unable to get countries, countries file "%s" was not found' % self.COUNTRIES_ISO3166)
            self.__country_codes = {}

        self.logger.trace(u'Found country codes: %s' % self.__country_codes)

    def set_country(self, country):
        """
        Configure country in wpa_supplicant conf file

        Args:
            country (string): country name to set

        Raises:
            Exception if country code is invalid
        """
        #load country codes
        if self.__country_codes is None:
            self.__load_country_codes()

        #get country code
        country_lower = country.lower()
        if country_lower not in self.__country_codes:
            self.logger.error(u'Country "%s" not found in country codes' % country_lower)
            raise Exception('Invalid country code "%s" specified' % country)
        country_code = self.__country_codes[country_lower]
        self.logger.debug(u'Found country code "%s" for country "%s"' % (country_code, country))

        #update wpa_supplicant files
        config_files = self.__get_configuration_files()
        old_conf = self.CONF
        for interface in config_files:
            self.CONF = config_files[interface]
            if self.replace_line(u'^\s*country\s*=.*$', 'country=%s' % country_code):
                self.logger.info(u'Country code "%s" updated in "%s" file' % (country_code, self.CONF))
            elif self.add_lines(['country=%s\n' % country_code], end=False):
                self.logger.info(u'Country code "%s" added in "%s" file' % (country_code, self.CONF))
            else: # pragma: no cover
                self.logger.warning(u'Unable to set country code in wpasupplicant file "%s"' % self.CONF)

        #restore old conf file
        self.CONF = old_conf

    def encrypt_password(self, network, password):
        """
        Encrypt specified password using wpa_passphrase

        Args:
            network (string): network name
            password (string): password to encrypt

        Returns:
            string: encrypted password
        """
        lines = self.wpa_passphrase(network, password)

        for line in lines:
            line = line.strip()
            if line.startswith(u'psk='):
                return line.replace(u'psk=', '')

        self.logger.error(u'No password generated by wpa_passphrase: %s' % lines)
        raise Exception(u'No password generated by wpa_passphrase command')

    def wpa_passphrase(self, network, password):
        """
        Execute wpa_passphrase command and return output

        Args:
            network (string): network name
            password (string): password

        Returns:
            list: wpa_passphrase output without password in clear
        """
        if network is None or len(network)==0:
            raise MissingParameter(u'Parameter network is missing')
        if password is None or len(password)==0:
            raise MissingParameter(u'Parameter password is missing')
        if len(password)<8 or len(password)>63:
            raise InvalidParameter(u'Parameter password must be 8..63 string length')

        c = Console()
        res = c.command(u'/usr/bin/wpa_passphrase "%s" "%s"' % (network, password))
        if res[u'error'] or res[u'killed']:
            self.logger.error(u'Error with wpa_passphrase: %s' % u''.join(res[u'stderr']))
            raise Exception(u'Error with wpa_passphrase: unable to encrypt it')
        if not ''.join(res[u'stdout']).startswith(u'network'):
            self.logger.error(u'Error with wpa_passphrase: %s' % u''.join(res[u'stdout']))
            raise Exception(u'Error with wpa_passphrase: invalid command output')
        output = [line+u'\n' for line in res[u'stdout'] if not line.startswith(u'\t#psk=')]

        return output

    def __get_configuration_files(self):
        """
        Scan /etc/wpa_supplicant directory to find interface specific confguration

        Returns:
            dict: interface and configuration file::

                {
                    interface(string): config path (string),
                    ...
                }

        """
        configs = {}

        self.logger.debug('Scan "%s" for wpa_supplicant config files' % self.WPASUPPLICANT_DIR)
        for f in os.listdir(self.WPASUPPLICANT_DIR):
            try:
                fpath = os.path.join(self.WPASUPPLICANT_DIR, f)
                (conf, ext) = os.path.splitext(f)
                if os.path.isfile(fpath) and conf==u'wpa_supplicant':
                    #default config file
                    configs[u'default'] = fpath

                elif os.path.isfile(fpath) and ext==u'.conf' and conf.startswith(u'wpa_supplicant-'):
                    #get interface
                    interface = conf.split(u'-', 1)[1]
                    configs[interface] = fpath

            except: # pragma: no cover
                self.logger.exception(u'Exception occured during wpa_supplicant config file search:')

        self.logger.debug(u'Found wpa_supplicant config files: %s' % configs)
        return configs

    def __get_configuration(self, config, interface):
        """
        Return networks found in conf file

        Args:
            config (string): config filepath to parse
            interface (string): interface that refers to specified file (used to store data)

        Returns:
            dict: list of wireless configurations::

                {
                    network name (string): {
                        group (string): full search result,
                        network (string): network name,
                        password (string): password,
                        hidden (bool): True if network is hidden,
                        encryption (string): encryption type (see ENCRYPTION_TYPE_XXX),
                        disabled (string): True if network is disabled
                    }
                }

        """
        networks = {}
        entries = []

        #force specified config file
        self.logger.debug(u'Read configuration of "%s" for interface "%s"' % (config, interface))
        self.CONF = config

        #parse network={} block:  {((?:[^{}]|(?R))*)}
        #parse inside network block:  \s+(.*?)=(.*?)\s*\R
        results = self.find(r'network\s*=\s*\{\s*(.*?)\s*\}', re.UNICODE | re.DOTALL)
        for group, groups in results:
            #prepare values
            ssid = None

            #filter none values
            groups = list(filter(None, groups))

            #create new entry
            current_entry = {
                u'group': group, #DO NOT REMOVE IT, field is removed at end of this function
                u'network': None,
                u'password': None,
                u'hidden': False,
                u'encryption': self.ENCRYPTION_TYPE_WPA2, #default encryption to WPA2 event if not specified in wpa_supplicant.conf file
                u'disabled': False
            }
            entries.append(current_entry)

            #fill entry
            pattern = r'^\s*(\w+)=(.*?)\s*$'
            for content in groups:
                sub_results = self.find_in_string(pattern, content, re.UNICODE | re.MULTILINE)
                
                #filter none values
                for sub_group, sub_groups in sub_results:
                    if len(sub_groups)==2:
                        if sub_groups[0].startswith(u'ssid'):
                            current_entry[u'network'] = sub_groups[1].replace('"','').replace('\'','')
                        elif sub_groups[0].startswith(u'scan_ssid'):
                            if sub_groups[1] is not None and sub_groups[1].isdigit() and sub_groups[1]=='1':
                                current_entry[u'hidden'] = True
                        elif sub_groups[0].startswith(u'key_mgmt'):
                            if sub_groups[1]==u'WPA-PSK':
                                current_entry[u'encryption'] = self.ENCRYPTION_TYPE_WPA2
                            elif sub_groups[1]==u'NONE':
                                current_entry[u'encryption'] = self.ENCRYPTION_TYPE_WEP
                        elif sub_groups[0].startswith(u'psk'):
                            current_entry[u'password'] = sub_groups[1].replace('"','').replace('\'','')
                        elif sub_groups[0].startswith(u'wep_key0'):
                            current_entry[u'password'] = sub_groups[1].replace('"','').replace('\'','')
                        elif sub_groups[0].startswith(u'disabled') and sub_groups[1]=='1':
                            current_entry[u'disabled'] = True

                    else: # pragma: no cover
                        #invalid content, drop this item
                        continue

        #clean entry
        if interface not in self.__groups:
            self.__groups[interface] = {}
        for entry in entries:
            self.__groups[interface][entry[u'network']] = entry[u'group']
            del entry[u'group']
            networks[entry[u'network']] = entry

        return networks

    def get_configurations(self):
        """
        Get all configuration files

        Returns:
            dict: dict of configurations per interface. If no config for interface, interface is named "default"
        """
        #init
        configs = {}

        #get configuration files
        config_files = self.__get_configuration_files()

        #get configurations
        if len(config_files)==0:
            #no specific configuration files found, fallback to default one
            configs[u'default'] = self.__get_configuration(self.DEFAULT_CONF, u'default')

        else:
            #parse all configuration files
            for interface in config_files:
                configs[interface] = self.__get_configuration(config_files[interface], interface)
        
        return configs

    def get_configuration(self, network, interface=None):
        """
        Get network config

        Args:
            network (string): network name
            interface (string|None): if specified try to add network in specific interface wpa_supplicant.conf file

        Returns:
            dict: network config, None if network is not found
        """
        #get configurations
        configurations = self.get_configurations()

        #get configuration of specified interface
        if interface:
            if interface not in configurations:
                return None
            elif network not in configurations[interface]:
                return None
            else:
                return configurations[interface][network]

        else:
            if u'default' not in configurations:
                return None
            elif network not in configurations[u'default']:
                return None
            else:
                return configurations[u'default'][network]

    def delete_network(self, network, interface=None):
        """
        Delete network from config

        Args:
            network (string): network name
            interface (string|None): if specified try to add network in specific interface wpa_supplicant.conf file

        Returns:
            bool: True if network deleted, False otherwise
        """
        #check params
        if network is None or len(network)==0:
            raise MissingParameter(u'Network parameter is missing')

        #check if network exists
        configuration = self.get_configuration(network, interface)
        self.logger.debug(u'Found configuration: %s' % configuration)
        if configuration is None:
            return False

        #get configurations files
        configurations = self.__get_configuration_files()

        #remove network config
        if interface:
            self.CONF = configurations[interface]
            return self.remove(self.__groups[interface][configuration[u'network']])
        else:
            self.CONF = configurations[u'default']
            return self.remove(self.__groups[u'default'][configuration[u'network']])

    def __check_wpa_supplicant_conf_existence(self, interface):
        """
        Check if wpa_supplicant conf file exists for specified interface.
        If not exists, create default one

        Args:
            interface (string): interface name
        """
        if not interface or interface==u'default':
            #invalid interface specified, no config file to create
            return

        path = os.path.join(self.WPASUPPLICANT_DIR, 'wpa_supplicant-%s.conf' % interface)
        if not os.path.exists(path):
            self.logger.info(u'Create default wpa_supplicant conf file for interface "%s" (%s)' % (interface, path))
            self.cleep_filesystem.copy(self.DEFAULT_CONF, path)
            time.sleep(0.25)

    def __add_network(self, config, interface=None):
        """
        Add new entry based on configuration

        Args:
            config (dict): configuration dict (see get_configuration)
            interface (string|None): if specified try to add network in specific interface wpa_supplicant.conf file

        Returns:
            bool: True if network added
        """
        content = [
            u'\nnetwork={\n',
            u'\tssid="%s"\n' % config[u'network']
        ]

        #encryption
        if config[u'encryption'] in [self.ENCRYPTION_TYPE_WPA, self.ENCRYPTION_TYPE_WPA2]:
            #WPA/WPA2 security
            content.append(u'\tkey_mgmt=WPA-PSK\n')
            content.append(u'\tpsk=%s\n' % config[u'password'])
        elif config[u'encryption']==self.ENCRYPTION_TYPE_WEP:
            #WEP security
            content.append(u'\tkey_mgmt=NONE\n')
            content.append(u'\twep_key0=%s\n' % config[u'password'])
            content.append(u'\twep_tx_keyidx=0\n')
        else:
            #unsecured network
            content.append(u'\tkey_mgmt=NONE\n')

        #hidden network
        if config[u'hidden']:
            content.append(u'\tscan_ssid=1\n')

        #disabled network
        if config[u'disabled']:
            content.append(u'\tdisabled=1\n')

        content.append(u'}\n')

        self.logger.debug('Config to append %s' % content)
        return self.add_lines(content)

    def add_network(self, network, encryption, password, hidden=False, interface=None, encrypt_password=True):
        """
        Add new network in config file
        Password is automatically encrypted using wpa_passphrase
        
        Args:
            network (string): network name (ssid)
            encryption (string): network encryption (wpa|wpa2|wep|unsecured)
            password (string): network password (not encrypted!)
            hidden (bool): hidden network flag
            interface (string|None): if specified try to add network in specific interface wpa_supplicant.conf file
            encrypt_password (bool): encrypt password if necessary before adding it to config file (default True)

        Returns:
            bool: True if network successfully added

        Raises:
            MissingParameter, InvalidParameter
        """
        #check params
        if network is None or len(network)==0:
            raise MissingParameter(u'Parameter "network" is missing')
        if encryption is None or len(encryption)==0:
            raise MissingParameter(u'Parameter "encryption" is missing')
        if encryption not in self.ENCRYPTION_TYPES:
            raise InvalidParameter(u'Encryption "%s" does not exist (available: %s)' % (encryption, u','.join(self.ENCRYPTION_TYPES)))
        if encryption!=self.ENCRYPTION_TYPE_UNSECURED and (password is None or len(password)==0):
            raise MissingParameter(u'Parameter "password" is missing')

        #check if network doesn't already exist
        if self.get_configuration(network, interface) is not None:
            raise InvalidParameter(u'Network "%s" is already configured' % network)

        #make sure config file exists for interface
        self.__check_wpa_supplicant_conf_existence(interface)
    
        #header
        output = [
            u'\nnetwork={\n',
            u'\tssid="%s"\n' % network,
        ]

        #inject hidden param if necessary
        if hidden:
            output.append(u'\tscan_ssid=1\n')

        #inject network type and password
        if encryption in [self.ENCRYPTION_TYPE_WPA, self.ENCRYPTION_TYPE_WPA2]:
            #WPA/WPA2 security
            output.append(u'\tkey_mgmt=WPA-PSK\n')
            if encrypt_password:
                output.append(u'\tpsk=%s\n' % self.encrypt_password(network, password))
            else:
                output.append(u'\tpsk=%s\n' % password)
        elif encryption==self.ENCRYPTION_TYPE_WEP:
            #WEP security
            output.append(u'\tkey_mgmt=NONE\n')
            output.append(u'\twep_key0=%s\n' % password)
            output.append(u'\twep_tx_keyidx=0\n')
        else:
            #unsecured network
            output.append(u'\tkey_mgmt=NONE\n')

        #footer
        output.append(u'}\n')

        #switch configuration file
        configurations = self.__get_configuration_files()
        if interface:
            self.CONF = configurations[interface]
        else:
            self.CONF = configurations[u'default']

        #write new network config
        return self.add_lines(output)

    def update_network_password(self, network, password, interface=None):
        """
        Update specified network password

        Args:
            network (string): network name (ssid)
            password (string): network password
            interface (string|None): if specified try to add network in specific interface wpa_supplicant.conf file

        Returns:
            bool: True if network password updated

        Raises:
            MissingParameter
        """
        #check params
        if network is None or len(network)==0:
            raise MissingParameter(u'Parameter network is missing')
        if password is None or len(password)==0:
            raise MissingParameter(u'Parameter password is missing')

        #first of all get network configuration
        config = self.get_configuration(network, interface)
        if config is None:
            return False

        #encrypt password if necessary
        if config[u'encryption'] in (self.ENCRYPTION_TYPE_WPA2, self.ENCRYPTION_TYPE_WPA):
            config[u'password'] = self.encrypt_password(network, password)
            self.logger.debug('Encrypt password %s: %s' % (password, config[u'password']))
        else:
            config[u'password'] = password

        #switch configuration file
        configurations = self.__get_configuration_files()
        if interface:
            self.CONF = configurations[interface]
        else:
            self.CONF = configurations[u'default']

        #delete existing entry
        if self.delete_network(network, interface):
            self.logger.debug('Config deleted')
            #and add new updated entry
            return self.__add_network(config, interface)

        return False

    def __update_network_disabled_flag(self, network, disabled, interface=None):
        """
        Update specified network disabled flag

        Args:
            network (string): network name (ssid)
            disabled (bool): disabled flag
            interface (string|None): if specified try to add network in specific interface wpa_supplicant.conf file

        Returns:
            bool: True if network flag updated
        """
        #check params
        if network is None or len(network)==0:
            raise MissingParameter(u'Parameter network is missing')
        if disabled is None: # pragma: no cover
            raise MissingParameter(u'Parameter disabled is missing')

        #first of all get network configuration
        config = self.get_configuration(network, interface)
        if config is None:
            return False

        #update disabled flag
        config[u'disabled'] = disabled

        #delete existing entry
        if self.delete_network(network, interface):
            #and add new updated entry
            return self.__add_network(config, interface)

        return False

    def enable_network(self, network, interface=None):
        """
        Enable network

        Args:
            network (string): network name
            interface (string|None): if specified try to add network in specific interface wpa_supplicant.conf file

        Returns:
            bool: True if network enabled

        Raises:
            MissingParameter
        """
        return self.__update_network_disabled_flag(network, False, interface=interface)

    def disable_network(self, network, interface=None):
        """
        Disable network

        Args:
            network (string): network name
            interface (string|None): if specified try to add network in specific interface wpa_supplicant.conf file

        Returns:
            bool: True if network disabled

        Raises:
            MissingParameter
        """
        return self.__update_network_disabled_flag(network, True, interface=interface)
