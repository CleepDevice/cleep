#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time

sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace("tests/", ""))
import download
from download import Download
from cleep.libs.tests.lib import TestLib, FileDescriptorMock
import unittest
import logging
from unittest.mock import Mock, MagicMock
import shutil
import io
import base64
import responses
import json
from threading import Event
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()


def create_files_tree(DOWNLOAD_FILE_PREFIX, CACHED_FILE_PREFIX, with_files=True):
    os.mkdir("test")
    filename = base64.urlsafe_b64encode("123456789".encode("utf-8")).decode("utf-8")
    if with_files:
        downloaded_file = "test/%s_%s" % (DOWNLOAD_FILE_PREFIX, filename)
        os.system('echo "download" > "%s"' % downloaded_file)
        purged_file = "test/%s_%s" % (CACHED_FILE_PREFIX, filename)
        os.system('echo "download" > "%s"' % purged_file)


class DownloadTests(unittest.TestCase):
    def setUp(self):
        TestLib()
        logging.basicConfig(
            level=LOG_LEVEL,
            format=u"%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s",
        )

        self.fs = Mock()

        self.async_status = None
        self.async_filepath = None
        self.async_filesize = None
        self.async_percent = None
        self.end_callback_call = 0
        self.status_callback_call = 0

    def tearDown(self):
        responses.reset()

    def init(
        self,
        url="https://www.google.com",
        resp_data="",
        resp_status=200,
        resp_headers={},
        stream=False,
    ):
        responses.add(
            responses.GET,
            url,
            body=resp_data,
            headers=resp_headers,
            status=resp_status,
            stream=stream,
            match_querystring=False,
        )

        self.d = Download(self.fs)
        self.d.temp_dir = os.path.abspath("./test")

    def test_add_auth_token(self):
        self.init()
        self.assertFalse("Authorization" in self.d.headers)
        self.d.add_auth_token("123456789")
        self.assertTrue("Authorization" in self.d.headers)
        self.assertEqual(self.d.headers["Authorization"], "Token 123456789")

    def test_add_auth_bearer(self):
        self.init()
        self.assertFalse("Authorization" in self.d.headers)
        self.d.add_auth_bearer("987654321")
        self.assertTrue("Authorization" in self.d.headers)
        self.assertEqual(self.d.headers["Authorization"], "Bearer 987654321")

    def test_purge_files(self):
        self.init()
        try:
            create_files_tree(self.d.DOWNLOAD_FILE_PREFIX, self.d.CACHED_FILE_PREFIX)
            self.d.purge_files()
            self.assertEqual(self.fs.rm.call_count, 1)
        finally:
            if os.path.exists("test"):
                shutil.rmtree("test")

    def test_purge_files_all_files(self):
        self.init()
        try:
            create_files_tree(self.d.DOWNLOAD_FILE_PREFIX, self.d.CACHED_FILE_PREFIX)
            self.d.purge_files(True)
            self.assertEqual(self.fs.rm.call_count, 2)
        finally:
            if os.path.exists("test"):
                shutil.rmtree("test")

    def test_get_cached_files(self):
        self.init()
        try:
            create_files_tree(self.d.DOWNLOAD_FILE_PREFIX, self.d.CACHED_FILE_PREFIX)
            cached = self.d.get_cached_files()
            logging.debug("Cached: %s" % cached)
            self.assertTrue(isinstance(cached, list))
            self.assertEqual(len(cached), 1)
            self.assertTrue("filename" in cached[0])
            self.assertTrue("filepath" in cached[0])
            self.assertTrue("filesize" in cached[0])
            # self.assertEqual(self.fs.rm.call_count, 2)
        finally:
            if os.path.exists("test"):
                shutil.rmtree("test")

    def test_is_file_cached(self):
        self.init()
        try:
            create_files_tree(self.d.DOWNLOAD_FILE_PREFIX, self.d.CACHED_FILE_PREFIX)
            cached = self.d.is_file_cached("123456789")
            self.assertIsNotNone(cached)
            self.assertTrue("filename" in cached)
            self.assertTrue("filepath" in cached)
            self.assertTrue("filesize" in cached)
        finally:
            if os.path.exists("test"):
                shutil.rmtree("test")

    def test_hashes(self):
        self.init()
        try:
            FILENAME = "test.txt"
            with io.open(FILENAME, "w") as fd:
                fd.write(u"test file")
            fd = io.open(FILENAME, "rb")
            self.fs.open = Mock(return_value=fd)

            md5sum = "f20d9f2072bbeb6691c0f9c5099b01f3"
            sha1sum = "8f93542443e98f41fe98e97d6d2a147193b1b005"
            sha256sum = (
                "9a30a503b2862c51c3c5acd7fbce2f1f784cf4658ccf8e87d5023a90c21c0714"
            )

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

    @responses.activate
    def test_download_content(self):
        url = "http://proof.ovh.net/files/1Mio.dat"
        self.init(url, resp_data="héllo world", stream=True)
        status, content = self.d.download_content(url)
        logging.debug("status: %s content:%s" % (status, content))
        self.assertEqual(content, "héllo world")
        self.assertEqual(status, self.d.STATUS_DONE)

    @responses.activate
    def test_download_content_invalid_status_code(self):
        url = "https://www.google.com"
        self.init(url, resp_data="héllo world", resp_status=400)
        status, content = self.d.download_content(url)
        self.assertIsNone(content)
        self.assertEqual(status, self.d.STATUS_ERROR)

    @responses.activate
    def test_download_content_exception(self):
        url = "https://www.google.com"
        self.init(url, resp_data=Exception("Test exception"))
        status, content = self.d.download_content(url)
        self.assertIsNone(content)
        self.assertEqual(status, self.d.STATUS_ERROR)

    def _end_callback(self, status, filepath):
        logging.debug("End callback: status=%s filepath=%s" % (status, filepath))
        self.async_status = status
        self.async_filepath = filepath
        self.end_callback_call += 1

    def _status_callback(self, status, filesize, percent):
        logging.debug(
            "Status callback: status=%s filesize=%s percent=%s"
            % (status, filesize, percent)
        )
        self.async_status = status
        self.async_filesize = filesize
        self.async_percent = percent
        self.status_callback_call += 1

    @responses.activate
    def test_download_file_async(self):
        response = "héllo world"
        self.init(
            resp_data=response,
            stream=True,
            resp_headers={
                "Content-Type": "application/octet-stream",
                "Content-Length": "%s" % len(response.encode("utf8")),
            },
        )
        self.d.download_file_async(
            "https://www.google.com",
            self._end_callback,
            status_callback=self._status_callback,
        )
        time.sleep(1)
        self.assertGreaterEqual(self.status_callback_call, 2)
        self.assertEqual(self.end_callback_call, 1)
        self.assertEqual(self.async_status, self.d.STATUS_DONE)
        self.assertEqual(self.async_percent, 100)
        self.assertEqual(self.async_filesize, len(response.encode("utf8")))
        self.assertEqual(
            self.async_filepath.find(self.d.CACHED_FILE_PREFIX), -1
        )  # file shouldn't be cached by default

    @responses.activate
    def test_download_file_async_with_cached_filename(self):
        response = "héllo world"
        self.init(
            resp_data=response,
            stream=True,
            resp_headers={
                "Content-Type": "application/octet-stream",
                "Content-Length": "%s" % len(response.encode("utf8")),
            },
        )
        self.d.download_file_async(
            "https://www.google.com",
            self._end_callback,
            status_callback=self._status_callback,
            cache_filename="mycachedfile",
        )
        time.sleep(0.5)
        self.assertEqual(self.async_status, self.d.STATUS_DONE)
        self.assertNotEqual(self.async_filepath.find(self.d.CACHED_FILE_PREFIX), -1)

    @responses.activate
    def test_download_file_async_with_cached_file(self):
        try:
            self.init()
            create_files_tree(self.d.DOWNLOAD_FILE_PREFIX, self.d.CACHED_FILE_PREFIX)
            self.d.download_file_async(
                "https://www.google.com",
                self._end_callback,
                status_callback=self._status_callback,
                cache_filename="123456789",
            )
            time.sleep(0.25)
            self.assertEqual(self.status_callback_call, 1)
            self.assertEqual(self.end_callback_call, 1)
            self.assertEqual(self.async_status, self.d.STATUS_DONE)
            self.assertEqual(self.async_percent, 100)
        finally:
            if os.path.exists("test"):
                shutil.rmtree("test")

    @responses.activate
    def test_download_file_async_check_sha1(self):
        self.init(stream=True)
        self.d.generate_sha1 = Mock(return_value="1234")
        self.d.generate_sha256 = Mock()
        self.d.generate_md5 = Mock()
        self.d.download_file_async(
            "https://www.google.com",
            self._end_callback,
            check_sha1="1234",
            status_callback=self._status_callback,
        )
        time.sleep(0.5)
        self.assertEqual(self.async_status, self.d.STATUS_DONE)
        self.assertTrue(self.d.generate_sha1.called)
        self.assertFalse(self.d.generate_sha256.called)
        self.assertFalse(self.d.generate_md5.called)

    @responses.activate
    def test_download_file_async_check_sha256(self):
        self.init(stream=True)
        self.d.generate_sha1 = Mock()
        self.d.generate_sha256 = Mock(return_value="1234")
        self.d.generate_md5 = Mock()
        self.d.download_file_async(
            "https://www.google.com",
            self._end_callback,
            check_sha256="1234",
            status_callback=self._status_callback,
        )
        time.sleep(0.5)
        self.assertEqual(self.async_status, self.d.STATUS_DONE)
        self.assertFalse(self.d.generate_sha1.called)
        self.assertTrue(self.d.generate_sha256.called)
        self.assertFalse(self.d.generate_md5.called)

    @responses.activate
    def test_download_file_async_check_md5(self):
        self.init(stream=True)
        self.d.generate_sha1 = Mock()
        self.d.generate_sha256 = Mock()
        self.d.generate_md5 = Mock(return_value="1234")
        self.d.download_file_async(
            "https://www.google.com",
            self._end_callback,
            check_md5="1234",
            status_callback=self._status_callback,
        )
        time.sleep(0.5)
        self.assertEqual(self.async_status, self.d.STATUS_DONE)
        self.assertFalse(self.d.generate_sha1.called)
        self.assertFalse(self.d.generate_sha256.called)
        self.assertTrue(self.d.generate_md5.called)

    @responses.activate
    def test_download_file_async_checksum_failed(self):
        self.init(stream=True)
        self.d.generate_md5 = Mock(return_value="12341234")
        self.d.download_file_async(
            "https://www.google.com",
            self._end_callback,
            check_md5="1234",
            status_callback=self._status_callback,
        )
        time.sleep(0.5)
        self.assertEqual(self.async_status, self.d.STATUS_ERROR_BADCHECKSUM)
        self.assertTrue(self.d.generate_md5.called)

    @responses.activate
    def test_download_file_async_invalid_status(self):
        self.init(stream=True, resp_status=400)
        self.d.download_file_async(
            "https://www.google.com",
            self._end_callback,
            status_callback=self._status_callback,
        )
        time.sleep(0.5)
        self.assertEqual(self.async_status, self.d.STATUS_ERROR)

    @responses.activate
    def test_download_file_async_exception_during_download(self):
        self.init(stream=True, resp_data=Exception("Test exception"))
        self.d.download_file_async(
            "https://www.google.com",
            self._end_callback,
            status_callback=self._status_callback,
        )
        time.sleep(0.5)
        self.assertEqual(self.async_status, self.d.STATUS_ERROR)

    @responses.activate
    def test_download_file_async_exception_during_download_preparation(self):
        self.init(stream=True)
        self.fs.open.side_effect = Exception("Test exception")
        self.d.download_file_async(
            "https://www.google.com",
            self._end_callback,
            status_callback=self._status_callback,
        )
        time.sleep(0.5)
        self.assertEqual(self.async_status, self.d.STATUS_ERROR)

    @responses.activate
    def test_download_file_async_exception_during_download_renaming(self):
        self.init(stream=True)
        self.fs.rename.side_effect = Exception("Test exception")
        self.d.download_file_async(
            "https://www.google.com",
            self._end_callback,
            status_callback=self._status_callback,
        )
        time.sleep(0.5)
        self.assertEqual(self.async_status, self.d.STATUS_ERROR)

    @responses.activate
    def test_download_file_async_invalid_size(self):
        response = "héllo world"
        self.init(
            resp_data=response,
            stream=True,
            resp_headers={
                "Content-Type": "application/octet-stream",
                "Content-Length": "%s" % (len(response.encode("utf8")) - 1),
            },
        )
        self.d.download_file_async(
            "https://www.google.com",
            self._end_callback,
            status_callback=self._status_callback,
        )
        time.sleep(1)
        self.assertGreaterEqual(self.status_callback_call, 2)
        self.assertEqual(self.end_callback_call, 1)
        self.assertEqual(self.async_status, self.d.STATUS_ERROR_INVALIDSIZE)
        self.assertEqual(self.async_percent, 100)


