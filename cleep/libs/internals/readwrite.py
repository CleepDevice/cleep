#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.console import Console
import logging
import os
import traceback
from subprocess import Popen, PIPE


class ReadWriteContext:
    """
    Object to hold some data about current context
    """

    def __init__(self):
        self.is_readonly_fs = None
        self.src = None
        self.dst = None
        self.action = None
        self.boot = None
        self.root = None

    def to_dict(self):
        return {
            "isreadonlyfs": self.is_readonly_fs,
            "src": self.src,
            "dst": self.dst,
            "action": self.action,
            "boot": self.boot,
            "root": self.root,
        }


class ReadWrite:
    """
    Read/write library allows user to toggle read/write mode on cleep protected iso
    """

    STATUS_WRITE = 0
    STATUS_READ = 1
    STATUS_UNKNOWN = 2

    PARTITION_ROOT = "/"
    PARTITION_BOOT = "/boot"

    CLEEP_DIR = "/tmp/cleep"

    def __init__(self):
        """
        Constructor
        """
        self.console = Console()
        self.logger = logging.getLogger(self.__class__.__name__)
        # self.logger.setLevel(logging.DEBUG)
        self.status = {}
        self.crash_report = None

    def set_crash_report(self, crash_report):
        """
        Set crash report

        Args:
            crash_report (CrashReport): CrashReport instance
        """
        self.crash_report = crash_report

    def __get_opened_files_for_writing(self):
        """
        Return opened files for writing for current program
        """
        cmd = '/usr/bin/lsof -p %s | grep -e "[[:digit:]]\+w"' % os.getpid()
        return [
            line.decode("utf-8").replace("\n", "")
            for line in Popen(
                cmd, shell=True, stdout=PIPE
            ).stdout.readlines()
        ]

    def is_path_on_root(self, path):
        """
        Return True if specified path is on root partition

        Args:
            path (string): path (absolute or not)

        Returns:
            bool: True if path on root partition
        """
        path = os.path.abspath(os.path.expanduser(path))
        return (
            path
            and path.find(self.PARTITION_BOOT) == -1
            and path.startswith(self.PARTITION_ROOT)
        )

    def __refresh(self, partition):
        """
        Refresh data

        Args:
            partition (string): partition to work on
        """
        partition_mod = partition.replace("/", "\/")
        command = (
            r'/bin/mount | sed -n -e "s/^.* on %s .*(\(r[w|o]\).*/\1/p"' % partition_mod
        )
        res = self.console.command(command)
        # self.logger.debug('Command "%s" result: %s' % (command, res))

        # check errors
        if res["error"] or res["killed"] or len(res["stdout"]) == 0:
            self.logger.error("Error when getting rw/ro flag: %s" % res)
            self.status[partition] = self.STATUS_UNKNOWN
            return

        # parse result
        line = res["stdout"][0].strip()
        if line == "rw":
            self.status[partition] = self.STATUS_WRITE
            self.logger.trace('Partition "%s" is in WRITE mode' % partition)
        elif line == "ro":
            self.status[partition] = self.STATUS_READ
            self.logger.trace('Partition "%s" is in READ mode' % partition)
        else:
            self.status[partition] = self.STATUS_UNKNOWN
            self.logger.error(
                'Unable to get partition "%s" status: %s' % (partition, res["stdout"])
            )

    def __is_cleep_iso(self):
        """
        Detect if cleep is running on cleep iso

        Returns:
            bool: True if it's cleep iso
        """
        return os.path.exists(self.CLEEP_DIR)

    def __is_ci_env(self): # pragma: no cover
        """
        Return True if Cleep is running in CI env

        Returns:
            bool: True if running in CI env
        """
        ci_env = os.environ.get('CI_ENV', None)
        return ci_env != None

    def get_status(self):
        """
        Return current filesystem status requesting mount command

        Returns:
            dict: partition status (please check STATUS_UNKNOWN that appears when problem occurs)::

                {
                    boot (int): STATUS_READ|STATUS_WRITE
                    root (int): STATUS_READ|STATUS_WRITE
                }

        """
        self.__refresh(self.PARTITION_BOOT)
        self.__refresh(self.PARTITION_ROOT)

        return {
            "boot": self.status[self.PARTITION_BOOT],
            "root": self.status[self.PARTITION_ROOT],
        }

    def __enable_write(self, partition):
        """
        Enable filesystem writing

        Args:
            partition (string): partition to work on

        Returns:
            bool: True if write enabled, False otherwise
        """
        if not self.__is_cleep_iso():
            self.logger.trace("Not running on cleep iso")
            return False
        if self.__is_ci_env(): # pragma: no cover
            self.logger.trace("Running in CI env")
            return False

        # execute command
        res = self.console.command(
            "/bin/mount -o remount,rw %s" % partition, timeout=10.0
        )
        self.logger.trace("Res: %s" % res)

        # check errors
        if res["error"] or res["killed"]:
            self.logger.error("Error when turning on writing mode: %s" % res)

            # dump current stack trace to log
            lines = traceback.format_list(traceback.extract_stack())
            self.logger.error("%s" % "".join(lines))

            # dump opened files to log
            self.logger.error(
                "Opened files in RW by PID[%s]: %s"
                % (os.getpid(), "".join(self.__get_opened_files_for_writing()))
            )

            # and send crash report
            if self.crash_report:
                self.crash_report.manual_report(
                    "Error when turning on writing mode",
                    {
                        "result": res,
                        "partition": partition,
                        "traceback": lines,
                        "files": self.__get_opened_files_for_writing(),
                    },
                )

        # refresh status
        self.__refresh(partition)

        return self.status[partition] is self.STATUS_WRITE

    def __disable_write(self, partition, context):
        """
        Disable filesystem writings

        Args:
            partition (string): partition to work on
            context (ReadWriteContext): write context

        Returns:
            bool: True if read enabled, False otherwise
        """
        if not self.__is_cleep_iso():
            return False
        if self.__is_ci_env(): # pragma: no cover
            print('=====> CIenv')
            return False

        # execute command
        res = self.console.command(
            "/bin/mount -o remount,ro %s" % partition, timeout=10.0
        )

        # check errors
        if res["error"] or res["killed"]:
            self.logger.error("Error when turning off writing mode: %s" % res)

            # dump current stack trace to log
            lines = traceback.format_list(traceback.extract_stack())
            self.logger.error("%s" % "".join(lines))

            # dump opened files to log
            opened_files = self.__get_opened_files_for_writing()
            self.logger.error(
                "Opened files in RW by PID[%s]: %s"
                % (os.getpid(), "".join(opened_files))
            )

            # do not crash report if filesystem is busy
            if (
                self.crash_report
                and (res["stderr"][0] if len(res["stderr"]) == 1 else "").find("busy")
                == -1
            ):
                self.crash_report.manual_report(
                    "Error when turning off writing mode",
                    {
                        "result": res,
                        "partition": partition,
                        "traceback": lines,
                        "context": context.to_dict(),
                        "files": opened_files,
                    },
                )

        # refresh status
        self.__refresh(partition)

        return self.status[partition] is self.STATUS_READ

    def enable_write_on_boot(self):
        """
        Enable filesystem writings on boot partition

        Returns:
            bool: True if write enabled, False otherwise
        """
        return self.__enable_write(self.PARTITION_BOOT)

    def disable_write_on_boot(self, context):
        """
        Disable filesystem writings on boot partition

        Args:
            context (ReadWriteContext): write context

        Returns:
            bool: True if write disabled, False otherwise
        """
        return self.__disable_write(self.PARTITION_BOOT, context)

    def enable_write_on_root(self):
        """
        Enable filesystem writings on root partition

        Returns:
            bool: True if write enabled, False otherwise
        """
        return self.__enable_write(self.PARTITION_ROOT)

    def disable_write_on_root(self, context):
        """
        Disable filesystem writings on root partition

        Args:
            context (ReadWriteContext): write context

        Returns:
            bool: True if write disabled, False otherwise
        """
        return self.__disable_write(self.PARTITION_ROOT, context)
