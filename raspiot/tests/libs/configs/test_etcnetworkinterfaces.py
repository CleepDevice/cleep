#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys 
sys.path.append('/root/cleep/raspiot/libs/configs')
from etcnetworkinterfaces import EtcNetworkInterfaces
from raspiot.libs.internals.cleepfilesystem import CleepFilesystem
from raspiot.exceptions import MissingParameter, InvalidParameter, CommandError
from raspiot.libs.tests.lib import TestLib, TRACE
import unittest
import logging
from pprint import pformat, pprint
import io

logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)s %(levelname)s : %(message)s')

class EtcNetworkInterfacesWithoutCacheTest(unittest.TestCase):

    FILE_NAME = 'interfaces.conf'
    CONTENT = u"""auto lo

iface lo inet loopback
iface eth0 inet dhcp

allow-hotplug wlan0
iface wlan0 inet manual
wpa-roam /etc/wpa_supplicant/wpa_supplicant.conf

allow-hotplug eth3
iface eth3 inet static
    address 192.168.11.100
    netmask 255.255.255.0
    gateway 192.168.11.1
    dns-domain example.com
    dns-nameservers 192.168.11.1
    broadcast 192.168.11.255
    
auto eth4
allow-hotplug eth4
iface eth4 inet dhcp

iface wlan1 inet dhcp
    wpa-conf /etc/wpa_supplicant/wpa_supplicant_wlan1.conf"""

    def setUp(self):
        TestLib()
        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.path = os.path.join(os.getcwd(), self.FILE_NAME)
        logging.debug('Using conf file "%s"' % self.path)

        #fill with default content
        with io.open(self.path, 'w') as f:
            f.write(self.CONTENT)

        e = EtcNetworkInterfaces
        e.CACHE_DURATION = 0
        e.CONF = self.FILE_NAME
        self.e = e(self.fs, False)

    def tearDown(self):
        if os.path.exists('%s' % self.FILE_NAME):
            os.remove('%s' % self.FILE_NAME)

    def test_get_configurations(self):
        configs = self.e.get_configurations()
        self.assertTrue(isinstance(configs, dict))
        self.assertTrue('lo' in configs)
        self.assertTrue('eth0' in configs)
        self.assertTrue('wlan0' in configs)
        self.assertTrue('eth3' in configs)

    def test_get_configuration(self):
        configs = self.e.get_configurations()

        #check fields
        lo = configs['lo']
        self.assertTrue('interface' in lo)
        self.assertTrue('mode' in lo)
        self.assertTrue('address' in lo)
        self.assertTrue('netmask' in lo)
        self.assertTrue('broadcast' in lo)
        self.assertTrue('gateway' in lo)
        self.assertTrue('dns_nameservers' in lo)
        self.assertTrue('dns_domain' in lo)
        self.assertTrue('hotplug' in lo)
        self.assertTrue('auto' in lo)
        self.assertTrue('wpa_conf' in lo)

        eth0 = configs['eth0']
        self.assertTrue('interface' in eth0)
        self.assertTrue('mode' in eth0)
        self.assertTrue('address' in eth0)
        self.assertTrue('netmask' in eth0)
        self.assertTrue('broadcast' in eth0)
        self.assertTrue('gateway' in eth0)
        self.assertTrue('dns_nameservers' in eth0)
        self.assertTrue('dns_domain' in eth0)
        self.assertTrue('hotplug' in eth0)
        self.assertTrue('auto' in eth0)
        self.assertTrue('wpa_conf' in eth0)

        eth3 = configs['eth3']
        self.assertTrue('interface' in eth3)
        self.assertTrue('mode' in eth3)
        self.assertTrue('address' in eth3)
        self.assertTrue('netmask' in eth3)
        self.assertTrue('broadcast' in eth3)
        self.assertTrue('gateway' in eth3)
        self.assertTrue('dns_nameservers' in eth3)
        self.assertTrue('dns_domain' in eth3)
        self.assertTrue('hotplug' in eth3)
        self.assertTrue('auto' in eth3)
        self.assertTrue('wpa_conf' in eth3)

        eth4 = configs['eth4']
        self.assertTrue('interface' in eth4)
        self.assertTrue('mode' in eth4)
        self.assertTrue('address' in eth4)
        self.assertTrue('netmask' in eth4)
        self.assertTrue('broadcast' in eth4)
        self.assertTrue('gateway' in eth4)
        self.assertTrue('dns_nameservers' in eth4)
        self.assertTrue('dns_domain' in eth4)
        self.assertTrue('hotplug' in eth4)
        self.assertTrue('auto' in eth4)
        self.assertTrue('wpa_conf' in eth4)

        wlan0 = configs['wlan0']
        self.assertTrue('interface' in wlan0)
        self.assertTrue('mode' in wlan0)
        self.assertTrue('address' in wlan0)
        self.assertTrue('netmask' in wlan0)
        self.assertTrue('broadcast' in wlan0)
        self.assertTrue('gateway' in wlan0)
        self.assertTrue('dns_nameservers' in wlan0)
        self.assertTrue('dns_domain' in wlan0)
        self.assertTrue('hotplug' in wlan0)
        self.assertTrue('auto' in wlan0)
        self.assertTrue('wpa_conf' in wlan0)

        wlan1 = configs['wlan1']
        self.assertTrue('interface' in wlan1)
        self.assertTrue('mode' in wlan1)
        self.assertTrue('address' in wlan1)
        self.assertTrue('netmask' in wlan1)
        self.assertTrue('broadcast' in wlan1)
        self.assertTrue('gateway' in wlan1)
        self.assertTrue('dns_nameservers' in wlan1)
        self.assertTrue('dns_domain' in wlan1)
        self.assertTrue('hotplug' in wlan1)
        self.assertTrue('auto' in wlan1)
        self.assertTrue('wpa_conf' in wlan1)

        #check values
        self.assertEqual(lo['interface'], 'lo')
        self.assertEqual(lo['mode'], self.e.MODE_LOOPBACK)
        self.assertEqual(lo['auto'], True)
        self.assertEqual(lo['hotplug'], False)

        self.assertEqual(eth0['interface'], 'eth0')
        self.assertEqual(eth0['mode'], self.e.MODE_DHCP)
        self.assertEqual(eth0['auto'], False)
        self.assertEqual(eth0['hotplug'], False)

        self.assertEqual(eth3['interface'], 'eth3')
        self.assertEqual(eth3['mode'], self.e.MODE_STATIC)
        self.assertEqual(eth3['auto'], False)
        self.assertEqual(eth3['hotplug'], True)
        self.assertEqual(eth3['address'], '192.168.11.100')
        self.assertEqual(eth3['netmask'], '255.255.255.0')
        self.assertEqual(eth3['gateway'], '192.168.11.1')
        self.assertEqual(eth3['dns_domain'], 'example.com')
        self.assertEqual(eth3['dns_nameservers'], '192.168.11.1')
        self.assertEqual(eth3['broadcast'], '192.168.11.255')

        self.assertEqual(eth4['interface'], 'eth4')
        self.assertEqual(eth4['mode'], self.e.MODE_DHCP)
        self.assertEqual(eth4['auto'], True)
        self.assertEqual(eth4['hotplug'], True)

        self.assertEqual(wlan0['interface'], 'wlan0')
        self.assertEqual(wlan0['mode'], self.e.MODE_MANUAL)
        self.assertEqual(wlan0['auto'], False)
        self.assertEqual(wlan0['hotplug'], True)
        self.assertEqual(wlan0['wpa_conf'], '/etc/wpa_supplicant/wpa_supplicant.conf')

        self.assertEqual(wlan1['interface'], 'wlan1')
        self.assertEqual(wlan1['mode'], self.e.MODE_DHCP)
        self.assertEqual(wlan1['auto'], False)
        self.assertEqual(wlan1['hotplug'], False)
        self.assertEqual(wlan1['wpa_conf'], '/etc/wpa_supplicant/wpa_supplicant_wlan1.conf')

    def test_static_interface(self):
        self.assertTrue(self.e.add_static_interface(u'eth10', self.e.OPTION_NONE, u'10.10.10.10', u'255.255.255.0', u'10.10.10.1'))
        self.assertIsNotNone(self.e.get_configuration(u'eth10'))
        self.assertTrue(self.e.delete_interface(u'eth10'))
        self.assertIsNone(self.e.get_configuration(u'eth10'))

        self.assertTrue(self.e.add_static_interface(u'eth11', self.e.OPTION_AUTO, u'10.10.10.10', u'255.255.255.0', u'10.10.10.1'))
        self.assertIsNotNone(self.e.get_configuration(u'eth11'))
        self.assertTrue(self.e.delete_interface(u'eth11'))
        self.assertIsNone(self.e.get_configuration(u'eth11'))

        self.assertTrue(self.e.add_static_interface(u'eth12', self.e.OPTION_HOTPLUG, u'10.10.10.10', u'255.255.255.0', u'10.10.10.1'))
        self.assertIsNotNone(self.e.get_configuration(u'eth12'))
        self.assertTrue(self.e.delete_interface(u'eth12'))
        self.assertIsNone(self.e.get_configuration(u'eth12'))

    def test_dhcp_interface(self):
        self.assertTrue(self.e.add_dhcp_interface(u'eth10', self.e.OPTION_NONE))
        self.assertIsNotNone(self.e.get_configuration(u'eth10'))
        self.assertTrue(self.e.delete_interface(u'eth10'))
        self.assertIsNone(self.e.get_configuration(u'eth10'))

        self.assertTrue(self.e.add_dhcp_interface(u'eth11', self.e.OPTION_AUTO))
        self.assertIsNotNone(self.e.get_configuration(u'eth11'))
        self.assertTrue(self.e.delete_interface(u'eth11'))
        self.assertIsNone(self.e.get_configuration(u'eth11'))

        self.assertTrue(self.e.add_dhcp_interface(u'eth12', self.e.OPTION_HOTPLUG))
        self.assertIsNotNone(self.e.get_configuration(u'eth12'))
        self.assertTrue(self.e.delete_interface(u'eth12'))
        self.assertIsNone(self.e.get_configuration(u'eth12'))

    def test_check_static_options(self):
        self.assertTrue(self.e.add_static_interface(u'eth10', self.e.OPTION_AUTO, u'10.10.10.10', u'255.255.255.0', u'10.10.10.1'))
        interface = self.e.get_configuration(u'eth10')
        self.assertIsNotNone(interface)
        self.assertTrue(interface[u'auto'])
        self.assertFalse(interface[u'hotplug'])

        self.assertTrue(self.e.add_static_interface(u'eth11', self.e.OPTION_HOTPLUG, u'10.10.10.10', u'255.255.255.0', u'10.10.10.1'))
        interface = self.e.get_configuration(u'eth11')
        self.assertIsNotNone(interface)
        self.assertFalse(interface[u'auto'])
        self.assertTrue(interface[u'hotplug'])

        self.assertTrue(self.e.add_static_interface(u'eth12', self.e.OPTION_NONE, u'10.10.10.10', u'255.255.255.0', u'10.10.10.1'))
        interface = self.e.get_configuration(u'eth12')
        self.assertIsNotNone(interface)
        self.assertFalse(interface[u'auto'])
        self.assertFalse(interface[u'hotplug'])

    def test_check_dhcp_options(self):
        self.assertTrue(self.e.add_dhcp_interface(u'eth10', self.e.OPTION_AUTO))
        interface = self.e.get_configuration(u'eth10')
        self.assertIsNotNone(interface)
        self.assertTrue(interface[u'auto'])
        self.assertFalse(interface[u'hotplug'])

        self.assertTrue(self.e.add_dhcp_interface(u'eth11', self.e.OPTION_HOTPLUG))
        interface = self.e.get_configuration(u'eth11')
        self.assertIsNotNone(interface)
        self.assertFalse(interface[u'auto'])
        self.assertTrue(interface[u'hotplug'])

        self.assertTrue(self.e.add_dhcp_interface(u'eth12', self.e.OPTION_NONE))
        interface = self.e.get_configuration(u'eth12')
        self.assertIsNotNone(interface)
        self.assertFalse(interface[u'auto'])
        self.assertFalse(interface[u'hotplug'])

    def test_multiple_options(self):
        self.assertTrue(self.e.add_dhcp_interface(u'eth10', self.e.OPTION_AUTO | self.e.OPTION_HOTPLUG))
        interface = self.e.get_configuration(u'eth10')
        self.assertIsNotNone(interface)
        self.assertTrue(interface[u'auto'])
        self.assertTrue(interface[u'hotplug'])

    def test_get_configuration_invalid_parameters(self):
        with self.assertRaises(MissingParameter) as cm:
            self.e.get_configuration(None)
        with self.assertRaises(MissingParameter) as cm:
            self.e.get_configuration('')
        self.assertEqual(cm.exception.message, 'Parameter "interface" is missing')

    def test_add_default_interface(self):
        self.assertTrue(self.e.add_default_interface())
        self.assertIsNotNone(self.e.get_configuration('default'))

    def test_add_default_interface_already_exists(self):
        self.e.add_default_interface()
        with self.assertRaises(InvalidParameter) as cm:
            self.e.add_default_interface()
        self.assertEqual(cm.exception.message, 'Interface "default" is already configured')

    def test_add_static_interface_invalid_parameters(self):
        with self.assertRaises(MissingParameter) as cm:
            self.e.add_static_interface(None, self.e.OPTION_AUTO, '10.10.10.10', '255.255.255.0', '10.10.10.1')
        with self.assertRaises(MissingParameter) as cm:
            self.e.add_static_interface('', self.e.OPTION_AUTO, '10.10.10.10', '255.255.255.0', '10.10.10.1')
        self.assertEqual(cm.exception.message, 'Parameter "interface" is missing')

        with self.assertRaises(MissingParameter) as cm:
            self.e.add_static_interface('eth10', None, '10.10.10.10', '255.255.255.0', '10.10.10.1')
        self.assertEqual(cm.exception.message, 'Parameter "option" is missing')
        with self.assertRaises(InvalidParameter) as cm:
            self.e.add_static_interface('eth10', 4, '10.10.10.10', '255.255.255.0', '10.10.10.1')
        self.assertEqual(cm.exception.message, 'Parameter "option" is invalid')

        with self.assertRaises(MissingParameter) as cm:
            self.e.add_static_interface('eth10', self.e.OPTION_AUTO, None, '255.255.255.0', '10.10.10.1')
        with self.assertRaises(MissingParameter) as cm:
            self.e.add_static_interface('eth10', self.e.OPTION_AUTO, '', '255.255.255.0', '10.10.10.1')
        self.assertEqual(cm.exception.message, 'Parameter "address" is missing')

        with self.assertRaises(MissingParameter) as cm:
            self.e.add_static_interface('eth10', self.e.OPTION_AUTO, '10.10.10.10', None, '10.10.10.1')
        with self.assertRaises(MissingParameter) as cm:
            self.e.add_static_interface('eth10', self.e.OPTION_AUTO, '10.10.10.10', '', '10.10.10.1')
        self.assertEqual(cm.exception.message, 'Parameter "gateway" is missing')

        with self.assertRaises(MissingParameter) as cm:
            self.e.add_static_interface('eth10', self.e.OPTION_AUTO, '10.10.10.10', '255.255.255.0', None)
        with self.assertRaises(MissingParameter) as cm:
            self.e.add_static_interface('eth10', self.e.OPTION_AUTO, '10.10.10.10', '255.255.255.0', '')
        self.assertEqual(cm.exception.message, 'Parameter "netmask" is missing')

    def test_add_dhcp_interface_invalid_parameters(self):
        with self.assertRaises(MissingParameter) as cm:
            self.e.add_dhcp_interface(None, self.e.OPTION_AUTO)
        with self.assertRaises(MissingParameter) as cm:
            self.e.add_dhcp_interface('', self.e.OPTION_AUTO)
        self.assertEqual(cm.exception.message, 'Parameter "interface" is missing')

        with self.assertRaises(MissingParameter) as cm:
            self.e.add_dhcp_interface('eth10', None)
        self.assertEqual(cm.exception.message, 'Parameter "option" is missing')
        with self.assertRaises(InvalidParameter) as cm:
            self.e.add_dhcp_interface('eth10', 4)
        self.assertEqual(cm.exception.message, 'Parameter "option" is invalid')

    def test_add_static_interface_already_configured(self):
        with self.assertRaises(InvalidParameter) as cm:
            self.e.add_static_interface('eth3', self.e.OPTION_AUTO, '10.10.10.10', '255.255.255.0', '10.10.10.1')
        self.assertEqual(cm.exception.message, 'Interface "eth3" is already configured')

    def test_add_dhcp_interface_already_configured(self):
        with self.assertRaises(InvalidParameter) as cm:
            self.e.add_dhcp_interface('eth3', self.e.OPTION_AUTO)
        self.assertEqual(cm.exception.message, 'Interface "eth3" is already configured')

    def test_add_static_interface_with_extra_parameters(self):
        self.assertTrue(self.e.add_static_interface('eth999', self.e.OPTION_AUTO, '10.10.10.10', '255.255.255.0', '10.10.10.1', '1.2.3.4', '2.3.4.5', '3.4.5.6', '/etc/mywpasupplicant.conf'))
        eth999 = self.e.get_configuration('eth999')
        self.assertIsNotNone(eth999)
        self.assertEqual(eth999['dns_nameservers'], '1.2.3.4')
        self.assertEqual(eth999['dns_domain'], '2.3.4.5')
        self.assertEqual(eth999['broadcast'], '3.4.5.6')
        self.assertEqual(eth999['wpa_conf'], '/etc/mywpasupplicant.conf')

    def test_delete_ethernet_static_interface(self):
        self.assertTrue(self.e.delete_interface('eth3'))
        self.assertIsNone(self.e.get_configuration('eth3'))

    def test_delete_ethernet_dhcp_interface(self):
        self.assertTrue(self.e.delete_interface('eth0'))
        self.assertIsNone(self.e.get_configuration('eth0'))

    def test_delete_wlan_interface(self):
        self.assertTrue(self.e.delete_interface('wlan0'))
        self.assertIsNone(self.e.get_configuration('wlan0'))

        self.assertTrue(self.e.delete_interface('wlan1'))
        self.assertIsNone(self.e.get_configuration('wlan1'))

    def test_delete_special_interface(self):
        #delete unknown interface
        self.assertFalse(self.e.delete_interface('an-interface'))

        #delete loopback interface
        self.assertFalse(self.e.delete_interface('lo'))


