#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace("tests/", ""))
from cleepfilesystem import CleepFilesystem
from cleep.libs.tests.lib import TestLib
from cleep.exception import InvalidParameter
import unittest
import logging
from unittest.mock import Mock, patch
import time
import io
import json
import shutil
from distutils import dir_util
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()


class MockFd:
    def __init__(self, content):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *args, **kargs):
        pass

    def readlines(self):
        return self.content.split("\n")


class CleepFilesystemTestsReadonly(unittest.TestCase):

    FSTAB = """proc            /proc           proc    defaults          0       0
    PARTUUID=c7cb7e34-01  /boot           vfat    defaults,%(value)s          0       2
    PARTUUID=c7cb7e34-02  /               ext4    defaults,noatime,%(value)s  0       1
    # a swapfile is not a swap partition, no line here
    # #   use  dphys-swapfile swap[on|off]  for that
    # tmpfs /var/log tmpfs nodev,nosuid 0 0
    # tmpfs /var/tmp tmpfs nodev,nosuid 0 0
    # tmpfs /tmp tmpfs nodev,nosuid 0 0"""

    def setUp(self):
        logging.basicConfig(
            level=LOG_LEVEL,
            format="%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s",
        )
        TestLib()
        io = Mock()

    def tearDown(self):
        pass

    def test_is_readonly_filesystem_true(self):
        io.open = Mock(return_value=MockFd(self.FSTAB % {"value": "ro"}))

        c = CleepFilesystem()
        self.assertTrue(c.is_readonly_fs)

    def test_is_readonly_filesystem_false(self):
        io.open = Mock(return_value=MockFd(self.FSTAB % {"value": "rw"}))

        c = CleepFilesystem()
        self.assertFalse(c.is_readonly_fs)


