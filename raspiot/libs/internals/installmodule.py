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
from raspiot.exception import ForcedException

__all__ = ['UninstallModule', 'InstallModule', 'UpdateModule']

PATH_FRONTEND = u'/opt/raspiot/html'
PATH_SCRIPTS = u'/opt/raspiot/scripts'
PATH_INSTALL = u'/opt/raspiot/install'
FRONTEND_DIR = u'frontend/'
BACKEND_DIR = u'backend/'
SCRIPTS_DIR = u'scripts/'
TESTS_DIR = u'tests/'


class Context():
    pass

class LocalModuleException(Exception):
    pass

class CancelException(Exception):
    pass

class UninstallModule(threading.Thread):
    """
    Uninstall module in background task
    This class executes preuninstall script, removes all installed files and executes postuninstall script
    """
    STATUS_IDLE = 0
    STATUS_UNINSTALLING = 1
    STATUS_UNINSTALLED = 2
    STATUS_ERROR_INTERNAL = 3
    STATUS_UNINSTALLED_ERROR_PREUNINST = 4
    STATUS_UNINSTALLED_ERROR_REMOVE = 5
    STATUS_UNINSTALLED_ERROR_POSTUNINST = 6

    def __init__(self, module, module_infos, update_process, force, callback, cleep_filesystem, crash_report):
        """
        Constructor

        Args:
            module (string): module name to install
            module_infos (dict): all module infos from modules.json file
            update_process (bool): True if module uninstall occured during update process
            force (bool): uninstall module and continue if error occured
            callback (function): status callback
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
            crash_report (CrashReport): CrashReport instance
        """
        threading.Thread.__init__(self)
        threading.Thread.daemon = True

        # logger   
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)

        # members
        self.status = self.STATUS_IDLE
        self.crash_report = crash_report
        self.update_process = update_process
        self.force = force
        self.raspiot_path = os.path.dirname(inspect.getfile(RaspIotModule))
        self.running = True
        self.module = module
        self.module_infos = module_infos
        self.cleep_filesystem = cleep_filesystem
        self.__script_running = True
        self.__pre_script_execution = False
        self.__pre_script_status = {u'stdout': [], u'stderr':[], u'returncode': None}
        self.__post_script_status = {u'stdout': [], u'stderr':[], u'returncode': None}
        self.callback = callback
        self.__process_status = []

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
            u'module': self.module,
            u'status': self.status,
            u'prescript': self.__pre_script_status,
            u'postscript': self.__post_script_status,
            u'updateprocess': self.update_process,
            u'process': self.__process_status
        }

    def __script_callback(self, stdout, stderr):
        """
        Get stdout/stderr from script execution

        Args:
            stdout (string): stdout line
            stderr (string): stderr line
        """
        self.logger.debug('Script callback: stdout=%s stderr=%s' % (stdout, stderr))
        if self.__pre_script_execution:
            if stdout:
                self.__pre_script_status[u'stdout'].append(stdout)
            if stderr:
                self.__pre_script_status['stderr'].append(stderr)

        else:
            if stdout:
                self.__post_script_status[u'stdout'].append(stdout)
            if stderr:
                self.__post_script_status[u'stderr'].append(stderr)

    def __script_terminated_callback(self, return_code, killed):
        """
        Get infos when script is terminated

        Note:
            see http://www.tldp.org/LDP/abs/html/exitcodes.html for return codes

        Args:
            return_code (int): script return code
            killed (bool): True if script killed, False otherwise
        """
        self.logger.debug('Script terminated callback: return_code=%s killed=%s' % (return_code, killed))
        if killed:
            if self.__pre_script_execution:
                self.__pre_script_status[u'returncode'] = 130
            else:
                self.__post_script_status[u'returncode'] = 130
        else:
            if self.__pre_script_execution:
                self.__pre_script_status[u'returncode'] = return_code
            else:
                self.__post_script_status[u'returncode'] = return_code

        # script execution terminated
        self.__script_running = False

    def __execute_script(self, path):
        """
        Execute specified script

        Args:
            script (string): script path

        Return
        """
        # init
        os.chmod(path, stat.S_IEXEC)

        # exec
        self.logger.debug(u'Executing "%s" script' % path)
        console = EndlessConsole(path, self.__script_callback, self.__script_terminated_callback)
        out = False

        # launch script execution
        console.start()

        # monitor end of script execution
        while self.__script_running:
            #pause
            time.sleep(0.25)

        # check script result
        if self.__pre_script_execution and self.__pre_script_status[u'returncode']==0:
            out = True
        elif self.__post_script_status[u'returncode']==0:
            out = True

        return out

    def run(self):
        """
        Run uninstall
        """
        # init
        self.logger.info(u'Start app "%s" uninstallation' % self.module)
        self.__process_status.append(u'Start app "%s" uninstallation' % self.module)
        self.status = self.STATUS_UNINSTALLING
        error = False
        module_log = None
        preuninst_sh = None
        postuninst_sh = None
        error_during_prescript = False
        error_during_remove = False
        error_during_postscript = False

        try:
            # enable write mode
            self.cleep_filesystem.enable_write()

            # uninstall local module
            if u'local' in self.module_infos and self.module_infos[u'local'] is True:
                # nothing to process for local modules, quit current process triggering no error
                raise LocalModuleException()

            # pre uninstallation script
            try:
                self.logger.debug(u'Run pre uninstallation script')
                self.__process_status.append(u'Run pre uninstallation script')
                self.__pre_script_execution = True
                preuninst_sh = os.path.join(os.path.join(PATH_INSTALL, self.module, u'preuninst.sh'))
                if os.path.exists(preuninst_sh):
                    self.logger.debug(u'Pre uninstallation script found "%s"' % preuninst_sh)
                    self.__script_running = True
                    if not self.__execute_script(preuninst_sh):
                        # script failed
                        raise Exception(u'Forced exception')
                else:
                    self.logger.debug(u'No preuninst script found at "%s"' % preuninst_sh)
                    self.__process_status.append(u'No pre uninstallation script')

            except Exception as e:
                if e.message!=u'Forced exception':
                    self.logger.exception(u'Exception occured during preuninst.sh script execution of module "%s"' % self.module)
                    self.__process_status.append(u'Exception occured during preuninst.sh script execution of module "%s"' % self.module)
                error_during_prescript = True
                # do not stop uninstall process, it's not blocking

            # send status
            if self.callback:
                self.callback(self.get_status())

            # remove all installed files
            paths = []
            try:
                self.__process_status.append(u'Remove installed files')
                module_log = os.path.join(PATH_INSTALL, self.module, u'%s.log' % self.module)
                self.logger.debug(u'Open install log file "%s"' % module_log)
                if not os.path.exists(module_log):
                    self.logger.warning(u'Problem during app "%s" uninstallation because "%s" file doesn\'t exist' % (self.module, module_log))
                install_log = self.cleep_filesystem.open(module_log, u'r')
                lines = install_log.readlines()
                self.cleep_filesystem.close(install_log)
                for line in lines:
                    line = line.strip()
                    if len(line)==0:
                        # empty line, drop it
                        continue

                    # check if we try to remove system library file (should not happen but we are never too careful)
                    if Tools.is_system_lib(line):
                        # it's a system library, log warning and continue
                        self.logger.warning(u'Trying to remove system library "%s" during app "%s" uninstallation. Drop deletion.' % (line, self.module))
                        continue

                    # try to delete file
                    if os.path.exists(line) and not self.cleep_filesystem.rm(line):
                        self.logger.warning(u'File "%s" was not removed during "%s" app uninstallation' % (line, self.module))

                    # keep track of file path
                    path = os.path.dirname(line)
                    if path not in paths:
                        paths.append(path)

                # clear paths
                for path in paths:
                    if os.path.exists(path):
                        if not self.cleep_filesystem.rmdir(path):
                            self.logger.warning(u'Directory "%s" was not removed during "%s" app uninstallation' % (path, self.module))

            except IOError as e:
                if e.errno==2:
                    self.logger.exception(u'Exception occured during "%s" files app uninstallation: %s' % (self.module, u'installation file not found'))
                    self.__process_status.append(u'Exception occured during "%s" files app uninstallation: %s' % (self.module, u'installation file not found'))
                else:
                    self.logger.exception(u'Exception occured during "%s" files app uninstallation: %s' % (self.module, os.strerror(e.errno)))
                    self.__process_status.append(u'Exception occured during "%s" files app uninstallation: %s' % (self.module, os.strerro(e.errno)))
                error_during_remove = True

            except Exception as e:
                if e.message!=u'Forced exception':
                    self.logger.exception(u'Exception occured during "%s" files app uninstallation: %s' % (self.module, str(e)))
                    self.__process_status.append(u'Exception occured during "%s" files app uninstallation: %s' % (self.module, str(e)))
                error_during_remove = True
                # do not stop uninstall process, some files could still remain after uninstall

            # send status
            if self.callback:
                self.callback(self.get_status())

            # post uninstallation script
            try:
                self.logger.debug(u'Run post uninstallation script')
                self.__process_status.append(u'Run post uninstallation script')
                self.__pre_script_execution = False
                postuninst_sh = os.path.join(os.path.join(PATH_INSTALL, self.module, u'postuninst.sh'))
                if os.path.exists(postuninst_sh):
                    self.logger.debug(u'Post uninstallation script found "%s"' % postuninst_sh)
                    self.__script_running = True
                    if not self.__execute_script(postuninst_sh):
                        # script failed
                        raise Exception(u'Forced exception')
                else:
                    self.logger.debug(u'No postuninst script found at "%s"' % postuninst_sh)
                    self.__process_status.append(u'No post uninstallation script')

            except Exception as e:
                if e.message!=u'Forced exception':
                    self.logger.exception(u'Exception occured during postuninst.sh script execution of app "%s"' % self.module)
                    self.__process_status.append(u'Exception occured during postuninst.sh script execution of app "%s"' % self.module)
                error_during_postscript = True
                # do not stop uninstall process

        except LocalModuleException:
            # local module to uninstall, proper exit
            pass

        except:
            # unexpected exception
            self.logger.exception(u'Unexpected exception during uninstall:')

            # local exception raised, invalid state :S
            error = True

            # report exception
            self.crash_report.report_exception()

        finally:
            self.logger.debug(u'Uninstall finalization')
            # clean stuff
            try:
                path = os.path.join(PATH_INSTALL, self.module)
                if path and os.path.exists(path):
                    self.cleep_filesystem.rmdir(path)
                path = os.path.join(PATH_FRONTEND, 'js/modules/%s' % self.module)
                if path and os.path.exists(path):
                    self.cleep_filesystem.rmdir(path)
                if module_log and os.path.exists(module_log):
                    self.cleep_filesystem.rm(module_log)
            except:
                self.logger.exception(u'Exception during "%s" install cleaning:' % self.module)

            self.logger.debug('error=%s error_during_prescript=%s error_during_postscript=%s error_during_remove=%s' % (error, error_during_prescript, error_during_postscript, error_during_remove))
            if self.force:
                # whatever the result return uninstalled
                self.status = self.STATUS_UNINSTALLED
            elif error:
                # error occured
                self.logger.debug(u'Error occured during "%s" app uninstallation' % self.module)
                self.status = self.STATUS_ERROR_INTERNAL
            elif error_during_prescript:
                error = True
                self.status = self.STATUS_UNINSTALLED_ERROR_PREUNINST
            elif error_during_remove:
                error = True
                self.status = self.STATUS_UNINSTALLED_ERROR_REMOVE
            elif error_during_postscript:
                error = True
                self.status = self.STATUS_UNINSTALLED_ERROR_POSTUNINST
            else:
                # install terminated successfully
                self.status = self.STATUS_UNINSTALLED

            # send status
            if self.callback:
                self.callback(self.get_status())

            # disable write mode
            self.cleep_filesystem.disable_write()

        self.__process_status.append(u'App "%s" uninstallation terminated (success:%s, forced:%s)' % (self.module, not error, self.force))
        self.logger.info(u'App "%s" uninstallation terminated (success: %s)' % (self.module, not error))





