#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
sys.path.append('/root/cleep/raspiot/libs/internals')
import download
from download import Download
from raspiot.libs.tests.lib import TestLib, Urllib3RequestResponseMock, FileDescriptorMock
import unittest
import logging
from mock import Mock, MagicMock
import shutil
import io
import base64


def create_files_tree(DOWNLOAD_FILE_PREFIX, CACHED_FILE_PREFIX, with_files=True):
    os.mkdir('test')
    filename = base64.urlsafe_b64encode('123456789'.encode('utf-8')).decode('utf-8')
    if with_files:
        downloaded_file = 'test/%s_%s' % (DOWNLOAD_FILE_PREFIX, filename)
        os.system('echo "download" > "%s"' % downloaded_file)
        purged_file = 'test/%s_%s' % (CACHED_FILE_PREFIX, filename)
        os.system('echo "download" > "%s"' % purged_file)

class DownloadTests(unittest.TestCase):

    RESPONSE = 'hello world'
    DUMMY_FILE = 'http://www.ovh.net/files/1Mio.dat'

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.fs = Mock()

        self.urllib3_original = download.urllib3
        (download.urllib3, self.request) = TestLib.mock_urllib3(Urllib3RequestResponseMock(raw=self.RESPONSE, getheader_side_effect=lambda: len(self.RESPONSE)))

        self.async_status = None
        self.async_filepath = None
        self.async_filesize = None
        self.async_percent = None
        self.end_callback_call = 0
        self.status_callback_call = 0

        self.d = Download(self.fs)
        self.d.temp_dir = os.path.abspath('./test')

    def tearDown(self):
        download.urllib3 = self.urllib3_original

    def test_add_auth_token(self):
        self.assertFalse('Authorization' in self.d.headers)
        self.d.add_auth_token('123456789')
        self.assertTrue('Authorization' in self.d.headers)
        self.assertEqual(self.d.headers['Authorization'], 'Token 123456789')

    def test_add_auth_bearer(self):
        self.assertFalse('Authorization' in self.d.headers)
        self.d.add_auth_bearer('987654321')
        self.assertTrue('Authorization' in self.d.headers)
        self.assertEqual(self.d.headers['Authorization'], 'Bearer 987654321')

    def test_purge_files(self):
        try:
            create_files_tree(self.d.DOWNLOAD_FILE_PREFIX, self.d.CACHED_FILE_PREFIX)
            self.d.purge_files()
            self.assertEqual(self.fs.rm.call_count, 1)
        finally:
            if os.path.exists('test'):
               shutil.rmtree('test')

    def test_purge_files_all_files(self):
        try:
            create_files_tree(self.d.DOWNLOAD_FILE_PREFIX, self.d.CACHED_FILE_PREFIX)
            self.d.purge_files(True)
            self.assertEqual(self.fs.rm.call_count, 2)
        finally:
            if os.path.exists('test'):
               shutil.rmtree('test')

    def test_hashes(self):
        try:
            FILENAME = 'test.txt'
            with io.open(FILENAME, 'w') as fd:
                fd.write(u'test file')

            md5sum = 'f20d9f2072bbeb6691c0f9c5099b01f3'
            sha1sum = '8f93542443e98f41fe98e97d6d2a147193b1b005'
            sha256sum = '9a30a503b2862c51c3c5acd7fbce2f1f784cf4658ccf8e87d5023a90c21c0714'

            self.assertEqual(self.d.generate_md5(FILENAME), md5sum)
            self.assertEqual(self.d.generate_sha1(FILENAME), sha1sum)
            self.assertEqual(self.d.generate_sha256(FILENAME), sha256sum)
        finally:
            if os.path.exists(FILENAME):
                os.remove(FILENAME)

    def test_get_cached_files(self):
        try:
            create_files_tree(self.d.DOWNLOAD_FILE_PREFIX, self.d.CACHED_FILE_PREFIX)
            cached = self.d.get_cached_files()
            logging.debug('Cached: %s' % cached)
            self.assertTrue(isinstance(cached, list))
            self.assertEqual(len(cached), 1)
            self.assertTrue('filename' in cached[0])
            self.assertTrue('filepath' in cached[0])
            self.assertTrue('filesize' in cached[0])
            # self.assertEqual(self.fs.rm.call_count, 2)
        finally:
            if os.path.exists('test'):
               shutil.rmtree('test')

    def test_is_file_cached(self):
        try:
            create_files_tree(self.d.DOWNLOAD_FILE_PREFIX, self.d.CACHED_FILE_PREFIX)
            cached = self.d.is_file_cached('123456789')
            self.assertIsNotNone(cached)
            self.assertTrue('filename' in cached)
            self.assertTrue('filepath' in cached)
            self.assertTrue('filesize' in cached)
        finally:
            if os.path.exists('test'):
               shutil.rmtree('test')

    def test_hashes(self):
        try:
            FILENAME = 'test.txt'
            with io.open(FILENAME, 'w') as fd:
                fd.write(u'test file')
            fd = io.open(FILENAME, 'rb')
            self.fs.open = Mock(return_value=fd)

            md5sum = 'f20d9f2072bbeb6691c0f9c5099b01f3'
            sha1sum = '8f93542443e98f41fe98e97d6d2a147193b1b005'
            sha256sum = '9a30a503b2862c51c3c5acd7fbce2f1f784cf4658ccf8e87d5023a90c21c0714'

            self.assertEqual(self.d.generate_md5(FILENAME), md5sum)
            fd.seek(0)
            self.assertEqual(self.d.generate_sha1(FILENAME), sha1sum)
            fd.seek(0)
            self.assertEqual(self.d.generate_sha256(FILENAME), sha256sum)
        finally:
            if fd:
                fd.close()
            if os.path.exists(FILENAME):
                os.remove(FILENAME)

    def test_download_content(self):
        status, content = self.d.download_content('http://www.google.com')
        self.assertTrue(self.request.called)
        self.assertEqual(content, self.RESPONSE)
        self.assertEqual(status, self.d.STATUS_DONE)

    def _end_callback(self, status, filepath):
        logging.debug('End callback: status=%s filepath=%s' % (status, filepath))
        self.async_status = status
        self.async_filepath = filepath
        self.end_callback_call += 1

    def _status_callback(self, status, filesize, percent):
        logging.debug('Status callback: status=%s filesize=%s percent=%s' % (status, filesize, percent))
        self.async_status = status
        self.async_filesize = filesize
        self.async_percent = percent
        self.status_callback_call += 1
    
    def test_download_file_async(self):
        self.d.download_file_async(self.DUMMY_FILE, self._end_callback, status_callback=self._status_callback)
        time.sleep(1)
        self.assertGreaterEqual(self.status_callback_call, 2)
        self.assertEqual(self.end_callback_call, 1)
        self.assertEqual(self.async_status, self.d.STATUS_DONE)
        self.assertEqual(self.async_percent, 100)
        self.assertEqual(self.async_filesize, len(self.RESPONSE))
        self.assertEqual(self.async_filepath.find(self.d.CACHED_FILE_PREFIX), -1) # file shouldn't be cached by default

    def test_download_file_async_with_cached_filename(self):
        self.d.download_file_async(self.DUMMY_FILE, self._end_callback, status_callback=self._status_callback, cache_filename='mycachedfile')
        time.sleep(1)
        self.assertEqual(self.async_status, self.d.STATUS_DONE)
        self.assertNotEqual(self.async_filepath.find(self.d.CACHED_FILE_PREFIX), -1)

    def test_download_file_async_with_cached_file(self):
        try:
            create_files_tree(self.d.DOWNLOAD_FILE_PREFIX, self.d.CACHED_FILE_PREFIX)
            self.d.download_file_async(self.DUMMY_FILE, self._end_callback, status_callback=self._status_callback, cache_filename='123456789')
            time.sleep(.25)
            self.assertEqual(self.status_callback_call, 1)
            self.assertEqual(self.end_callback_call, 1)
            self.assertEqual(self.async_status, self.d.STATUS_DONE)
            self.assertEqual(self.async_percent, 100)
        finally:
            if os.path.exists('test'):
               shutil.rmtree('test')

    def test_download_file_async_check_sha1(self):
        self.d.generate_sha1 = Mock(return_value='1234')
        self.d.generate_sha256 = Mock()
        self.d.generate_md5 = Mock()
        self.d.download_file_async(self.DUMMY_FILE, self._end_callback, check_sha1='1234', status_callback=self._status_callback)
        time.sleep(1)
        self.assertEqual(self.async_status, self.d.STATUS_DONE)
        self.assertTrue(self.d.generate_sha1.called)
        self.assertFalse(self.d.generate_sha256.called)
        self.assertFalse(self.d.generate_md5.called)

    def test_download_file_async_check_sha256(self):
        self.d.generate_sha1 = Mock()
        self.d.generate_sha256 = Mock(return_value='1234')
        self.d.generate_md5 = Mock()
        self.d.download_file_async(self.DUMMY_FILE, self._end_callback, check_sha256='1234', status_callback=self._status_callback)
        time.sleep(1)
        self.assertEqual(self.async_status, self.d.STATUS_DONE)
        self.assertFalse(self.d.generate_sha1.called)
        self.assertTrue(self.d.generate_sha256.called)
        self.assertFalse(self.d.generate_md5.called)

    def test_download_file_async_check_md5(self):
        self.d.generate_sha1 = Mock()
        self.d.generate_sha256 = Mock()
        self.d.generate_md5 = Mock(return_value='1234')
        self.d.download_file_async(self.DUMMY_FILE, self._end_callback, check_md5='1234', status_callback=self._status_callback)
        time.sleep(1)
        self.assertEqual(self.async_status, self.d.STATUS_DONE)
        self.assertFalse(self.d.generate_sha1.called)
        self.assertFalse(self.d.generate_sha256.called)
        self.assertTrue(self.d.generate_md5.called)

    def test_download_file_async_checksum_failed(self):
        self.d.generate_md5 = Mock(return_value='12341234')
        self.d.download_file_async(self.DUMMY_FILE, self._end_callback, check_md5='1234', status_callback=self._status_callback)
        time.sleep(1)
        self.assertEqual(self.async_status, self.d.STATUS_ERROR_BADCHECKSUM)
        self.assertTrue(self.d.generate_md5.called)


