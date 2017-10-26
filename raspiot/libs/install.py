#!/usr/bin/env python
# -*- coding: utf-8 -*

import logging
import time
import os
from raspiot.libs.console import EndlessConsole

class Install():
    """
    Install helper
    This class helps you to install different kind of files:
     - deb files using dpkg
     - tar.gz using tar
     - zip using unzip
    """

    STATUS_IDLE = 0
    STATUS_PROCESSING = 1
    STATUS_ERROR = 2
    STATUS_DONE = 3
    STATUS_CANCELED = 4

    def __init__(self, status_callback, blocking=False):
        """
        Constructor

        Args:
            status_callback (function): status callback. Params: status
            blocking (bool): enable or not blocking mode. If blocking mode is enabled, all functions are blocking
        """
        #logger
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)

        #members
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
            'status': self.status,
            'stdout': self.stdout,
            'stderr': self.stderr
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
        self.logger.debug('End of command')

        #update status if necessary
        if self.status!=self.STATUS_ERROR:
            self.status = self.STATUS_DONE

        #send for the last time current status
        self.status_callback(self.get_status())

        #unblock function call
        self.__running = False

    def __callback_quiet(self, stdout, stderr):
        """
        Quiet output. Does nothing
        """
        pass

    def refresh_packages(self):
        """
        Refresh packages list
        """
        if self.status==self.STATUS_PROCESSING:
            raise Exception(u'Installer is already processing')

        #update status
        self.__reset_status(self.STATUS_PROCESSING)

        #refresh packages
        command = u'/usr/bin/aptitude update'
        self.logger.debug('Command: %s' % command)
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

    def install_package(self, package_name):
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

        #install deb
        command = u'/usr/bin/aptitude install -y "%s"' % package_name
        self.logger.debug('Command: %s' % command)
        self.__console = EndlessConsole(command, self.__callback_package, self.__callback_end)
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

    def uninstall_package(self, package_name, purge=False):
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

        #install deb
        action = 'remove'
        if purge:
            action = 'purge'
        command = u'/usr/bin/aptitude %s -y "%s"' % (action, package_name)
        self.logger.debug('Command: %s' % command)
        self.__console = EndlessConsole(command, self.__callback_package, self.__callback_end)
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

        #install deb (and dependencies)
        command = u'/usr/bin/yes | /usr/bin/dpkg -i "%s" && /usr/bin/apt-get install -f && /usr/bin/yes | /usr/bin/dpkg -i "%s"' % (deb, deb)
        self.logger.debug('Command: %s' % command)
        self.__console = EndlessConsole(command, self.__callback_deb, self.__callback_end)
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
            raise Exception('Parameter "archive" is missing')
        if install_path is None or len(install_path.strip())==0:
            raise Exception('Parameter "install_path" is missing')
        if not os.path.exists(archive):
            raise Exception('Archive does not exist')

        #create output dir if it isn't exist
        if not os.path.exists(install_path):
            os.makedirs(install_path)

        #update status
        self.__reset_status(self.STATUS_PROCESSING)

        #get archive decompressor according to archive extension
        command = None
        dummy, ext = os.path.splitext(archive)
        if ext=='.gz':
            _, ext = os.path.splitext(dummy)
            if ext=='.tar':
                command = '/bin/tar xzvf "%s" -C "%s"' % (archive, install_path)

        elif ext=='.zip':
            command = '/usr/bin/unzip "%s" -d "%s"' % (archive, install_path)

        #execute command
        if command is None:
            raise Exception('File format not supported. Only zip and tar.gz supported.')
        else:
            self.logger.debug('Command: %s' % command)
            self.__console = EndlessConsole(command, self.__callback_archive, self.__callback_end)
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

