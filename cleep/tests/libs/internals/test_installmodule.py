#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from installmodule import InstallModule, UninstallModule, UpdateModule, Download, Context, PATH_FRONTEND
import cleep.libs.internals.download
from cleep.libs.internals.installdeb import InstallDeb
from cleep.libs.tests.lib import TestLib
from cleep.exception import MissingParameter, InvalidParameter
import unittest
import logging
import time
from unittest.mock import Mock, patch, MagicMock
import subprocess
import tempfile
from threading import Timer
from cleep.libs.internals.cleepfilesystem import CleepFilesystem
import shutil
import cleep

INSTALL_DIR = cleep.__file__.replace('__init__.py', '')

class UninstallModuleTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format='%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

    def tearDown(self):
        pass

    def _init_context(self, module_name='module', module_infos=None, update_process=False, cleep_filesystem_copy_side_effect=None,
            cleep_filesystem_open_side_effect=None, callback_side_effect=None, force_uninstall=False, cleep_filesystem_rm_side_effect=None,
            cleep_filesystem_rmdir_side_effect=None):
        self.crash_report = Mock()
        self.cleep_filesystem = Mock()
        if cleep_filesystem_copy_side_effect:
            self.cleep_filesystem.copy.side_effect = cleep_filesystem_copy_side_effect
        if cleep_filesystem_open_side_effect:
            self.cleep_filesystem.open.side_effect = cleep_filesystem_open_side_effect
        if cleep_filesystem_rm_side_effect:
            self.cleep_filesystem.rm.side_effect = cleep_filesystem_rm_side_effect
        if cleep_filesystem_rmdir_side_effect:
            self.cleep_filesystem.rmdir.side_effect = cleep_filesystem_rmdir_side_effect

        if module_infos is None:
            module_infos = self._get_module_infos()

        self.callback = Mock(side_effect=callback_side_effect)

        self.u = UninstallModule(module_name, module_infos, update_process, force_uninstall, self.callback, self.cleep_filesystem, self.crash_report)
        self.u.cleep_path = '/testinstall'
        self.c = Context()
        self.c.force_uninstall = force_uninstall
        self.c.module_log = None
        self.c.install_dir = 'dummy'

    def _init_console_mock(self, console_mock, return_code=0, killed=False, timeout=0.5, stdout='message on stdout', stderr='message on stderr'):
        def init():
            init_args = console_mock.call_args[0]
            logging.debug('console_mock constructor args: %s' % str(init_args))
            path, cb, end_cb, exec_dir = init_args

            # call script terminated
            cb(stdout, stderr)

            time.sleep(timeout)

            # call script terminated
            end_cb(return_code, killed)
            
        t = Timer(timeout, init)
        t.start()

    def _get_module_infos(self):
        return {
            "category": "APPLICATION",
            "description": "description",
            "tags": ["tag1", "tag2"],
            "country": None,
            "price": 0,
            "author": "Cleep",
            "changelog": "First official release",
            "deps": [],
            "longdescription": "long description",
            "version": "1.0.0",
            "urls": {
                "info": None,
                "bugs": None,
                "site": None,
                "help": None
            },
            "icon": "icon",
            "certified": True,
            "note": -1,
            "download": "https://www.google.com",
            "sha256": "f5723bae112c217f6b1be26445ce5ffda9ad7701276bcb1ea1ae9bc7232e1926"
        }

    @patch('installmodule.os')
    @patch('installmodule.EndlessConsole')
    def test_run_script_preuninst(self, console_mock, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.exists.return_value = True

        self._init_context()
        self._init_console_mock(console_mock)

        self.assertTrue(self.u._run_script(self.c, 'preuninst.sh'))
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['prescript']['returncode'], 0)
        self.assertEqual(status['prescript']['stdout'], ['message on stdout'])
        self.assertEqual(status['prescript']['stderr'], ['message on stderr'])
        self.assertEqual(status['postscript']['returncode'], None)
        self.assertEqual(status['postscript']['stdout'], [])
        self.assertEqual(status['postscript']['stderr'], [])

    @patch('installmodule.os')
    @patch('installmodule.EndlessConsole')
    def test_run_script_postuninst(self, console_mock, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.exists.return_value = True

        self._init_context()
        self._init_console_mock(console_mock)

        self.assertTrue(self.u._run_script(self.c, 'postuninst.sh'))
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['prescript']['returncode'], None)
        self.assertEqual(status['prescript']['stdout'], [])
        self.assertEqual(status['prescript']['stderr'], [])
        self.assertEqual(status['postscript']['returncode'], 0)
        self.assertEqual(status['postscript']['stdout'], ['message on stdout'])
        self.assertEqual(status['postscript']['stderr'], ['message on stderr'])

    @patch('installmodule.os')
    @patch('installmodule.EndlessConsole')
    def test_run_script_preuninst_killed(self, console_mock, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.exists.return_value = True

        self._init_context()
        self._init_console_mock(console_mock, killed=True)

        self.assertFalse(self.u._run_script(self.c, 'preuninst.sh'))
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['prescript']['returncode'], 130)
        self.assertEqual(status['prescript']['stdout'], ['message on stdout'])
        self.assertEqual(status['prescript']['stderr'], ['message on stderr'])
        self.assertEqual(status['postscript']['returncode'], None)
        self.assertEqual(status['postscript']['stdout'], [])
        self.assertEqual(status['postscript']['stderr'], [])
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installmodule.os')
    @patch('installmodule.EndlessConsole')
    def test_run_script_postuninst_killed(self, console_mock, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.exists.return_value = True

        self._init_context()
        self._init_console_mock(console_mock, killed=True)

        self.assertFalse(self.u._run_script(self.c, 'postuninst.sh'))
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['prescript']['returncode'], None)
        self.assertEqual(status['prescript']['stdout'], [])
        self.assertEqual(status['prescript']['stderr'], [])
        self.assertEqual(status['postscript']['returncode'], 130)
        self.assertEqual(status['postscript']['stdout'], ['message on stdout'])
        self.assertEqual(status['postscript']['stderr'], ['message on stderr'])
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installmodule.os')
    def test_run_script_no_script(self, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.exists.return_value = False

        self._init_context()

        self.assertTrue(self.u._run_script(self.c, 'preuninst.sh'))

    @patch('installmodule.os')
    def test_run_script_exception(self, os_mock):
        os_mock.path.join.side_effect = Exception('Test exception')

        self._init_context()

        self.assertFalse(self.u._run_script(self.c, 'preuninst.sh'))
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(len(status['process']), 1)
        self.assertTrue(status['process'][0].find('Exception occured during "preuninst.sh" script execution of module "module"')>=0)
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installmodule.os')
    def test_remove_installed_files(self, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.dirname = os.path.dirname
        os_mock.path.exists.return_value = True
        fd = Mock()
        fd.readlines.return_value = [
            'testinstall/modules/module/module.py',
            'testinstall/modules/module/__init__.py',
            '',
            '/opt/cleep/html/js/modules/module/desc.json',
            '/opt/cleep/html/js/modules/module/module.config.js',
            '/opt/cleep/html/js/modules/module/module.config.html'
        ]
        self._init_context(cleep_filesystem_open_side_effect=[fd])

        self.assertTrue(self.u._remove_installed_files(self.c))
        self.assertEqual(self.cleep_filesystem.rm.call_count, 5)
        self.assertEqual(self.cleep_filesystem.rmdir.call_count, 2)

    @patch('installmodule.os')
    def test_remove_installed_files_no_log_file(self, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.dirname = os.path.dirname
        os_mock.path.exists.return_value = False
        self._init_context()

        self.assertFalse(self.u._remove_installed_files(self.c))
        self.assertEqual(self.cleep_filesystem.rm.call_count, 0)
        self.assertEqual(self.cleep_filesystem.rmdir.call_count, 0)
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['process'][1], 'Install log file "/opt/cleep/install/module/module.log" for module "module" was not found')

    @patch('installmodule.os')
    def test_remove_installed_files_no_log_file_force_uninstall(self, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.dirname = os.path.dirname
        os_mock.path.exists.return_value = False
        self._init_context(force_uninstall=True)

        # should returns True event if file does not exist in force mode to continue uninstallation
        self.assertTrue(self.u._remove_installed_files(self.c))
        self.assertEqual(self.cleep_filesystem.rm.call_count, 0)
        self.assertEqual(self.cleep_filesystem.rmdir.call_count, 0)
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['process'][1], 'Install log file "/opt/cleep/install/module/module.log" for module "module" was not found')

    @patch('installmodule.os')
    def test_remove_installed_files_exception(self, os_mock):
        os_mock.path.join.side_effect = Exception('Test exception')
        self._init_context()

        self.assertFalse(self.u._remove_installed_files(self.c))
        self.assertEqual(self.cleep_filesystem.rm.call_count, 0)
        self.assertEqual(self.cleep_filesystem.rmdir.call_count, 0)

    @patch('installmodule.os')
    def test_remove_installed_files_exception_force_uninstall(self, os_mock):
        os_mock.path.join.side_effect = Exception('Test exception')
        self._init_context(force_uninstall=True)

        self.assertTrue(self.u._remove_installed_files(self.c))
        self.assertEqual(self.cleep_filesystem.rm.call_count, 0)
        self.assertEqual(self.cleep_filesystem.rmdir.call_count, 0)

    @patch('installmodule.os')
    def test_remove_installed_files_rm_failed(self, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.dirname = os.path.dirname
        os_mock.path.exists.return_value = True
        fd = Mock()
        fd.readlines.return_value = [
            'testinstall/modules/module/module.py',
            'testinstall/modules/module/__init__.py',
            '/opt/cleep/html/js/modules/module/desc.json',
            '/opt/cleep/html/js/modules/module/module.config.js',
            '/opt/cleep/html/js/modules/module/module.config.html'
        ]
        self._init_context(cleep_filesystem_open_side_effect=[fd], cleep_filesystem_rm_side_effect=[True, True, False, True, True])

        self.assertTrue(self.u._remove_installed_files(self.c))
        self.assertEqual(self.cleep_filesystem.rm.call_count, 5)
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['process'][1], 'Unable to remove file "/opt/cleep/html/js/modules/module/desc.json" during module "module" uninstallation')

    @patch('installmodule.os')
    def test_remove_installed_files_file_doesnt_exist(self, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.dirname = os.path.dirname
        os_mock.path.exists.side_effect = [True, True, True, False, True, False, True, True]
        fd = Mock()
        fd.readlines.return_value = [
            'testinstall/modules/module/module.py',
            'testinstall/modules/module/__init__.py',
            '/opt/cleep/html/js/modules/module/desc.json',
            '/opt/cleep/html/js/modules/module/module.config.js',
            '/opt/cleep/html/js/modules/module/module.config.html'
        ]
        self._init_context(cleep_filesystem_open_side_effect=[fd])

        self.assertTrue(self.u._remove_installed_files(self.c))
        self.assertEqual(self.cleep_filesystem.rm.call_count, 3)
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['process'][1], 'Unable to remove file "/opt/cleep/html/js/modules/module/desc.json" that does not exist during module "module" uninstallation')
        self.assertEqual(status['process'][2], 'Unable to remove file "/opt/cleep/html/js/modules/module/module.config.html" that does not exist during module "module" uninstallation')

    @patch('installmodule.os')
    def test_remove_installed_files_file_doesnt_exist(self, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.dirname = os.path.dirname
        os_mock.path.exists.side_effect = [True, True, True, False, True, False, True, True]
        fd = Mock()
        fd.readlines.return_value = [
            'testinstall/modules/module/module.py',
            'testinstall/modules/module/__init__.py',
            '/opt/cleep/html/js/modules/module/desc.json',
            '/opt/cleep/html/js/modules/module/module.config.js',
            '/opt/cleep/html/js/modules/module/module.config.html'
        ]
        self._init_context(cleep_filesystem_open_side_effect=[fd])

        self.assertTrue(self.u._remove_installed_files(self.c))
        self.assertEqual(self.cleep_filesystem.rm.call_count, 3)
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['process'][1], 'Unable to remove file "/opt/cleep/html/js/modules/module/desc.json" that does not exist during module "module" uninstallation')
        self.assertEqual(status['process'][2], 'Unable to remove file "/opt/cleep/html/js/modules/module/module.config.html" that does not exist during module "module" uninstallation')

    @patch('installmodule.Tools')
    @patch('installmodule.os')
    def test_remove_installed_files_core_library(self, os_mock, tools_mock):
        os_mock.path.join = os.path.join
        os_mock.path.dirname = os.path.dirname
        os_mock.path.exists.return_value = True
        tools_mock.is_core_lib.side_effect = [True, False, True, False, True]
        fd = Mock()
        fd.readlines.return_value = [
            'testinstall/modules/module/module.py',
            'testinstall/modules/module/__init__.py',
            '/opt/cleep/html/js/modules/module/desc.json',
            '/opt/cleep/html/js/modules/module/module.config.js',
            '/opt/cleep/html/js/modules/module/module.config.html'
        ]
        self._init_context(cleep_filesystem_open_side_effect=[fd])

        self.assertTrue(self.u._remove_installed_files(self.c))
        self.assertEqual(self.cleep_filesystem.rm.call_count, 2)
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['process'][1], 'Trying to remove core library file "testinstall/modules/module/module.py" during module "module" uninstallation. Drop deletion.')
        self.assertEqual(status['process'][2], 'Trying to remove core library file "/opt/cleep/html/js/modules/module/desc.json" during module "module" uninstallation. Drop deletion.')
        self.assertEqual(status['process'][3], 'Trying to remove core library file "/opt/cleep/html/js/modules/module/module.config.html" during module "module" uninstallation. Drop deletion.')

    @patch('installmodule.os')
    def test_remove_installed_files_clearing_path_failed(self, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.dirname = os.path.dirname
        os_mock.path.exists.return_value = True
        fd = Mock()
        fd.readlines.return_value = [
            'testinstall/modules/module/module.py',
            'testinstall/modules/module/__init__.py',
            '/opt/cleep/html/js/modules/module/desc.json',
            '/opt/cleep/html/js/modules/module/module.config.js',
            '/opt/cleep/html/js/modules/module/module.config.html'
        ]
        self._init_context(cleep_filesystem_open_side_effect=[fd], cleep_filesystem_rmdir_side_effect=[False, True])

        self.assertTrue(self.u._remove_installed_files(self.c))
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['process'][1], 'Unable to remove directory "testinstall/modules/module" during module "module" uninstallation')

    @patch('installmodule.os')
    def test_run(self, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.exists.return_value = True
        self._init_context()
        def dummy_function(*args, **kwargs):
            args[0].module_log = '/tmp/dummy.log'
            args[0].install_dir = '/tmp'
            return True
        self.u._run_script = Mock(side_effect=[True, True])
        self.u._remove_installed_files = dummy_function

        self.u.run()
        while self.u.is_uninstalling():
            time.sleep(0.25)
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['status'], UninstallModule.STATUS_UNINSTALLED)
        self.assertTrue(self.callback.called)
        self.assertTrue(self.cleep_filesystem.enable_write.called)
        self.assertTrue(self.cleep_filesystem.disable_write.called)
        self.assertFalse(self.crash_report.report_exception.called)

    def test_run_local_module(self):
        module_infos = self._get_module_infos()
        module_infos['local'] = True
        self._init_context(module_infos=module_infos)
        self.u._run_script = Mock(side_effect=[True, True])
        self.u._remove_installed_files = Mock(return_value=True)

        self.u.run()
        while self.u.is_uninstalling():
            time.sleep(0.25)
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['status'], UninstallModule.STATUS_UNINSTALLED)
        self.assertTrue(self.callback.called)
        self.assertTrue(self.cleep_filesystem.enable_write.called)
        self.assertTrue(self.cleep_filesystem.disable_write.called)
        self.assertFalse(self.crash_report.report_exception.called)

    def test_run_prescript_failed(self):
        self._init_context()
        self.u._run_script = Mock(side_effect=[False, True])
        self.u._remove_installed_files = Mock(return_value=True)

        self.u.run()
        while self.u.is_uninstalling():
            time.sleep(0.25)
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['status'], UninstallModule.STATUS_ERROR_PREUNINST)
        self.assertTrue(self.callback.called)
        self.assertTrue(self.cleep_filesystem.enable_write.called)
        self.assertTrue(self.cleep_filesystem.disable_write.called)
        self.assertFalse(self.crash_report.report_exception.called)

    def test_run_remove_installed_files_failed(self):
        self._init_context()
        self.u._run_script = Mock(side_effect=[True, True])
        self.u._remove_installed_files = Mock(return_value=False)

        self.u.run()
        while self.u.is_uninstalling():
            time.sleep(0.25)
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['status'], UninstallModule.STATUS_ERROR_REMOVE)
        self.assertTrue(self.callback.called)
        self.assertTrue(self.cleep_filesystem.enable_write.called)
        self.assertTrue(self.cleep_filesystem.disable_write.called)
        self.assertFalse(self.crash_report.report_exception.called)

    def test_run_postscript_failed(self):
        self._init_context()
        self.u._run_script = Mock(side_effect=[True, False])
        self.u._remove_installed_files = Mock(return_value=True)

        self.u.run()
        while self.u.is_uninstalling():
            time.sleep(0.25)
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['status'], UninstallModule.STATUS_ERROR_POSTUNINST)
        self.assertTrue(self.callback.called)
        self.assertTrue(self.cleep_filesystem.enable_write.called)
        self.assertTrue(self.cleep_filesystem.disable_write.called)
        self.assertFalse(self.crash_report.report_exception.called)

    def test_run_exception(self):
        self._init_context()
        self.u._run_script = Mock(side_effect=Exception('Test exception'))
        self.u._remove_installed_files = Mock(return_value=True)

        self.u.run()
        while self.u.is_uninstalling():
            time.sleep(0.25)
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['status'], UninstallModule.STATUS_ERROR_INTERNAL)
        self.assertTrue(self.callback.called)
        self.assertTrue(self.cleep_filesystem.enable_write.called)
        self.assertTrue(self.cleep_filesystem.disable_write.called)
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installmodule.os')
    def test_run_clean_exception(self, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.exists.return_value = True
        self._init_context(cleep_filesystem_rmdir_side_effect=Exception('Test exception'))
        def dummy_function(*args, **kwargs):
            args[0].module_log = '/tmp/dummy.log'
            return True
        self.u._run_script = Mock(side_effect=[True, True])
        self.u._remove_installed_files = dummy_function

        self.u.run()
        while self.u.is_uninstalling():
            time.sleep(0.25)
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['status'], UninstallModule.STATUS_UNINSTALLED)
        self.assertTrue(self.callback.called)
        self.assertTrue(self.cleep_filesystem.enable_write.called)
        self.assertTrue(self.cleep_filesystem.disable_write.called)
        self.assertTrue(self.crash_report.report_exception.called)
        self.assertEqual(status['process'][1], 'Exception occured during "module" uninstall cleaning')





