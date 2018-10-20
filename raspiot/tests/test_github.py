#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.internals.github import Github
import unittest
import logging

logging.basicConfig(level=logging.WARN, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class GithubTests(unittest.TestCase):

    def setUp(self):
        self.g = Github()
        self.owner = 'tangb'
        self.repo = 'raspiot'

    def tearDown(self):
        pass

    def test_get_releases(self):
        releases = self.g.get_releases(self.owner, self.repo, only_latest=True, only_released=False)
        self.assertTrue(isinstance(releases, list))
        self.assertEqual(1, len(releases))

    def test_get_all_releases(self):
        release = self.g.get_releases(self.owner, self.repo, only_latest=False, only_released=False)
        self.assertTrue(isinstance(release, list))
        self.assertNotEqual(0, len(release))

    def test_unknown_repo(self):
        self.assertRaises(Exception, self.g.get_releases, 'tangb', 'test')

    def test_release_version_changelog(self):
        releases = self.g.get_releases(self.owner, self.repo, only_latest=True, only_released=False)
        self.assertEqual(1, len(releases))
        version = self.g.get_release_version(releases[0])
        changelog = self.g.get_release_changelog(releases[0])
        self.assertNotEqual(0, len(version.strip()))
        self.assertNotEqual(0, len(changelog.strip()))

    def test_release_assets_infos(self):
        releases = self.g.get_releases(self.owner, self.repo, only_latest=True, only_released=False)
        self.assertEqual(1, len(releases))
        infos = self.g.get_release_assets_infos(releases[0])
        logging.debug(infos)

    def test_released_release(self):
        releases = self.g.get_releases(self.owner, self.repo, only_released=True)
        for release in releases:
            self.assertTrue(self.g.is_released(release))

        releases = self.g.get_releases(self.owner, self.repo, only_released=False)
        released = 0
        unreleased = 0
        for release in releases:
            if self.g.is_released(release):
                released += 1
            else:
                unreleased += 1
        self.assertNotEqual(0, released)
        self.assertNotEqual(0, unreleased)

    def test_api_rate(self):
        rate = self.g.get_api_rate()
        logging.debug(rate)
        self.assertTrue(u'limit' in rate)
        self.assertTrue(u'remaining' in rate)
        self.assertTrue(u'reset' in rate)

