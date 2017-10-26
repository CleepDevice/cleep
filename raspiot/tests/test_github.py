#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.github import Github
import unittest
import logging

logging.basicConfig(level=logging.WARN, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class GithubTests(unittest.TestCase):

    def setUp(self):
        self.g = Github()
        self.owner = 'resin-io'
        self.repo = 'etcher'

    def tearDown(self):
        pass

    def test_get_release(self):
        releases = self.g.get_releases(self.owner, self.repo)
        self.assertTrue(isinstance(releases, list))
        self.assertEqual(1, len(releases))

    def test_get_all_releases(self):
        release = self.g.get_releases(self.owner, self.repo)
        self.assertTrue(isinstance(release, list))
        self.assertNotEqual(0, len(release))

    def test_unknown_repo(self):
        self.assertRaises(Exception, self.g.get_releases, 'tangb', 'test')

    def test_release_version(self):
        releases = self.g.get_releases(self.owner, self.repo)
        self.assertEqual(1, len(releases))
        version = self.g.get_release_version(releases[0])
        self.assertNotEqual(0, len(version.strip()))

    def test_release_assets_infos(self):
        releases = self.g.get_releases(self.owner, self.repo)
        self.assertEqual(1, len(releases))
        infos = self.g.get_release_assets_infos(releases[0])
        print(infos)