class EtcNetworkInterfacesWithCacheTest(unittest.TestCase):

    FILE_NAME = 'interfaces.conf'
    CONTENT = u"""auto lo

iface lo inet loopback
iface eth0 inet dhcp

allow-hotplug wlan0
iface wlan0 inet manual
wpa-roam /etc/wpa_supplicant/wpa_supplicant.conf
iface default inet dhcp

allow-hotplug eth3
iface eth3 inet static
    address 192.168.11.100
    netmask 255.255.255.0
    gateway 192.168.11.1
    broadcast 10.10.10.10
    dns-domain example.com
    dns-nameservers 192.168.11.1"""

    def setUp(self):
        TestLib()
        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.path = os.path.join(os.getcwd(), self.FILE_NAME)
        logging.debug('Using conf file "%s"' % self.path)

        #fill with default content
        with io.open(self.path, 'w') as f:
            f.write(self.CONTENT)

        e = EtcNetworkInterfaces
        e.CONF = self.FILE_NAME
        self.e = e(self.fs, False)

    def tearDown(self):
        if os.path.exists('%s' % self.FILE_NAME):
            os.remove('%s' % self.FILE_NAME)

    def test_return_cached_configurations(self):
        old_configs = self.e.get_configurations()
        with io.open(self.FILE_NAME, 'w') as cm:
            cm.write(u'')
        new_configs = self.e.get_configurations()
        self.assertEqual(old_configs, new_configs, 'Lib should returns cached content')
    


if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_etcnetworkinterfaces.py
    #coverage report -m
    unittest.main()
