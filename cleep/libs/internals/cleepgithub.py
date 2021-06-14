#!/usr/bin/env python
# -*- coding: utf-8 -*

import logging
import time
import requests
import json
import re
import os


class CleepGithub:
    """
    Github release helper
    This class get releases from specified project and return content as dict
    """

    GITHUB_URL = "https://api.github.com/repos/%s/%s/releases"
    GITHUB_RATE = "https://api.github.com/rate_limit"

    def __init__(self, auth_string=None):
        """
        Constructor

        Args:
            auth_string (string): if specified add authorization field in requests header (Bearer xxxx, Token xxx)
        """
        # logger
        self.logger = logging.getLogger(self.__class__.__name__)

        # members
        self.http_headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0"
        }
        self.version_pattern = r"\d+\.\d+\.\d+"
        if auth_string:
            self.http_headers["Authorization"] = auth_string

    def get_api_rate(self):
        """
        Get current api rate
        Api requests are limited on free usage of github. This method returns current rate

        Returns:
            dict: general rate values::

                {
                    limit (int): limit of requests
                    remaining (int): number of requests processed
                    reset (int): timestamp when rate is resetted to limit
                }

        """
        try:
            resp = requests.get(self.GITHUB_RATE, headers=self.http_headers)
            self.logger.trace('GET "%s": %s' % (self.GITHUB_RATE, resp.text))

            if resp.status_code == 200:
                # response successful, parse data to get current latest version
                data = resp.json()
                self.logger.debug("Data: %s" % data)

                if "rate" in data:
                    return data["rate"]
                else:
                    raise Exception("Invalid data from github rate_limit request")
            else:
                raise Exception("Invalid response (status=%d)" % resp.status_code)

        except Exception as error:
            self.logger.exception("Unable to get api rate:")
            raise Exception("Unable to get api rate: %s" % str(error))

    def get_release_version(self, release):
        """
        Return version of specified release

        Args:
            release (dict): release data as returned by get_releases function

        Returns:
            string: version of release

        Raises:
            Exception if version field not found or input release is invalid
        """
        if not isinstance(release, dict):
            raise Exception("Invalid release format. Dict type awaited")

        if "tag_name" in release.keys():
            version = re.search(self.version_pattern, release["tag_name"])
            if version:
                return version.group()
            return release["tag_name"]

        else:
            raise Exception("Specified release has no version field")

    def get_release_changelog(self, release):
        """
        Return changelog of specified release

        Args:
            release (dict): release data as returned by get_releases function

        Returns:
            string: changelog of release. Can be empty string if no changelog specified.

        Raises:
            Exception if version field not found or input release is invalid
        """
        if not isinstance(release, dict):
            raise Exception("Invalid release format. Dict type awaited")

        if "body" in release.keys():
            return release["body"]
        else:
            # no body tag found, return empty string
            return ""

    def is_released(self, release):
        """
        Return True if release is released (it means not prerelease or draft)

        Args:
            release (dict): release data as returned by get_releases function

        Returns:
            bool: True if release is released

        Raises:
            Exception if input release is invalid
        """
        if not isinstance(release, dict):
            raise Exception("Invalid release format. Dict type awaited")

        prerelease = True
        if "prerelease" in release.keys():
            prerelease = release["prerelease"]
        draft = True
        if "draft" in release.keys():
            draft = release["draft"]

        return not prerelease and not draft

    def get_release_assets_infos(self, release):
        """
        Return simplified structure of all release assets

        Args:
            release (dict): release data as returned by get_releases function

        Returns:
            list of dict: list of assets infos (name, url, size)::

                [
                    {
                        name (string): asset name
                        url (string): download url
                        size (int): asset size
                    },
                    ...
                ]

        Raises:
            Exception if input release is invalid
        """
        if not isinstance(release, dict):
            raise Exception("Invalid release format. Dict type awaited")
        if "assets" not in release.keys():
            raise Exception("Invalid release format")

        out = []
        for asset in release["assets"]:
            if "browser_download_url" and "size" and "name" in asset.keys():
                out.append(
                    {
                        "name": asset["name"],
                        "url": asset["browser_download_url"],
                        "size": asset["size"],
                    }
                )

        return out

    def __get_all_releases(self, owner, repository):
        """
        Get releases of specify project repository

        Args:
            owner (string): name of owner
            repository (string): name of repository

        Returns:
            list: list of releases. Format can be found here https://developer.github.com/v3/repos/releases/

        Raises:
            Exception if error occured during request
        """
        try:
            url = self.GITHUB_URL % (owner, repository)
            resp = requests.get(url, headers=self.http_headers)
            self.logger.trace('GET "%s"' % url)

            if resp.status_code == 200:
                # response successful, parse data to get current latest version
                data = resp.json()
                self.logger.debug("Data: %s" % data)

                # return all releases
                return data

            else:
                raise Exception(
                    "Invalid response (status=%d): %s"
                    % (resp.status_code, resp.text.encode("utf8"))
                )

        except Exception as e:
            self.logger.exception("Unable to get releases:")
            raise Exception("Unable to get releases: %s" % str(e))

    def __get_released_releases(self, owner, repository):
        """
        Get released releases

        Args:
            owner (string): name of owner
            repository (string): name of repository
        """
        return [
            release
            for release in self.__get_all_releases(owner, repository)
            if self.is_released(release)
        ]

    def get_releases(self, owner, repository, only_latest=False, only_released=True):
        """
        Get releases of specify project repository

        Args:
            owner (string): name of owner
            repository (string): name of repository
            only_latest (bool): if True returns only latest release
            only_released (bool): if True returns only released releases

        Returns:
            list: list of releases. Format can be found here https://developer.github.com/v3/repos/releases/
        """
        # get all releases
        if only_released:
            releases = self.__get_released_releases(owner, repository)
        else:
            releases = self.__get_all_releases(owner, repository)

        if only_latest:
            # return only latest release
            return releases[0:1]

        return releases