class DownloadTestsNoCleepFilesystem(unittest.TestCase):
    def setUp(self):
        TestLib()
        logging.basicConfig(
            level=LOG_LEVEL,
            format=u"%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s",
        )
        self.os_remove_original = os.remove
        self.os_rename_original = os.rename
        self.io_open_original = io.open

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
        if os.path.exists("test"):
            shutil.rmtree("test")

    def _init_download(
        self,
        remove_side_effect=None,
        rename_side_effect=None,
        open_side_effect=None,
        url="https://www.google.com",
        resp_data="",
        resp_status=200,
        resp_headers={},
        stream=False,
    ):
        responses.add(
            responses.GET,
            url,
            body=resp_data,
            headers=resp_headers,
            status=resp_status,
            stream=stream,
        )
        os.remove = Mock(side_effect=remove_side_effect)
        os.rename = Mock(side_effect=rename_side_effect)
        self.d = Download(None)
        self.d.temp_dir = os.path.abspath("./test")

    @responses.activate
    def test_purge_files(self):
        self._init_download()
        create_files_tree(self.d.DOWNLOAD_FILE_PREFIX, self.d.CACHED_FILE_PREFIX)
        self.d.purge_files()
        self.assertEqual(os.remove.call_count, 1)

    @responses.activate
    def test_purge_files_exception(self):
        self._init_download(remove_side_effect=Exception("Test exception"))
        create_files_tree(self.d.DOWNLOAD_FILE_PREFIX, self.d.CACHED_FILE_PREFIX)
        self.d.purge_files()

    @responses.activate
    def test_purge_files_all_files(self):
        self._init_download()
        create_files_tree(self.d.DOWNLOAD_FILE_PREFIX, self.d.CACHED_FILE_PREFIX)
        self.d.purge_files(True)
        self.assertEqual(os.remove.call_count, 2)

    @responses.activate
    def test_purge_files_all_files_exception(self):
        self._init_download(remove_side_effect=Exception("Test exception"))
        create_files_tree(self.d.DOWNLOAD_FILE_PREFIX, self.d.CACHED_FILE_PREFIX)
        self.d.purge_files(True)

    def _end_callback(self, status, filepath):
        logging.debug("End callback: status=%s filepath=%s" % (status, filepath))
        self.async_status = status
        self.async_filepath = filepath
        self.end_callback_call += 1

    def _status_callback(self, status, filesize, percent):
        logging.debug(
            "Status callback: status=%s filesize=%s percent=%s"
            % (status, filesize, percent)
        )
        self.async_status = status
        self.async_filesize = filesize
        self.async_percent = percent
        self.status_callback_call += 1

    @responses.activate
    def test_download_file_async_rename_exception(self):
        self._init_download(rename_side_effect=Exception("Test exception"))
        create_files_tree(
            self.d.DOWNLOAD_FILE_PREFIX, self.d.CACHED_FILE_PREFIX, with_files=False
        )
        self.d.download_file_async(
            "https://www.google.com",
            self._end_callback,
            status_callback=self._status_callback,
        )
        time.sleep(1)
        self.assertEqual(self.async_status, self.d.STATUS_ERROR)


