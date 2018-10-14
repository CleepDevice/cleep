#!/usr/bin/env python
# -*- coding: utf-8 -*

import logging
from zipfile import ZipFile, ZIP_DEFLATED

class RaspiotBackup:
    """
    RaspiotBackup allows you:
     - to backup raspiot configuration files on filesystem (in /etc/raspiot.bak directory)
     - to generate backup archive of configuration files

    It uses rsync to backup files locally
    """
    RASPIOT_PATH = u'/etc/raspiot/'
    BACKUP_PATH = u'/etc/raspiot.bak/'

    def __init__(self, cleep_filesystem, crash_report):
        """
        Constructor
        """
        #member
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)
        self.crash_report = crash_report
        self.cleep_filesystem = cleep_filesystem

    def backup(self):
        """
        Backup configuration files on filesystem

        Returns:
            bool: True if backup completed sucessfully
        """
        return self.cleep_filesystem.rsync(self.RASPIOT_PATH, self.BACKUP_PATH)

    def generate_archive(self):
        """
        Generate backup archive (tar.gz format)

        Returns:
            string: generated archive fullpath
        """
        fd = NamedTemporaryFile(delete=False)
        archive_name = fd.name
        archive = ZipFile(fd, u'w', ZIP_DEFLATED)
        for f in os.listdir(self.RASPIOT_PATH):
            #build path
            fullpath = os.path.join(self.RASPIOT_PATH, f)
            #archive.write()
        archive.close()

        return archive_name
        
