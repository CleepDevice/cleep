#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append('/root/cleep/raspiot/libs/commands')
from iwgetid import Iwgetid
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
from mock import Mock

class IwgetidTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.i = Iwgetid()

    def tearDown(self):
        pass

    def test_get_connections(self):
        self.i.command = Mock(return_value={
            'error': False,
            'killed': False,
            'stderr': [],
            'stdout': ['wlan0     ESSID:"mywifinetwork"']
        })
        self.i.get_last_return_code = Mock(return_value=0)

        connections = self.i.get_connections()
        logging.debug(connections)
        self.assertEqual(len(connections), 1, 'Connections list should contains 1 element')
        key = connections.keys()[0]
        self.assertTrue('network' in connections[key], 'Network key should exists in connection item')
        self.assertEqual(connections[key]['network'], 'mywifinetwork', 'Invalid returned network name')

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_iwgetid.py; coverage report -m
    unittest.main()