class InstallModule(threading.Thread):
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
    STATUS_ERROR_COPY = 8
    STATUS_ERROR_POSTINST = 9

    def __init__(self, module_name, module_infos, update_process, callback, cleep_filesystem, crash_report):
        """
        Constructor

        Args:
            module_name (string): module name to install
            module_infos (dict): all module infos from modules.json file
            update_process (bool): True if module install occured during update process
            callback (function): status callback
            cleep_filesystem (CleepFilesystem): CleepFilesystem singleton
            crash_report (CrashReport): Crash report instance
        """
        threading.Thread.__init__(self)
        threading.Thread.daemon = True

        # logger
        self.logger = logging.getLogger(self.__class__.__name__)
        # self.logger.setLevel(logging.DEBUG)

        # members
        self.callback = callback
        self.crash_report = crash_report
        self.update_process = update_process
        self.status = self.STATUS_IDLE
        self.raspiot_path = os.path.dirname(inspect.getfile(RaspIotModule))
        self.running = True
        self.module_name = module_name
        self.module_infos = module_infos
        self.cleep_filesystem = cleep_filesystem
        self.__script_running = True
        self.__pre_script_execution = False
        self.__pre_script_status = {u'stdout': [], u'stderr':[], u'returncode':None}
        self.__post_script_status = {u'stdout': [], u'stderr':[], u'returncode':None}
        self.__process_status = []
        self.status = self.STATUS_IDLE

        # make sure install paths exist
        if not os.path.exists(PATH_SCRIPTS):
            self.cleep_filesystem.mkdir(PATH_SCRIPTS, True)
        if not os.path.exists(PATH_INSTALL):
            self.cleep_filesystem.mkdir(PATH_INSTALL, True)

    def cancel(self):
        """
        Cancel installation
        """
        self.logger.info(u'Module "%s" installation canceled' % self.module_name)
        self.running = False

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
            u'prescript': self.__pre_script_status,
            u'postscript': self.__post_script_status,
            u'updateprocess': self.update_process,
            u'process': self.__process_status
        }

    def __script_callback(self, stdout, stderr):
        """
        Get stdout/stderr from script execution

        Args:
            stdout (string): stdout line
            stderr (string): stderr line
        """
        self.logger.debug('Script callback: stdout=%s stderr=%s' % (stdout, stderr))
        if self.__pre_script_execution:
            if stdout:
                self.__pre_script_status[u'stdout'].append(stdout)
            if stderr:
                self.__pre_script_status['stderr'].append(stderr)

        else:
            if stdout:
                self.__post_script_status[u'stdout'].append(stdout)
            if stderr:
                self.__post_script_status[u'stderr'].append(stderr)

    def __script_terminated_callback(self, return_code, killed):
        """
        Get infos when script is terminated

        Note:
            see http://www.tldp.org/LDP/abs/html/exitcodes.html for return codes

        Args:
            return_code (int): script return code
            killed (bool): True if script killed, False otherwise
        """
        self.logger.debug('Script terminated callback: return_code=%s killed=%s' % (return_code, killed))
        if killed:
            if self.__pre_script_execution:
                self.__pre_script_status[u'returncode'] = 130
            else:
                self.__post_script_status[u'returncode'] = 130
        else:
            if self.__pre_script_execution:
                self.__pre_script_status[u'returncode'] = return_code
            else:
                self.__post_script_status[u'returncode'] = return_code

        # script execution terminated
        self.__script_running = False

    def __execute_script(self, path):
        """ 
        Execute specified script

        Args:
            path (string): script path

        Return
        """
        # init
        os.chmod(path, stat.S_IEXEC)

        # exec
        self.logger.debug(u'Executing %s script' % path)
        console = EndlessConsole(path, self.__script_callback, self.__script_terminated_callback)
        out = False

        # launch script execution
        console.start()

        # monitor end of script execution
        while self.__script_running:
            # pause
            time.sleep(0.25)

        # check script result
        if self.__pre_script_execution and self.__pre_script_status[u'returncode']==0:
            out = True
        elif self.__post_script_status[u'returncode']==0:
            out = True

        return out

    def is_installing(self):
        """
        Return True is process is running

        Returns:
            bool: True if running
        """
        return True if self.status==self.STATUS_INSTALLING else False

    def __log_process_status(self, context, log_level, message):
        """
        Log exception to stdout and keep track of message in install log file

        Args:
            context (Context): install context
            log_level (int): logging level
            message (string): message to log
        """
        if log_level==logging.NOTSET:
            self.logger.exception(message)

            # exception occured, crash report
            if self.crash_report:
                self.crash_report.report_exception(extra={ u'message': message })
        else:
            self.logger.log(log_level, message)

        self.__process_status.append(message)

    def __download_archive(self, context):
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
            context.archive_path = download.download_file(self.module_infos[u'download'], check_sha256=self.module_infos[u'sha256'])
            if context.archive_path is None:
                download_status = download.get_status()

                if download_status==download.STATUS_ERROR:
                    self.error = u'Error during "%s" download: internal error' % self.module_infos[u'download']
                elif download_status==download.STATUS_ERROR_INVALIDSIZE:
                    self.error = u'Error during "%s" download: invalid filesize' % self.module_infos[u'download']
                elif download_status==download.STATUS_ERROR_BADCHECKSUM:
                    self.error = u'Error during "%s" download: invalid checksum' % self.module_infos[u'download']
                else:
                    self.error = u'Error during "%s" download: unknown error' % self.module_infos[u'download']
    
                self.__log_process_status(context, logging.ERROR, self.error)

                return False

            return True

        except:
            self.__log_process_status(context, logging.NOTSET, u'Exception occured during module "%s" package download "%s":' % (self.module_name, self.module_infos[u'download']))
            return False

    def __extract_archive(self, context):
        """
        Extract module archive

        Args:
            context (Context): install context

        Returns:
            bool: True if operation succeed
        """
        self.logger.debug(u'Extracting archive "%s"' % context.archive_path)
        try:
            zipfile = ZipFile(context.archive_path, u'r')
            context.extract_path = tempfile.mkdtemp()
            self.logger.debug(u'Extract archive to "%s"' % context.extract_path)
            zipfile.extractall(context.extract_path)
            zipfile.close()

            return True

        except:
            self.__log_process_status(context, logging.NOTSET, u'Error decompressing module "%s" package "%s" in "%s":' % (self.module_name, context.archive_path, context.extract_path))
            return False

    def __backup_scripts(self, context):
        """
        Backup uninstall scripts

        Args:
            context (Context): install context

        Returns:
            bool: True if operation succeed
        """
        self.logger.debug(u'Save module "%s" uninstall scripts')
        try:
            # preinst
            src_path = os.path.join(extract_path, SCRIPTS_DIR, u'preinst.sh')
            dst_path = os.path.join(PATH_INSTALL, self.module_name, u'preinst.sh')
            if os.path.exists(src_path):
                self.cleep_filesystem.copy(src_path, dst_path)
            else:
                self.logger.trace(u'Script preinst.sh not found in archive')

            # postinst
            src_path = os.path.join(extract_path, SCRIPTS_DIR, u'postinst.sh')
            dst_path = os.path.join(PATH_INSTALL, self.module_name, u'postinst.sh')
            if os.path.exists(src_path):
                self.cleep_filesystem.copy(src_path, dst_path)
            else:
                self.logger.trace(u'Script postinst.sh not found in archive')

            # preuninst
            src_path = os.path.join(extract_path, SCRIPTS_DIR, u'preuninst.sh')
            dst_path = os.path.join(PATH_INSTALL, self.module_name, u'preuninst.sh')
            if os.path.exists(src_path):
                self.cleep_filesystem.copy(src_path, dst_path)
            else:
                self.logger.trace(u'Script preuninst.sh not found in archive')

            # postuninst
            src_path = os.path.join(extract_path, SCRIPTS_DIR, u'postuninst.sh')
            dst_path = os.path.join(PATH_INSTALL, self.module_name, u'postuninst.sh')
            if os.path.exists(src_path):
                self.cleep_filesystem.copy(src_path, dst_path)
            else:
                self.logger.trace(u'Script postuninst.sh not found in archive')

            return True

        except:
            self.__log_process_status(context, logging.NOTSET, u'Error saving module "%s" uninstall scripts:' % self.module_name)
            return False

    def __run_script(self, context, script):
        """
        Execute preinst.sh script

        Args:
            context (Context): install context
            script (string): script to execute (preinst.sh, postinst.sh, ...)

        Returns:
            bool: True if operation succeed
        """
        self.logger.debug(u'Executing preinst.sh')
        try:
            self.__pre_script_execution = True
            path = os.path.join(context.extract_path, SCRIPTS_DIR, script)
            if os.path.exists(path):
                self.__script_running = True
                if not self.__execute_script(path):
                    return False
            else:
                self.logger.debug('No script found at "%s"' % path)

            return True

        except:
            self.__log_process_status(context, logging.NOTSET, u'Exception occured during "%s" script execution of module "%s"' % (script, self.module_name))
            return False

    def __copy_module_files(self, context):
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
                    if rel_path[0]==u'/':
                        rel_path = rel_path[1:]
                    archive_files.append(rel_path)
            self.logger.trace(u'archive_files: %s' % archive_files)

            # process them according to their directory
            for f in archive_files:
                if f.startswith(BACKEND_DIR):
                    # copy python files
                    src_path = os.path.join(context.extract_path, f)
                    dst_path = os.path.join(self.raspiot_path, f).replace(BACKEND_DIR, u'')
                    self.logger.trace(u'Backend src=%s dst=%s' % (src_path, dst_path))

                    # check file overwritings
                    if os.path.exists(dst_path):
                        if Tools.is_core_lib(dst_path):
                            # system lib, just drop file install with warning
                            self.__log_process_status(context, logging.WARNING, u'File "%s" is a core lib and shouldn\'t be exists in module "%s" package. File is dropped.' % (dst_path, self.module_name))
                            continue
                        else:
                            # it's a third part file, can't overwrite existing one, trigger exception
                            self.__log_process_status(context, logging.WARNING, u'Module "%s" installation overwrites existing file "%s"' % (self.module_name, dst_path))

                    self.cleep_filesystem.mkdir(os.path.dirname(dst_path))
                    if not self.cleep_filesystem.copy(src_path, dst_path):
                        return False

                    # keep track of copied file for uninstall
                    context.install_log_fd.write(u'%s\n' % dst_path)
                    context.install_log_fd.flush()

                elif f.startswith(FRONTEND_DIR):
                    # copy ui files
                    src_path = os.path.join(extract_path, f)
                    dst_path = os.path.join(PATH_FRONTEND, f).replace(FRONTEND_DIR, u'')
                    self.logger.trace(u'Frontend src=%s dst=%s' % (src_path, dst_path))
                    self.cleep_filesystem.mkdir(os.path.dirname(dst_path))
                    if not self.cleep_filesystem.copy(src_path, dst_path):
                        return False

                    # keep track of copied file for uninstall
                    context.install_log_fd.write(u'%s\n' % dst_path)
                    context.install_log_fd.flush()

                else:
                    # drop file
                    self.logger.debug(u'Drop archive file: %s' % f)

            return True
                
        except Exception as e:
            self.__log_process_status(context, logging.NOTSET, u'Exception occured during module "%s" files copy:' % self.module_name)
            return False

    def __step(self, context, cancel=True):
        """
        Process step, check process is not canceled and send current status

        Args:
            context (Context): install context
            cancel (bool): allow cancel (True) or not (False)
        """
        if cancel and not self.running:
            raise CancelException()

        if self.callback:
            self.callback(self.get_status())

    def __rollback_install(self, context):
        """
        Rollback installation, removing installed files
        """
        self.logger.debug(u'Rollbacking installation')
        # remove installed files
        if context.install_log is not None and os.path.exists(context.install_log):
            try:
                fd = self.cleep_filesystem.open(context.install_log, u'r')
                lines = fd.readlines()
                for line in lines:
                    self.cleep_filesystem.rm(line.strip())
                self.cleep_filesystem.rmdir(os.path.dirname(context.install_log))

            except:
                self.__log_process_status(context, logging.NOTSET, u'Unable to revert "%s" module installation:' % self.module_name)

    def run(self):
        """
        Run install
        """
        # init
        self.status = self.STATUS_INSTALLING
        context = Context()
        rollback = False
        context.install_log = None
        context.install_log_fd = None
        context.extract_path = None
        context.archive_path = None

        self.__log_process_status(context, logging.INFO, u'Start module "%s" installation' % self.module_name)

        try:
            # enable write mode
            self.cleep_filesystem.enable_write()

            # install local module
            if u'local' in self.module_infos and self.module_infos[u'local'] is True:
                # nothing to process for local modules, quit current process triggering no error
                raise LocalModuleException()
        
            # open log file for writing installed files
            context.install_log = os.path.join(PATH_INSTALL, self.module_name, u'%s.log' % self.module_name)
            self.logger.debug(u'Create install log file "%s"' % context.install_log)
            try:
                self.cleep_filesystem.mkdirs(os.path.join(PATH_INSTALL, self.module_name))
                context.install_log_fd = self.cleep_filesystem.open(context.install_log, u'w')
                context.install_log_fd.flush()
            except:
                self.__log_process_status(context, logging.NOTSET, u'Exception occured during install log init "%s":' % path)
                self.status = self.STATUS_ERROR_INTERNAL
                raise Exception(u'Forced exception')
            self.__step(context)

            # download module package
            if not self.__download_archive(context):
                self.status = self.STATUS_ERROR_DOWNLOAD
                raise ForcedException()
            self.__step(context)

            # extract archive
            if not self.__extract_archive(context):
                self.status = self.STATUS_ERROR_EXTRACT
                raise ForcedException()
            self.__step(context)

            # copy uninstall scripts to install path (to make them available during uninstallation)
            if not self.__backup_scripts(context):
                # TODO handle fs errors
                raise ForcedException()

            # pre installation script
            if not self.__run_script(context, u'preinst.sh'):
                self.status = self.STATUS_ERROR_PREINST
                raise ForcedException()
            self.__step(context)

            # copy module files
            if not self.__copy_module_files(context):
                self.status = self.STATUS_ERROR_COPY
                raise ForcedException()
            self.__step(context, cancel=False)

            # post installation script
            if not self.__run_script(context, u'postinst.sh'):
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
            rollback = True
            self.status = self.STATUS_CANCELED

        except ForcedException:
            # error during installation, nothing else to do here
            rollback = True

        except:
            # unexpected error occured, invalid state
            rollback = True
            self.status = self.STATUS_ERROR_INTERNAL

            # report crash
            self.crash_report.report_exception()

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
                self.__log_process_status(context, logging.NOTSET, u'Exception during "%s" install cleaning:' % self.module_name)

            if rollback:
                # perform requested rollback
                self.__log_process_status(context, logging.INFO, u'Error occured during module "%s" install, rollback installation' % self.module_name)
                self.__rollback_install(context)

            # disable write mode
            self.cleep_filesystem.disable_write()

        # finalize installation
        success = True if self.status==self.STATUS_INSTALLED else False
        self.__log_process_status(context, logging.INFO, u'Module "%s" installation terminated (success:%s, rollback:%s)' % (self.module_name, success, rollback))
        self.__step(context, cancel=False)





