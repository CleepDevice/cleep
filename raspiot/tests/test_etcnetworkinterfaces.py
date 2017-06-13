#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.etcnetworkinterfaces import EtcNetworkInterfaces
import unittest
import os

class etcNetworkInterfaces_validConf(unittest.TestCase):
    def setUp(self):
        #fake conf file
        fd = open('interfaces.fake.conf', 'w')
        fd.write("""auto lo

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
    dns-domain example.com
    dns-nameservers 192.168.11.1""")
        fd.close()

        self.e = EtcNetworkInterfaces(backup=False)
        self.e.CONF = 'interfaces.fake.conf'

    def tearDown(self):
        os.remove('interfaces.fake.conf')

    def test_static_interface(self):
        self.assertTrue(self.e.add_static_interface('eth10', u'none', u'10.10.10.10', u'255.255.255.0', u'10.10.10.1'))
        self.assertIsNotNone(self.e.get_interface('eth10'))
        self.assertTrue(self.e.delete_static_interface('eth10'))
        self.assertIsNone(self.e.get_interface('eth10'))

        self.assertTrue(self.e.add_static_interface('eth11', u'auto', u'10.10.10.10', u'255.255.255.0', u'10.10.10.1'))
        self.assertIsNotNone(self.e.get_interface(u'eth11'))
        self.assertTrue(self.e.delete_static_interface(u'eth11'))
        self.assertIsNone(self.e.get_interface(u'eth11'))

        self.assertTrue(self.e.add_static_interface('eth12', u'hotplug', u'10.10.10.10', u'255.255.255.0', u'10.10.10.1'))
        self.assertIsNotNone(self.e.get_interface(u'eth12'))
        self.assertTrue(self.e.delete_static_interface(u'eth12'))
        self.assertIsNone(self.e.get_interface(u'eth12'))

    def test_dhcp_interface(self):
        self.assertTrue(self.e.add_dhcp_interface(u'eth10', u'none'))
        self.assertIsNotNone(self.e.get_interface(u'eth10'))
        self.assertTrue(self.e.delete_dhcp_interface(u'eth10'))
        self.assertIsNone(self.e.get_interface(u'eth10'))

        self.assertTrue(self.e.add_dhcp_interface(u'eth11', u'auto'))
        self.assertIsNotNone(self.e.get_interface(u'eth11'))
        self.assertTrue(self.e.delete_dhcp_interface(u'eth11'))
        self.assertIsNone(self.e.get_interface(u'eth11'))

        self.assertTrue(self.e.add_dhcp_interface(u'eth12', u'hotplug'))
        self.assertIsNotNone(self.e.get_interface(u'eth12'))
        self.assertTrue(self.e.delete_dhcp_interface(u'eth12'))
        self.assertIsNone(self.e.get_interface(u'eth12'))

    def test_check_static_options(self):
        self.assertTrue(self.e.add_static_interface(u'eth10', u'auto', u'10.10.10.10', u'255.255.255.0', u'10.10.10.1'))
        interface = self.e.get_interface(u'eth10')
        self.assertIsNotNone(interface)
        self.assertTrue(interface[u'auto'])
        self.assertFalse(interface[u'hotplug'])

        self.assertTrue(self.e.add_static_interface(u'eth11', u'hotplug', u'10.10.10.10', u'255.255.255.0', u'10.10.10.1'))
        interface = self.e.get_interface(u'eth11')
        self.assertIsNotNone(interface)
        self.assertFalse(interface[u'auto'])
        self.assertTrue(interface[u'hotplug'])

        self.assertTrue(self.e.add_static_interface(u'eth12', u'none', u'10.10.10.10', u'255.255.255.0', u'10.10.10.1'))
        interface = self.e.get_interface(u'eth12')
        self.assertIsNotNone(interface)
        self.assertFalse(interface[u'auto'])
        self.assertFalse(interface[u'hotplug'])

    def test_check_dhcp_options(self):
        self.assertTrue(self.e.add_dhcp_interface(u'eth10', u'auto'))
        interface = self.e.get_interface(u'eth10')
        self.assertIsNotNone(interface)
        self.assertTrue(interface[u'auto'])
        self.assertFalse(interface[u'hotplug'])

        self.assertTrue(self.e.add_dhcp_interface(u'eth11', u'hotplug'))
        interface = self.e.get_interface(u'eth11')
        self.assertIsNotNone(interface)
        self.assertFalse(interface[u'auto'])
        self.assertTrue(interface[u'hotplug'])

        self.assertTrue(self.e.add_dhcp_interface(u'eth12', u'none'))
        interface = self.e.get_interface(u'eth12')
        self.assertIsNotNone(interface)
        self.assertFalse(interface[u'auto'])
        self.assertFalse(interface[u'hotplug'])



