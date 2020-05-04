#!/usr/bin/env python
# -*- coding: utf-8 -*

# File contains UninstallModule and InstallModule classes
# that are used in install.py file to install and uninstall
# raspiot modules

import logging
import time
import os
import inspect
from zipfile import ZipFile
import threading
import tempfile
import stat
from raspiot.libs.internals.console import EndlessConsole
from raspiot.core import RaspIotModule
from raspiot.libs.internals.download import Download
import raspiot.libs.internals.tools as Tools

__all__ = ['UninstallModule', 'InstallModule', 'UpdateModule']

PATH_FRONTEND = u'/opt/raspiot/html'
PATH_SCRIPTS = u'/opt/raspiot/scripts'
PATH_INSTALL = u'/opt/raspiot/install'
FRONTEND_DIR = u'frontend/'
BACKEND_DIR = u'backend/'
SCRIPTS_DIR = u'scripts/'
TESTS_DIR = u'tests/'


class Context():
    def __init__(self):
        pass

    def __str__(self):
        return '%s' % self.to_dict()

    def to_dict(self):
        return {k: v for k, v in self.__dict__.iteritems()}

class LocalModuleException(Exception):
    pass

class CancelException(Exception):
    pass

class ForcedException(Exception):
    pass

class CommonProcess(threading.Thread):
    """
    Common process class for install/uninstall/update module
    """

    def __init__(self, status_callback, cleep_filesystem, crash_report):
        """
        Constructor

        Args:
            status_callback (function): status callback
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
            crash_report (CrashReport): CrashReport instance
        """
        threading.Thread.__init__(self, daemon=True)

        # logger   
        self.logger = logging.getLogger(self.__class__.__name__)
        # self.logger.setLevel(logging.DEBUG)

        # members
        self.running = False
        self.status_callback = status_callback
        self.cleep_filesystem = cleep_filesystem
        self.crash_report = crash_report
        self._script_running = False
        self._pre_script_execution = False
        self._pre_script_status = {
            u'returncode': None,
            u'stdout': [],
            u'stderr': []
        }
        self._post_script_status = {
            u'returncode': None,
            u'stdout': [],
            u'stderr': []
        }
        self._process_status = []

    def _script_callback(self, stdout, stderr):
        """
        Get stdout/stderr from script execution

        Args:
            stdout (string): stdout line
            stderr (string): stderr line
        """
        self.logger.debug('Script callback: stdout=%s stderr=%s' % (stdout, stderr))
        if self._pre_script_execution:
            if stdout:
                self._pre_script_status[u'stdout'].append(stdout)
            if stderr:
                self._pre_script_status['stderr'].append(stderr)

        else:
            if stdout:
                self._post_script_status[u'stdout'].append(stdout)
            if stderr:
                self._post_script_status[u'stderr'].append(stderr)

    def _script_terminated_callback(self, return_code, killed):
        """
        Get infos when script is terminated

        Note:
            see http://www.tldp.org/LDP/abs/html/exitcodes.html for return codes

        Args:
            return_code (int): script return code
            killed (bool): True if script killed, False otherwise
        """
        self.logger.debug('Script terminated callback (return_code=%s killed=%s)' % (return_code, killed))
        if killed:
            if self._pre_script_execution:
                self._pre_script_status[u'returncode'] = 130
            else:
                self._post_script_status[u'returncode'] = 130
        else:
            if self._pre_script_execution:
                self._pre_script_status[u'returncode'] = return_code
            else:
                self._post_script_status[u'returncode'] = return_code

        # script execution terminated
        self._script_running = False

    def _execute_script(self, path):
        """ 
        Execute specified script

        Args:
            path (string): script path

        Return
        """
        # init
        os.chmod(path, stat.S_IEXEC)

        # exec
        self._script_running = True
        self.logger.debug(u'Executing %s script' % path)
        console = EndlessConsole(path, self._script_callback, self._script_terminated_callback)

        # launch script execution
        console.start()

        # monitor end of script execution
        while self._script_running:
            # pause
            time.sleep(0.25)

        # check script result
        if self._pre_script_execution and self._pre_script_status[u'returncode'] == 0:
            return True
        elif self._post_script_status[u'returncode'] == 0:
            return True
        return False

    def _log_process_status(self, context, log_level, message, force_crash_report=False):
        """
        Log exception to stdout and keep track of message in install log file

        Args:
            context (Context): install context
            log_level (int): logging level
            message (string): message to log
            force_crash_report (bool): send crash report if True (default False)
        """
        # logging
        if log_level == logging.NOTSET:
            self.logger.exception(message)
        else:
            self.logger.log(log_level, message)

        # crash report
        if (log_level == logging.NOTSET or force_crash_report) and self.crash_report:
            self.crash_report.report_exception(extra={ u'message': message, 'context': context.to_dict()})

        # save track of error in install process messages
        self._process_status.append(message)

    def _step(self, context, cancel=True):
        """
        Process step, check process is not canceled and send current status

        Args:
            context (Context): install context
            cancel (bool): allow cancel (True) or not (False)
        """
        if cancel and not self.running:
            raise CancelException()

        if self.status_callback:
            try:
                self.status_callback(self.get_status())
            except:
                self.logger.exception('Exception occured during status callback call')
                self.status_callback = None

    def get_status(self): # pragma: no cover
        raise NotImplementedError('_get_status method must be implemented')

    def run(self): # pragma: no cover
        raise NotImplementedError('_get_status method must be implemented')





