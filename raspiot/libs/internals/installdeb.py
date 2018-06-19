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
        #self.logger.setLevel(logging.DEBUG)

        #members
        self.cleep_filesystem = cleep_filesystem
        self.status_callback = status_callback
        self.blocking = blocking
        self.running = True
        self.stderr = []
        self.stdout = []
        self.status = self.STATUS_IDLE

    def get_status(self):
        """
        Return current status
        """
        return {
            u'status': self.status,
            u'stdout': self.stdout,
            u'stderr': self.stderr
        }

    def __callback_end(self, return_code, killed):
        """
        End of process callback
        """
        self.logger.debug(u'End of command with returncode=%s and killed=%s' % (return_code, killed))

        #update status if necessary
        if killed:
            self.status = self.STATUS_KILLED
        elif return_code!=0:
            self.status = self.STATUS_ERROR
        elif self.status!=self.STATUS_ERROR:
            self.status = self.STATUS_DONE

        #unblock function call
        self.running = False

        #disable write at end of command execution
        self.cleep_filesystem.disable_write()

        #send for the last time current status
        if self.status_callback:
            self.logger.debug('Final status: %s' % self.get_status())
            self.status_callback(self.get_status())

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
        if self.status_callback:
            self.logger.debug('Process status: %s' % self.get_status())
            self.status_callback(self.get_status())

    def install(self, deb):
        """
        Install specified .deb file

        Args:
            deb (string): deb package path
        """
        #update status
        self.status = self.STATUS_RUNNING

        #enable write
        self.cleep_filesystem.enable_write()

        #install deb (and dependencies)
        command = u'/usr/bin/yes | /usr/bin/dpkg -i "%s" && /usr/bin/apt-get install -f && /usr/bin/yes | /usr/bin/dpkg -i "%s"' % (deb, deb)
        self.logger.debug(u'Command: %s' % command)
        console = EndlessConsole(command, self.__callback_deb, self.__callback_end)
        console.start()

        #blocking mode
        if self.blocking:
            #loop
            while self.running:
                time.sleep(0.25)
            
            if self.status==self.STATUS_DONE:
                return True
            return False

        else:
            #useless result
            return None


