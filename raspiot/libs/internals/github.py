#!/usr/bin/env python
# -*- coding: utf-8 -*

import logging
import time
import urllib3
urllib3.disable_warnings()
import json
import re

class Github():
    """
    Github release helper
    This class get releases from specified project and return content as dict
    """

    GITHUB_URL = u'https://api.github.com/repos/%s/%s/releases'
    GITHUB_RATE = u'https://api.github.com/rate_limit'

    def __init__(self):
        """
        Constructor
        """
        #logger
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)

        #members
        self.http_headers =  {'user-agent':'Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0'}
        self.http = urllib3.PoolManager(num_pools=1)
        self.version_pattern = r'\d+\.\d+\.\d+'

    def get_api_rate(self):
        """
        Get current api rate
        Api requests are limited on free usage of github. This method returns current rate

        Returns:
            dict: general rate values::
                {
                    limit (int): limit of requests
                    remaining (int): number of requests processed
                    reset (int): timestamp when rate is resetted to limit
                }
        """
        resp = self.http.urlopen('GET', self.GITHUB_RATE, headers=self.http_headers)

        if resp.status==200:
            #response successful, parse data to get current latest version
            data = json.loads(resp.data.decode('utf-8'))
            self.logger.debug('Data: %s' % data)

            if u'rate' in data:
                return data[u'rate']
            else:
                raise Exception(u'Invalid data from github rate_limit request')
        else:
            raise Exception(u'Invalid response (status=%d): %s' % (resp.status, resp.data))

    def get_release_version(self, release):
        """
        Return version of specified release

        Args:
            release (dict): release data as returned by get_releases function

        Returns:
            string: version of release
        """
        if not isinstance(release, dict):
            raise Exception('Invalid release format. Dict type awaited')

        if u'tag_name' in release.keys():
            version = re.search(self.version_pattern, release[u'tag_name'])
            if version:
                return version.group()
            return release[u'tag_name']

        else:
            raise Exception('Specified release has no version field')

    def get_release_changelog(self, release):
        """
        Return changelog of specified release

        Args:
            release (dict): release data as returned by get_releases function

        Returns:
            string: changelog of release. Can be empty string if no changelog specified.
        """
        if not isinstance(release, dict):
            raise Exception('Invalid release format. Dict type awaited')

        if u'body' in release.keys():
            return release[u'body']
        else:
            #no body tag found, return empty string
            return u''

    def is_released(self, release):
        """
        Return True if release is released (it means not prerelease or draft)

        Args:
            release (dict): release data as returned by get_releases function

        Returns:
            bool: True if release is released
        """
        if not isinstance(release, dict):
            raise Exception('Invalid release format. Dict type awaited')

        prerelease = True
        if u'prerelease' in release.keys():
            prerelease = release[u'prerelease']
        draft = True
        if u'draft' in release.keys():
            draft = release[u'draft']

        return not prerelease and not draft

    def get_release_assets_infos(self, release):
        """
        Return simplified structure of all release assets

        Args:
            release (dict): release data as returned by get_releases function

        Returns:
            list of dict: list of assets infos (name, url, size)::
                [
                    {name (string), url (string), size (int)},
                    {name (string), url (string), size (int)},
                    ...
                ]
        """
        if not isinstance(release, dict):
            raise Exception(u'Invalid release format. Dict type awaited')
        if u'assets' not in release.keys():
            raise Exception(u'Invalid release format.')

        out = []
        for asset in release[u'assets']:
            if u'browser_download_url' and u'size' and u'name' in asset.keys():
                out.append({
                    u'name': asset[u'name'],
                    u'url': asset[u'browser_download_url'],
                    u'size': asset[u'size']
                })

        return out

    def __get_all_releases(self, owner, repository):
        """
        Get releases of specify project repository

        Args:
            owner (string): name of owner
            repository (string): name of repository

        Returns:
            list: list of releases. Format can be found here https://developer.github.com/v3/repos/releases/
        """
        try:
            url = self.GITHUB_URL % (owner, repository)
            resp = self.http.urlopen('GET', url, headers=self.http_headers)

            if resp.status==200:
                #response successful, parse data to get current latest version
                data = json.loads(resp.data.decode('utf-8'))
                self.logger.debug('Data: %s' % data)

                #return all releases
                return data

            else:
                raise Exception('Invalid response (status=%d): %s' % (resp.status, resp.data))

        except Exception as e:
            self.logger.exception('Unable to get releases:')
            raise Exception('Unable to get releases: %s' % str(e))

    def __get_released_releases(self, owner, repository):
        """
        Get released releases

        Args:
            owner (string): name of owner
            repository (string): name of repository
        """
        return [release for release in self.__get_all_releases(owner, repository) if self.is_released(release)]

    def get_releases(self, owner, repository, only_latest=False, only_released=True):
        """
        Get releases of specify project repository

        Args:
            owner (string): name of owner
            repository (string): name of repository
            only_latest (bool): if True returns only latest release
            only_released (bool): if True returns only released releases

        Returns:
            list: list of releases. Format can be found here https://developer.github.com/v3/repos/releases/
        """
        #get all releases
        if only_released:
            releases = self.__get_released_releases(owner, repository)
        else:
            releases = self.__get_all_releases(owner, repository)

        if only_latest:
            #return only latest release
            return releases[0:1]

        return releases