class UpdateModule(threading.Thread):
    """
    Update CleepOS module
    """
    STATUS_IDLE = 0
    STATUS_UPDATING = 1
    STATUS_UPDATED = 2
    STATUS_ERROR = 3

    def __init__(self, module, module_infos, force_uninstall, callback, cleep_filesystem, crash_report):
        """
        Constructor

        Args:
            module (string): module name to install
            update_process (bool): True if module uninstall occured during update process
            force_uninstall (bool): force module uninstall even if error occured
            callback (function): status callback
            cleep_filesystem (CleepFilesystem): CleepFilesystem singleton
            crash_report (CrashReport): Crash report instance
        """
        threading.Thread.__init__(self)
        threading.Thread.daemon = True

        # logger   
        self.logger = logging.getLogger(self.__class__.__name__)
        # self.logger.setLevel(logging.DEBUG)

        # members
        self.module = module
        self.module_infos = module_infos
        self.force_uninstall = force_uninstall
        self.callback = callback
        self.cleep_filesystem = cleep_filesystem
        self.crash_report = crash_report
        self.status = self.STATUS_IDLE
        self.__is_uninstalling = True
        self.__uninstall_status = {
            u'module': self.module,
            u'status': InstallModule.STATUS_IDLE,
            u'prescript': {u'stdout': [], u'stderr':[], u'returncode': None},
            u'postscript': {u'stdout': [], u'stderr':[], u'returncode': None},
            u'updateprocess': True,
            u'process': [],
        }
        self.__install_status = {
            u'module': self.module,
            u'status': UninstallModule.STATUS_IDLE,
            u'prescript': {u'stdout': [], u'stderr':[], u'returncode': None},
            u'postscript': {u'stdout': [], u'stderr':[], u'returncode': None},
            u'updateprocess': True,
            u'process': [],
        }

    def get_status(self):
        """
        Return update status

        Return:
            dict: current status
                {
                    status (int): see STATUS_XXX
                    uninstall (dict): dict as returned by uninstall module status
                    install (dict): dict as returned by uninstall module status
                    module (string): module name
                }
        """
        return {
            u'module': self.module,
            u'status': self.status,
            u'uninstall': self.__uninstall_status,
            u'install': self.__install_status,
        }

    def __status_callback(self, status):
        """
        Install/Uninstall status callback

        Args:
            status (dict): status returned by install/uninstall
        """
        if self.__is_uninstalling:
            # callback from uninstall process
            self.logger.debug('Update callback from uninstall: %s' % status)
            self.__uninstall_status[u'status'] = status[u'status']
            self.__uninstall_status[u'prescript'] = status[u'prescript']
            self.__uninstall_status[u'postscript'] = status[u'postscript']
            self.__uninstall_status[u'process'] = status[u'process']

        else:
            # callback from install process
            self.logger.debug('Update callback from install: %s' % status)
            self.__install_status[u'status'] = status[u'status']
            self.__install_status[u'prescript'] = status[u'prescript']
            self.__install_status[u'postscript'] = status[u'postscript']
            self.__install_status[u'process'] = status[u'process']

        if self.callback:
            self.callback(self.get_status())

    def run(self):
        """
        Run module update
        """
        try:
            # init
            self.logger.info(u'Start module "%s" update' % self.module)
            error_uninstall = False
            error_install = False
            self.status = self.STATUS_UPDATING

            # run uninstall
            self.__is_uninstalling = True
            uninstall = UninstallModule(self.module, self.module_infos, True, self.force_uninstall, self.__status_callback, self.cleep_filesystem, self.crash_report)
            uninstall.start()
            time.sleep(0.5)
            while uninstall.get_status()[u'status']==uninstall.STATUS_UNINSTALLING:
                time.sleep(0.5)
            if uninstall.get_status()[u'status']!=uninstall.STATUS_UNINSTALLED:
                # module can have error during uninstall but all process is still done
                self.logger.warning(u'Error during module "%s" update: uninstall encountered errors but continue anyway the new version installation' % self.module)
                error_uninstall = True

            # callback
            if self.callback:
                self.callback(self.get_status())
            
            # run new package install
            self.__is_uninstalling = False
            install = InstallModule(self.module, self.module_infos, True, self.__status_callback, self.cleep_filesystem, self.crash_report)
            install.start()
            time.sleep(0.5)
            while install.get_status()[u'status']==install.STATUS_INSTALLING:
                time.sleep(0.5)

            # check install status
            if install.get_status()[u'status']!=install.STATUS_INSTALLED:
                self.status = self.STATUS_ERROR
                error_install = True
                self.logger.error(u'Error during module "%s" update: install encountered errors' % self.module)

            else:
                # module updated
                self.status = self.STATUS_UPDATED
    
            # callback
            if self.callback:
                self.callback(self.get_status())

        except:
            self.status = self.STATUS_ERROR
            error_install = True
            self.logger.exception(u'Error occured updating module "%s"' % self.module)

        if error_install:
            self.logger.info(u'Module "%s" update terminated (success: False)' % self.module)
        elif error_uninstall:
            self.logger.info(u'Module "%s" update terminated (success: True with error during uninstall)' % self.module)
        else:
            self.logger.info(u'Module "%s" update terminated (success: True)' % self.module)

        # final callback
        if self.callback:
            self.callback(self.get_status())

