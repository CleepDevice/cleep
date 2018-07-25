#!/usr/bin/env python
# -*- coding: utf-8 -*

import logging
import time
import urllib3
import json
import re

class Github():
    """
    Github release helper
    This class get releases from specified project and return content as dict
    """

    GITHUB_URL = u'https://api.github.com/repos/%s/%s/releases'

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

    def get_release_version(self, release):
        """
        Return version of specified release

        Args:
            release (dict): release data as returned by get_releases function

        Return:
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

    def get_release_assets_infos(self, release):
        """
        Return simplified structure of all release assets

        Args:
            release (dict): release data as returned by get_releases function

        Return:
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

    def get_releases(self, owner, repository, only_latest=False):
        """
        Get releases of specify project repository

        Args:
            owner (string): name of owner
            repository (string): name of repository
            only_latest (bool): if True returns only latest release

        Return:
            list: list of releases. Format can be found here https://developer.github.com/v3/repos/releases/
        """
        try:
            url = self.GITHUB_URL % (owner, repository)
            resp = self.http.urlopen('GET', url, headers=self.http_headers)

            if resp.status==200:
                #response successful, parse data to get current latest version
                data = json.loads(resp.data.decode('utf-8'))
                self.logger.debug('Data: %s' % data)

                if not only_latest:
                    #return all releases
                    return data

                elif len(data)>0:
                    #return latest release
                    return data[0:1]

                else:
                    #it seems there is no release yet
                    return []

            else:
                raise Exception('Invalid response (status=%d): %s' % (resp.status, resp.data))

        except Exception as e:
            self.logger.exception('Unable to get releases:')
            raise Exception('Unable to get releases: %s' % str(e))
    

