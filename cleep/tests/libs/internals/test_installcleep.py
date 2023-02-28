#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from installcleep import InstallCleep, Download, InstallDeb, EndlessConsole
from cleep.libs.tests.lib import TestLib
from cleep.exception import MissingParameter, InvalidParameter
import unittest
import logging
import time
from unittest.mock import Mock, patch
import zipfile
from io import BytesIO
import io
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()


class InstallDebStatus():
    STATUS_IDLE = 0
    STATUS_RUNNING = 1
    STATUS_DONE = 2
    STATUS_ERROR = 3
    STATUS_KILLED = 4
    STATUS_TIMEOUT = 5

    @staticmethod
    def init_mock(mocked):
        mocked.return_value.STATUS_IDLE = 0
        mocked.return_value.STATUS_RUNNING = 1
        mocked.return_value.STATUS_DONE = 2
        mocked.return_value.STATUS_ERROR = 3
        mocked.return_value.STATUS_KILLED = 4
        mocked.return_value.STATUS_TIMEOUT = 5

class DownloadStatus():
    STATUS_IDLE = 0
    STATUS_DOWNLOADING = 1
    STATUS_DOWNLOADING_NOSIZE = 2
    STATUS_ERROR = 3
    STATUS_ERROR_INVALIDSIZE = 4
    STATUS_ERROR_BADCHECKSUM = 5
    STATUS_DONE = 6
    STATUS_CANCELED = 7
    STATUS_CACHED = 8

    @staticmethod
    def init_mock(mocked):
        mocked.STATUS_IDLE = 0
        mocked.STATUS_DOWNLOADING = 1
        mocked.STATUS_DOWNLOADING_NOSIZE = 2
        mocked.STATUS_ERROR = 3
        mocked.STATUS_ERROR_INVALIDSIZE = 4
        mocked.STATUS_ERROR_BADCHECKSUM = 5
        mocked.STATUS_DONE = 6
        mocked.STATUS_CANCELED = 7
        mocked.STATUS_CACHED = 8

class InMemoryZip(object):
    """
    source: https://stackoverflow.com/a/2463818 (py2), https://stackoverflow.com/a/44946732 (py3)
    """
    def __init__(self):
        self.in_memory_zip = BytesIO()

    def append(self, filename_in_zip, file_contents):
        """
        Appends a file with name filename_in_zip and contents of 
        file_contents to the in-memory zip.
        """
        with zipfile.ZipFile(self.in_memory_zip, 'a', zipfile.ZIP_DEFLATED, False) as zf:
            zf.writestr(filename_in_zip, file_contents)
            for zfile in zf.filelist:
                zfile.create_system = 0

        return self

    def read(self):
        self.in_memory_zip.seek(0)
        return self.in_memory_zip.getvalue()

    def write_to_file(self, filename):
        with open(filename, 'wb') as f:
            f.write(self.read())


class InstallCleepTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.archive_name = 'test_installcleep.zip'
        self.checksum = '1234567890'
        self.checksum_full = '%s archive.fake.zip' % self.checksum
        self.archive_url = 'http://www.github.com/dummy/dummy/archive.fake.zip'
        self.checksum_url = 'http://www.github.com/dummy/dummy/archive.fake.sha256'        

    def tearDown(self):
        if os.path.exists('/usr/bin/gpio'):
            os.system('/usr/bin/yes 2>/dev/null | apt-get purge wiringpi > /dev/null 2>&1')
        if os.path.exists(self.archive_name):
            os.remove(self.archive_name)

    def callback(self, status):
        logging.debug('Callback status=%s' % status)

    def _create_archive(self, preinst=None, postinst=None, alter_archive=False):
        imz = InMemoryZip()
        imz.append('cleep.deb', 'fake deb package')
        if preinst:
            imz.append('preinst.sh', preinst)
        if postinst:
            imz.append('postinst.sh', postinst)
        imz.write_to_file(self.archive_name)
        if alter_archive:
            with open(self.archive_name, 'w') as fd:
                fd.write('--')

    def _init_context(self, download_mock=None,
                    download_file_return_value=None, download_file_side_effect=None,
                    download_content_return_value=None, download_content_side_effect=None,
                    download_get_status_return_value=None,
                    installdeb_mock=None,
                    installdeb_get_status_return_value=None, installdeb_install_side_effect=None,
                    endlessconsole_mock=None, endlessconsole_side_effect=None):
        self.fs = Mock()
        self.crash_report = Mock()
        self.crash_report.manual_report = Mock()
        self.crash_report.report_exception = Mock()

        if download_mock:
            DownloadStatus.init_mock(download_mock)
            download_content_return_value = download_content_return_value if download_content_return_value is not None else (6, self.checksum_full)
            if download_content_side_effect:
                download_mock.return_value.download_content = Mock(side_effect=download_content_side_effect)
            else:
                download_mock.return_value.download_content = Mock(return_value=download_content_return_value)
            if download_file_side_effect:
                download_mock.return_value.download_file = Mock(side_effect=download_file_side_effect)
            else:
                download_file_return_value = download_file_return_value if download_file_return_value is not None else (6, self.archive_name)
                download_mock.return_value.download_file = Mock(return_value=download_file_return_value)
            download_get_status_return_value = download_file_return_value if download_file_return_value is not None else {
            }
        if installdeb_mock:
            InstallDebStatus.init_mock(installdeb_mock)
            installdeb_mock.return_value.dry_run = Mock(return_value=True)
            installdeb_mock.return_value.install = Mock(side_effect=installdeb_install_side_effect)
            installdeb_get_status_return_value = installdeb_get_status_return_value if installdeb_get_status_return_value is not None else {
                'status': 2, # STATUS_DONE
                'stdout': [],
                'returncode': 0,
            }
            installdeb_mock.return_value.get_status = Mock(return_value=installdeb_get_status_return_value)
        if endlessconsole_mock:
            endlessconsole_mock.return_value.start = Mock(side_effect=endlessconsole_side_effect)

    @patch('installcleep.InstallDeb')
    @patch('installcleep.Download')
    def test_install(self, download_mock, installdeb_mock):
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock)
        self._create_archive()

        i = InstallCleep(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertTrue('status' in status)
        self.assertEqual(status['status'], i.STATUS_UPDATED)
        self.assertTrue('progress' in status)
        self.assertEqual(status['progress'], 100)
        self.assertTrue('deb' in status)
        self.assertTrue('status' in status['deb'])
        self.assertEqual(status['deb']['status'], 2)
        self.assertTrue('stdout' in status['deb'])
        self.assertTrue('returncode' in status['deb'])

    @patch('installcleep.InstallDeb')
    @patch('installcleep.Download')
    def test_install_exception_during_callback(self, download_mock, installdeb_mock):
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock)
        self._create_archive(None, None)

        def invalid_callback(*args, **kwargs):
            raise Exception('Test')

        i = InstallCleep(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, invalid_callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_INTERNAL)
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installcleep.InstallDeb')
    @patch('installcleep.Download')
    def test_download_checksum_failed(self, download_mock, installdeb_mock):
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock, download_content_return_value=(3, None))
        self._create_archive()

        i = InstallCleep(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_DOWNLOAD_CHECKSUM)

    @patch('installcleep.InstallDeb')
    @patch('installcleep.Download')
    def test_download_checksum_exception(self, download_mock, installdeb_mock):
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock, download_content_side_effect=Exception('Test'))
        self._create_archive()

        i = InstallCleep(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_DOWNLOAD_CHECKSUM)
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installcleep.InstallDeb')
    @patch('installcleep.Download')
    def test_download_archive_failed(self, download_mock, installdeb_mock):
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock, download_file_side_effect=Exception('test'))
        self._create_archive()

        i = InstallCleep(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_DOWNLOAD_PACKAGE)
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installcleep.Download')
    def test_install_deb_invalid_deb_archive(self, download_mock):
        self._init_context(download_mock=download_mock)
        self._create_archive()

        i = InstallCleep(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_DEB)
        self.assertTrue(self.crash_report.manual_report.called)

    @patch('installcleep.InstallDeb')
    @patch('installcleep.Download')
    def test_install_deb_exception(self, download_mock, installdeb_mock):
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock, installdeb_install_side_effect=Exception('Test'))
        self._create_archive(None, None)

        i = InstallCleep(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_DEB)
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installcleep.InstallDeb')
    @patch('installcleep.Download')
    def test_install_deb_failed(self, download_mock, installdeb_mock):
        installdeb_get_status_return_value = {
            'status': 3, # STATUS_ERROR
            'stdout': [],
            'returncode': 0,
        }
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock, installdeb_get_status_return_value=installdeb_get_status_return_value)
        self._create_archive(None, None)

        i = InstallCleep(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_DEB)

    @patch('installcleep.InstallDeb')
    @patch('installcleep.Download')
    def test_download_archive_internal_error(self, download_mock, installdeb_mock):
        # STATUS_ERROR
        download_file_return_value = (3, None)
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock, download_file_return_value=download_file_return_value)
        self._create_archive()

        i = InstallCleep(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_DOWNLOAD_PACKAGE)

    @patch('installcleep.InstallDeb')
    @patch('installcleep.Download')
    def test_download_archive_invalid_checksum(self, download_mock, installdeb_mock):
        # STATUS_ERROR_BADCHECKSUM
        download_file_return_value = (5, None)
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock, download_file_return_value=download_file_return_value)
        self._create_archive()

        i = InstallCleep(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_DOWNLOAD_PACKAGE)

    @patch('installcleep.InstallDeb')
    @patch('installcleep.Download')
    def test_download_archive_invalid_size(self, download_mock, installdeb_mock):
        # STATUS_ERROR_INVALIDSIZE
        download_file_return_value = (4, None)
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock, download_file_return_value=download_file_return_value)
        self._create_archive()

        i = InstallCleep(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_DOWNLOAD_PACKAGE)

    @patch('installcleep.InstallDeb')
    @patch('installcleep.Download')
    def test_download_archive_unmanaged_error(self, download_mock, installdeb_mock):
        # STATUS_CANCELED
        download_file_return_value = (7, None)
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock, download_file_return_value=download_file_return_value)
        self._create_archive()

        i = InstallCleep(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_DOWNLOAD_PACKAGE)

