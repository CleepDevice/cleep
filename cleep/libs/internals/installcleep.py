#!/usr/bin/env python
# -*- coding: utf-8 -*

import logging
import time
import os
import inspect
from zipfile import ZipFile
import threading
import tempfile
import stat
from cleep.libs.internals.console import EndlessConsole
from cleep.core import CleepModule
from cleep.libs.internals.download import Download
from cleep.libs.internals.installdeb import InstallDeb


PATH_FRONTEND = '/opt/cleep/html'
PATH_INSTALL = '/etc/cleep/install/'
FRONTEND_DIR = 'frontend/'
BACKEND_DIR = 'backend/'


class ForcedException(Exception):
    def __init__(self, code):
        Exception.__init__(self)
        self.code = code

class InstallCleep(threading.Thread):
    """
    Install cleep update
    This class download latest package from cleep repository, dry run deb install and finally
    install deb package.
    """
    STATUS_IDLE = 0
    STATUS_UPDATING = 1
    STATUS_UPDATED = 2
    STATUS_ERROR_INTERNAL = 3
    STATUS_ERROR_DOWNLOAD_CHECKSUM = 4
    STATUS_ERROR_DOWNLOAD_PACKAGE = 5
    STATUS_ERROR_DEB = 6

    def __init__(self, cleep_filesystem, crash_report):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
            crash_report (CrashReport): CrashReport instance
        """
        threading.Thread.__init__(self, daemon=True, name='installcleep')

        # logger   
        self.logger = logging.getLogger(self.__class__.__name__)
        # self.logger.setLevel(logging.DEBUG)

        # members
        self.status = self.STATUS_IDLE
        self.cleep_filesystem = cleep_filesystem
        self.crash_report = crash_report
        self.__reset()

    def __reset(self):
        self.running = True
        self.__progress = 0
        self.__script_running = True
        self.__deb_status = {
            'status': InstallDeb.STATUS_IDLE,
            'stdout': [],
            'returncode': None
        }
        self.__last_download_percent = None

    def install(self, url_package, url_checksum, callback):
        """
        Launch installation.
        The process is non blocking. Follow install process status using get_status.

        Args:
            url_package (string): url of Cleep deb package
            url_checksum (string): url of checksum
            callback (function): status callback
        """
        self.url_package = url_package
        self.url_checksum = url_checksum
        self.callback = callback
        self.__reset()
        self.start()

    def get_status(self):
        """
        Return current status

        Returns:
            dict: update status::

                {
                    progress (int): progress percentage
                    status (int): see STATUS_XXX for available codes
                    deb (dict): deb status (status, returncode, stdout, stderr)
                }

        """
        return {
            'progress': self.__progress,
            'status': self.status,
            'deb': self.__deb_status
        }

    def __download_callback(self, status, filesize, percent):
        """
        Download callback
        """
        # just log download status
        if not percent % 10 and percent!=self.__last_download_percent: # pragma: no cover
            self.__last_download_percent = percent
            self.logger.debug('Download callback: %s %s %s' % (status, filesize, percent))

    def __download_checksum(self, download, url_checksum):
        """
        Download specified checksum file

        Args:
            download (Download): Download instance
            url_checksum (string): checksum file url

        Returns:
            string: checkum file content, None if something failed
        """
        checksum = None

        try:
            # download checksum
            self.logger.debug('Download file "%s"' % url_checksum)
            download_status, checksum_content = download.download_content(url_checksum)
            self.logger.debug('Checksum file content: %s' % checksum_content)

            checksum = None if checksum_content is None else checksum_content.split()[0]
            self.logger.debug('Cleep package checksum: %s' % checksum)

        except:
            self.logger.exception('Exception occured during checksum file download "%s":' % url_checksum)
            self.crash_report.report_exception()
            checksum = None

        return checksum

    def __download_package(self, download, url_package, checksum):
        """
        Download cleep packagee file

        Args:
            download (Download): Download instance
            url_package (string): deb package url
            checksum (string): checksum to use to validate download

        Returns:
            string: downloaded package path or None if error occured
        """
        package_path = None

        try:
            self.logger.debug('Download file "%s"' % self.url_package)
            download_status, package_path = download.download_file(url_package, check_sha256=checksum)

            self.logger.debug('Download terminated with status "%s" and package path "%s"' % (download_status, package_path))
            if package_path is None:
                if download_status==Download.STATUS_ERROR:
                    error = 'Error during "%s" download: internal error' % self.url_package
                elif download_status==Download.STATUS_ERROR_INVALIDSIZE:
                    error = 'Error during "%s" download: invalid filesize' % self.url_package
                elif download_status==Download.STATUS_ERROR_BADCHECKSUM:
                    error = 'Error during "%s" download: invalid checksum' % self.url_package
                else:
                    error = 'Error during "%s" download: unknown error' % self.url_package
                self.logger.error(error)
                package_path = None

        except:
            self.logger.exception('Exception occured during cleepos package "%s" download:' % url_package)
            self.crash_report.report_exception()
            package_path = None

        return package_path

    def __install_deb(self, package_path):
        """
        Install deb

        Args:
            package_path (string): deb package path

        Returns:
            bool: True if installation succeed, False otherwise
        """
        error = False

        try:
            # prepare installer
            self.logger.debug('Installing "%s" debian package' % package_path)
            installer = InstallDeb(self.cleep_filesystem, self.crash_report)

            # dry run install
            if not installer.dry_run(package_path):
                # dry run failed, report error and quit install
                self.logger.error('Install dry-run failed: %s' % installer.get_status())
                self.crash_report.manual_report('Dry-run cleep install failed', installer.get_status())
                raise ForcedException(0)

            # install deb
            self.logger.debug('Waiting for end of debian package install...')
            installer.install(package_path, blocking=True)
            self.logger.debug('Deb package install terminated with status: %s' % installer.get_status())

            # check deb install result
            if installer.get_status()['status']!=installer.STATUS_DONE:
                self.logger.error('Cleep updated failed (installer returns status "%s" while "%s" awaited)' % (installer.get_status()['status'], installer.STATUS_DONE))
                self.crash_report.manual_report('Cleep update failed: deb install failed', installer.get_status())
                error = True

        except ForcedException:
            error = True

        except:
            # deb install failed
            self.logger.exception('Exception occured during deb package install:')
            self.crash_report.report_exception()
            error = True

        finally:
            if installer:
                self.__deb_status = installer.get_status()

        return not error

    def run(self):
        """
        Run update
        """
        #init
        self.logger.info('Start Cleep update')
        self.status = self.STATUS_UPDATING
        error = False
        package_path = None
        extract_path = None

        try:
            # send status asap to update frontend
            if self.callback:
                self.__progress = 0
                self.callback(self.get_status())

            # download checksum file
            download = Download(self.cleep_filesystem)
            checksum = self.__download_checksum(download, self.url_checksum)
            if not checksum:
                self.status = self.STATUS_ERROR_DOWNLOAD_CHECKSUM
                raise ForcedException(0)

            # send status
            if self.callback:
                self.__progress = 33
                self.callback(self.get_status())

            # download cleep deb package
            package_path = self.__download_package(download, self.url_package, checksum)
            if not package_path:
                self.status = self.STATUS_ERROR_DOWNLOAD_PACKAGE
                raise ForcedException(1)

            # send status
            if self.callback:
                self.__progress = 66
                self.callback(self.get_status())

            # install deb package
            if not self.__install_deb(package_path):
                self.status = self.STATUS_ERROR_DEB
                raise ForcedException(2)

            # send status
            if self.callback:
                self.__progress = 100
                self.callback(self.get_status())

        except ForcedException as e:
            # a step failed, error should already be logged
            self.logger.debug('Error occured during Cleep update [%s]' % e.code)
            error = True

        except:
            self.logger.exception('Exception occured during Cleep update:')
            self.crash_report.report_exception()
            error = True

        finally:
            # clean stuff
            try:
                if package_path:
                    self.cleep_filesystem.rm(package_path)
                if extract_path:
                    self.cleep_filesystem.rmdir(extract_path)
            except: # pragma: no cover
                self.logger.exception('Exception during Cleep update cleaning:')

            if error:
                # error occured
                self.logger.debug('Error occured during Cleep update')

                # fix unspecified error status
                if self.status==self.STATUS_UPDATING: # pragma: no cover
                    self.status = self.STATUS_ERROR_INTERNAL
            else:
                # update terminated successfully
                self.status = self.STATUS_UPDATED

            # send status
            if self.callback:
                self.__progress = 100
                try:
                    self.callback(self.get_status())
                except: # pragma: no cover
                    pass

        self.logger.info('Cleep update terminated (success: %s)' % (not error))
    

