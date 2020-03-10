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
from raspiot.utils import ForcedException
from raspiot.libs.internals.console import EndlessConsole
from raspiot.raspiot import RaspIotModule
from raspiot.libs.internals.download import Download
from raspiot.libs.internals.installdeb import InstallDeb


PATH_FRONTEND = u'/opt/raspiot/html'
PATH_INSTALL = u'/etc/raspiot/install/'
FRONTEND_DIR = u'frontend/'
BACKEND_DIR = u'backend/'


class InstallRaspiot(threading.Thread):
    """
    Install raspiot update
    This class download latest archive from raspiot repository, executes prescript, installs deb package
    and ends by post script install
    """
    STATUS_IDLE = 0
    STATUS_UPDATING = 1
    STATUS_UPDATED = 2
    STATUS_ERROR_INTERNAL = 3
    STATUS_ERROR_DOWNLOAD_CHECKSUM = 4
    STATUS_ERROR_DOWNLOAD_ARCHIVE = 5
    STATUS_ERROR_EXTRACT = 6
    STATUS_ERROR_PREINST = 7
    STATUS_ERROR_DEB = 8
    STATUS_ERROR_POSTINST = 9

    def __init__(self, cleep_filesystem, crash_report):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
            crash_report (CrashReport): CrashReport instance
        """
        threading.Thread.__init__(self)
        threading.Thread.daemon = True

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
        self.__pre_script_execution = False
        self.__pre_script_status = {
            u'stdout': [],
            u'stderr':[],
            u'returncode': None
        }
        self.__post_script_status = {
            u'stdout': [],
            u'stderr':[],
            u'returncode': None
        }
        self.__deb_status = {
            u'status': InstallDeb.STATUS_IDLE,
            u'stdout': [],
            u'returncode': None
        }
        self.__last_download_percent = None

    def install(self, url_archive, url_checksum, callback):
        """
        Launch installation.
        The process is non blocking. Follow install process status using get_status.

        Args:
            url_archive (string): url of cleepos archive
            url_checksum (string): url of checksum
            callback (function): status callback
        """
        self.url_archive = url_archive
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
                    prescript (dict): preinst status (returncode, stdout, stderr)
                    postscript (dict): postinst status (returncode, stdout, stderr)
                    deb (dict): deb status (status, returncode, stdout, stderr)
                }

        """
        return {
            u'progress': self.__progress,
            u'status': self.status,
            u'prescript': self.__pre_script_status,
            u'postscript': self.__post_script_status,
            u'deb': self.__deb_status
        }

    def __download_callback(self, status, filesize, percent):
        """
        Download callback
        """
        # just log download status
        if not percent % 10 and percent!=self.__last_download_percent: # pragma: no cover
            self.__last_download_percent = percent
            self.logger.debug('Download callback: %s %s %s' % (status, filesize, percent))

    def __script_callback(self, stdout, stderr):
        """
        Get stdout/stderr from script execution

        Args:
            stdout (string): stdout line
            stderr (string): stderr line
        """
        if self.__pre_script_execution:
            if stdout:
                self.__pre_script_status[u'stdout'].append(stdout)
            if stderr:
                self.__pre_script_status['stderr'].append(stderr)

        else:
            if stdout:
                self.__post_script_status[u'stdout'].append(stdout)
            if stderr:
                self.__post_script_status[u'stderr'].append(stderr)

    def __script_terminated_callback(self, return_code, killed):
        """
        Get infos when script is terminated

        Note:
            see http://www.tldp.org/LDP/abs/html/exitcodes.html for return codes

        Args:
            return_code (int): script return code
            killed (bool): True if script killed, False otherwise
        """
        self.logger.debug(u'Script execution terminated with returncode=%s and killed=%s' % (return_code, killed))
        if killed: # pragma: no cover
            if self.__pre_script_execution:
                self.__pre_script_status[u'returncode'] = 130
            else:
                self.__post_script_status[u'returncode'] = 130
        else:
            if self.__pre_script_execution:
                self.__pre_script_status[u'returncode'] = return_code
            else:
                self.__post_script_status[u'returncode'] = return_code

        # script execution terminated
        self.__script_running = False

    def __execute_script(self, path):
        """
        Execute specified script
        This method is blocking !

        Args:
            path (string): script path

        Returns:
            bool: True if script execution succeed
        """
        # init
        out = False

        # exec
        os.chmod(path, stat.S_IEXEC)
        console = EndlessConsole(path, self.__script_callback, self.__script_terminated_callback)

        # launch script execution
        console.start()

        # monitor end of script execution
        self.__script_running = True
        while self.__script_running:
            #pause
            time.sleep(0.25)

        # check script result
        if self.__pre_script_execution and self.__pre_script_status[u'returncode']==0:
            out = True
        elif self.__post_script_status[u'returncode']==0:
            out = True

        return out

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
            self.logger.debug(u'Download file "%s"' % url_checksum)
            download_status, checksum_content = download.download_content(url_checksum)
            self.logger.debug(u'Checksum file content: %s' % checksum_content)

            checksum = None if checksum_content is None else checksum_content.split()[0]
            self.logger.debug(u'Raspiot archive checksum: %s' % checksum)

        except:
            self.logger.exception(u'Exception occured during checksum file download "%s":' % url_checksum)
            self.crash_report.report_exception()
            checksum = None

        return checksum

    def __download_archive(self, download, url_archive, checksum):
        """
        Download raspiot archive file

        Args:
            download (Download): Download instance
            url_archuive (string): archive file url
            checksum (string): checksum to use to validate download

        Returns:
            string: downloaded archive path or None if error occured
        """
        archive_path = None

        try:
            self.logger.debug(u'Download file "%s"' % self.url_archive)
            download_status, archive_path = download.download_file(url_archive, check_sha256=checksum)

            self.logger.debug(u'Download terminated with status "%s" and archive path "%s"' % (download_status, archive_path))
            if archive_path is None:
                if download_status==Download.STATUS_ERROR:
                    error = u'Error during "%s" download: internal error' % self.url_archive
                elif download_status==Download.STATUS_ERROR_INVALIDSIZE:
                    error = u'Error during "%s" download: invalid filesize' % self.url_archive
                elif download_status==Download.STATUS_ERROR_BADCHECKSUM:
                    error = u'Error during "%s" download: invalid checksum' % self.url_archive
                else:
                    error = u'Error during "%s" download: unknown error' % self.url_archive
                self.logger.error(error)
                archive_path = None

        except:
            self.logger.exception(u'Exception occured during cleepos archive "%s" download:' % url_archive)
            self.crash_report.report_exception()
            archive_path = None

        return archive_path

    def __extract_archive(self, archive_path):
        """
        Extract specified archive

        Args:
            archive_path (string): archive to extract

        Returns:
            string: extract path or None if error occured
        """
        self.logger.debug('Extracting archive "%s"' % archive_path)
        extract_path = None

        try:
            extract_path = tempfile.mkdtemp()
            self.logger.debug('Extraction path: "%s"' % extract_path)

            zipfile = ZipFile(archive_path, u'r')
            zipfile.extractall(extract_path)
            zipfile.close()
            self.logger.debug(u'Archive extracted successfully')

        except:
            self.logger.exception(u'Error decompressing raspiot archive "%s" in "%s":' % (archive_path, extract_path))
            self.crash_report.report_exception()
            extract_path = None

        return extract_path

    def __execute_preinst_script(self, extract_path):
        """
        Execute preinst.sh script

        Args:
            extract_path (string): archive extract path

        Returns:
            bool: True if prescript execution succeed
        """
        error = False

        self.logger.debug(u'Executing preinst.sh script')
        try:
            self.__pre_script_execution = True
            path = os.path.join(extract_path, u'preinst.sh')
            if os.path.exists(path):
                self.__script_running = True
                if not self.__execute_script(path):
                    # script failed
                    self.logger.debug(u'Script preinst.sh execution failed')
                    self.crash_report.manual_report(u'Raspiot update failed: prescript failed', self.__pre_script_status)
                    error = True
                else:
                    self.logger.debug(u'Script preinst.sh execution terminated successfully: %s' % self.__pre_script_status)
            else:
                self.logger.debug(u'No preinst.sh script in archive')

        except:
            self.logger.exception(u'Exception occured during preinst.sh script execution:')
            self.crash_report.report_exception()
            error = True

        return not error

    def __execute_postinst_script(self, extract_path):
        """
        Execute postinst.sh script

        Args:
            extract_path (string): archive extract path

        Returns:
            bool: True if prescript execution succeed
        """
        error = False

        try:
            self.logger.debug(u'Executing postinst.sh script')
            self.__pre_script_execution = False
            path = os.path.join(extract_path, u'postinst.sh')
            if os.path.exists(path):
                self.__script_running = True
                if not self.__execute_script(path):
                    # script failed
                    self.logger.debug(u'Script postinst.sh execution failed: %s' % self.__post_script_status)
                    self.crash_report.manual_report(u'Raspiot update failed: postscript failed', self.__post_script_status)
                    error = True
                else:
                    self.logger.debug(u'Script postinst.sh execution terminated successfully: %s' % self.__post_script_status)
            else:
                self.logger.debug(u'No postinst.sh script in archive')

        except:
            self.logger.exception(u'Exception occured during postinst.sh script execution:')
            self.crash_report.report_exception()
            error = True

        return not error

    def __install_deb(self, extract_path):
        """
        Install deb

        Args:
            extract_path (string): archive extraction path

        Returns:
            bool: True if installation succeed, False otherwise
        """
        error = False

        try:
            # prepare installer
            deb_path = os.path.join(extract_path, u'raspiot.deb')
            self.logger.debug('Installing "%s" debian package' % deb_path)
            installer = InstallDeb(self.cleep_filesystem, self.crash_report)

            # dry run install
            if not installer.dry_run(deb_path):
                #dry run failed, report error and quit install
                self.logger.error(u'Install dry-run failed: %s' % installer.get_status())
                self.crash_report.manual_report(u'Dry-run raspiot install failed', installer.get_status())
                raise ForcedException()

            # install deb
            self.logger.debug(u'Waiting for end of debian package install...')
            installer.install(deb_path, blocking=True)
            self.logger.debug(u'Deb package install terminated with status: %s' % installer.get_status())

            # check deb install result
            if installer.get_status()[u'status']!=installer.STATUS_DONE:
                self.logger.error('Raspiot updated failed (installer returns status "%s" while "%s" awaited)' % (installer.get_status()[u'status'], installer.STATUS_DONE))
                self.crash_report.manual_report(u'Raspiot update failed: deb install failed', installer.get_status())
                error = True

        except ForcedException:
            error = True

        except:
            #deb install failed
            self.logger.exception(u'Exception occured during deb package install:')
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
        self.logger.info(u'Start raspiot update')
        self.status = self.STATUS_UPDATING
        error = False
        archive_path = None
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
                self.__progress = 16
                self.callback(self.get_status())

            # download raspiot archive
            archive_path = self.__download_archive(download, self.url_archive, checksum)
            if not archive_path:
                self.status = self.STATUS_ERROR_DOWNLOAD_ARCHIVE
                raise ForcedException(1)

            # send status
            if self.callback:
                self.__progress = 32
                self.callback(self.get_status())

            # extract archive
            extract_path = self.__extract_archive(archive_path)
            if not extract_path:
                self.status = self.STATUS_ERROR_EXTRACT
                raise ForcedException(2)

            # send status
            if self.callback:
                self.__progress = 48
                self.callback(self.get_status())

            # pre update script
            if not self.__execute_preinst_script(extract_path):
                self.status = self.STATUS_ERROR_PREINST
                raise ForcedException(3)

            # send status
            if self.callback:
                self.__progress = 64
                self.callback(self.get_status())

            # install deb package
            if not self.__install_deb(extract_path):
                self.status = self.STATUS_ERROR_DEB
                raise ForcedException(4)

            # send status
            if self.callback:
                self.__progress = 80
                self.callback(self.get_status())

            # post update script
            if not self.__execute_postinst_script(extract_path):
                self.status = self.STATUS_ERROR_POSTINST
                raise ForcedException(5)

            # send status
            if self.callback:
                self.__progress = 96
                self.callback(self.get_status())

        except ForcedException as e:
            # a step failed, error should already be logged
            self.logger.debug(u'Error occured during raspiot update [%s]' % e.code)
            error = True

        except:
            self.logger.exception(u'Exception occured during raspiot update:')
            self.crash_report.report_exception()
            error = True

        finally:
            # clean stuff
            try:
                if archive_path:
                    self.cleep_filesystem.rm(archive_path)
                if extract_path:
                    self.cleep_filesystem.rmdir(extract_path)
            except: # pragma: no cover
                self.logger.exception(u'Exception during raspiot update cleaning:')

            if error:
                # error occured
                self.logger.debug('Error occured during raspiot update')

                # fix unspecified error status
                if self.status==self.STATUS_UPDATING: # pragma: no cover
                    self.status = self.STATUS_ERROR_INTERNAL
            else:
                # update terminated successfully
                self.status = self.STATUS_UPDATED

            # send status
            if self.callback:
                self.__progress = 100
                self.callback(self.get_status())

        self.logger.info(u'Raspiot update terminated (success: %s)' % (not error))
    

