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

    def __init__(self, url_raspiot, url_checksum, callback, cleep_filesystem):
        """
        Constructor

        Args:
            url_raspiot (string): url of raspiot archive
            url_checksum (string): url of checksum
            callback (function): status callback
            cleep_filesystem (CleepFilesystem): CleepFilesystem singleton
        """
        threading.Thread.__init__(self)
        threading.Thread.daemon = True

        #logger   
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)

        #members
        self.status = self.STATUS_IDLE
        self.running = True
        self.cleep_filesystem = cleep_filesystem
        self.url_raspiot = url_raspiot
        self.url_checksum = url_checksum
        self.__script_running = True
        self.__pre_script_execution = False
        self.__pre_script_status = {u'stdout': [], u'stderr':[], u'returncode': None}
        self.__post_script_status = {u'stdout': [], u'stderr':[], u'returncode': None}
        self.__deb_status = {u'status': InstallDeb.STATUS_IDLE, u'stdout': [], u'stderr': [], u'returncode':None}
        self.callback = callback
        self.__last_download_percent = None

    def get_status(self):
        """
        Return current status

        Return:
            dict: update status::
                {
                    status (int): see STATUS_XXX for available codes
                    prescript (dict): preinst status (returncode, stdout, stderr)
                    postscript (dict): postinst status (returncode, stdout, stderr)
                    deb (dict): deb status (status, returncode, stdout, stderr)
                }
        """
        return {
            u'status': self.status,
            u'prescript': self.__pre_script_status,
            u'postscript': self.__post_script_status,
            u'deb': self.__deb_status
        }

    def __download_callback(self, status, filesize, percent):
        """
        Download callback
        """
        #just log download status
        if not percent % 10 and percent!=self.__last_download_percent:
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
        if killed:
            if self.__pre_script_execution:
                self.__pre_script_status[u'returncode'] = 130
            else:
                self.__post_script_status[u'returncode'] = 130
        else:
            if self.__pre_script_execution:
                self.__pre_script_status[u'returncode'] = return_code
            else:
                self.__post_script_status[u'returncode'] = return_code

        #script execution terminated
        self.__script_running = False

    def __execute_script(self, path):
        """
        Execute specified script

        Args:
            path (string): script path

        Return
        """
        #init
        os.chmod(path, stat.S_IEXEC)

        #exec
        console = EndlessConsole(path, self.__script_callback, self.__script_terminated_callback)
        out = False

        #launch script execution
        console.start()

        #monitor end of script execution
        self.__script_running = True
        while self.__script_running:
            #pause
            time.sleep(0.25)

        #check script result
        if self.__pre_script_execution and self.__pre_script_status[u'returncode']==0:
            out = True
        elif self.__post_script_status[u'returncode']==0:
            out = True

        return out

    def stop(self):
        """
        Stop update
        """
        self.running = False

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

        #send status asap to update frontend
        if self.callback:
            self.callback(self.get_status())

        try:
            #download checksum file
            download = Download(self.cleep_filesystem, self.__download_callback)
            self.logger.debug(u'Download file "%s"' % self.url_checksum)
            try:
                checksum_content = download.download_file(self.url_checksum)
                self.logger.debug('Checksum file content: %s' % checksum_content)
                if checksum_content is None:
                    #failed to download checksum file
                    raise Exception(u'')
                checksum, _ = checksum_content.split()
                self.logger.debug(u'Raspiot archive checksum: %s' % checksum)

            except Exception as e:
                if len(e.message)>0:
                    self.logger.exception(u'Exception occured during checksum file download "%s":' % self.url_checksum)
                self.status = self.STATUS_ERROR_DOWNLOAD_CHECKSUM
                raise Exception(u'Forced exception')

            #canceled ?
            if not self.running:
                raise Exception(u'Canceled exception')

            #send status
            if self.callback:
                self.callback(self.get_status())

            #download raspiot archive
            self.logger.debug(u'Download file "%s"' % self.url_raspiot)
            try:
                #blocking mode
                archive_path = download.download_file_advanced(self.url_raspiot, check_sha256=checksum)
                self.logger.debug(u'Download terminated with result: %s' % archive_path)
                if archive_path is None:
                    download_status = download.get_status()
                    if download_status==download.STATUS_ERROR:
                        self.error = u'Error during "%s" download: internal error' % self.url_raspiot
                    if download_status==download.STATUS_ERROR_INVALIDSIZE:
                        self.error = u'Error during "%s" download: invalid filesize' % self.url_raspiot
                    elif download_status==download.STATUS_ERROR_BADCHECKSUM:
                        self.error = u'Error during "%s" download: invalid checksum' % self.url_raspiot
                    else:
                        self.error = u'Error during "%s" download: unknown error' % self.url_raspiot
                    self.logger.error(self.error)

                    raise Exception(u'')

            except:
                self.status = self.STATUS_ERROR_DOWNLOAD_ARCHIVE
                raise Exception(u'Forced exception')

            #canceled ?
            if not self.running:
                raise Exception(u'Canceled exception')

            #send status
            if self.callback:
                self.callback(self.get_status())

            #extract archive
            self.logger.debug('Extracting archive "%s"' % archive_path)
            extract_path = None
            try:
                zipfile = ZipFile(archive_path, u'r')
                extract_path = tempfile.mkdtemp()
                self.logger.debug('Extracting archive to "%s"' % extract_path)
                zipfile.extractall(extract_path)
                zipfile.close()
                self.logger.debug(u'Archive extracted successfully')

            except:
                self.logger.exception(u'Error decompressing raspiot archive "%s" in "%s":' % (archive_path, extract_path))
                self.status = self.STATUS_ERROR_EXTRACT
                raise Exception(u'Forced exception')

            #canceled ? last chance
            if not self.running:
                raise Exception(u'Canceled exception')

            #send status
            if self.callback:
                self.callback(self.get_status())

            #pre update script
            try:
                self.logger.debug(u'Executing preinst.sh script')
                self.__pre_script_execution = True
                path = os.path.join(extract_path, u'preinst.sh')
                if os.path.exists(path):
                    self.__script_running = True
                    if not self.__execute_script(path):
                        #script failed
                        self.logger.debug(u'Script preinst.sh execution failed')
                        raise Exception(u'')
                else:
                    self.logger.debug(u'No preinst.sh script in archive')

            except Exception as e:
                if len(e.message)>0:
                    self.logger.exception(u'Exception occured during preinst.sh script execution:')
                self.status = self.STATUS_ERROR_PREINST
                raise Exception(u'Forced exception')

            #send status
            if self.callback:
                self.callback(self.get_status())

            #install deb package
            archive_path = None
            try:
                self.logger.debug(u'Installing deb package')
                deb_path = os.path.join(extract_path, u'raspiot.deb')
                self.logger.debug('Installing "%s" package' % deb_path)
                installer = InstallDeb(None, self.cleep_filesystem, blocking=False)
                installer.install(deb_path)
                #time.sleep(1.0)

                #wait until end of script
                while installer.get_status()[u'status']==installer.STATUS_RUNNING:
                    time.sleep(0.25)
                self.__deb_status = installer.get_status()
                self.logger.debug(u'Deb package install terminated with status: %s' % self.__deb_status)

                #check deb install result
                if installer.get_status()[u'status']!=installer.STATUS_DONE:
                    raise Exception(u'Forced exception')

            except Exception as e:
                #deb install failed
                if e.message!=u'Forced exception':
                    self.logger.exception(u'Exception occured during deb package install:')
                self.status = self.STATUS_ERROR_DEB
                raise Exception(u'Forced exception')

            #send status
            if self.callback:
                self.callback(self.get_status())

            #post update script
            try:
                self.logger.debug(u'Executing postinst.sh script')
                self.__pre_script_execution = False
                path = os.path.join(extract_path, u'postinst.sh')
                if os.path.exists(path):
                    self.__script_running = True
                    if not self.__execute_script(path):
                        #script failed
                        self.logger.debug(u'Script postinst.sh execution failed')
                        raise Exception(u'')
                else:
                    self.logger.debug(u'No postinst.sh script in archive')

            except Exception as e:
                if len(e.message)>0:
                    self.logger.exception(u'Exception occured during postinst.sh script execution:')
                self.status = self.STATUS_ERROR_POSTINST
                raise Exception(u'Forced exception')

            #send status
            if self.callback:
                self.callback(self.get_status())

        except Exception as e:
            #local exception raised, invalid state :S
            if e.message not in (u'Forced exception', u'Canceled exception'):
                self.logger.exception(u'Exception occured during raspiot update:')
            error = True

        finally:
            #clean stuff
            try:
                if archive_path:
                    self.cleep_filesystem.rm(archive_path)
                if extract_path:
                    self.cleep_filesystem.rmdir(extract_path)

            except:
                self.logger.exception(u'Exception during raspiot update cleaning:')

            if error:
                #error occured
                self.logger.debug('Error occured during raspiot update')

                #fix unspecified error status
                if self.status==self.STATUS_UPDATING:
                    self.status = self.STATUS_ERROR_INTERNAL
            else:
                #update terminated successfully
                self.status = self.STATUS_UPDATED

            #send status
            if self.callback:
                self.callback(self.get_status())

        self.logger.info(u'Raspiot update terminated (success: %s)' % (not error))
    

