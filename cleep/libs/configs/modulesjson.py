#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import json
import time
import requests
from cleep import __version__ as CLEEP_VERSION
from cleep.libs.internals.download import Download

class ModulesJson():
    """
    Helper class to update and read values from /etc/cleep/modules.json file
    """

    CONF = '/etc/cleep/modules.json'
    REMOTE_URL_VERSION = 'https://raw.githubusercontent.com/tangb/cleep-apps/v%(version)s/modules.json'
    REMOTE_URL_LATEST =  'https://raw.githubusercontent.com/tangb/cleep-apps/main/modules.json'

    def __init__(self, cleep_filesystem):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
        """
        # members
        self.cleep_filesystem = cleep_filesystem
        self.logger = logging.getLogger(self.__class__.__name__)

        # use local REMOTE_CONF if provided
        # if 'CLEEPOS_REMOTE_CONF' in os.environ:
        #     REMOTE_CONF = os.environ['CLEEPOS_REMOTE_CONF']

    def exists(self):
        """
        Return True if modules.json exists locally
    
        Returns:
            bool: True if modules.json exists
        """
        return os.path.exists(self.CONF)

    def get_empty(self):
        """
        Return empty version of modules.json
        Used to have something to parse file in case of error

        Returns:
            dict: default (and empty) modules.json content
        """
        return {
            'update': int(time.time()),
            'list': {}
        }

    def get_json(self):
        """
        Get modules.json file content

        Returns:
            dict: None if file doesn't exist (please use exists function) or modules.json content as dict::

                {
                    update (int): last update timestamp
                    list (dict): dict of available modules
                }
    
        Raises:
            Exception if modules.json does not exist or is invalid

        """
        # check
        if not os.path.exists(self.CONF):
            raise Exception('File "modules.json" doesn\'t exist. Please update it first.')
            
        # read content
        modules_json = self.cleep_filesystem.read_json(self.CONF)

        # check content
        if modules_json is None or 'list' not in modules_json or 'update' not in modules_json:
            self.logger.error('Invalid "modules.json" file content')
            raise Exception('Invalid "modules.json" file content')

        return modules_json

    def __get_remote_url(self):
        """
        Get remote url choosing between latest of versionned one according to availability

        Returns:
            string: remote url
        """
        # check versionned first. If available it means current installed Cleep version is not the latest
        # and should be upgraded. Returned modules verions will be fixed forever for this version.
        try:
            url = self.REMOTE_URL_VERSION % {'version': CLEEP_VERSION}
            resp = requests.get(url)
            if resp.status_code == 200:
                return url
        except:
            # do not fail
            pass

        return self.REMOTE_URL_LATEST

    def update(self):
        """
        Update modules.json file downloading fresh version from cleepos website

        Returns:
            bool: True if modules.json is different from local one, False if file is identical

        Raises:
            Exception if error occured
        """
        self.logger.debug('Updating "modules.json" file...')

        # download file (blocking because file is small)
        download = Download(self.cleep_filesystem)
        download_status, raw = download.download_content(self.__get_remote_url())
        if raw is None:
            raise Exception('Download of modules.json failed (download status %s)' % download_status)
        remote_modules_json = json.loads(raw)
        self.logger.trace('Downloaded modules.json: %s' % remote_modules_json)

        # check remote content
        if 'list' not in remote_modules_json or 'update' not in remote_modules_json:
            self.logger.error('Remote "modules.json" file has invalid format')
            raise Exception('Remote "modules.json" file has invalid format')
        
        # get local
        local_modules_json = None
        if os.path.exists(self.CONF):
            local_modules_json = self.get_json()

        # compare update field
        self.logger.debug('Compare update timestamp: %s>%s' % (remote_modules_json['update'], local_modules_json['update'] if local_modules_json else None))
        if local_modules_json is None or remote_modules_json['update']>local_modules_json['update']:
            # modules.json updated, save new file
            fd = self.cleep_filesystem.open(self.CONF, 'w')
            fd.write(raw)
            self.cleep_filesystem.close(fd)
            self.logger.info('File "modules.json" updated successfully')
        
            # make sure file is written
            time.sleep(0.25)

            return True

        # no update from remote modules.json file
        self.logger.info('No difference between local and remote modules.json. File not updated.')
        return False

