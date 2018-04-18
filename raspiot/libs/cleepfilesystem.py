#!/usr/bin/env python
# -*- coding: utf-8 -*-

from console import Console
from raspiot.libs.readwrite import ReadWrite
import logging
import os
from threading import Lock, Timer
import io
import shutil

class CleepFilesystem():
    """
    Filesystem helper with read/write filesystem support (uses readwrite lib)
    A debounce function shifts switch to readonly mode to avoid multiple operation
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

        #disable writings
        self.logger.debug('Disable writings')
        self.rw.enable_write_on_root()
        self.__debounce_timer = None

        #release lock
        self.logger.debug('Release lock in really_disable_write')
        self.__rw_lock.acquire()

    def __enable_write(self):
        """
        Enable write mode
        """
        #acquire lock
        self.logger.debug('Acquire lock in enable_write')
        self.__rw_lock.acquire()

        if self.__debounce_timer is not None:
            #debounce timer running and we need to enable write mode, cancel timer
            self.__debounce_timer.cancel()
            self.__debounce_timer = None

        if self.__counter==0:
            #enable write
            self.logger.debug('Enable writings')
            self.rw.enable_write_on_root()

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
            return

        #decrease usage counter
        self.__counter -= 1

        if self.__counter==0:
            #disable write
            self.logger.debug('Launch debounce timer')
            self.__debounce_timer = Timer(self.DEBOUNCE_DURATION, self.__really_disable_write)
            self.__debounce_timer.start()

        else:
            #operation still need write mode
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

    def open(self, path, mode, encoding=None):
        """
        Open file

        Args:
            path (string): file path
            mode (string): mode as builtin open() function
            encoding (string): file encoding

        Return:
            descriptor: file descriptor
        """
        #enable writings if necessary
        read_mode = mode.find('r')>=0 and not mode.find('+')>=0
        if not read_mode and not self.__is_on_tmp(path):
            self.__enable_write()

        return io.open(path, mode=mode, encoding=encoding)

    def close(self, fd):
        """
        Close file descriptor

        Args:
            fd (descriptor): file descriptor
        """
        #disable writings
        self.__disable_write()

        #close file descriptor
        fd.close()

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
        self.__disable_writings()

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
        self.__disable_writings()

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
        self.__disable_writings()

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
        self.__disable_writings()

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
        self.__disable_writings()