class DownloadTestsFileDownloadCancel(unittest.TestCase):
    def setUp(self):
        logging.basicConfig(
            level=LOG_LEVEL,
            format=u"%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s",
        )
        TestLib()
        self.fs = Mock()
        self.async_status = None
        self.async_filepath = None

    def tearDown(self):
        responses.reset()
        if os.path.exists("test"):
            shutil.rmtree("test")

    def init(self):
        responses.add(
            responses.GET,
            "https://www.google.com",
            body="hello work",
            status=200,
            stream=True,
        )
        self.d = Download(self.fs)
        self.d.temp_dir = os.path.abspath("./test")

    def _end_callback(self, status, filepath):
        logging.debug("End callback: status=%s filepath=%s" % (status, filepath))
        self.async_status = status
        self.async_filepath = filepath

    def _delay(self, *args, **kwargs):
        time.sleep(1.0)
        logging.debug("TIMEOUT")

    @responses.activate
    def test_download_file_async(self):
        self.init()
        self.fs.open.side_effect = self._delay
        self.d.download_file_async("https://www.google.com", self._end_callback)
        time.sleep(0.5)
        self.d.cancel()
        time.sleep(1.0)
        self.assertEqual(self.async_status, self.d.STATUS_CANCELED)
        self.assertEqual(self.async_filepath, None)

    @responses.activate
    def test_download_file_async_cancel_while_not(self):
        try:
            self.init()
            self.d.cancel()
        except:
            self.fail("Should not failed")


if __name__ == "__main__":
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_download.py; coverage report -m -i
    unittest.main()
