#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import CommandError, MissingParameter, InvalidParameter
from raspiot.libs.configs.wpasupplicantconf import WpaSupplicantConf
from raspiot.libs.internals.cleepfilesystem import CleepFilesystem
import unittest
import os
import logging

logging.basicConfig(level=logging.WARN, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class WpaSupplicantConfTests_validConf(unittest.TestCase):
    def setUp(self):
        #fake conf file
        fd = file('wpa_supplicant.conf', 'w')
        #fd.write('country=GB\nctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\nupdate_config=1\n\nnetwork = {\n\tssid="mynetwork1"\n\tpsk="mypassword1"\n}\nnetwork={\n\tssid="mynetwork2"\n\tscan_ssid=1\n\t#psk="helloworld"\n\tpsk="mypassword2"\n}\n')
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
        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.w = WpaSupplicantConf(self.fs)
        self.w.WPASUPPLICANT_DIR = os.path.abspath('./')
        self.w.DEFAULT_CONF = 'wpa_supplicant.conf'

    def tearDown(self):
        os.remove('wpa_supplicant.conf')

    def test_get_configurations(self):
        configs = self.w.get_configurations()
        logging.debug(configs)
        self.assertEqual(len(configs), 1)
        self.assertTrue('default' in configs)
        self.assertEqual(len(configs['default']), 2)
        self.assertEqual(configs['default']['mynetwork1']['network'], 'mynetwork1')
        self.assertEqual(configs['default']['mynetwork2']['network'], 'mynetwork2')

    def test_add_network(self):
        self.assertTrue(self.w.add_network('mynetwork3', 'wpa', 'mypassword3'))
        configs = self.w.get_configurations()
        self.assertEqual(len(configs), 1)
        self.assertTrue('default' in configs)
        self.assertEqual(len(configs['default']), 3)
        self.assertEqual(configs['default']['mynetwork3']['network'], 'mynetwork3')

    def test_add_existing_network(self):
        self.assertRaises(Exception, self.w.add_network, 'mynetwork2', 'wpa', 'mypassword2')

    def test_add_missing_params(self):
        self.assertRaises(MissingParameter, self.w.add_network, None, 'wpa', 'mypassword2')
        self.assertRaises(MissingParameter, self.w.add_network, '', 'wpa', 'mypassword2')
        self.assertRaises(MissingParameter, self.w.add_network, 'mynetwork3', None, 'mypassword2')
        self.assertRaises(MissingParameter, self.w.add_network, 'mynetwork3', '', 'mypassword2')
        self.assertRaises(MissingParameter, self.w.add_network, 'mynetwork3', 'wpa', None)
        self.assertRaises(MissingParameter, self.w.add_network, 'mynetwork3', 'wpa', '')

    def test_add_invalid_params(self):
        self.assertRaises(InvalidParameter, self.w.add_network, 'mynetwork3', 'wpa6', 'mypassword2')
        self.assertRaises(InvalidParameter, self.w.add_network, 'mynetwork2', 'wpa2', 'mypassword2')

    def test_delete_existing_network(self):
        self.assertTrue(self.w.delete_network('mynetwork2'))
        self.assertEqual(len(self.w.get_configurations()['default']), 1)
        self.assertTrue(self.w.delete_network('mynetwork1'))
        self.assertEqual(len(self.w.get_configurations()['default']), 0)

    def test_delete_unknown_network(self):
        self.assertFalse(self.w.delete_network('network666'))
        self.assertEqual(len(self.w.get_configurations()['default']), 2)

    def test_update_password(self):
        before_config = self.w.get_configuration('mynetwork2')
        self.assertTrue(self.w.update_network_password('mynetwork2', 'newsuperpassword'))
        after_config = self.w.get_configuration('mynetwork2')
        self.assertNotEqual(before_config['psk'], after_config['psk'])

    def test_enable_disable_network(self):
        self.assertTrue(self.w.enable_network('mynetwork2'))
        config = self.w.get_configuration('mynetwork2')
        self.assertFalse(config[u'disabled'])

        self.assertTrue(self.w.disable_network('mynetwork2'))
        config = self.w.get_configuration('mynetwork2')
        self.assertTrue(config[u'disabled'])


class WpaSupplicantConfTests_emptyConf(unittest.TestCase):
    def setUp(self):
        #fake conf file
        fd = file('wpa_supplicant.conf', 'w')
        fd.write('country=GB\nctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\nupdate_config=1')
        fd.close()
        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.w = WpaSupplicantConf(self.fs)
        self.w.CONF = 'wpa_supplicant.conf'
        self.w.WPASUPPLICANT_DIR = os.path.abspath('./')

    def tearDown(self):
        os.remove('wpa_supplicant.conf')

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


class WpaSupplicantConfTests_multipleConfigs(unittest.TestCase):
    def setUp(self):
        #fake conf files
        fd = file('wpa_supplicant.conf', 'w')
        fd.write("""country=GB
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network = {
    ssid="mynetwork666"
    psk="mypassword666"
}""")
        fd.close()
        fd = file('wpa_supplicant-wlan0.conf', 'w')
        fd.write('country=GB\nctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\nupdate_config=1')
        fd.close()
        fd = file('wpa_supplicant-wlan1.conf', 'w')
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
        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.w = WpaSupplicantConf(self.fs)
        self.w.CONF = 'wpa_supplicant.conf'
        self.w.WPASUPPLICANT_DIR = os.path.abspath('./')

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

        self.assertNotEqual(before_config['psk'], after_config['psk'])

    def test_enable_disable_network(self):
        self.assertTrue(self.w.enable_network('mynetwork2', 'wlan1'))
        config = self.w.get_configuration('mynetwork2', 'wlan1')
        self.assertFalse(config[u'disabled'])

        self.assertTrue(self.w.disable_network('mynetwork2', 'wlan1'))
        config = self.w.get_configuration('mynetwork2', 'wlan1')
        self.assertTrue(config[u'disabled'])

