#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.internals.console import Console
import logging
import os
import traceback
import subprocess

class ReadWriteContext():
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
            u'isreadonlyfs': self.is_readonly_fs,
            u'src': self.src,
            u'dst': self.dst,
            u'action': self.action,
            u'boot': self.boot,
            u'root': self.root
        }

class ReadWrite():
    """
    Read/write library allows user to toggle read/write mode on cleep protected iso
    """

    STATUS_WRITE = 0
    STATUS_READ = 1
    STATUS_UNKNOWN = 2

    PARTITION_ROOT = u'/'
    PARTITION_BOOT = u'/boot'

    RASPIOT_DIR = u'/tmp/raspiot'

    def __init__(self):
        """
        Constructor
        """
        self.console = Console()
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)
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
        cmd = u'/usr/bin/lsof -p %s | grep -e "[[:digit:]]\+w"' % os.getpid()
        return [line.replace(u'\n','') for line in subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.readlines()]

    def is_path_on_root(self, path):
        """
        Return True if specified path is on root partition

        Args:
            path (string): path (absolute or not)

        Returns:
            bool: True if path on root partition
        """
        path = os.path.abspath(os.path.expanduser(path))
        return path and path.find(self.PARTITION_BOOT)==-1 and path.startswith(self.PARTITION_ROOT)

    def __refresh(self, partition):
        """
        Refresh data

        Args:
            partition (string): partition to work on
        """
        partition_mod = partition.replace(u'/', u'\/')
        command = r'/bin/mount | sed -n -e "s/^.* on %s .*(\(r[w|o]\).*/\1/p"' % partition_mod
        res = self.console.command(command)
        #self.logger.debug('Command "%s" result: %s' % (command, res))

        #check errors
        if res[u'error'] or res[u'killed'] or len(res[u'stdout'])==0:
            self.logger.error('Error when getting rw/ro flag: %s' % res)
            self.status[partition] = self.STATUS_UNKNOWN
            return

        #parse result
        line = res[u'stdout'][0].strip()
        if line==u'rw':
            self.status[partition] = self.STATUS_WRITE
            self.logger.trace(u'Partition "%s" is in WRITE mode' % partition)
        elif line==u'ro':
            self.status[partition] = self.STATUS_READ
            self.logger.trace(u'Partition "%s" is in READ mode' % partition)
        else:
            self.status[partition] = self.STATUS_UNKNOWN
            self.logger.error(u'Unable to get partition "%s" status: %s' % (partition, res[u'stdout']))

    def __is_cleep_iso(self):
        """
        Detect if raspiot is running on cleep iso

        Returns:
            bool: True if it's cleep iso
        """
        if os.path.exists(self.RASPIOT_DIR):
            return True

        return False

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
            'boot': self.status[self.PARTITION_BOOT],
            'root': self.status[self.PARTITION_ROOT],
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
            return False

        #execute command
        res = self.console.command(u'/bin/mount -o remount,rw %s' % partition, timeout=10.0)

        #check errors
        if res[u'error'] or res[u'killed']:
            self.logger.error(u'Error when turning on writing mode: %s' % res)

            #dump current stack trace to log
            lines = traceback.format_list(traceback.extract_stack())
            self.logger.error(u'%s' % u''.join(lines))

            #dump opened files to log
            self.logger.error(u'Opened files in RW by PID[%s]: %s' % (os.getpid(), u''.join(self.__get_opened_files_for_writing())))

            #and send crash report
            if self.crash_report:
                self.crash_report.manual_report(u'Error when turning on writing mode', {
                    u'result': res,
                    u'partition': partition,
                    u'traceback': lines,
                    u'files': self.__get_opened_files_for_writing(),
                })
            
        #refresh status
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

        #execute command
        res = self.console.command(u'/bin/mount -o remount,ro %s' % partition, timeout=10.0)

        #check errors
        if res[u'error'] or res[u'killed']:
            self.logger.error(u'Error when turning off writing mode: %s' % res)

            #dump current stack trace to log
            lines = traceback.format_list(traceback.extract_stack())
            self.logger.error(u'%s' % u''.join(lines))

            #dump opened files to log
            self.logger.error(u'Opened files in RW by PID[%s]: %s' % (os.getpid(), u''.join(self.__get_opened_files_for_writing())))

            #and send crash report
            if self.crash_report:
                self.crash_report.manual_report(u'Error when turning off writing mode', {
                    u'result': res,
                    u'partition': partition,
                    u'traceback': lines,
                    u'context': context.to_dict(),
                    u'files': self.__get_opened_files_for_writing(),
                })
            
        #refresh status
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

