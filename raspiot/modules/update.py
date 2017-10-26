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

__all__ = [u'Update']


class Update(RaspIotModule):

    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Keep your device up-to-date with automatic updates'
    MODULE_LOCKED = False
    MODULE_URL = None
    MODULE_TAGS = [u'update', u'raspiot']
    MODULE_COUNTRY = u'any'

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
        self.last_check = None
        self.__reset_update()
        self.status = {
            u'status': self.STATUS_IDLE,
            u'download_filesize': 0,
            u'download_percent': 0
        }

    def __download_callback(self, status, filesize, percent):
        """
        Download callback
        """
        #update status
        if status in (Download.STATUS_DOWNLOADING, Download.STATUS_DOWNLOADING_NOSIZE):
            self.status[u'status'] = self.STATUS_DOWNLOADING
        elif status==Downwload.STATUS_ERROR:
            self.status[u'status'] = self.STATUS_DOWNLOADING_ERROR
        elif status==Downwload.STATUS_ERROR_INVALIDSIZE:
            self.status[u'status'] = self.STATUS_DOWNLOADING_ERROR_INVALIDSIZE
        elif status==Downwload.STATUS_ERROR_BADCHECKSUM:
            self.status[u'status'] = self.STATUS_DOWNLOADING_ERROR_BADCHECKSUM
        self.status[u'download_filesize'] = filesize
        self.status[u'download_percent'] = percent

        #send event to update ui
        self.send_event('update.status.update', self.download_status)

    def __install_callback(self, status):
        """
        Install callback
        """
        #update status
        if status==Install.STATUS_PROCESSING:
            self.status[u'status'] = self.INSTALLING
        elif status==Install.STATUS_ERROR:
            self.status[u'status'] = self.INSTALLING_ERROR
        elif status==Install.STATUS_DONE:
            self.status[u'status'] = self.INSTALLING_DONE

    def __reset_update(self):
        """
        Reset all update members
        """
        self.__update = None
        self.__checksum = None
        self.status = {
            u'status': Download.STATUS_IDLE,
            u'download_filesize': 0,
            u'download_percent': 0
        }
        self.__downloader = None
        self.__installer = None

    def get_status(self):
        """
        Return current status

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
        if self.__update and self.__checksum:
            self.status[u'status'] = self.STATUS_CANCELED
            if self.__installer is not None:
                self.logger.debug(u'Cancel installer')
                self.__installer.cancel()
            elif self.__downloader is not None:
                self.logger.debug(u'Cancel downloader')
                self.__downloader.cancel()
            else:
                self.logger.debug(u'Nothing to cancel. Maybe too soon?')

    def _custom_process(self):
        """
        Custom process
        """
        if self.__update and self.__checksum:
            #new update available

            #get checksum key
            self.__downloader = Download(self.__download_callback)
            checksum = self.__downloader.download(self.__checksum[u'url'])
            self.logger.debug('Checksum: %s' % checksum)
            
            #download update
            deb_file = self.__downloader.download_advanced(self.__update[u'url'], check_sha256=checksum)
            if deb_file is None:
                #download failed, status updated in download callback so nothing else to do here
                self.logger.error(u'Update download failed or canceled')

            else:
                #install deb file
                self.__installer = Install(self.__install_callback, blocking=True)
                if not self.__installer.install_deb(deb_file):
                    #installation failed, status updated in install callback so nothing else to do here
                    self.logger.error(u'Update installation failed or canceled')

                else:
                    #installation succeed
                    self.logger.info(u'Update processed succesfully')

                    #send event to request reboot
                    self.send_event(u'update.system.needreboot', params={u'force':True}, to=u'system')

            #reset update process
            self.__reset_update()

    def check_update(self):
        """
        Check for available update

        Return:
            dict: update informations
        """
        self.last_check = int(time.time())
    
        try:
            github = Github()
            releases = github.get_releases(self.RASPIOT_GITHUB_OWNER, self.RASPIOT_GITHUB_REPO)
            if len(releases)==1:
                #get latest version available
                version = github.get_release_version(release[0])
                if version!=VERSION:
                    #new version available, trigger update
                    assets = github.get_release_assets_infos(release)

                    #search for deb file
                    for asset in assets:
                        if asset[u'name'].find('.deb')!=-1:
                            self.logger.info('Found deb asset: %s' % asset)
                            self.__update = asset
                            break

                    #search for checksum file
                    if self.__update is not None:
                        name_to_search = '%s.%s' % (self.__update[u'name'].splitext()[0], u'sha256')
                        for asset in assets:
                            if asset[u'name']==name_to_search:
                                self.logger.info('Found checksum asset: %s' % asset)
                                self.__checksum = asset
                                break

            else:
                #no release found
                self.logger.warning(u'No release found during check')

        except:
            self.logger.exception(u'Error occured during updates checking:')

    def event_received(self, event):
        """
        Event received
        """
        if event[u'event']==u'system.time.now' and event[u'params'][u'hour']==12 and event[u'params'][u'minute']==0:
            #check updates at noon
            self.__updates = self.check_updates()

