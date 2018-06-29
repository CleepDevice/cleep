#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.internals.console import Console
from raspiot.libs.internals.readwrite import ReadWrite
import logging
import os
from threading import Timer, Lock
import gevent.lock as glock
import io
import shutil
import json


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
        self.rw = ReadWrite()
        self.__counter = 0;
        self.__rw_lock = Lock()
        self.__debounce_timer = None

        #check if os is in readonly mode
        self.is_readonly = self.__is_readonly_filesystem()
        if self.is_readonly:
            self.logger.info(u'Raspiot is running on readonly configured filesystem')

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
                self.logger.info(u'Running RaspIot on configured read-only filesystem')
                return True

        return False

    def __really_disable_write(self):
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
        self.rw.disable_write_on_root()

        #release lock
        self.logger.debug('Release lock in really_disable_write')
        self.__rw_lock.release()

    def __enable_write(self):
        """
        Enable write mode
        """
        #acquire lock
        self.logger.debug('Acquire lock in enable_write [counter=%s]' % (self.__counter))
        self.__rw_lock.acquire()

        if self.__debounce_timer is not None:
            #debounce timer running and we need to enable write mode, cancel timer
            self.__debounce_timer.cancel()
            self.__debounce_timer = None

        if self.__counter==0:
            #first to request writing, enable it
            self.logger.debug('Enable writings')
            self.rw.enable_write_on_root()
            #self.__counter += 1

        else:
            #write mode already enabled
            pass

        #increase usage counter
        self.__counter += 1

        #release lock
        self.logger.debug('Release lock in enable_write [counter=%s]' % self.__counter)
        self.__rw_lock.release()

    def __disable_write(self):
        """
        Disable write mode
        """
        #acquire lock
        self.logger.debug('Acquire lock in disable_write [counter=%s]' % self.__counter)
        self.__rw_lock.acquire()

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
            self.__debounce_timer = Timer(self.DEBOUNCE_DURATION, self.__really_disable_write)
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

    def enable_write(self):
        """
        Enable write as long as you disable it
        This function must be used in specific cases when you need to disable readonly mode for a while (like system update)
        Please make sure to call disable_write after you finished your process!
        """
        self.logger.warning(u'Filesystem readonly protection is disabled completely by application!')
        self.__enable_write()

    def disable_write(self):
        """
        Disable write
        This function must be used in specific cases when you need to disable readonly mode for a while (like system update)
        Use this function only if you called enable_write function before!
        """
        self.logger.info(u'Filesystem readonly protection is enabled again')
        self.__disable_write()

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
            self.__enable_write()

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
            self.__disable_write()

    def read_json(self, path, encoding=None):
        """
        Read file content as json

        Args:
            path (string): file path
            encoding (string): file encoding (default is system one)

        Return:
            dict: json content as dict
        """
        fp = None
        lines = None

        #encoding
        if not encoding:
            encoding = locale.getpreferredencoding()

        try:
            fp = self.open(path, u'r', encoding)
            lines = fp.readlines()
            lines = json.loads(u'\n'.join(lines), encoding)

        except:
            self.logger.exception(u'Unable to get json content of "%s":' % path)

        finally:
            if fp:
                self.close(fp)

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
        fp = None
        res = False

        #encoding
        if not encoding:
            encoding = locale.getpreferredencoding()

        try:
            fp = self.open(path, u'w', encoding)
            #ensure_ascii as workaround for unicode encoding on python 2.X https://bugs.python.org/issue13769
            fp.write(unicode(json.dumps(data, ensure_ascii=False)))
            res = True

        except:
            self.logger.exception(u'Unable to write json content to "%s"' % path)
            res = False

        finally:
            if fp:
                self.close(fp)

        return res

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
            self.__enable_write()

        #move 
        try:
            shutil.move(src, dst)
            moved = True
        except:
            self.logger.exception(u'Exception moving directory from "%s" to "%s"' % (src, dst))

        #disable writings
        if self.is_readonly and (not self.__is_on_tmp(src) or not self.__is_on_tmp(dst)):
            self.__disable_write()

        return moved

    def copy(self, src, dst):
        """
        Copy file/dir to destination (uses shutil.copy2)

        Args:
            src (string): source path
            dst (string): destination path

        Return:
            bool: True if operation succeed
        """
        copied = False

        #enable writings if necessary
        if self.is_readonly and (not self.__is_on_tmp(src) or not self.__is_on_tmp(dst)):
            self.__enable_write()

        #copy
        try:
            shutil.copy2(src, dst)
            copied = True
        except:
            self.logger.exception(u'Exception copying "%s" to "%s"' % (src, dst))

        #disable writings
        if self.is_readonly and (not self.__is_on_tmp(src) or not self.__is_on_tmp(dst)):
            self.__disable_write()

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
            self.__enable_write()

        #remove file
        try:
            if os.path.exists(path):
                os.remove(path)
                removed = True
        except:
            self.logger.exception(u'Exception removing "%s"' % path)

        #disable writings
        if self.is_readonly and not self.__is_on_tmp(path):
            self.__disable_write()

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
            self.__enable_write()

        #remove dir
        try:
            if os.path.exists(path):
                shutil.rmtree(path, ignore_errors=True)
                removed = True
        except:
            self.logger.exception(u'Exception removing directory "%s"' % path)

        #disable writings
        if self.is_readonly and not self.__is_on_tmp(path):
            self.__disable_write()

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
            self.__enable_write()

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

        #disable writings
        if self.is_readonly and not self.__is_on_tmp(path):
            self.__disable_write()

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