class DownloadTestsNoCleepFilesystem(unittest.TestCase):

    DUMMY_FILE = 'http://www.ovh.net/files/1Mio.dat'
    RESPONSE = 'hello world'

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.os_remove_original = os.remove
        self.os_rename_original = os.rename
        self.io_open_original = io.open

        self.urllib3_original = download.urllib3
        (download.urllib3, self.request) = TestLib.mock_urllib3(Urllib3RequestResponseMock(raw=self.RESPONSE, getheader_side_effect=lambda: len(self.RESPONSE)))

        self.async_status = None
        self.async_filepath = None
        self.async_filesize = None
        self.async_percent = None
        self.end_callback_call = 0
        self.status_callback_call = 0

    def tearDown(self):
        os.remove = self.os_remove_original
        os.rename = self.os_rename_original
        io.open = self.io_open_original
        if os.path.exists('test'):
            shutil.rmtree('test')

    def _init_download(self, remove_side_effect=None, rename_side_effect=None, open_side_effect=None):
        os.remove = Mock(side_effect=remove_side_effect)
        os.rename = Mock(side_effect=rename_side_effect)
        self.fd_mock = FileDescriptorMock()
        io.open = Mock(return_value=self.fd_mock, side_effect=open_side_effect)
        self.d = Download(None)
        self.d.temp_dir = os.path.abspath('./test')

    def test_purge_files(self):
        self._init_download()
        create_files_tree(self.d.DOWNLOAD_FILE_PREFIX, self.d.CACHED_FILE_PREFIX)
        self.d.purge_files()
        self.assertEqual(os.remove.call_count, 1)

    def test_purge_files_exception(self):
        self._init_download(remove_side_effect=Exception('test exception'))
        create_files_tree(self.d.DOWNLOAD_FILE_PREFIX, self.d.CACHED_FILE_PREFIX)
        self.d.purge_files()

    def test_purge_files_all_files(self):
        self._init_download()
        create_files_tree(self.d.DOWNLOAD_FILE_PREFIX, self.d.CACHED_FILE_PREFIX)
        self.d.purge_files(True)
        self.assertEqual(os.remove.call_count, 2)

    def test_purge_files_all_files_exception(self):
        self._init_download(remove_side_effect=Exception('test exception'))
        create_files_tree(self.d.DOWNLOAD_FILE_PREFIX, self.d.CACHED_FILE_PREFIX)
        self.d.purge_files(True)

    def _end_callback(self, status, filepath):
        logging.debug('End callback: status=%s filepath=%s' % (status, filepath))
        self.async_status = status
        self.async_filepath = filepath
        self.end_callback_call += 1

    def _status_callback(self, status, filesize, percent):
        logging.debug('Status callback: status=%s filesize=%s percent=%s' % (status, filesize, percent))
        self.async_status = status
        self.async_filesize = filesize
        self.async_percent = percent
        self.status_callback_call += 1

    def test_download_file_async_rename_exception(self):
        self._init_download(rename_side_effect=Exception('test exception'))
        create_files_tree(self.d.DOWNLOAD_FILE_PREFIX, self.d.CACHED_FILE_PREFIX, with_files=False)
        self.d.download_file_async('http://www.google.com', self._end_callback, status_callback=self._status_callback)
        time.sleep(1)
        self.assertEqual(self.async_status, self.d.STATUS_ERROR)

    def test_hashes(self):
        self._init_download()

        hashes = self.fd_mock.get_content_hashes()

        self.assertEqual(self.d.generate_md5('dummy'), hashes['md5'])
        self.assertEqual(self.d.generate_sha1('dummy'), hashes['sha1'])
        self.assertEqual(self.d.generate_sha256('dummy'), hashes['sha256'])



