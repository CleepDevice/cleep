#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.tests.lib import TestLib
import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from cleepgithub import CleepGithub
import unittest
import logging
import json
from unittest.mock import Mock
from copy import deepcopy
import responses
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()


GET_API_RATE = {
  "resources": {
    "core": {
      "limit": 60,
      "remaining": 46,
      "reset": 1582901790
    },
    "search": {
      "limit": 10,
      "remaining": 10,
      "reset": 1582900028
    },
    "graphql": {
      "limit": 0,
      "remaining": 0,
      "reset": 1582903568
    },
    "integration_manifest": {
      "limit": 5000,
      "remaining": 5000,
      "reset": 1582903568
    },
    "source_import": {
      "limit": 5,
      "remaining": 5,
      "reset": 1582900028
    }
  },
  "rate": {
    "limit": 60,
    "remaining": 46,
    "reset": 1582901790
  }
}

GET_RELEASES = [
{'assets': [{'browser_download_url': 'https://github.com/tangb/cleep/releases/download/v0.0.18/cleep_0.0.18.sha256',
               'content_type': 'application/octet-stream',
               'created_at': '2019-02-25T21:21:59Z',
               'download_count': 419,
               'id': 11238731,
               'label': '',
               'name': 'cleep_0.0.18.sha256',
               'node_id': 'MDEyOlJlbGVhc2VBc3NldDExMjM4NzMx',
               'size': 83,
               'state': 'uploaded',
               'updated_at': '2019-02-25T21:21:59Z',
               'uploader': {'avatar_url': 'https://avatars1.githubusercontent.com/u/2676511?v=4',
                             'events_url': 'https://api.github.com/users/tangb/events{/privacy}',
                             'followers_url': 'https://api.github.com/users/tangb/followers',
                             'following_url': 'https://api.github.com/users/tangb/following{/other_user}',
                             'gists_url': 'https://api.github.com/users/tangb/gists{/gist_id}',
                             'gravatar_id': '',
                             'html_url': 'https://github.com/tangb',
                             'id': 2676511,
                             'login': 'tangb',
                             'node_id': 'MDQ6VXNlcjI2NzY1MTE=',
                             'organizations_url': 'https://api.github.com/users/tangb/orgs',
                             'received_events_url': 'https://api.github.com/users/tangb/received_events',
                             'repos_url': 'https://api.github.com/users/tangb/repos',
                             'site_admin': False,
                             'starred_url': 'https://api.github.com/users/tangb/starred{/owner}{/repo}',
                             'subscriptions_url': 'https://api.github.com/users/tangb/subscriptions',
                             'type': 'User',
                             'url': 'https://api.github.com/users/tangb'},
               'url': 'https://api.github.com/repos/tangb/cleep/releases/assets/11238731'},
              {'browser_download_url': 'https://github.com/tangb/cleep/releases/download/v0.0.18/cleep_0.0.18.zip',
               'content_type': 'application/octet-stream',
               'created_at': '2019-02-25T20:04:58Z',
               'download_count': 14,
               'id': 11237840,
               'label': '',
               'name': 'cleep_0.0.18.zip',
               'node_id': 'MDEyOlJlbGVhc2VBc3NldDExMjM3ODQw',
               'size': 727221751,
               'state': 'uploaded',
               'updated_at': '2019-02-25T21:21:58Z',
               'uploader': {'avatar_url': 'https://avatars1.githubusercontent.com/u/2676511?v=4',
                             'events_url': 'https://api.github.com/users/tangb/events{/privacy}',
                             'followers_url': 'https://api.github.com/users/tangb/followers',
                             'following_url': 'https://api.github.com/users/tangb/following{/other_user}',
                             'gists_url': 'https://api.github.com/users/tangb/gists{/gist_id}',
                             'gravatar_id': '',
                             'html_url': 'https://github.com/tangb',
                             'id': 2676511,
                             'login': 'tangb',
                             'node_id': 'MDQ6VXNlcjI2NzY1MTE=',
                             'organizations_url': 'https://api.github.com/users/tangb/orgs',
                             'received_events_url': 'https://api.github.com/users/tangb/received_events',
                             'repos_url': 'https://api.github.com/users/tangb/repos',
                             'site_admin': False,
                             'starred_url': 'https://api.github.com/users/tangb/starred{/owner}{/repo}',
                             'subscriptions_url': 'https://api.github.com/users/tangb/subscriptions',
                             'type': 'User',
                             'url': 'https://api.github.com/users/tangb'},
               'url': 'https://api.github.com/repos/tangb/cleep/releases/assets/11237840'},
              {'browser_download_url': 'https://github.com/tangb/cleep/releases/download/v0.0.18/cleep_0.0.18.sha256',
               'content_type': 'application/octet-stream',
               'created_at': '2019-02-25T13:28:37Z',
               'download_count': 58,
               'id': 11231657,
               'label': None,
               'name': 'cleep_0.0.18.sha256',
               'node_id': 'MDEyOlJlbGVhc2VBc3NldDExMjMxNjU3',
               'size': 85,
               'state': 'uploaded',
               'updated_at': '2019-02-25T13:28:38Z',
               'uploader': {'avatar_url': 'https://avatars1.githubusercontent.com/u/2676511?v=4',
                             'events_url': 'https://api.github.com/users/tangb/events{/privacy}',
                             'followers_url': 'https://api.github.com/users/tangb/followers',
                             'following_url': 'https://api.github.com/users/tangb/following{/other_user}',
                             'gists_url': 'https://api.github.com/users/tangb/gists{/gist_id}',
                             'gravatar_id': '',
                             'html_url': 'https://github.com/tangb',
                             'id': 2676511,
                             'login': 'tangb',
                             'node_id': 'MDQ6VXNlcjI2NzY1MTE=',
                             'organizations_url': 'https://api.github.com/users/tangb/orgs',
                             'received_events_url': 'https://api.github.com/users/tangb/received_events',
                             'repos_url': 'https://api.github.com/users/tangb/repos',
                             'site_admin': False,
                             'starred_url': 'https://api.github.com/users/tangb/starred{/owner}{/repo}',
                             'subscriptions_url': 'https://api.github.com/users/tangb/subscriptions',
                             'type': 'User',
                             'url': 'https://api.github.com/users/tangb'},
               'url': 'https://api.github.com/repos/tangb/cleep/releases/assets/11231657'},
              {'browser_download_url': 'https://github.com/tangb/cleep/releases/download/v0.0.18/cleep_0.0.18.zip',
               'content_type': 'application/x-zip-compressed',
               'created_at': '2019-02-25T13:28:37Z',
               'download_count': 59,
               'id': 11231658,
               'label': None,
               'name': 'cleep_0.0.18.zip',
               'node_id': 'MDEyOlJlbGVhc2VBc3NldDExMjMxNjU4',
               'size': 3769652,
               'state': 'uploaded',
               'updated_at': '2019-02-25T13:30:47Z',
               'uploader': {'avatar_url': 'https://avatars1.githubusercontent.com/u/2676511?v=4',
                             'events_url': 'https://api.github.com/users/tangb/events{/privacy}',
                             'followers_url': 'https://api.github.com/users/tangb/followers',
                             'following_url': 'https://api.github.com/users/tangb/following{/other_user}',
                             'gists_url': 'https://api.github.com/users/tangb/gists{/gist_id}',
                             'gravatar_id': '',
                             'html_url': 'https://github.com/tangb',
                             'id': 2676511,
                             'login': 'tangb',
                             'node_id': 'MDQ6VXNlcjI2NzY1MTE=',
                             'organizations_url': 'https://api.github.com/users/tangb/orgs',
                             'received_events_url': 'https://api.github.com/users/tangb/received_events',
                             'repos_url': 'https://api.github.com/users/tangb/repos',
                             'site_admin': False,
                             'starred_url': 'https://api.github.com/users/tangb/starred{/owner}{/repo}',
                             'subscriptions_url': 'https://api.github.com/users/tangb/subscriptions',
                             'type': 'User',
                             'url': 'https://api.github.com/users/tangb'},
               'url': 'https://api.github.com/repos/tangb/cleep/releases/assets/11231658'}],
  'assets_url': 'https://api.github.com/repos/tangb/cleep/releases/15754939/assets',
  'author': {'avatar_url': 'https://avatars1.githubusercontent.com/u/2676511?v=4',
              'events_url': 'https://api.github.com/users/tangb/events{/privacy}',
              'followers_url': 'https://api.github.com/users/tangb/followers',
              'following_url': 'https://api.github.com/users/tangb/following{/other_user}',
              'gists_url': 'https://api.github.com/users/tangb/gists{/gist_id}',
              'gravatar_id': '',
              'html_url': 'https://github.com/tangb',
              'id': 2676511,
              'login': 'tangb',
              'node_id': 'MDQ6VXNlcjI2NzY1MTE=',
              'organizations_url': 'https://api.github.com/users/tangb/orgs',
              'received_events_url': 'https://api.github.com/users/tangb/received_events',
              'repos_url': 'https://api.github.com/users/tangb/repos',
              'site_admin': False,
              'starred_url': 'https://api.github.com/users/tangb/starred{/owner}{/repo}',
              'subscriptions_url': 'https://api.github.com/users/tangb/subscriptions',
              'type': 'User',
              'url': 'https://api.github.com/users/tangb'},
  'body': '* Improve module install/uninstall/update process\r\n* Remove some gpios stuff to gpios module (gpiosPin component)',
  'created_at': '2018-10-09T10:33:55Z',
  'draft': False,
  'html_url': 'https://github.com/tangb/cleep/releases/tag/v0.0.18',
  'id': 15754939,
  'name': '0.0.18',
  'node_id': 'MDc6UmVsZWFzZTE1NzU0OTM5',
  'prerelease': False,
  'published_at': '2019-02-25T13:30:49Z',
  'tag_name': 'v0.0.18',
  'tarball_url': 'https://api.github.com/repos/tangb/cleep/tarball/v0.0.18',
  'target_commitish': 'master',
  'upload_url': 'https://uploads.github.com/repos/tangb/cleep/releases/15754939/assets{?name,label}',
  'url': 'https://api.github.com/repos/tangb/cleep/releases/15754939',
  'zipball_url': 'https://api.github.com/repos/tangb/cleep/zipball/v0.0.18'},
{'assets': [{'browser_download_url': 'https://github.com/tangb/cleep/releases/download/v0.0.13/cleep_0.0.13.sha256',
               'content_type': 'application/octet-stream',
               'created_at': '2018-09-27T05:35:54Z',
               'download_count': 0,
               'id': 8863737,
               'label': '',
               'name': 'cleep_0.0.13.sha256',
               'node_id': 'MDEyOlJlbGVhc2VBc3NldDg4NjM3Mzc=',
               'size': 83,
               'state': 'uploaded',
               'updated_at': '2018-09-27T05:35:55Z',
               'uploader': {'avatar_url': 'https://avatars1.githubusercontent.com/u/2676511?v=4',
                             'events_url': 'https://api.github.com/users/tangb/events{/privacy}',
                             'followers_url': 'https://api.github.com/users/tangb/followers',
                             'following_url': 'https://api.github.com/users/tangb/following{/other_user}',
                             'gists_url': 'https://api.github.com/users/tangb/gists{/gist_id}',
                             'gravatar_id': '',
                             'html_url': 'https://github.com/tangb',
                             'id': 2676511,
                             'login': 'tangb',
                             'node_id': 'MDQ6VXNlcjI2NzY1MTE=',
                             'organizations_url': 'https://api.github.com/users/tangb/orgs',
                             'received_events_url': 'https://api.github.com/users/tangb/received_events',
                             'repos_url': 'https://api.github.com/users/tangb/repos',
                             'site_admin': False,
                             'starred_url': 'https://api.github.com/users/tangb/starred{/owner}{/repo}',
                             'subscriptions_url': 'https://api.github.com/users/tangb/subscriptions',
                             'type': 'User',
                             'url': 'https://api.github.com/users/tangb'},
               'url': 'https://api.github.com/repos/tangb/cleep/releases/assets/8863737'},
              {'browser_download_url': 'https://github.com/tangb/cleep/releases/download/v0.0.13/cleep_0.0.13.zip',
               'content_type': 'application/octet-stream',
               'created_at': '2018-09-26T20:13:38Z',
               'download_count': 0,
               'id': 8856998,
               'label': '',
               'name': 'cleep_0.0.13.zip',
               'node_id': 'MDEyOlJlbGVhc2VBc3NldDg4NTY5OTg=',
               'size': 732660023,
               'state': 'uploaded',
               'updated_at': '2018-09-26T21:37:27Z',
               'uploader': {'avatar_url': 'https://avatars1.githubusercontent.com/u/2676511?v=4',
                             'events_url': 'https://api.github.com/users/tangb/events{/privacy}',
                             'followers_url': 'https://api.github.com/users/tangb/followers',
                             'following_url': 'https://api.github.com/users/tangb/following{/other_user}',
                             'gists_url': 'https://api.github.com/users/tangb/gists{/gist_id}',
                             'gravatar_id': '',
                             'html_url': 'https://github.com/tangb',
                             'id': 2676511,
                             'login': 'tangb',
                             'node_id': 'MDQ6VXNlcjI2NzY1MTE=',
                             'organizations_url': 'https://api.github.com/users/tangb/orgs',
                             'received_events_url': 'https://api.github.com/users/tangb/received_events',
                             'repos_url': 'https://api.github.com/users/tangb/repos',
                             'site_admin': False,
                             'starred_url': 'https://api.github.com/users/tangb/starred{/owner}{/repo}',
                             'subscriptions_url': 'https://api.github.com/users/tangb/subscriptions',
                             'type': 'User',
                             'url': 'https://api.github.com/users/tangb'},
               'url': 'https://api.github.com/repos/tangb/cleep/releases/assets/8856998'},
              {'browser_download_url': 'https://github.com/tangb/cleep/releases/download/v0.0.13/cleep_0.0.13.sha256',
               'content_type': 'application/octet-stream',
               'created_at': '2018-09-25T22:12:08Z',
               'download_count': 1,
               'id': 8841647,
               'label': '',
               'name': 'cleep_0.0.13.sha256',
               'node_id': 'MDEyOlJlbGVhc2VBc3NldDg4NDE2NDc=',
               'size': 85,
               'state': 'uploaded',
               'updated_at': '2018-09-25T22:12:08Z',
               'uploader': {'avatar_url': 'https://avatars1.githubusercontent.com/u/2676511?v=4',
                             'events_url': 'https://api.github.com/users/tangb/events{/privacy}',
                             'followers_url': 'https://api.github.com/users/tangb/followers',
                             'following_url': 'https://api.github.com/users/tangb/following{/other_user}',
                             'gists_url': 'https://api.github.com/users/tangb/gists{/gist_id}',
                             'gravatar_id': '',
                             'html_url': 'https://github.com/tangb',
                             'id': 2676511,
                             'login': 'tangb',
                             'node_id': 'MDQ6VXNlcjI2NzY1MTE=',
                             'organizations_url': 'https://api.github.com/users/tangb/orgs',
                             'received_events_url': 'https://api.github.com/users/tangb/received_events',
                             'repos_url': 'https://api.github.com/users/tangb/repos',
                             'site_admin': False,
                             'starred_url': 'https://api.github.com/users/tangb/starred{/owner}{/repo}',
                             'subscriptions_url': 'https://api.github.com/users/tangb/subscriptions',
                             'type': 'User',
                             'url': 'https://api.github.com/users/tangb'},
               'url': 'https://api.github.com/repos/tangb/cleep/releases/assets/8841647'},
              {'browser_download_url': 'https://github.com/tangb/cleep/releases/download/v0.0.13/cleep_0.0.13.zip',
               'content_type': 'application/octet-stream',
               'created_at': '2018-09-25T22:11:37Z',
               'download_count': 1,
               'id': 8841630,
               'label': '',
               'name': 'cleep_0.0.13.zip',
               'node_id': 'MDEyOlJlbGVhc2VBc3NldDg4NDE2MzA=',
               'size': 3864670,
               'state': 'uploaded',
               'updated_at': '2018-09-25T22:12:07Z',
               'uploader': {'avatar_url': 'https://avatars1.githubusercontent.com/u/2676511?v=4',
                             'events_url': 'https://api.github.com/users/tangb/events{/privacy}',
                             'followers_url': 'https://api.github.com/users/tangb/followers',
                             'following_url': 'https://api.github.com/users/tangb/following{/other_user}',
                             'gists_url': 'https://api.github.com/users/tangb/gists{/gist_id}',
                             'gravatar_id': '',
                             'html_url': 'https://github.com/tangb',
                             'id': 2676511,
                             'login': 'tangb',
                             'node_id': 'MDQ6VXNlcjI2NzY1MTE=',
                             'organizations_url': 'https://api.github.com/users/tangb/orgs',
                             'received_events_url': 'https://api.github.com/users/tangb/received_events',
                             'repos_url': 'https://api.github.com/users/tangb/repos',
                             'site_admin': False,
                             'starred_url': 'https://api.github.com/users/tangb/starred{/owner}{/repo}',
                             'subscriptions_url': 'https://api.github.com/users/tangb/subscriptions',
                             'type': 'User',
                             'url': 'https://api.github.com/users/tangb'},
               'url': 'https://api.github.com/repos/tangb/cleep/releases/assets/8841630'}],
  'assets_url': 'https://api.github.com/repos/tangb/cleep/releases/13092235/assets',
  'author': {'avatar_url': 'https://avatars1.githubusercontent.com/u/2676511?v=4',
              'events_url': 'https://api.github.com/users/tangb/events{/privacy}',
              'followers_url': 'https://api.github.com/users/tangb/followers',
              'following_url': 'https://api.github.com/users/tangb/following{/other_user}',
              'gists_url': 'https://api.github.com/users/tangb/gists{/gist_id}',
              'gravatar_id': '',
              'html_url': 'https://github.com/tangb',
              'id': 2676511,
              'login': 'tangb',
              'node_id': 'MDQ6VXNlcjI2NzY1MTE=',
              'organizations_url': 'https://api.github.com/users/tangb/orgs',
              'received_events_url': 'https://api.github.com/users/tangb/received_events',
              'repos_url': 'https://api.github.com/users/tangb/repos',
              'site_admin': False,
              'starred_url': 'https://api.github.com/users/tangb/starred{/owner}{/repo}',
              'subscriptions_url': 'https://api.github.com/users/tangb/subscriptions',
              'type': 'User',
              'url': 'https://api.github.com/users/tangb'},
  'body': '* Remove completely all modules. Now they are external parts even system modules\r\n* Remove all formatters and keep only profiles\r\n* Fix some bugs and improve cleepos\r\n* Modules are only loaded by inventory now\r\n',
  'created_at': '2018-08-06T17:20:27Z',
  'draft': False,
  'html_url': 'https://github.com/tangb/cleep/releases/tag/v0.0.13',
  'id': 13092235,
  'name': '0.0.13',
  'node_id': 'MDc6UmVsZWFzZTEzMDkyMjM1',
  'prerelease': True,
  'published_at': '2018-09-26T12:05:53Z',
  'tag_name': 'v0.0.13',
  'tarball_url': 'https://api.github.com/repos/tangb/cleep/tarball/v0.0.13',
  'target_commitish': 'master',
  'upload_url': 'https://uploads.github.com/repos/tangb/cleep/releases/13092235/assets{?name,label}',
  'url': 'https://api.github.com/repos/tangb/cleep/releases/13092235',
  'zipball_url': 'https://api.github.com/repos/tangb/cleep/zipball/v0.0.13'},
]