class UninstallModule(CommonProcess):
    """
    Uninstall module in background task
    This class executes preuninstall script, removes all installed files and executes postuninstall script
    """
    STATUS_IDLE = 0
    STATUS_UNINSTALLING = 1
    STATUS_UNINSTALLED = 2
    STATUS_ERROR_INTERNAL = 3
    STATUS_ERROR_PREUNINST = 4
    STATUS_ERROR_REMOVE = 5
    STATUS_ERROR_POSTUNINST = 6

    def __init__(self, module_name, module_infos, update_process, force_uninstall, status_callback, cleep_filesystem, crash_report):
        """
        Constructor

        Args:
            module_name (string): module name to install
            module_infos (dict): all module infos from modules.json file
            update_process (bool): True if module uninstall occured during update process
            force_uninstall (bool): uninstall module and continue if error occured. Process will always succeed
            callback (function): status callback
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
            crash_report (CrashReport): CrashReport instance
        """
        CommonProcess.__init__(self, status_callback, cleep_filesystem, crash_report)

        # members
        self.status = self.STATUS_IDLE
        self.update_process = update_process
        self.force_uninstall = force_uninstall
        self.raspiot_path = os.path.dirname(inspect.getfile(RaspIotModule))
        self.module_name = module_name
        self.module_infos = module_infos

    def is_uninstalling(self):
        """
        Return True is process is running

        Returns:
            bool: True if running
        """
        return True if self.status == self.STATUS_UNINSTALLING else False

    def get_status(self):
        """
        Return current status

        Return:
            dict: uninstall status::
                {
                    status (int): see STATUS_XXX for available codes
                    module (string): module name
                    prescript (dict): preuninst status (returncode, stdout, stderr)
                    postscript (dict): postuninst status (returncode, stdout, stderr)
                    updateprocess (bool): uninstall triggered by module update
                    process (list): process status
                }
        """
        return {
            u'module': self.module_name,
            u'status': self.status,
            u'prescript': self._pre_script_status,
            u'postscript': self._post_script_status,
            u'updateprocess': self.update_process,
            u'process': self._process_status
        }

    def _run_script(self, context, script):
        """
        Execute preinst.sh script

        Args:
            context (Context): install context
            script (string): script to execute (preinst.sh, postinst.sh, ...)

        Returns:
            bool: True if operation succeed
        """
        self.logger.debug(u'Running script "%s"' % script)
        try:
            self._pre_script_execution = True if script == 'preuninst.sh' else False
            path = os.path.join(os.path.join(PATH_INSTALL, self.module_name, script))
            if os.path.exists(path):
                if not self._execute_script(path):
                    self._log_process_status(context, logging.ERROR, u'Error occured during "%s" script execution of module "%s"' % (script, self.module_name), force_crash_report=True)
                    return False
            else:
                self.logger.debug('No script found at "%s"' % path)

            return True

        except:
            self._log_process_status(context, logging.NOTSET, u'Exception occured during "%s" script execution of module "%s"' % (script, self.module_name))
            return False

    def _remove_installed_files(self, context):
        """
        Remove all installed module files

        Args:
            context (Context): install context

        Returns:
            bool: True if operation succeed
        """
        paths = []
        try:
            # read install log file
            self._log_process_status(context, logging.INFO, u'Remove installed files')
            context.module_log = os.path.join(PATH_INSTALL, self.module_name, u'%s.log' % self.module_name)
            context.install_dir = os.path.join(PATH_INSTALL, self.module_name)
            self.logger.debug(u'Open install log file "%s"' % context.module_log)
            if not os.path.exists(context.module_log):
                self._log_process_status(context, logging.WARN, u'Install log file "%s" for module "%s" was not found' % (context.module_log, self.module_name))
                return True if context.force_uninstall else False
            install_log_fd = self.cleep_filesystem.open(context.module_log, u'r')
            lines = install_log_fd.readlines()
            self.cleep_filesystem.close(install_log_fd)
            self.logger.trace('lines = %s' % lines)

            # remove files
            for line in lines:
                self.logger.trace(u'Processing file "%s"' % line)
                line = line.strip()
                if len(line)==0:
                    # empty line, drop it
                    self.logger.trace(u'Drop empty line')
                    continue

                # check if file exists on filesystem
                if not os.path.exists(line):
                    self._log_process_status(context, logging.ERROR, u'Unable to remove file "%s" that does not exist during module "%s" uninstallation' % (line, self.module_name))
                    continue

                # check if we try to remove system library file (should not happen but we are never too careful)
                if Tools.is_core_lib(line):
                    # it's a core library, log warning and continue
                    self._log_process_status(context, logging.WARN, u'Trying to remove core library file "%s" during module "%s" uninstallation. Drop deletion.' % (line, self.module_name))
                    continue

                # try to delete file
                if not self.cleep_filesystem.rm(line):
                    # just log error and continu processing, we must try to delete as much file as possible
                    self._log_process_status(context, logging.ERROR, u'Unable to remove file "%s" during module "%s" uninstallation' % (line, self.module_name))

                # keep track of file path
                path = os.path.dirname(line)
                if path not in paths:
                    paths.append(path)

            # clear paths
            self.logger.trace(u'Clearing paths: %s' % paths)
            for path in paths:
                if os.path.exists(path) and not self.cleep_filesystem.rmdir(path):
                    self._log_process_status(context, logging.ERROR, u'Unable to remove directory "%s" during module "%s" uninstallation' % (path, self.module_name))

            return True

        except:
            self._log_process_status(context, logging.NOTSET, u'Exception occured removing files during "%s" module uninstallation' % self.module_name)
            return True if context.force_uninstall else False

    def run(self):
        """
        Run uninstall
        """
        # init
        self.running = True
        self.status = self.STATUS_UNINSTALLING
        context = Context()
        context.step = 'init'
        context.force_uninstall = self.force_uninstall
        context.module_log = None
        context.install_dir = None

        self._log_process_status(context, logging.INFO, u'Start module "%s" uninstallation' % self.module_name)

        try:
            # enable write mode
            self.cleep_filesystem.enable_write()

            # uninstall local module
            if u'local' in self.module_infos and self.module_infos[u'local'] is True:
                # nothing to process for local modules, quit current process triggering no error
                raise LocalModuleException()

            # pre uninstallation script
            context.step = 'preuninst'
            if not self._run_script(context, u'preuninst.sh'):
                self.status = self.STATUS_ERROR_PREUNINST
                raise ForcedException()
            self._step(context)

            # remove all installed files
            context.step = 'remove'
            if not self._remove_installed_files(context):
                self.status = self.STATUS_ERROR_REMOVE
                raise ForcedException()
            self._step(context)

            # post uninstallation script
            context.step = 'postuninst'
            if not self._run_script(context, u'postuninst.sh'):
                self.status = self.STATUS_ERROR_POSTUNINST
                raise ForcedException()
            self._step(context)

            # set final status
            self.status = self.STATUS_UNINSTALLED

        except LocalModuleException:
            # local module to uninstall, proper exit
            self.status = self.STATUS_UNINSTALLED

        except ForcedException:
            # error during installation, nothing else to do here
            pass

        except:
            # unexpected error occured, invalid state
            self._log_process_status(context, logging.NOTSET, u'Exception occured during module "%s" uninstallation' % self.module_name)
            self.status = self.STATUS_ERROR_INTERNAL

            # report crash
            self.crash_report.report_exception(extra={'context': context.to_dict()})

        finally:
            # clean stuff
            try:
                # clean backend
                path = os.path.join(self.raspiot_path, 'modules', self.module_name)
                if path and os.path.exists(path):
                    self.cleep_filesystem.rmdir(path)
                # clean frontend
                path = os.path.join(PATH_FRONTEND, 'js/modules/%s' % self.module_name)
                if path and os.path.exists(path):
                    self.cleep_filesystem.rmdir(path)
                # clean install log file
                if context.module_log and os.path.exists(context.module_log):
                    self.cleep_filesystem.rm(context.module_log)
                if context.install_dir and os.path.exists(os.path.join(context.install_dir, u'preuninst.sh')):
                    self.cleep_filesystem.rm(os.path.join(context.install_dir, u'preuninst.sh'))
                if context.install_dir and os.path.exists(os.path.join(context.install_dir, u'postuninst.sh')):
                    self.cleep_filesystem.rm(os.path.join(context.install_dir, u'postuninst.sh'))
            except:
                self._log_process_status(context, logging.NOTSET, u'Exception occured during "%s" uninstall cleaning' % self.module_name)

            # disable write mode
            self.cleep_filesystem.disable_write()

        # finalize installation
        success = True if self.status == self.STATUS_UNINSTALLED else False
        self._log_process_status(context, logging.INFO, u'Module "%s" uninstallation terminated (success:%s, force:%s)' % (self.module_name, success, self.force_uninstall))
        self._step(context)





