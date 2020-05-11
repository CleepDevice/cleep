#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from wpasupplicantconf import WpaSupplicantConf
from raspiot.libs.internals.cleepfilesystem import CleepFilesystem
from raspiot.libs.internals.console import Console
from raspiot.exception import MissingParameter, InvalidParameter, CommandError
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
from pprint import pprint
import io
from unittest.mock import Mock
import time

class WpaSupplicantConfTestsValidConf(unittest.TestCase):

    FILE_NAME = 'wpa_supplicant.conf'
    CONTENT = u"""country=GB
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
}"""

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.path = os.path.join(os.getcwd(), self.FILE_NAME)
        logging.debug('Using conf file "%s"' % self.path)

        #fill with default content
        with io.open(self.path, 'w') as f:
            f.write(self.CONTENT)

        w = WpaSupplicantConf
        w.WPASUPPLICANT_DIR = os.path.abspath('./')
        w.DEFAULT_CONF = 'wpa_supplicant.conf'
        self.w = w(self.fs)

    def tearDown(self):
        if os.path.exists('%s' % self.FILE_NAME):
            os.remove('%s' % self.FILE_NAME)

    def test_set_country(self):
        self.w.set_country('france')
    
    def test_set_country_invalid_code(self):
        self.assertRaises(Exception, self.w.set_country, ['moon'])

    def test_set_country_no_countries_file(self):
        self.w.COUNTRIES_ISO3166 = ''
        with self.assertRaises(Exception) as cm:
            self.w.set_country('france')
        self.assertEqual(str(cm.exception), 'Invalid country code "france" specified')

    def test_set_country_empty_countries_file(self):
        with io.open(self.path, 'w') as f:
            f.write(u'')
        self.w.COUNTRIES_ISO3166 = self.path
        with self.assertRaises(Exception) as cm:
            self.w.set_country('france')
        self.assertEqual(str(cm.exception), 'Invalid country code "france" specified')

    def test_encrypt_password(self):
        self.assertEqual(self.w.encrypt_password('mynetwork', 'mypassword'), '69e49214ef4e7e23d0ece077c2faf3c73f7522ad52a26b33527fa78d9033ff35')

    def test_encrypt_password_invalid_parameters(self):
        with self.assertRaises(MissingParameter) as cm:
            self.w.encrypt_password(None, 'mypassword')
        self.assertEqual(str(cm.exception), 'Parameter network is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.w.encrypt_password('', 'mypassword')
        self.assertEqual(str(cm.exception), 'Parameter network is missing')

        with self.assertRaises(MissingParameter) as cm:
            self.w.encrypt_password('mynetwork', None)
        self.assertEqual(str(cm.exception), 'Parameter password is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.w.encrypt_password('mynetwork', '')
        self.assertEqual(str(cm.exception), 'Parameter password is missing')
        with self.assertRaises(InvalidParameter) as cm:
            self.w.encrypt_password('mynetwork', 'azer')
        self.assertEqual(str(cm.exception), 'Parameter password must be 8..63 string length')
        with self.assertRaises(InvalidParameter) as cm:
            self.w.encrypt_password('mynetwork', 'azertyuiopqsdfghjklmwxcvbnazertyuiopqsdfghjklmwxcvbnazertyuiopqsdfghjklmwxcvbn')
        self.assertEqual(str(cm.exception), 'Parameter password must be 8..63 string length')

    def test_encrypt_password_invalid_command(self):
        restore_mock = Console.command

        Console.command = Mock(return_value={
            'error': True,
            'killed': False,
            'stderr': 'error'
        })
        with self.assertRaises(Exception) as cm:
            self.w.encrypt_password('mynetwork', 'mypassword')
        self.assertEqual(str(cm.exception), 'Error with wpa_passphrase: unable to encrypt it')

        Console.command = Mock(return_value={
            'error': False,
            'killed': True,
            'stderr': 'error'
        })
        with self.assertRaises(Exception) as cm:
            self.w.encrypt_password('mynetwork', 'mypassword')
        self.assertEqual(str(cm.exception), 'Error with wpa_passphrase: unable to encrypt it')

        Console.command = Mock(return_value={
            'error': False,
            'killed': False,
            'stderr': 'error',
            'stdout': 'Error occured'
        })
        with self.assertRaises(Exception) as cm:
            self.w.encrypt_password('mynetwork', 'mypassword')
        self.assertEqual(str(cm.exception), 'Error with wpa_passphrase: invalid command output')

        Console.command = Mock(return_value={
            'error': False,
            'killed': False,
            'stderr': 'error',
            'stdout': 'network={\nssid="mynetwork"}'
        })
        with self.assertRaises(Exception) as cm:
            self.w.encrypt_password('mynetwork', 'mypassword')
        self.assertEqual(str(cm.exception), 'No password generated by wpa_passphrase command')

        Console.command = restore_mock

    def test_get_configurations(self):
        configs = self.w.get_configurations()
        logging.debug(configs)
        self.assertEqual(len(configs), 1)
        self.assertTrue('default' in configs)
        self.assertEqual(len(configs['default']), 3)
        self.assertEqual(configs['default']['mynetwork1']['network'], 'mynetwork1')
        self.assertEqual(configs['default']['mynetwork2']['network'], 'mynetwork2')

    def test_add_network(self):
        self.assertTrue(self.w.add_network('mynetwork3', 'wpa', 'mypassword3'))
        configs = self.w.get_configurations()
        self.assertEqual(len(configs), 1)
        self.assertTrue('default' in configs)
        self.assertEqual(len(configs['default']), 4)
        self.assertEqual(configs['default']['mynetwork3']['network'], 'mynetwork3')

    def test_add_network_existing_network(self):
        self.assertRaises(Exception, self.w.add_network, 'mynetwork2', 'wpa', 'mypassword2')

    def test_add_network_missing_params(self):
        self.assertRaises(MissingParameter, self.w.add_network, None, 'wpa', 'mypassword2')
        self.assertRaises(MissingParameter, self.w.add_network, '', 'wpa', 'mypassword2')
        self.assertRaises(MissingParameter, self.w.add_network, 'mynetwork3', None, 'mypassword2')
        self.assertRaises(MissingParameter, self.w.add_network, 'mynetwork3', '', 'mypassword2')
        self.assertRaises(MissingParameter, self.w.add_network, 'mynetwork3', 'wpa', None)
        self.assertRaises(MissingParameter, self.w.add_network, 'mynetwork3', 'wpa', '')

    def test_add_network_invalid_params(self):
        self.assertRaises(InvalidParameter, self.w.add_network, 'mynetwork3', 'wpa6', 'mypassword2')
        self.assertRaises(InvalidParameter, self.w.add_network, 'mynetwork2', 'wpa2', 'mypassword2')

    def test_add_network_new_network(self):
        interface = 'wlan666'
        self.assertTrue(self.w.add_network('mynetwork666', 'wpa2', 'mypassword', interface=interface))
        self.assertTrue(os.path.exists('wpa_supplicant-%s.conf' % interface))
        os.remove('wpa_supplicant-%s.conf' % interface)
        time.sleep(1.0)

    def test_add_network_no_password_encryption(self):
        self.assertTrue(self.w.add_network('mynetwork3', 'wpa', 'mypassword3', encrypt_password=False))
        configs = self.w.get_configurations()
        self.assertEqual(configs['default']['mynetwork3']['password'], 'mypassword3')

    def test_add_network_wep(self):
        self.assertTrue(self.w.add_network('mywepnetwork', 'wep', 'myweppassword'))
        configs = self.w.get_configurations()
        self.assertEqual(configs['default']['mywepnetwork']['password'], 'myweppassword')

    def test_add_network_unsecure(self):
        self.assertTrue(self.w.add_network('mywepnetwork', 'unsecured', 'myweppassword'))
        configs = self.w.get_configurations()
        self.assertIsNone(configs['default']['mywepnetwork']['password'])

    def test_delete_existing_network(self):
        self.assertTrue(self.w.delete_network('mynetwork2'))
        self.assertEqual(len(self.w.get_configurations()['default']), 2)
        self.assertTrue(self.w.delete_network('mynetwork1'))
        self.assertEqual(len(self.w.get_configurations()['default']), 1)

    def test_delete_unknown_network(self):
        self.assertFalse(self.w.delete_network('network666'))
        self.assertEqual(len(self.w.get_configurations()['default']), 3)

    def test_update_password(self):
        before_config = self.w.get_configuration('mynetwork2')
        self.assertTrue(self.w.update_network_password('mynetwork2', 'newsuperpassword'))
        after_config = self.w.get_configuration('mynetwork2')
        self.assertNotEqual(before_config['password'], after_config['password'])

    def test_update_password_wep(self):
        self.assertTrue(self.w.update_network_password('wepnetwork', 'newsuperpassword'))
        config = self.w.get_configuration('wepnetwork')
        self.assertEqual(config['password'], 'newsuperpassword')

    def test_enable_disable_network(self):
        self.assertTrue(self.w.enable_network('mynetwork2'))
        config = self.w.get_configuration('mynetwork2')
        self.assertFalse(config[u'disabled'])

        self.assertTrue(self.w.disable_network('mynetwork2'))
        config = self.w.get_configuration('mynetwork2')
        self.assertTrue(config[u'disabled'])

    def test_enable_disable_network_invalid_parameters(self):
        with self.assertRaises(MissingParameter) as cm:
            self.w.enable_network(None)
        self.assertEqual(str(cm.exception), 'Parameter network is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.w.enable_network('')
        self.assertEqual(str(cm.exception), 'Parameter network is missing')

        with self.assertRaises(MissingParameter) as cm:
            self.w.disable_network(None)
        self.assertEqual(str(cm.exception), 'Parameter network is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.w.disable_network('')
        self.assertEqual(str(cm.exception), 'Parameter network is missing')

    def test_enable_disable_network_unknow_interface(self):
        self.assertFalse(self.w.enable_network('mynetwork', 'myinterface'))
        self.assertFalse(self.w.disable_network('mynetwork', 'myinterface'))

    def test_get_configuration_unknown_interface(self):
        self.assertIsNone(self.w.get_configuration('mynetwork', 'wlan1'))


class WpaSupplicantConfTestsEmptyConf(unittest.TestCase):

    FILE_NAME = 'wpa_supplicant.conf'
    CONTENT = u"""ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\nupdate_config=1"""

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.path = os.path.join(os.getcwd(), self.FILE_NAME)
        logging.debug('Using conf file "%s"' % self.path)

        #fill with default content
        with io.open(self.path, 'w') as f:
            f.write(self.CONTENT)

        w = WpaSupplicantConf
        w.WPASUPPLICANT_DIR = os.path.abspath('./')
        w.DEFAULT_CONF = 'wpa_supplicant.conf'
        self.w = w(self.fs)

    def tearDown(self):
        if os.path.exists('%s' % self.FILE_NAME):
            os.remove('%s' % self.FILE_NAME)

    def test_set_country_with_no_country_field_in_file(self):
        self.w.set_country('france')

    def test_get_configurations(self):
        networks = self.w.get_configurations()
        logging.debug('networks: %s' % networks)
        self.assertEqual(len(networks), 1)
        self.assertTrue('default' in networks)
        self.assertEqual(len(networks['default']), 0)

    def test_add_network(self):
        self.assertTrue(self.w.add_network('mynetwork3', 'wpa', 'mypassword3'))
        networks = self.w.get_configurations()
        self.assertEqual(len(networks), 1)
        self.assertTrue('default' in networks)
        self.assertEqual(networks['default']['mynetwork3']['network'], 'mynetwork3')


class WpaSupplicantConfTestsMultipleConfigs(unittest.TestCase):
    
    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

        self.fs = CleepFilesystem()
        self.fs.enable_write()

        #fake conf files
        fd = open('wpa_supplicant.conf', 'w')
        fd.write("""country=GB
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network = {
    ssid="mynetwork666"
    psk="mypassword666"
}""")
        fd.close()
        fd = open('wpa_supplicant-wlan0.conf', 'w')
        fd.write('country=GB\nctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\nupdate_config=1')
        fd.close()
        fd = open('wpa_supplicant-wlan1.conf', 'w')
        fd.write("""country=GB
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
}""")
        fd.close()

        w = WpaSupplicantConf
        w.WPASUPPLICANT_DIR = os.path.abspath('./')
        w.CONF = 'wpa_supplicant.conf'
        self.w = w(self.fs)

    def tearDown(self):
        os.remove('wpa_supplicant.conf')
        os.remove('wpa_supplicant-wlan0.conf')
        os.remove('wpa_supplicant-wlan1.conf')

    def test_get_configurations(self):
        configs = self.w.get_configurations()
        logging.debug(configs)
        self.assertTrue('default' in configs)
        self.assertTrue('wlan0' in configs)
        self.assertTrue('wlan1' in configs)
        self.assertEqual(len(configs['default']), 1)
        self.assertEqual(len(configs['wlan0']), 0)
        self.assertEqual(len(configs['wlan1']), 2)
    
    def test_get_interface_configs(self):
        self.assertIsNotNone(self.w.get_configuration('mynetwork666'))
        self.assertIsNotNone(self.w.get_configuration('mynetwork666', 'default'))
        self.assertIsNotNone(self.w.get_configuration('mynetwork2', 'wlan1'))
        self.assertIsNone(self.w.get_configuration('mynetwork2', 'wlan0'))

    def test_add_network_in_wlan0(self):
        self.assertTrue(self.w.add_network('mynetwork3', 'wpa', 'mypassword3', interface='wlan0'))
        configs = self.w.get_configurations()
        self.assertTrue('default' in configs)
        self.assertTrue('wlan0' in configs)
        self.assertTrue('wlan1' in configs)
        self.assertEqual(len(configs['wlan0']), 1)
        self.assertEqual(configs['wlan0']['mynetwork3']['network'], 'mynetwork3')

    def test_add_network_in_multiple_interfaces(self):
        self.assertTrue(self.w.add_network('mynetwork3', 'wpa', 'mypassword3', interface='wlan0'))
        self.assertTrue(self.w.add_network('mynetwork3', 'wpa', 'mypassword3', interface='wlan1'))
        self.assertTrue(self.w.add_network('mynetwork3', 'wpa', 'mypassword3', interface='default'))
        configs = self.w.get_configurations()
        logging.debug(configs)
        self.assertTrue('mynetwork3' in configs['default'])
        self.assertTrue('mynetwork3' in configs['wlan1'])
        self.assertTrue('mynetwork3' in configs['wlan0'])

    def test_delete_existing_networks_in_interface(self):
        self.assertTrue(self.w.delete_network('mynetwork2', 'wlan1'))
        configs = self.w.get_configurations()
        self.assertEqual(len(configs['wlan1']), 1)

        self.assertTrue(self.w.delete_network('mynetwork1', 'wlan1'))
        configs = self.w.get_configurations()
        self.assertEqual(len(configs['wlan1']), 0)

        self.assertTrue(self.w.delete_network('mynetwork666'))
        self.assertEqual(len(configs['wlan0']), 0)

        self.assertFalse(self.w.delete_network('unknown', 'wlan0'))

    def test_update_password(self):
        before_config = self.w.get_configuration('mynetwork2', 'wlan1')
        self.assertTrue(self.w.update_network_password('mynetwork2', 'newsuperpassword', 'wlan1'))
        after_config = self.w.get_configuration('mynetwork2', 'wlan1')

        self.assertNotEqual(before_config['password'], after_config['password'])

    def test_enable_disable_network(self):
        self.assertTrue(self.w.enable_network('mynetwork2', 'wlan1'))
        config = self.w.get_configuration('mynetwork2', 'wlan1')
        self.assertFalse(config[u'disabled'])

        self.assertTrue(self.w.disable_network('mynetwork2', 'wlan1'))
        config = self.w.get_configuration('mynetwork2', 'wlan1')
        self.assertTrue(config[u'disabled'])

class WpaSupplicantConfTestsNoConfig(unittest.TestCase):
    
    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

        self.fs = CleepFilesystem()
        self.fs.enable_write()

        w = WpaSupplicantConf
        w.WPASUPPLICANT_DIR = os.path.abspath('./')
        w.CONF = 'wpa_supplicant.conf'
        self.w = w(self.fs)

    def tearDown(self):
        pass

    def test_get_configurations(self):
        configs = self.w.get_configurations()
        self.assertEqual(len(configs.keys()), 1)

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","*test_*.py" --concurrency=thread test_wpasupplicantconf.py; coverage report -m -i
    unittest.main()
