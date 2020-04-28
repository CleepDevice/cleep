#!/usr/bin/env python
# -*- coding: utf-8 -*

import logging
import urllib3
urllib3.disable_warnings()
import uuid
import time
import os
import hashlib
import platform
import tempfile
import base64
import io
from raspiot.libs.internals.task import Task

class Download():
    """
    Download file helper
    """
    TMP_FILE_PREFIX = 'cleep_tmp'
    DOWNLOAD_FILE_PREFIX = 'cleep_download'
    CACHED_FILE_PREFIX = 'cleep_cached'

    STATUS_IDLE = 0
    STATUS_DOWNLOADING = 1
    STATUS_DOWNLOADING_NOSIZE = 2
    STATUS_ERROR = 3
    STATUS_ERROR_INVALIDSIZE = 4
    STATUS_ERROR_BADCHECKSUM = 5
    STATUS_DONE = 6
    STATUS_CANCELED = 7
    STATUS_CACHED = 8

    def __init__(self, cleep_filesystem):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance. If None does not handle R/O mode
        """
        # logger
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)

        # members
        self.cleep_filesystem = cleep_filesystem
        self.temp_dir = tempfile.gettempdir()
        self.__cancel = False
        self.__status_callback = None
        self.__end_callback = None
        self.__download_task = None
        self.download = None
        self.http = urllib3.PoolManager(num_pools=1)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:57.0) Gecko/20100101 Firefox/57.0'
        }

    def add_auth_token(self, token):
        """
        Add auth token for download authentication

        Args:
            token (string): auth token
        """
        self.headers['Authorization'] = 'Token %s' % token

    def add_auth_bearer(self, bearer):
        """
        Add auth bearer for download authentication

        Args:
            bearer (string): bearer
        """
        self.headers['Authorization'] = 'Bearer %s' % bearer

    def purge_files(self, force_all=False):
        """
        Remove all files that stay from previous processes

        Args:
            force_all (bool): force deletion of all files (cached ones too)
        """
        for _, _, dls in os.walk(self.temp_dir):
            for dl in dls:
                self.logger.trace('Purge found file "%s"' % dl)
                # delete temp files
                if os.path.basename(dl).startswith(self.DOWNLOAD_FILE_PREFIX):
                    self.logger.debug('Purge existing downloaded temp file: %s' % dl)
                    try:
                        if self.cleep_filesystem:
                            self.cleep_filesystem.rm(os.path.join(self.temp_dir, dl))
                        else:
                            os.remove(os.path.join(self.temp_dir, dl))
                    except:
                        self.logger.exception(u'Unable to purge downloaded file:')

                # delete cached files
                elif force_all and os.path.basename(dl).startswith(self.CACHED_FILE_PREFIX):
                    self.logger.debug('Purge existing downloaded cached file: %s' % dl)
                    try:
                        if self.cleep_filesystem:
                            self.cleep_filesystem.rm(os.path.join(self.temp_dir, dl))
                        else:
                            os.remove(os.path.join(self.temp_dir, dl))
                    except:
                        self.logger.exception(u'Unable to cached downloaded file:')

    def get_cached_files(self):
        """
        Return list of cached files

        Returns:
            list: list of cached files::

                [
                    {
                        filename (string): real filename,
                        filepath (string): full file path,
                        filesize (long): file size
                    }
                    ...
                ]

        """
        cached = []

        self.logger.trace('Get cached files from "%s"' % self.temp_dir)
        for _, _, dls in os.walk(self.temp_dir):
            for dl in dls:
                if os.path.basename(dl).startswith(self.CACHED_FILE_PREFIX):
                    filepath = os.path.join(self.temp_dir, dl)
                    filename = os.path.basename(dl).replace(self.CACHED_FILE_PREFIX, '')
                    filename = base64.b64decode(filename).decode('utf-8')
                    cached.append({
                        'filename': filename,
                        'filepath': filepath,
                        'filesize': os.path.getsize(filepath)
                    })

        return cached

    def is_file_cached(self, filename):
        """
        Return infos if file is already downloaded and hence cached

        Args:
            filename (string): filename to search

        Returns:
            dict: cached file infos or None if file not cached::

                {
                    filename (string): real filename,
                    filepath (string): full file path,
                    filesize (long): file size
                }

        """
        for cached_file in self.get_cached_files():
            if cached_file['filename'] == filename:
                return cached_file

        return None

    def generate_sha1(self, file_path):
        """
        Generate SHA1 checksum for specified file

        Args:
            file_path (string): file path
        """
        sha1 = hashlib.sha1()
        if self.cleep_filesystem:
            fd = self.cleep_filesystem.open(file_path, u'rb')
        else:
            fd = io.open(file_path, u'rb')
        while True:
            buf = fd.read(1024)
            if not buf:
                break
            sha1.update(buf)
        if self.cleep_filesystem:
            self.cleep_filesystem.close(fd)
        else:
            fd.close() # pragma: no cover

        return sha1.hexdigest()

    def generate_sha256(self, file_path):
        """
        Generate SHA256 checksum for specified file

        Args:
            file_path (string): file path
        """
        sha256 = hashlib.sha256()
        if self.cleep_filesystem:
            fd = self.cleep_filesystem.open(file_path, u'rb')
        else:
            fd = io.open(file_path, u'rb')
        while True:
            buf = fd.read(1024)
            if not buf:
                break
            sha256.update(buf)
        if self.cleep_filesystem:
            self.cleep_filesystem.close(fd)
        else:
            fd.close() # pragma: no cover

        return sha256.hexdigest()

    def generate_md5(self, file_path):
        """
        Generate MD5 checksum for specified file

        Args:
            file_path (string): file path
        """
        md5 = hashlib.md5()
        if self.cleep_filesystem:
            fd = self.cleep_filesystem.open(file_path, u'rb')
        else:
            fd = io.open(file_path, u'rb')
        while True:
            buf = fd.read(1024)
            if not buf:
                break
            md5.update(buf)
        if self.cleep_filesystem:
            self.cleep_filesystem.close(fd)
        else:
            fd.close() # pragma: no cover

        return md5.hexdigest()

    def download_content(self, url):
        """
        Download file content from specified url.
        This function is blocking.
        Prefer using this function to download small files.

        Args:
            url (string): url of file to download
        
        Returns:
            tuple: download status and downloaded content::
            
                (
                    status (int): see STATUS_XXX for possible values,
                    content (string): downloaded content
                )

        """
        self.__cancel = False
        try:
            self.logger.trace(u'Headers=%s' % self.headers)
            resp = self.http.request(u'GET', url, preload_content=False, headers=self.headers)
            if resp.status != 200:
                self.logger.error(u'Download "%s" failed' % url)
                return self.STATUS_ERROR, None

        except:
            self.logger.exception(u'Error initializing http request:')
            return self.STATUS_ERROR, None

        # process download
        content = u''
        try:
            while True:
                # read data
                buf = resp.read(1024)
                if not buf:
                    # download ended or failed, stop statement
                    break

                # save data 
                content += buf.decode('utf-8')

        except:
            self.logger.exception(u'Error downloading file "%s"' % url)
            return self.STATUS_ERROR, None

        return self.STATUS_DONE, content

    def __send_download_status(self, status, size, percent):
        """
        Call download status callback if configured

        Args:
            status (int): current download status
            size (int): downloaded filesize (bytes)
            percent (int): percentage of download
        """
        if self.__status_callback:
            self.__status_callback(status, size, percent)

    def __send_download_end(self, status, filepath):
        """
        Call download end callback if configured

        Args:
            status (int): final download status
            filepath (string): downloaded local filepath or None if download failed
        """
        if self.__end_callback:
            self.__end_callback(status, filepath)

        return status, filepath

    def cancel(self):
        """
        Cancel current download (only possible for download_file_async)
        """
        self.logger.debug('Cancel file downloading')
        self.__cancel = True
        if self.__download_task:
            self.__download_task.stop()

    def download_file_async(self, url, end_callback, status_callback=None, check_sha1=None, check_sha256=None, check_md5=None, cache_filename=None):
        """
        Same as download_file function but embedded in Task instance to run it in background
        Call cancel instance function to stop current download

        Args:
            url (string): url to download
            end_callback (function): function called when download is terminated (params: status (int), filepath (string))
            status_callback (function): status callback. (params: status (int), filesize (long), percent (int))
            check_sha1 (string): sha1 key to check
            check_sha256 (string): sha256 key to check
            check_md5 (string): md5 key to check
            cache_filename (string): specify output filename and enable caching (the file will not be purged automatically)
        """
        self.__cancel = False
        self.__status_callback = status_callback

        self.__download_task = Task(None, self.download_file, self.logger, task_kwargs={
            'url': url,
            'end_callback': end_callback,
            'check_sha1': check_sha1,
            'check_sha256': check_sha256,
            'check_md5': check_md5,
            'cache_filename': cache_filename,
        })
        self.__download_task.start()

    def download_file(self, url, end_callback=None, check_sha1=None, check_sha256=None, check_md5=None, cache_filename=None):
        """
        Download specified file url and check its integrity if specified.
        This function is blocking. Run download_file_async if you need to download a file asynchronously

        Args:
            url (string): url to download
            end_callback (function): function called when download is terminated (params: status (int), downloaded filepath (string))
            check_sha1 (string): sha1 key to check
            check_sha256 (string): sha256 key to check
            check_md5 (string): md5 key to check
            cache_filename (string): specify output filename and enable caching (the file will not be purged automatically)
        
        Returns:
            tuple: download status and downloaded filepath (or None if error occured) ::

                (
                    status (int): download status (see STATUS_XXX),
                    filepath (string): downloaded filepath
                )

        """
        self.__end_callback = end_callback

        # prepare filename
        download_uuid = str(uuid.uuid4())
        self.download = os.path.join(self.temp_dir, u'%s_%s' % (self.TMP_FILE_PREFIX, download_uuid))
        self.logger.debug(u'File will be saved to "%s"' % self.download)
        download = None

        # check if file is cached
        if cache_filename:
            cached_file = self.is_file_cached(cache_filename)
            if cached_file:
                self.__send_download_status(self.STATUS_CACHED, os.path.getsize(cached_file['filepath']), 100)
                return self.__send_download_end(self.STATUS_DONE, cached_file['filepath'])
        
        # prepare download
        try:
            if self.cleep_filesystem:
                download = self.cleep_filesystem.open(self.download, u'wb')
            else:
                download = io.open(self.download, u'wb')
        except:
            self.logger.exception(u'Unable to create file:')
            return self.__send_download_end(self.STATUS_ERROR, None)

        # initialize download
        try:
            resp = self.http.request(u'GET', url, preload_content=False, headers=self.headers)
            if resp.status != 200:
                self.logger.error(u'Download "%s" failed' % url)
                return self.__send_download_end(self.STATUS_ERROR, None)

        except:
            self.logger.exception(u'Error initializing http request:')
            return self.__send_download_end(self.STATUS_ERROR, None)

        # get file size
        file_size = 0
        downloading_status = self.STATUS_DOWNLOADING
        try:
            content_length = resp.getheader('Content-Length')
            file_size = int(content_length)
            downloading_status = self.STATUS_DOWNLOADING
        except Exception as e:
            self.logger.warning(u'Unable to get content-length value from header. Disable filesize check: %s' % str(e))
            downloading_status = self.STATUS_DOWNLOADING_NOSIZE
        self.__send_download_status(downloading_status, 0, 0)
        self.logger.trace(u'Size to download: %d bytes' % file_size)

        # download file
        downloaded_size = 0
        percent = 0
        last_percent = -1
        while True:
            # cancel download
            if self.__cancel:
                if self.cleep_filesystem:
                    self.cleep_filesystem.close(download)
                else:
                    download.close() # pragma: no cover
                self.logger.debug(u'Download canceled')
                return self.__send_download_end(self.STATUS_CANCELED, None)

            # read data
            buf = resp.read(1024)
            if not buf:
                # download ended or failed, stop statement
                self.logger.trace('Download terminated')
                break

            # save data to output file
            downloaded_size += len(buf)
            try:
                download.write(buf)
            except:
                self.logger.exception(u'Unable to write to download file "%s":' % self.download)
                if self.cleep_filesystem:
                    self.cleep_filesystem.close(download)
                else:
                    download.close() # pragma: no cover
                return self.__send_download_end(self.STATUS_ERROR, None)
            
            # compute percentage
            if file_size != 0:
                percent = int(float(downloaded_size) / float(file_size) * 100.0)
                self.__send_download_status(downloading_status, downloaded_size, percent)
                if not percent%5 and last_percent != percent:
                    last_percent = percent
                    self.logger.trace(u'Downloading %s %d%%' % (self.download, percent))

        # download terminated
        if self.cleep_filesystem:
            self.cleep_filesystem.close(download)
        else:
            download.close() # pragma: no cover

        # file size
        if file_size>0:
            if downloaded_size == file_size:
                self.logger.debug(u'File size is valid')
            else:
                self.logger.error(u'Invalid downloaded size %d instead of %d' % (downloaded_size, file_size))
                return self.__send_download_end(self.STATUS_ERROR_INVALIDSIZE, None)

        # checksum
        checksum_computed = None
        checksum_provided = None
        if check_sha1:
            checksum_computed = self.generate_sha1(self.download)
            checksum_provided = check_sha1
            self.logger.trace(u'SHA1 for %s: %s' % (self.download, checksum_computed))
        elif check_sha256:
            checksum_computed = self.generate_sha256(self.download)
            checksum_provided = check_sha256
            self.logger.trace(u'SHA256 for %s: %s' % (self.download, checksum_computed))
        elif check_md5:
            checksum_computed = self.generate_md5(self.download)
            checksum_provided = check_md5
            self.logger.trace(u'MD5 for %s: %s' % (self.download, checksum_computed))
        if checksum_provided is not None:
            if checksum_computed.lower() == checksum_provided.lower():
                self.logger.debug(u'Checksum is valid')
            else:
                self.logger.error(u'Checksum from downloaded file is invalid (computed=%s provided=%s)' % (checksum_computed, checksum_provided))
                return self.__send_download_end(self.STATUS_ERROR_BADCHECKSUM, None)
        else:
            self.logger.debug(u'No checksum to verify :(')

        # send last status callback
        self.__send_download_status(downloading_status, file_size, 100)

        # rename file
        if not cache_filename:
            download = os.path.join(self.temp_dir, u'%s_%s' % (self.DOWNLOAD_FILE_PREFIX, download_uuid))
        else:
            hashname = base64.urlsafe_b64encode(cache_filename.encode(u'utf-8')).decode(u'utf-8')
            download = os.path.join(self.temp_dir, u'%s_%s' % (self.CACHED_FILE_PREFIX, hashname))
        try:
            self.logger.trace('Rename downloaded file "%s" to "%s"' % (self.download, download))
            if self.cleep_filesystem:
                self.cleep_filesystem.rename(self.download, download)
            else:
                os.rename(self.download, download)
            self.download = download
        except:
            self.logger.exception(u'Unable to rename downloaded file:')
            return self.__send_download_end(self.STATUS_ERROR, None)

        return self.__send_download_end(self.STATUS_DONE, self.download)