class InstallCleepFunctionalTests(unittest.TestCase):

    def setUp(self):
        t = TestLib(self)
        t.set_functional_tests()
        logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        from cleep.libs.internals.cleepfilesystem import CleepFilesystem
        self.fs = CleepFilesystem()
        self.fs.enable_write(True, True)
        self.crash_report = Mock()

        self.url_cleep = 'https://github.com/tangb/cleep/raw/master/tests/installcleep/%s.zip'
        self.url_checksum = 'https://github.com/tangb/cleep/raw/master/tests/installcleep/%s.sha256'

    def tearDown(self):
        if os.path.exists('/usr/bin/gpio'):
            os.system('/usr/bin/yes 2>/dev/null | apt-get purge wiringpi > /dev/null 2>&1')

    def callback(self, status):
        logging.debug('Callback status=%s' % status)

    def test_install_ok_with_scripts(self):
        name = 'installcleep.ok'
        url_cleep = self.url_cleep % name
        url_checksum = self.url_checksum % name
        i = InstallCleep(self.fs, self.crash_report)
        i.install(url_cleep, url_checksum, self.callback)
        i.join()

        self.assertEqual(i.get_status()['status'], i.STATUS_UPDATED)
        self.assertEqual(i.get_status()['progress'], 100)
        self.assertTrue(os.path.exists('/usr/bin/gpio'))

    def test_install_error_deb(self):
        name = 'installcleep.deb-ko'
        url_cleep = self.url_cleep % name
        url_checksum = self.url_checksum % name
        i = InstallCleep(self.fs, self.crash_report)
        i.install(url_cleep, url_checksum, self.callback)
        i.join()

        self.assertEqual(i.get_status()['status'], i.STATUS_ERROR_DEB)

    def test_install_ok_without_script(self):
        name = 'installcleep.noscript-ok'
        url_cleep = self.url_cleep % name
        url_checksum = self.url_checksum % name
        i = InstallCleep(self.fs, self.crash_report)
        i.install(url_cleep, url_checksum, self.callback)
        i.join()

        self.assertEqual(i.get_status()['status'], i.STATUS_UPDATED)

    def test_install_bad_checksum(self):
        name = 'installcleep.badchecksum-ko'
        url_cleep = self.url_cleep % name
        url_checksum = self.url_checksum % name
        i = InstallCleep(self.fs, self.crash_report)
        i.install(url_cleep, url_checksum, self.callback)
        i.join()

        self.assertEqual(i.get_status()['status'], i.STATUS_ERROR_DOWNLOAD_PACKAGE)

    
if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_installcleep.py; coverage report -m -i
    unittest.main()

