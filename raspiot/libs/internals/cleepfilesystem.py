#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.internals.console import Console
from raspiot.libs.internals.readwrite import ReadWrite, ReadWriteContext
import logging
import os
from threading import Timer, Lock
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
        #self.logger.setLevel(logging.TRACE)

        #members
        self.crash_report = None
        self.rw = ReadWrite()
        self.__counter_root = 0;
        self.__counter_boot = 0;
        self.__rw_lock = Lock()
        self.__debounce_timer_root = None
        self.__debounce_timer_boot = None
        self.__errors_busy = 0
        self.__errors = 0

        #check if os is in readonly mode
        self.is_readonly_fs = self.__is_readonly_filesystem()

    def _get_counters(self):
        """
        Useful during test to check if counters have awaited value

        Returns:
            dict: counters::

                {
                    root (int),
                    boot (int)
                }

        """
        return {
            'root': self.__counter_root,
            'boot': self.__counter_boot,
        }

    def __get_default_encoding(self):
        """
        Return default encoding
        """
        return locale.getdefaultlocale()[1]

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

    def __report_exception(self, *args, **kwargs):
        """
        Report exception using crash report instance if configured
        """
        if self.crash_report:
            self.crash_report.report_exception(args=args, kwargs=kwargs)

    def __is_readonly_filesystem(self):
        """
        Check if readonly is configured in OS

        Returns:
            bool: True if RO configured on OS
        """
        encoding = self.__get_default_encoding()
        fd = io.open(u'/etc/fstab', u'r', encoding=encoding)
        lines = fd.readlines()
        fd.close()
        for line in lines:
            if line.find(u',ro')>=0 or line.find(u'ro,')>=0:
                #read only configured
                return True

        return False

    def __really_disable_write(self, context, root=True, boot=False):
        """
        Function used in debounce timer
        """
        #acquire lock
        self.logger.trace('Acquire lock in really_disable_write')
        self.__rw_lock.acquire()

        #handle debounce timer canceled
        if root and self.__debounce_timer_root is None:
            self.logger.trace(u'Debounce timer for root has already been canceled')
            self.__rw_lock.release()
            return
        if boot and self.__debounce_timer_boot is None:
            self.logger.trace(u'Debounce timer for boot has already been canceled')
            self.__rw_lock.release()
            return
        
        #reset flag and disable writings
        if root:
            self.__debounce_timer_root = None
            self.logger.trace(u'/!\ Disable writings for root partition')
            self.rw.disable_write_on_root(context)
        if boot:
            self.__debounce_timer_boot = None
            self.logger.trace(u'/!\ Disable writings for boot partition')
            self.rw.disable_write_on_boot(context)

        #release lock
        self.logger.trace(u'Release lock in really_disable_write')
        self.__rw_lock.release()

    def __enable_write(self, root=True, boot=False):
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
        self.logger.trace(u'Acquire lock in enable_write')
        self.__rw_lock.acquire()

        if root and self.__debounce_timer_root is not None:
            #debounce timer running and we need to enable write mode, cancel timer
            self.logger.trace(u'Stop running debounce timer for root partition')
            self.__debounce_timer_root.cancel()
            self.__debounce_timer_root = None
        if boot and self.__debounce_timer_boot is not None:
            #debounce timer running and we need to enable write mode, cancel timer
            self.logger.trace(u'Stop running debounce timer for boot partition')
            self.__debounce_timer_boot.cancel()
            self.__debounce_timer_boot = None

        if root and self.__counter_root==0:
            #first to request writing, enable it
            self.logger.trace('/!\ Enable writings on root partition')
            self.rw.enable_write_on_root()
        if boot and self.__counter_boot==0:
            self.logger.trace('/!\ Enable writings on boot partition')
            self.rw.enable_write_on_boot()

        #increase usage counter
        if root:
            self.__counter_root += 1
            self.logger.trace(u'Increase root counter (counter_root=%s)' % self.__counter_root)
        if boot:
            self.__counter_boot += 1
            self.logger.trace(u'Increase boot counter (counter_boot=%s)' % self.__counter_boot)

        #release lock
        self.logger.trace(u'Release lock in enable_write')
        self.__rw_lock.release()

    def __disable_write(self, context, root=True, boot=False):
        """
        Disable write mode
        """
        #acquire lock
        self.__rw_lock.acquire()
        self.logger.trace(u'Acquire lock in disable_write')

        #cancel action if necessary
        if root and self.__counter_root==0:
            #not in writing mode
            self.logger.warning(u'Root partition not in writing mode, a bug surely exist!')

            self.logger.trace(u'Release lock in disable_write')
            self.__rw_lock.release()
            return
        if boot and self.__counter_boot==0:
            #not in writing mode
            self.logger.warning(u'Boot partition not in writing mode, a bug surely exist!')

            self.logger.trace(u'Release lock in disable_write')
            self.__rw_lock.release()
            return

        #decrease usage counter
        if root:
            self.__counter_root -= 1
            self.logger.trace(u'Decrease root counter (counter_boot=%s)' % self.__counter_root)
        if boot:
            self.__counter_boot -= 1
            self.logger.trace(u'Decrease root counter (counter_root=%s)' % self.__counter_root)

        #disable write after debounce time
        if root and self.__counter_root==0:
            self.logger.trace('Launch debounce timer for root partition')
            self.__debounce_timer_root = Timer(self.DEBOUNCE_DURATION, self.__really_disable_write, [context, root, boot])
            self.__debounce_timer_root.start()
        if boot and self.__counter_boot==0:
            self.logger.trace('Launch debounce timer for boot partition')
            self.__debounce_timer_boot = Timer(self.DEBOUNCE_DURATION, self.__really_disable_write, [context, root, boot])
            self.__debounce_timer_boot.start()

        #release lock
        self.logger.trace(u'Release lock in disable_write')
        self.__rw_lock.release()

    def __is_on_tmp(self, path):
        """
        Return True if specified file path is on /tmp which is writable

        Args:
            path (string): path

        Returns:
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
            root (bool): enable write on root partition (default True)
            boot (bool): enable write on boot partition (default False)
        """
        self.__enable_write(root=root, boot=boot)

    def disable_write(self, root=True, boot=True):
        """
        Disable write
        This function must be used in specific cases when you need to disable readonly mode for a while (like system update)
        Use this function only if you called enable_write function before!

        Args:
            root (bool): disable write on root partition (default True)
            boot (bool): disable write on boot partition (default True)
        """
        context = ReadWriteContext()
        context.action = u'disable_write'
        self.__disable_write(context, root=root, boot=boot)

    def open(self, path, mode, encoding=None):
        """
        Open file

        Args:
            path (string): file path
            mode (string): mode as builtin open() function
            encoding (string): file encoding (default is system one)

        Returns:
            descriptor: file descriptor
        """
        #enable writings if necessary
        read_mode = mode.find(u'r')>=0 and not mode.find('+')>=0
        self.logger.trace(u'Open %s read_mode=%s rofs=%s' % (path, read_mode, self.is_readonly_fs))
        if self.is_readonly_fs and not read_mode and not self.__is_on_tmp(path):
            root = self.rw.is_path_on_root(path)
            self.__enable_write(root=root, boot=not root)

        #use system encoding if not specified
        if not encoding:
            encoding = self.__get_default_encoding()
        self.logger.trace(u'Encoding: %s' % encoding)

        #check binary mode
        try:
            if mode.find(u'b')==-1:
                return io.open(path, mode=mode, encoding=encoding)
            else:
                return io.open(path, mode=mode)
        except:
            #error occured, disable write and rethrow exception
            read_mode = mode.find(u'r')>=0 and not mode.find('+')>=0
            self.logger.trace(u'Open %s read_mode=%s rofs=%s' % (path, read_mode, self.is_readonly_fs))
            if self.is_readonly_fs and not read_mode and not self.__is_on_tmp(path):
                root = self.rw.is_path_on_root(path)
                context = ReadWriteContext()
                context.src = path,
                context.action = u'open'
                context.is_readonly_fs = self.is_readonly_fs
                context.root = root
                context.boot = not root
                self.__disable_write(context, root=root, boot=not root)
            raise

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
        self.logger.trace(u'Close %s read_mode=%s ro=%s' % (fd.name, read_mode, self.is_readonly_fs))
        self.logger.trace(u'if self.is_readonly_fs and not read_mode => %s' % (self.is_readonly_fs and not read_mode))
        self.logger.trace(u'if self.is_readonly_fs and not read_mode and not in self.__is_on_tmp(path) => %s' % (self.is_readonly_fs and not read_mode and not self.__is_on_tmp(fd.name)))
        if self.is_readonly_fs and not read_mode and not self.__is_on_tmp(fd.name):
            context = ReadWriteContext()
            context.src = fd.name
            context.action = u'close'
            context.is_readonly_fs = self.is_readonly_fs
            root = self.rw.is_path_on_root(fd.name)
            self.__disable_write(context, root, not root)

    def write_data(self, path, data, encoding=None):
        """
        Write data on specified path

        Args:
            path (string): file path
            data (any): data to write
            encoding (string): file encoding (default is system one)

        Returns:
            bool: True if operation succeed
        """
        fp = None
        res = False

        try:
            fp = self.open(path, u'w', encoding)
            fp.write(data)
            res = True

        except:
            self.logger.trace('Data to be written: %s' % data)
            self.logger.exception(u'Unable to write content to file "%s"' % path)
            self.__report_exception({
                u'message': u'Unable to write content to file "%s"' % path,
                u'encoding': encoding or self.__get_default_encoding(),
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

        Returns:
            list: file lines or None if errors
        """
        fp = None
        lines = None

        try:
            fp = self.open(path, u'r', encoding)
            lines = fp.readlines()

        except:
            self.logger.exception(u'Unable to get content of file "%s":' % path)
            self.__report_exception({
                u'message': u'Unable to get content of file "%s"' % path,
                u'encoding': encoding or self.__get_default_encoding(),
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

        Returns:
            dict: json content as dict
        """
        lines = self.read_data(path, encoding)
        try:
            lines = json.loads(u'\n'.join(lines), encoding)
        except:
            self.logger.exception(u'Unable to parse file "%s" content as json:' % (path))
            self.__report_exception({
                u'message': u'Unable to parse file "%s" content as json' % path,
                u'encoding' : encoding or self.__get_default_encoding(),
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

        Returns:
            bool: True if operation succeed
        """
        #ensure_ascii as workaround for unicode encoding on python 2.X https://bugs.python.org/issue13769
        json_data = unicode(json.dumps(data, indent=4, ensure_ascii=False))

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

        Returns:
            bool: True if operation succeed
        """
        moved = False

        #enable writings if necessary
        if self.is_readonly_fs and (not self.__is_on_tmp(src) or not self.__is_on_tmp(dst)):
            root = self.rw.is_path_on_root(src) or self.rw.is_path_on_root(dst)
            boot = not self.rw.is_path_on_root(src) or not self.rw.is_path_on_root(dst)
            self.__enable_write(root=root, boot=root)

        #move 
        try:
            shutil.move(src, dst)
            moved = True
        except:
            self.logger.exception(u'Exception moving directory from "%s" to "%s"' % (src, dst))
            self.__report_exception({
                u'message': u'Exception moving directory from "%s" to "%s"' % (src, dst),
                u'src': src,
                u'dst': dst
            })

        #disable writings
        if self.is_readonly_fs and (not self.__is_on_tmp(src) or not self.__is_on_tmp(dst)):
            context = ReadWriteContext()
            context.src = src
            context.dst = dst
            context.action = u'move'
            context.root = root
            context.boot = boot
            context.is_readonly_fs = self.is_readonly_fs
            self.__disable_write(context, root, boot)

        return moved

    def copy(self, src, dst):
        """
        Copy file to destination (uses shutil.copy2)

        Args:
            src (string): source file path
            dst (string): destination path

        Returns:
            bool: True if operation succeed
        """
        #enable writings if necessary
        if self.is_readonly_fs and (not self.__is_on_tmp(src) or not self.__is_on_tmp(dst)):
            root = self.rw.is_path_on_root(src) or self.rw.is_path_on_root(dst)
            boot = not self.rw.is_path_on_root(src) or not self.rw.is_path_on_root(dst)
            self.logger.trace('root=%s boot=%s src=%s dst=%s' % (root, boot, src, dst))
            self.__enable_write(root=root, boot=boot)

        #copy
        copied = False
        try:
            shutil.copy2(src, dst)
            copied = True
        except:
            self.logger.exception(u'Exception copying "%s" to "%s"' % (src, dst))
            self.__report_exception({
                u'message': u'Exception copying "%s" to "%s"' % (src, dst),
                u'src': src,
                u'dst': dst
            })

        #disable writings
        if self.is_readonly_fs and (not self.__is_on_tmp(src) or not self.__is_on_tmp(dst)):
            context = ReadWriteContext()
            context.src = src
            context.dst = dst
            context.action = u'copy'
            context.root = root
            context.boot = boot
            context.is_readonly_fs = self.is_readonly_fs
            self.__disable_write(context, root, boot)

        return copied

    def copy_dir(self, src, dst):
        """
        Copy directory content to destination (uses distutils.dir_util.copy_tree)

        Args:
            src (string): source dir path
            dst (string): destination path

        Returns:
            bool: True if operation succeed
        """
        #enable writings if necessary
        if self.is_readonly_fs and (not self.__is_on_tmp(src) or not self.__is_on_tmp(dst)):
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
            self.__report_exception({
                u'message': u'Exception copying dir "%s" to "%s"' % (src, dst),
                u'src': src,
                u'dst': dst
            })

        #disable writings
        if self.is_readonly_fs and (not self.__is_on_tmp(src) or not self.__is_on_tmp(dst)):
            context = ReadWriteContext()
            context.src = src
            context.dst = dst
            context.action = u'copy_dir'
            context.root = root
            context.boot = boot
            context.is_readonly_fs = self.is_readonly_fs
            self.__disable_write(context, root, boot)

        return copied

    def ln(self, src, link, force=False):
        """
        Create symbolic link

        Args:
            src (string): source path
            link (string): link path
            force (bool): if True will delete existing file or link specified for link path
        
        Returns:
            bool: True if operation succeed
        """
        linked = False

        #enable writings if necessary
        if self.is_readonly_fs and (not self.__is_on_tmp(src) or not self.__is_on_tmp(link)):
            root = self.rw.is_path_on_root(src) or self.rw.is_path_on_root(link)
            boot = not self.rw.is_path_on_root(src) or not self.rw.is_path_on_root(link)
            self.__enable_write(root=root, boot=boot)

        #remove file
        try:
            delete = False
            if (os.path.exists(link) or os.path.islink(link)) and force==True:
                delete = True

            if delete:
                os.remove(link)

            os.symlink(src, link)
            if os.path.exists(link) and os.path.islink(link):
                linked = True
        except:
            self.logger.exception(u'Exception creating symlink from "%s" to "%s"' % (src, link))
            self.__report_exception({
                u'message': u'Exception symlinking "%s" to "%s"' % (src, link),
                u'src': src,
                u'link': link
            })

        #disable writings
        if self.is_readonly_fs and (not self.__is_on_tmp(src) or not self.__is_on_tmp(link)):
            context = ReadWriteContext()
            context.src = src
            context.link = link
            context.action = u'ln'
            context.root = root
            context.boot = boot
            context.is_readonly_fs = self.is_readonly_fs
            self.__disable_write(context, root, boot)

        return linked

    def remove(self, path):
        """
        Remove file (alias of rm function)

        Args:
            path (string): path
        
        Returns:
            bool: True if operation succeed
        """
        return self.rm(path)

    def rm(self, path):
        """
        Remove file

        Args:
            path (string): path
        
        Returns:
            bool: True if operation succeed
        """
        removed = False

        #enable writings if necessary
        self.logger.trace(u'is_readonly_fs=%s' % (self.is_readonly_fs))
        if self.is_readonly_fs and not self.__is_on_tmp(path):
            root = self.rw.is_path_on_root(path)
            self.__enable_write(root=root, boot=not root)

        #remove file
        try:
            if os.path.exists(path) or os.path.islink(path):
                os.remove(path)
                removed = True
        except:
            self.logger.exception(u'Exception removing "%s"' % path)
            self.__report_exception({
                u'message': u'Exception removing "%s"' % path,
                u'path': path
            })

        #disable writings
        if self.is_readonly_fs and not self.__is_on_tmp(path):
            context = ReadWriteContext()
            context.src = path
            context.action = u'rm'
            context.root = root
            context.boot = not root
            context.is_readonly_fs = self.is_readonly_fs
            self.__disable_write(context, root, not root)

        return removed

    def rmdir(self, path):
        """
        Remove directory

        Args:
            path (string): path
        
        Returns:
            bool: True if operation succeed
        """
        removed = False

        #enable writings if necessary
        if self.is_readonly_fs and not self.__is_on_tmp(path):
            root = self.rw.is_path_on_root(path)
            self.__enable_write(root=root, boot=not root)

        #remove dir
        try:
            if os.path.exists(path):
                shutil.rmtree(path, ignore_errors=True)
                removed = True
        except:
            self.logger.exception(u'Exception removing directory "%s"' % path)
            self.__report_exception({
                u'message': u'Exception removing directory "%s"' % path,
                u'path': path
            })

        #disable writings
        if self.is_readonly_fs and not self.__is_on_tmp(path):
            context = ReadWriteContext()
            context.src = path
            context.action = u'rmdir'
            context.root = root
            context.boot = not root
            context.is_readonly_fs = self.is_readonly_fs
            self.__disable_write(context, root, not root)

        return removed

    def mkdir(self, path, recursive=False):
        """
        Create directory

        Args:
            path (string): path
            recursive (bool): recursive creation (default False)

        Returns:
            bool: True if operation succeed
        """
        created = False

        #enable writings if necessary
        if self.is_readonly_fs and not self.__is_on_tmp(path):
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
            self.__report_exception({
                u'message': u'Exception creating "%s"' % path,
                u'path': path
            })

        #disable writings
        if self.is_readonly_fs and not self.__is_on_tmp(path):
            context = ReadWriteContext()
            context.src = path
            context.action = u'mkdir'
            context.root = root
            context.boot = not root
            context.is_readonly_fs = self.is_readonly_fs
            self.__disable_write(context, root, not root)

        return created

    def mkdirs(self, path):
        """
        Create directories tree

        Args:
            path (string): path

        Returns:
            bool: True if operation succeed
        """
        return self.mkdir(path, True)


    def rsync(self, src, dst, options=u'-ah --delete'):
        """
        Copy source to destination using rsync

        Args:
            src (string): source
            dst (string): destination
            options (string): rsync options
        
        Returns:
            bool: True if operation succeed
        """
        error = False

        #enable writings if necessary
        if self.is_readonly_fs and (not self.__is_on_tmp(src) or not self.__is_on_tmp(dst)):
            root = self.rw.is_path_on_root(src) or self.rw.is_path_on_root(dst)
            boot = not self.rw.is_path_on_root(src) or not self.rw.is_path_on_root(dst)
            self.__enable_write(root=root, boot=boot)

        #rsync
        try:
            console = Console()
            cmd = u'/usr/bin/rsync %s %s %s' % (options, src, dst)
            resp = console.command(cmd)
            self.logger.debug('%s resp: %s' % (cmd, resp))
            if resp[u'returncode']!=0:
                self.logger.error(u'Error occured during rsync command execution "%s" (return code %s)' % (cmd, console.get_last_return_code()))
                error = True

        except:
            self.logger.exception(u'Exception executing rsync command "%s"' % cmd)
            self.__report_exception({
                u'message': u'Exception executing rsync command "%s"' % cmd,
                u'options': options,
                u'src': src,
                u'dst': dst
            })
            error = True

        #disable writings
        if self.is_readonly_fs and (not self.__is_on_tmp(src) or not self.__is_on_tmp(dst)):
            context = ReadWriteContext()
            context.src = src
            context.dst = dst
            context.cmd = cmd
            context.options = options
            context.action = u'rsync'
            context.root = root
            context.boot = boot
            context.is_readonly_fs = self.is_readonly_fs
            self.__disable_write(context, root, boot)

        return error