class DownloadTestsFileDownloadRequestFailed(unittest.TestCase):

    RESPONSE = 'hello world'

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.fs = TestLib.mock_cleepfilesystem()

        self.urllib3_original = download.urllib3
        self.end_callback_call = 0
        self.status_callback_call = 0
        self.async_status = None
        self.async_filesize = None
        self.async_filepath = None
        self.async_percent = None

    def tearDown(self):
        download.urllib3 = self.urllib3_original
        if os.path.exists('test'):
            shutil.rmtree('test')

    def _mock_urllib3(self, status, request_side_effect=None, read_side_effect=None, getheader_side_effect=None):
        (download.urllib3, self.request) = TestLib.mock_urllib3(
            Urllib3RequestResponseMock(status=status, raw=self.RESPONSE, read_side_effect=read_side_effect, getheader_side_effect=getheader_side_effect),
            request_side_effect=request_side_effect,
        )
        self.d = Download(self.fs)
        self.d.temp_dir = os.path.abspath('./test')

    def test_download_file_request_failed(self):
        self._mock_urllib3(404)
        status, content = self.d.download_content('http://www.google.com')
        self.assertTrue(self.request.called)
        self.assertIsNone(content)
        self.assertEqual(status, self.d.STATUS_ERROR)

    def test_download_file_request_exception(self):
        self._mock_urllib3(200, request_side_effect=Exception('test exception'))
        status, content = self.d.download_content('http://www.google.com')
        self.assertTrue(self.request.called)
        self.assertIsNone(content)
        self.assertEqual(status, self.d.STATUS_ERROR)

    def test_download_file_request_read_exception(self):
        self._mock_urllib3(200, read_side_effect=Exception('test exception'))
        status, content = self.d.download_content('http://www.google.com')
        self.assertIsNone(content)
        self.assertEqual(status, self.d.STATUS_ERROR)

    def _end_callback(self, status, filepath):
        logging.debug('End callback: status=%s filepath=%s' % (status, filepath))
        self.async_status = status
        self.async_filepath = filepath
        self.end_callback_call += 1

    def _status_callback(self, status, filesize, percent):
        logging.debug('Status callback: status=%s filesize=%s percent=%s' % (status, filesize, percent))
        self.async_status = status
        self.async_filesize = filesize
        self.async_percent = percent
        self.status_callback_call += 1  

    def test_download_file_async_request_failed(self):
        self._mock_urllib3(404)
        self.d.download_file_async('http://www.google.com', self._end_callback, status_callback=self._status_callback)
        time.sleep(1)
        self.assertEqual(self.async_status, self.d.STATUS_ERROR)
        self.assertIsNone(self.async_filepath)
        self.assertEqual(self.status_callback_call, 0)
        self.assertEqual(self.end_callback_call, 1)

    def test_download_file_async_request_exception(self):
        self._mock_urllib3(200, request_side_effect=Exception('test exception'))
        self.d.download_file_async('http://www.google.com', self._end_callback, status_callback=self._status_callback)
        time.sleep(1)
        self.assertEqual(self.async_status, self.d.STATUS_ERROR)
        self.assertIsNone(self.async_filepath)
        self.assertEqual(self.status_callback_call, 0)
        self.assertEqual(self.end_callback_call, 1)

    def test_download_file_async_getheader_exception(self):
        self._mock_urllib3(200, getheader_side_effect=Exception('test exception'))
        self.d.download_file_async('http://www.google.com', self._end_callback, status_callback=self._status_callback)
        time.sleep(1)
        self.assertEqual(self.async_status, self.d.STATUS_DONE)
        self.assertIsNotNone(self.async_filepath)
        self.assertGreaterEqual(self.status_callback_call, 1)
        self.assertEqual(self.end_callback_call, 1)

    def test_download_file_async_invalid_filesize(self):
        self._mock_urllib3(200, getheader_side_effect=lambda: 666)
        self.d.download_file_async('http://www.google.com', self._end_callback, status_callback=self._status_callback)
        time.sleep(1)
        self.assertEqual(self.async_status, self.d.STATUS_ERROR_INVALIDSIZE)
        self.assertIsNone(self.async_filepath)
        self.assertGreaterEqual(self.status_callback_call, 1)
        self.assertEqual(self.end_callback_call, 1)



