#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append('%s/../../../libs/internals' % os.getcwd())
from cleepgithub import CleepGithub
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
import json
from mock import Mock
from copy import deepcopy

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
{u'assets': [{u'browser_download_url': u'https://github.com/tangb/raspiot/releases/download/v0.0.18/cleep_0.0.18.sha256',
               u'content_type': u'application/octet-stream',
               u'created_at': u'2019-02-25T21:21:59Z',
               u'download_count': 419,
               u'id': 11238731,
               u'label': u'',
               u'name': u'cleep_0.0.18.sha256',
               u'node_id': u'MDEyOlJlbGVhc2VBc3NldDExMjM4NzMx',
               u'size': 83,
               u'state': u'uploaded',
               u'updated_at': u'2019-02-25T21:21:59Z',
               u'uploader': {u'avatar_url': u'https://avatars1.githubusercontent.com/u/2676511?v=4',
                             u'events_url': u'https://api.github.com/users/tangb/events{/privacy}',
                             u'followers_url': u'https://api.github.com/users/tangb/followers',
                             u'following_url': u'https://api.github.com/users/tangb/following{/other_user}',
                             u'gists_url': u'https://api.github.com/users/tangb/gists{/gist_id}',
                             u'gravatar_id': u'',
                             u'html_url': u'https://github.com/tangb',
                             u'id': 2676511,
                             u'login': u'tangb',
                             u'node_id': u'MDQ6VXNlcjI2NzY1MTE=',
                             u'organizations_url': u'https://api.github.com/users/tangb/orgs',
                             u'received_events_url': u'https://api.github.com/users/tangb/received_events',
                             u'repos_url': u'https://api.github.com/users/tangb/repos',
                             u'site_admin': False,
                             u'starred_url': u'https://api.github.com/users/tangb/starred{/owner}{/repo}',
                             u'subscriptions_url': u'https://api.github.com/users/tangb/subscriptions',
                             u'type': u'User',
                             u'url': u'https://api.github.com/users/tangb'},
               u'url': u'https://api.github.com/repos/tangb/raspiot/releases/assets/11238731'},
              {u'browser_download_url': u'https://github.com/tangb/raspiot/releases/download/v0.0.18/cleep_0.0.18.zip',
               u'content_type': u'application/octet-stream',
               u'created_at': u'2019-02-25T20:04:58Z',
               u'download_count': 14,
               u'id': 11237840,
               u'label': u'',
               u'name': u'cleep_0.0.18.zip',
               u'node_id': u'MDEyOlJlbGVhc2VBc3NldDExMjM3ODQw',
               u'size': 727221751,
               u'state': u'uploaded',
               u'updated_at': u'2019-02-25T21:21:58Z',
               u'uploader': {u'avatar_url': u'https://avatars1.githubusercontent.com/u/2676511?v=4',
                             u'events_url': u'https://api.github.com/users/tangb/events{/privacy}',
                             u'followers_url': u'https://api.github.com/users/tangb/followers',
                             u'following_url': u'https://api.github.com/users/tangb/following{/other_user}',
                             u'gists_url': u'https://api.github.com/users/tangb/gists{/gist_id}',
                             u'gravatar_id': u'',
                             u'html_url': u'https://github.com/tangb',
                             u'id': 2676511,
                             u'login': u'tangb',
                             u'node_id': u'MDQ6VXNlcjI2NzY1MTE=',
                             u'organizations_url': u'https://api.github.com/users/tangb/orgs',
                             u'received_events_url': u'https://api.github.com/users/tangb/received_events',
                             u'repos_url': u'https://api.github.com/users/tangb/repos',
                             u'site_admin': False,
                             u'starred_url': u'https://api.github.com/users/tangb/starred{/owner}{/repo}',
                             u'subscriptions_url': u'https://api.github.com/users/tangb/subscriptions',
                             u'type': u'User',
                             u'url': u'https://api.github.com/users/tangb'},
               u'url': u'https://api.github.com/repos/tangb/raspiot/releases/assets/11237840'},
              {u'browser_download_url': u'https://github.com/tangb/raspiot/releases/download/v0.0.18/raspiot_0.0.18.sha256',
               u'content_type': u'application/octet-stream',
               u'created_at': u'2019-02-25T13:28:37Z',
               u'download_count': 58,
               u'id': 11231657,
               u'label': None,
               u'name': u'raspiot_0.0.18.sha256',
               u'node_id': u'MDEyOlJlbGVhc2VBc3NldDExMjMxNjU3',
               u'size': 85,
               u'state': u'uploaded',
               u'updated_at': u'2019-02-25T13:28:38Z',
               u'uploader': {u'avatar_url': u'https://avatars1.githubusercontent.com/u/2676511?v=4',
                             u'events_url': u'https://api.github.com/users/tangb/events{/privacy}',
                             u'followers_url': u'https://api.github.com/users/tangb/followers',
                             u'following_url': u'https://api.github.com/users/tangb/following{/other_user}',
                             u'gists_url': u'https://api.github.com/users/tangb/gists{/gist_id}',
                             u'gravatar_id': u'',
                             u'html_url': u'https://github.com/tangb',
                             u'id': 2676511,
                             u'login': u'tangb',
                             u'node_id': u'MDQ6VXNlcjI2NzY1MTE=',
                             u'organizations_url': u'https://api.github.com/users/tangb/orgs',
                             u'received_events_url': u'https://api.github.com/users/tangb/received_events',
                             u'repos_url': u'https://api.github.com/users/tangb/repos',
                             u'site_admin': False,
                             u'starred_url': u'https://api.github.com/users/tangb/starred{/owner}{/repo}',
                             u'subscriptions_url': u'https://api.github.com/users/tangb/subscriptions',
                             u'type': u'User',
                             u'url': u'https://api.github.com/users/tangb'},
               u'url': u'https://api.github.com/repos/tangb/raspiot/releases/assets/11231657'},
              {u'browser_download_url': u'https://github.com/tangb/raspiot/releases/download/v0.0.18/raspiot_0.0.18.zip',
               u'content_type': u'application/x-zip-compressed',
               u'created_at': u'2019-02-25T13:28:37Z',
               u'download_count': 59,
               u'id': 11231658,
               u'label': None,
               u'name': u'raspiot_0.0.18.zip',
               u'node_id': u'MDEyOlJlbGVhc2VBc3NldDExMjMxNjU4',
               u'size': 3769652,
               u'state': u'uploaded',
               u'updated_at': u'2019-02-25T13:30:47Z',
               u'uploader': {u'avatar_url': u'https://avatars1.githubusercontent.com/u/2676511?v=4',
                             u'events_url': u'https://api.github.com/users/tangb/events{/privacy}',
                             u'followers_url': u'https://api.github.com/users/tangb/followers',
                             u'following_url': u'https://api.github.com/users/tangb/following{/other_user}',
                             u'gists_url': u'https://api.github.com/users/tangb/gists{/gist_id}',
                             u'gravatar_id': u'',
                             u'html_url': u'https://github.com/tangb',
                             u'id': 2676511,
                             u'login': u'tangb',
                             u'node_id': u'MDQ6VXNlcjI2NzY1MTE=',
                             u'organizations_url': u'https://api.github.com/users/tangb/orgs',
                             u'received_events_url': u'https://api.github.com/users/tangb/received_events',
                             u'repos_url': u'https://api.github.com/users/tangb/repos',
                             u'site_admin': False,
                             u'starred_url': u'https://api.github.com/users/tangb/starred{/owner}{/repo}',
                             u'subscriptions_url': u'https://api.github.com/users/tangb/subscriptions',
                             u'type': u'User',
                             u'url': u'https://api.github.com/users/tangb'},
               u'url': u'https://api.github.com/repos/tangb/raspiot/releases/assets/11231658'}],
  u'assets_url': u'https://api.github.com/repos/tangb/raspiot/releases/15754939/assets',
  u'author': {u'avatar_url': u'https://avatars1.githubusercontent.com/u/2676511?v=4',
              u'events_url': u'https://api.github.com/users/tangb/events{/privacy}',
              u'followers_url': u'https://api.github.com/users/tangb/followers',
              u'following_url': u'https://api.github.com/users/tangb/following{/other_user}',
              u'gists_url': u'https://api.github.com/users/tangb/gists{/gist_id}',
              u'gravatar_id': u'',
              u'html_url': u'https://github.com/tangb',
              u'id': 2676511,
              u'login': u'tangb',
              u'node_id': u'MDQ6VXNlcjI2NzY1MTE=',
              u'organizations_url': u'https://api.github.com/users/tangb/orgs',
              u'received_events_url': u'https://api.github.com/users/tangb/received_events',
              u'repos_url': u'https://api.github.com/users/tangb/repos',
              u'site_admin': False,
              u'starred_url': u'https://api.github.com/users/tangb/starred{/owner}{/repo}',
              u'subscriptions_url': u'https://api.github.com/users/tangb/subscriptions',
              u'type': u'User',
              u'url': u'https://api.github.com/users/tangb'},
  u'body': u'* Improve module install/uninstall/update process\r\n* Remove some gpios stuff to gpios module (gpiosPin component)',
  u'created_at': u'2018-10-09T10:33:55Z',
  u'draft': False,
  u'html_url': u'https://github.com/tangb/raspiot/releases/tag/v0.0.18',
  u'id': 15754939,
  u'name': u'0.0.18',
  u'node_id': u'MDc6UmVsZWFzZTE1NzU0OTM5',
  u'prerelease': False,
  u'published_at': u'2019-02-25T13:30:49Z',
  u'tag_name': u'v0.0.18',
  u'tarball_url': u'https://api.github.com/repos/tangb/raspiot/tarball/v0.0.18',
  u'target_commitish': u'master',
  u'upload_url': u'https://uploads.github.com/repos/tangb/raspiot/releases/15754939/assets{?name,label}',
  u'url': u'https://api.github.com/repos/tangb/raspiot/releases/15754939',
  u'zipball_url': u'https://api.github.com/repos/tangb/raspiot/zipball/v0.0.18'},
{u'assets': [{u'browser_download_url': u'https://github.com/tangb/raspiot/releases/download/v0.0.13/cleep_0.0.13.sha256',
               u'content_type': u'application/octet-stream',
               u'created_at': u'2018-09-27T05:35:54Z',
               u'download_count': 0,
               u'id': 8863737,
               u'label': u'',
               u'name': u'cleep_0.0.13.sha256',
               u'node_id': u'MDEyOlJlbGVhc2VBc3NldDg4NjM3Mzc=',
               u'size': 83,
               u'state': u'uploaded',
               u'updated_at': u'2018-09-27T05:35:55Z',
               u'uploader': {u'avatar_url': u'https://avatars1.githubusercontent.com/u/2676511?v=4',
                             u'events_url': u'https://api.github.com/users/tangb/events{/privacy}',
                             u'followers_url': u'https://api.github.com/users/tangb/followers',
                             u'following_url': u'https://api.github.com/users/tangb/following{/other_user}',
                             u'gists_url': u'https://api.github.com/users/tangb/gists{/gist_id}',
                             u'gravatar_id': u'',
                             u'html_url': u'https://github.com/tangb',
                             u'id': 2676511,
                             u'login': u'tangb',
                             u'node_id': u'MDQ6VXNlcjI2NzY1MTE=',
                             u'organizations_url': u'https://api.github.com/users/tangb/orgs',
                             u'received_events_url': u'https://api.github.com/users/tangb/received_events',
                             u'repos_url': u'https://api.github.com/users/tangb/repos',
                             u'site_admin': False,
                             u'starred_url': u'https://api.github.com/users/tangb/starred{/owner}{/repo}',
                             u'subscriptions_url': u'https://api.github.com/users/tangb/subscriptions',
                             u'type': u'User',
                             u'url': u'https://api.github.com/users/tangb'},
               u'url': u'https://api.github.com/repos/tangb/raspiot/releases/assets/8863737'},
              {u'browser_download_url': u'https://github.com/tangb/raspiot/releases/download/v0.0.13/cleep_0.0.13.zip',
               u'content_type': u'application/octet-stream',
               u'created_at': u'2018-09-26T20:13:38Z',
               u'download_count': 0,
               u'id': 8856998,
               u'label': u'',
               u'name': u'cleep_0.0.13.zip',
               u'node_id': u'MDEyOlJlbGVhc2VBc3NldDg4NTY5OTg=',
               u'size': 732660023,
               u'state': u'uploaded',
               u'updated_at': u'2018-09-26T21:37:27Z',
               u'uploader': {u'avatar_url': u'https://avatars1.githubusercontent.com/u/2676511?v=4',
                             u'events_url': u'https://api.github.com/users/tangb/events{/privacy}',
                             u'followers_url': u'https://api.github.com/users/tangb/followers',
                             u'following_url': u'https://api.github.com/users/tangb/following{/other_user}',
                             u'gists_url': u'https://api.github.com/users/tangb/gists{/gist_id}',
                             u'gravatar_id': u'',
                             u'html_url': u'https://github.com/tangb',
                             u'id': 2676511,
                             u'login': u'tangb',
                             u'node_id': u'MDQ6VXNlcjI2NzY1MTE=',
                             u'organizations_url': u'https://api.github.com/users/tangb/orgs',
                             u'received_events_url': u'https://api.github.com/users/tangb/received_events',
                             u'repos_url': u'https://api.github.com/users/tangb/repos',
                             u'site_admin': False,
                             u'starred_url': u'https://api.github.com/users/tangb/starred{/owner}{/repo}',
                             u'subscriptions_url': u'https://api.github.com/users/tangb/subscriptions',
                             u'type': u'User',
                             u'url': u'https://api.github.com/users/tangb'},
               u'url': u'https://api.github.com/repos/tangb/raspiot/releases/assets/8856998'},
              {u'browser_download_url': u'https://github.com/tangb/raspiot/releases/download/v0.0.13/raspiot_0.0.13.sha256',
               u'content_type': u'application/octet-stream',
               u'created_at': u'2018-09-25T22:12:08Z',
               u'download_count': 1,
               u'id': 8841647,
               u'label': u'',
               u'name': u'raspiot_0.0.13.sha256',
               u'node_id': u'MDEyOlJlbGVhc2VBc3NldDg4NDE2NDc=',
               u'size': 85,
               u'state': u'uploaded',
               u'updated_at': u'2018-09-25T22:12:08Z',
               u'uploader': {u'avatar_url': u'https://avatars1.githubusercontent.com/u/2676511?v=4',
                             u'events_url': u'https://api.github.com/users/tangb/events{/privacy}',
                             u'followers_url': u'https://api.github.com/users/tangb/followers',
                             u'following_url': u'https://api.github.com/users/tangb/following{/other_user}',
                             u'gists_url': u'https://api.github.com/users/tangb/gists{/gist_id}',
                             u'gravatar_id': u'',
                             u'html_url': u'https://github.com/tangb',
                             u'id': 2676511,
                             u'login': u'tangb',
                             u'node_id': u'MDQ6VXNlcjI2NzY1MTE=',
                             u'organizations_url': u'https://api.github.com/users/tangb/orgs',
                             u'received_events_url': u'https://api.github.com/users/tangb/received_events',
                             u'repos_url': u'https://api.github.com/users/tangb/repos',
                             u'site_admin': False,
                             u'starred_url': u'https://api.github.com/users/tangb/starred{/owner}{/repo}',
                             u'subscriptions_url': u'https://api.github.com/users/tangb/subscriptions',
                             u'type': u'User',
                             u'url': u'https://api.github.com/users/tangb'},
               u'url': u'https://api.github.com/repos/tangb/raspiot/releases/assets/8841647'},
              {u'browser_download_url': u'https://github.com/tangb/raspiot/releases/download/v0.0.13/raspiot_0.0.13.zip',
               u'content_type': u'application/octet-stream',
               u'created_at': u'2018-09-25T22:11:37Z',
               u'download_count': 1,
               u'id': 8841630,
               u'label': u'',
               u'name': u'raspiot_0.0.13.zip',
               u'node_id': u'MDEyOlJlbGVhc2VBc3NldDg4NDE2MzA=',
               u'size': 3864670,
               u'state': u'uploaded',
               u'updated_at': u'2018-09-25T22:12:07Z',
               u'uploader': {u'avatar_url': u'https://avatars1.githubusercontent.com/u/2676511?v=4',
                             u'events_url': u'https://api.github.com/users/tangb/events{/privacy}',
                             u'followers_url': u'https://api.github.com/users/tangb/followers',
                             u'following_url': u'https://api.github.com/users/tangb/following{/other_user}',
                             u'gists_url': u'https://api.github.com/users/tangb/gists{/gist_id}',
                             u'gravatar_id': u'',
                             u'html_url': u'https://github.com/tangb',
                             u'id': 2676511,
                             u'login': u'tangb',
                             u'node_id': u'MDQ6VXNlcjI2NzY1MTE=',
                             u'organizations_url': u'https://api.github.com/users/tangb/orgs',
                             u'received_events_url': u'https://api.github.com/users/tangb/received_events',
                             u'repos_url': u'https://api.github.com/users/tangb/repos',
                             u'site_admin': False,
                             u'starred_url': u'https://api.github.com/users/tangb/starred{/owner}{/repo}',
                             u'subscriptions_url': u'https://api.github.com/users/tangb/subscriptions',
                             u'type': u'User',
                             u'url': u'https://api.github.com/users/tangb'},
               u'url': u'https://api.github.com/repos/tangb/raspiot/releases/assets/8841630'}],
  u'assets_url': u'https://api.github.com/repos/tangb/raspiot/releases/13092235/assets',
  u'author': {u'avatar_url': u'https://avatars1.githubusercontent.com/u/2676511?v=4',
              u'events_url': u'https://api.github.com/users/tangb/events{/privacy}',
              u'followers_url': u'https://api.github.com/users/tangb/followers',
              u'following_url': u'https://api.github.com/users/tangb/following{/other_user}',
              u'gists_url': u'https://api.github.com/users/tangb/gists{/gist_id}',
              u'gravatar_id': u'',
              u'html_url': u'https://github.com/tangb',
              u'id': 2676511,
              u'login': u'tangb',
              u'node_id': u'MDQ6VXNlcjI2NzY1MTE=',
              u'organizations_url': u'https://api.github.com/users/tangb/orgs',
              u'received_events_url': u'https://api.github.com/users/tangb/received_events',
              u'repos_url': u'https://api.github.com/users/tangb/repos',
              u'site_admin': False,
              u'starred_url': u'https://api.github.com/users/tangb/starred{/owner}{/repo}',
              u'subscriptions_url': u'https://api.github.com/users/tangb/subscriptions',
              u'type': u'User',
              u'url': u'https://api.github.com/users/tangb'},
  u'body': u'* Remove completely all modules. Now they are external parts even system modules\r\n* Remove all formatters and keep only profiles\r\n* Fix some bugs and improve cleepos\r\n* Modules are only loaded by inventory now\r\n',
  u'created_at': u'2018-08-06T17:20:27Z',
  u'draft': False,
  u'html_url': u'https://github.com/tangb/raspiot/releases/tag/v0.0.13',
  u'id': 13092235,
  u'name': u'0.0.13',
  u'node_id': u'MDc6UmVsZWFzZTEzMDkyMjM1',
  u'prerelease': True,
  u'published_at': u'2018-09-26T12:05:53Z',
  u'tag_name': u'v0.0.13',
  u'tarball_url': u'https://api.github.com/repos/tangb/raspiot/tarball/v0.0.13',
  u'target_commitish': u'master',
  u'upload_url': u'https://uploads.github.com/repos/tangb/raspiot/releases/13092235/assets{?name,label}',
  u'url': u'https://api.github.com/repos/tangb/raspiot/releases/13092235',
  u'zipball_url': u'https://api.github.com/repos/tangb/raspiot/zipball/v0.0.13'},
]


