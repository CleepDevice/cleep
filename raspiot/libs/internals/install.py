#!/usr/bin/env python
# -*- coding: utf-8 -*

import logging
import time
import os
import inspect
from zipfile import ZipFile
import threading
import tempfile
from raspiot.libs.internals.console import EndlessConsole
from raspiot.raspiot import RaspIotModule
from raspiot.libs.internals.download import Download
from raspiot.libs.internals.installmodule import InstallModule, UninstallModule, UpdateModule
from raspiot.libs.internals.installdeb import InstallDeb

__all__ = ['Install']


class Install():
    """
    Install helper
    This class helps you to install different kind of things:
     - deb files using dpkg
     - tar.gz using tar
     - zip using unzip
     - raspiot module install/uninstall/update (ok class name is not correct ;) )
     - system packages install/uninst using apt-get command
    """

    STATUS_IDLE = 0
    STATUS_PROCESSING = 1
    STATUS_ERROR = 2
    STATUS_DONE = 3
    STATUS_CANCELED = 4

    def __init__(self, cleep_filesystem, crash_report, status_callback, blocking=False):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
            crash_report (CrashReport): Crash report instance
            status_callback (function): status callback. Params: status
            blocking (bool): enable or not blocking mode. If blocking mode is enabled, all functions are blocking
        """
        #logger
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)

        #members
        self.cleep_filesystem = cleep_filesystem
        self.crash_report = crash_report
        self.blocking = blocking
        self.__console = None
        self.__cancel = False
        self.status = self.STATUS_IDLE
        self.status_callback = status_callback
        self.stdout = []
        self.stderr = []
        self.__running = True
        self.__can_cancel = True

    def cancel(self):
        """
        Cancel current install
        """
        if self.__can_cancel:
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
        if self.status_callback:
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
        if self.status_callback:
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

    def __callback_deb(self, status):
        """
        Deb install callback

        Args:
            status (dict): status dict like returned by InstallDeb get_status function
        """
        #update output
        self.stdout = status[u'stdout']
        self.stderr = status[u'stderr']

        #update status
        if status[u'status']==InstallDeb.STATUS_RUNNING:
            self.status = self.STATUS_PROCESSING
        elif status[u'status'] in (InstallDeb.STATUS_ERROR, InstallDeb.STATUS_KILLED):
            self.status = self.STATUS_ERROR
        elif status[u'status']==InstallDeb.STATUS_DONE:
            self.status = self.STATUS_DONE

        #send status to caller callback
        if self.status_callback:
            self.status_callback(self.get_status())

    def install_deb(self, deb):
        """
        Install .deb file using dpkg
        Cannot be canceled once launched

        Return:
            bool: True if install succeed or None if non blocking
        """
        if self.status==self.STATUS_PROCESSING:
            raise Exception(u'Installer is already processing')

        #disable cancel
        self.__can_cancel = False

        #update status
        self.__reset_status(self.STATUS_PROCESSING)

        #install deb (and its dependencies)
        installer = InstallDeb(self.__callback_deb, self.cleep_filesystem, blocking=False)
        installer.install(deb)

        #blocking mode
        if self.blocking:
            #loop
            while self.status==self.STATUS_PROCESSING:
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
        if self.status_callback:
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
                    process (list): process status
                }
        """
        self.logger.debug('Install status: %s' % status)
        #save status
        if status[u'status']==InstallModule.STATUS_IDLE:
            self.status = self.STATUS_IDLE
        elif status[u'status']==InstallModule.STATUS_INSTALLING:
            self.status = self.STATUS_PROCESSING
        elif status[u'status']==InstallModule.STATUS_INSTALLED:
            self.status = self.STATUS_DONE
        else:
            self.status = self.STATUS_ERROR

        #save stdout/stderr at end of process
        if self.status in (self.STATUS_CANCELED, self.STATUS_DONE, self.STATUS_ERROR):
            #prescript
            if status[u'prescript'][u'returncode'] is not None:
                self.stdout += [u'Preinstall script stdout:'] + status[u'prescript'][u'stdout'] + [u'Preinstall script return code: %s' % status[u'prescript'][u'returncode']]
                self.stderr += [u'Preinstall script stderr:'] + status[u'prescript'][u'stderr']
            else:
                self.stdout += [u'No preinstall script']
                self.stderr += [u'No preinstall script']

            #postscript
            if status[u'postscript'][u'returncode'] is not None:
                self.stdout += [u'', u'Postinstall script stdout:'] + status[u'postscript'][u'stdout'] + [u'Postinstall script return code: %s' % status[u'postscript'][u'returncode']]
                self.stderr += [u'', u'Postinstall script stderr:'] + status[u'postscript'][u'stderr']
            else:
                self.stdout += [u'', u'No postinstall script']
                self.stderr += [u'', u'No postinstall script']

        #send status
        if self.status_callback:
            current_status = self.get_status()
            #inject module name and updateprocess
            current_status[u'module'] = status[u'module']
            current_status[u'updateprocess'] = status[u'updateprocess']
            current_status[u'process'] = status[u'process']
            self.status_callback(current_status)

    def install_module(self, module, module_infos):
        """
        Install specified module

        Params:
            module (string): module name to install
            modules_infos (dict): module infos reported in modules.json

        Returns:
            bool: True if module installed or None if non blocking
        """
        #check params
        if module is None or len(module)==0:
            raise MissingParameter(u'Parameter "module" is missing')
        if module_infos is None or len(module_infos)==0:
            raise MissingParameter(u'Parameter "module_infos" is missing')

        #disable cancel
        self.__can_cancel = False

        #launch installation
        install = InstallModule(module, module_infos, False, self.__callback_install_module, self.cleep_filesystem, self.crash_report)
        install.start()

        #blocking mode
        self.logger.debug(u'Install module blocking? %s' % self.blocking)
        if self.blocking:
            #wait for end of installation
            while install.get_status()==install.STATUS_INSTALLING:
                time.sleep(0.25)

            #check install status
            if install.get_status()==install.STATUS_INSTALLED:
                return True
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
            #prescript
            if status[u'prescript'][u'returncode']:
                self.stdout += [u'Preuninstall script stdout:'] + status[u'prescript'][u'stdout'] + [u'Preuninstall script return code: %s' % status[u'prescript'][u'returncode']]
                self.stderr += [u'Preuninstall script stderr:'] + status[u'prescript'][u'stderr']
            else:
                self.stdout += [u'No preuninstall script']
                self.stderr += [u'No preuninstall script']
                
            #postscript
            if status[u'postscript'][u'returncode']:
                self.stdout += [u'', u'Postuninstall script process:'] + status[u'postscript'][u'stdout'] + [u'Postuninstall script return code: %s' % status[u'postscript'][u'returncode']]
                self.stderr += [u'', u'Postuninstall script stderr:'] + status[u'postscript'][u'stderr']
            else:
                self.stdout += [u'No postuninstall script']
                self.stderr += [u'No postuninstall script']

        #send status
        if self.status_callback:
            current_status = self.get_status()
            #inject module name and updateprocess status
            current_status[u'module'] = status[u'module']
            current_status[u'updateprocess'] = status[u'updateprocess']
            current_status[u'process'] = status[u'process']
            self.status_callback(current_status)

    def uninstall_module(self, module, module_infos, force=False):
        """
        Uninstall specified module

        Params:
            module (string): module name to uninstall
            modules_infos (dict): module infos reported in modules.json
            force (bool): uninstall module and continue if error occured

        Returns:
            bool: True if module uninstalled or None if non blocking
        """
        #check params
        if module is None or len(module)==0:
            raise MissingParameter(u'Parameter "module" is missing')

        #launch uninstallation
        uninstall = UninstallModule(module, module_infos, False, force, self.__callback_uninstall_module, self.cleep_filesystem, self.crash_report)
        uninstall.start()

        #blocking mode
        if self.blocking:
            #wait for end of installation
            while uninstall.get_status()==uninstall.STATUS_UNINSTALLING:
                time.sleep(0.25)

            #check uinstall status
            if uninstall.get_status()==uninstall.STATUS_UNINSTALLED:
                return True
            return False

        else:
            #useless result
            return None

    def __callback_update_module(self, status):
        """
        Module update callback

        Args:
            status (dict): module status::
                {
                    module (string): module name
                    status (int): module process status
                    uninstall (dict): {status, prescript, postscript}
                    install (dict): {status, prescript, postscript}
                }
        """
        #save status
        if status[u'status']==UpdateModule.STATUS_IDLE:
            self.status = self.STATUS_IDLE
        elif status[u'status']==UpdateModule.STATUS_UPDATING:
            self.status = self.STATUS_PROCESSING
        elif status[u'status']==UpdateModule.STATUS_UPDATED:
            self.status = self.STATUS_DONE
        else:
            self.status = self.STATUS_ERROR

        #save install/uninstall status at end of process
        if self.status in (self.STATUS_CANCELED, self.STATUS_DONE, self.STATUS_ERROR):
            #uninstall prescript
            if status[u'uninstall'][u'prescript'][u'returncode']:
                self.stdout += [u'Preuninstall script stdout:'] + status[u'uninstall'][u'prescript'][u'stdout'] + [u'Preuninstall script return code: %s' % status[u'uninstall'][u'prescript'][u'returncode']]
                self.stderr += [u'Preuninstall script stderr:'] + status[u'uninstall'][u'prescript'][u'stderr']
            else:
                self.stdout += [u'No preuninstall script']

            #uninstall postscript
            if status[u'uninstall'][u'postscript'][u'returncode']:
                self.stdout += [u'', u'Postuninstall script stdout:'] + status[u'uninstall'][u'postscript'][u'stdout'] + [u'Postuninstall script return code: %s' % status[u'uninstall'][u'postscript'][u'returncode']]
                self.stderr += [u'', u'Postuninstall script stderr:'] + status[u'uninstall'][u'postscript'][u'stderr']
            else:
                self.stdout = [u'', u'No postuninstall script']

            #install prescript
            if status[u'install'][u'prescript'][u'returncode']:
                self.stdout += [u'', u'Preinstall script stdout:'] + status[u'install'][u'prescript'][u'stdout'] + [u'Preinstall script return code: %s' % status[u'install'][u'prescript'][u'returncode']]
                self.stderr += [u'', u'Preinstall script stderr:'] + status[u'install'][u'prescript'][u'stderr']
            else:
                self.stdout = [u'', u'No preinstall script']

            #install postscript
            if status[u'install'][u'postscript'][u'returncode']:
                self.stdout += [u'', u'Postinstall script stdout:'] + status[u'install'][u'postscript'][u'stdout'] + [u'Postinstall script return code: %s' % status[u'install'][u'postscript'][u'returncode']]
                self.stderr += [u'', u'Postinstall script stderr:'] + status[u'install'][u'postscript'][u'stderr']
            else:
                self.stdout = [u'', u'No postinstall script']

        #send status
        if self.status_callback:
            current_status = self.get_status()
            #inject module name
            current_status[u'module'] = status[u'module']
            self.logger.debug('current_status=%s' % current_status)
            self.status_callback(current_status)

    def update_module(self, module, module_infos, force_uninstall=False):
        """
        Update specified module
        An update executes consecutively uninstall and install action

        Args:
            module (string): module name
            modules_infos (dict): module infos reported in modules.json
            force_uninstall (bool): force module uninstall even if error occured

        Returns:
            bool: True if module updated or None if non blocking
        """
        #check params
        if module is None or len(module)==0:
            raise MissingParameter(u'Parameter "module" is missing')
        if module_infos is None or len(module_infos)==0:
            raise MissingParameter(u'Parameter "module_infos" is missing')

        #disable cancel
        self.__can_cancel = False

        #launch update
        update = UpdateModule(module, module_infos, force_uninstall, self.__callback_update_module, self.cleep_filesystem, self.crash_report)
        update.start()

        #blocking mode
        if self.blocking:
            #wait for end of update
            while update.get_status()==update.STATUS_UPDATING:
                time.sleep(0.25)

            #check update status
            if update.get_status()==update.STATUS_UPDATED:
                return True
            return False

        else:
            #useless return
            return None


