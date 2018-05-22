#!/usr/bin/env python
# -*- coding: utf-8 -*-

from console import Console
from raspiot.libs.readwrite import ReadWrite
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
        #members
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)
        self.rw = ReadWrite()
        self.__counter = 0;
        self.__rw_lock = Lock()
        self.__debounce_timer = None
        #self.__rw_lock = glock.BoundedSemaphore(1)

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
        self.logger.debug('Acquire lock in enable_write %s' % type(self.__rw_lock))
        self.__rw_lock.acquire()

        if self.__debounce_timer is not None:
            #debounce timer running and we need to enable write mode, cancel timer
            self.__debounce_timer.cancel()
            self.__debounce_timer = None

        if self.__counter==0:
            #first to request writing, enable it
            self.logger.debug('Enable writings')
            self.rw.enable_write_on_root()
            self.__counter += 1

        else:
            #write mode already enabled
            pass

        #increase usage counter
        self.__counter += 1

        #release lock
        self.logger.debug('Release lock in enable_write')
        self.__rw_lock.release()

    def __disable_write(self):
        """
        Disable write mode
        """
        #acquire lock
        self.logger.debug('Acquire lock in disable_write')
        self.__rw_lock.acquire()

        #cancel action if necessary
        if self.__counter==0:
            #not in writing mode
            self.logger.warning(u'Not in writing mode, a bug surely exist!')
            return

        #decrease usage counter
        self.__counter -= 1

        if self.__counter==0:
            #disable write
            self.logger.debug('Launch debounce timer')
            self.__debounce_timer = Timer(self.DEBOUNCE_DURATION, self.__really_disable_write)
            self.__debounce_timer.start()

        else:
            #a running action still needs write mode
            pass

        #release lock
        self.logger.debug('Release lock in disable_write')
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

    def open(self, path, mode, encoding=u'utf-8'):
        """
        Open file

        Args:
            path (string): file path
            mode (string): mode as builtin open() function
            encoding (string): file encoding (default utf8)

        Return:
            descriptor: file descriptor
        """
        #enable writings if necessary
        read_mode = mode.find(u'r')>=0 and not mode.find('+')>=0
        self.logger.debug(u'Open %s read_mode=%s' % (path, read_mode))
        if not read_mode and not self.__is_on_tmp(path):
            self.__enable_write()

        return io.open(path, mode=mode, encoding=encoding)

    def close(self, fd):
        """
        Close file descriptor

        Args:
            fd (descriptor): file descriptor
        """
        self.logger.debug('Close %s' % fd.name)
        #disable writings
        read_mode = fd.mode.find('r')>=0 and not fd.mode.find('+')>=0
        if not read_mode:
            self.__disable_write()

        #close file descriptor
        fd.close()

    def read_json(self, path, encoding=u'utf-8'):
        """
        Read file content as json

        Args:
            path (string): file path
            encoding (string): file encoding (default utf8)

        Return:
            dict: json content as dict
        """
        fp = None
        lines = None

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

    def write_json(self, path, data, encoding=u'utf-8'):
        """
        Write file as json format

        Args:
            path (string): file path
            data (any): data to write as json
            encoding (string): file encoding (default utf8)
        """
        fp = None
        res = False

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

    def makedirs(self, path):
        """
        Make directory structure

        Args:
            path (string): source

        Return:
            bool: True if operation succeed
        """
        #enable writings if necessary
        if not self.__is_on_tmp(path):
            self.__enable_write()

        #create dirs
        os.makedirs(path)

        #disable writings
        self.__disable_write()

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
        #enable writings if necessary
        if not self.__is_on_tmp(src) or not self.__is_on_tmp(dst):
            self.__enable_write()

        #move 
        shutil.move(src, dst)

        #disable writings
        self.__disable_write()

    def copy(self, src, dst):
        """
        Copy file/dir to destination (uses shutil.copy2)

        Args:
            src (string): source path
            dst (string): destination path

        Return:
            bool: True if operation succeed
        """
        #enable writings if necessary
        if not self.__is_on_tmp(src) or not self.__is_on_tmp(dst):
            self.__enable_write()

        #copy
        shutil.copy2(src, dst)

        #disable writings
        self.__disable_write()

    def rm(self, path):
        """
        Remove file

        Args:
            path (string): path
        
        Return:
            bool: True if operation succeed
        """
        #enable writings if necessary
        if not self.__is_on_tmp(path):
            self.__enable_write()

        #remove file
        os.remove(path)

        #disable writings
        self.__disable_write()

    def rmdir(self, path, recursive=False):
        """
        Remove directory

        Args:
            path (string): path
            recursive (bool): recursive deletion (default False)
        
        Return:
            bool: True if operation succeed
        """
        #enable writings if necessary
        if not self.__is_on_tmp(path):
            self.__enable_write()

        #remove dir
        if recursive:
            os.removedirs(path)
        else:
            os.remove(path)

        #disable writings
        self.__disable_write()


