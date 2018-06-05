#!/usr/bin/env python
# -*- coding: utf-8 -*

import logging
import time
import os
import inspect
from zipfile import ZipFile
import threading
import tempfile
from raspiot.libs.console import EndlessConsole
from raspiot.raspiot import RaspIotModule
from raspiot.libs.download import Download
from raspiot.libs.raspiotconf import RaspiotConf

__all__ = ['Install']

PATH_FRONTEND = u'/opt/raspiot/html'
PATH_INSTALL = u'/etc/raspiot/install/'
FRONTEND_DIR = u'frontend/'
BACKEND_DIR = u'backend/'

class UninstallModule(threading.Thread):
    """
    Uninstall module in background task
    """
    STATUS_IDLE = 0
    STATUS_UNINSTALLING = 1
    STATUS_UNINSTALLED = 2
    STATUS_ERROR_INTERNAL = 3
    STATUS_ERROR_PREUNINST = 4
    STATUS_ERROR_REMOVE = 5
    STATUS_ERROR_POSTUNINST = 6

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
        self.logger.setLevel(logging.DEBUG)

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
        if self.__pre_script_execution:
            if stdout:
                self.__pre_script_status[u'stdout'].append(stdout)
            if stderr:
                self.__pre_script_status['stderr'].append(stderr)

        elif self.__post_script_execution:
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

    def __execute_script(self, script):
        """
        Execute specified script

        Args:
            script (string): script path

        Return
        """
        #init
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
        if self.__script_return_code==0:
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

        try:
            #pre uninstallation script
            try:
                self.__pre_script_execution = True
                preuninst_sh = os.path.join(os.path.join(PATH_INSTALL, u'%s_preuninst.sh' % self.module))
                if os.path.exists(preuninst_sh):
                    self.__script_running = True
                    self.__execute_script(preuninst_sh)

            except Exception as e:
                self.logger.exception(u'Exception occured during preuninst.sh script execution of module "%s"' % self.module)
                self.status = self.STATUS_ERROR_PREUNINST
                raise Exception(u'Forced exception')

            #send status
            if self.callback:
                self.callback(self.get_status())

            #remove all installed files
            try:
                module_log = os.path.join(PATH_INSTALL, u'%s.log' % self.module)
                self.logger.debug(u'Open install log file "%s"' % module_log)
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

                #remove install log file
                self.cleep_filesystem.rm(module_log)

            except:
                self.logger.exception(u'Exception occured during "%s" files module uninstallation' % self.module)
                self.status = self.STATUS_ERROR_REMOVE
                raise Exception(u'Forced exception')

            #send status
            if self.callback:
                self.callback(self.get_status())

            #post uninstallation script
            try:
                self.__pre_script_execution = False
                postuninst_sh = os.path.join(os.path.join(PATH_INSTALL, u'%s_postuninst.sh' % self.module))
                if os.path.exists(postuninst_sh):
                    self.__script_running = True
                    self.__execute_script(postuninst_sh)

            except Exception as e:
                self.logger.exception(u'Exception occured during postuninst.sh script execution of module "%s"' % self.module)
                self.status = self.STATUS_ERROR_POSTUNINST
                raise Exception(u'Forced exception')

        except:
            #local exception raised, invalid state :S
            error = True

        finally:
            #clean stuff
            try:
                if module_log:
                    self.cleep_filesystem.rm(module_log)
                if preuninst_sh:
                    self.cleep_filesystem.rm(preuninst_sh)
                if postuninst_sh:
                    self.cleep_filesystem.rm(postuninst_sh)
            except:
                self.logger.exception(u'Exception during "%s" install cleaning:' % self.module)

            if error:
                #error occured
                self.logger.debug('Error occured during "%s" module uninstallation' % self.module)
                if self.status==self.STATUS_UNINSTALLING:
                    self.status = self.STATUS_ERROR_INTERNAL
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
        self.logger.setLevel(logging.DEBUG)

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
        if self.__pre_script_execution:
            if stdout:
                self.__pre_script_status[u'stdout'].append(stdout)
            if stderr:
                self.__pre_script_status['stderr'].append(stderr)

        elif self.__post_script_execution:
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

    def __execute_script(self, script):
        """
        Execute specified script

        Args:
            script (string): script path

        Return
        """
        #init
        self.logger.debug(u'Executing %s script' % path)
        console = EndlessConsole(path, self.__script_callback, self.__script_terminated_callback)
        out = False

        #launch script execution
        console.start()

        #monitor end of script execution
        while self.__script_running:
            #handle installation canceling
            if not self.running:
                #kill process
                console.kill()

                #set output value and stop statement
                out = False
                break
            
            #pause
            time.sleep(0.25)

        #check script result
        if self.__script_return_code==0:
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
        extract_path = None
        archive_path = None

        try:
            #open file for writing installed files
            path = os.path.join(PATH_INSTALL, u'%s.log' % self.module)
            self.logger.debug(u'Create install log file "%s"' % path)
            try:
                install_log = self.cleep_filesystem.open(path, u'w')
                install_log.flush()
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
    
                    self.logger.error(error)
                    self.status = self.STATUS_ERROR_DOWNLOAD
                    raise Exception(u'Forced exception')

            except:
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
            self.logger.debug('Extracting archive "%s"' % archive_path)
            try:
                zipfile = ZipFile(archive_path, u'r')
                extract_path = tempfile.mkdtemp()
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
            dst_path = os.path.join(PATH_INSTALL, u'%s_preuninst.sh' % self.module)
            if os.path.exists(src_path):
                self.cleep_filesystem.copy(src_path, dst_path)
            src_path = os.path.join(extract_path, u'postuninst.sh')
            dst_path = os.path.join(PATH_INSTALL, u'%s_postuninst.sh' % self.module)
            if os.path.exists(src_path):
                self.cleep_filesystem.copy(src_path, dst_path)

            #pre installation script
            try:
                self.__pre_script_execution = True
                path = os.path.join(extract_path, u'preinst.sh')
                if os.path.exists(path):
                    self.__script_running = True
                    self.__execute_script(path)

            except Exception as e:
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

                #canceled ?
                if not self.running:
                    raise Exception(u'Canceled exception')
    
                #process them according to their directory
                for f in archive_files:
                    if f.startswith(BACKEND_DIR):
                        #copy python files
                        src_path = os.path.join(extract_path, f)
                        dst_path = os.path.join(self.raspiot_path, f).replace(BACKEND_DIR, u'')
                        self.logger.debug('src=%s dst=%s' % (src_path, dst_path))
                        self.cleep_filesystem.mkdir(os.path.dirname(dst_path))
                        if not self.cleep_filesystem.copy(src_path, dst_path):
                            raise Exception(u'Forced exception')

                        #keep track of copied file for uninstall
                        install_log.write(u'%s\n' % dst_path)
                        install_log.flush()

                    elif f.startswith(FRONTEND_DIR):
                        #copy ui files
                        src_path = os.path.join(extract_path, f)
                        dst_path = os.path.join(PATH_FRONTEND, f).replace(FRONTEND_DIR, u'')
                        self.logger.debug('src=%s dst=%s' % (src_path, dst_path))
                        self.cleep_filesystem.mkdir(os.path.dirname(dst_path))
                        if not self.cleep_filesystem.copy(src_path, dst_path):
                            raise Exception(u'Forced exception')

                        #keep track of copied file for uninstall
                        install_log.write(u'%s\n' % dst_path)
                        install_log.flush()

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
                    self.__execute_script(path)
            except:
                self.logger.exception(u'Exception occured during postinst.sh script execution of module "%s"' % self.module)
                self.status = self.STATUS_ERROR_POSTINST
                raise Exception(u'Forced exception')
                    
            #canceled ?
            if not self.running:
                raise Exception(u'Canceled exception')

        except:
            #local exception raised, revert installation
            error = True

        finally:
            #clean stuff
            try:
                if install_log:
                    self.cleep_filesystem.close(install_log)
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
                self.logger.debug('Error occured during "%s" install, revert installed files' % self.module)
                if self.status==self.STATUS_INSTALLING:
                    self.status = self.STATUS_ERROR_INTERNAL
                
                #remove installed files
                try:
                    fd = self.cleep_filesystem.open(install_log, u'r')
                    lines = fd.readlines()
                    for line in lines:
                        self.cleep_filesystem.rm(line.strip())
                except:
                    self.logger.exception(u'Unable to revert "%s" module installation:' % self.module)

            else:
                #install terminated successfully
                self.status = self.STATUS_INSTALLED

            #send status
            if self.callback:
                self.callback(self.get_status())

        self.logger.info(u'Module "%s" installation terminated (success: %s)' % (self.module, not error))





