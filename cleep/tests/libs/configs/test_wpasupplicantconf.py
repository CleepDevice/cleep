#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from wpasupplicantconf import WpaSupplicantConf
from cleep.libs.internals.cleepfilesystem import CleepFilesystem
from cleep.libs.internals.console import Console
from cleep.exception import MissingParameter, InvalidParameter, CommandError
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from pprint import pprint
import io
from unittest.mock import Mock, patch, ANY, mock_open
import time

class TestsWpaSupplicantConf(unittest.TestCase):

    CONTENT_WITHOUT_COUNTRY = """ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network = {
    ssid="mynetwork1"
    psk="mypassword1"
}"""
    CONTENT_WITH_COUNTRY = """country=GB
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network = {
    ssid="mynetwork1"
    psk="mypassword1"
}
network={
    ssid="mynetwork2"
    scan_ssid=1
    #psk="helloworld"
    psk="mypassword2"
}
network={
        ssid="wepnetwork"
        key_mgmt=NONE
        wep_key0="12345"
        wep_tx_keyidx=0
}
network={
        ssid="wpanetwork"
        key_mgmt=WPA-PSK
        wep_key0="12345"
        wep_tx_keyidx=0
        disabled=1
}"""
    COUNTRY_SAMPLE = """FM      Micronesia
FO      Faroe Islands
FR      France
GA      Gabon
GB      Britain (UK)
#MO      Moon
KP      Korea (North)
KR      Korea (South)
GD      Grenada"""

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format='%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.fs = Mock()
        self.w = WpaSupplicantConf(self.fs)

    def tearDown(self):
        pass

    @patch('wpasupplicantconf.os.path.exists')
    def test_load_country_codes(self, mock_ospathexists):
        mock_ospathexists.return_value = True
        self.fs.read_data.return_value = self.COUNTRY_SAMPLE.split('\n')
        self.w._WpaSupplicantConf__load_country_codes()
        logging.debug('Country codes: %s' % self.w._WpaSupplicantConf__country_codes)

        self.assertCountEqual(self.w._WpaSupplicantConf__country_codes, {
            'micronesia': 'FM',
            'faroe islands': 'FO',
            'france': 'FR',
            'gabon': 'GA',
            'britain (uk)': 'GB',
            'grenada': 'GD',
            'korea (south)': 'KR',
            'korea (north)': 'KP',
        })

    @patch('wpasupplicantconf.os.path.exists')
    def test_load_country_codes_no_file(self, mock_ospathexists):
        mock_ospathexists.return_value = False
        self.fs.read_data.return_value = self.COUNTRY_SAMPLE.split('\n')
        self.w._WpaSupplicantConf__load_country_codes()
        logging.debug('Country codes: %s' % self.w._WpaSupplicantConf__country_codes)

        self.assertCountEqual(self.w._WpaSupplicantConf__country_codes, {})

    def test_save_default_config(self):
        self.w.save_default_config('wlan0')

        self.fs.write_data.assert_called_with('/etc/wpa_supplicant/wpa_supplicant-wlan0.conf', ANY)

    def test_save_default_config_no_interface(self):
        self.w.save_default_config(None)

        self.fs.write_data.assert_called_with('/etc/wpa_supplicant/wpa_supplicant.conf', ANY)

    @patch('wpasupplicantconf.os.path.exists')
    @patch('wpasupplicantconf.os.path.join')
    def test_has_config(self, mock_ospathjoin, mock_ospathexists):
        mock_ospathexists.return_value = True

        self.assertTrue(self.w.has_config('wlan0'))
        mock_ospathjoin.assert_called_with('/etc/wpa_supplicant', 'wpa_supplicant-wlan0.conf')

    @patch('wpasupplicantconf.os.path.exists')
    @patch('wpasupplicantconf.os.path.join')
    def test_has_config_no_interface(self, mock_ospathjoin, mock_ospathexists):
        mock_ospathexists.return_value = True

        self.assertTrue(self.w.has_config(None))
        mock_ospathjoin.assert_called_with('/etc/wpa_supplicant', 'wpa_supplicant.conf')

    @patch('wpasupplicantconf.os.listdir')
    @patch('wpasupplicantconf.os.path.isfile')
    def test_has_country(self, mock_ospathisfile, mock_oslistdir):
        mock_ospathisfile.return_value = True
        mock_oslistdir.return_value = ['wpa_supplicant-wlan0.conf', 'wpa_supplicant-wlan1.conf', 'wpa_supplicant.conf']
        self.fs.read_data.return_value = self.CONTENT_WITH_COUNTRY

        self.assertTrue(self.w.has_country('wlan0'))

    @patch('wpasupplicantconf.os.listdir')
    @patch('wpasupplicantconf.os.path.isfile')
    def test_has_country_without_country(self, mock_ospathisfile, mock_oslistdir):
        mock_ospathisfile.return_value = True
        mock_oslistdir.return_value = ['wpa_supplicant-wlan0.conf', 'wpa_supplicant-wlan1.conf', 'wpa_supplicant.conf']
        self.fs.read_data.return_value = self.CONTENT_WITHOUT_COUNTRY

        self.assertFalse(self.w.has_country('wlan0'))

    @patch('wpasupplicantconf.os.listdir')
    @patch('wpasupplicantconf.os.path.isfile')
    def test_has_country_invalid_interface(self, mock_ospathisfile, mock_oslistdir):
        mock_ospathisfile.return_value = True
        mock_oslistdir.return_value = ['wpa_supplicant-wlan0.conf', 'wpa_supplicant-wlan1.conf', 'wpa_supplicant.conf']
        self.fs.read_data.return_value = self.CONTENT_WITH_COUNTRY

        self.assertFalse(self.w.has_country('wlan3'))

    def test_set_country_replace_line(self):
        self.fs.read_data.return_value = self.COUNTRY_SAMPLE.split('\n')
        self.w.add_line = Mock(return_value=True)
        self.w.replace_line = Mock(return_value=True)

        self.w.set_country('france')
        
        self.w.replace_line.assert_called_with('^\s*country\s*=.*$', 'country=FR')
        self.assertFalse(self.w.add_line.called)

    def test_set_country_add_line(self):
        self.fs.read_data.return_value = self.COUNTRY_SAMPLE.split('\n')
        self.w.add_lines = Mock(return_value=True)
        self.w.replace_line = Mock(return_value=False)

        self.w.set_country('france')
        
        self.w.add_lines.assert_called_with(['country=FR\n'], end=False)
        self.w.replace_line.assert_called()
    
    def test_set_country_invalid_country(self):
        self.fs.read_data.return_value = self.COUNTRY_SAMPLE.split('\n')
        self.assertRaises(Exception, self.w.set_country, ['moon'])

    def test_set_country_empty_countries_file(self):
        self.fs.read_data.return_value = []
        with self.assertRaises(Exception) as cm:
            self.w.set_country('france')
        self.assertEqual(str(cm.exception), 'Invalid country code "france" specified')

    def test_set_country_no_countries_file(self):
        self.w.COUNTRIES_ISO3166 = ''
        with self.assertRaises(Exception) as cm:
            self.w.set_country('france')
        self.assertEqual(str(cm.exception), 'Invalid country code "france" specified')

    def test_set_country_alpha2(self):
        self.fs.read_data.return_value = self.COUNTRY_SAMPLE.split('\n')
        self.w.add_lines = Mock(return_value=True)
        self.w.replace_line = Mock(return_value=False)

        self.w.set_country_alpha2('FR')
        
        self.w.add_lines.assert_called_with(['country=FR\n'], end=False)
        self.w.replace_line.assert_called()

    def test_set_country_alpha2_invalid_alpha2(self):
        self.fs.read_data.return_value = []
        with self.assertRaises(Exception) as cm:
            self.w.set_country_alpha2('MO')
        self.assertEqual(str(cm.exception), 'Invalid country code "MO" specified')

    def test_encrypt_password(self):
        self.assertEqual(self.w.encrypt_password('mynetwork', 'mypassword'), '69e49214ef4e7e23d0ece077c2faf3c73f7522ad52a26b33527fa78d9033ff35')

    def test_encrypt_password_invalid_parameters(self):
        with self.assertRaises(MissingParameter) as cm:
            self.w.encrypt_password(None, 'mypassword')
        self.assertEqual(str(cm.exception), 'Parameter "network" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.w.encrypt_password('', 'mypassword')
        self.assertEqual(str(cm.exception), 'Parameter "network" is missing')

        with self.assertRaises(MissingParameter) as cm:
            self.w.encrypt_password('mynetwork', None)
        self.assertEqual(str(cm.exception), 'Parameter "password" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.w.encrypt_password('mynetwork', '')
        self.assertEqual(str(cm.exception), 'Parameter "password" is missing')
        with self.assertRaises(InvalidParameter) as cm:
            self.w.encrypt_password('mynetwork', 'azer')
        self.assertEqual(str(cm.exception), 'Parameter "password" must be 8..63 string length')
        with self.assertRaises(InvalidParameter) as cm:
            self.w.encrypt_password('mynetwork', 'azertyuiopqsdfghjklmwxcvbnazertyuiopqsdfghjklmwxcvbnazertyuiopqsdfghjklmwxcvbn')
        self.assertEqual(str(cm.exception), 'Parameter "password" must be 8..63 string length')

    @patch('wpasupplicantconf.Console')
    def test_encrypt_password_invalid_command(self, mock_console):
        mock_console.return_value.command.return_value = {
            'error': True,
            'killed': False,
            'stderr': 'error'
        }
        with self.assertRaises(Exception) as cm:
            self.w.encrypt_password('mynetwork', 'mypassword')
        self.assertEqual(str(cm.exception), 'Error with wpa_passphrase: unable to encrypt it')

        mock_console.return_value.command.return_value = {
            'error': False,
            'killed': True,
            'stderr': 'error'
        }
        with self.assertRaises(Exception) as cm:
            self.w.encrypt_password('mynetwork', 'mypassword')
        self.assertEqual(str(cm.exception), 'Error with wpa_passphrase: unable to encrypt it')

        mock_console.return_value.command.return_value = {
            'error': False,
            'killed': False,
            'stderr': 'error',
            'stdout': 'Error occured'
        }
        with self.assertRaises(Exception) as cm:
            self.w.encrypt_password('mynetwork', 'mypassword')
        self.assertEqual(str(cm.exception), 'Error with wpa_passphrase: invalid command output')

        mock_console.return_value.command.return_value = {
            'error': False,
            'killed': False,
            'stderr': ['error'],
            'stdout': ['network={\nssid="mynetwork"}']
        }
        with self.assertRaises(Exception) as cm:
            self.w.encrypt_password('mynetwork', 'mypassword')
        self.assertEqual(str(cm.exception), 'No password generated by wpa_passphrase command')

    @patch('wpasupplicantconf.Console')
    def test_wpa_passphrase(self, mock_console):
        mock_console.return_value.command.return_value = {
            'error': False,
            'killed': False,
            'stderr': [''],
            'stdout': [
                'network={',
                '    ssid="dummy"',
                '    #psk="password"',
                '    psk=1234567890',
                '}',
            ],
        }
        
        output = self.w.wpa_passphrase('dummy', 'password')
        logging.debug('Output: %s' % output)

        self.assertListEqual(output, ['network={\n', '    ssid="dummy"\n', '    psk=1234567890\n', '}\n'])

    @patch('wpasupplicantconf.Console')
    def test_wpa_passphrase_invalid_command_output(self, mock_console):
        mock_console.return_value.command.return_value = {
            'error': False,
            'killed': False,
            'stderr': [''],
            'stdout': [
                'ssid="dummy"',
                '#psk="password"',
                'psk=1234567890',
            ],
        }

        with self.assertRaises(Exception) as cm:
            output = self.w.wpa_passphrase('dummy', 'password')
        self.assertEqual(str(cm.exception), 'Error with wpa_passphrase: invalid command output')

    @patch('wpasupplicantconf.Console')
    def test_wpa_passphrase_command_failed(self, mock_console):
        mock_console.return_value.command.return_value = {
            'error': True,
            'killed': False,
            'stderr': [''],
            'stdout': [
                'Passphrase must be 8..63 characters',
            ],
        }

        with self.assertRaises(Exception) as cm:
            output = self.w.wpa_passphrase('dummy', 'password')
        self.assertEqual(str(cm.exception), 'Error with wpa_passphrase: unable to encrypt it')

    def test_wpa_passphrase_invalid_params(self):
        with self.assertRaises(MissingParameter) as cm:
            self.w.wpa_passphrase(None, 'azerty')
        self.assertEqual(str(cm.exception), 'Parameter "network" is missing')

        with self.assertRaises(MissingParameter) as cm:
            self.w.wpa_passphrase('', 'azerty')
        self.assertEqual(str(cm.exception), 'Parameter "network" is missing')

        with self.assertRaises(InvalidParameter) as cm:
            self.w.wpa_passphrase('dummy', 'azerty')
        self.assertEqual(str(cm.exception), 'Parameter "password" must be 8..63 string length')

    @patch('wpasupplicantconf.os.listdir')
    @patch('wpasupplicantconf.os.path.isfile')
    def test_get_configuration_files(self, mock_ospathisfile, mock_oslistdir):
        mock_ospathisfile.return_value = True
        mock_oslistdir.return_value = ['wpa_supplicant-wlan0.conf', 'wpa_supplicant-wlan1.conf', 'wpa_supplicant.conf']
        self.fs.read_data.return_value = self.CONTENT_WITH_COUNTRY

        files = self.w._WpaSupplicantConf__get_configuration_files()
        logging.debug('Files: %s' % files)

        self.assertCountEqual(files, {
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'wlan1': '/etc/wpa_supplicant/wpa_supplicant-wlan1.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })

    @patch('wpasupplicantconf.os.path.exists')
    def test_private_get_configuration(self, mock_ospathexists):
        mock_ospathexists.return_value = True
        self.fs.open = mock_open(read_data=self.CONTENT_WITH_COUNTRY)

        config = self.w._WpaSupplicantConf__get_configuration('dummyfile', 'wlan0')
        logging.debug('Config: %s' % config)

        self.maxDiff = None
        self.assertDictEqual(config, {
            'mynetwork1': {
                'network': 'mynetwork1',
                'password': 'mypassword1',
                'hidden': False,
                'encryption': 'wpa2',
                'disabled': False
            },
            'mynetwork2': {
                'network': 'mynetwork2',
                'password': 'mypassword2',
                'hidden': True,
                'encryption': 'wpa2',
                'disabled': False
            },
            'wepnetwork': {
                'network': 'wepnetwork',
                'password': '12345',
                'hidden': False,
                'encryption': 'wep',
                'disabled': False
            },
            'wpanetwork': {
                'network': 'wpanetwork',
                'password': '12345',
                'hidden': False,
                'encryption': 'wpa2',
                'disabled': True
            }
        })
        self.assertEqual(self.w.DEFAULT_CONF, self.w.CONF)

    def test_get_configurations(self):
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        self.w._WpaSupplicantConf__get_configuration = Mock(side_effect=[{'k1': 'v1'}, {'k2': 'v2'}])

        configs = self.w.get_configurations()
        logging.debug(configs)
        self.assertEqual(len(configs), 2)
        self.assertTrue('default' in configs)
        self.assertDictEqual(configs['wlan0'], {'k1': 'v1'})
        self.assertDictEqual(configs['default'], {'k2': 'v2'})

    def test_get_configurations_no_config(self):
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={})

        configs = self.w.get_configurations()

        self.assertDictEqual(configs, {})

    def test_get_configuration(self):
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        wepnetwork_conf = {
            'network': 'wepnetwork',
            'password': '12345',
            'hidden': False,
            'encryption': 'wep',
            'disabled': False,
        }
        self.w._WpaSupplicantConf__get_configuration = Mock(side_effect=[{'wepnetwork': wepnetwork_conf}, {'default': {'k2': 'v2'}}])

        config = self.w.get_configuration('wepnetwork', 'wlan0')
        logging.debug('Config: %s' % config)
        self.assertDictEqual(config, {
            'network': 'wepnetwork',
            'password': '12345',
            'hidden': False,
            'encryption': 'wep',
            'disabled': False,
        })

    def test_get_configuration_no_config(self):
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        wepnetwork_conf = {
            'network': 'wepnetwork',
            'password': '12345',
            'hidden': False,
            'encryption': 'wep',
            'disabled': False,
        }
        self.w._WpaSupplicantConf__get_configuration = Mock(side_effect=[{'wepnetwork': wepnetwork_conf}, {'default': {'k2': 'v2'}}])

        config = self.w.get_configuration('wepnetwork', 'wlan0')
        logging.debug('Config: %s' % config)
        self.assertIsNone(config)

    def test_get_configuration_no_network(self):
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        self.w._WpaSupplicantConf__get_configuration = Mock(side_effect=[{}, {'default': {'k2': 'v2'}}])

        config = self.w.get_configuration('wepnetwork', 'wlan0')
        logging.debug('Config: %s' % config)
        self.assertIsNone(config)

    def test_get_configuration_fallback_default(self):
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        wepnetwork_conf = {
            'network': 'wepnetwork',
            'password': '12345',
            'hidden': False,
            'encryption': 'wep',
            'disabled': False,
        }
        self.w._WpaSupplicantConf__get_configuration = Mock(return_value={'wepnetwork': wepnetwork_conf})

        config = self.w.get_configuration('wepnetwork')
        logging.debug('Config: %s' % config)
        self.assertDictEqual(config, wepnetwork_conf)

    def test_get_configuration_fallback_no_config(self):
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
        })
        wepnetwork_conf = {
            'network': 'wepnetwork',
            'password': '12345',
            'hidden': False,
            'encryption': 'wep',
            'disabled': False,
        }
        self.w._WpaSupplicantConf__get_configuration = Mock(return_value={'wepnetwork': wepnetwork_conf})

        config = self.w.get_configuration('wepnetwork')
        logging.debug('Config: %s' % config)
        self.assertIsNone(config)

    def test_get_configuration_fallback_no_network(self):
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        self.w._WpaSupplicantConf__get_configuration = Mock(return_value={})

        config = self.w.get_configuration('wepnetwork')
        logging.debug('Config: %s' % config)
        self.assertIsNone(config)

    def test_delete_network_existing_network(self):
        network_conf = {
            'network': 'network',
            'password': '12345',
            'hidden': False,
            'encryption': 'wep',
            'disabled': False,
        }
        self.w.get_configuration = Mock(return_value=network_conf)
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        self.w._WpaSupplicantConf__groups = {
            'default': {'network': 'default_group'},
            'wlan0': {'network': 'wlan0_group'},
        }
        self.w.remove = Mock(return_value=True)
        self.w._WpaSupplicantConf__restore_conf = Mock()

        self.assertTrue(self.w.delete_network('network', 'wlan0'))

        self.w.remove.assert_called_with('wlan0_group')
        self.w._WpaSupplicantConf__restore_conf.assert_called()

    def test_delete_network_unknown_network(self):
        self.w.get_configuration = Mock(return_value=None)
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        self.w._WpaSupplicantConf__groups = {
            'default': {'network': 'default_group'},
            'wlan0': {'network': 'wlan0_group'},
        }
        self.w.remove = Mock(return_value=True)
        self.w._WpaSupplicantConf__restore_conf = Mock()

        self.assertFalse(self.w.delete_network('unknownnetwork', 'wlan0'))

        self.assertFalse(self.w.remove.called)
        self.assertFalse(self.w._WpaSupplicantConf__restore_conf.called)

    def test_delete_network_existing_network_default(self):
        network_conf = {
            'network': 'network',
            'password': '12345',
            'hidden': False,
            'encryption': 'wep',
            'disabled': False,
        }
        self.w.get_configuration = Mock(return_value=network_conf)
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        self.w._WpaSupplicantConf__groups = {
            'default': {'network': 'default_group'},
            'wlan0': {'network': 'wlan0_group'},
        }
        self.w.remove = Mock(return_value=True)
        self.w._WpaSupplicantConf__restore_conf = Mock()

        self.assertTrue(self.w.delete_network('network'))

        self.w.remove.assert_called_with('default_group')
        self.w._WpaSupplicantConf__restore_conf.assert_called()

    def test_delete_network_invalid_params(self):
        with self.assertRaises(MissingParameter) as cm:
            self.w.delete_network('')
        self.assertEqual(str(cm.exception), 'Parameter "network" is missing')

        with self.assertRaises(MissingParameter) as cm:
            self.w.delete_network(None)
        self.assertEqual(str(cm.exception), 'Parameter "network" is missing')

    def test_private_add_network(self):
        self.w.add_lines = Mock()

        self.w._WpaSupplicantConf__add_network({
            'network': 'network',
            'encryption': 'wpa2',
            'password': 'mypassword',
            'hidden': True,
            'disabled': True,
        }, 'wlan0')

        self.w.add_lines.assert_called_with([
            '\nnetwork={\n',
            '\tssid="network"\n',
            '\tkey_mgmt=WPA-PSK\n',
            '\tpsk=mypassword\n',
            '\tscan_ssid=1\n',
            '\tdisabled=1\n',
            '}\n',
        ])

    def test_add_network_wep(self):
        self.w.get_configuration = Mock(return_value=None)
        self.w.has_config = Mock(return_value=True)
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        self.w.add_lines = Mock()
        self.w._WpaSupplicantConf__restore_conf = Mock()

        self.assertTrue(self.w.add_network('network', 'wep', 'password', interface='wlan0'))

        self.w.add_lines.assert_called_with([
            '\nnetwork={\n',
            '\tssid="network"\n',
            '\tkey_mgmt=NONE\n',
            '\twep_key0=password\n',
            '\twep_tx_keyidx=0\n',
            '}\n'
        ])
        self.w._WpaSupplicantConf__restore_conf.assert_called()
        self.w.has_config.assert_called_with('wlan0')

    def test_add_network_wpa(self):
        self.w.get_configuration = Mock(return_value=None)
        self.w.has_config = Mock(return_value=True)
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        self.w.add_lines = Mock()
        self.w._WpaSupplicantConf__restore_conf = Mock()

        self.assertTrue(self.w.add_network('network', 'wpa', 'password', interface='wlan0'))

        self.w.add_lines.assert_called_with([
            '\nnetwork={\n',
            '\tssid="network"\n',
            '\tkey_mgmt=WPA-PSK\n',
            '\tpsk=e2e04dcb82891a286e5d524b63f4963ac1f8dc49852bd6b97441d9545054d270\n',
            '}\n'
        ])
        self.w._WpaSupplicantConf__restore_conf.assert_called()
        self.w.has_config.assert_called_with('wlan0')

    def test_add_network_wpa_no_encryption(self):
        self.w.get_configuration = Mock(return_value=None)
        self.w.has_config = Mock(return_value=True)
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        self.w.add_lines = Mock()
        self.w._WpaSupplicantConf__restore_conf = Mock()

        self.assertTrue(self.w.add_network('network', 'wpa', 'password', interface='wlan0', encrypt_password=False))

        self.w.add_lines.assert_called_with([
            '\nnetwork={\n',
            '\tssid="network"\n',
            '\tkey_mgmt=WPA-PSK\n',
            '\tpsk=password\n',
            '}\n'
        ])
        self.w._WpaSupplicantConf__restore_conf.assert_called()
        self.w.has_config.assert_called_with('wlan0')

    def test_add_network_wpa2(self):
        self.w.get_configuration = Mock(return_value=None)
        self.w.has_config = Mock(return_value=True)
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        self.w.add_lines = Mock()
        self.w._WpaSupplicantConf__restore_conf = Mock()

        self.assertTrue(self.w.add_network('network', 'wpa2', 'password', interface='wlan0'))

        self.w.add_lines.assert_called_with([
            '\nnetwork={\n',
            '\tssid="network"\n',
            '\tkey_mgmt=WPA-PSK\n',
            '\tpsk=e2e04dcb82891a286e5d524b63f4963ac1f8dc49852bd6b97441d9545054d270\n',
            '}\n'
        ])
        self.w._WpaSupplicantConf__restore_conf.assert_called()
        self.w.has_config.assert_called_with('wlan0')

    def test_add_network_wpa2_no_encryption(self):
        self.w.get_configuration = Mock(return_value=None)
        self.w.has_config = Mock(return_value=True)
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        self.w.add_lines = Mock()
        self.w._WpaSupplicantConf__restore_conf = Mock()

        self.assertTrue(self.w.add_network('network', 'wpa', 'password', interface='wlan0', encrypt_password=False))

        self.w.add_lines.assert_called_with([
            '\nnetwork={\n',
            '\tssid="network"\n',
            '\tkey_mgmt=WPA-PSK\n',
            '\tpsk=password\n',
            '}\n'
        ])
        self.w._WpaSupplicantConf__restore_conf.assert_called()
        self.w.has_config.assert_called_with('wlan0')

    def test_add_network_unsecured(self):
        self.w.get_configuration = Mock(return_value=None)
        self.w.has_config = Mock(return_value=True)
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        self.w.add_lines = Mock()
        self.w._WpaSupplicantConf__restore_conf = Mock()

        self.assertTrue(self.w.add_network('network', 'unsecured', 'password', interface='wlan0'))

        self.w.add_lines.assert_called_with([
            '\nnetwork={\n',
            '\tssid="network"\n',
            '\tkey_mgmt=NONE\n',
            '}\n'
        ])
        self.w._WpaSupplicantConf__restore_conf.assert_called()
        self.w.has_config.assert_called_with('wlan0')

    def test_add_network_hidden(self):
        self.w.get_configuration = Mock(return_value=None)
        self.w.has_config = Mock(return_value=True)
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        self.w.add_lines = Mock()
        self.w._WpaSupplicantConf__restore_conf = Mock()

        self.assertTrue(self.w.add_network('network', 'wep', 'password', hidden=True, interface='wlan0'))

        self.w.add_lines.assert_called_with([
            '\nnetwork={\n',
            '\tssid="network"\n',
            '\tkey_mgmt=NONE\n',
            '\twep_key0=password\n',
            '\twep_tx_keyidx=0\n',
            '\tscan_ssid=1\n',
            '}\n'
        ])
        self.w._WpaSupplicantConf__restore_conf.assert_called()
        self.w.has_config.assert_called_with('wlan0')

    def test_add_network_create_default_conf(self):
        self.w.get_configuration = Mock(return_value=None)
        self.w.has_config = Mock(return_value=False)
        self.w.save_default_config = Mock()
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        self.w.add_lines = Mock()
        self.w._WpaSupplicantConf__restore_conf = Mock()

        self.assertTrue(self.w.add_network('network', 'wep', 'password', hidden=True, interface='wlan0'))

        self.w.save_default_config.assert_called_with('wlan0')

    def test_add_network_failed(self):
        self.w.get_configuration = Mock(return_value=None)
        self.w.has_config = Mock(return_value=True)
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        self.w.add_lines = Mock(return_value=False)
        self.w._WpaSupplicantConf__restore_conf = Mock()

        self.assertFalse(self.w.add_network('network', 'wep', 'password', interface='wlan0'))

        self.w.add_lines.assert_called_with([
            '\nnetwork={\n',
            '\tssid="network"\n',
            '\tkey_mgmt=NONE\n',
            '\twep_key0=password\n',
            '\twep_tx_keyidx=0\n',
            '}\n'
        ])
        self.w._WpaSupplicantConf__restore_conf.assert_called()
        self.w.has_config.assert_called_with('wlan0')

    def test_add_network_already_configured(self):
        network_conf = {
            'network': 'network',
            'password': '12345',
            'hidden': False,
            'encryption': 'wep',
            'disabled': False,
        }
        self.w.get_configuration = Mock(return_value=network_conf)
        self.w.add_lines = Mock()

        with self.assertRaises(InvalidParameter) as cm:
            self.w.add_network('network', 'wep', 'password', interface='wlan0')
        self.assertEqual(str(cm.exception), 'Network "network" is already configured')
        self.assertFalse(self.w.add_lines.called)

    def test_add_network_default(self):
        self.w.get_configuration = Mock(return_value=None)
        self.w.has_config = Mock(return_value=True)
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        self.w.add_lines = Mock()
        self.w._WpaSupplicantConf__restore_conf = Mock()

        self.assertTrue(self.w.add_network('network', 'wep', 'password'))

        self.w.has_config.assert_called_with(None)
        self.w.add_lines.assert_called_with([
            '\nnetwork={\n',
            '\tssid="network"\n',
            '\tkey_mgmt=NONE\n',
            '\twep_key0=password\n',
            '\twep_tx_keyidx=0\n',
            '}\n'
        ])
        self.w._WpaSupplicantConf__restore_conf.assert_called()

    def test_add_network_check_parameters(self):
        with self.assertRaises(MissingParameter) as cm:
            self.w.add_network('', 'wpa', 'pwd')
        self.assertEqual(str(cm.exception), 'Parameter "network" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.w.add_network(None, 'wpa', 'pwd')
        self.assertEqual(str(cm.exception), 'Parameter "network" is missing')

        with self.assertRaises(MissingParameter) as cm:
            self.w.add_network('network', '', 'pwd')
        self.assertEqual(str(cm.exception), 'Parameter "encryption" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.w.add_network('network', None, 'pwd')
        self.assertEqual(str(cm.exception), 'Parameter "encryption" is missing')
        with self.assertRaises(InvalidParameter) as cm:
            self.w.add_network('network', 'test', 'pwd')
        self.assertEqual(str(cm.exception), 'Parameter "encryption" is invalid (available: wpa,wpa2,wep,unsecured,unknown)')

        with self.assertRaises(MissingParameter) as cm:
            self.w.add_network('network', 'wpa', '')
        self.assertEqual(str(cm.exception), 'Parameter "password" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.w.add_network('network', 'wpa2', '')
        self.assertEqual(str(cm.exception), 'Parameter "password" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.w.add_network('network', 'wep', '')
        self.assertEqual(str(cm.exception), 'Parameter "password" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.w.add_network('network', 'unknown', '')
        self.assertEqual(str(cm.exception), 'Parameter "password" is missing')

    def test_update_network_password_wep(self):
        network_conf = {
            'network': 'network',
            'password': '12345',
            'hidden': False,
            'encryption': 'wep',
            'disabled': False,
        }
        self.w.get_configuration = Mock(return_value=network_conf)
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        self.w._WpaSupplicantConf__groups = {
            'default': {'network': 'default_group'},
            'wlan0': {'network': 'wlan0_group'},
        }
        self.w.add_lines = Mock()
        self.w.remove = Mock()
        self.w._WpaSupplicantConf__restore_conf = Mock()
        self.w.delete_network = Mock()
        self.w._WpaSupplicantConf__add_network = Mock()

        self.assertTrue(self.w.update_network_password('network', 'password', interface='wlan0'))

        self.w.delete_network.assert_called_with('network', 'wlan0')
        self.w._WpaSupplicantConf__add_network.assert_called_with({
            'network': 'network',
            'password': 'password',
            'hidden': False,
            'encryption': 'wep',
            'disabled': False,
        }, 'wlan0')
        self.w._WpaSupplicantConf__restore_conf.assert_called()

    def test_update_network_password_wpa(self):
        network_conf = {
            'network': 'network',
            'password': '12345',
            'hidden': False,
            'encryption': 'wpa',
            'disabled': False,
        }
        self.w.get_configuration = Mock(return_value=network_conf)
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        self.w._WpaSupplicantConf__groups = {
            'default': {'network': 'default_group'},
            'wlan0': {'network': 'wlan0_group'},
        }
        self.w.add_lines = Mock()
        self.w.remove = Mock()
        self.w._WpaSupplicantConf__restore_conf = Mock()
        self.w.delete_network = Mock()
        self.w._WpaSupplicantConf__add_network = Mock()

        self.assertTrue(self.w.update_network_password('network', 'password', interface='wlan0'))

        self.w.delete_network.assert_called_with('network', 'wlan0')
        self.w._WpaSupplicantConf__add_network.assert_called_with({
            'network': 'network',
            'password': 'e2e04dcb82891a286e5d524b63f4963ac1f8dc49852bd6b97441d9545054d270',
            'hidden': False,
            'encryption': 'wpa',
            'disabled': False,
        }, 'wlan0')
        self.w._WpaSupplicantConf__restore_conf.assert_called()

    def test_update_network_password_wpa2(self):
        network_conf = {
            'network': 'network',
            'password': '12345',
            'hidden': False,
            'encryption': 'wpa2',
            'disabled': False,
        }
        self.w.get_configuration = Mock(return_value=network_conf)
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        self.w._WpaSupplicantConf__groups = {
            'default': {'network': 'default_group'},
            'wlan0': {'network': 'wlan0_group'},
        }
        self.w.add_lines = Mock()
        self.w.remove = Mock()
        self.w._WpaSupplicantConf__restore_conf = Mock()
        self.w.delete_network = Mock()
        self.w._WpaSupplicantConf__add_network = Mock()

        self.assertTrue(self.w.update_network_password('network', 'password', interface='wlan0'))

        self.w.delete_network.assert_called_with('network', 'wlan0')
        self.w._WpaSupplicantConf__add_network.assert_called_with({
            'network': 'network',
            'password': 'e2e04dcb82891a286e5d524b63f4963ac1f8dc49852bd6b97441d9545054d270',
            'hidden': False,
            'encryption': 'wpa2',
            'disabled': False,
        }, 'wlan0')
        self.w._WpaSupplicantConf__restore_conf.assert_called()

    def test_update_network_password_unsecured(self):
        network_conf = {
            'network': 'network',
            'password': 'toto',
            'hidden': False,
            'encryption': 'unsecured',
            'disabled': False,
        }
        self.w.get_configuration = Mock(return_value=network_conf)
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        self.w._WpaSupplicantConf__groups = {
            'default': {'network': 'default_group'},
            'wlan0': {'network': 'wlan0_group'},
        }
        self.w.add_lines = Mock()
        self.w.remove = Mock()
        self.w._WpaSupplicantConf__restore_conf = Mock()
        self.w.delete_network = Mock()
        self.w._WpaSupplicantConf__add_network = Mock()

        self.assertFalse(self.w.update_network_password('network', 'password', interface='wlan0'))

        self.assertFalse(self.w.delete_network.called)
        self.assertFalse(self.w._WpaSupplicantConf__add_network.called)
        self.assertFalse(self.w._WpaSupplicantConf__restore_conf.called)

    def test_update_network_password_default(self):
        network_conf = {
            'network': 'network',
            'password': '12345',
            'hidden': False,
            'encryption': 'wep',
            'disabled': False,
        }
        self.w.get_configuration = Mock(return_value=network_conf)
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        self.w._WpaSupplicantConf__groups = {
            'default': {'network': 'default_group'},
            'wlan0': {'network': 'wlan0_group'},
        }
        self.w.add_lines = Mock()
        self.w.remove = Mock()
        self.w._WpaSupplicantConf__restore_conf = Mock()
        self.w.delete_network = Mock()
        self.w._WpaSupplicantConf__add_network = Mock()

        self.assertTrue(self.w.update_network_password('network', 'password'))

        self.w.delete_network.assert_called_with('network', None)
        self.w._WpaSupplicantConf__add_network.assert_called_with({
            'network': 'network',
            'password': 'password',
            'hidden': False,
            'encryption': 'wep',
            'disabled': False,
        }, None)
        self.w._WpaSupplicantConf__restore_conf.assert_called()

    def test_update_network_password_no_config(self):
        self.w.get_configuration = Mock(return_value=None)
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        self.w._WpaSupplicantConf__groups = {
            'default': {'network': 'default_group'},
            'wlan0': {'network': 'wlan0_group'},
        }
        self.w.add_lines = Mock()
        self.w.remove = Mock()
        self.w._WpaSupplicantConf__restore_conf = Mock()
        self.w.delete_network = Mock()
        self.w._WpaSupplicantConf__add_network = Mock()

        with self.assertRaises(InvalidParameter) as cm:
            self.assertTrue(self.w.update_network_password('network', 'password', interface='wlan0'))
        self.assertEqual(str(cm.exception), 'Network "network" is not configured')

        self.assertFalse(self.w.delete_network.called)
        self.assertFalse(self.w._WpaSupplicantConf__add_network.called)
        self.assertFalse(self.w._WpaSupplicantConf__restore_conf.called)

    def test_update_network_password_delete_network_failed(self):
        network_conf = {
            'network': 'network',
            'password': '12345',
            'hidden': False,
            'encryption': 'wep',
            'disabled': False,
        }
        self.w.get_configuration = Mock(return_value=network_conf)
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        self.w._WpaSupplicantConf__groups = {
            'default': {'network': 'default_group'},
            'wlan0': {'network': 'wlan0_group'},
        }
        self.w.add_lines = Mock()
        self.w.remove = Mock()
        self.w._WpaSupplicantConf__restore_conf = Mock()
        self.w.delete_network = Mock(return_value=False)
        self.w._WpaSupplicantConf__add_network = Mock()

        self.assertFalse(self.w.update_network_password('network', 'password', interface='wlan0'))

        self.w.delete_network.assert_called_with('network', 'wlan0')
        self.assertFalse(self.w._WpaSupplicantConf__add_network.called)
        self.w._WpaSupplicantConf__restore_conf.assert_called()

    def test_update_network_password_add_network_failed(self):
        network_conf = {
            'network': 'network',
            'password': '12345',
            'hidden': False,
            'encryption': 'wep',
            'disabled': False,
        }
        self.w.get_configuration = Mock(return_value=network_conf)
        self.w._WpaSupplicantConf__get_configuration_files = Mock(return_value={
            'wlan0': '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf',
            'default': '/etc/wpa_supplicant/wpa_supplicant.conf',
        })
        self.w._WpaSupplicantConf__groups = {
            'default': {'network': 'default_group'},
            'wlan0': {'network': 'wlan0_group'},
        }
        self.w.add_lines = Mock()
        self.w.remove = Mock()
        self.w._WpaSupplicantConf__restore_conf = Mock()
        self.w.delete_network = Mock()
        self.w._WpaSupplicantConf__add_network = Mock(return_value=False)

        self.assertFalse(self.w.update_network_password('network', 'password', interface='wlan0'))

        self.w.delete_network.assert_called_with('network', 'wlan0')
        self.w._WpaSupplicantConf__add_network.assert_called()
        self.w._WpaSupplicantConf__restore_conf.assert_called()

    def test_update_network_password_check_parameters(self):
        with self.assertRaises(MissingParameter) as cm:
            self.w.update_network_password('', 'newpassword', 'wlan0')
        self.assertEqual(str(cm.exception), 'Parameter "network" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.w.update_network_password(None, 'newpassword', 'wlan0')
        self.assertEqual(str(cm.exception), 'Parameter "network" is missing')

        with self.assertRaises(MissingParameter) as cm:
            self.w.update_network_password('network', '', 'wlan0')
        self.assertEqual(str(cm.exception), 'Parameter "password" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.w.update_network_password('network', None, 'wlan0')
        self.assertEqual(str(cm.exception), 'Parameter "password" is missing')

    def test_update_network_disabled_flag_disable(self):
        network_conf = {
            'network': 'network',
            'password': '12345',
            'hidden': False,
            'encryption': 'wep',
            'disabled': False,
        }
        self.w.get_configuration = Mock(return_value=network_conf)
        self.w.delete_network = Mock()
        self.w._WpaSupplicantConf__add_network = Mock()

        self.assertTrue(self.w._WpaSupplicantConf__update_network_disabled_flag('network', True, interface='wlan0'))

        self.w.delete_network.assert_called_with('network', 'wlan0')
        self.w._WpaSupplicantConf__add_network.assert_called_with({
            'network': 'network',
            'password': '12345',
            'hidden': False,
            'encryption': 'wep',
            'disabled': True
        }, 'wlan0')

    def test_update_network_disabled_flag_enable(self):
        network_conf = {
            'network': 'network',
            'password': '12345',
            'hidden': False,
            'encryption': 'wep',
            'disabled': True,
        }
        self.w.get_configuration = Mock(return_value=network_conf)
        self.w.delete_network = Mock()
        self.w._WpaSupplicantConf__add_network = Mock()

        self.assertTrue(self.w._WpaSupplicantConf__update_network_disabled_flag('network', False, interface='wlan0'))

        self.w.delete_network.assert_called_with('network', 'wlan0')
        self.w._WpaSupplicantConf__add_network.assert_called_with({
            'network': 'network',
            'password': '12345',
            'hidden': False,
            'encryption': 'wep',
            'disabled': False
        }, 'wlan0')

    def test_update_network_disabled_flag_delete_network_failed(self):
        network_conf = {
            'network': 'network',
            'password': '12345',
            'hidden': False,
            'encryption': 'wep',
            'disabled': False,
        }
        self.w.get_configuration = Mock(return_value=network_conf)
        self.w.delete_network = Mock(return_value=False)
        self.w._WpaSupplicantConf__add_network = Mock()

        self.assertFalse(self.w._WpaSupplicantConf__update_network_disabled_flag('network', True, interface='wlan0'))

        self.w.delete_network.assert_called_with('network', 'wlan0')
        self.assertFalse(self.w._WpaSupplicantConf__add_network.called)

    def test_update_network_disabled_flag_add_network_failed(self):
        network_conf = {
            'network': 'network',
            'password': '12345',
            'hidden': False,
            'encryption': 'wep',
            'disabled': False,
        }
        self.w.get_configuration = Mock(return_value=network_conf)
        self.w.delete_network = Mock()
        self.w._WpaSupplicantConf__add_network = Mock(return_value=False)

        self.assertFalse(self.w._WpaSupplicantConf__update_network_disabled_flag('network', True, interface='wlan0'))

        self.w.delete_network.assert_called_with('network', 'wlan0')
        self.w._WpaSupplicantConf__add_network.assert_called_with({
            'network': 'network',
            'password': '12345',
            'hidden': False,
            'encryption': 'wep',
            'disabled': True
        }, 'wlan0')

    def test_update_network_disabled_flag_default(self):
        network_conf = {
            'network': 'network',
            'password': '12345',
            'hidden': False,
            'encryption': 'wep',
            'disabled': False,
        }
        self.w.get_configuration = Mock(return_value=network_conf)
        self.w.delete_network = Mock()
        self.w._WpaSupplicantConf__add_network = Mock()

        self.assertTrue(self.w._WpaSupplicantConf__update_network_disabled_flag('network', True))

        self.w.delete_network.assert_called_with('network', None)
        self.w._WpaSupplicantConf__add_network.assert_called_with({
            'network': 'network',
            'password': '12345',
            'hidden': False,
            'encryption': 'wep',
            'disabled': True
        }, None)

    def test_update_network_disabled_flag_no_config(self):
        self.w.get_configuration = Mock(return_value=None)
        self.w.delete_network = Mock()
        self.w._WpaSupplicantConf__add_network = Mock()

        self.assertFalse(self.w._WpaSupplicantConf__update_network_disabled_flag('network', True))

        self.assertFalse(self.w.delete_network.called)
        self.assertFalse(self.w._WpaSupplicantConf__add_network.called)

    def test_update_network_disabled_flag_check_parameters(self):
        with self.assertRaises(MissingParameter) as cm:
            self.w._WpaSupplicantConf__update_network_disabled_flag('', True)
        self.assertEqual(str(cm.exception), 'Parameter "network" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.w._WpaSupplicantConf__update_network_disabled_flag(None, True)
        self.assertEqual(str(cm.exception), 'Parameter "network" is missing')

        with self.assertRaises(InvalidParameter) as cm:
            self.w._WpaSupplicantConf__update_network_disabled_flag('netork', 123)
        self.assertEqual(str(cm.exception), 'Parameter "disabled" is invalid')

    def test_enable_network(self):
        self.w._WpaSupplicantConf__update_network_disabled_flag = Mock()

        self.w.enable_network('network', interface='wlan0')

        self.w._WpaSupplicantConf__update_network_disabled_flag.assert_called_with('network', False, interface='wlan0')

    def test_enable_network_default(self):
        self.w._WpaSupplicantConf__update_network_disabled_flag = Mock()

        self.w.enable_network('network')

        self.w._WpaSupplicantConf__update_network_disabled_flag.assert_called_with('network', False, interface=None)

    def test_disable_network(self):
        self.w._WpaSupplicantConf__update_network_disabled_flag = Mock()

        self.w.disable_network('network', interface='wlan0')

        self.w._WpaSupplicantConf__update_network_disabled_flag.assert_called_with('network', True, interface='wlan0')

    def test_disable_network_default(self):
        self.w._WpaSupplicantConf__update_network_disabled_flag = Mock()

        self.w.disable_network('network')

        self.w._WpaSupplicantConf__update_network_disabled_flag.assert_called_with('network', True, interface=None)


if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_wpasupplicantconf.py; coverage report -m -i
    unittest.main()

