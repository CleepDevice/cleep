#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.internals.console import Console
from raspiot.libs.internals.readwrite import ReadWrite, ReadWriteContext
import logging
import os
from threading import Timer, Lock
import gevent.lock as glock
import io
import shutil
import json
import locale
from distutils.dir_util import copy_tree


class CleepFilesystem():
    """
    Filesystem helper with read/write filesystem support (uses readwrite lib)
    A debounce function waits to switch to readonly mode to reduce number of switch
    """

    DEBOUNCE_DURATION = 10.0

    def __init__(self):
        """
        Constructor
        """
        #logger
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)

        #members
        self.crash_report = None
        self.rw = ReadWrite()
        self.__counter = 0;
        self.__rw_lock = Lock()
        self.__debounce_timer = None
        self.__errors_busy = 0
        self.__errors = 0

        #check if os is in readonly mode
        self.is_readonly = self.__is_readonly_filesystem()
        if self.is_readonly:
            self.logger.info(u'Raspiot is running on read-only filesystem')

    def reset_errors(self):
        """
        Reset internal errors counters
        """
        self.__errors_busy = 0
        self.__errors = 0

    def set_crash_report(self, crash_report):
        """
        Set crash report

        Args:
            crash_report (CrashReport): CrashReport instance
        """
        self.crash_report = crash_report
        self.rw.set_crash_report(crash_report)

    def __is_readonly_filesystem(self):
        """
        Check if readonly is configured in OS

        Return:
            bool: True if RO configured on OS
        """
        encoding = locale.getpreferredencoding()
        fd = io.open(u'/etc/fstab', u'r', encoding=encoding)
        lines = fd.readlines()
        fd.close()
        for line in lines:
            if line.find(u',ro')>=0 or line.find(u'ro,')>=0:
                #read only configured
                return True

        return False

    def __really_disable_write(self, context):
        """
        Function used in debounce timer
        """
        #acquire lock
        self.logger.debug('Acquire lock in really_disable_write')
        self.__rw_lock.acquire()

        if self.__debounce_timer is None:
            #debounce timer canceled
            return
        
        #reset flag
        self.__debounce_timer = None

        #disable writings
        self.logger.debug('Disable writings')
        self.rw.disable_write_on_root(context)
        self.rw.disable_write_on_boot(context)

        #release lock
        self.logger.debug('Release lock in really_disable_write')
        self.__rw_lock.release()

    def __enable_write(self, boot=True, root=False):
        """
        Enable write mode

        Args:
            root: enable write on root partition (efault true)
            boot (bool): enable write on boot partition (default false)
        """
        if not boot and not root:
            self.logger.warning(u'No partition specified, enable write action ignored.')
            return

        #acquire lock
        self.__rw_lock.acquire()
        self.logger.debug('Acquire lock in enable_write [counter=%s]' % (self.__counter))

        if self.__debounce_timer is not None:
            #debounce timer running and we need to enable write mode, cancel timer
            self.__debounce_timer.cancel()
            self.__debounce_timer = None

        if self.__counter==0:
            #first to request writing, enable it
            if root:
                self.logger.debug('Enable writings on root partition')
                self.rw.enable_write_on_root()
            if boot:
                self.logger.debug('Enable writings on boot partition')
                self.rw.enable_write_on_boot()

        else:
            #write mode already enabled
            pass

        #increase usage counter
        self.__counter += 1

        #release lock
        self.logger.debug('Release lock in enable_write [counter=%s]' % self.__counter)
        self.__rw_lock.release()

    def __disable_write(self, context):
        """
        Disable write mode
        """
        #acquire lock
        self.__rw_lock.acquire()
        self.logger.debug('Acquire lock in disable_write [counter=%s]' % self.__counter)

        #cancel action if necessary
        if self.__counter==0:
            #not in writing mode
            self.logger.warning(u'Not in writing mode, a bug surely exist!')

            self.logger.debug('Release lock in disable_write [counter=%s]' % self.__counter)
            self.__rw_lock.release()

        #decrease usage counter
        self.__counter -= 1

        if self.__counter==0:
            #disable write after debounce time
            self.logger.debug('Launch debounce timer')
            self.__debounce_timer = Timer(self.DEBOUNCE_DURATION, self.__really_disable_write, [context])
            self.__debounce_timer.start()

        else:
            #running action still needs write mode
            pass

        #release lock
        self.logger.debug('Release lock in disable_write [counter=%s]' % self.__counter)
        self.__rw_lock.release()

    def __is_on_tmp(self, path):
        """
        Return True if specified file path is on /tmp which is writable

        Args:
            path (string): path

        Return:
            bool: True if on /tmp
        """
        path = os.path.normpath(path)
        path = os.path.realpath(path)
        parts = path.split(os.sep)

        return u'tmp'==parts[1]

    def enable_write(self, root=True, boot=False):
        """
        Enable write as long as you disable it
        This function must be used in specific cases when you need to disable readonly mode for a while (like system update)
        Please make sure to call disable_write after you finished your job!

        Args:
            root (bool): enable write on root partition
            boot (bool): enable write on boot partition
        """
        self.logger.warning(u'Filesystem readonly protection is disabled completely by application!')
        self.__enable_write(root=root, boot=boot)

    def disable_write(self):
        """
        Disable write
        This function must be used in specific cases when you need to disable readonly mode for a while (like system update)
        Use this function only if you called enable_write function before!
        """
        self.logger.info(u'Filesystem readonly protection is enabled again')
        context = ReadWriteContext()
        context.action = u'disable_write'
        self.__disable_write(context)

    def open(self, path, mode, encoding=None):
        """
        Open file

        Args:
            path (string): file path
            mode (string): mode as builtin open() function
            encoding (string): file encoding (default is system one)

        Return:
            descriptor: file descriptor
        """
        #enable writings if necessary
        read_mode = mode.find(u'r')>=0 and not mode.find('+')>=0
        self.logger.debug(u'Open %s read_mode=%s ro=%s' % (path, read_mode, self.is_readonly))
        if self.is_readonly and not read_mode and not self.__is_on_tmp(path):
            root = self.rw.is_path_on_root(path)
            self.__enable_write(root=root, boot=not root)

        #use system encoding if not specified
        if not encoding:
            encoding = locale.getpreferredencoding()

        #check binary mode
        if mode.find(u'b')==-1:
            return io.open(path, mode=mode, encoding=encoding)
        else:
            return io.open(path, mode=mode)

    def close(self, fd):
        """
        Close file descriptor

        Args:
            fd (descriptor): file descriptor
        """
        #close file descriptor
        fd.close()

        #disable writings
        read_mode = fd.mode.find(u'r')>=0 and not fd.mode.find(u'+')>=0
        self.logger.debug(u'Close %s read_mode=%s ro=%s' % (fd.name, read_mode, self.is_readonly))
        self.logger.debug(u'if self.is_readonly and not read_mode => %s' % (self.is_readonly and not read_mode))
        self.logger.debug(u'if self.is_readonly and not read_mode and not in self.__is_on_tmp(path) => %s' % (self.is_readonly and not read_mode and not self.__is_on_tmp(fd.name)))
        if self.is_readonly and not read_mode and not self.__is_on_tmp(fd.name):
            context = ReadWriteContext()
            context.src = fd.name
            context.action = u'close'
            context.is_readonly = self.is_readonly
            self.__disable_write(context)

    def write_data(self, path, data, encoding=None):
        """
        Write data on specified path

        Args:
            path (string): file path
            data (any): data to write
            encoding (string): file encoding (default is system one)

        Return:
            bool: True if operation succeed
        """
        fp = None
        res = False

        #encoding
        if not encoding:
            encoding = locale.getpreferredencoding()

        try:
            fp = self.open(path, u'w', encoding)
            fp.write(data)
            res = True

        except:
            self.logger.debug('Data to be written: %s' % data)
            self.logger.exception(u'Unable to write content to file "%s"' % path)
            self.crash_report.report_exception({
                u'message': u'Unable to write content to file "%s"' % path,
                u'encoding': encoding,
                u'path': path
            })
            res = False

        finally:
            if fp:
                self.close(fp)

        return res

    def read_data(self, path, encoding=None):
        """
        Read file content

        Args:
            path (string): file path
            encoding (string): file encoding (default is system one)

        Return:
            list: file lines
        """
        fp = None
        lines = None

        #encoding
        if not encoding:
            encoding = locale.getpreferredencoding()

        try:
            fp = self.open(path, u'r', encoding)
            lines = fp.readlines()

        except:
            self.logger.exception(u'Unable to get content of file "%s":' % path)
            self.crash_report.report_exception({
                u'message': u'Unable to get content of file "%s"' % path,
                u'encoding': encoding,
                u'path': path
            })

        finally:
            if fp:
                self.close(fp)

        return lines

    def read_json(self, path, encoding=None):
        """
        Read file content as json

        Args:
            path (string): file path
            encoding (string): file encoding (default is system one)

        Return:
            dict: json content as dict
        """
        lines = self.read_data(path, encoding)
        try:
            lines = json.loads(u'\n'.join(lines), encoding)
        except:
            self.logger.exception(u'Unable to parse file "%s" content as json:' % (path))
            self.crash_report.report_exception({
                u'message': u'Unable to parse file "%s" content as json' % path,
                u'encoding' : encoding,
                u'path': path
            })
            lines = ''

        return lines

    def write_json(self, path, data, encoding=None):
        """
        Write file as json format

        Args:
            path (string): file path
            data (any): data to write as json
            encoding (string): file encoding (default is system one)

        Return:
            bool: True if operation succeed
        """
        #ensure_ascii as workaround for unicode encoding on python 2.X https://bugs.python.org/issue13769
        json_data = unicode(json.dumps(data, ensure_ascii=False))

        return self.write_data(path, json_data, encoding)

    def rename(self, src, dst):
        """
        Rename file/dir to specified destination
        Alias of move
        """
        return self.move(src, dst)

    def move(self, src, dst):
        """
        Move file/dir to destination (uses shutil.move)

        Args:
            src (string): source
            dst (string): destination

        Return:
            bool: True if operation succeed
        """
        moved = False

        #enable writings if necessary
        if self.is_readonly and (not self.__is_on_tmp(src) or not self.__is_on_tmp(dst)):
            root = self.rw.is_path_on_root(src) or self.rw.is_path_on_root(dst)
            boot = not self.rw.is_path_on_root(src) or not self.rw.is_path_on_root(dst)
            self.__enable_write(root=root, boot=root)

        #move 
        try:
            shutil.move(src, dst)
            moved = True
        except:
            self.logger.exception(u'Exception moving directory from "%s" to "%s"' % (src, dst))
            self.crash_report.report_exception({
                u'message': u'Exception moving directory from "%s" to "%s"' % (src, dst),
                u'src': src,
                u'dst': dst
            })

        #disable writings
        if self.is_readonly and (not self.__is_on_tmp(src) or not self.__is_on_tmp(dst)):
            context = ReadWriteContext()
            context.src = src
            context.dst = dst
            context.action = u'move'
            context.root = root
            context.boot = boot
            context.is_readonly = self.is_readonly
            self.__disable_write(context)

        return moved

    def copy(self, src, dst):
        """
        Copy file to destination (uses shutil.copy2)

        Args:
            src (string): source file path
            dst (string): destination path

        Return:
            bool: True if operation succeed
        """
        #enable writings if necessary
        if self.is_readonly and (not self.__is_on_tmp(src) or not self.__is_on_tmp(dst)):
            root = self.rw.is_path_on_root(src) or self.rw.is_path_on_root(dst)
            boot = not self.rw.is_path_on_root(src) or not self.rw.is_path_on_root(dst)
            self.__enable_write(root=root, boot=root)

        #copy
        copied = False
        try:
            shutil.copy2(src, dst)
            copied = True
        except:
            self.logger.exception(u'Exception copying "%s" to "%s"' % (src, dst))
            self.crash_report.report_exception({
                u'message': u'Exception copying "%s" to "%s"' % (src, dst),
                u'src': src,
                u'dst': dst
            })

        #disable writings
        if self.is_readonly and (not self.__is_on_tmp(src) or not self.__is_on_tmp(dst)):
            context = ReadWriteContext()
            context.src = src
            context.dst = dst
            context.action = u'copy'
            context.root = root
            context.boot = boot
            context.is_readonly = self.is_readonly
            self.__disable_write(context)

        return copied

    def copy_dir(self, src, dst):
        """
        Copy directory content to destination (uses distutils.dir_util.copy_tree)

        Args:
            src (string): source dir path
            dst (string): destination path

        Return:
            bool: True if operation succeed
        """
        #enable writings if necessary
        if self.is_readonly and (not self.__is_on_tmp(src) or not self.__is_on_tmp(dst)):
            root = self.rw.is_path_on_root(src) or self.rw.is_path_on_root(dst)
            boot = not self.rw.is_path_on_root(src) or not self.rw.is_path_on_root(dst)
            self.__enable_write(root=root, boot=boot)

        #copy
        copied = False
        try:
            copy_tree(src, dst)
            copied = True
        except:
            self.logger.exception(u'Exception copying dir "%s" to "%s"' % (src, dst))
            self.crash_report.report_exception({
                u'message': u'Exception copying dir "%s" to "%s"' % (src, dst),
                u'src': src,
                u'dst': dst
            })

        #disable writings
        if self.is_readonly and (not self.__is_on_tmp(src) or not self.__is_on_tmp(dst)):
            context = ReadWriteContext()
            context.src = src
            context.dst = dst
            context.action = u'copy_dir'
            context.root = root
            context.boot = boot
            context.is_readonly = self.is_readonly
            self.__disable_write(context)

        return copied

    def remove(self, path):
        """
        Remove file (alias of rm function)

        Args:
            path (string): path
        
        Return:
            bool: True if operation succeed
        """
        return self.rm(path)

    def rm(self, path):
        """
        Remove file

        Args:
            path (string): path
        
        Return:
            bool: True if operation succeed
        """
        removed = False

        #enable writings if necessary
        if self.is_readonly and not self.__is_on_tmp(path):
            root = self.rw.is_path_on_root(path)
            self.__enable_write(root=root, boot=not root)

        #remove file
        try:
            if os.path.exists(path):
                os.remove(path)
                removed = True
        except:
            self.logger.exception(u'Exception removing "%s"' % path)
            self.crash_report.report_exception({
                u'message': u'Exception removing "%s"' % path,
                u'path': path
            })

        #disable writings
        if self.is_readonly and not self.__is_on_tmp(path):
            context = ReadWriteContext()
            context.src = path
            context.action = u'rm'
            context.root = root
            context.boot = not root
            context.is_readonly = self.is_readonly
            self.__disable_write(context)

        return removed

    def rmdir(self, path):
        """
        Remove directory

        Args:
            path (string): path
        
        Return:
            bool: True if operation succeed
        """
        removed = False

        #enable writings if necessary
        if self.is_readonly and not self.__is_on_tmp(path):
            root = self.rw.is_path_on_root(path)
            self.__enable_write(root=root, boot=not root)

        #remove dir
        try:
            if os.path.exists(path):
                shutil.rmtree(path, ignore_errors=True)
                removed = True
        except:
            self.logger.exception(u'Exception removing directory "%s"' % path)
            self.crash_report.report_exception({
                u'message': u'Exception removing directory "%s"' % path,
                u'path': path
            })

        #disable writings
        if self.is_readonly and not self.__is_on_tmp(path):
            context = ReadWriteContext()
            context.src = path
            context.action = u'rmdir'
            context.root = root
            context.boot = not root
            context.is_readonly = self.is_readonly
            self.__disable_write(context)

        return removed

    def mkdir(self, path, recursive=False):
        """
        Create directory

        Args:
            path (string): path
            recursive (bool): recursive creation (default False)

        Return:
            bool: True if operation succeed
        """
        created = False

        #enable writings if necessary
        if self.is_readonly and not self.__is_on_tmp(path):
            root = self.rw.is_path_on_root(path)
            self.__enable_write(root=root, boot=not root)

        #create dir
        try:
            if not os.path.exists(path):
                if recursive:
                    os.makedirs(path)
                else:
                    os.mkdir(path)
            created = True

        except:
            self.logger.exception(u'Exception creating "%s"' % path)
            self.crash_report.report_exception({
                u'message': u'Exception creating "%s"' % path,
                u'path': path
            })

        #disable writings
        if self.is_readonly and not self.__is_on_tmp(path):
            context = ReadWriteContext()
            context.src = path
            context.action = u'mkdir'
            context.root = root
            context.boot = not root
            context.is_readonly = self.is_readonly
            self.__disable_write(context)

        return created

    def mkdirs(self, path):
        """
        Create directories tree

        Args:
            path (string): path

        Return:
            bool: True if operation succeed
        """
        return self.mkdir(path, True)


    def rsync(self, src, dst, options=u'-ah --delete'):
        """
        Remove directory

        Args:
            src (string): source
            dst (string): destination
            options (string): rsync options
        
        Return:
            bool: True if operation succeed
        """
        error = False

        #enable writings if necessary
        if self.is_readonly and (not self.__is_on_tmp(src) or not self.__is_on_tmp(dst)):
            root = self.rw.is_path_on_root(src) or self.rw.is_path_on_root(dst)
            boot = not self.rw.is_path_on_root(src) or not self.rw.is_path_on_root(dst)
            self.__enable_write(root=root, boot=boot)

        #rsync
        try:
            console = Console()
            cmd = u'/usr/bin/rsync %s %s %s' % (options, src, dst)
            console.command(cmd)
            if console.get_last_return_code()!=0:
                self.logger.error(u'Error occured during rsync command execution "%s" (return code %s)' % (cmd, console.get_last_return_code()))
                error = True

        except:
            self.logger.exception(u'Exception executing rsync command "%s"' % cmd)
            self.crash_report.report_exception({
                u'message': u'Exception executing rsync command "%s"' % cmd,
                u'options': options,
                u'src': src,
                u'dst': dst
            })
            error = True

        #disable writings
        if self.is_readonly and (not self.__is_on_tmp(src) or not self.__is_on_tmp(dst)):
            context = ReadWriteContext()
            context.src = src
            context.dst = dst
            context.cmd = cmd
            context.options = options
            context.action = u'rsync'
            context.root = root
            context.boot = boot
            context.is_readonly = self.is_readonly
            self.__disable_write(context)

        return error

