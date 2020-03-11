#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append('%s/../../../libs/internals' % os.getcwd())
from installraspiot import InstallRaspiot, Download, InstallDeb, EndlessConsole
from raspiot.libs.tests.lib import TestLib
from raspiot.utils import MissingParameter, InvalidParameter
import unittest
import logging
import time
from mock import Mock, patch
import zipfile
import StringIO

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
    source: https://stackoverflow.com/a/2463818
    """
    def __init__(self):
        self.in_memory_zip = StringIO.StringIO()

    def append(self, filename_in_zip, file_contents):
        '''Appends a file with name filename_in_zip and contents of 
        file_contents to the in-memory zip.'''
        zf = zipfile.ZipFile(self.in_memory_zip, "a", zipfile.ZIP_DEFLATED, False)
        zf.writestr(filename_in_zip, file_contents)
        for zfile in zf.filelist:
            zfile.create_system = 0        
        return self

    def read(self):
        self.in_memory_zip.seek(0)
        return self.in_memory_zip.read()

    def write_to_file(self, filename):
        f = file(filename, "w")
        f.write(self.read())
        f.close()


class InstallRaspiotTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.archive_name = 'test_installraspiot.zip'
        self.checksum = '1234567890'
        self.checksum_full = '%s archive.fake.zip' % self.checksum
        self.archive_url = 'http://www.github.com/dummy/dummy/archive.fake.zip'
        self.checksum_url = 'http://www.github.com/dummy/dummy/archive.fake.sha256'        

    def tearDown(self):
        if os.path.exists('/usr/bin/gpio'):
            os.system('/usr/bin/yes 2>/dev/null | apt-get purge wiringpi > /dev/null 2>&1')
        if os.path.exists('/tmp/preinst.tmp'):
            os.remove('/tmp/preinst.tmp')
        if os.path.exists('/tmp/postinst.tmp'):
            os.remove('/tmp/postinst.tmp')
        if os.path.exists(self.archive_name):
            os.remove(self.archive_name)

    def callback(self, status):
        logging.debug('Callback status=%s' % status)

    def _create_archive(self, preinst=None, postinst=None, alter_archive=False):
        imz = InMemoryZip()
        imz.append('raspiot.deb', 'fake deb package')
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

    @patch('installraspiot.InstallDeb')
    @patch('installraspiot.Download')
    def test_install_without_scripts(self, download_mock, installdeb_mock):
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock)
        self._create_archive()

        i = InstallRaspiot(self.fs, self.crash_report)
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
        self.assertTrue('prescript' in status)
        self.assertTrue('stdout' in status['prescript'])
        self.assertTrue('stderr' in status['prescript'])
        self.assertTrue('returncode' in status['prescript'])
        self.assertEqual(status['prescript']['returncode'], None)
        self.assertTrue('postscript' in status)
        self.assertTrue('stdout' in status['postscript'])
        self.assertTrue('stderr' in status['postscript'])
        self.assertTrue('returncode' in status['postscript'])
        self.assertEqual(status['postscript']['returncode'], None)

    @patch('installraspiot.InstallDeb')
    @patch('installraspiot.Download')
    def test_install_with_scripts(self, download_mock, installdeb_mock):
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock)
        self._create_archive(u'echo "stdout message for pre"; echo "stderr message for pre" >&2; exit 0', u'echo "stdout message for post"; echo "stderr message for post" >&2; exit 0')

        i = InstallRaspiot(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['prescript']['returncode'], 0)
        self.assertTrue('stdout message for pre' in status['prescript']['stdout'])
        self.assertTrue('stderr message for pre' in status['prescript']['stderr'])
        self.assertEqual(status['postscript']['returncode'], 0)
        self.assertTrue('stdout message for post' in status['postscript']['stdout'])
        self.assertTrue('stderr message for post' in status['postscript']['stderr'])

    @patch('installraspiot.InstallDeb')
    @patch('installraspiot.Download')
    @patch('installraspiot.EndlessConsole')
    def test_install_preinst_exception(self, endlessconsole_mock, download_mock, installdeb_mock):
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock, endlessconsole_mock=endlessconsole_mock, endlessconsole_side_effect=Exception('Test'))
        self._create_archive(u'echo "stdout message for pre"; exit 0', u'echo "stdout message for post"; exit 0')

        i = InstallRaspiot(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_PREINST)

    @patch('installraspiot.InstallDeb')
    @patch('installraspiot.Download')
    @patch('installraspiot.EndlessConsole')
    def test_install_postinst_exception(self, endlessconsole_mock, download_mock, installdeb_mock):
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock, endlessconsole_mock=endlessconsole_mock, endlessconsole_side_effect=Exception('Test'))
        self._create_archive(None, u'echo "stdout message for post"; exit 0')

        i = InstallRaspiot(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_POSTINST)

    @patch('installraspiot.InstallDeb')
    @patch('installraspiot.Download')
    def test_install_exception_during_callback(self, download_mock, installdeb_mock):
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock)
        self._create_archive(None, None)

        def invalid_callback(*args, **kwargs):
            raise Exception('Test')

        i = InstallRaspiot(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, invalid_callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_INTERNAL)
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installraspiot.InstallDeb')
    @patch('installraspiot.Download')
    def test_download_checksum_failed(self, download_mock, installdeb_mock):
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock, download_content_return_value=(3, None))
        self._create_archive()

        i = InstallRaspiot(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_DOWNLOAD_CHECKSUM)

    @patch('installraspiot.InstallDeb')
    @patch('installraspiot.Download')
    def test_download_checksum_exception(self, download_mock, installdeb_mock):
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock, download_content_side_effect=Exception('Test'))
        self._create_archive()

        i = InstallRaspiot(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_DOWNLOAD_CHECKSUM)
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installraspiot.InstallDeb')
    @patch('installraspiot.Download')
    def test_download_archive_failed(self, download_mock, installdeb_mock):
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock, download_file_side_effect=Exception('test'))
        self._create_archive()

        i = InstallRaspiot(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_DOWNLOAD_ARCHIVE)
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installraspiot.Download')
    def test_extract_archive_failed(self, download_mock):
        self._init_context(download_mock=download_mock)
        self._create_archive(alter_archive=True)

        i = InstallRaspiot(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_EXTRACT)
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installraspiot.Download')
    def test_install_deb_invalid_deb_archive(self, download_mock):
        self._init_context(download_mock=download_mock)
        self._create_archive()

        i = InstallRaspiot(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_DEB)
        self.assertTrue(self.crash_report.manual_report.called)

    @patch('installraspiot.InstallDeb')
    @patch('installraspiot.Download')
    def test_install_deb_exception(self, download_mock, installdeb_mock):
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock, installdeb_install_side_effect=Exception('Test'))
        self._create_archive(None, None)

        i = InstallRaspiot(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_DEB)
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installraspiot.InstallDeb')
    @patch('installraspiot.Download')
    def test_install_deb_failed(self, download_mock, installdeb_mock):
        installdeb_get_status_return_value = {
            'status': 3, # STATUS_ERROR
            'stdout': [],
            'returncode': 0,
        }
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock, installdeb_get_status_return_value=installdeb_get_status_return_value)
        self._create_archive(None, None)

        i = InstallRaspiot(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_DEB)

    @patch('installraspiot.InstallDeb')
    @patch('installraspiot.Download')
    def test_preinst_failed(self, download_mock, installdeb_mock):
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock)
        self._create_archive('exit 1')

        i = InstallRaspiot(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_PREINST)

    @patch('installraspiot.InstallDeb')
    @patch('installraspiot.Download')
    def test_postinst_failed(self, download_mock, installdeb_mock):
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock)
        self._create_archive(postinst='exit 1')

        i = InstallRaspiot(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_POSTINST)

    @patch('installraspiot.InstallDeb')
    @patch('installraspiot.Download')
    def test_download_archive_internal_error(self, download_mock, installdeb_mock):
        # STATUS_ERROR
        download_file_return_value = (3, None)
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock, download_file_return_value=download_file_return_value)
        self._create_archive()

        i = InstallRaspiot(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_DOWNLOAD_ARCHIVE)

    @patch('installraspiot.InstallDeb')
    @patch('installraspiot.Download')
    def test_download_archive_invalid_checksum(self, download_mock, installdeb_mock):
        # STATUS_ERROR_BADCHECKSUM
        download_file_return_value = (5, None)
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock, download_file_return_value=download_file_return_value)
        self._create_archive()

        i = InstallRaspiot(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_DOWNLOAD_ARCHIVE)

    @patch('installraspiot.InstallDeb')
    @patch('installraspiot.Download')
    def test_download_archive_invalid_size(self, download_mock, installdeb_mock):
        # STATUS_ERROR_INVALIDSIZE
        download_file_return_value = (4, None)
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock, download_file_return_value=download_file_return_value)
        self._create_archive()

        i = InstallRaspiot(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_DOWNLOAD_ARCHIVE)

    @patch('installraspiot.InstallDeb')
    @patch('installraspiot.Download')
    def test_download_archive_unmanaged_error(self, download_mock, installdeb_mock):
        # STATUS_CANCELED
        download_file_return_value = (7, None)
        self._init_context(download_mock=download_mock, installdeb_mock=installdeb_mock, download_file_return_value=download_file_return_value)
        self._create_archive()

        i = InstallRaspiot(self.fs, self.crash_report)
        i.install(self.archive_url, self.checksum_url, self.callback)
        i.join()

        status = i.get_status()
        logging.debug('Status=%s' % status)
        self.assertEqual(status['status'], i.STATUS_ERROR_DOWNLOAD_ARCHIVE)

class InstallRaspiotFunctionalTests(unittest.TestCase):

    def setUp(self):
        t = TestLib(self)
        t.declare_functional_test()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        from raspiot.libs.internals.cleepfilesystem import CleepFilesystem
        self.fs = CleepFilesystem()
        self.fs.enable_write(True, True)
        self.crash_report = Mock()

        self.url_raspiot = 'https://github.com/tangb/raspiot/raw/master/tests/installraspiot/%s.zip'
        self.url_checksum = 'https://github.com/tangb/raspiot/raw/master/tests/installraspiot/%s.sha256'

    def tearDown(self):
        if os.path.exists('/usr/bin/gpio'):
            os.system('/usr/bin/yes 2>/dev/null | apt-get purge wiringpi > /dev/null 2>&1')
        if os.path.exists('/tmp/preinst.tmp'):
            os.remove('/tmp/preinst.tmp')
        if os.path.exists('/tmp/postinst.tmp'):
            os.remove('/tmp/postinst.tmp')

    def callback(self, status):
        logging.debug('Callback status=%s' % status)

    def test_install_ok_with_scripts(self):
        name = 'installraspiot.ok'
        url_raspiot = self.url_raspiot % name
        url_checksum = self.url_checksum % name
        i = InstallRaspiot(self.fs, self.crash_report)
        i.install(url_raspiot, url_checksum, self.callback)
        i.join()

        self.assertEqual(i.get_status()['status'], i.STATUS_UPDATED)
        self.assertEqual(i.get_status()['progress'], 100)
        self.assertTrue(os.path.exists('/usr/bin/gpio'))
        self.assertTrue(os.path.exists('/tmp/preinst.tmp'))
        self.assertTrue(os.path.exists('/tmp/postinst.tmp'))

    def test_install_error_postscript(self):
        name = 'installraspiot.post-ko'
        url_raspiot = self.url_raspiot % name
        url_checksum = self.url_checksum % name
        i = InstallRaspiot(self.fs, self.crash_report)
        i.install(url_raspiot, url_checksum, self.callback)
        i.join()

        self.assertEqual(i.get_status()[u'status'], i.STATUS_ERROR_POSTINST)

    def test_install_error_prescript(self):
        #install
        name = 'installraspiot.pre-ko'
        url_raspiot = self.url_raspiot % name
        url_checksum = self.url_checksum % name
        i = InstallRaspiot(self.fs, self.crash_report)
        i.install(url_raspiot, url_checksum, self.callback)
        i.join()

        self.assertEqual(i.get_status()[u'status'], i.STATUS_ERROR_PREINST)

    def test_install_error_deb(self):
        name = 'installraspiot.deb-ko'
        url_raspiot = self.url_raspiot % name
        url_checksum = self.url_checksum % name
        i = InstallRaspiot(self.fs, self.crash_report)
        i.install(url_raspiot, url_checksum, self.callback)
        i.join()

        self.assertEqual(i.get_status()[u'status'], i.STATUS_ERROR_DEB)

    def test_install_ok_without_script(self):
        name = 'installraspiot.noscript-ok'
        url_raspiot = self.url_raspiot % name
        url_checksum = self.url_checksum % name
        i = InstallRaspiot(self.fs, self.crash_report)
        i.install(url_raspiot, url_checksum, self.callback)
        i.join()

        self.assertEqual(i.get_status()[u'status'], i.STATUS_UPDATED)

    def test_install_bad_checksum(self):
        name = 'installraspiot.badchecksum-ko'
        url_raspiot = self.url_raspiot % name
        url_checksum = self.url_checksum % name
        i = InstallRaspiot(self.fs, self.crash_report)
        i.install(url_raspiot, url_checksum, self.callback)
        i.join()

        self.assertEqual(i.get_status()[u'status'], i.STATUS_ERROR_DOWNLOAD_ARCHIVE)

    
if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_installraspiot.py; coverage report -m
    unittest.main()

