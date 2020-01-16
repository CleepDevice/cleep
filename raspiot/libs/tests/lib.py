#!/usr/bin/env python
# -*- coding: utf-8 -*-

import raspiot.libs.internals.tools as tools
import os
import logging
from mock import Mock

TRACE = tools.TRACE

class Urllib3RequestResponseMock():
    """
    Urllib3RequestResponseMock is used to simulate output of urllib3.request function and force some output values or side effects
    """
    def __init__(self, status=200, raw='', read_side_effect=None, getheader_side_effect=None):
        """
        Constructor

        Args:
            status (int): http response status
            raw (string): raw content to return to request call
            read_side_effect (function|exception): function to call as read function side effect or exception to raise
            getheader_side_effect (function|exception): function to call as getheader function side effect or exception to raise
        """
        self.status = status
        self.raw = raw
        self.__step = 0
        self.range = 4
        self.read_side_effect = read_side_effect
        self.getheader_side_effect = getheader_side_effect

    def read(self, *args, **kwargs):
        if self.read_side_effect:
            if isinstance(self.read_side_effect, Exception):
                # pylint: disable=E0702
                raise self.read_side_effect
            else:
                self.read_side_effect()
        out = self.raw[self.__step:self.__step+self.range]
        self.__step += self.range
        return None if len(out)==0 else out

    def getheader(self, *args, **kwargs):
        if self.getheader_side_effect:
            if isinstance(self.getheader_side_effect, Exception):
                # pylint: disable=E0702
                raise self.getheader_side_effect
            else:
                return self.getheader_side_effect()

class FileDescriptorMock():
    """
    FileDescriptorMock is used to simulate output of file|io.open function and force some output values or side effects
    """
    def __init__(self, write_side_effect=None, content='file content\n', read_side_effect=None):
        """
        Constructor

        Args:
            write_side_effect (function|exception): function to call as write function side effect or exception to raise
            content (string): default file content returned by read
            read_side_effect (function|exception): function to call as read function side effect or exception to raise
        """
        self.write_side_effect = write_side_effect
        self.read_side_effect = read_side_effect
        self.content = content
        self.__step = 0
        self.range = 4

    def get_content_hashes(self):
        """
        Returns hashes of specified content
        """
        import hashlib
        md5 = hashlib.md5()
        md5.update(self.content)
        sha1 = hashlib.sha1()
        sha1.update(self.content)
        sha256 = hashlib.sha256()
        sha256.update(self.content)
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
        out = self.content[self.__step:self.__step+self.range]
        self.__step += self.range
        return None if len(out)==0 else out

    def close(self, *args, **kwargs):
        self.__step = 0
        return


class TestLib():
    """
    Instanciate TestLib to enable some features to be able to run tests on a library for Cleep
    """

    def __init__(self):
        """
        Constructor
        """
        tools.install_trace_logging_level()

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
