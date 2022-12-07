#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import json
import time
import requests
from cleep import __version__ as CLEEP_VERSION
from cleep.libs.internals.download import Download


class ModulesJson:
    """
    Helper class to update and read values from modules.json file

    Provided content must be in json and has format::

        {
            update (int): last update timestamp (ms)
            list (dict): list of applications
        }

    """

    def __init__(self, cleep_filesystem, source):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
            source (dict): source content::

                {
                    filepath (string): source filepath
                    remote_url_version (string): source remote url with custom version
                    remote_url_latest (string): source remote url for latest version
                }

        """
        # members
        self.cleep_filesystem = cleep_filesystem
        self.logger = logging.getLogger(self.__class__.__name__)
        self.source = source

    def __is_valid(self):
        """
        Assert error if source property is invalid

        Raises:
            Exception if source format is invalid
        """
        if not isinstance(self.source, dict):
            return False

        keys = ["filepath", "remote_url_version", "remote_url_latest"]
        if not all([key in self.source for key in keys]):
            return False

        if self.source["remote_url_version"].find("%(version)s") == -1:
            return False

        return True

    def get_source_filepath(self):
        """
        Return source file path

        Returns:
            string: source filepath
        """
        return self.source["filepath"]

    def exists(self):
        """
        Return True if source file exists locally

        Returns:
            bool: True if modules.json exists
        """
        return os.path.exists(self.source["filepath"])

    def get_empty(self):
        """
        Return empty version of modules.json
        Used to have something to parse file in case of error

        Returns:
            dict: default (and empty) modules.json content
        """
        return {"update": int(time.time()), "list": {}}

    def get_content(self):
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
        if not os.path.exists(self.source["filepath"]):
            raise Exception(
                'File "%s" doesn\'t exist. Please update it first.'
                % self.source["filepath"]
            )

        # read content
        modules_json = self.cleep_filesystem.read_json(self.source["filepath"], "utf8")

        # check content
        if (
            modules_json is None
            or "list" not in modules_json
            or "update" not in modules_json
        ):
            self.logger.error('Invalid "%s" file content', self.source["filepath"])
            raise Exception('Invalid "%s" file content' % self.source["filepath"])

        return modules_json

    def __get_remote_url(self):
        """
        Get remote url choosing between latest of versionned one according to availability

        Returns:
            string: remote url
        """
        # check versionned first. If available it means current installed Cleep version is not the latest
        # and should be upgraded. Returned apps versions will be fixed forever for this version.
        try:
            url = self.source["remote_url_version"] % {"version": CLEEP_VERSION}
            resp = requests.get(url)
            if resp.status_code == 200:
                return url
        except:
            # do not fail
            pass

        return self.source["remote_url_latest"]

    def update(self):
        """
        Update apps file downloading fresh version from remote url

        Returns:
            bool: True if apps are different from local ones, False if file is identical

        Raises:
            Exception if error occured
        """
        if not self.__is_valid():
            raise Exception(f"Source is invalid: {self.source}")
        self.logger.debug('Updating "%s" file...', self.source["filepath"])

        # download file (blocking because file is small)
        download = Download(self.cleep_filesystem)
        download_status, raw = download.download_content(self.__get_remote_url())
        if raw is None:
            raise Exception(
                'Download of "%s" failed (download status %s)'
                % (self.source["filepath"], download_status)
            )
        remote_modules_json = json.loads(raw)
        self.logger.trace(
            'Downloaded "%s": %s' % (self.source["filepath"], remote_modules_json)
        )

        # check remote content
        if "list" not in remote_modules_json or "update" not in remote_modules_json:
            self.logger.error(
                'Remote "%s" file has invalid format', self.source["filepath"]
            )
            raise Exception(
                f"Remote \"{self.source['filepath']}\" file has invalid format"
            )

        # get local
        local_modules_json = None
        if os.path.exists(self.source["filepath"]):
            local_modules_json = self.get_content()

        # compare update field
        self.logger.debug(
            "Compare update timestamp: %s>%s"
            % (
                remote_modules_json["update"],
                local_modules_json["update"] if local_modules_json else None,
            )
        )
        if (
            local_modules_json is None
            or remote_modules_json["update"] > local_modules_json["update"]
        ):
            # modules.json updated, save new file
            fd = self.cleep_filesystem.open(self.source["filepath"], "w")
            fd.write(raw)
            self.cleep_filesystem.close(fd)
            self.logger.info(
                'File "%s" updated successfully', self.source["filepath"]
            )

            # make sure file is written
            time.sleep(0.25)

            return True

        # no update from remote modules.json file
        self.logger.info(
            "No difference between local and remote {self.source['filepath']}. File not updated."
        )
        return False