class DownloadTestsFileDownloadFsFailed(unittest.TestCase):

    RESPONSE = 'hello world'

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.urllib3_original = download.urllib3

        self.end_callback_call = 0
        self.status_callback_call = 0
        self.async_status = None
        self.async_filesize = None
        self.async_filepath = None
        self.async_percent = None

    def tearDown(self):
        download.urllib3 = self.urllib3_original
        if os.path.exists('test'):
            shutil.rmtree('test')

    def _init_fs(self, open_side_effect=None, write_side_effect=None, rename_side_effect=None):
        open_response = None
        if write_side_effect or rename_side_effect:
            open_response = FileDescriptorMock(write_side_effect=write_side_effect)
        self.fs = TestLib.mock_cleepfilesystem(open_response=open_response, open_side_effect=open_side_effect, rename_side_effect=rename_side_effect)

        (download.urllib3, self.request) = TestLib.mock_urllib3(Urllib3RequestResponseMock(status=200, raw=self.RESPONSE))
        self.d = Download(self.fs)
        self.d.temp_dir = os.path.abspath('./test')

    def _end_callback(self, status, filepath):
        logging.debug('End callback: status=%s filepath=%s' % (status, filepath))
        self.async_status = status
        self.async_filepath = filepath
        self.end_callback_call += 1

    def _status_callback(self, status, filesize, percent):
        logging.debug('Status callback: status=%s filesize=%s percent=%s' % (status, filesize, percent))
        self.async_status = status
        self.async_filesize = filesize
        self.async_percent = percent
        self.status_callback_call += 1  

    def test_download_file_async_fs_open_exception(self):
        self._init_fs(open_side_effect=Exception('test exception'))
        self.d.download_file_async('http://www.google.com', self._end_callback, status_callback=self._status_callback)
        time.sleep(1)
        self.assertEqual(self.async_status, self.d.STATUS_ERROR)
        self.assertIsNone(self.async_filepath)
        self.assertEqual(self.status_callback_call, 0)
        self.assertEqual(self.end_callback_call, 1)

    def test_download_file_async_fs_write_exception(self):
        self._init_fs(write_side_effect=Exception('test exception'))
        self.d.download_file_async('http://www.google.com', self._end_callback, status_callback=self._status_callback)
        time.sleep(1)
        self.assertEqual(self.async_status, self.d.STATUS_ERROR)
        self.assertIsNone(self.async_filepath)
        self.assertGreaterEqual(self.status_callback_call, 1)
        self.assertEqual(self.end_callback_call, 1)

    def test_download_file_async_fs_rename_exception(self):
        self._init_fs(rename_side_effect=Exception('test exception'))
        self.d.download_file_async('http://www.google.com', self._end_callback, status_callback=self._status_callback)
        time.sleep(1)
        self.assertEqual(self.async_status, self.d.STATUS_ERROR)
        self.assertIsNone(self.async_filepath)
        self.assertGreaterEqual(self.status_callback_call, 1)
        self.assertEqual(self.end_callback_call, 1)



