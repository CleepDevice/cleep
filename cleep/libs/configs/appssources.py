#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
from copy import deepcopy
from cleep.libs.configs.modulesjson import ModulesJson
from cleep.exception import InvalidParameter, MissingParameter


class AppsSources:
    """
    Helper class to read and write apps.sources file
    It also reads all modules.json files and return aggregated content
    """

    CLEEP_APPS_FREE = {
        "filename": "cleep-free-apps.json",
        "remote_url_version": "https://raw.githubusercontent.com/tangb/cleep-apps/v%(version)s/modules.json",
        "remote_url_latest": "https://raw.githubusercontent.com/tangb/cleep-apps/main/modules.json",
    }
    CLEEP_APPS_NON_FREE = {
        "filename": "cleep-non-free-apps.json",
        "remote_url_version": "https://raw.githubusercontent.com/tangb/cleep-apps-nonfree/v%(version)s/modules.json",
        "remote_url_latest": "https://raw.githubusercontent.com/tangb/cleep-apps-nonfree/main/modules.json",
    }

    APPS_SOURCES_PATH = "/etc/cleep/apps.sources"
    SOURCES_PATH = "/etc/cleep/sources"
    MANDATORY_KEYS = ["filename", "remote_url_version", "remote_url_latest"]

    def __init__(self, cleep_filesystem):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
        """
        # members
        self.cleep_filesystem = cleep_filesystem
        self.logger = logging.getLogger(self.__class__.__name__)
        self.apps = {"update": 0, "list": {}}
        self.last_update = 0
        self.sources = []

        self.__refresh_sources()

    def __refresh_sources(self):
        """
        Refresh sources checking apps.sources file content and setting sources member
        """
        if not os.path.exists(self.SOURCES_PATH):
            self.cleep_filesystem.mkdirs(self.SOURCES_PATH)

        self.__check_apps_sources()
        self.__update_sources()

    def __check_apps_sources(self):
        """
        Check apps sources file (existence and content)
        Create default file if error occured
        """
        if not os.path.exists(self.APPS_SOURCES_PATH):
            if not self.__create_default_file():
                return

        try:
            data = self.cleep_filesystem.read_json(self.APPS_SOURCES_PATH, "utf8")
            if not isinstance(data, dict) or not data.get("sources"):
                raise Exception("Invalid apps.sources content")
            for source in data["sources"]:
                keys = [key in self.MANDATORY_KEYS for key in source.keys()]
                if not all(keys):
                    raise Exception(f"Invalid app source content {source}")

        except Exception:
            self.logger.warning(
                'Invalid "apps.sources" content, generate default content'
            )
            self.__create_default_file()

    def __create_default_file(self):
        """
        Create default app.sources with Cleep sources inside

        Returns:
            bool: True if default file created successfully, False otherwise
        """
        self.logger.debug('Create default "apps.sources" file')
        try:
            sources = []
            sources.append(self.CLEEP_APPS_FREE)
            sources.append(self.CLEEP_APPS_NON_FREE)
            data = {
                "sources": sources,
            }

            res = self.cleep_filesystem.write_json(self.APPS_SOURCES_PATH, data, "utf8")
            if not res:
                raise Exception('Error writing "apps.sources" file content')

            return True

        except Exception:
            self.logger.exception("Unable to create default apps.sources file")
            return False

    def __update_sources(self):
        """
        Update sources from app.sources file
        """
        try:
            data = self.cleep_filesystem.read_json(self.APPS_SOURCES_PATH, "utf8")
            self.sources = data["sources"]
        except Exception:
            self.logger.exception(
                'Error reading "apps.sources" content. No apps sources loaded'
            )

    def get_sources(self):
        """
        Return all sources

        Returns:
            list: list of sources::

            [
                {
                    filename (str): source filename
                    remote_url_version (str): url for specific version
                    remote_url_latest (str): url for latest version
                },
                ...
            ]

        """
        return deepcopy(self.sources)

    def add_source(self, source):
        """
        Add source

        Args:
            source (dict): source::

                {
                    filename (string): filename to store source to
                    remote_url_version (string): versionned remote url to get list of apps. Must contains
                                                 "%(version)s" to be able to replace with specific version
                    remote_url_latest (string): non versionned remote url to get list of apps. Use to get latest apps list
                }

        """
        if not source or not isinstance(source, dict):
            raise MissingParameter('Parameter "source" is missing')
        keys = [key in self.MANDATORY_KEYS for key in source.keys()]
        if not all(keys):
            raise InvalidParameter('Parameter "source" is invalid')
        if source["remote_url_version"].find("%(version)s") == -1:
            raise InvalidParameter(
                'Parameter "source" field "remote_url_version" is invalid'
            )

        self.logger.debug('Add source %s', source)
        data = self.cleep_filesystem.read_json(self.APPS_SOURCES_PATH, "utf8")
        data["sources"].append(source)

        if not self.cleep_filesystem.write_json(self.APPS_SOURCES_PATH, data, "utf8"):
            self.logger.error("Error saving new source %s", source)
            raise Exception("Error saving new source")

        self.__refresh_sources()

    def delete_source(self, source_filename):
        """
        Delete specified source

        Args:
            source_filename (str): source filename

        Raises:
            Exception if error occured
        """
        if not source_filename or not isinstance(source_filename, str):
            raise MissingParameter('Parameter "source_filename" is missing')
        if source_filename in [AppsSources.CLEEP_APPS_FREE["filename"], AppsSources.CLEEP_APPS_NON_FREE["filename"]]:
            raise InvalidParameter('Parameter "source_filename" must not refer to a Cleep source')

        data = self.cleep_filesystem.read_json(self.APPS_SOURCES_PATH, "utf8")
        new_sources = [
            source
            for source in data["sources"]
            if source["filename"] != source_filename
        ]
        data["sources"] = new_sources

        if not self.cleep_filesystem.write_json(self.APPS_SOURCES_PATH, data, "utf8"):
            self.logger.error("Error saving new source %s", source_filename)
            raise Exception("Error saving new source")

        self.__refresh_sources()

    def get_market(self):
        """
        Get all applications from aggregated content for all registered sources

        Returns:
            dict: None if file doesn't exist (please use exists function) or modules.json content as dict::

                {
                    update (int): last update timestamp
                    list (dict): dict of available modules
                }
        """
        if self.apps["update"] != 0:
            return deepcopy(self.apps)

        self.update_market(force_update=False)
        return deepcopy(self.apps)

    def update_market(self, force_update=True):
        """
        Update all applications from all sources

        Args:
            force_update (bool): force update if True (internal usage). Default True

        Returns:
            bool: True if at least one source has been updated since last update
        """
        self.logger.info('Updating applications list')
        apps = {
            "update": self.apps.get("update", 0),
            "list": {},
        }
        has_updates = False

        for source in self.sources:
            # update if not exists
            updated, source_apps = self.__get_modules_json_content(force_update, source)
            self.logger.debug('Apps from source "%s": %s' % (source["filename"], source_apps))

            apps["list"].update(source_apps["list"])
            if updated:
                self.logger.debug('Source "%s" was updated since last update', source["filename"])
                has_updates = True
                if source_apps["update"] > apps["update"]:
                    apps["update"] = source_apps["update"]

        self.apps = apps
        self.logger.info('Found %s available applications', len(apps["list"].keys()))

        return has_updates

    def __get_modules_json_content(self, force_update, source):
        """
        Get content from modules.json

        Returns:
            tuple: updated status and modules.json content
        """
        modules_json = ModulesJson(self.cleep_filesystem, self.SOURCES_PATH, source)

        updated = False
        if force_update or not modules_json.exists():
            try:
                self.logger.debug('Updating source "%s"', source)
                updated = modules_json.update()
            except Exception as error:
                self.logger.error('Error occured while updating source "%s": %s', source, str(error))
                return False, modules_json.get_empty()

        return updated, modules_json.get_content()