class InstallModule(CommonProcess):
    """
    Install module in background task
    """
    
    STATUS_IDLE = 0
    STATUS_INSTALLING = 1
    STATUS_INSTALLED = 2
    STATUS_CANCELED = 3
    STATUS_ERROR_INTERNAL = 4
    STATUS_ERROR_DOWNLOAD = 5
    STATUS_ERROR_EXTRACT = 6
    STATUS_ERROR_PREINST = 7
    STATUS_ERROR_BACKUP = 8
    STATUS_ERROR_COPY = 9
    STATUS_ERROR_POSTINST = 10

    def __init__(self, module_name, module_infos, update_process, status_callback, cleep_filesystem, crash_report):
        """
        Constructor

        Args:
            module_name (string): module name to install
            module_infos (dict): all module infos from modules.json file
            update_process (bool): True if module install occured during update process
            status_callback (function): status callback
            cleep_filesystem (CleepFilesystem): CleepFilesystem singleton
            crash_report (CrashReport): Crash report instance
        """
        CommonProcess.__init__(self, status_callback, cleep_filesystem, crash_report)

        # members
        self.update_process = update_process
        self.status = self.STATUS_IDLE
        self.raspiot_path = os.path.dirname(inspect.getfile(RaspIotModule))
        self.module_name = module_name
        self.module_infos = module_infos

        # make sure install paths exist
        if not os.path.exists(PATH_SCRIPTS):
            self.cleep_filesystem.mkdir(PATH_SCRIPTS, True)
        if not os.path.exists(PATH_INSTALL):
            self.cleep_filesystem.mkdir(PATH_INSTALL, True)

    def cancel(self):
        """
        Cancel installation
        """
        self.logger.trace(u'Received module "%s" installation cancelation' % self.module_name)
        self.running = False

    def is_installing(self):
        """
        Return True is process is running

        Returns:
            bool: True if running
        """
        return True if self.status == self.STATUS_INSTALLING else False

    def get_status(self):
        """
        Return current status

        Return:
            dict: install status::
                {
                    module (string): module name
                    status (int): see STATUS_XXX for available codes
                    prescript (dict): preinst status (returncode, stdout, stderr)
                    postscript (dict): postinst status (returncode, stdout, stderr)
                    updateprocess (bool): install triggered by module update
                    process (list): process status
                }
        """
        return {
            u'module': self.module_name,
            u'status': self.status,
            u'prescript': self._pre_script_status,
            u'postscript': self._post_script_status,
            u'updateprocess': self.update_process,
            u'process': self._process_status
        }


    def _download_archive(self, context):
        """
        Download module archive

        Args:
            context (Context): install context

        Returns:
            bool: True if download succeed
        """
        self.logger.debug(u'Download file "%s"' % self.module_infos[u'download'])
        try:
            download = Download(self.cleep_filesystem)
            download_status, context.archive_path = download.download_file(self.module_infos[u'download'], check_sha256=self.module_infos[u'sha256'])
            self.logger.trace(u'archive_path: %s' % context.archive_path)
            if context.archive_path is None:
                self.logger.trace(u'download_status: %s' % download_status)

                if download_status == download.STATUS_ERROR:
                    self.error = u'Error during "%s" download: internal error' % self.module_infos[u'download']
                elif download_status == download.STATUS_ERROR_INVALIDSIZE:
                    self.error = u'Error during "%s" download: invalid filesize' % self.module_infos[u'download']
                elif download_status == download.STATUS_ERROR_BADCHECKSUM:
                    self.error = u'Error during "%s" download: invalid checksum' % self.module_infos[u'download']
                else:
                    self.error = u'Error during "%s" download: unknown error' % self.module_infos[u'download']
    
                self._log_process_status(context, logging.ERROR, self.error, force_crash_report=True)

                return False

            return True

        except:
            self._log_process_status(context, logging.NOTSET, u'Exception occured during module "%s" archive download "%s":' % (self.module_name, self.module_infos[u'download']))
            return False

    def _extract_archive(self, context):
        """
        Extract module archive

        Args:
            context (Context): install context

        Returns:
            bool: True if operation succeed
        """
        self.logger.debug(u'Extracting archive "%s"' % context.archive_path)
        try:
            with ZipFile(context.archive_path, u'r') as zipfile:
                context.extract_path = tempfile.mkdtemp()
                self.logger.debug(u'Extract archive to "%s"' % context.extract_path)
                zipfile.extractall(context.extract_path)

            return True

        except:
            self._log_process_status(context, logging.NOTSET, u'Exception decompressing module "%s" archive "%s" in "%s":' % (self.module_name, context.archive_path, context.extract_path))
            return False

    def _backup_scripts(self, context):
        """
        Backup uninstall scripts

        Args:
            context (Context): install context

        Returns:
            bool: True if operation succeed
        """
        self.logger.debug(u'Save module "%s" uninstall scripts', self.module_name)
        try:
            # preuninst
            src_path = os.path.join(context.extract_path, SCRIPTS_DIR, u'preuninst.sh')
            dst_path = os.path.join(PATH_INSTALL, self.module_name, u'preuninst.sh')
            if os.path.exists(src_path):
                self.logger.trace(u'Copying "%s" to "%s"' % (src_path, dst_path))
                self.cleep_filesystem.copy(src_path, dst_path)
            else:
                self.logger.trace(u'Script preuninst.sh not found in archive')

            # postuninst
            src_path = os.path.join(context.extract_path, SCRIPTS_DIR, u'postuninst.sh')
            dst_path = os.path.join(PATH_INSTALL, self.module_name, u'postuninst.sh')
            if os.path.exists(src_path):
                self.logger.trace(u'Copying "%s" to "%s"' % (src_path, dst_path))
                self.cleep_filesystem.copy(src_path, dst_path)
            else:
                self.logger.trace(u'Script postuninst.sh not found in archive')

            return True

        except:
            self._log_process_status(context, logging.NOTSET, u'Exception saving module "%s" scripts:' % self.module_name)
            return False

    def _run_script(self, context, script):
        """
        Execute preinst.sh script

        Args:
            context (Context): install context
            script (string): script to execute (preinst.sh, postinst.sh, ...)

        Returns:
            bool: True if operation succeed
        """
        self.logger.debug(u'Running script "%s"' % script)
        try:
            self._pre_script_execution = True if script == 'preinst.sh' else False
            path = os.path.join(context.extract_path, SCRIPTS_DIR, script)
            if os.path.exists(path):
                if not self._execute_script(path):
                    self._log_process_status(context, logging.ERROR, u'Error occured during "%s" script execution of module "%s"' % (script, self.module_name), force_crash_report=True)
                    return False
            else:
                self.logger.debug('No script found at "%s"' % path)

            return True

        except:
            self._log_process_status(context, logging.NOTSET, u'Exception occured during "%s" script execution of module "%s"' % (script, self.module_name))
            return False

    def _copy_module_files(self, context):
        """
        Install module files

        Args:
            context (Context): install context

        Returns:
            bool: True if operation succeed
        """
        self.logger.debug(u'Installing module files')
        try:
            # list archive files
            archive_files = []
            for directory, _, files in os.walk(context.extract_path):
                for filename in files:
                    full_path = os.path.join(directory, filename)
                    rel_path = full_path.replace(context.extract_path, u'')
                    rel_path = rel_path[1:] if rel_path[0]==u'/' else rel_path
                    archive_files.append(rel_path)
            self.logger.trace(u'archive_files: %s' % archive_files)

            # process them according to their directory
            for archive_file in archive_files:
                self.logger.trace('Processing archive file "%s"' % archive_file)
                if archive_file.startswith(BACKEND_DIR):
                    # copy python files
                    src_path = os.path.join(context.extract_path, archive_file)
                    dst_path = os.path.join(self.raspiot_path, archive_file).replace(BACKEND_DIR, u'')
                    self.logger.trace(u'Backend src=%s dst=%s' % (src_path, dst_path))

                    # check file overwritings
                    if os.path.exists(dst_path):
                        if Tools.is_core_lib(dst_path):
                            # system lib, just drop file install with warning
                            self._log_process_status(context, logging.WARNING, u'File "%s" is a core lib and shouldn\'t be exists in module "%s" package. File is dropped.' % (dst_path, self.module_name))
                            continue
                        else:
                            # warning about file overwriting
                            self._log_process_status(context, logging.WARNING, u'Module "%s" installation overwrites existing file "%s"' % (self.module_name, dst_path))

                    self.cleep_filesystem.mkdir(os.path.dirname(dst_path))
                    if not self.cleep_filesystem.copy(src_path, dst_path):
                        self._log_process_status(context, logging.ERROR, u'Error copying file "%s" to "%s" during module "%s" installation' % (src_path, dst_path, self.module_name), force_crash_report=True)
                        return False

                    # keep track of copied file for uninstall
                    context.install_log_fd.write(u'%s\n' % dst_path)
                    context.install_log_fd.flush()

                elif archive_file.startswith(FRONTEND_DIR):
                    # copy ui files
                    src_path = os.path.join(context.extract_path, archive_file)
                    dst_path = os.path.join(PATH_FRONTEND, archive_file).replace(FRONTEND_DIR, u'')
                    self.logger.trace(u'Frontend src=%s dst=%s' % (src_path, dst_path))
                    self.cleep_filesystem.mkdir(os.path.dirname(dst_path))
                    if not self.cleep_filesystem.copy(src_path, dst_path):
                        self._log_process_status(context, logging.ERROR, u'Error copying file "%s" to "%s" during module "%s" installation' % (src_path, dst_path, self.module_name), force_crash_report=True)
                        return False

                    # keep track of copied file for uninstall
                    context.install_log_fd.write(u'%s\n' % dst_path)
                    context.install_log_fd.flush()

                else:
                    # drop file
                    self.logger.debug(u'Drop unhandled archive file: %s' % archive_file)

            return True
                
        except Exception as e:
            self._log_process_status(context, logging.NOTSET, u'Exception occured during module "%s" files copy' % self.module_name)
            return False

    def _rollback_install(self, context):
        """
        Rollback installation, removing installed files
        """
        self.logger.debug(u'Rollbacking installation')
        if context.install_log is not None and os.path.exists(context.install_log):
            try:
                # remove installed files
                fd = self.cleep_filesystem.open(context.install_log, u'r')
                lines = fd.readlines()
                for line in lines:
                    self.logger.trace(u'Removing "%s" module "%s" file.' % (line, self.module_name))
                    self.cleep_filesystem.rm(line.strip())

                # remove module install dir
                self.cleep_filesystem.rmdir(os.path.dirname(context.install_log))

            except:
                self._log_process_status(context, logging.NOTSET, u'Exception ocurred during "%s" module installation rollback' % self.module_name)

    def run(self):
        """
        Run install
        """
        # init
        self.running = True
        self.status = self.STATUS_INSTALLING
        context = Context()
        rollback = False
        context.install_log = None
        context.install_log_fd = None
        context.extract_path = None
        context.archive_path = None
        context.step = 'init'

        self._log_process_status(context, logging.INFO, u'Start module "%s" installation' % self.module_name)

        try:
            # enable write mode
            self.cleep_filesystem.enable_write()

            # install local module
            if u'local' in self.module_infos and self.module_infos[u'local'] is True:
                # nothing to process for local modules, quit current process triggering no error
                raise LocalModuleException()
        
            # init install
            context.install_log = os.path.join(PATH_INSTALL, self.module_name, u'%s.log' % self.module_name)
            self.logger.debug(u'Create install log file "%s"' % context.install_log)
            self.cleep_filesystem.mkdirs(os.path.join(PATH_INSTALL, self.module_name))
            context.install_log_fd = self.cleep_filesystem.open(context.install_log, u'w')
            context.install_log_fd.flush()

            # download module package
            context.step = 'download'
            if not self._download_archive(context):
                self.status = self.STATUS_ERROR_DOWNLOAD
                raise ForcedException()
            self._step(context)

            # extract archive
            context.step = 'extract'
            if not self._extract_archive(context):
                self.status = self.STATUS_ERROR_EXTRACT
                raise ForcedException()
            self._step(context)

            # copy uninstall scripts to install path (to make them available during uninstallation)
            context.step = 'backup'
            if not self._backup_scripts(context):
                self.status = self.STATUS_ERROR_BACKUP
                raise ForcedException()

            # pre installation script
            context.step = 'preinst'
            if not self._run_script(context, u'preinst.sh'):
                self.status = self.STATUS_ERROR_PREINST
                raise ForcedException()
            self._step(context)

            # copy module files
            context.step = 'copy'
            if not self._copy_module_files(context):
                self.status = self.STATUS_ERROR_COPY
                raise ForcedException()
            self._step(context, cancel=False)

            # post installation script
            context.step = 'postinst'
            if not self._run_script(context, u'postinst.sh'):
                self.status = self.STATUS_ERROR_POSTINST
                raise ForcedException()

            # set final status
            self.status = self.STATUS_INSTALLED

        except LocalModuleException:
            # local module to install, proper exit
            rollback = False
            self.status = self.STATUS_INSTALLED

        except CancelException:
            # install canceled
            self._log_process_status(context, logging.INFO, u'Module "%s" installation canceled' % self.module_name)
            rollback = True
            self.status = self.STATUS_CANCELED

        except ForcedException:
            # error during installation
            rollback = True

        except:
            # unexpected error occured, invalid state
            self._log_process_status(context, logging.NOTSET, u'Exception occured during module "%s" installation' % self.module_name)
            rollback = True
            self.status = self.STATUS_ERROR_INTERNAL

            # report crash
            self.crash_report.report_exception(extra={'context': context.to_dict()})

        finally:
            # clean stuff
            try:
                if context.install_log_fd:
                    self.cleep_filesystem.close(context.install_log_fd)
                if context.extract_path:
                    self.cleep_filesystem.rmdir(context.extract_path)
                if context.archive_path:
                    self.cleep_filesystem.rm(context.archive_path)
            except:
                self._log_process_status(context, logging.NOTSET, u'Exception occured during "%s" install cleaning' % self.module_name)

            if rollback:
                # perform requested rollback
                self._log_process_status(context, logging.INFO, u'Rollback module "%s" installation after error' % self.module_name)
                self._rollback_install(context)

            # disable write mode
            self.cleep_filesystem.disable_write()

        # finalize installation
        success = True if self.status == self.STATUS_INSTALLED else False
        self._log_process_status(context, logging.INFO, u'Module "%s" installation terminated (success:%s, rollback:%s)' % (self.module_name, success, rollback))
        self._step(context, cancel=False)





