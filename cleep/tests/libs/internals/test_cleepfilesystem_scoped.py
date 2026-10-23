#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest
import logging
import shutil
from unittest.mock import Mock, patch

from cleep.libs.tests.lib import TestLib
from cleep.libs.internals.cleepfilesystem import CleepFilesystem, ScopedCleepFilesystem
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()


class CleepFilesystemScopedTests(unittest.TestCase):
    def setUp(self):
        TestLib()
        logging.basicConfig(
            level=LOG_LEVEL,
            format="%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s",
        )
        self.tmp = tempfile.mkdtemp()
        self.storage = os.path.join(self.tmp, "storage")
        self.config = os.path.join(self.tmp, "etc", "app.conf")
        os.makedirs(self.storage)
        os.makedirs(os.path.dirname(self.config))
        self.parent = Mock(spec=CleepFilesystem)
        self.parent.crash_report = None
        self.parent.rw = Mock()
        self.parent.is_readonly_fs = False
        # Make isinstance checks work: use a real root instead of Mock
        self.root = CleepFilesystem()
        self.root.rw = Mock()
        self.root.is_readonly_fs = False
        self.root.open = Mock()
        self.root.write_data = Mock()
        self.root.write_json = Mock()
        self.root.copy = Mock()
        self.root.enable_write = Mock()
        self.scoped = self.root.scoped(
            "dummyapp",
            allowed_roots=[self.storage, self.config],
            policy=CleepFilesystem.POLICY_WARN,
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_scoped_returns_scoped_instance(self):
        self.assertIsInstance(self.scoped, ScopedCleepFilesystem)
        self.assertIsInstance(self.scoped, CleepFilesystem)
        self.assertTrue(self.scoped.underlying is self.root)
        self.assertEqual(self.scoped.path_policy, CleepFilesystem.POLICY_WARN)

    def test_is_path_under(self):
        self.assertTrue(
            CleepFilesystem.is_path_under(
                os.path.join(self.storage, "db.sqlite"), self.storage
            )
        )
        self.assertTrue(CleepFilesystem.is_path_under(self.storage, self.storage))
        self.assertFalse(
            CleepFilesystem.is_path_under(
                os.path.join(self.tmp, "other", "x"), self.storage
            )
        )
        self.assertTrue(CleepFilesystem.is_path_under(self.config, self.config))

    def test_write_inside_allowed_no_warning(self):
        path = os.path.join(self.storage, "data.bin")
        with patch.object(self.scoped.logger, "warning") as warn:
            self.scoped.write_data(path, "x")
            warn.assert_not_called()
        self.root.write_data.assert_called_with(path, "x", None)

    def test_write_outside_warns_and_continues(self):
        path = os.path.join(self.tmp, "escape.txt")
        with patch.object(self.scoped.logger, "warning") as warn:
            self.scoped.write_data(path, "x")
            warn.assert_called()
            self.assertIn("outside allowed dirs", warn.call_args[0][0])
        self.root.write_data.assert_called_with(path, "x", None)

    def test_write_outside_deny_raises(self):
        scoped = self.root.scoped(
            "dummyapp",
            allowed_roots=[self.storage],
            policy=CleepFilesystem.POLICY_DENY,
        )
        path = os.path.join(self.tmp, "escape.txt")
        with self.assertRaises(PermissionError):
            scoped.write_data(path, "x")
        self.root.write_data.assert_not_called()

    def test_open_read_outside_allowed(self):
        path = "/etc/hostname"
        self.scoped.open(path, "r")
        self.root.open.assert_called_with(path, "r", None)

    def test_open_write_outside_warns(self):
        path = os.path.join(self.tmp, "escape.txt")
        with patch.object(self.scoped.logger, "warning") as warn:
            self.scoped.open(path, "w")
            warn.assert_called()
        self.root.open.assert_called_with(path, "w", None)

    def test_copy_checks_destination_only(self):
        src = "/tmp/download.bin"
        dst = os.path.join(self.storage, "download.bin")
        with patch.object(self.scoped.logger, "warning") as warn:
            self.scoped.copy(src, dst)
            warn.assert_not_called()
        self.root.copy.assert_called_with(src, dst)

    def test_enable_write_forwards_to_parent(self):
        self.scoped.enable_write(root=True)
        self.root.enable_write.assert_called_with(root=True, boot=False)

    def test_invalid_policy(self):
        with self.assertRaises(ValueError):
            self.root.scoped("x", policy="nope")

    def test_nested_scoped_uses_root_parent(self):
        nested = self.scoped.scoped(
            "other",
            allowed_roots=[self.storage],
            policy=CleepFilesystem.POLICY_WARN,
        )
        self.assertTrue(nested.underlying is self.root)


if __name__ == "__main__":
    # pragma: no cover
    unittest.main()