class CleepGithubTests(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        TestLib()

        self.owner = 'dummy'
        self.repo = 'dummy'

    def tearDown(self):
        pass

    def _init_context(self, url, resp_data={}, resp_status=200, resp_headers={}):
        self.g = CleepGithub()
        responses.add(
            responses.GET,
            url,
            body=json.dumps(resp_data).encode('utf8'),
            headers=resp_headers,
            status=resp_status,
        )

    def test_auth_string(self):
        g = CleepGithub()
        self.assertFalse('Authorization' in g.http_headers)

        g = CleepGithub(auth_string='Bearer myjwt')
        self.assertTrue('Authorization' in g.http_headers)

    @responses.activate
    def test_get_releases(self):
        self._init_context(url=CleepGithub.GITHUB_URL % (self.owner, self.repo), resp_data=GET_RELEASES)
        releases = self.g.get_releases(self.owner, self.repo, only_latest=True, only_released=False)
        self.assertTrue(isinstance(releases, list))
        self.assertEqual(1, len(releases))

    @responses.activate
    def test_get_all_releases(self):
        self._init_context(url=CleepGithub.GITHUB_URL % (self.owner, self.repo), resp_data=GET_RELEASES)
        releases = self.g.get_releases(self.owner, self.repo, only_latest=False, only_released=False)
        logging.debug('Releases: %s' % releases)
        self.assertTrue(isinstance(releases, list))
        self.assertEqual(len(releases), 2)

    @responses.activate
    def test_unknown_repo(self):
        self._init_context(url=CleepGithub.GITHUB_URL % ('tangb', 'test'), resp_status=404)
        self.assertRaises(Exception, self.g.get_releases, 'tangb', 'test')

    @responses.activate
    def test_release_version(self):
        self._init_context(url=CleepGithub.GITHUB_URL % (self.owner, self.repo), resp_data=GET_RELEASES)
        releases = self.g.get_releases(self.owner, self.repo, only_latest=True, only_released=False)
        self.assertEqual(1, len(releases))
        version = self.g.get_release_version(releases[0])
        logging.debug('Version: %s' % version)
        self.assertEqual(version, '0.0.18')

    def test_release_version_with_invalid_release(self):
        self._init_context(url=CleepGithub.GITHUB_URL % (self.owner, self.repo), resp_data=GET_RELEASES)

        class Dummy():
            pass
        with self.assertRaises(Exception) as cm:
            self.g.get_release_version(Dummy())
        self.assertEqual(str(cm.exception), 'Invalid release format. Dict type awaited')

        with self.assertRaises(Exception) as cm:
            self.g.get_release_version({})
        self.assertEqual(str(cm.exception), 'Specified release has no version field')

    @responses.activate
    def test_release_version_raw_version(self):
        self._init_context(url=CleepGithub.GITHUB_URL % (self.owner, self.repo), resp_data=GET_RELEASES)

        releases = deepcopy(GET_RELEASES)
        release = releases[0]
        release['tag_name'] = 'myversion'

        version = self.g.get_release_version(release)
        self.assertEqual(version, 'myversion')

    @responses.activate
    def test_release_changelog(self):
        self._init_context(url=CleepGithub.GITHUB_URL % (self.owner, self.repo), resp_data=GET_RELEASES)
        releases = self.g.get_releases(self.owner, self.repo, only_latest=True, only_released=False)
        self.assertEqual(1, len(releases))
        changelog = self.g.get_release_changelog(releases[0])
        self.assertNotEqual(0, len(changelog.strip()))

    def test_release_changelog_with_invalid_release(self):
        self._init_context(url=CleepGithub.GITHUB_URL % (self.owner, self.repo), resp_data=GET_RELEASES)

        class Dummy():
            pass
        with self.assertRaises(Exception) as cm:
            self.g.get_release_changelog(Dummy())
        self.assertEqual(str(cm.exception), 'Invalid release format. Dict type awaited')

    def test_release_changelog_with_empty_changelog(self):
        self._init_context(url=CleepGithub.GITHUB_URL % (self.owner, self.repo), resp_data=GET_RELEASES)

        releases = deepcopy(GET_RELEASES)
        release = releases[0]
        del release['body']

        changelog = self.g.get_release_changelog(release)
        self.assertEqual(changelog, '')

    @responses.activate
    def test_get_release_assets_infos(self):
        self._init_context(url=CleepGithub.GITHUB_URL % (self.owner, self.repo), resp_data=GET_RELEASES)
        releases = self.g.get_releases(self.owner, self.repo, only_latest=True, only_released=False)
        self.assertEqual(1, len(releases))
        infos = self.g.get_release_assets_infos(releases[0])
        logging.debug(infos)

    def test_get_release_assets_infos_with_invalid_release(self):
        self._init_context(url='', resp_data=GET_RELEASES)

        class Dummy():
            pass
        with self.assertRaises(Exception) as cm:
            self.g.get_release_assets_infos(Dummy())
        self.assertEqual(str(cm.exception), 'Invalid release format. Dict type awaited')

        releases = deepcopy(GET_RELEASES)
        release = releases[0]
        del release['assets']
        with self.assertRaises(Exception) as cm:
            self.g.get_release_assets_infos(release)
        self.assertEqual(str(cm.exception), 'Invalid release format')

    @responses.activate
    def test_is_release(self):
        self._init_context(url=CleepGithub.GITHUB_URL % (self.owner, self.repo), resp_data=GET_RELEASES)
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

    def test_is_released_with_invalid_release(self):
        self._init_context(url=CleepGithub.GITHUB_URL % (self.owner, self.repo), resp_data=GET_RELEASES)

        class Dummy():
            pass
        with self.assertRaises(Exception) as cm:
            self.g.is_released(Dummy())
        self.assertEqual(str(cm.exception), 'Invalid release format. Dict type awaited')

    @responses.activate
    def test_api_rate(self):
        self._init_context(url=CleepGithub.GITHUB_RATE, resp_data=GET_API_RATE)
        rate = self.g.get_api_rate()
        logging.debug(rate)
        self.assertTrue('limit' in rate)
        self.assertTrue('remaining' in rate)
        self.assertTrue('reset' in rate)

    @responses.activate
    def test_api_rate_invalid_data_received(self):
        GET_API_RATE_ = deepcopy(GET_API_RATE)
        del GET_API_RATE_['rate']
        self._init_context(url=CleepGithub.GITHUB_RATE, resp_data=GET_API_RATE_)

        with self.assertRaises(Exception) as cm:
            self.g.get_api_rate()
        self.assertEqual(str(cm.exception), 'Unable to get api rate: Invalid data from github rate_limit request')

    @responses.activate
    def test_api_rate_invalid_response_status(self):
        self._init_context(url=CleepGithub.GITHUB_RATE, resp_status=500)
        with self.assertRaises(Exception) as cm:
            self.g.get_api_rate()
        self.assertEqual(str(cm.exception), 'Unable to get api rate: Invalid response (status=500)')


if __name__ == '__main__':
     # coverage run --omit="*/lib/python*/*","*test_*" --concurrency=thread test_cleepgithub.py; coverage report -m -i
     unittest.main()

