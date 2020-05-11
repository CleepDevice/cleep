#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from etcmodules import EtcModules
from raspiot.libs.internals.cleepfilesystem import CleepFilesystem
from raspiot.exception import MissingParameter, InvalidParameter, CommandError
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
from pprint import pformat
import io


class EtcModulesTests(unittest.TestCase):

    FILE_NAME = 'modules.conf'
    CONTENT = u"""# /etc/modules: kernel modules to load at boot time.
#
# This file contains the names of kernel modules that should be loaded
# at boot time, one per line. Lines beginning with "#" are ignored.
w1-therm
w1-gpio
bcm4522"""

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

        e = EtcModules
        e.CONF = self.FILE_NAME
        self.e = e(self.fs, False)

    def tearDown(self):
        if os.path.exists('%s' % self.FILE_NAME):
            os.remove('%s' % self.FILE_NAME)

    def test_generic_module(self):
        mod = 'mymodule'
        self.assertFalse(self.e.is_module_enabled(mod))
        self.assertTrue(self.e.enable_module(mod))
        self.assertTrue(self.e.disable_module(mod))
        self.assertFalse(self.e.is_module_enabled(mod))
        self.assertTrue(self.e.enable_module(mod))
        self.assertTrue(self.e.is_module_enabled(mod))

    def test_generic_module_invalid_parameters(self):
        with self.assertRaises(MissingParameter) as cm:
            self.e.is_module_enabled(None)
        with self.assertRaises(MissingParameter) as cm:
            self.e.is_module_enabled('')

        with self.assertRaises(MissingParameter) as cm:
            self.e.enable_module(None)
        with self.assertRaises(MissingParameter) as cm:
            self.e.enable_module('')

        with self.assertRaises(MissingParameter) as cm:
            self.e.disable_module(None)
        with self.assertRaises(MissingParameter) as cm:
            self.e.disable_module('')

    def test_onewire(self):
        self.assertTrue(self.e.is_onewire_enabled())
        self.assertTrue(self.e.enable_onewire())
        self.assertTrue(self.e.disable_onewire())
        self.assertFalse(self.e.is_onewire_enabled())
        self.assertTrue(self.e.enable_onewire())
        self.assertTrue(self.e.is_onewire_enabled())

    def test_embedded_sound(self):
        self.assertFalse(self.e.is_embedded_sound_enabled())
        self.assertTrue(self.e.enable_embedded_sound())
        self.assertTrue(self.e.disable_embedded_sound())
        self.assertFalse(self.e.is_embedded_sound_enabled())
        self.assertTrue(self.e.enable_embedded_sound())
        self.assertTrue(self.e.is_embedded_sound_enabled())

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","*test_*.py" --concurrency=thread test_etcmodules.py; coverage report -m -i
    unittest.main()
