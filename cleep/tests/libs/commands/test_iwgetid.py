#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from iwgetid import Iwgetid
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from unittest.mock import Mock

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
        key = list(connections.keys())[0]
        self.assertTrue('network' in connections[key], 'Network key should exists in connection item')
        self.assertEqual(connections[key]['network'], 'mywifinetwork', 'Invalid returned network name')

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python*/*","*test_*.py" --concurrency=thread test_iwgetid.py; coverage report -m -i
    unittest.main()