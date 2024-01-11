#!/usr/bin/env python
# -*- coding: utf-8 -*

import logging
import os
from zipfile import ZipFile, ZIP_DEFLATED
from tempfile import NamedTemporaryFile

class CleepBackup:
    """
    CleepBackup allows you:
     - to backup cleep configuration files on filesystem (in /etc/cleep.bak directory)
     - to generate backup archive of configuration files

    It uses rsync to backup files locally
    """
    CLEEP_PATH = '/etc/cleep/'
    BACKUP_PATH = '/etc/cleep.bak/'

    def __init__(self, cleep_filesystem, crash_report):
        """
        Constructor
        """
        # member
        self.logger = logging.getLogger(self.__class__.__name__)
        # self.logger.setLevel(logging.DEBUG)
        self.crash_report = crash_report
        self.cleep_filesystem = cleep_filesystem

        # make sure path exists
        if not os.path.exists(self.CLEEP_PATH):
            self.cleep_filesystem.mkdirs(self.CLEEP_PATH)
        if not os.path.exists(self.BACKUP_PATH):
            self.cleep_filesystem.mkdirs(self.BACKUP_PATH)

    def backup(self): # pragma: no cover
        """
        Backup configuration files on filesystem

        Returns:
            bool: True if backup completed sucessfully
        """
        return self.cleep_filesystem.rsync(self.CLEEP_PATH, self.BACKUP_PATH)

    def generate_archive(self):
        """
        Generate backup archive (zip format)

        Warning:
            Caller is in charge of file deletion !

        Returns:
            string: generated archive fullpath
        """
        fd = NamedTemporaryFile(delete=False)
        archive_name = fd.name
        archive = ZipFile(fd, 'w', ZIP_DEFLATED)
        for f in os.listdir(self.CLEEP_PATH):
            # build path
            fullpath = os.path.join(self.CLEEP_PATH, f)
            archive.write(fullpath)
        archive.close()

        return archive_name
        