class CleepFilesystemTests(unittest.TestCase):

    FILE = "test.tmp"

    def setUp(self):
        TestLib()
        logging.basicConfig(
            level=LOG_LEVEL,
            format="%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s",
        )

        self.c = CleepFilesystem()
        self.c.DEBOUNCE_DURATION = 0.5
        self.c.rw = Mock()
        self.c.rw.enable_write_on_root = Mock(return_value=True)
        self.c.rw.disable_write_on_root = Mock(return_value=True)
        self.c.rw.enable_write_on_boot = Mock(return_value=True)
        self.c.rw.disable_write_on_boot = Mock(return_value=True)

    def tearDown(self):
        if os.path.exists(self.FILE):
            os.remove(self.FILE)

    def test_enable_write(self):
        self.c.enable_write()

        self.assertTrue(self.c.rw.enable_write_on_root.called)
        self.assertFalse(self.c.rw.disable_write_on_root.called)
        self.assertFalse(self.c.rw.enable_write_on_boot.called)
        self.assertFalse(self.c.rw.disable_write_on_boot.called)

    def test_enable_write_all_false(self):
        self.c.enable_write(False, False)

        self.assertFalse(self.c.rw.enable_write_on_root.called)
        self.assertFalse(self.c.rw.enable_write_on_boot.called)

    def test_enable_write_called_multiple_times(self):
        self.c.enable_write()
        self.c.enable_write()
        self.c.enable_write()

        self.assertTrue(self.c.rw.enable_write_on_root.called_once)
        self.assertFalse(self.c.rw.disable_write_on_root.called)
        self.assertFalse(self.c.rw.enable_write_on_boot.called)
        self.assertFalse(self.c.rw.disable_write_on_boot.called)

    def test_enable_write_only_boot(self):
        self.c.enable_write(True, False)

        self.assertTrue(self.c.rw.enable_write_on_root.called)
        self.assertFalse(self.c.rw.disable_write_on_root.called)
        self.assertFalse(self.c.rw.enable_write_on_boot.called)
        self.assertFalse(self.c.rw.disable_write_on_boot.called)

    def test_enable_write_only_root(self):
        self.c.enable_write(False, True)

        self.assertFalse(self.c.rw.enable_write_on_root.called)
        self.assertFalse(self.c.rw.disable_write_on_root.called)
        self.assertTrue(self.c.rw.enable_write_on_boot.called)
        self.assertFalse(self.c.rw.disable_write_on_boot.called)

    def test_disable_write(self):
        self.c.enable_write()
        self.c.disable_write()
        time.sleep(self.c.DEBOUNCE_DURATION + 0.5)

        self.assertTrue(self.c.rw.enable_write_on_root.called)
        self.assertTrue(self.c.rw.disable_write_on_root.called)
        self.assertFalse(self.c.rw.enable_write_on_boot.called)
        self.assertFalse(self.c.rw.disable_write_on_boot.called)

    def test_disable_write_all_false(self):
        self.c.enable_write(False, False)
        self.c.disable_write(False, False)
        time.sleep(self.c.DEBOUNCE_DURATION + 0.5)

        self.assertFalse(self.c.rw.disable_write_on_root.called)
        self.assertFalse(self.c.rw.disable_write_on_boot.called)

    def test_disable_write_called_multiple_times(self):
        self.c.enable_write(True, True)
        self.c.disable_write(True, True)
        # should trigger warning about bug
        self.c.disable_write(True, True)
        time.sleep(self.c.DEBOUNCE_DURATION + 1)

        self.assertTrue(self.c.rw.enable_write_on_root.called)
        self.assertTrue(self.c.rw.disable_write_on_root.called_once)
        self.assertTrue(self.c.rw.enable_write_on_boot.called)
        self.assertTrue(self.c.rw.disable_write_on_boot.called_once)

    def test_disable_write_only_root(self):
        self.c.enable_write(True, False)
        self.c.disable_write(True, False)
        time.sleep(self.c.DEBOUNCE_DURATION + 0.5)

        self.assertTrue(self.c.rw.enable_write_on_root.called)
        self.assertTrue(self.c.rw.disable_write_on_root.called)
        self.assertFalse(self.c.rw.enable_write_on_boot.called)
        self.assertFalse(self.c.rw.disable_write_on_boot.called)

    def test_disable_write_only_boot(self):
        self.c.enable_write(False, True)
        self.c.disable_write(False, True)
        time.sleep(self.c.DEBOUNCE_DURATION + 0.5)

        self.assertFalse(self.c.rw.enable_write_on_root.called)
        self.assertFalse(self.c.rw.disable_write_on_root.called)
        self.assertTrue(self.c.rw.enable_write_on_boot.called)
        self.assertTrue(self.c.rw.disable_write_on_boot.called)

    def test_enable_disable_write(self):
        self.c.enable_write()
        time.sleep(0.5)
        self.c.disable_write()
        time.sleep(self.c.DEBOUNCE_DURATION + 0.5)

        self.assertTrue(self.c.rw.enable_write_on_root.called)
        self.assertTrue(self.c.rw.disable_write_on_root.called)
        self.assertFalse(self.c.rw.enable_write_on_boot.called)
        self.assertFalse(self.c.rw.disable_write_on_boot.called)

    def test_enable_disable_write_check_timer_renewing(self):
        self.c.DEBOUNCE_DURATION = 2.0
        self.c.enable_write(True, True)
        time.sleep(0.5)
        self.c.disable_write(True, True)
        time.sleep(0.5)
        self.c.enable_write(True, True)
        time.sleep(0.5)
        self.c.disable_write(True, True)
        counter = 0
        while not self.c.rw.disable_write_on_root.called:
            counter += 1
            time.sleep(0.25)
        self.assertGreaterEqual(counter, 7)  # it should be 8 (2.0/0.25=8)

    def test_crash_report(self):
        self.assertIsNone(self.c.crash_report)
        self.c.set_crash_report(Mock())
        self.assertIsNotNone(self.c.crash_report)
        self.assertTrue(self.c.rw.set_crash_report.called)

    def test_open_text(self):
        try:
            self.c.is_readonly_fs = True
            fd = self.c.open(self.FILE, "w")
            self.assertTrue(os.path.exists(self.FILE))
            self.assertTrue(self.c.rw.enable_write_on_root.called)
            self.assertTrue(isinstance(fd, io.TextIOWrapper))
        finally:
            self.c.close(fd)

    def test_open_binary(self):
        try:
            self.c.is_readonly_fs = True
            fd = self.c.open(self.FILE, "wb")
            self.assertTrue(os.path.exists(self.FILE))
            self.assertTrue(self.c.rw.enable_write_on_root.called)
            self.assertTrue(isinstance(fd, io.BufferedIOBase))
        finally:
            self.c.close(fd)

    def test_open_exception(self):
        io_open_original = io.open
        try:
            self.c.is_readonly_fs = True
            io.open = Mock(side_effect=Exception("Test exception"))
            with self.assertRaises(Exception) as cm:
                self.c.open(self.FILE, "w")
            self.assertEqual(str(cm.exception), "Test exception")
            time.sleep(self.c.DEBOUNCE_DURATION + 0.5)
            self.assertTrue(self.c.rw.disable_write_on_root.called)
        finally:
            io.open = io_open_original

    def test_close(self):
        self.c.is_readonly_fs = True
        fd = self.c.open(self.FILE, "w")
        self.c.close(fd)
        time.sleep(self.c.DEBOUNCE_DURATION + 0.5)
        self.assertTrue(self.c.rw.disable_write_on_root.called)

    def test_close_exception(self):
        try:
            self.c.is_readonly_fs = True
            fd = self.c.open(self.FILE, "w")
            close_restore = fd.close
            fd.close = Mock(side_effect=Exception("Test exception"))
            with self.assertRaises(Exception) as cm:
                self.c.close(fd)
            self.assertEqual(str(cm.exception), "Test exception")
            time.sleep(self.c.DEBOUNCE_DURATION + 0.5)
            self.assertTrue(self.c.rw.disable_write_on_root.called)
        finally:
            fd.close = close_restore
            self.c.close(fd)

    def test_write_data(self):
        self.c.is_readonly_fs = True
        self.assertTrue(self.c.write_data(self.FILE, "write_data test"))
        with io.open(self.FILE, "r") as fd:
            content = fd.read()
            self.assertEqual("write_data test", content.strip())
        time.sleep(self.c.DEBOUNCE_DURATION + 0.5)
        self.assertTrue(self.c.rw.disable_write_on_root.called)

    def test_write_data_invalid_parameters(self):
        with self.assertRaises(InvalidParameter) as cm:
            self.c.write_data(self.FILE, 666)
        self.assertEqual(str(cm.exception), "Data must be string")

    def test_write_data_exception(self):
        self.c.open = Mock(side_effect=Exception("Test exception"))
        self.c.set_crash_report(Mock())

        self.assertFalse(self.c.write_data(self.FILE, "test"))
        # can't test disable_write_on_root because we trigger exception during open function call, so no fd available to close
        # self.assertTrue(self.c.rw.disable_write_on_root.called)
        self.assertTrue(self.c.crash_report.report_exception.called)

    def test_read_data(self):
        with io.open(self.FILE, "w") as fd:
            fd.write("read_data test")
        lines = self.c.read_data(self.FILE)
        self.assertTrue(isinstance(lines, list))

    def test_read_data_with_non_existing_file(self):
        self.c.set_crash_report(Mock())

        # file does not exist
        self.assertIsNone(self.c.read_data(self.FILE))
        self.assertTrue(self.c.crash_report.report_exception.called)

    def test_read_json(self):
        with io.open(self.FILE, "w") as fd:
            fd.write('{"test": "read_json"}')
        lines = self.c.read_json(self.FILE)
        logging.debug("Read lines: %s", lines)
        self.assertTrue(isinstance(lines, dict))
        self.assertTrue("test" in lines)

    def test_read_json_exception(self):
        self.c.set_crash_report(Mock())
        with io.open(self.FILE, "w") as fd:
            fd.write('{"test": "read_json"}')
        json_loads_original = json.loads
        json.loads = Mock(side_effect=Exception("Test exception"))

        try:
            self.assertIsNone(self.c.read_json(self.FILE))
        finally:
            json.loads = json_loads_original
        self.assertTrue(self.c.crash_report.report_exception.called)

    def test_write_json(self):
        self.c.is_readonly_fs = True
        self.assertTrue(self.c.write_json(self.FILE, {"test": "write_json"}))
        time.sleep(self.c.DEBOUNCE_DURATION + 0.5)
        self.assertTrue(self.c.rw.disable_write_on_root.called)
        with io.open(self.FILE, "r") as fd:
            self.assertEqual('{\n    "test": "write_json"\n}', fd.read().strip())

    def test_rename(self):
        with io.open(self.FILE, "w") as fd:
            fd.write("test")
        try:
            self.assertTrue(self.c.rename(self.FILE, "renamed.tmp"))
            self.assertTrue(os.path.exists("renamed.tmp"))
        finally:
            if os.path.exists("renamed.tmp"):
                os.remove("renamed.tmp")

    def test_rename_exception(self):
        self.c.set_crash_report(Mock())
        with io.open(self.FILE, "w") as fd:
            fd.write('{"test": "read_json"}')
        shutil_move_original = shutil.move
        shutil.move = Mock(side_effect=Exception("Test exception"))
        self.c.is_readonly_fs = True

        try:
            self.assertFalse(self.c.rename(self.FILE, "renamed.tmp"))
        finally:
            shutil.move = shutil_move_original
        self.assertTrue(self.c.crash_report.report_exception.called)
        time.sleep(self.c.DEBOUNCE_DURATION + 0.5)
        self.assertTrue(self.c.rw.disable_write_on_root.called)

    def test_copy(self):
        with io.open(self.FILE, "w") as fd:
            fd.write('{"test": "read_json"}')
        try:
            self.assertTrue(self.c.copy(self.FILE, "copied.tmp"))
            self.assertTrue(os.path.exists("copied.tmp"))
        finally:
            if os.path.exists("copied.tmp"):
                os.remove("copied.tmp")

    def test_copy_exception(self):
        self.c.set_crash_report(Mock())
        with io.open(self.FILE, "w") as fd:
            fd.write('{"test": "read_json"}')
        shutil_copy2_original = shutil.copy2
        shutil.copy2 = Mock(side_effect=Exception("Test exception"))
        self.c.is_readonly_fs = True

        try:
            self.assertFalse(self.c.copy(self.FILE, "copied.tmp"))
        finally:
            shutil.copy2 = shutil_copy2_original
        self.assertTrue(self.c.crash_report.report_exception.called)
        time.sleep(self.c.DEBOUNCE_DURATION + 0.5)
        self.assertTrue(self.c.rw.disable_write_on_root.called)

    def test_copy_dir(self):
        try:
            os.mkdir("test")
            with io.open("test/%s" % self.FILE, "w") as fd:
                fd.write("test")
            self.assertTrue(os.path.exists("test"))
            self.assertTrue(os.path.exists("test/%s" % self.FILE))

            self.assertTrue(self.c.copy_dir("test", "copied_test"))
            self.assertTrue(os.path.exists("copied_test"))
            self.assertTrue(os.path.exists("copied_test/%s" % self.FILE))
        finally:
            if os.path.exists("copied_test/%s" % self.FILE):
                os.remove("copied_test/%s" % self.FILE)
            if os.path.exists("copied_test"):
                os.removedirs("copied_test")
            if os.path.exists("test/%s" % self.FILE):
                os.remove("test/%s" % self.FILE)
            if os.path.exists("test"):
                os.removedirs("test")

    def test_copy_dir_exception(self):
        dir_util_copy_tree_original = dir_util.copy_tree
        try:
            self.c.is_readonly_fs = True
            self.c.set_crash_report(Mock())
            os.mkdir("test")
            with io.open("test/%s" % self.FILE, "w") as fd:
                fd.write("test")
            self.assertTrue(os.path.exists("test"))
            self.assertTrue(os.path.exists("test/%s" % self.FILE))
            dir_util.copy_tree = Mock(side_effect=Exception("Test exception"))

            self.assertFalse(self.c.copy_dir("test", "copied_test"))
            self.assertFalse(os.path.exists("copied_test"))
        finally:
            dir_util.copy_tree = dir_util_copy_tree_original
            if os.path.exists("copied_test/%s" % self.FILE):
                os.remove("copied_test/%s" % self.FILE)
            if os.path.exists("copied_test"):
                os.removedirs("copied_test")
            if os.path.exists("test/%s" % self.FILE):
                os.remove("test/%s" % self.FILE)
            if os.path.exists("test"):
                os.removedirs("test")
        self.assertTrue(self.c.crash_report.report_exception.called)
        time.sleep(self.c.DEBOUNCE_DURATION + 0.5)
        self.assertTrue(self.c.rw.disable_write_on_root.called)

    def test_ln(self):
        with io.open(self.FILE, "w") as fd:
            fd.write("test")
        try:
            self.assertTrue(self.c.ln(self.FILE, "test.lnk"))
            self.assertTrue(os.path.exists("test.lnk"))
            self.assertTrue(os.path.islink("test.lnk"))
        finally:
            if os.path.exists("test.lnk"):
                os.remove("test.lnk")

    def test_ln_with_existing_link(self):
        with io.open(self.FILE, "w") as fd:
            fd.write("test")
        os.system("ln -s /etc/fstab test.lnk")

        try:
            self.assertTrue(self.c.ln(self.FILE, "test.lnk", True))
            self.assertTrue(os.path.exists("test.lnk"))
            self.assertTrue(os.path.islink("test.lnk"))
            with io.open("test.lnk", "r") as fd:
                self.assertEqual("test", fd.read().strip())
        finally:
            if os.path.exists("test.lnk"):
                os.remove("test.lnk")

    def test_ln_exception(self):
        self.c.set_crash_report(Mock())
        os_symlink_original = os.symlink
        os.symlink = Mock(side_effect=Exception("Test exception"))
        with io.open(self.FILE, "w") as fd:
            fd.write("test")
        self.c.is_readonly_fs = True

        try:
            self.assertFalse(self.c.ln(self.FILE, "test.lnk"))
        finally:
            os.symlink = os_symlink_original

        self.assertTrue(self.c.crash_report.report_exception.called)
        time.sleep(self.c.DEBOUNCE_DURATION + 0.5)
        self.assertTrue(self.c.rw.disable_write_on_root.called)

    def test_rm(self):
        with io.open(self.FILE, "w") as fd:
            fd.write("test")

        self.assertTrue(self.c.rm(self.FILE))
        self.assertFalse(os.path.exists(self.FILE))

    def test_rm_exception(self):
        self.c.set_crash_report(Mock())
        with io.open(self.FILE, "w") as fd:
            fd.write("test")
        os_remove_original = os.remove
        os.remove = Mock(side_effect=Exception("Test exception"))
        self.c.is_readonly_fs = True

        try:
            self.assertFalse(self.c.rm(self.FILE))
            self.assertTrue(os.path.exists(self.FILE))
        finally:
            os.remove = os_remove_original
        self.assertTrue(self.c.crash_report.report_exception.called)
        time.sleep(self.c.DEBOUNCE_DURATION + 0.5)
        self.assertTrue(self.c.rw.disable_write_on_root.called)

    def test_remove(self):
        with io.open(self.FILE, "w") as fd:
            fd.write("test")

        self.assertTrue(self.c.remove(self.FILE))
        self.assertFalse(os.path.exists(self.FILE))

    def test_rm_dir(self):
        try:
            os.mkdir("test")
            with io.open("test/%s" % self.FILE, "w") as fd:
                fd.write("test")
            self.assertTrue(os.path.exists("test"))
            self.assertTrue(os.path.exists("test/%s" % self.FILE))

            self.assertTrue(self.c.rmdir("test"))
            self.assertFalse(os.path.exists("test"))
        finally:
            if os.path.exists("test"):
                shutil.rmtree("test")

    def test_rm_dir_exception(self):
        self.c.set_crash_report(Mock())
        with io.open(self.FILE, "w") as fd:
            fd.write("test")
        shutil_rmtree_original = shutil.rmtree
        shutil.rmtree = Mock(side_effect=Exception("Test exception"))
        self.c.is_readonly_fs = True

        try:
            os.mkdir("test")
            with io.open("test/%s" % self.FILE, "w") as fd:
                fd.write("test")
            self.assertTrue(os.path.exists("test"))
            self.assertTrue(os.path.exists("test/%s" % self.FILE))

            self.assertFalse(self.c.rmdir("test"))
            self.assertTrue(os.path.exists("test"))
        finally:
            shutil.rmtree = shutil_rmtree_original
            if os.path.exists("test"):
                shutil.rmtree("test")

        self.assertTrue(self.c.crash_report.report_exception.called)
        time.sleep(self.c.DEBOUNCE_DURATION + 0.5)
        self.assertTrue(self.c.rw.disable_write_on_root.called)

    def test_mkdir(self):
        try:
            self.c.is_readonly_fs = True
            self.assertTrue(self.c.mkdir("test"))
            self.assertTrue(os.path.exists("test"))
            self.assertTrue(os.path.isdir("test"))
            self.assertTrue(self.c.rw.disable_on_root_called)
        finally:
            if os.path.exists("test"):
                shutil.rmtree("test")

    def test_mkdir_exists(self):
        self.c.mkdir("test")
        self.assertFalse(self.c.mkdir("test"))
        if os.path.exists("test"):
            shutil.rmtree("test")

    def test_mkdir_recursive(self):
        try:
            self.assertTrue(self.c.mkdirs("test/sub"))
            self.assertTrue(os.path.exists("test"))
            self.assertTrue(os.path.exists("test/sub"))
            self.assertTrue(os.path.isdir("test/sub"))
        finally:
            if os.path.exists("test"):
                shutil.rmtree("test")

    def test_mkdir_not_recursive_while_should(self):
        try:
            self.assertFalse(self.c.mkdir("test/sub", False))
            self.assertFalse(os.path.exists("test"))
        finally:
            if os.path.exists("test"):
                shutil.rmtree("test")

    def test_mkdir_exception(self):
        os_mkdir_original = os.mkdir
        os.mkdir = Mock(side_effect=Exception("Test exception"))
        try:
            self.assertFalse(self.c.mkdir("test"))
            self.assertFalse(os.path.exists("test"))
        finally:
            os.mkdir = os_mkdir_original
            if os.path.exists("test"):
                shutil.rmtree("test")

    def test_mkdir_exception_recursive(self):
        os_makedirs_original = os.makedirs
        os.makedirs = Mock(side_effect=Exception("Test exception"))
        try:
            self.assertFalse(self.c.mkdirs("test"))
            self.assertFalse(os.path.exists("test"))
        finally:
            os.makedirs = os_makedirs_original
            if os.path.exists("test"):
                shutil.rmtree("test")

    def test_exists_path_exists(self):
        with patch("cleepfilesystem.os.path.exists") as exists_mock:
            exists_mock.return_value = True
            res = self.c.exists("a/path")
            self.assertTrue(res)

    def test_exists_path_not_exists(self):
        with patch("cleepfilesystem.os.path.exists") as exists_mock:
            exists_mock.return_value = False
            res = self.c.exists("a/path")
            self.assertFalse(res)

    @patch("cleepfilesystem.Console")
    def test_rsync(self, mock_console):
        self.c._CleepFilesystem__enable_write = Mock()
        self.c._CleepFilesystem__disable_write = Mock()
        mock_console.return_value.command.return_value = {"returncode": 0}

        res = self.c.rsync("src", "dst")

        self.assertTrue(res)
        mock_console.return_value.command.assert_called_with(
            '/usr/bin/rsync -ah --delete --exclude=".*" src dst'
        )

    @patch("cleepfilesystem.Console")
    def test_rsync_command_failed(self, mock_console):
        self.c._CleepFilesystem__enable_write = Mock()
        self.c._CleepFilesystem__disable_write = Mock()
        mock_console.return_value.command.return_value = {
            "returncode": 1,
            "stdout": [],
            "stderr": [],
            "error": False,
            "killed": False,
        }

        res = self.c.rsync("src", "dst")

        self.assertFalse(res)

    @patch("cleepfilesystem.Console")
    def test_rsync_enable_disable_writings(self, mock_console):
        self.c._CleepFilesystem__enable_write = Mock()
        self.c._CleepFilesystem__disable_write = Mock()
        self.c.is_readonly_fs = True
        mock_console.return_value.command.return_value = {"returncode": 0}

        res = self.c.rsync("src", "dst")

        self.assertTrue(res)
        self.c._CleepFilesystem__enable_write.assert_called()
        self.c._CleepFilesystem__disable_write.assert_called()

    @patch("cleepfilesystem.Console")
    def test_rsync_exception(self, mock_console):
        self.c._CleepFilesystem__enable_write = Mock()
        self.c._CleepFilesystem__disable_write = Mock()
        self.c.is_readonly_fs = True
        mock_console.return_value.command.side_effect = Exception("Shell error")
        crash_report = Mock()
        self.c.set_crash_report(crash_report)

        res = self.c.rsync("src", "dst")

        self.assertFalse(res)
        self.c._CleepFilesystem__enable_write.assert_called()
        self.c._CleepFilesystem__disable_write.assert_called()
        crash_report.report_exception.assert_called_with(
            {
                "message": 'Exception executing rsync command "/usr/bin/rsync -ah --delete --exclude=".*" src dst"',
                "options": '-ah --delete --exclude=".*"',
                "src": "src",
                "dst": "dst",
            }
        )


if __name__ == "__main__":
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_cleepfilesystem.py; coverage report -m -i
    unittest.main()
