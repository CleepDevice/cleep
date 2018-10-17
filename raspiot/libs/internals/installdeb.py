#!/usr/bin/env python
# -*- coding: utf-8 -*

# File contains InstallDeb class that is used
# in install.py file to install raspiot package
# and to provide function to install deb package

import logging
import time
from raspiot.libs.internals.console import EndlessConsole


class InstallDeb():
    """
    Install .deb package using dpkg
    """
    STATUS_IDLE = 0
    STATUS_RUNNING = 1
    STATUS_DONE = 2
    STATUS_ERROR = 3
    STATUS_KILLED = 4

    WATCHDOG_TIMEOUT = 60 #seconds

    def __init__(self, status_callback, cleep_filesystem, blocking=True):
        """
        Constructor
        
        Args:
            status_callback (function): status callback
            blocking (bool): blocking mode. True by default
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
        """
        #logger
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)

        #members
        self.cleep_filesystem = cleep_filesystem
        self.status_callback = status_callback
        self.blocking = blocking
        self.running = True
        self.stderr = []
        self.stdout = []
        self.status = self.STATUS_IDLE
        self.return_code = None

    def stop(self):
        """
        Stop installation
        """
        self.running = False

    def get_status(self):
        """
        Return current status
        """
        return {
            u'status': self.status,
            u'stdout': self.stdout,
            u'stderr': self.stderr,
            u'returncode': self.return_code
        }

    def is_terminated(self):
        """
        Return True if installation terminated

        Returns:
            bool: True if terminated
        """
        return not self.running

    def __callback_end(self, return_code, killed):
        """
        End of process callback
        """
        self.logger.debug(u'End of command with returncode=%s and killed=%s' % (return_code, killed))

        #update return code
        self.return_code = return_code

        #update status
        if killed:
            self.status = self.STATUS_KILLED
        elif return_code!=0:
            self.status = self.STATUS_ERROR
        else:
            self.status = self.STATUS_DONE

        #send for the last time current status
        if self.status_callback:
            self.logger.debug('Final status: %s' % self.get_status())
            self.status_callback(self.get_status())

        #unblock function call
        self.running = False

    def __callback_deb(self, stdout, stderr):
        """
        Deb install callback

        Args:
            stdout (list): console stdout
            stderr (list): console stderr
        """
        self.logger.debug(u'Callback command stdout: %s' % stdout)
        self.logger.debug(u'Callback command stderr: %s' % stderr)
        #append current stdout/stderr
        if stdout is not None:
            #end of command ends with broken pipe on yes execution, this is normal. Drop this unimportant message
            #https://stackoverflow.com/questions/20573282/hudson-yes-standard-output-broken-pipe
            if stdout.find(u'yes')==-1 and stdout.lower().find(u'broken pipe')==-1:
                self.stdout.append(stdout)

        if stderr is not None:
            #mix stderr with stdout
            self.stdout.append(stderr)

        #send status to caller callback
        if self.status_callback:
            self.logger.debug('Process status: %s' % self.get_status())
            self.status_callback(self.get_status())

    def dry_run(self, deb):
        """
        Try to install deb archive executing dpkg with --dry-run option
        This method is blocking even if blocking params is False
        Process result can be found calling get_status()

        Args:
            deb (string): deb package path

        Returns:
            bool: True if install simulation succeed, False otherwise
        """
        #try install deb
        command = u'/usr/bin/yes | /usr/bin/dpkg --dry-run -i "%s"' % (deb)
        self.logger.debug(u'Command: %s' % command)
        console = EndlessConsole(command, self.__callback_deb, self.__callback_end)
        console.start()

        #loop
        error = False
        watchdog_end_time = int(time.time()) + self.WATCHDOG_TIMEOUT
        while self.running:
            #watchdog
            if int(time.time())>watchdog_end_time:
                self.logger.error(u'Timeout (%s seconds) during debian dry-run install' % self.WATCHDOG_TIMEOUT)
                self.crash_report.manual_report(u'Debian "%s" dry-run install failed because of timeout (%s seconds)' % (deb, self.WATCHDOG_TIMEOUT), self.get_status())
                error = True
                continue

            time.sleep(0.25)
            
        #handle result
        if not error and self.status==self.STATUS_DONE:
            return True
        return False

    def install(self, deb):
        """
        Install specified .deb file
        Please note in non blocking mode you must allow by yourself filesystem writing

        Args:
            deb (string): deb package path

        Returns:
            bool: True if install succeed, False otherwise. None is returned if blocking mode is disabled
        """
        #update status
        self.status = self.STATUS_RUNNING

        if self.blocking:
            #enable write
            self.cleep_filesystem.enable_write()

        #install deb
        command = u'/usr/bin/yes | /usr/bin/dpkg -i "%s"' % (deb)
        self.logger.debug(u'Command: %s' % command)
        console = EndlessConsole(command, self.__callback_deb, self.__callback_end)
        console.start()

        #blocking mode
        self.logger.debug('Blocking mode: %s' % self.blocking)
        if self.blocking:
            #loop
            error = False
            end_time = int(time.time()) + self.WATCHDOG_TIMEOUT
            while self.running:
                #watchdog
                if int(time.time())>watchdog_end_time:
                    self.logger.error(u'Timeout (%s seconds) during debian dry-run install' % self.WATCHDOG_TIMEOUT)
                    self.crash_report.manual_report(u'Debian "%s" install failed because of watchdog timeout (%s seconds)' % (deb, self.WATCHDOG_TIMEOUT), self.get_status())
                    error = True
                    continue

                time.sleep(0.25)
            
            #disable write at end of command execution
            self.cleep_filesystem.disable_write()

            #handle result
            if not error and self.status==self.STATUS_DONE:
                return True
            return False

        else:
            #useless result
            return None


