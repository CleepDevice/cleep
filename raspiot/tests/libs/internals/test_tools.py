#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
import tools
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
import io
import time

class ToolsTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

    def tearDown(self):
        pass

    def test_raspberry_pi_infos(self):
        infos = tools.raspberry_pi_infos()

        self.assertTrue('date' in infos)
        self.assertTrue('model' in infos)
        self.assertTrue('pcbrevision' in infos)
        self.assertTrue('memory' in infos)
        self.assertTrue('notes' in infos)
        self.assertTrue('ethernet' in infos)
        self.assertTrue('wireless' in infos)
        self.assertTrue('audio' in infos)

        self.assertTrue(isinstance(infos['date'], str))
        self.assertTrue(isinstance(infos['model'], str))
        self.assertTrue(isinstance(infos['pcbrevision'], str))
        self.assertTrue(isinstance(infos['memory'], str))
        self.assertTrue(isinstance(infos['notes'], str))
        self.assertTrue(isinstance(infos['ethernet'], bool))
        self.assertTrue(isinstance(infos['wireless'], bool))
        self.assertTrue(isinstance(infos['audio'], bool))

    def test_install_dbm_to_percent(self):
        self.assertEqual(tools.dbm_to_percent(-1), 100)
        self.assertEqual(tools.dbm_to_percent(-25), 98)
        self.assertEqual(tools.dbm_to_percent(-50), 79)
        self.assertEqual(tools.dbm_to_percent(-75), 40)
        self.assertEqual(tools.dbm_to_percent(-100), 1)
        self.assertEqual(tools.dbm_to_percent(-200), 0)
        self.assertEqual(tools.dbm_to_percent(0), 0)

    def test_wpa_passphrase(self):
        # values generated with wpa_passphrase system command
        self.assertEqual(tools.wpa_passphrase('wifinetwork', 'my super passphrase'), '57cead2492066a4bf783f715ddac4d8b6849424b92e36f3e7da68f0242592081')

    def test_file_to_base64(self):
        path_bin = 'test_tob64.bin'
        try:
            with io.open(path_bin, 'w') as fd:
                fd.write(u'some binary data\r')
            b64 = tools.file_to_base64(path_bin)
            logging.debug('Computed base64: %s' % b64)
            self.assertEqual('c29tZSBiaW5hcnkgZGF0YQ0=', b64)
        finally:
            if os.path.exists(path_bin):
                os.remove(path_bin)

        path_invalid = 'dummy'
        try:
            b64 = tools.file_to_base64(path_invalid)
            self.fail('Invalid file should raises exception')
        except:
            pass

    def test_hr_uptime(self):
        uptime = tools.hr_uptime(time.time())
        self.assertTrue(isinstance(uptime, str))
        splits = uptime.split()
        self.assertEqual(len(splits), 3)
        self.assertTrue(splits[0].endswith('d'))
        self.assertTrue(splits[1].endswith('h'))
        self.assertTrue(splits[2].endswith('m'))

    def test_hr_bytes(self):
        self.assertEqual(tools.hr_bytes(1), '1B')
        self.assertEqual(tools.hr_bytes(1000), '1000B')
        self.assertEqual(tools.hr_bytes(10000), '9.8K')
        self.assertEqual(tools.hr_bytes(1048576), '1.0M')

    def test_compare_versions(self):
        self.assertTrue(tools.compare_versions('1.0.0', '1.0.1'))
        self.assertFalse(tools.compare_versions('1.0.1', '1.0.0'))
        self.assertTrue(tools.compare_versions('1.2.3', '3.2.1'))

        with self.assertRaises(Exception) as cm:
            tools.compare_versions('1.2', '1.2.3')
        self.assertEqual(str(cm.exception), 'Invalid version "1.2" format, only 3 digits format allowed')
        with self.assertRaises(Exception) as cm:
            tools.compare_versions('1.2.3', '1.2')
        self.assertEqual(str(cm.exception), 'Invalid version "1.2" format, only 3 digits format allowed')

    def test_split_path(self):
        path = tools.full_split_path('/a/path/to/hell/')
        logging.debug('Path: %s' % path)
        self.assertEqual(len(path), 5)

        path = tools.full_split_path('/a/path/to/hell/diablo.txt')
        logging.debug('Path: %s' % path)
        self.assertEqual(len(path), 6)

        path = tools.full_split_path('')
        logging.debug('Path: %s' % path)
        self.assertEqual(len(path), 0)

        path = tools.full_split_path('/')
        logging.debug('Path: %s' % path)
        self.assertEqual(len(path), 1)
        self.assertEqual(path[0], '/')

        path = tools.full_split_path('a/relative/path/to/hell/')
        logging.debug('Path: %s' % path)
        self.assertEqual(len(path), 5)

        path = tools.full_split_path('a/relative/path/to/hell/diablo.txt')
        logging.debug('Path: %s' % path)
        self.assertEqual(len(path), 6)

    def test_is_core_lib(self):
        self.assertFalse(tools.is_core_lib('/usr/lib/python2.7/dist-packages/raspiot/libs/dummy.py'))
        self.assertFalse(tools.is_core_lib('/usr/lib/python2.7/dist-packages/raspiot/libs/internals/dummy.py'))
        self.assertTrue(tools.is_core_lib('/usr/lib/python2.7/dist-packages/raspiot/libs/internals/task.py'))
        self.assertTrue(tools.is_core_lib('/usr/lib/python2.7/dist-packages/raspiot/libs/drivers/driver.py'))
        self.assertFalse(tools.is_core_lib('/usr/lib/python2.7/dist-packages/raspiot/libs/drivers/dummy.py'))
        self.assertTrue(tools.is_core_lib('/usr/lib/python2.7/dist-packages/raspiot/libs/commands/alsa.py'))
        self.assertFalse(tools.is_core_lib('/usr/lib/python2.7/dist-packages/raspiot/libs/commands/dummy.py'))
        self.assertTrue(tools.is_core_lib('/usr/lib/python2.7/dist-packages/raspiot/libs/configs/config.py'))
        self.assertFalse(tools.is_core_lib('/usr/lib/python2.7/dist-packages/raspiot/libs/configs/dummy.py'))
        self.assertFalse(tools.is_core_lib('/usr/lib/python2.7/dist-packages/raspiot/libs/dummy/task.py'))
        self.assertTrue(tools.is_core_lib('/usr/lib/raspiot/libs/internals/task.py'))
        self.assertFalse(tools.is_core_lib('libs/task.py'))

class ToolsTestsLogLevelTrace(unittest.TestCase):

    def test_install_trace_logging_level_for_custom_loggers(self):
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        tools.install_trace_logging_level()
        logger = logging.getLogger('test_trace_before')
        try:
            logger.setLevel(logging.TRACE)
            logger.trace('trace message')
        except:
            self.fail('logging.TRACE not installed')

    def test_install_trace_logging_level_for_root_logger(self):
        tools.install_trace_logging_level()
        try:
            logging.basicConfig(level=logging.TRACE, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
            logging.trace('trace message')
        except:
            self.fail('logging.TRACE not installed')

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","*test_*.py" --concurrency=thread test_tools.py; coverage report -m -i
    unittest.main()

