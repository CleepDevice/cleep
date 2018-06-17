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
from raspiot.libs.console import EndlessConsole
from raspiot.raspiot import RaspIotModule
from raspiot.libs.download import Download


PATH_FRONTEND = u'/opt/raspiot/html'
PATH_INSTALL = u'/etc/raspiot/install/'
FRONTEND_DIR = u'frontend/'
BACKEND_DIR = u'backend/'


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

    def __init__(self, module, update_process, callback, cleep_filesystem):
        """
        Constructor

        Args:
            module (string): module name to install
            update_process (bool): True if module uninstall occured during update process
            callback (function): status callback
            cleep_filesystem (CleepFilesystem): CleepFilesystem singleton
        """
        threading.Thread.__init__(self)
        threading.Thread.daemon = True

        #logger   
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)

        #members
        self.status = self.STATUS_IDLE
        self.update_process = update_process
        self.raspiot_path = os.path.dirname(inspect.getfile(RaspIotModule))
        self.running = True
        self.module = module
        self.cleep_filesystem = cleep_filesystem
        self.__script_running = True
        self.__pre_script_execution = False
        self.__pre_script_status = {u'stdout': [], u'stderr':[], u'returncode': None}
        self.__post_script_status = {u'stdout': [], u'stderr':[], u'returncode': None}
        self.callback = callback

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
                }
        """
        return {
            u'module': self.module,
            u'status': self.status,
            u'prescript': self.__pre_script_status,
            u'postscript': self.__post_script_status,
            u'updateprocess': self.update_process
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

        #script execution terminated
        self.__script_running = False

    def __execute_script(self, path):
        """
        Execute specified script

        Args:
            script (string): script path

        Return
        """
        #init
        os.chmod(path, stat.S_IEXEC)

        #exec
        self.logger.debug(u'Executing "%s" script' % path)
        console = EndlessConsole(path, self.__script_callback, self.__script_terminated_callback)
        out = False

        #launch script execution
        console.start()

        #monitor end of script execution
        while self.__script_running:
            #pause
            time.sleep(0.25)

        #check script result
        if self.__pre_script_execution and self.__pre_script_status[u'returncode']==0:
            out = True
        elif self.__post_script_status[u'returncode']==0:
            out = True


        return out

    def start(self):
        """
        Run install
        """
        #init
        self.logger.info(u'Start module "%s" uninstallation' % self.module)
        self.status = self.STATUS_UNINSTALLING
        error = False
        module_log = None
        preuninst_sh = None
        postuninst_sh = None
        error_during_prescript = False
        error_during_remove = False
        error_during_postscript = False

        try:
            #pre uninstallation script
            try:
                self.__pre_script_execution = True
                preuninst_sh = os.path.join(os.path.join(PATH_INSTALL, self.module, u'preuninst.sh'))
                if os.path.exists(preuninst_sh):
                    self.__script_running = True
                    if not self.__execute_script(preuninst_sh):
                        #script failed
                        raise Exception(u'')
                else:
                    self.logger.debug(u'No preuninst script found at "%s"' % preuninst_sh)

            except Exception as e:
                if len(e.message)>0:
                    self.logger.exception(u'Exception occured during preuninst.sh script execution of module "%s"' % self.module)
                error_during_prescript = True
                #do not stop uninstall process.

            #send status
            if self.callback:
                self.callback(self.get_status())

            #remove all installed files
            try:
                module_log = os.path.join(PATH_INSTALL, self.module, u'%s.log' % self.module)
                self.logger.debug(u'Open install log file "%s"' % module_log)
                if not os.path.exists(module_log):
                    self.logger.error(u'Unable to remove module "%s" files because "%s" file doesn\'t exist' % (self.module, module_log))
                    raise Exception(u'')
                install_log = self.cleep_filesystem.open(module_log, u'r')
                lines = install_log.readlines()
                self.cleep_filesystem.close(install_log)
                for line in lines:
                    line = line.strip()
                    if len(line)==0:
                        #empty line, drop it
                        continue

                    #try to delete file
                    if not self.cleep_filesystem.rm(line):
                        self.logger.warning(u'File "%s" was not removed during "%s" module uninstallation' % (line, self.module))

                #remove install log file and supposed frontend directory
                self.cleep_filesystem.rm(module_log)

            except Exception as e:
                if len(e.message)>0:
                    self.logger.exception(u'Exception occured during "%s" files module uninstallation' % self.module)
                error_during_remove = True
                #do not stop uninstall process

            #send status
            if self.callback:
                self.callback(self.get_status())

            #post uninstallation script
            try:
                self.__pre_script_execution = False
                postuninst_sh = os.path.join(os.path.join(PATH_INSTALL, self.module, u'postuninst.sh'))
                if os.path.exists(postuninst_sh):
                    self.__script_running = True
                    if not self.__execute_script(postuninst_sh):
                        #script failed
                        raise Exception(u'')
                else:
                    self.logger.debug(u'No postuninst script found at "%s"' % postuninst_sh)

            except Exception as e:
                if len(e.message)>0:
                    self.logger.exception(u'Exception occured during postuninst.sh script execution of module "%s"' % self.module)
                error_during_postscript = True
                #do not stop uninstall process

        except:
            #local exception raised, invalid state :S
            error = True

        finally:
            #clean stuff
            try:
                path = os.path.join(PATH_INSTALL, self.module)
                if os.path.exists(path):
                    self.cleep_filesystem.rmdir(path)
                path = os.path.join(PATH_FRONTEND, 'js/modules/%s' % self.module)
                if os.path.exists(path):
                    self.cleep_filesystem.rmdir(path)
            except:
                self.logger.exception(u'Exception during "%s" install cleaning:' % self.module)

            self.logger.debug('error=%s error_during_prescript=%s error_during_postscript=%s error_during_remove=%s' % (error, error_during_prescript, error_during_postscript, error_during_remove))
            if error:
                #error occured
                self.logger.debug(u'Error occured during "%s" module uninstallation' % self.module)
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
                #install terminated successfully
                self.status = self.STATUS_UNINSTALLED

            #send status
            if self.callback:
                self.callback(self.get_status())

        self.logger.info(u'Module "%s" uninstallation terminated (success: %s)' % (self.module, not error))





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

    def __init__(self, module, module_infos, update_process, callback, cleep_filesystem):
        """
        Constructor

        Args:
            module (string): module name to install
            module_infos (dict): all module infos from modules.json file
            update_process (bool): True if module uninstall occured during update process
            callback (function): status callback
            cleep_filesystem (CleepFilesystem): CleepFilesystem singleton
        """
        threading.Thread.__init__(self)
        threading.Thread.daemon = True

        #logger
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)

        #members
        self.callback = callback
        self.update_process = update_process
        self.status = self.STATUS_IDLE
        self.raspiot_path = os.path.dirname(inspect.getfile(RaspIotModule))
        self.running = True
        self.module = module
        self.module_infos = module_infos
        self.cleep_filesystem = cleep_filesystem
        self.__script_running = True
        self.__pre_script_execution = False
        self.__pre_script_status = {u'stdout': [], u'stderr':[], u'returncode':None}
        self.__post_script_status = {u'stdout': [], u'stderr':[], u'returncode':None}

        #make sure install log path exists
        if not os.path.exists(PATH_INSTALL):
            self.cleep_filesystem.mkdir(PATH_INSTALL, True)

    def cancel(self):
        """
        Cancel installation
        """
        self.logger.info(u'Module "%s" installation canceled' % self.module)
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
                }
        """
        return {
            u'module': self.module,
            u'status': self.status,
            u'prescript': self.__pre_script_status,
            u'postscript': self.__post_script_status,
            u'updateprocess': self.update_process
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

        #script execution terminated
        self.__script_running = False

    def __execute_script(self, path):
        """ 
        Execute specified script

        Args:
            path (string): script path

        Return
        """
        #init
        os.chmod(path, stat.S_IEXEC)

        #exec
        self.logger.debug(u'Executing %s script' % path)
        console = EndlessConsole(path, self.__script_callback, self.__script_terminated_callback)
        out = False

        #launch script execution
        console.start()

        #monitor end of script execution
        while self.__script_running:
            #pause
            time.sleep(0.25)

        #check script result
        if self.__pre_script_execution and self.__pre_script_status[u'returncode']==0:
            out = True
        elif self.__post_script_status[u'returncode']==0:
            out = True

        return out

    def start(self):
        """
        Run install
        """
        #init
        self.logger.info(u'Start module "%s" installation' % self.module)
        self.status = self.STATUS_INSTALLING
        error = False
        install_log = None
        install_log_fd = None
        extract_path = None
        archive_path = None

        try:
            #open file for writing installed files
            install_log = os.path.join(PATH_INSTALL, self.module, u'%s.log' % self.module)
            self.logger.debug(u'Create install log file "%s"' % install_log)
            try:
                self.cleep_filesystem.mkdirs(os.path.join(PATH_INSTALL, self.module))
                install_log_fd = self.cleep_filesystem.open(install_log, u'w')
                install_log_fd.flush()
            except:
                self.logger.exception(u'Exception occured during install log init "%s":' % path)
                self.status = self.STATUS_ERROR_INTERNAL
                raise Exception(u'Forced exception')

            #canceled ?
            if not self.running:
                raise Exception(u'Canceled exception')

            #send status
            if self.callback:
                self.callback(self.get_status())

            #download module package
            self.logger.debug(u'Download file "%s"' % self.module_infos[u'download'])
            try:
                download = Download(self.cleep_filesystem)
                archive_path = download.download_file_advanced(self.module_infos[u'download'], check_sha256=self.module_infos[u'sha256'])
                if archive_path is None:
                    download_status = download.get_status()
                    if download_status==download.STATUS_ERROR:
                        self.error = u'Error during "%s" download: internal error' % self.module_infos[u'download']
                    if download_status==download.STATUS_ERROR_INVALIDSIZE:
                        self.error = u'Error during "%s" download: invalid filesize' % self.module_infos[u'download']
                    elif download_status==download.STATUS_ERROR_BADCHECKSUM:
                        self.error = u'Error during "%s" download: invalid checksum' % self.module_infos[u'download']
                    else:
                        self.error = u'Error during "%s" download: unknown error' % self.module_infos[u'download']
    
                    self.logger.error(self.error)
                    self.status = self.STATUS_ERROR_DOWNLOAD
                    raise Exception(u'')

            except Exception as e:
                if len(e.message)>0:
                    self.logger.exception(u'Exception occured during module "%s" package download "%s"' % (self.module, self.module_infos[u'download']))
                self.status = self.STATUS_ERROR_DOWNLOAD
                raise Exception(u'Forced exception')

            #canceled ?
            if not self.running:
                raise Exception(u'Canceled exception')

            #send status
            if self.callback:
                self.callback(self.get_status())

            #extract archive
            self.logger.debug(u'Extracting archive "%s"' % archive_path)
            try:
                zipfile = ZipFile(archive_path, u'r')
                extract_path = tempfile.mkdtemp()
                self.logger.debug(u'Extract archive to "%s"' % extract_path)
                zipfile.extractall(extract_path)
                zipfile.close()

            except:
                self.logger.exception(u'Error decompressing module "%s" package "%s" in "%s":' % (self.module, archive_path, extract_path))
                self.status = self.STATUS_ERROR_EXTRACT
                raise Exception(u'Forced exception')

            #canceled ?
            if not self.running:
                raise Exception(u'Canceled exception')

            #send status
            if self.callback:
                self.callback(self.get_status())

            #copy uninstall scripts to install path
            src_path = os.path.join(extract_path, u'preuninst.sh')
            dst_path = os.path.join(PATH_INSTALL, self.module, u'preuninst.sh')
            if os.path.exists(src_path):
                self.cleep_filesystem.copy(src_path, dst_path)
            else:
                self.logger.debug(u'Script preuninst.sh not found in archive')
            src_path = os.path.join(extract_path, u'postuninst.sh')
            dst_path = os.path.join(PATH_INSTALL, self.module, u'postuninst.sh')
            if os.path.exists(src_path):
                self.cleep_filesystem.copy(src_path, dst_path)
            else:
                self.logger.debug(u'Script postuninst.sh not found in archive')

            #pre installation script
            try:
                self.__pre_script_execution = True
                path = os.path.join(extract_path, u'preinst.sh')
                if os.path.exists(path):
                    self.__script_running = True
                    if not self.__execute_script(path):
                        raise Exception(u'')
                else:
                    self.logger.debug('No preinst script found at "%s"' % path)

            except Exception as e:
                if len(e.message)>0:
                    self.logger.exception(u'Exception occured during preinst.sh script execution of module "%s"' % self.module)
                self.status = self.STATUS_ERROR_PREINST
                raise Exception(u'Forced exception')

            #canceled ?
            if not self.running:
                raise Exception(u'Canceled exception')

            #send status
            if self.callback:
                self.callback(self.get_status())

            #copy module files
            try:
                #list archive files
                archive_files = []
                for directory, _, files in os.walk(extract_path):
                    for filename in files:
                        full_path = os.path.join(directory, filename)
                        rel_path = full_path.replace(extract_path, u'')
                        if rel_path[0]==u'/':
                            rel_path = rel_path[1:]
                        archive_files.append(rel_path)
                self.logger.debug(u'archive_files: %s' % archive_files)

                #process them according to their directory
                for f in archive_files:
                    if f.startswith(BACKEND_DIR):
                        #copy python files
                        src_path = os.path.join(extract_path, f)
                        dst_path = os.path.join(self.raspiot_path, f).replace(BACKEND_DIR, u'')
                        self.logger.debug(u'src=%s dst=%s' % (src_path, dst_path))
                        self.cleep_filesystem.mkdir(os.path.dirname(dst_path))
                        if not self.cleep_filesystem.copy(src_path, dst_path):
                            raise Exception(u'Forced exception')

                        #keep track of copied file for uninstall
                        install_log_fd.write(u'%s\n' % dst_path)
                        install_log_fd.flush()

                    elif f.startswith(FRONTEND_DIR):
                        #copy ui files
                        src_path = os.path.join(extract_path, f)
                        dst_path = os.path.join(PATH_FRONTEND, f).replace(FRONTEND_DIR, u'')
                        self.logger.debug(u'src=%s dst=%s' % (src_path, dst_path))
                        self.cleep_filesystem.mkdir(os.path.dirname(dst_path))
                        if not self.cleep_filesystem.copy(src_path, dst_path):
                            raise Exception(u'Forced exception')

                        #keep track of copied file for uninstall
                        install_log_fd.write(u'%s\n' % dst_path)
                        install_log_fd.flush()

                    else:
                        #drop file
                        self.logger.debug(u'Drop archive file: %s' % f)
                
                    #canceled ?
                    if not self.running:
                        raise Exception(u'Canceled exception')

            except Exception as e:
                if e.message!=u'Canceled exception':
                    self.logger.exception(u'Exception occured during module "%s" files copy:' % self.module)
                    self.status = self.STATUS_ERROR_COPY
                raise Exception(u'Forced exception')

            #send status
            if self.callback:
                self.callback(self.get_status())

            #post installation script
            try:
                self.__pre_script_execution = False
                path = os.path.join(extract_path, u'postinst.sh')
                if os.path.exists(path):
                    self.__script_running = True
                    if not self.__execute_script(path):
                        raise Exception(u'')
                else:
                    self.logger.debug('No postinst script found at "%s"' % path)

            except Exception as e:
                if len(e.message)>0:
                    self.logger.exception(u'Exception occured during postinst.sh script execution of module "%s"' % self.module)
                self.status = self.STATUS_ERROR_POSTINST
                raise Exception(u'Forced exception')
                    
        except Exception as e:
            #local exception raised, revert installation
            #if self.logger.getEffectiveLevel()==logging.DEBUG:
            #    self.logger.exception(e)
            error = True

        finally:
            #clean stuff
            try:
                if install_log_fd:
                    self.cleep_filesystem.close(install_log_fd)
                if extract_path:
                    self.cleep_filesystem.rmdir(extract_path)
                if archive_path:
                    self.cleep_filesystem.rm(archive_path)
            except:
                self.logger.exception(u'Exception during "%s" install cleaning:' % self.module)

            if self.running==False:
                #installation canceled
                self.status = self.STATUS_CANCELED

            elif error:
                #error occured, revert installation
                self.logger.debug(u'Error occured during "%s" install, revert installed files' % self.module)
                if self.status==self.STATUS_INSTALLING:
                    self.status = self.STATUS_ERROR_INTERNAL
                
                #remove installed files
                if install_log is not None and os.path.exists(install_log):
                    try:
                        fd = self.cleep_filesystem.open(install_log, u'r')
                        lines = fd.readlines()
                        for line in lines:
                            self.cleep_filesystem.rm(line.strip())
                        self.cleep_filesystem.rmdir(os.path.dirname(install_log))

                    except:
                        self.logger.exception(u'Unable to revert "%s" module installation:' % self.module)

            else:
                #install terminated successfully
                self.status = self.STATUS_INSTALLED

            #send status
            if self.callback:
                self.callback(self.get_status())

        self.logger.info(u'Module "%s" installation terminated (success: %s)' % (self.module, not error))





class UpdateModule(threading.Thread):
    """
    """
    STATUS_IDLE = 0
    STATUS_UPDATING = 1
    STATUS_UPDATED = 2
    STATUS_ERROR = 3

    def __init__(self, module, module_infos, callback, cleep_filesystem):
        """
        Constructor

        Args:
            module (string): module name to install
            update_process (bool): True if module uninstall occured during update process
            callback (function): status callback
            cleep_filesystem (CleepFilesystem): CleepFilesystem singleton
        """
        threading.Thread.__init__(self)
        threading.Thread.daemon = True

        #logger   
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)

        #members
        self.module = module
        self.module_infos = module_infos
        self.callback = callback
        self.cleep_filesystem = cleep_filesystem
        self.status = self.STATUS_IDLE
        self.__is_uninstalling = True
        self.__uninstall_status = {
            u'status': InstallModule.STATUS_IDLE,
            u'prescript': {u'stdout': [], u'stderr':[], u'returncode': None},
            u'postscript': {u'stdout': [], u'stderr':[], u'returncode': None}
        }
        self.__install_status = {
            u'status': UninstallModule.STATUS_IDLE,
            u'prescript': {u'stdout': [], u'stderr':[], u'returncode': None},
            u'postscript': {u'stdout': [], u'stderr':[], u'returncode': None}
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
            u'status': self.status,
            u'uninstall': self.__uninstall_status,
            u'install': self.__install_status,
            u'module': self.module
        }

    def __callback(self, status):
        """
        Install/Uninstall callback

        Args:
            status (dict): status returned by install/uninstall
        """
        if self.__is_uninstalling:
            #callback from uninstall process
            self.logger.debug('Update callback from uninstall: %s' % status)
            self.__uninstall_status[u'status'] = status[u'status']
            self.__uninstall_status[u'prescript'] = status[u'prescript']
            self.__uninstall_status[u'postscript'] = status[u'postscript']

        else:
            #callback from install process
            self.logger.debug('Update callback from install: %s' % status)
            self.__install_status[u'status'] = status[u'status']
            self.__install_status[u'prescript'] = status[u'prescript']
            self.__install_status[u'postscript'] = status[u'postscript']

        if self.callback:
            self.callback(self.get_status())

    def start(self):
        """
        Process module update
        """
        #init
        self.logger.info(u'Start module "%s" update' % self.module)
        error_uninstall = False
        error_install = False
        self.status = self.STATUS_UPDATING

        #run uninstall
        self.__is_uninstalling = True
        uninstall = UninstallModule(self.module, True, self.__callback, self.cleep_filesystem)
        uninstall.start()
        time.sleep(0.5)
        while uninstall.get_status()[u'status']==uninstall.STATUS_UNINSTALLING:
            time.sleep(0.5)
        if uninstall.get_status()[u'status']!=uninstall.STATUS_UNINSTALLED:
            #module can have error during uninstall but all process is still done
            self.logger.warning(u'Error during module "%s" update: uninstall encountered errors but continue anyway the new version installation' % self.module)
            error_uninstall = True

        #callback
        if self.callback:
            self.callback(self.get_status())
        
        #run new package install
        self.__is_uninstalling = False
        install = InstallModule(self.module, self.module_infos, True, self.__callback, self.cleep_filesystem)
        install.start()
        time.sleep(0.5)
        while install.get_status()[u'status']==install.STATUS_INSTALLING:
            time.sleep(0.5)

        #check install status
        if install.get_status()[u'status']!=install.STATUS_INSTALLED:
            self.status = self.STATUS_ERROR
            error_install = True
            self.logger.error(u'Error during module "%s" update: install encountered errors' % self.module)

        else:
            #module updated
            self.status = self.STATUS_UPDATED

        #callback
        if self.callback:
            self.callback(self.get_status())

        if error_install:
            self.logger.info(u'Module "%s" update terminated (success: False)' % self.module)
        elif error_uninstall:
            self.logger.info(u'Module "%s" update terminated (success: True with error during uninstall)' % self.module)
        else:
            self.logger.info(u'Module "%s" update terminated (success: True)' % self.module)

