#!/usr/bin/env python
# -*- coding: utf-8 -*

import logging
import time
import urllib3
import json

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

    def __clean_releases(self, assets):
        """
        Clean releases removing useless fields

        Args:
            assets (list): list of assets to clean
        """
        out = []
        for asset in assets:
            del asset[u'uploader']
            out.append(asset)

        return out

    def get_releases(self, owner, repository, all_releases=False):
        """
        Get releases of specify project repository

        Args:
            owner (string): name of owner
            repository (string): name of repository
            all (bool): return all releases instead of latest one

        Return:
            dict: releases as returned in assets by github api (https://developer.github.com/v3/repos/releases/)
        """
        try:
            url = self.GITHUB_URL % (owner, repository)
            resp = self.http.urlopen('GET', url, headers=self.http_headers)

            if resp.status==200:
                #response successful, parse data to get current latest version
                data = json.loads(resp.data.decode('utf-8'))
                self.logger.debug('Data: %s' % data)
                if isinstance(data, list) and len(data)>0:
                    data = data[0]
                if u'assets' not in data.keys():
                    self.logger.error(u'It seems github api format for repos has changed')
                    return {}
                elif all_releases:
                    return self.__clean_releases(data[u'assets'])
                elif len(data[u'assets'])>0:
                    assets = []
                    assets.append(data[u'assets'][0])
                    return self.__clean_releases(assets)
                else:
                    return {}

            else:
                self.logger.error('Unable to fetch releases (status=%d)' % resp.status)
                self.logger.error('Etcher request data: %s' % resp.data)
                return {}

        except:
            self.logger.exception('Unable to get releases:')

