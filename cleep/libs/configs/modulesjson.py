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
    """

    DEFAULT_MODULES_JSON = {
        "filepath": "/etc/cleep/modules.json",
        "remote_url_version": "https://raw.githubusercontent.com/tangb/cleep-apps/v%(version)s/modules.json",
        "remote_url_latest": "https://raw.githubusercontent.com/tangb/cleep-apps/main/modules.json",
    }

    def __init__(self, cleep_filesystem, custom_file=None):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
            custom_file (dict): info for custom modules.json file::

                {
                    filepath (str): place to store custom file,
                    remote_url_version (str): url to find custom file for specific version. String must contains %(version) to replace it with current Cleep version,
                    remote_url_latest (str): url to find latest custom file,
                }

        """
        # members
        self.cleep_filesystem = cleep_filesystem
        self.logger = logging.getLogger(self.__class__.__name__)
        self.modulesjson = self.__build_modules_json(custom_file)

        # use local REMOTE_CONF if provided
        # if 'CLEEPOS_REMOTE_CONF' in os.environ:
        #     REMOTE_CONF = os.environ['CLEEPOS_REMOTE_CONF']

    def __build_modules_json(self, custom_file):
        """
        Build valid modulesjson object

        Args:
            custom_file (dict): info for custom modules.json file (see constructor)

        Returns:
            dict: modulesjson content in the same format as custom_file (see constructor)
        """
        filepath = None
        remote_url_version = None
        remote_url_latest = None
        try:
            filepath = custom_file and custom_file.get("filepath") or None
            remote_url_version = custom_file and custom_file.get("remote_url_version") or None
            remote_url_latest = custom_file and custom_file.get("remote_url_latest") or None
        except:
            # invalid format
            pass

        if any(v is None for v in [filepath, remote_url_version, remote_url_latest]):
            return self.DEFAULT_MODULES_JSON

        return {
            "filepath": filepath,
            "remote_url_version": remote_url_version,
            "remote_url_latest": remote_url_latest,
        }

    
    def exists(self):
        """
        Return True if modules.json exists locally

        Returns:
            bool: True if modules.json exists
        """
        return os.path.exists(self.modulesjson["filepath"])

    def get_empty(self):
        """
        Return empty version of modules.json
        Used to have something to parse file in case of error

        Returns:
            dict: default (and empty) modules.json content
        """
        return {"update": int(time.time()), "list": {}}

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
        if not os.path.exists(self.modulesjson["filepath"]):
            raise Exception(
                'File "%s" doesn\'t exist. Please update it first.'
                % self.modulesjson["filepath"]
            )

        # read content
        modules_json = self.cleep_filesystem.read_json(self.modulesjson["filepath"])

        # check content
        if (
            modules_json is None
            or "list" not in modules_json
            or "update" not in modules_json
        ):
            self.logger.error('Invalid "%s" file content', self.modulesjson["filepath"])
            raise Exception('Invalid "%s" file content' % self.modulesjson["filepath"])

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
            url = self.modulesjson["remote_url_version"] % {"version": CLEEP_VERSION}
            resp = requests.get(url)
            if resp.status_code == 200:
                return url
        except:
            # do not fail
            pass

        return self.modulesjson["remote_url_latest"]

    def update(self):
        """
        Update modules.json file downloading fresh version from remote url

        Returns:
            bool: True if modules.json is different from local one, False if file is identical

        Raises:
            Exception if error occured
        """
        self.logger.debug('Updating "%s" file...', self.modulesjson["filepath"])

        # download file (blocking because file is small)
        download = Download(self.cleep_filesystem)
        download_status, raw = download.download_content(self.__get_remote_url())
        if raw is None:
            raise Exception(
                'Download of "%s" failed (download status %s)'
                % (self.modulesjson["filepath"], download_status)
            )
        remote_modules_json = json.loads(raw)
        self.logger.trace(
            'Downloaded "%s": %s' % (self.modulesjson["filepath"], remote_modules_json)
        )

        # check remote content
        if "list" not in remote_modules_json or "update" not in remote_modules_json:
            self.logger.error(
                'Remote "%s" file has invalid format', self.modulesjson["filepath"]
            )
            raise Exception(
                f"Remote \"{self.modulesjson['filepath']}\" file has invalid format"
            )

        # get local
        local_modules_json = None
        if os.path.exists(self.modulesjson["filepath"]):
            local_modules_json = self.get_json()

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
            fd = self.cleep_filesystem.open(self.modulesjson["filepath"], "w")
            fd.write(raw)
            self.cleep_filesystem.close(fd)
            self.logger.info(
                'File "%s" updated successfully', self.modulesjson["filepath"]
            )

            # make sure file is written
            time.sleep(0.25)

            return True

        # no update from remote modules.json file
        self.logger.info(
            "No difference between local and remote {self.modulesjson['filepath']}. File not updated."
        )
        return False
