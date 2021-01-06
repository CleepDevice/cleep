#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import json
import time
from cleep.libs.internals.download import Download

class ModulesJson():
    """
    Helper class to update and read values from /etc/cleep/modules.json file
    """

    CONF = u'/etc/cleep/modules.json'
    # REMOTE_URL =  'https://raw.githubusercontent.com/tangb/cleep-apps/main/modules.json'
    REMOTE_URL = 'http://tanguy.duckdns.org/modules.json'

    def __init__(self, cleep_filesystem):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
        """
        #members
        self.cleep_filesystem = cleep_filesystem
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)

        #use local REMOTE_CONF if provided
        #if u'CLEEPOS_REMOTE_CONF' in os.environ:
        #    REMOTE_CONF = os.environ[u'CLEEPOS_REMOTE_CONF']

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
            u'update': int(time.time()),
            u'list': {}
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
        #check
        if not os.path.exists(self.CONF):
            raise Exception(u'File "modules.json" doesn\'t exist. Please update it first.')
            
        #read content
        modules_json = self.cleep_filesystem.read_json(self.CONF)

        #check content
        if modules_json is None or u'list' not in modules_json or u'update' not in modules_json:
            self.logger.error(u'Invalid "modules.json" file content')
            raise Exception(u'Invalid "modules.json" file content')

        return modules_json

    def update(self):
        """
        Update modules.json file downloading fresh version from cleepos website

        Returns:
            bool: True if modules.json is different from local one, False if file is identical

        Raises:
            Exception if error occured
        """
        self.logger.debug('Updating "modules.json" file...')
        #download file (blocking because file is small)
        download = Download(self.cleep_filesystem)
        download_status, raw = download.download_content(self.REMOTE_URL)
        if raw is None:
            raise Exception('Download of modules.json failed (download status %s)' % download_status)
        remote_modules_json = json.loads(raw)
        self.logger.trace(u'Downloaded modules.json: %s' % remote_modules_json)

        #check remote content
        if u'list' not in remote_modules_json or u'update' not in remote_modules_json:
            self.logger.error(u'Remote "modules.json" file has invalid format')
            raise Exception(u'Remote "modules.json" file has invalid format')
        
        #get local
        local_modules_json = None
        if os.path.exists(self.CONF):
            local_modules_json = self.get_json()

        #compare update field
        self.logger.debug(u'Compare update timestamp: %s>%s' % (remote_modules_json[u'update'], local_modules_json[u'update'] if local_modules_json else None))
        if local_modules_json is None or remote_modules_json[u'update']>local_modules_json[u'update']:
            #modules.json updated, save new file
            fd = self.cleep_filesystem.open(self.CONF, u'w')
            fd.write(raw)
            self.cleep_filesystem.close(fd)
            self.logger.info(u'File "modules.json" updated successfully')
        
            #make sure file is written
            time.sleep(0.25)

            return True

        else:
            #no update from remote modules.json file
            self.logger.info(u'No difference between local and remote modules.json. File not updated.')

        #no new content
        return False