class Install():
    """
    Install helper
    This class helps you to install different kind of files:
     - deb files using dpkg
     - tar.gz using tar
     - zip using unzip
     - raspiot module installation and uninstallation (ok class name is not correct ;) )
     - system packages install/uninst using apt-get command
    """

    STATUS_IDLE = 0
    STATUS_PROCESSING = 1
    STATUS_ERROR = 2
    STATUS_DONE = 3
    STATUS_CANCELED = 4

    def __init__(self, cleep_filesystem, status_callback, blocking=False):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
            status_callback (function): status callback. Params: status
            blocking (bool): enable or not blocking mode. If blocking mode is enabled, all functions are blocking
        """
        #logger
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)

        #members
        self.cleep_filesystem = cleep_filesystem
        self.blocking = blocking
        self.__console = None
        self.__cancel = False
        self.status = self.STATUS_IDLE
        self.status_callback = status_callback
        self.stdout = []
        self.stderr = []
        self.__running = True

    def cancel(self):
        """
        Cancel current install
        """
        self.status = self.STATUS_CANCELED
        if self.__console:
            self.__console.stop()
        self.__running = False

    def get_status(self):
        """
        Return current installation status

        Return:
            dict: status::
                {
                    status (string): current status
                    stdout (list): list of messages received on console
                    stderr (list): list of messages received on stderr
                }
        """
        return {
            u'status': self.status,
            u'stdout': self.stdout,
            u'stderr': self.stderr
        }

    def __reset_status(self, status):
        """
        Reset status

        Args:
            status (int): status to set (use self.STATUS_XXX)
        """
        self.status = status
        self.stdout = []
        self.stderr = []

    def __callback_end(self):
        """
        End of process callback
        """
        self.logger.debug(u'End of command')

        #update status if necessary
        if self.status!=self.STATUS_ERROR and self.status!=self.STATUS_CANCELED:
            self.status = self.STATUS_DONE

        #send for the last time current status
        self.status_callback(self.get_status())

        #unblock function call
        self.__running = False

        #disable write at end of command execution
        self.cleep_filesystem.disable_write()

    def __callback_quiet(self, stdout, stderr):
        """
        Quiet output. Does nothing
        """
        pass

    def refresh_system_packages(self):
        """
        Refresh sytem packages list
        """
        if self.status==self.STATUS_PROCESSING:
            raise Exception(u'Installer is already processing')

        #update status
        self.__reset_status(self.STATUS_PROCESSING)

        #refresh packages
        command = u'/usr/bin/aptitude update'
        self.logger.debug(u'Command: %s' % command)
        self.__console = EndlessConsole(command, self.__callback_quiet, self.__callback_end)
        self.__console.start()

        #blocking mode
        if self.blocking:
            self.__running = True
            while self.__running:
                time.sleep(0.25)
            
            if self.status==self.STATUS_DONE:
                return True
            return False

        else:
            #useless result
            return None

    def __callback_package(self, stdout, stderr):
        """
        Package install callback

        Args:
            stdout (list): console stdout
            stderr (list): console stderr
        """
        #append current stdout/stderr
        if stdout is not None:
            self.stdout.append(stdout)
        if stderr is not None:
            self.status = self.STATUS_ERROR
            self.stderr.append(stderr)

        #send status to caller callback
        self.status_callback(self.get_status())

    def install_system_package(self, package_name):
        """
        Install package using aptitude

        Args:
            package_name (string): package name to install

        Return:
            bool: True if install succeed
        """
        if self.status==self.STATUS_PROCESSING:
            raise Exception(u'Installer is already processing')

        #update status
        self.__reset_status(self.STATUS_PROCESSING)

        #enable write
        self.cleep_filesystem.enable_write()

        #install deb
        command = u'/usr/bin/aptitude install -y "%s"' % package_name
        self.logger.debug(u'Command: %s' % command)
        self.__running = True
        self.__console = EndlessConsole(command, self.__callback_package, self.__callback_end)
        self.__console.start()

        #blocking mode
        if self.blocking:
            while self.__running:
                time.sleep(0.25)
            
            if self.status==self.STATUS_DONE:
                return True
            return False

        else:
            #useless result
            return None

    def uninstall_system_package(self, package_name, purge=False):
        """
        Install package using aptitude

        Args:
            package_name (string): package name to install
            purge (bool): purge package (remove config files)

        Return:
            bool: True if install succeed
        """
        if self.status==self.STATUS_PROCESSING:
            raise Exception(u'Installer is already processing')

        #update status
        self.__reset_status(self.STATUS_PROCESSING)

        #enable write
        self.cleep_filesystem.enable_write()

        #install deb
        action = u'remove'
        if purge:
            action = u'purge'
        command = u'/usr/bin/aptitude %s -y "%s"' % (action, package_name)
        self.logger.debug(u'Command: %s' % command)
        self.__running = True
        self.__console = EndlessConsole(command, self.__callback_package, self.__callback_end)
        self.__console.start()

        #blocking mode
        if self.blocking:
            while self.__running:
                time.sleep(0.25)
            
            if self.status==self.STATUS_DONE:
                return True
            return False

        else:
            #useless result
            return None

    def __callback_deb(self, stdout, stderr):
        """
        Deb install callback

        Args:
            stdout (list): console stdout
            stderr (list): console stderr
        """
        #append current stdout/stderr
        if stdout is not None:
            #end of command ends with broken pipe on yes execution, this is normal. Drop this unimportant message
            #https://stackoverflow.com/questions/20573282/hudson-yes-standard-output-broken-pipe
            if stdout.find(u'yes')==-1 and stdout.lower().find(u'broken pipe')==-1:
                self.stdout.append(stdout)
        if stderr is not None:
            self.status = self.STATUS_ERROR
            self.stderr.append(stderr)

        #send status to caller callback
        self.status_callback(self.get_status())

    def install_deb(self, deb):
        """
        Install .deb file using dpkg

        Return:
            bool: True if install succeed
        """
        if self.status==self.STATUS_PROCESSING:
            raise Exception(u'Installer is already processing')

        #update status
        self.__reset_status(self.STATUS_PROCESSING)

        #enable write
        self.cleep_filesystem.enable_write()

        #install deb (and dependencies)
        command = u'/usr/bin/yes | /usr/bin/dpkg -i "%s" && /usr/bin/apt-get install -f && /usr/bin/yes | /usr/bin/dpkg -i "%s"' % (deb, deb)
        self.logger.debug(u'Command: %s' % command)
        self.__running = True
        self.__console = EndlessConsole(command, self.__callback_deb, self.__callback_end)
        self.__console.start()

        #blocking mode
        if self.blocking:
            #loop
            while self.__running:
                time.sleep(0.25)
            
            if self.status==self.STATUS_DONE:
                return True
            return False

        else:
            #useless result
            return None

    def __callback_archive(self, stdout, stderr):
        """
        Deb install callback

        Args:
            stdout (list): console stdout
            stderr (list): console stderr
        """
        #append current stdout/stderr
        if stdout is not None:
            self.stdout.append(stdout)
        if stderr is not None:
            self.status = self.STATUS_ERROR
            self.stderr.append(stderr)

        #send status to caller callback
        self.status_callback(self.get_status())
        
    def install_archive(self, archive, install_path):
        """
        Install archive (.tar.gz, .zip) to specified install path

        Args:
            archive (string): archive full path
            install_path (string): installation fullpath directory

        Return:
            bool: True if install succeed
        """
        if self.status==self.STATUS_PROCESSING:
            raise Exception(u'Installer is already processing')

        #check params
        if archive is None or len(archive.strip())==0:
            raise Exception(u'Parameter "archive" is missing')
        if install_path is None or len(install_path.strip())==0:
            raise Exception(u'Parameter "install_path" is missing')
        if not os.path.exists(archive):
            raise Exception(u'Archive does not exist')

        #create output dir if it isn't exist
        if not os.path.exists(install_path):
            self.cleep_filesystem.mkdir(install_path, recursive=True)

        #update status
        self.__reset_status(self.STATUS_PROCESSING)

        #get archive decompressor according to archive extension
        command = None
        dummy, ext = os.path.splitext(archive)
        if ext==u'.gz':
            _, ext = os.path.splitext(dummy)
            if ext==u'.tar':
                command = u'/bin/tar xzvf "%s" -C "%s"' % (archive, install_path)

        elif ext==u'.zip':
            command = u'/usr/bin/unzip "%s" -d "%s"' % (archive, install_path)

        #execute command
        if command is None:
            raise Exception(u'File format not supported. Only zip and tar.gz supported.')
        else:
            #enable write
            self.cleep_filesystem.enable_write()

            #execute command
            self.logger.debug(u'Command: %s' % command)
            self.__running = True
            self.__console = EndlessConsole(command, self.__callback_archive, self.__callback_end)
            self.__console.start()

        #blocking mode
        if self.blocking:
            #loop
            while self.__running:
                time.sleep(0.25)

            if self.status==self.STATUS_DONE:
                return True
            return False

        else:
            #useless result
            return None

    def __callback_install_module(self, status):
        """
        Module install callback

        Args:
            status (dict): module status::
                {
                    module (string): module name
                    status (int): module process status
                    prescript (dict): {stderr, stdout, returncode}
                    postscript (dict): {stderr, stdout, returncode}
                    updateprocess (bool): uninstall triggered by module update
                }
        """
        #save status
        if status[u'status']==InstallModule.STATUS_IDLE:
            self.status = self.STATUS_IDLE
        elif status[u'status']==InstallModule.STATUS_INSTALLING:
            self.status = self.STATUS_PROCESSING
        elif status[u'status']==InstallModule.STATUS_CANCELED:
            self.status = self.STATUS_CANCELED
        elif status[u'status']==InstallModule.STATUS_INSTALLED:
            self.status = self.STATUS_DONE
        else:
            self.status = self.STATUS_ERROR

        #save stdout/stderr at end of process
        if self.status in (self.STATUS_CANCELED, self.STATUS_DONE, self.STATUS_ERROR):
            self.stdout = [u'Pre-script stdout:'] + status[u'prescript'][u'stdout'] + [u'Pre-script return code: %s' % status[u'prescript'][u'returncode']]
            self.stdout += [u'', u'Post-script process:'] + status[u'postscript'][u'stdout'] + [u'Post-script return code: %s' % status[u'postscript'][u'returncode']]
            self.stderr = [u'Pre-script stderr:'] + status[u'prescript'][u'stderr'] + [u'Pre-script return code: %s' % status[u'prescript'][u'returncode']]
            self.stderr += [u'', u'Post-script stderr:'] + status[u'postscript'][u'stderr'] + [u'Post-script return code: %s' % status[u'postscript'][u'returncode']]

        #send status
        if self.status_callback:
            current_status = self.get_status()
            #inject module name and updateprocess
            current_status[u'module'] = status[u'module']
            current_status[u'updateprocess'] = status[u'updateprocess']
            self.status_callback(current_status)

    def install_module(self, module, module_infos, update_process):
        """
        Install specified module

        Params:
            module (string): module name to install
            modules_infos (dict): module infos reported in modules.json
            update_process (bool): True if module uninstall occured during update process

        Returns:
            bool: True if module installed
        """
        #check params
        if module is None or len(module)==0:
            raise MissingParameter(u'Parameter "module" is missing')
        if module_infos is None or len(module_infos)==0:
            raise MissingParameter(u'Parameter "module_infos" is missing')

        #launch installation
        install = InstallModule(module, module_infos, update_process, self.__callback_install_module, self.cleep_filesystem)
        install.start()

        #blocking mode
        if self.blocking:
            #wait for end of installation
            while install.get_status()==install.STATUS_INSTALLING:
                time.sleep(0.25)

            #check install status
            if install.get_status()==install.STATUS_INSTALLED:
                self.__need_restart = True
                #update raspiot.conf
                raspiot = RaspiotConf(self.cleep_filesystem)
                return raspiot.install_module(module)

            return False

        else:
            #useless return
            return None

    def __callback_uninstall_module(self, status):
        """
        Module uninstall callback

        Args:
            status (dict): module status::
                {
                    module (string): module name
                    status (int): module process status
                    prescript (dict): {stderr, stdout, returncode}
                    postscript (dict): {stderr, stdout, returncode}
                    updateprocess (bool): uninstall triggered by module update
                }
        """
        #save status
        if status[u'status']==UninstallModule.STATUS_IDLE:
            self.status = self.STATUS_IDLE
        elif status[u'status']==UninstallModule.STATUS_UNINSTALLING:
            self.status = self.STATUS_PROCESSING
        elif status[u'status']==UninstallModule.STATUS_UNINSTALLED:
            self.status = self.STATUS_DONE
        else:
            self.status = self.STATUS_ERROR

        #save stdout/stderr at end of process
        if self.status in (self.STATUS_CANCELED, self.STATUS_DONE, self.STATUS_ERROR):
            self.stdout = [u'Pre-script stdout:'] + status[u'prescript'][u'stdout'] + [u'Pre-script return code: %s' % status[u'prescript'][u'returncode']]
            self.stdout += [u'', u'Post-script process:'] + status[u'postscript'][u'stdout'] + [u'Post-script return code: %s' % status[u'postscript'][u'returncode']]
            self.stderr = [u'Pre-script stderr:'] + status[u'prescript'][u'stderr'] + [u'Pre-script return code: %s' % status[u'prescript'][u'returncode']]
            self.stderr += [u'', u'Post-script stderr:'] + status[u'postscript'][u'stderr'] + [u'Post-script return code: %s' % status[u'postscript'][u'returncode']]

        #send status
        if self.status_callback:
            current_status = self.get_status()
            #inject module name and updateprocess status
            current_status[u'module'] = status[u'module']
            current_status[u'updateprocess'] = status[u'updateprocess']
            self.status_callback(current_status)

    def uninstall_module(self, module, update_process):
        """
        Uninstall specified module

        Params:
            module (string): module name to install
            update_process (bool): True if module uninstall occured during update process

        Returns:
            bool: True if module uninstalled
        """
        #check params
        if module is None or len(module)==0:
            raise MissingParameter(u'Parameter "module" is missing')

        #launch uninstallation
        uninstall = UninstallModule(module, update_process, self.__callback_uninstall_module, self.cleep_filesystem)
        uninstall.start()

        #blocking mode
        if self.blocking:
            #wait for end of installation
            while uninstall.get_status()==uninstall.STATUS_UNINSTALLING:
                time.sleep(0.25)

            #check uinstall status
            if uninstall.get_status()==uninstall.STATUS_UNINSTALLED:
                self.__need_restart = True
                #update raspiot.conf
                raspiot = RaspiotConf(self.cleep_filesystem)
                return raspiot.uninstall_module(module)

            return False

        else:
            #useless result
            return None