class DownloadTestsFileDownloadCancel(unittest.TestCase):

    DUMMY_FILE = 'http://www.ovh.net/files/1Mio.dat'
    RESPONSE = 'hello world hello world hello world'

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.fs = Mock()
        self.async_status = None
        self.async_filepath = None

        self.urllib3_original = download.urllib3
        (download.urllib3, self.request) = TestLib.mock_urllib3(
            Urllib3RequestResponseMock(raw=self.RESPONSE, getheader_side_effect=lambda: len(self.RESPONSE), read_side_effect=self._side_effect_sleep)
        )

        self.d = Download(self.fs)
        self.d.temp_dir = os.path.abspath('./test')

    def tearDown(self):
        download.urllib3 = self.urllib3_original
        if os.path.exists('test'):
            shutil.rmtree('test')

    def _side_effect_sleep(self):
        time.sleep(1.0)

    def _end_callback(self, status, filepath):
        logging.debug('End callback: status=%s filepath=%s' % (status, filepath))
        self.async_status = status
        self.async_filepath = filepath

    def test_download_file_async(self):
        self.d.download_file_async(self.DUMMY_FILE, self._end_callback)
        time.sleep(1.0)
        self.d.cancel()
        time.sleep(1.0)
        self.assertEqual(self.async_status, self.d.STATUS_CANCELED)
        self.assertEqual(self.async_filepath, None)

    def test_download_file_async_cancel_while_not(self):
        #should not crash
        self.d.cancel()
            


if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_download.py; coverage report -m
    unittest.main()
