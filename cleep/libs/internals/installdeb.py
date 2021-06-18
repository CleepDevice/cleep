#!/usr/bin/env python
# -*- coding: utf-8 -*

# File contains InstallDeb class that is used
# in install.py file to install cleep package
# and to provide function to install deb package

import logging
import time
import os
from cleep.libs.internals.console import EndlessConsole
from cleep.exception import MissingParameter, InvalidParameter


class InstallDeb:
    """
    Install .deb package using dpkg
    Due to quantity of messages, stderr is mixed within stdout to keep message order
    """

    STATUS_IDLE = 0
    STATUS_RUNNING = 1
    STATUS_DONE = 2
    STATUS_ERROR = 3
    STATUS_KILLED = 4
    STATUS_TIMEOUT = 5

    WATCHDOG_TIMEOUT = 3600  # seconds

    def __init__(self, cleep_filesystem, crash_report):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
            crash_report (CrashReport): CrashReport instance
        """
        # logger
        self.logger = logging.getLogger(self.__class__.__name__)
        # self.logger.setLevel(logging.DEBUG)

        # members
        self.cleep_filesystem = cleep_filesystem
        self.crash_report = crash_report
        self.running = True
        self.stdout = []
        self.status = self.STATUS_IDLE
        self.return_code = None
        self._console = None
        self.blocking = False
        self.status_callback = None

    def stop(self):
        """
        Stop installation
        """
        self.logger.trace("Stop installation")
        self.running = False
        self.status = self.STATUS_KILLED
        if not self.blocking and self._console:
            self._console.stop()

    def get_status(self):
        """
        Return current status
        """
        return {
            "status": self.status,
            "stdout": self.stdout,
            "returncode": self.return_code,
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
        self.logger.debug(
            "End of command with returncode=%s and killed=%s" % (return_code, killed)
        )

        # update return code
        self.return_code = return_code

        # update status
        if killed:
            self.status = self.STATUS_KILLED
        elif return_code != 0:
            self.status = self.STATUS_ERROR
        else:
            self.status = self.STATUS_DONE

        # send for the last time current status
        if self.status_callback:
            self.logger.debug("Final status: %s" % self.get_status())
            self.status_callback(self.get_status())

        # unblock function call
        self.running = False

    def __callback_deb(self, stdout, stderr):
        """
        Deb install callback

        Args:
            stdout (list): console stdout
            stderr (list): console stderr
        """
        self.logger.debug("Callback command stdout: %s" % stdout)
        self.logger.debug("Callback command stderr: %s" % stderr)
        # append current stdout/stderr
        if stdout is not None:
            # end of command ends with broken pipe on yes execution, this is normal. Drop this unimportant message
            # https://stackoverflow.com/questions/20573282/hudson-yes-standard-output-broken-pipe
            if stdout.find("yes") == -1 and stdout.lower().find("broken pipe") == -1:
                self.stdout.append(stdout)

        if stderr is not None:
            # mix stderr with stdout
            self.stdout.append(stderr)

        # send status to caller callback
        if self.status_callback:
            self.logger.debug("Process status: %s" % self.get_status())
            self.status_callback(self.get_status())

    def dry_run(self, deb, status_callback=None, timeout=60):
        """
        Try to install deb archive executing dpkg with --dry-run option
        This method is blocking
        Process result can be found calling get_status()

        Args:
            deb (string): deb package path
            status_callback (function): status callback. If not specified use get_status function
            timeout (number): kill command after specified timeout. 0 to disable it. Default 60s

        Returns:
            bool: True if install simulation succeed, False otherwise
        """
        # init
        self.status_callback = status_callback
        self.running = True

        # try install deb
        command = '/usr/bin/yes | /usr/bin/dpkg --dry-run -i "%s"' % (deb)
        self.logger.debug("Command: %s" % command)
        self._console = EndlessConsole(
            command, self.__callback_deb, self.__callback_end
        )
        self._console.start()

        # loop
        error = False
        watchdog_end_time = int(time.time()) + (timeout or self.WATCHDOG_TIMEOUT)
        while self.running:
            # watchdog
            if int(time.time()) > watchdog_end_time:
                self.logger.error(
                    "Timeout (%s seconds) during debian package dry-run"
                    % self.WATCHDOG_TIMEOUT
                )
                self.crash_report.manual_report(
                    'Debian "%s" dry-run install failed because of timeout (%s seconds)'
                    % (
                        deb,
                        (timeout or self.WATCHDOG_TIMEOUT),
                    ),
                    self.get_status(),
                )
                error = True
                self._console.kill()
                self.running = False
                self.status = self.STATUS_TIMEOUT

            time.sleep(0.25)

        # handle result
        return not error and self.status == self.STATUS_DONE

    def install(self, deb, blocking=False, status_callback=None, timeout=60):
        """
        Install specified .deb file
        Please note in non blocking mode you must allow by yourself filesystem writing

        Args:
            deb (string): deb package path
            blocking (bool): if True this function is blocking (default is False)
            status_callback (function): status callback. Must be specified if blocking is False
            timeout (number): kill command after specified timeout. 0 to disable it. Default 60s

        Returns:
            bool: True if install succeed, False otherwise. None is returned if blocking mode is disabled
        """
        # check parameters
        if deb is None or len(deb) == 0:
            raise MissingParameter('Parameter "deb" is missing')
        if blocking is False and status_callback is None:
            raise MissingParameter(
                'Parameter "status_callback" is mandatary if blocking mode enabled'
            )
        if not os.path.exists(deb):
            raise InvalidParameter('Deb archive "%s" does not exist' % deb)

        # update status
        self.status_callback = status_callback
        self.running = True
        self.status = self.STATUS_RUNNING
        self.blocking = blocking

        if blocking:
            # enable write
            self.cleep_filesystem.enable_write()

        # install deb
        command = '/usr/bin/yes | /usr/bin/dpkg -i "%s"' % (deb)
        self.logger.debug("Command: %s" % command)
        self._console = EndlessConsole(
            command, self.__callback_deb, self.__callback_end
        )
        self._console.start()

        # blocking mode
        self.logger.debug("Blocking mode: %s" % blocking)
        if blocking:
            # loop
            error = False
            watchdog_end_time = int(time.time()) + (timeout or self.WATCHDOG_TIMEOUT)
            self.logger.trace("Watchdog_end_time=%s" % watchdog_end_time)
            while self.running:
                # watchdog
                if int(time.time()) > watchdog_end_time:
                    self.logger.error(
                        "Timeout (%s seconds) during debian package install"
                        % self.WATCHDOG_TIMEOUT
                    )
                    self.crash_report.manual_report(
                        'Debian "%s" install failed because of watchdog timeout (%s seconds)'
                        % (deb, (timeout or self.WATCHDOG_TIMEOUT)),
                        self.get_status(),
                    )
                    error = True
                    self._console.kill()
                    self.running = False
                    self.status = self.STATUS_TIMEOUT

                time.sleep(0.25)

            # disable write at end of command execution
            self.cleep_filesystem.disable_write()

            # handle result
            return not error and self.status == self.STATUS_DONE

        # useless result
        return None
