#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gevent import monkey
monkey.patch_all()
import cleep.libs.internals.tools as tools
import os
import logging
from unittest.mock import Mock

TRACE = tools.TRACE
KEY_FUNCTIONAL_TEST = 'UNITTEST_FUNC'


class FileDescriptorMock():
    """
    FileDescriptorMock is used to simulate output of file|io.open function and force some output values or side effects
    """
    def __init__(self, write_side_effect=None, content='file content\n', read_side_effect=None, readlines_side_effect=None):
        """
        Constructor

        Args:
            write_side_effect (function|exception): function to call as write function side effect or exception to raise
            content (string): default file content returned by read
            read_side_effect (function|exception): function to call as read function side effect or exception to raise
            readlines_side_effect (function|exception): function to call as readlines function side effect or exception to raise
        """
        self.write_side_effect = write_side_effect
        self.read_side_effect = read_side_effect
        self.readlines_side_effect = readlines_side_effect
        self.content = content

    def get_content_hashes(self):
        """
        Returns hashes of specified content
        """
        import hashlib
        md5 = hashlib.md5()
        md5.update(self.content.encode('utf-8'))
        sha1 = hashlib.sha1()
        sha1.update(self.content.encode('utf-8'))
        sha256 = hashlib.sha256()
        sha256.update(self.content.encode('utf-8'))
        return {
            'md5': md5.hexdigest(),
            'sha1': sha1.hexdigest(),
            'sha256': sha256.hexdigest(),
        }

    def __exit__(self, *args, **kwargs):
        pass

    def __enter__(self, *args, **kwargs):
        return self

    def write(self, *args, **kwargs):
        if self.write_side_effect:
            if isinstance(self.write_side_effect, Exception):
                # pylint: disable=E0702
                raise self.write_side_effect
            else:
                self.write_side_effect()
        return 6

    def read(self, *args, **kwargs):
        if self.read_side_effect:
            if isinstance(self.read_side_effect, Exception):
                # pylint: disable=E0702
                raise self.read_side_effect
            else:
                self.read_side_effect()
        return None if len(self.content)==0 else self.content

    def readlines(self, *args, **kwargs):
        if self.readlines_side_effect:
            if isinstance(self.readlines_side_effect, Exception):
                # pylint: disable=E0702
                raise self.readlines_side_effect
            else:
                self.readlines_side_effect()
        return None if len(self.content)==0 else self.content.split()

    def close(self, *args, **kwargs):
        return


class TestLib():
    """
    Instanciate TestLib to enable some features to be able to run tests on a library for Cleep
    """

    def __init__(self, test_case=None):
        """
        Constructor

        Args:
            test_case (TestCase): test case instance. Optional
        """
        self.test_case = test_case
        tools.install_trace_logging_level()

    def set_functional_tests(self):
        if self.test_case is None:
            logging.warning('Can\'t declare functional test if "test_case" param not specified during TestLib() init')
            return
        if KEY_FUNCTIONAL_TEST not in os.environ:
            self.test_case.skipTest('Functional tests are skipped')

    @staticmethod
    def mock_urllib3(request_response, request_side_effect=None):
        """
        Mock urllib3

        Args:
            request_response (instance): mocked response instance. You can use Urllib3RequestResponseMock.
            request_side_effect (anything): value passed to Mock side_effect parameter

        Returns:
            tuple::

                (
                    urllib3 mock (Mock): urllib3 mock instance
                    request mock (Mock): urllib3.PoolManager.request mock instance
                )

        """
        urllib3_mock = Mock()
        urllib3_mock.PoolManager = Mock()
        urllib3_mock.PoolManager.return_value = Mock()
        if request_side_effect:
            request_mock = urllib3_mock.PoolManager.return_value.request = Mock(side_effect=request_side_effect)
        else:
            request_mock = urllib3_mock.PoolManager.return_value.request = Mock()
        urllib3_mock.PoolManager.return_value.request.return_value = request_response

        return urllib3_mock, request_mock

    @staticmethod
    def mock_cleepfilesystem(open_response=None, open_side_effect=None, rename_side_effect=None):
        """
        Mock cleepfilsystem

        Args:
            open_response (instance): mock output of open function
            open_side_effect (function|exception): value passed to mock side_effect parameter
            rename_side_effect (function|exception): value passed to mock side_effect parameter
        """
        fs = Mock()
        fs.open = Mock(side_effect=open_side_effect)
        fs.rename = Mock(side_effect=rename_side_effect)
        if open_response:
            fs.open.return_value = open_response

        return fs

    @staticmethod
    def clone_class(base_class):
        """ 
        Clone specified base class. This can be useful when you need to alter class (adding mock)
        keeping original one clean.

        Args:
            base_class (Class): class object (not instance!)

        Returns:
            Class: cloned class that can be instanciated. Cloned class name is prefixed by "C"
        """
        class ClonedClass(base_class):
            pass
        ClonedClass.__name__ = 'C%s' % base_class.__name__

        return ClonedClass