class MockedResponse():
    def __init__(self, data={}, status=200, headers={}):
        self.status = status
        self.data = data
        self.headers = headers

class CleepGithubTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.TRACE, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.owner = 'dummy'
        self.repo = 'dummy'

    def tearDown(self):
        pass

    def _init_context(self, resp_data={}, resp_status=200, resp_headers={}):
        self.g = CleepGithub()
        self.g.http.urlopen = Mock(return_value=MockedResponse(resp_data, resp_status, resp_headers))

    def test_auth_string(self):
        g = CleepGithub()
        self.assertFalse('Authorization' in g.http_headers)

        g = CleepGithub(auth_string='Bearer myjwt')
        self.assertTrue('Authorization' in g.http_headers)

    def test_get_releases(self):
        self._init_context(resp_data=json.dumps(GET_RELEASES))
        releases = self.g.get_releases(self.owner, self.repo, only_latest=True, only_released=False)
        self.assertTrue(isinstance(releases, list))
        self.assertEqual(1, len(releases))

    def test_get_all_releases(self):
        self._init_context(resp_data=json.dumps(GET_RELEASES))
        release = self.g.get_releases(self.owner, self.repo, only_latest=False, only_released=False)
        self.assertTrue(isinstance(release, list))
        self.assertNotEqual(0, len(release))

    def test_unknown_repo(self):
        self._init_context(resp_status=404)
        self.assertRaises(Exception, self.g.get_releases, 'tangb', 'test')

    def test_release_version(self):
        self._init_context(resp_data=json.dumps(GET_RELEASES))
        releases = self.g.get_releases(self.owner, self.repo, only_latest=True, only_released=False)
        self.assertEqual(1, len(releases))
        version = self.g.get_release_version(releases[0])
        self.assertNotEqual(0, len(version.strip()))

    def test_release_version_with_invalid_release(self):
        self._init_context(resp_data=json.dumps(GET_RELEASES))

        class Dummy():
            pass
        with self.assertRaises(Exception) as cm:
            self.g.get_release_version(Dummy())
        self.assertEqual(cm.exception.message, 'Invalid release format. Dict type awaited')

        with self.assertRaises(Exception) as cm:
            self.g.get_release_version({})
        self.assertEqual(cm.exception.message, 'Specified release has no version field')

    def test_release_version_raw_version(self):
        self._init_context(resp_data=json.dumps(GET_RELEASES))

        releases = deepcopy(GET_RELEASES)
        release = releases[0]
        release['tag_name'] = 'myversion'

        version = self.g.get_release_version(release)
        self.assertEqual(version, 'myversion')

    def test_release_changelog(self):
        self._init_context(resp_data=json.dumps(GET_RELEASES))
        releases = self.g.get_releases(self.owner, self.repo, only_latest=True, only_released=False)
        self.assertEqual(1, len(releases))
        changelog = self.g.get_release_changelog(releases[0])
        self.assertNotEqual(0, len(changelog.strip()))

    def test_release_changelog_with_invalid_release(self):
        self._init_context(resp_data=json.dumps(GET_RELEASES))

        class Dummy():
            pass
        with self.assertRaises(Exception) as cm:
            self.g.get_release_changelog(Dummy())
        self.assertEqual(cm.exception.message, 'Invalid release format. Dict type awaited')

    def test_release_changelog_with_empty_changelog(self):
        self._init_context(resp_data=json.dumps(GET_RELEASES))

        releases = deepcopy(GET_RELEASES)
        release = releases[0]
        del release['body']

        changelog = self.g.get_release_changelog(release)
        self.assertEqual(changelog, '')

    def test_get_release_assets_infos(self):
        self._init_context(resp_data=json.dumps(GET_RELEASES))
        releases = self.g.get_releases(self.owner, self.repo, only_latest=True, only_released=False)
        self.assertEqual(1, len(releases))
        infos = self.g.get_release_assets_infos(releases[0])
        logging.debug(infos)

    def test_get_release_assets_infos_with_invalid_release(self):
        self._init_context(resp_data=json.dumps(GET_RELEASES))

        class Dummy():
            pass
        with self.assertRaises(Exception) as cm:
            self.g.get_release_assets_infos(Dummy())
        self.assertEqual(cm.exception.message, 'Invalid release format. Dict type awaited')

        releases = deepcopy(GET_RELEASES)
        release = releases[0]
        del release['assets']
        with self.assertRaises(Exception) as cm:
            self.g.get_release_assets_infos(release)
        self.assertEqual(cm.exception.message, 'iInvalid release format')

    def test_is_release(self):
        self._init_context(resp_data=json.dumps(GET_RELEASES))
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
        self._init_context(resp_data=json.dumps(GET_RELEASES))

        class Dummy():
            pass
        with self.assertRaises(Exception) as cm:
            self.g.is_released(Dummy())
        self.assertEqual(cm.exception.message, 'Invalid release format. Dict type awaited')

    def test_api_rate(self):
        self._init_context(resp_data=json.dumps(GET_API_RATE))
        rate = self.g.get_api_rate()
        logging.debug(rate)
        self.assertTrue(u'limit' in rate)
        self.assertTrue(u'remaining' in rate)
        self.assertTrue(u'reset' in rate)

    def test_api_rate_invalid_data_received(self):
        GET_API_RATE_ = deepcopy(GET_API_RATE)
        del GET_API_RATE_['rate']

        self._init_context(resp_data=json.dumps(GET_API_RATE_))
        with self.assertRaises(Exception) as cm:
            self.g.get_api_rate()
        self.assertEqual(cm.exception.message, 'Unable to get api rate: Invalid data from github rate_limit request')

    def test_api_rate_invalid_response_status(self):
        self._init_context(resp_status=500)
        with self.assertRaises(Exception) as cm:
            self.g.get_api_rate()
        self.assertEqual(cm.exception.message, 'Unable to get api rate: Invalid response (status=500)')


if __name__ == '__main__':
     #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_cleepgithub.py; coverage report -m
     unittest.main()