class UninstallModuleFunctionalTests(unittest.TestCase):

    def setUp(self):
        t = TestLib(self)
        t.set_functional_tests()
        logging.basicConfig(level=logging.FATAL, format='%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.url_archive = 'https://github.com/tangb/cleep/raw/master/cleepos/tests/resources/installmodule/%s.zip'
        self.module_infos = {
            "description": "Test",
            "author": "Cleep",
            "country": None,
            "price": 0,
            "tags": [],
            "deps": [],
            "version": "1.0.0",
            "urls": {
                "info": None,
                "bugs": None,
                "site": None,
                "help": None
            },
            "icon": "message-processing",
            "download": None,
            "sha256": None
        }
        self.cleep_filesystem = CleepFilesystem()
        self.cleep_filesystem.enable_write()
        self.crash_report = Mock()

    def tearDown(self):
        if os.path.exists('/tmp/preinst.tmp'):
            os.remove('/tmp/preinst.tmp')
        if os.path.exists('/tmp/postinst.tmp'):
            os.remove('/tmp/postinst.tmp')
        if os.path.exists('/tmp/preuninst.tmp'):
            os.remove('/tmp/preuninst.tmp')
        if os.path.exists('/tmp/postuninst.tmp'):
            os.remove('/tmp/postuninst.tmp')
        if os.path.exists('/opt/cleep/install/test/'):
            shutil.rmtree('/opt/cleep/install/test/', ignore_errors=True)
        if os.path.exists(os.path.join(INSTALL_DIR, 'modules/test')):
            shutil.rmtree(os.path.join('modules/test'), ignore_errors=True)
        if os.path.exists('/opt/cleep/html/js/modules/test'):
            shutil.rmtree('/opt/cleep/html/js/modules/test', igore_errors=True)

    def callback(self, status):
        pass

    def test_uninstall_ok(self):
        #install
        name = 'cleepmod_test_1.0.0.ok'
        self.module_infos['download'] = self.url_archive % name
        self.module_infos['sha256'] = '5a522882b74f990ba0175808f52540bd1c1bcfe258873f83fc9e90e85d64a8f4'
        i = InstallModule('test', self.module_infos, False, self.callback, self.cleep_filesystem, self.crash_report)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.is_installing():
            time.sleep(0.25)
        self.assertEqual(i.get_status()['status'], i.STATUS_INSTALLED)

        #check installation
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertTrue(os.path.exists('/opt/cleep/install/test/test.log'))
        self.assertTrue(os.path.exists('/opt/cleep/install/test/preuninst.sh'))
        self.assertTrue(os.path.exists('/opt/cleep/install/test/postuninst.sh'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

        #uninstall module
        u = UninstallModule('test', self.module_infos, False, False, self.callback, self.cleep_filesystem, self.crash_report)
        u.start()
        time.sleep(0.5)

        #wait until end of uninstall
        while u.is_uninstalling():
            time.sleep(0.25)
        self.assertEqual(u.get_status()['status'], u.STATUS_UNINSTALLED)

        #check uninstallation
        self.assertFalse(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/')))
        self.assertTrue(os.path.exists('/opt/cleep/install/test/'))
        self.assertFalse(os.path.exists('/opt/cleep/install/test/preuninst.sh'))
        self.assertFalse(os.path.exists('/opt/cleep/install/test/postuninst.sh'))

    def test_uninstall_without_script_ok(self):
        #install
        name = 'cleepmod_test_1.0.0.noscript-ok'
        self.module_infos['download'] = self.url_archive % name
        self.module_infos['sha256'] = '0b43bcff0e4dc88f4e24261913bd118cb53c9c9a82ab1a61b053477615421da7'
        i = InstallModule('test', self.module_infos, False, self.callback, self.cleep_filesystem, self.crash_report)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.is_installing():
            time.sleep(0.25)
        self.assertEqual(i.get_status()['status'], i.STATUS_INSTALLED)

        #check installation
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertTrue(os.path.exists('/opt/cleep/install/test/test.log'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

        #uninstall module
        u = UninstallModule('test', self.module_infos, False, False, self.callback, self.cleep_filesystem, self.crash_report)
        u.start()
        time.sleep(0.5)

        #wait until end of uninstall
        while u.is_uninstalling():
            time.sleep(0.5)
        self.assertEqual(u.get_status()['status'], u.STATUS_UNINSTALLED)

        #check uninstallation
        self.assertFalse(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertFalse(os.path.exists('/opt/cleep/install/test/test.log'))

    def test_uninstall_ko_preuninst(self):
        #install
        name = 'cleepmod_test_1.0.0.preuninst-ko'
        self.module_infos['download'] = self.url_archive % name
        self.module_infos['sha256'] = '0565957885fb6438bfbeeb44e54f7ec66bb0144d196e9243bfd8e452b3e22853'
        i = InstallModule('test', self.module_infos, False, self.callback, self.cleep_filesystem, self.crash_report)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.is_installing():
            time.sleep(0.25)
        self.assertEqual(i.get_status()['status'], i.STATUS_INSTALLED)

        #check installation
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertTrue(os.path.exists('/opt/cleep/install/test/test.log'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

        #uninstall module
        u = UninstallModule('test', self.module_infos, False, False, self.callback, self.cleep_filesystem, self.crash_report)
        u.start()
        time.sleep(0.5)

        #wait until end of uninstall
        while u.is_uninstalling():
            time.sleep(0.25)
        self.assertEqual(u.get_status()['status'], u.STATUS_ERROR_PREUNINST)

        #check uninstallation
        self.assertFalse(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        # keep install log file if preuninst failed
        self.assertTrue(os.path.exists('/opt/cleep/install/test/test.log'))

    def test_uninstall_ko_postuninst(self):
        #install
        name = 'cleepmod_test_1.0.0.postuninst-ko'
        self.module_infos['download'] = self.url_archive % name
        self.module_infos['sha256'] = '0b7a48ca0c39926915a22213fccc871064b5e8e5054e4095d0b9b4c14ce39493'
        i = InstallModule('test', self.module_infos, False, self.callback, self.cleep_filesystem, self.crash_report)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.is_installing():
            time.sleep(0.25)
        self.assertEqual(i.get_status()['status'], i.STATUS_INSTALLED)

        #check installation
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertTrue(os.path.exists('/opt/cleep/install/test/test.log'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

        #uninstall module
        u = UninstallModule('test', self.module_infos, False, False, self.callback, self.cleep_filesystem, self.crash_report)
        u.start()
        time.sleep(0.5)

        #wait until end of uninstall
        while u.is_uninstalling():
            time.sleep(0.25)
        self.assertEqual(u.get_status()['status'], u.STATUS_ERROR_POSTUNINST)

        #check uninstallation
        self.assertFalse(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/')))
        self.assertTrue(os.path.exists('/opt/cleep/install/test/'))

    def test_uninstall_ko_remove(self):
        #install
        name = 'cleepmod_test_1.0.0.postuninst-ko'
        self.module_infos['download'] = self.url_archive % name
        self.module_infos['sha256'] = '0b7a48ca0c39926915a22213fccc871064b5e8e5054e4095d0b9b4c14ce39493'
        i = InstallModule('test', self.module_infos, False, self.callback, self.cleep_filesystem, self.crash_report)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()['status']==i.STATUS_INSTALLING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()['status'], i.STATUS_INSTALLED)

        #check installation
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertTrue(os.path.exists('/opt/cleep/install/test/test.log'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

        #remove installed file to simulate error
        os.remove('/opt/cleep/install/test/test.log')

        #uninstall module
        u = UninstallModule('test', self.module_infos, False, False, self.callback, self.cleep_filesystem, self.crash_report)
        u.start()
        time.sleep(0.5)

        #wait until end of uninstall
        while u.get_status()['status']==u.STATUS_UNINSTALLING:
            time.sleep(0.5)
        self.assertEqual(u.get_status()['status'], u.STATUS_ERROR_REMOVE)

        #check uninstallation
        self.assertFalse(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/')))
        self.assertTrue(os.path.exists('/opt/cleep/install/test/'))






class InstallModuleTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format='%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

    def tearDown(self):
        pass

    def _init_context(self, module_name='module', module_infos=None, update_process=False, cleep_filesystem_copy_side_effect=None,
            cleep_filesystem_open_side_effect=None, callback_side_effect=None):
        self.crash_report = Mock()
        self.cleep_filesystem = Mock()
        if cleep_filesystem_copy_side_effect:
            self.cleep_filesystem.copy.side_effect = cleep_filesystem_copy_side_effect
        if cleep_filesystem_open_side_effect:
            self.cleep_filesystem.open.side_effect = cleep_filesystem_open_side_effect

        if module_infos is None:
            module_infos = self._get_module_infos()

        self.callback = Mock(side_effect=callback_side_effect)

        self.i = InstallModule(module_name, module_infos, update_process, self.callback, self.cleep_filesystem, self.crash_report)
        self.i.cleep_path = '/testinstall'
        self.c = Context()
        self.c.archive_path = None
        self.c.extract_path = None

    def _init_download_mock(self, download_mock, download_file_return_value=None, download_file_side_effect=None,
            download_get_status_return_value=None):
        download_mock.return_value.STATUS_ERROR = 3
        download_mock.return_value.STATUS_ERROR_INVALIDSIZE = 4
        download_mock.return_value.STATUS_ERROR_BADCHECKSUM = 5
        download_mock.return_value.STATUS_CANCELED = 7

        if download_file_side_effect:
            download_mock.return_value.download_file.side_effect = download_file_side_effect
        else:
            status = download_get_status_return_value if download_get_status_return_value else 6 # STATUS_DONE
            download_mock.return_value.download_file.return_value = (status, download_file_return_value)
        if download_get_status_return_value:
            download_mock.return_value.get_status.return_value = download_get_status_return_value

    def _init_console_mock(self, console_mock, return_code=0, killed=False, timeout=0.5, stdout='message on stdout', stderr='message on stderr'):
        def init():
            init_args = console_mock.call_args[0]
            logging.debug('console_mock constructor args: %s' % list(init_args))
            path, cb, end_cb, exec_dir = init_args

            # call script terminated
            cb(stdout, stderr)

            time.sleep(timeout)

            # call script terminated
            end_cb(return_code, killed)
            
        t = Timer(timeout, init)
        t.start()

    def _get_module_infos(self):
        return {
            "category": "APPLICATION",
            "description": "description",
            "tags": ["tag1", "tag2"],
            "country": None,
            "price": 0,
            "author": "Cleep",
            "changelog": "First official release",
            "deps": [],
            "longdescription": "long description",
            "version": "1.0.0",
            "urls": {
                "info": None,
                "bugs": None,
                "site": None,
                "help": None
            },
            "icon": "icon",
            "certified": True,
            "note": -1,
            "download": "https://www.google.com",
            "sha256": "f5723bae112c217f6b1be26445ce5ffda9ad7701276bcb1ea1ae9bc7232e1926"
        }

    @patch('installmodule.Download')
    def test_download_archive(self, download_mock):
        self._init_download_mock(download_mock, download_file_return_value='/tmp/dummy.zip')
        self._init_context()
        
        self.assertTrue(self.i._download_archive(self.c))
        self.assertEqual(self.c.archive_path, '/tmp/dummy.zip')
        self.assertFalse(self.crash_report.report_exception.called)

    @patch('installmodule.Download')
    def test_download_archive_failed_internal_error(self, download_mock):
        self._init_download_mock(download_mock, download_get_status_return_value=3)
        self._init_context()
        
        self.assertFalse(self.i._download_archive(self.c))
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(len(status['process']), 1)
        self.assertTrue(status['process'][0].startswith('Error'))
        self.assertTrue(status['process'][0].find('internal error')>=0)
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installmodule.Download')
    def test_download_archive_failed_invalid_filesize(self, download_mock):
        self._init_download_mock(download_mock, download_get_status_return_value=4)
        self._init_context()
        
        self.assertFalse(self.i._download_archive(self.c))
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(len(status['process']), 1)
        self.assertTrue(status['process'][0].startswith('Error'))
        self.assertTrue(status['process'][0].find('invalid filesize')>=0)
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installmodule.Download')
    def test_download_archive_failed_bad_checksum(self, download_mock):
        self._init_download_mock(download_mock, download_get_status_return_value=5)
        self._init_context()
        
        self.assertFalse(self.i._download_archive(self.c))
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(len(status['process']), 1)
        self.assertTrue(status['process'][0].startswith('Error'))
        self.assertTrue(status['process'][0].find('invalid checksum')>=0)
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installmodule.Download')
    def test_download_archive_failed_unknown_error(self, download_mock):
        self._init_download_mock(download_mock, download_get_status_return_value=7)
        self._init_context()
        
        self.assertFalse(self.i._download_archive(self.c))
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(len(status['process']), 1)
        self.assertTrue(status['process'][0].startswith('Error'))
        self.assertTrue(status['process'][0].find('unknown error')>=0)
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installmodule.Download')
    def test_download_archive_failed_exception(self, download_mock):
        self._init_download_mock(download_mock, download_file_side_effect=Exception('Test exception'))
        self._init_context()
        
        self.assertFalse(self.i._download_archive(self.c))
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(len(status['process']), 1)
        self.assertTrue(status['process'][0].startswith('Exception'))
        self.assertTrue(status['process'][0].find('Exception occured during module "module" archive download')>=0)
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installmodule.ZipFile')
    def test_extract_archive(self, zip_mock):
        self._init_context()
        self.c.archive_path = '/tmp/dummy.zip'

        self.assertTrue(self.i._extract_archive(self.c))
        zip_mock.assert_called_with(self.c.archive_path, 'r')
        self.assertTrue('extract_path' in dir(self.c))
        self.assertTrue(self.c.extract_path.startswith('/tmp'))

    @patch('installmodule.ZipFile')
    def test_extract_archive_exception(self, zip_mock):
        self._init_context()
        self.c.archive_path = '/tmp/dummy.zip'
        zip_obj = MagicMock()
        zip_obj.extractall.side_effect = Exception('Test exception')
        zip_obj.__enter__.return_value = zip_obj
        zip_mock.return_value = zip_obj

        self.assertFalse(self.i._extract_archive(self.c))
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(len(status['process']), 1)
        self.assertTrue(status['process'][0].startswith('Exception'))
        self.assertTrue(status['process'][0].find('decompressing module "module" archive')>=0)
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installmodule.os')
    def test_backup_scripts(self, os_mock):
        os_mock.path.join = os.path.join

        self._init_context()
        self.c.archive_path = '/tmp/dummy/zip'
        self.c.extract_path = '/tmp/123456789'

        self.assertTrue(self.i._backup_scripts(self.c))
        self.cleep_filesystem.copy.assert_any_call('/tmp/123456789/scripts/preuninst.sh', '/opt/cleep/install/module/preuninst.sh')
        self.cleep_filesystem.copy.assert_any_call('/tmp/123456789/scripts/postuninst.sh', '/opt/cleep/install/module/postuninst.sh')

    @patch('installmodule.os')
    def test_backup_scripts_no_script(self, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.exists.return_value = False

        self._init_context()
        self.c.archive_path = '/tmp/dummy/zip'
        self.c.extract_path = '/tmp/123456789'

        self.assertTrue(self.i._backup_scripts(self.c))
        self.assertFalse(self.cleep_filesystem.copy.called)
        self.assertFalse(self.crash_report.report_exception.called)

    @patch('installmodule.os')
    def test_backup_scripts_exception(self, os_mock):
        os_mock.path.join.side_effect = Exception('Test exception')

        self._init_context()
        self.c.archive_path = '/tmp/dummy/zip'
        self.c.extract_path = '/tmp/123456789'

        self.assertFalse(self.i._backup_scripts(self.c))
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(len(status['process']), 1)
        self.assertTrue(status['process'][0].find('Exception saving module "module" scripts')>=0)
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installmodule.os')
    @patch('installmodule.EndlessConsole')
    def test_run_script_preinst(self, console_mock, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.exists.return_value = True

        self._init_context()
        self._init_console_mock(console_mock)
        self.c.archive_path = '/tmp/dummy/zip'
        self.c.extract_path = '/tmp/123456789'

        self.assertTrue(self.i._run_script(self.c, 'preinst.sh'))
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['prescript']['returncode'], 0)
        self.assertEqual(status['prescript']['stdout'], ['message on stdout'])
        self.assertEqual(status['prescript']['stderr'], ['message on stderr'])
        self.assertEqual(status['postscript']['returncode'], None)
        self.assertEqual(status['postscript']['stdout'], [])
        self.assertEqual(status['postscript']['stderr'], [])

    @patch('installmodule.os')
    @patch('installmodule.EndlessConsole')
    def test_run_script_postinst(self, console_mock, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.exists.return_value = True

        self._init_context()
        self._init_console_mock(console_mock)
        self.c.archive_path = '/tmp/dummy/zip'
        self.c.extract_path = '/tmp/123456789'

        self.assertTrue(self.i._run_script(self.c, 'postinst.sh'))
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['prescript']['returncode'], None)
        self.assertEqual(status['prescript']['stdout'], [])
        self.assertEqual(status['prescript']['stderr'], [])
        self.assertEqual(status['postscript']['returncode'], 0)
        self.assertEqual(status['postscript']['stdout'], ['message on stdout'])
        self.assertEqual(status['postscript']['stderr'], ['message on stderr'])

    @patch('installmodule.os')
    @patch('installmodule.EndlessConsole')
    def test_run_script_preinst_killed(self, console_mock, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.exists.return_value = True

        self._init_context()
        self._init_console_mock(console_mock, killed=True)
        self.c.archive_path = '/tmp/dummy/zip'
        self.c.extract_path = '/tmp/123456789'

        self.assertFalse(self.i._run_script(self.c, 'preinst.sh'))
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['prescript']['returncode'], 130)
        self.assertEqual(status['prescript']['stdout'], ['message on stdout'])
        self.assertEqual(status['prescript']['stderr'], ['message on stderr'])
        self.assertEqual(status['postscript']['returncode'], None)
        self.assertEqual(status['postscript']['stdout'], [])
        self.assertEqual(status['postscript']['stderr'], [])
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installmodule.os')
    @patch('installmodule.EndlessConsole')
    def test_run_script_postinst_killed(self, console_mock, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.exists.return_value = True

        self._init_context()
        self._init_console_mock(console_mock, killed=True)
        self.c.archive_path = '/tmp/dummy/zip'
        self.c.extract_path = '/tmp/123456789'

        self.assertFalse(self.i._run_script(self.c, 'postinst.sh'))
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['prescript']['returncode'], None)
        self.assertEqual(status['prescript']['stdout'], [])
        self.assertEqual(status['prescript']['stderr'], [])
        self.assertEqual(status['postscript']['returncode'], 130)
        self.assertEqual(status['postscript']['stdout'], ['message on stdout'])
        self.assertEqual(status['postscript']['stderr'], ['message on stderr'])
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installmodule.os')
    def test_run_script_no_script(self, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.exists.return_value = False

        self._init_context()
        self.c.archive_path = '/tmp/dummy/zip'
        self.c.extract_path = '/tmp/123456789'

        self.assertTrue(self.i._run_script(self.c, 'preinst.sh'))

    @patch('installmodule.os')
    def test_run_script_exception(self, os_mock):
        os_mock.path.join.side_effect = Exception('Test exception')

        self._init_context()
        self.c.archive_path = '/tmp/dummy/zip'
        self.c.extract_path = '/tmp/123456789'

        self.assertFalse(self.i._run_script(self.c, 'preinst.sh'))
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(len(status['process']), 1)
        self.assertTrue(status['process'][0].find('Exception occured during "preinst.sh" script execution of module "module"')>=0)
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installmodule.os')
    @patch('installmodule.Tools')
    def test_copy_module_files(self, tools_mock, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.exists.side_effect = [True, True, False, False]
        os_mock.walk.return_value = [
            ('backend/modules/module', [], ['module.py', '__init__.py']),
            ('frontend/js/modules/module', [], ['desc.json', 'module.config.js', 'module.config.html'])
        ]
        tools_mock.is_core_lib.return_value = False

        self._init_context()
        self.c.archive_path = '/tmp/dummy/zip'
        self.c.extract_path = '/tmp/123456789'
        self.c.install_log_fd = MagicMock()

        self.assertTrue(self.i._copy_module_files(self.c))
        logging.debug('cleep_fs calls: %s' % self.cleep_filesystem.mock_calls)
        self.assertEqual(self.cleep_filesystem.copy.call_count, 5) # 5 files in walk return value

    @patch('installmodule.os')
    @patch('installmodule.Tools')
    def test_copy_module_files_overwrite_existing_files(self, tools_mock, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.exists.side_effect = [True, True, True, True]
        os_mock.walk.return_value = [
            ('backend/modules/module', [], ['module.py', '__init__.py']),
            ('frontend/js/modules/module', [], ['desc.json', 'module.config.js', 'module.config.html'])
        ]
        tools_mock.is_core_lib.return_value = False

        self._init_context()
        self.c.archive_path = '/tmp/dummy/zip'
        self.c.extract_path = '/tmp/123456789'
        self.c.install_log_fd = MagicMock()

        self.assertTrue(self.i._copy_module_files(self.c))
        logging.debug('cleep_fs calls: %s' % self.cleep_filesystem.mock_calls)
        self.assertEqual(self.cleep_filesystem.copy.call_count, 5)

    @patch('installmodule.os')
    @patch('installmodule.Tools')
    def test_copy_module_files_dont_overwrite_core_libs(self, tools_mock, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.exists.side_effect = [True, True, True, False]
        os_mock.walk.return_value = [
            ('backend/modules/module', [], ['module.py', '__init__.py']),
            ('frontend/js/modules/module', [], ['desc.json', 'module.config.js', 'module.config.html'])
        ]
        tools_mock.is_core_lib.side_effect = [True, False]

        self._init_context()
        self.c.archive_path = '/tmp/dummy/zip'
        self.c.extract_path = '/tmp/123456789'
        self.c.install_log_fd = MagicMock()

        self.assertTrue(self.i._copy_module_files(self.c))
        logging.debug('cleep_fs calls: %s' % self.cleep_filesystem.mock_calls)
        self.assertEqual(self.cleep_filesystem.copy.call_count, 4)

    @patch('installmodule.os')
    @patch('installmodule.Tools')
    def test_copy_module_files_backend_file_copy_failed(self, tools_mock, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.exists.side_effect = [True, True, False, False]
        os_mock.walk.return_value = [
            ('backend/modules/module', [], ['module.py', '__init__.py']),
            ('frontend/js/modules/module', [], ['desc.json', 'module.config.js', 'module.config.html'])
        ]
        tools_mock.is_core_lib.return_value = False

        self._init_context(cleep_filesystem_copy_side_effect=[False])
        self.c.archive_path = '/tmp/dummy/zip'
        self.c.extract_path = '/tmp/123456789'
        self.c.install_log_fd = MagicMock()

        self.assertFalse(self.i._copy_module_files(self.c))
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(len(status['process']), 1)
        self.assertTrue(status['process'][0].startswith('Error copying file'))
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installmodule.os')
    @patch('installmodule.Tools')
    def test_copy_module_files_frontend_file_copy_failed(self, tools_mock, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.exists.side_effect = [True, True, False, False]
        os_mock.walk.return_value = [
            ('backend/modules/module', [], ['module.py', '__init__.py']),
            ('frontend/js/modules/module', [], ['desc.json', 'module.config.js', 'module.config.html'])
        ]
        tools_mock.is_core_lib.return_value = False

        self._init_context(cleep_filesystem_copy_side_effect=[True, True, False])
        self.c.archive_path = '/tmp/dummy/zip'
        self.c.extract_path = '/tmp/123456789'
        self.c.install_log_fd = MagicMock()

        self.assertFalse(self.i._copy_module_files(self.c))
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(len(status['process']), 1)
        self.assertTrue(status['process'][0].startswith('Error copying file'))
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installmodule.os')
    @patch('installmodule.Tools')
    def test_copy_module_files_drop_unwanted_files(self, tools_mock, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.exists.side_effect = [True, True, False, False]
        os_mock.walk.return_value = [
            ('backend/modules/module', [], ['module.py', '__init__.py']),
            ('frontend/js/modules/module', [], ['desc.json', 'module.config.js', 'module.config.html']),
            ('test/dummy', [], ['file.py']),
        ]
        tools_mock.is_core_lib.return_value = False

        self._init_context()
        self.c.archive_path = '/tmp/dummy/zip'
        self.c.extract_path = '/tmp/123456789'
        self.c.install_log_fd = MagicMock()

        self.assertTrue(self.i._copy_module_files(self.c))
        logging.debug('cleep_fs calls: %s' % self.cleep_filesystem.mock_calls)
        self.assertEqual(self.cleep_filesystem.copy.call_count, 5) # 5 files in walk return value

    @patch('installmodule.os')
    @patch('installmodule.Tools')
    def test_copy_module_files_exception(self, tools_mock, os_mock):
        os_mock.path.join = os.path.join
        os_mock.path.exists.side_effect = [True, True, False, False]
        os_mock.walk.side_effect = Exception('Test exception')

        self._init_context()
        self.c.archive_path = '/tmp/dummy/zip'
        self.c.extract_path = '/tmp/123456789'
        self.c.install_log_fd = MagicMock()

        self.assertFalse(self.i._copy_module_files(self.c))
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(len(status['process']), 1)
        self.assertTrue(status['process'][0].startswith('Exception occured during module "module" files copy'))
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('installmodule.os')
    def test_rollback_install(self, os_mock):
        fd = Mock()
        fd.readlines.return_value = [
            'testinstall/modules/module/module.py',
            'testinstall/modules/module/__init__.py',
            '/opt/cleep/html/js/modules/module/desc.json',
            '/opt/cleep/html/js/modules/module/module.config.js',
            '/opt/cleep/html/js/modules/module/module.config.html'
        ]
        self._init_context(cleep_filesystem_open_side_effect=[fd])
        self.c.install_log = '/tmp/install.log'

        self.i._rollback_install(self.c)
        logging.debug('Rm mock calls: %s' % self.cleep_filesystem.rm.mock_calls)
        self.assertEqual(self.cleep_filesystem.rm.call_count, 5)
        logging.debug('Rmdir mock calls: %s' % self.cleep_filesystem.rmdir_call_mocks)
        self.assertEqual(self.cleep_filesystem.rmdir.call_count, 1)
        self.assertFalse(self.crash_report.report_exception.called)

    @patch('installmodule.os')
    def test_rollback_install_exception(self, os_mock):
        self._init_context(cleep_filesystem_open_side_effect=Exception('Test exception'))
        self.c.install_log = '/tmp/install.log'

        self.i._rollback_install(self.c)
        logging.debug('Rm mock calls: %s' % self.cleep_filesystem.rm.mock_calls)
        self.assertEqual(self.cleep_filesystem.rm.call_count, 0)
        logging.debug('Rmdir mock calls: %s' % self.cleep_filesystem.rmdir_call_mocks)
        self.assertEqual(self.cleep_filesystem.rmdir.call_count, 0)

        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(len(status['process']), 1)
        self.assertTrue(status['process'][0].startswith('Exception ocurred during "module" module installation rollback'))
        self.assertTrue(self.crash_report.report_exception.called)

    def test_run(self):
        self._init_context()
        self.i._download_archive = Mock(return_value=True)
        def dummy_extract(*args, **kwargs):
            logging.debug('args: %s' % args)
            args[0].extract_path = '/tmp/dummy/'
            args[0].archive_path = '/tmp/dummy.zip'
            return True
        self.i._extract_archive = dummy_extract
        self.i._run_script = Mock(side_effect=[True, True])
        self.i._backup_scripts = Mock(return_value=True)
        self.i._copy_module_files = Mock(return_value=True)

        self.i.run()
        while self.i.is_installing():
            time.sleep(0.25)
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['status'], InstallModule.STATUS_INSTALLED)
        self.assertTrue(self.callback.called)
        self.assertTrue(self.cleep_filesystem.enable_write.called)
        self.assertTrue(self.cleep_filesystem.disable_write.called)
        self.assertFalse(self.crash_report.report_exception.called)

    def test_run_with_package(self):
        self._init_context()
        self.i._download_archive = Mock()
        def dummy_extract(*args, **kwargs):
            logging.debug('args: %s' % args)
            args[0].extract_path = '/tmp/dummy/'
            args[0].archive_path = '/tmp/dummy.zip'
            return True
        self.i._extract_archive = dummy_extract
        self.i._run_script = Mock(side_effect=[True, True])
        self.i._backup_scripts = Mock(return_value=True)
        self.i._copy_module_files = Mock(return_value=True)

        self.i.set_package('archive.zip')
        self.i.run()
        while self.i.is_installing():
            time.sleep(0.25)
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertFalse(self.i._download_archive.called)
        self.assertEqual(status['status'], InstallModule.STATUS_INSTALLED)
        self.assertTrue(self.callback.called)
        self.assertTrue(self.cleep_filesystem.enable_write.called)
        self.assertTrue(self.cleep_filesystem.disable_write.called)
        self.assertFalse(self.crash_report.report_exception.called)

    def test_run_cancel(self):
        self._init_context()
        self.i._download_archive = Mock(return_value=True)
        def dummy_cancel(*args, **kwargs):
            # force cancel in unusual way due to thread
            # that did not stop when cancel is called (but works
            # only with logging trace or debug enabled)
            self.i.cancel()
            return True
        self.i._extract_archive = Mock(return_value=True)
        self.i._run_script = dummy_cancel
        self.i._backup_scripts = Mock(return_value=True)
        self.i._copy_module_files = Mock(return_value=True)

        self.i.run()
        status = self.i.get_status()
        self.assertEqual(status['status'], InstallModule.STATUS_CANCELED)
        self.assertTrue(self.cleep_filesystem.enable_write.called)
        self.assertTrue(self.cleep_filesystem.disable_write.called)
        self.assertFalse(self.crash_report.report_exception.called)

    def test_run_exception(self):
        self._init_context()
        self.cleep_filesystem.mkdirs.side_effect = Exception('Test exception')

        self.i.run()
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['status'], InstallModule.STATUS_ERROR_INTERNAL)
        self.assertTrue(status['process'][1].startswith('Exception occured during module "module" installation'))
        self.assertTrue(self.cleep_filesystem.enable_write.called)
        self.assertTrue(self.cleep_filesystem.disable_write.called)
        self.assertTrue(self.crash_report.report_exception.called)

    def test_run_clean_exception(self):
        self._init_context()
        self.i._download_archive = Mock(return_value=True)
        def dummy_extract(*args, **kwargs):
            logging.debug('args: %s' % args)
            args[0].extract_path = '/tmp/dummy/'
            args[0].archive_path = '/tmp/dummy.zip'
            return True
        self.i._extract_archive = dummy_extract
        self.i._run_script = Mock(side_effect=[True, True])
        self.i._backup_scripts = Mock(return_value=True)
        self.i._copy_module_files = Mock(return_value=True)
        self.cleep_filesystem.close.side_effect = Exception('Test exception')

        self.i.run()
        while self.i.is_installing():
            time.sleep(0.25)
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['status'], InstallModule.STATUS_INSTALLED)
        self.assertTrue(self.callback.called)
        self.assertTrue(self.cleep_filesystem.enable_write.called)
        self.assertTrue(self.cleep_filesystem.disable_write.called)
        self.assertTrue(self.crash_report.report_exception.called)

    def test_run_download_archive_failed(self):
        self._init_context()
        self.i._download_archive = Mock(return_value=False)
        self.i._extract_archive = Mock(return_value=True)
        self.i._run_script = Mock(side_effect=[True, True])
        self.i._backup_scripts = Mock(return_value=True)
        self.i._copy_module_files = Mock(return_value=True)
        self.i._rollback_install = Mock()

        self.i.run()
        while self.i.is_installing():
            time.sleep(0.25)
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['status'], InstallModule.STATUS_ERROR_DOWNLOAD)
        self.assertTrue(self.i._rollback_install.called)
        self.assertTrue(self.cleep_filesystem.enable_write.called)
        self.assertTrue(self.cleep_filesystem.disable_write.called)

    def test_run_extract_archive_failed(self):
        self._init_context()
        self.i._download_archive = Mock(return_value=True)
        self.i._extract_archive = Mock(return_value=False)
        self.i._run_script = Mock(side_effect=[True, True])
        self.i._backup_scripts = Mock(return_value=True)
        self.i._copy_module_files = Mock(return_value=True)
        self.i._rollback_install = Mock()

        self.i.run()
        while self.i.is_installing():
            time.sleep(0.25)
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['status'], InstallModule.STATUS_ERROR_EXTRACT)
        self.assertTrue(self.i._rollback_install.called)
        self.assertTrue(self.cleep_filesystem.enable_write.called)
        self.assertTrue(self.cleep_filesystem.disable_write.called)

    def test_run_preinst_failed(self):
        self._init_context()
        self.i._download_archive = Mock(return_value=True)
        self.i._extract_archive = Mock(return_value=True)
        self.i._run_script = Mock(side_effect=[False, True])
        self.i._backup_scripts = Mock(return_value=True)
        self.i._copy_module_files = Mock(return_value=True)
        self.i._rollback_install = Mock()

        self.i.run()
        while self.i.is_installing():
            time.sleep(0.25)
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['status'], InstallModule.STATUS_ERROR_PREINST)
        self.assertTrue(self.i._rollback_install.called)
        self.assertTrue(self.cleep_filesystem.enable_write.called)
        self.assertTrue(self.cleep_filesystem.disable_write.called)

    def test_run_backup_scripts_failed(self):
        self._init_context()
        self.i._download_archive = Mock(return_value=True)
        self.i._extract_archive = Mock(return_value=True)
        self.i._run_script = Mock(side_effect=[True, True])
        self.i._backup_scripts = Mock(return_value=False)
        self.i._copy_module_files = Mock(return_value=True)
        self.i._rollback_install = Mock()

        self.i.run()
        while self.i.is_installing():
            time.sleep(0.25)
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['status'], InstallModule.STATUS_ERROR_BACKUP)
        self.assertTrue(self.i._rollback_install.called)
        self.assertTrue(self.cleep_filesystem.enable_write.called)
        self.assertTrue(self.cleep_filesystem.disable_write.called)

    def test_run_copy_module_files_failed(self):
        self._init_context()
        self.i._download_archive = Mock(return_value=True)
        self.i._extract_archive = Mock(return_value=True)
        self.i._run_script = Mock(side_effect=[True, True])
        self.i._backup_scripts = Mock(return_value=True)
        self.i._copy_module_files = Mock(return_value=False)
        self.i._rollback_install = Mock()

        self.i.run()
        while self.i.is_installing():
            time.sleep(0.25)
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['status'], InstallModule.STATUS_ERROR_COPY)
        self.assertTrue(self.i._rollback_install.called)
        self.assertTrue(self.cleep_filesystem.enable_write.called)
        self.assertTrue(self.cleep_filesystem.disable_write.called)

    def test_run_postinst_failed(self):
        self._init_context()
        self.i._download_archive = Mock(return_value=True)
        self.i._extract_archive = Mock(return_value=True)
        self.i._run_script = Mock(side_effect=[True, False])
        self.i._backup_scripts = Mock(return_value=True)
        self.i._copy_module_files = Mock(return_value=True)
        self.i._rollback_install = Mock()

        self.i.run()
        while self.i.is_installing():
            time.sleep(0.25)
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['status'], InstallModule.STATUS_ERROR_POSTINST)
        self.assertTrue(self.i._rollback_install.called)
        self.assertTrue(self.cleep_filesystem.enable_write.called)
        self.assertTrue(self.cleep_filesystem.disable_write.called)

    def test_run_callback_exception(self):
        self._init_context(callback_side_effect=Exception('Test exception'))
        self.i._download_archive = Mock(return_value=True)
        self.i._extract_archive = Mock(return_value=True)
        self.i._run_script = Mock(side_effect=[True, True])
        self.i._backup_scripts = Mock(return_value=True)
        self.i._copy_module_files = Mock(return_value=True)

        self.i.run()
        while self.i.is_installing():
            time.sleep(0.25)
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['status'], InstallModule.STATUS_INSTALLED)
        self.assertTrue(self.callback.called)
        self.assertTrue(self.cleep_filesystem.enable_write.called)
        self.assertTrue(self.cleep_filesystem.disable_write.called)

    def test_run_install_local_module(self):
        module_infos = self._get_module_infos()
        module_infos['local'] = True
        self._init_context(module_infos=module_infos)
        self.i._download_archive = Mock(return_value=True)
        self.i._extract_archive = Mock(return_value=True)
        self.i._run_script = Mock(side_effect=[True, True])
        self.i._backup_scripts = Mock(return_value=True)
        self.i._copy_module_files = Mock(return_value=True)

        self.i.run()
        while self.i.is_installing():
            time.sleep(0.25)
        status = self.i.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['status'], InstallModule.STATUS_INSTALLED)
        self.assertTrue(self.callback.called)
        self.assertTrue(self.cleep_filesystem.enable_write.called)
        self.assertTrue(self.cleep_filesystem.disable_write.called)






class InstallModuleFunctionalTests(unittest.TestCase):

    def setUp(self):
        t = TestLib(self)
        t.set_functional_tests()
        logging.basicConfig(level=logging.FATAL, format='%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.url_archive = 'https://github.com/tangb/cleep/raw/master/cleepos/tests/resources/installmodule/%s.zip'
        self.module_infos = {
            "description": "Test",
            "author": "Cleep",
            "country": None,
            "price": 0,
            "tags": [],
            "deps": [],
            "version": "1.0.0",
            "urls": {
                "info": None,
                "bugs": None,
                "site": None,
                "help": None
            },
            "icon": "message-processing",
            "download": None,
            "sha256": None
        }
        self.cleep_filesystem = CleepFilesystem()
        self.cleep_filesystem.enable_write()
        self.crash_report = Mock()

    def tearDown(self):
        if os.path.exists('/tmp/preinst.tmp'):
            os.remove('/tmp/preinst.tmp')
        if os.path.exists('/tmp/postinst.tmp'):
            os.remove('/tmp/postinst.tmp')
        if os.path.exists('/tmp/preuninst.tmp'):
            os.remove('/tmp/preuninst.tmp')
        if os.path.exists('/tmp/postuninst.tmp'):
            os.remove('/tmp/postuninst.tmp')
        if os.path.exists('/opt/cleep/install/test/'):
            shutil.rmtree('/opt/cleep/install/test/', ignore_errors=True)
        if os.path.exists(os.path.join(INSTALL_DIR, 'modules/test')):
            shutil.rmtree(os.path.join(INSTALL_DIR, 'modules/test'), ignore_errors=True)
        if os.path.exists('/opt/cleep/html/js/modules/test'):
            shutil.rmtree('/opt/cleep/html/js/modules/test', ignore_errors=True)

    def callback(self, status):
        pass

    def test_install_ok(self):
        #install
        name = 'cleepmod_test_1.0.0.ok'
        self.module_infos['download'] = self.url_archive % name
        self.module_infos['sha256'] = '5a522882b74f990ba0175808f52540bd1c1bcfe258873f83fc9e90e85d64a8f4'
        i = InstallModule('test', self.module_infos, False, self.callback, self.cleep_filesystem, self.crash_report)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.is_installing():
            time.sleep(0.25)
        self.assertEqual(i.get_status()['status'], i.STATUS_INSTALLED)

        #check installation
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertTrue(os.path.exists('/opt/cleep/install/test/test.log'))
        self.assertTrue(os.path.exists('/opt/cleep/install/test/preuninst.sh'))
        self.assertTrue(os.path.exists('/opt/cleep/install/test/postuninst.sh'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

    def test_install_ok_without_script(self):
        #install
        name = 'cleepmod_test_1.0.0.noscript-ok'
        self.module_infos['download'] = self.url_archive % name
        self.module_infos['sha256'] = '0b43bcff0e4dc88f4e24261913bd118cb53c9c9a82ab1a61b053477615421da7'
        i = InstallModule('test', self.module_infos, False, self.callback, self.cleep_filesystem, self.crash_report)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.is_installing():
            time.sleep(0.25)
        self.assertEqual(i.get_status()['status'], i.STATUS_INSTALLED)

        #check installation
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertTrue(os.path.exists('/opt/cleep/install/test/test.log'))
        self.assertFalse(os.path.exists('/opt/cleep/install/test/preuninst.sh'))
        self.assertFalse(os.path.exists('/opt/cleep/install/test/postuninst.sh'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

    def test_install_ko_checksum(self):
        #install
        name = 'cleepmod_test_1.0.0.ok'
        self.module_infos['download'] = self.url_archive % name
        #enter invalid checkum
        self.module_infos['sha256'] = '5a522882b74f990ba0175808f52540bd1c1bcfe258873f83fc9e90e85d64a8f'
        i = InstallModule('test', self.module_infos, False, self.callback, self.cleep_filesystem, self.crash_report)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.is_installing():
            time.sleep(0.25)
        self.assertEqual(i.get_status()['status'], i.STATUS_ERROR_DOWNLOAD)

        #check installation
        self.assertFalse(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertFalse(os.path.exists('/opt/cleep/install/test/test.log'))
        self.assertFalse(os.path.exists('/opt/cleep/install/test/preuninst.sh'))
        self.assertFalse(os.path.exists('/opt/cleep/install/test/postuninst.sh'))
        self.assertFalse(os.path.exists('/opt/cleep/install/test/'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

    def test_install_ko_preinst(self):
        #install
        name = 'cleepmod_test_1.0.0.preinst-ko'
        self.module_infos['download'] = self.url_archive % name
        self.module_infos['sha256'] = '7c96e007d2ecebcde543c2bbf7f810904976f1dae7a8bfce438807e5b30392a6'
        i = InstallModule('test', self.module_infos, False, self.callback, self.cleep_filesystem, self.crash_report)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.is_installing():
            time.sleep(0.25)
        self.assertEqual(i.get_status()['status'], i.STATUS_ERROR_PREINST)

        #check installation
        self.assertFalse(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertFalse(os.path.exists('/opt/cleep/install/test/test.log'))
        self.assertFalse(os.path.exists('/opt/cleep/install/test/preuninst.sh'))
        self.assertFalse(os.path.exists('/opt/cleep/install/test/postuninst.sh'))
        self.assertFalse(os.path.exists('/opt/cleep/install/test/'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

    def test_install_ko_postinst(self):
        #install
        name = 'cleepmod_test_1.0.0.postinst-ko'
        self.module_infos['download'] = self.url_archive % name
        self.module_infos['sha256'] = '31d04988811c1ab449278bce66d608d1fbbc9324b0d60dd260ce36a326b700b4'
        i = InstallModule('test', self.module_infos, False, self.callback, self.cleep_filesystem, self.crash_report)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.is_installing():
            time.sleep(0.25)
        self.assertEqual(i.get_status()['status'], i.STATUS_ERROR_POSTINST)

        #check installation
        self.assertFalse(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertFalse(os.path.exists('/opt/cleep/install/test.log'))
        self.assertFalse(os.path.exists('/opt/cleep/install/test/preuninst.sh'))
        self.assertFalse(os.path.exists('/opt/cleep/install/test/postuninst.sh'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)




class UpdateModuleTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format='%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

    def tearDown(self):
        pass

    def _init_context(self, module_name='module', new_module_infos=None, callback_side_effect=None, force_uninstall=False):
        self.crash_report = Mock()
        self.cleep_filesystem = Mock()

        if new_module_infos is None:
            new_module_infos = self._get_module_infos('2.0.0')

        self.status_callback = Mock(side_effect=callback_side_effect)

        self.u = UpdateModule(module_name, new_module_infos, force_uninstall, self.status_callback, self.cleep_filesystem, self.crash_report)

    def _init_install_mock(self, install_mock, timeout=1.5, get_status_return_value=None):
        class InstallContext():
            installing = True

        def end_of_install():
            InstallContext.installing = False

        def is_installing(*args, **kwargs):
            return InstallContext.installing

        install = Mock()
        install.is_installing = is_installing
        if get_status_return_value == None:
            get_status_return_value = {
                'status': 2
            }
        install.get_status.return_value = get_status_return_value
        install_mock.return_value = install
        install.STATUS_IDLE = 0
        install.STATUS_INSTALLING = 1
        install.STATUS_INSTALLED = 2
        install.STATUS_CANCELED = 3
        install.STATUS_ERROR_INTERNAL = 4
        install.STATUS_ERROR_DOWNLOAD = 5
        install.STATUS_ERROR_EXTRACT = 6
        install.STATUS_ERROR_PREINST = 7
        install.STATUS_ERROR_BACKUP = 8
        install.STATUS_ERROR_COPY = 9
        install.STATUS_ERROR_POSTINST = 10

        t = Timer(timeout, end_of_install)
        t.start()

    def _init_uninstall_mock(self, uninstall_mock, timeout=0.75, get_status_return_value=None, is_uninstalling_side_effect=None):
        class UninstallContext():
            uninstalling = True

        def end_of_uninstall():
            UninstallContext.uninstalling = False

        def is_uninstalling(*args, **kwargs):
            return UninstallContext.uninstalling

        uninstall = Mock()
        if is_uninstalling_side_effect:
            uninstall.is_uninstalling.side_effect = is_uninstalling_side_effect
        else:
            uninstall.is_uninstalling = is_uninstalling
        if get_status_return_value == None:
            get_status_return_value = {
                'status': 2
            }
        uninstall.get_status.return_value = get_status_return_value
        uninstall_mock.return_value = uninstall
        uninstall.STATUS_IDLE = 0
        uninstall.STATUS_UNINSTALLING = 1
        uninstall.STATUS_UNINSTALLED = 2
        uninstall.STATUS_ERROR_INTERNAL = 3
        uninstall.STATUS_ERROR_PREUNINST = 4
        uninstall.STATUS_ERROR_REMOVE = 5
        uninstall.STATUS_ERROR_POSTUNINST = 6

        t = Timer(timeout, end_of_uninstall)
        t.start()

    def _get_module_infos(self, version):
        return {
            "category": "APPLICATION",
            "description": "description",
            "tags": ["tag1", "tag2"],
            "country": None,
            "price": 0,
            "author": "Cleep",
            "changelog": "First official release",
            "deps": [],
            "longdescription": "long description",
            "version": version,
            "urls": {
                "info": None,
                "bugs": None,
                "site": None,
                "help": None
            },
            "icon": "icon",
            "certified": True,
            "note": -1,
            "download": "https://www.google.com",
            "sha256": "f5723bae112c217f6b1be26445ce5ffda9ad7701276bcb1ea1ae9bc7232e1926"
        }

    @patch('installmodule.InstallModule')
    @patch('installmodule.UninstallModule')
    def test_run(self, uninstall_mock, install_mock):
        uninstall_status = {
            'status': 2,
            'process': ['uninstall process message'],
            'stdout': ['uninstall message on stdout'],
            'stderr': ['uninstall message on stderr']
        }
        install_status = {
            'status': 2,
            'process': ['install process message2'],
            'stdout': ['install message on stdout'],
            'stderr': ['install message on stderr']
        }
        self._init_uninstall_mock(uninstall_mock, get_status_return_value=uninstall_status)
        self._init_install_mock(install_mock, get_status_return_value=install_status)
        self._init_context()

        self.u.run()
        while self.u.is_updating():
            time.sleep(0.25)
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['status'], UpdateModule.STATUS_UPDATED)
        self.assertEqual(status['install'], install_status)
        self.assertEqual(status['uninstall'], uninstall_status)

    @patch('installmodule.InstallModule')
    @patch('installmodule.UninstallModule')
    def test_run_uninstall_failed(self, uninstall_mock, install_mock):
        uninstall_status = {
            'status': 3,
            'process': ['uninstall process message'],
            'stdout': ['uninstall message on stdout'],
            'stderr': ['uninstall message on stderr']
        }
        install_status = {
            'status': 2,
            'process': ['install process message2'],
            'stdout': ['install message on stdout'],
            'stderr': ['install message on stderr']
        }
        self._init_uninstall_mock(uninstall_mock, get_status_return_value=uninstall_status)
        self._init_install_mock(install_mock, get_status_return_value=install_status)
        self._init_context()

        self.u.run()
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['status'], UpdateModule.STATUS_UPDATED)
        self.assertEqual(status['install'], install_status)
        self.assertEqual(status['uninstall'], uninstall_status)

    @patch('installmodule.InstallModule')
    @patch('installmodule.UninstallModule')
    def test_run_install_failed(self, uninstall_mock, install_mock):
        uninstall_status = {
            'status': 2,
            'process': ['uninstall process message'],
            'stdout': ['uninstall message on stdout'],
            'stderr': ['uninstall message on stderr']
        }
        install_status = {
            'status': 5,
            'process': ['install process message2'],
            'stdout': ['install message on stdout'],
            'stderr': ['install message on stderr']
        }
        self._init_uninstall_mock(uninstall_mock, get_status_return_value=uninstall_status)
        self._init_install_mock(install_mock, get_status_return_value=install_status)
        self._init_context()

        self.u.run()
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['status'], UpdateModule.STATUS_ERROR)
        self.assertEqual(status['install'], install_status)
        self.assertEqual(status['uninstall'], uninstall_status)

    @patch('installmodule.InstallModule')
    @patch('installmodule.UninstallModule')
    def test_run_exception(self, uninstall_mock, install_mock):
        uninstall_status = {
            'status': 2,
            'process': ['uninstall process message'],
            'stdout': ['uninstall message on stdout'],
            'stderr': ['uninstall message on stderr']
        }
        install_status = {
            'status': 2,
            'process': ['install process message2'],
            'stdout': ['install message on stdout'],
            'stderr': ['install message on stderr']
        }
        self._init_uninstall_mock(uninstall_mock, get_status_return_value=uninstall_status, is_uninstalling_side_effect=Exception('Test exception'))
        self._init_install_mock(install_mock, get_status_return_value=install_status)
        self._init_context()

        self.u.run()
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['status'], UpdateModule.STATUS_ERROR)
        self.assertEqual(status['install'], install_status)
        self.assertEqual(status['uninstall'], uninstall_status)

    @patch('installmodule.InstallModule')
    @patch('installmodule.UninstallModule')
    def test_run_callback_exception(self, uninstall_mock, install_mock):
        uninstall_status = {
            'status': 2,
            'process': ['uninstall process message'],
            'stdout': ['uninstall message on stdout'],
            'stderr': ['uninstall message on stderr']
        }
        install_status = {
            'status': 2,
            'process': ['install process message2'],
            'stdout': ['install message on stdout'],
            'stderr': ['install message on stderr']
        }
        self._init_uninstall_mock(uninstall_mock, get_status_return_value=uninstall_status)
        self._init_install_mock(install_mock, get_status_return_value=install_status)
        self._init_context(callback_side_effect=Exception('Test exception'))

        self.u.run()
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['status'], UpdateModule.STATUS_UPDATED)
        self.assertEqual(status['install'], install_status)
        self.assertEqual(status['uninstall'], uninstall_status)

    def test_status_callback(self):
        self._init_context()
        status1 = {
            'process': ['process message'],
            'stdout': None,
            'stderr': [],
            'error': False
        }
        status2 = {
            'stdout': ['stdout message'],
            'foo': 'bar',
        }

        self.u._status_callback(status1)
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['uninstall'], status1)

        self.u._status_callback(status2)
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['uninstall']['foo'], status2['foo'])
        self.assertEqual(status['uninstall']['stdout'], status2['stdout'])

        self.u._is_uninstalling = False
        self.u._status_callback(status2)
        status = self.u.get_status()
        logging.debug('Status: %s' % status)
        self.assertEqual(status['install'], status2)

        self.assertTrue(self.status_callback.called)





class UpdateModuleFunctionalTests(unittest.TestCase):

    def setUp(self):
        t = TestLib(self)
        t.set_functional_tests()
        logging.basicConfig(level=logging.FATAL, format='%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.url_archive = 'https://github.com/tangb/cleep/raw/master/cleepos/tests/resources/installmodule/%s.zip'
        self.module_infos = {
            "description": "Test",
            "author": "Cleep",
            "country": None,
            "price": 0,
            "tags": [],
            "deps": [],
            "version": "1.0.0",
            "urls": {
                "info": None,
                "bugs": None,
                "site": None,
                "help": None
            },
            "icon": "message-processing",
            "download": None,
            "sha256": None
        }
        self.cleep_filesystem = CleepFilesystem()
        self.cleep_filesystem.enable_write()
        self.crash_report = Mock()

    def tearDown(self):
        if os.path.exists('/tmp/preinst.tmp'):
            os.remove('/tmp/preinst.tmp')
        if os.path.exists('/tmp/postinst.tmp'):
            os.remove('/tmp/postinst.tmp')
        if os.path.exists('/tmp/preuninst.tmp'):
            os.remove('/tmp/preuninst.tmp')
        if os.path.exists('/tmp/postuninst.tmp'):
            os.remove('/tmp/postuninst.tmp')
        if os.path.exists('/opt/cleep/install/test/test.log'):
            shutil.rmtree('/opt/cleep/install/test/', ignore_errors=True)
        if os.path.exists(os.path.join(INSTALL_DIR, 'modules/test')):
            shutil.rmtree(os.path.join(INSTALL_DIR, 'modules/test'), ignore_errors=True)
        if os.path.exists('/opt/cleep/html/js/modules/test'):
            shutil.rmtree('/opt/cleep/html/js/modules/test', ignore_errors=True)

    def callback(self, status):
        pass

    def test_update_ok(self):
        #install
        name = 'cleepmod_test_1.0.0.ok'
        self.module_infos['download'] = self.url_archive % name
        self.module_infos['sha256'] = '5a522882b74f990ba0175808f52540bd1c1bcfe258873f83fc9e90e85d64a8f4'
        i = InstallModule('test', self.module_infos, False, self.callback, self.cleep_filesystem, self.crash_report)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.is_installing():
            time.sleep(0.25)
        self.assertEqual(i.get_status()['status'], i.STATUS_INSTALLED)

        #check installation
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertTrue(os.path.exists('/opt/cleep/install/test/test.log'))
        self.assertTrue(os.path.exists('/opt/cleep/install/test/preuninst.sh'))
        self.assertTrue(os.path.exists('/opt/cleep/install/test/postuninst.sh'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

        #update module
        u = UpdateModule('test', self.module_infos, self.module_infos, False, self.callback, self.cleep_filesystem, self.crash_report)
        u.start()
        time.sleep(0.5)

        #wait until end of update
        while u.is_updating():
            time.sleep(0.25)
        self.assertEqual(u.get_status()['status'], u.STATUS_UPDATED)

        #check update
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/')))
        self.assertTrue(os.path.exists('/opt/cleep/install/test/'))




if __name__ == '__main__':
    # coverage run --omit="*lib/python*/*","*test_*.py" --concurrency=thread test_installmodule.py; coverage report -i -m
    unittest.main()

