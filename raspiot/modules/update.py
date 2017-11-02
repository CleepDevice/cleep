#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from raspiot.raspiot import RaspIotModule
import time
from raspiot.libs.download import Download
from raspiot.libs.install import Install
from raspiot.libs.github import Github
from raspiot import __version__ as VERSION
from raspiot.libs.task import BackgroundTask

__all__ = [u'Update']


class Update(RaspIotModule):

    MODULE_CONFIG_FILE = u'update.conf'
    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Keep your device up-to-date with automatic updates'
    MODULE_LOCKED = True
    MODULE_URL = None
    MODULE_TAGS = [u'update', u'raspiot']
    MODULE_COUNTRY = None
    MODULE_LINK = None

    DEFAULT_CONFIG = {
        u'last_update': None,
        u'last_check': None,
        u'last_stdout': u'',
        u'last_stderr': u'',
        u'automatic_update': True,
        u'status': 0 #STATUS_IDLE
    }

    RASPIOT_GITHUB_OWNER = u'tangb'
    RASPIOT_GITHUB_REPO = u'raspiot'

    STATUS_IDLE = 0
    STATUS_DOWNLOADING = 1
    STATUS_DOWNLOADING_ERROR = 2
    STATUS_DOWNLOADING_ERROR_INVALIDSIZE = 3
    STATUS_DOWNLOADING_ERROR_BADCHECKSUM = 4
    STATUS_INSTALLING = 5
    STATUS_INSTALLING_ERROR = 6
    STATUS_INSTALLING_DONE = 7
    STATUS_CANCELED = 8
    STATUS_COMPLETED = 9
    STATUS_ERROR = 10

    def __init__(self, bus, debug_enabled, join_event):
        """
        Constructor

        Args:
            bus (MessageBus): MessageBus instance
            debug_enabled (bool): flag to set debug level to logger
        """
        RaspIotModule.__init__(self, bus, debug_enabled, join_event)

        #members
        self.__update = None
        self.status = {
            u'status': self.STATUS_IDLE,
            u'download_filesize': 0,
            u'download_percent': 0,
        }
        self.__update_task = None
        self.__reset_update(self.STATUS_IDLE)

    def _configure(self):
        """
        Configure module
        """
        self.__update_task = BackgroundTask(self.__update_raspiot, self.logger, pause=1.0)
        self.__update_task.start()

    def _stop(self):
        """
        Stop module
        """
        if self.__update_task:
            self.__update_task.stop()

    def __download_callback(self, status, filesize, percent):
        """
        Download callback
        """
        #update status
        self.logger.debug('Download callback: %s %s %s' % (status, filesize, percent))
        if status in (Download.STATUS_DOWNLOADING, Download.STATUS_DOWNLOADING_NOSIZE):
            self.status[u'status'] = self.STATUS_DOWNLOADING
        elif status==Download.STATUS_ERROR:
            self.status[u'status'] = self.STATUS_DOWNLOADING_ERROR
        elif status==Download.STATUS_ERROR_INVALIDSIZE:
            self.status[u'status'] = self.STATUS_DOWNLOADING_ERROR_INVALIDSIZE
        elif status==Download.STATUS_ERROR_BADCHECKSUM:
            self.status[u'status'] = self.STATUS_DOWNLOADING_ERROR_BADCHECKSUM
        self.status[u'download_filesize'] = filesize
        self.status[u'download_percent'] = percent

        #send event to update ui
        self.send_event(u'update.status.update', self.get_status(), to=u'rpc')

    def __install_callback(self, status):
        """
        Install callback
        """
        #update status
        self.logger.debug('Install callback: %s' % status)
        if status[u'status']==Install.STATUS_PROCESSING:
            self.status[u'status'] = self.STATUS_INSTALLING
        elif status[u'status']==Install.STATUS_ERROR:
            self.status[u'status'] = self.STATUS_INSTALLING_ERROR
        elif status[u'status']==Install.STATUS_DONE:
            self.status[u'status'] = self.STATUS_INSTALLING_DONE

        #update last stdout/stderr
        if status[u'status'] in (Install.STATUS_ERROR, Install.STATUS_DONE):
            config = self._get_config()
            config[u'last_stdout'] = status[u'stdout']
            config[u'last_stderr'] = status[u'stderr']
            self._save_config(config)

        #send event to update ui
        self.send_event(u'update.status.update', self.get_status(), to=u'rpc')

    def __reset_update(self, status=None):
        """
        Reset all update members

        Args:
            status (int): current status (use STATUS_XXX)
        """
        self.__update = None
        self.__checksum = None
        if status is None:
            status = self.status
        self.status = {
            u'status': status,
            u'download_filesize': 0,
            u'download_percent': 0
        }
        self.__downloader = None
        self.__installer = None
        self.__canceled = False

        #send event to update ui
        self.send_event(u'update.status.update', self.get_status(), to=u'rpc')

    def get_full_status(self):
        """
        Return full status including config
        Module does not return its config due to size of stdout/stderr

        Return:
            dict: current status::
                {
                    status (string)
                    download_filesize (int)
                    download_percent (int)
                    last_stdout (list)
                    last_stderr (list)
                    last_update (int)
                    last_check (int)
                    version (string)
                }
        """
        config = self._get_config()
        status = self.status.copy()
        status[u'version'] = VERSION
        status.update(config)

        return status

    def get_status(self):
        """
        Return light status

        Return:
            dict: current status::
                {
                    status (string)
                    download_filesize (int)
                    download_percent (int)
                }
        """
        return self.status

    def cancel(self):
        """
        Cancel current update
        """
        self.logger.debug(u'Cancel requested')
        self.__canceled = True
        if self.__update and self.__checksum:
            if self.__installer is not None:
                self.logger.debug(u'Cancel installer')
                self.__installer.cancel()
            elif self.__downloader is not None:
                self.logger.debug(u'Cancel downloader')
                self.__downloader.cancel()
            else:
                self.logger.debug(u'Nothing to cancel. Maybe too soon?')

    def set_automatic_update(self, automatic_update):
        """
        Set automatic update value

        Args:
            automatic_update (bool): new automatic update value
        """
        if not isinstance(automatic_update, bool):
            raise InvalidParameter('Automatic update value is invalid')

        config = self._get_config()
        config[u'automatic_update'] = automatic_update

        if self._save_config(config):
            return True
        return False

    def __update_raspiot(self):
        """
        Update raspiot task
        """
        try:
            if self.__update and self.__checksum:
                #new update available

                #get checksum key
                self.__downloader = Download(self.__download_callback)
                checksum_content = self.__downloader.download_file(self.__checksum[u'url'])
                self.logger.debug('Checksum file content: %s' % checksum_content)
                checksum, _ = checksum_content.split()
                self.logger.debug(u'Checksum: %s' % checksum)

                #check cancel
                if self.__canceled:
                    self.logger.debug('Installation canceled')
                    self.__reset_update(self.STATUS_CANCELED)
                    return
            
                #download update
                deb_file = self.__downloader.download_file_advanced(self.__update[u'url'], check_sha256=checksum)
                if deb_file is None:
                    if self.__canceled:
                        #download canceled
                        self.logger.info(u'Download canceled by user')
                        self.__reset_update(self.STATUS_CANCELED)
                    else:
                        #download failed, status updated in download callback so nothing else to do here
                        self.logger.error(u'Update download failed')
                        self.__reset_update()

                else:
                    #install deb file
                    self.__installer = Install(self.__install_callback, blocking=True)
                    if not self.__installer.install_deb(deb_file):
                        if self.__canceled:
                            #installation canceled
                            self.logger.info(u'Installation canceled by user')
                            self.__reset_update(self.STATUS_CANCELED)
                        else:
                            #installation failed, status updated in install callback so nothing else to do here
                            self.logger.error(u'Update installation failed')
                            self.__reset_update()

                    else:
                        #installation succeed
                        self._config[u'last_update'] = int(time.time())
                        self._save_config(self._config)
                        self.logger.info(u'Update processed succesfully')

                        #reset update process
                        self.__reset_update(self.STATUS_COMPLETED)
    
                        #send event to request restart
                        self.send_event(u'update.system.needrestart', params={u'force':True}, to=u'system')
    
        except:
            #exception occured
            self.logger.exception('Exception occured during raspiot update:')
            #prevent from infinite update attempts
            self.__reset_update(self.STATUS_ERROR)

    def check_update(self):
        """
        Check for available update

        Return:
            bool: True if update available
        """
        #update last check
        self._config[u'last_check'] = int(time.time())
        self._save_config(self._config)
    
        update_available = False
        try:
            github = Github()
            releases = github.get_releases(self.RASPIOT_GITHUB_OWNER, self.RASPIOT_GITHUB_REPO)
            if len(releases)==1:
                #get latest version available
                version = github.get_release_version(releases[0])
                if version!=VERSION:
                    #new version available, trigger update
                    assets = github.get_release_assets_infos(releases[0])

                    #search for deb file
                    for asset in assets:
                        if asset[u'name'].find(u'.deb')!=-1:
                            self.logger.info(u'Found deb asset: %s' % asset)
                            self.__update = asset
                            break

                    #search for checksum file
                    if self.__update is not None:
                        deb_name = os.path.splitext(self.__update[u'name'])[0]
                        checksum_name = u'%s.%s' % (deb_name, u'sha256')
                        self.logger.debug(u'Checksum filename to search: %s' % checksum_name)
                        for asset in assets:
                            if asset[u'name']==checksum_name:
                                self.logger.info(u'Found checksum asset: %s' % asset)
                                self.__checksum = asset
                                break

                    if self.__update and self.__checksum:
                        self.logger.debug(u'Update and checksum found, can trigger update')
                        update_available = True

            else:
                #no release found
                self.logger.warning(u'No release found during check')

        except:
            self.logger.exception(u'Error occured during updates checking:')

        return update_available

    def event_received(self, event):
        """
        Event received
        """
        if event[u'event']==u'system.time.now' and event[u'params'][u'hour']==12 and event[u'params'][u'minute']==0:
            #check updates at noon
            self.__updates = self.check_updates()

