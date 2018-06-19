#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import json
import time
from raspiot.libs.internals.download import Download

class ModulesJson():
    """
    Helper class to update and read values from /etc/raspiot/raspiot.conf file
    """

    CONF = u'/etc/raspiot/modules.json'
    REMOTE_CONF = u'https://raw.githubusercontent.com/tangb/raspiot/master/modules.json'

    def __init__(self, cleep_filesystem):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
        """
        #members
        self.cleep_filesystem = cleep_filesystem
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)

    def exists(self):
        """
        Return True if modules.json exists locally
    
        Return:
            bool: True if modules.json exists
        """
        return os.path.exists(self.CONF)

    def get_json(self):
        """
        Get modules.json file content

        Return:
            dict: None if file doesn't exist (please use exists function) or modules.json content as dict::
                {
                    update (int): last update timestamp
                    list (dict): dict of available modules
                }
        """
        #read content
        modules_json = self.cleep_filesystem.read_json(self.CONF)

        #check content
        if modules_json is None:
            return None
        if u'list' not in modules_json or u'update' not in modules_json:
            self.logger.fatal(u'Invalid modules.json file')
            raise Exception('Invalid modules.json')

        return modules_json

    def update(self):
        """
        Update modules.json file downloading fresh version from raspiot website

        Return:
            bool: True if remove modules.json is different from local one
        """
        #download file (blocking because file is small)
        download = Download(self.cleep_filesystem)
        raw = download.download_file(self.REMOTE_CONF)
        remote_modules_json = json.loads(raw)

        #check remote content
        if u'list' not in remote_modules_json or u'update' not in remote_modules_json:
            self.logger.warning(u'Remote modules.json file has unknown format')
            return False
        
        #get local
        local_modules_json = self.get_json()

        #compare update field
        if local_modules_json is None or remote_modules_json[u'update']>local_modules_json['update']:
            #modules.json updated, save new file
            fd = self.cleep_filesystem.open(self.CONF, u'w')
            fd.write(raw)
            self.cleep_filesystem.close(fd)
        
            #make sure file is written
            time.sleep(0.5)

            return True

        else:
            #no update from remote modules.json file
            self.logger.info(u'No difference between local and remote modules.json. File not updated.')

        #no new content
        return False
