#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from etcasoundconf import EtcAsoundConf
from cleep.libs.internals.cleepfilesystem import CleepFilesystem
from cleep.exception import MissingParameter, InvalidParameter, CommandError
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from pprint import pformat
import io

logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class EtcAsoundConfTest(unittest.TestCase):

    FILE_NAME = 'asound.conf'
    CONTENT = u"""pcm.!default {
    type hw
    card 1
    device 2
}

ctl.!default {
    type hw
    card 0
}"""

    def setUp(self):
        TestLib()
        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.path = os.path.join(os.getcwd(), self.FILE_NAME)
        logging.debug('Using conf file "%s"' % self.path)

        #fill with default content
        with io.open(self.path, 'w') as f:
            f.write(self.CONTENT)

        e = EtcAsoundConf
        e.CONF = self.FILE_NAME
        self.e = e(self.fs)

    def tearDown(self):
        if os.path.exists('%s' % self.FILE_NAME):
            os.remove('%s' % self.FILE_NAME)

    def test_get_raw_configuration(self):
        conf = self.e.get_raw_configuration()
        logging.debug('conf=%s' % conf)
        self.assertTrue(isinstance(conf, dict))
        self.assertTrue('pcm.!default' in conf, 'Section "pcm.!default" does not exist')
        self.assertTrue('ctl.!default' in conf, 'Section "pcm.!default" does not exist')
        pcm = conf['pcm.!default']
        self.assertTrue('type' in pcm, 'Item "type" does not exist')
        self.assertTrue('card' in pcm, 'Item "card"  does not exist')
        self.assertTrue('device' in pcm, 'Item "device" does not exist')
        ctl = conf['ctl.!default']
        self.assertTrue('type' in ctl, 'Item "type" does not exist')
        self.assertTrue('card' in ctl, 'Item "card"  does not exist')
        self.assertFalse('device' in ctl, 'Item "device" should not exist')

    def test_get_default_pcm_section(self):
        pcm = self.e.get_default_pcm_section()
        self.assertTrue(isinstance(pcm, dict))
        self.assertTrue('type' in pcm, 'Item "type" does not exist')
        self.assertTrue('card' in pcm, 'Item "card"  does not exist')
        self.assertTrue('device' in pcm, 'Item "device" does not exist')

    def test_get_default_ctl_section(self):
        ctl = self.e.get_default_ctl_section()
        self.assertTrue(isinstance(ctl, dict))
        self.assertTrue('type' in ctl, 'Item "type" does not exist')
        self.assertTrue('card' in ctl, 'Item "card"  does not exist')
        self.assertFalse('device' in ctl, 'Item "device" should not exist')

    def test_add_default_pcm_section(self):
        #nothing addded because section already exists
        self.assertTrue(self.e.add_default_pcm_section(5))
        pcm = self.e.get_default_pcm_section()
        self.assertEqual(pcm['card'], 1)
        self.assertEqual(pcm['device'], 2)

    def test_add_default_pcm_section_invalid_params(self):
        with self.assertRaises(InvalidParameter) as cm:
            self.e.add_default_pcm_section(None)
        with self.assertRaises(InvalidParameter) as cm:
            self.e.add_default_pcm_section('')
        with self.assertRaises(InvalidParameter) as cm:
            self.e.add_default_pcm_section(5, None)
        with self.assertRaises(InvalidParameter) as cm:
            self.e.add_default_pcm_section(5, '')

    def test_add_default_ctl_section(self):
        #nothing addded because section already exists
        self.assertTrue(self.e.add_default_ctl_section(5))
        ctl = self.e.get_default_ctl_section()
        self.assertEqual(ctl['card'], 0)

    def test_add_default_ctl_section_invalid_params(self):
        with self.assertRaises(InvalidParameter) as cm:
            self.e.add_default_ctl_section(None)
        with self.assertRaises(InvalidParameter) as cm:
            self.e.add_default_ctl_section('')
        with self.assertRaises(InvalidParameter) as cm:
            self.e.add_default_ctl_section(5, None)
        with self.assertRaises(InvalidParameter) as cm:
            self.e.add_default_ctl_section(5, '')

    def test_save_default_file(self):
        self.assertTrue(self.e.save_default_file(5))
        conf = self.e.get_raw_configuration()
        self.assertTrue(isinstance(conf, dict))
        self.assertTrue('pcm.!default' in conf, 'Section "pcm.!default" does not exist')
        self.assertTrue('ctl.!default' in conf, 'Section "pcm.!default" does not exist')
        pcm = conf['pcm.!default']
        self.assertTrue('type' in pcm, 'Item "type" does not exist')
        self.assertTrue('card' in pcm, 'Item "card"  does not exist')
        self.assertFalse('device' in pcm, 'Item "device" does not exist')
        self.assertEqual(pcm['card'], 5)
        ctl = conf['ctl.!default']
        self.assertTrue('type' in ctl, 'Item "type" does not exist')
        self.assertTrue('card' in ctl, 'Item "card"  does not exist')
        self.assertFalse('device' in ctl, 'Item "device" should not exist')
        self.assertEqual(ctl['card'], 5)

    def test_dave_default_file_invalid_parameters(self):
        with self.assertRaises(InvalidParameter) as cm:
            self.e.save_default_file(None)
        with self.assertRaises(InvalidParameter) as cm:
            self.e.save_default_file('')
        with self.assertRaises(InvalidParameter) as cm:
            self.e.save_default_file(5, None)
        with self.assertRaises(InvalidParameter) as cm:
            self.e.save_default_file(5, '')

    def test_delete(self):
        with io.open(self.e.ASOUND_STATE, 'w') as fd:
            fd.write(u'')
        self.assertTrue(self.e.delete(), 'File not deleted')

    def test_delete_non_existing_file(self):
        os.remove(self.FILE_NAME)
        self.assertTrue(self.e.delete())