class UpdateModule(threading.Thread):
    """
    Update CleepOS module
    """
    STATUS_IDLE = 0
    STATUS_UPDATING = 1
    STATUS_UPDATED = 2
    STATUS_ERROR = 3

    def __init__(self, module_name, current_module_infos, new_module_infos, force_uninstall, status_callback, cleep_filesystem, crash_report):
        """
        Constructor

        Args:
            module_name (string): module name to update
            current_module_infos (dict): current module infos
            new_module_infos (dict): new module infos
            update_process (bool): True if module uninstall occured during update process
            force_uninstall (bool): force module uninstall even if error occured
            status_callback (function): status callback
            cleep_filesystem (CleepFilesystem): CleepFilesystem singleton
            crash_report (CrashReport): Crash report instance
        """
        threading.Thread.__init__(self, daemon=True)

        # logger   
        self.logger = logging.getLogger(self.__class__.__name__)
        # self.logger.setLevel(logging.DEBUG)

        # members
        self.module_name = module_name
        self.current_module_infos = current_module_infos
        self.new_module_infos = new_module_infos
        self.force_uninstall = force_uninstall
        self.status_callback = status_callback
        self.cleep_filesystem = cleep_filesystem
        self.crash_report = crash_report
        self.status = self.STATUS_IDLE
        self._is_uninstalling = True
        # initialized when update process starts
        self.__uninstall_status = {}
        self.__install_status = {}

    def is_updating(self):
        """
        Return True is process is running

        Returns:
            bool: True if running
        """
        return True if self.status == self.STATUS_UPDATING else False

    def get_status(self):
        """
        Return update status

        Return:
            dict: current status
                {
                    status (int): see STATUS_XXX
                    uninstall (dict): dict as returned by uninstall module status
                    install (dict): dict as returned by install module status
                    module (string): module name
                }
        """
        return {
            u'module': self.module_name,
            u'status': self.status,
            u'uninstall': self.__uninstall_status,
            u'install': self.__install_status,
        }

    def _status_callback(self, status):
        """
        Install/Uninstall status callback

        Args:
            status (dict): status returned by install/uninstall
        """
        message = 'Update callback from uninstall: %s' if self._is_uninstalling else 'Update callback from install: %s'
        update = self.__uninstall_status.update if self._is_uninstalling else self.__install_status.update
        
        # callback from uninstall process
        self.logger.debug(message % status)
        update(status)

        self._step()

    def _step(self):
        """
        Process step
        """
        if self.status_callback:
            try:
                self.status_callback(self.get_status())
            except:
                self.logger.exception('Exception occured during status callback call')
                self.status_callback = None

    def run(self):
        """
        Run module update
        """
        try:
            # init
            self.logger.info(u'Start module "%s" update' % self.module_name)
            self.status = self.STATUS_UPDATING
            uninstall = UninstallModule(self.module_name, self.new_module_infos, True, self.force_uninstall, self._status_callback, self.cleep_filesystem, self.crash_report)
            self.__uninstall_status = uninstall.get_status()
            install = InstallModule(self.module_name, self.new_module_infos, True, self._status_callback, self.cleep_filesystem, self.crash_report)
            self.__install_status = install.get_status()

            # run uninstall
            self._is_uninstalling = True
            uninstall.start()
            time.sleep(0.5)
            while uninstall.is_uninstalling():
                time.sleep(0.25)
            if uninstall.get_status()[u'status'] != uninstall.STATUS_UNINSTALLED:
                # uninstall failed
                # TODO implement rollback reinstalling previous module version
                self.logger.warning(u'Error uninstalling "%s" module during update. Try to install new version anyway' % self.module_name)
            self._step()
            
            # run new package install
            self._is_uninstalling = False
            install.start()
            time.sleep(0.5)
            while install.is_installing():
                time.sleep(0.25)
            if install.get_status()[u'status'] != install.STATUS_INSTALLED:
                # install failed
                # TODO implement rollback reinstalling previous module version
                self.logger.error(u'Error installing new "%s" module version during update' % self.module_name)
                raise ForcedException()
            self._step()

            # set final status
            self.status = self.STATUS_UPDATED
    
        except ForcedException:
            # error during update
            self.status = self.STATUS_ERROR

        except:
            # unexpected error
            self.status = self.STATUS_ERROR
            self.logger.exception(u'Exception occured during "%s" module update' % self.module_name)

        # finalize update
        success = True if self.status == self.STATUS_UPDATED else False
        self.logger.info(u'Module "%s" installation terminated (success:%s)' % (self.module_name, success))
        self._step()

