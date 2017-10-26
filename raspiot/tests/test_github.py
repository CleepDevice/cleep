#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.github import Github
import unittest
import logging

logging.basicConfig(level=logging.WARN, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class GithubTests(unittest.TestCase):

    def setUp(self):
        self.g = Github()

    def tearDown(self):
        pass

    def test_get_release(self):
        release = self.g.get_releases('resin-io', 'etcher')
        self.assertTrue(isinstance(release, list))
        self.assertEqual(1, len(release))
        release = release[0]
        self.assertTrue('browser_download_url' in release.keys())
        self.assertTrue('name' in release.keys())
        self.assertTrue('size' in release.keys())
        self.assertNotEqual(0, len(release['browser_download_url']))
        self.assertNotEqual(0, len(release['name']))

    def test_get_all_releases(self):
        release = self.g.get_releases('resin-io', 'etcher')
        self.assertTrue(isinstance(release, list))
        self.assertNotEqual(0, len(release))

    def test_unknown_repo(self):
        self.assertRaises(Exception, self.g.get_releases, 'tangb', 'test')