class EtcAsoundConfTestNoPcmSection(unittest.TestCase):

    FILE_NAME = 'asound.conf'
    CONTENT = u"""ctl.!default {
    type hw
    card 0
}"""

    def setUp(self):
        TestLib()
        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.path = os.path.join(os.getcwd(), self.FILE_NAME)
        logging.debug('Using conf file "%s"' % self.path)

        #fill with default content
        with io.open(self.path, 'w') as f:
            f.write(self.CONTENT)

        e = EtcAsoundConf
        e.CONF = self.FILE_NAME
        self.e = e(self.fs)

    def tearDown(self):
        if os.path.exists('%s' % self.FILE_NAME):
            os.remove('%s' % self.FILE_NAME)

    def test_add_default_pcm_section(self):
        self.assertTrue(self.e.add_default_pcm_section(666))
        pcm = self.e.get_default_pcm_section()
        self.assertEqual(pcm['card'], 666)
        self.assertTrue('device' in pcm)
        self.assertEqual(pcm['device'], 0)

    def test_add_default_pcm_section_with_device_id(self):
        self.assertTrue(self.e.add_default_pcm_section(666, 999))
        pcm = self.e.get_default_pcm_section()
        self.assertEqual(pcm['card'], 666)
        self.assertEqual(pcm['device'], 999)



class EtcAsoundConfTestNoCtlSection(unittest.TestCase):

    FILE_NAME = 'asound.conf'
    CONTENT = u"""pcm.!default {
    type hw
    card 1
    device 2
}"""

    def setUp(self):
        TestLib()
        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.path = os.path.join(os.getcwd(), self.FILE_NAME)
        logging.debug('Using conf file "%s"' % self.path)

        #fill with default content
        with io.open(self.path, 'w') as f:
            f.write(self.CONTENT)

        e = EtcAsoundConf
        e.CONF = self.FILE_NAME
        self.e = e(self.fs)

    def tearDown(self):
        if os.path.exists('%s' % self.FILE_NAME):
            os.remove('%s' % self.FILE_NAME)

    def test_add_default_ctl_section(self):
        self.assertTrue(self.e.add_default_ctl_section(666))
        ctl = self.e.get_default_ctl_section()
        self.assertEqual(ctl['card'], 666)
        self.assertFalse('device' in ctl)

    def test_add_default_ctl_section_with_device_id(self):
        self.assertTrue(self.e.add_default_ctl_section(666, 999))
        ctl = self.e.get_default_ctl_section()
        self.assertEqual(ctl['card'], 666)
        self.assertEqual(ctl['device'], 999)


if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python*/*","*test_*.py" --concurrency=thread test_etcasoundconf.py; coverage report -m -i
    unittest.main()

