#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import InvalidParameter, MissingParameter, CommandError
import os
import re
import io
import shutil
import logging
import time

class Config():
    """
    Helper class to read and write any configuration file.
    Give you methods:
     - to get file entries (regexp)
     - to set entry
     - to load and save file content
     - to backup and restore configuration file
    It also ensures to read file content as unicode and it uses cleep filesystem to operate on readonly cleep distribution
    """

    MODE_WRITE = u'w'
    MODE_READ = u'r'
    MODE_APPEND = u'a'

    def __init__(self, cleep_filesystem, path, comment_tag, backup=True):
        """
        Constructor

        Args:
            cleep_filesystem: CleepFilesystem instance
            path (string): configuration file path. If None specified, CONF member will be used instead
            comment_tag (string): comment tag
            backup (bool): auto backup original file (default True). Enabled only if path is not None
        """
        self.cleep_filesystem = cleep_filesystem
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)
        self.path = path
        self.backup_path = None
        self.comment_tag = comment_tag
        self.__fd = None

        #backup original file
        if path is not None and backup:
            self.backup_path = self.__get_backup_path(path)
            self.__make_backup()

    def __del__(self):
        """
        Destructor
        """
        self._close()

    def __get_path(self):
        """
        Return current cleaned conf file path

        Returns:
            string: cleaned path
        """
        if self.path:
            #use path value specified in constructor
            self.logger.debug(u'Use path value specified in constructor (%s)' % self.path)
            return self.path

        #use CONF member
        path = getattr(self, u'CONF', u'')
        path = os.path.expanduser(path)
        path = os.path.realpath(path)

        return path

    def __make_backup(self):
        """
        Backup original file if necessary
        """
        if not os.path.exists(self.backup_path) and os.path.exists(self.__get_path()):
            self.cleep_filesystem.copy(self.__get_path(), self.backup_path)

    def restore_backup(self):
        """
        Overwrite original config file by backup one
        """
        if not self.backup_path:
            self.logger.info(u'Backup disabled when path is not specified in class init')
            return False

        if os.path.exists(self.backup_path):
            self.cleep_filesystem.copy(self.backup_path, self.__get_path())
            return True

        return False

    def __get_backup_path(self, path):
        """
        Return backup path

        Args:
            path (string): path of path to backup
        """
        base_path = os.path.dirname(path)
        base, ext = os.path.splitext(path)
        filename = os.path.split(base)[1]

        return os.path.join(base_path, '%s.backup%s' % (filename, ext))

    def _open(self, mode=u'r', encoding=None):
        """
        Open config file

        Args:
            mode (string): opening file mode (see MODE_XXX)
            encoding (string): encoding to use to open file (default is system one)

        Returns:
            file: file descriptor as returned by open() function

        Raises:
            Exception if file doesn't exist
        """
        if not os.path.exists(self.__get_path()) and mode==self.MODE_READ:
            raise Exception(u'%s file does not exist' % self.__get_path())

        self.__fd = self.cleep_filesystem.open(self.__get_path(), mode, encoding)

        return self.__fd

    def _close(self):
        """
        Close file descriptor is still opened
        """
        if self.__fd:
            self.cleep_filesystem.close(self.__fd)
            self.__fd = None

    def _write(self, content):
        """
        Write content to config file.
        This function removes automatically spaces at end of content

        Args:
            content (string): content to write
        """
        try:
            fd = self._open(self.MODE_WRITE)
            fd.write(content.rstrip())
            self._close()
            time.sleep(0.25)

            return True

        except:
            self.logger.exception('Failed to write config file:')
            return False

    def exists(self):
        """
        Return True if config file exists
        
        Returns:
            bool: True if config file exists
        """
        return os.path.exists(self.__get_path())

    def find(self, pattern, options=re.UNICODE | re.MULTILINE):
        """
        Find all pattern matches in config files. Found order is respected.

        Args:
            pattern (string): search pattern
            options (flag): regexp flags (see https://docs.python.org/2/library/re.html#module-contents)

        Returns:
            list: list of matches::
                [
                    (group (string), subgroups (tuple)),
                    ...
                ]
        """
        #check file existence
        if not self.exists():
            self.logger.debug(u'No file found (%s). Return empty result' % self.__get_path())
            return []

        results = []
        fd = self._open()
        content = fd.read()
        self._close()
        matches = re.finditer(pattern, content, options)

        #concat content list if options singleline specified (DOTALL)
        #if re.DOTALL & options:
        #    content = u''.join(content)

        for matchNum, match in enumerate(matches):
            group = match.group().strip()
            if len(group)>0 and len(match.groups())>0:
                #results[group] = match.groups()
                results.append((group, match.groups()))

        return results

    def find_in_string(self, pattern, content, options=re.UNICODE | re.MULTILINE):
        """
        Find all pattern matches in specified string. Found order is respected.

        Args:
            pattern (string): search pattern
            content (string): string to search in
            options (flag): regexp flags (see https://docs.python.org/2/library/re.html#module-contents)

        Returns:
            list: list of matches::
                [
                    (group (string), subgroups (tuple)),
                    ...
                ]
        """
        results = []

        #check file existence
        if not self.exists():
            self.logger.debug(u'No file found (%s). Return empty result' % self.__get_path())
            return []

        matches = re.finditer(pattern, content, options)
        for matchNum, match in enumerate(matches):
            group = match.group().strip()
            if len(group)>0 and len(match.groups())>0:
                #results[group] = match.groups()
                results.append((group, match.groups()))

        return results
   

    def uncomment(self, comment):
        """
        Uncomment specified line

        Args:
            comment (string): full line to search and uncomment

        Returns:
            bool: True if line commented
        """
        if self.comment_tag is None:
            #no way to add comment
            return False
        if not comment.startswith(self.comment_tag):
            #line already uncommented
            return False
        if not self.exists():
            self.logger.debug(u'No file found (%s)' % self.__get_path())
            return False

        #read file content
        fd = self._open()
        lines = fd.readlines()
        self._close()

        #get line indexes to remove
        found = False
        index = 0
        for line in lines:
            if line.strip()==comment.strip():
                found = True
                lines[index] = lines[index][len(self.comment_tag):]
                break
            index += 1

        if found:
            #write config file
            return self._write(u''.join(lines))

        return False

    def comment(self, comment):
        """
        Comment specified line

        Args:
            comment (string): full line to search and comment

        Returns:
            bool: True if line commented
        """
        if self.comment_tag is None:
            #no way to add comment
            return False
        if comment.startswith(self.comment_tag):
            #line already commented
            return False
        if not self.exists():
            self.logger.debug(u'No file found (%s)' % self.__get_path())
            return False

        #read file content
        fd = self._open()
        lines = fd.readlines()
        self._close()

        #get line indexes to remove
        found = False
        index = 0
        for line in lines:
            if line.strip()==comment.strip():
                found = True
                lines[index] = u'%s%s' % (self.comment_tag, lines[index])
                break
            index += 1

        if found:
            #write config file
            return self._write(u''.join(lines))

        return False

    def remove(self, content):
        """
        Remove specified content (must be exactly the same string!)

        Args:
            content (string): string to remove

        Returns:
            bool: True if content removed
        """
        #check params
        if not isinstance(content, unicode):
            raise Exception('Content parameter must be unicode')
        if not self.exists():
            self.logger.debug(u'No file found (%s)' % self.__get_path())
            return False

        fd = self._open()
        lines = fd.read()
        self._close()

        #remove content
        before = len(lines)
        lines = lines.replace(content, '')
        after = len(lines)

        if before!=after:
            #write config file
            return self._write(u''.join(lines))
            
        return False

    def remove_lines(self, removes):
        """
        Remove specified lines

        Args:
            removes (list): list of lines to remove. Line must be exactly the same

        Returns:
            bool: True if at least one line removed, False otherwise
        """
        #check params
        if not isinstance(removes, list):
            raise Exception('Removes parameter must be list of string')
        if not self.exists():
            self.logger.debug(u'No file found (%s)' % self.__get_path())
            return False

        fd = self._open()
        lines = fd.readlines()
        self._close()

        #get line indexes to remove
        indexes = []
        for remove in removes:
            index = 0
            for line in lines:
                if line.strip()==remove.strip():
                    indexes.append(index)
                    break
                index += 1

        #delete lines
        indexes.sort()
        indexes.reverse()
        for index in indexes:
            lines.pop(index)

        if len(indexes)>0:
            #write config file
            return self._write(u''.join(lines))

        return False

    def remove_pattern(self, line_regexp):
        """
        Remove specified line pattern

        Args:
            line_regexp (pattern): regexp line pattern

        Return:
            int: number of lines removed
        """
        if not self.exists():
            self.logger.debug(u'No file found (%s)' % self.__get_path())
            return False

        #read content
        fd = self._open()
        lines = fd.readlines()
        self._close()

        #remove line
        count = 0
        indexes = []
        index = 0
        for line in lines:
            if re.match(line_regexp, line):
                indexes.append(index)
                count += 1

            index += 1

        #delete lines
        indexes.sort()
        indexes.reverse()
        for index in indexes:
            lines.pop(index)

        #write config file
        if len(indexes)>0:
            #write config file
            if self._write(u''.join(lines)):
                return count
            else:
                return 0
                
        return count

    def remove_after(self, header_regexp, line_regexp, lines_to_delete):
        """
        Remove line matching pattern after header pattern

        Args:
            header_pattern (pattern): regexp header pattern
            line_pattern (pattern): regexp line pattern
            lines_to_delete (int): number of lines to delete

        Returns:
            int: number of lines deleted (blank and commented lines not counted)
        """
        if not self.exists():
            self.logger.debug(u'No file found (%s)' % self.__get_path())
            return 0

        #read content
        fd = self._open()
        lines = fd.readlines()
        self._close()

        #get line indexes to remove
        start = False
        indexes = []
        index = 0
        count = 0
        for line in lines:
            if re.match(header_regexp, line):
                #header found, start
                indexes.append(index)
                start = True
                count += 1
            elif count==lines_to_delete:
                #number of line to delete reached, stop
                break
            elif start and self.comment_tag is not None and line.strip().startswith(self.comment_tag):
                #commented line
                continue
            elif start and re.match(line_regexp, line):
                #save index of line to delete
                indexes.append(index)
                count += 1
            index += 1

        #delete lines
        indexes.sort()
        indexes.reverse()
        for index in indexes:
            lines.pop(index)

        #write config file
        if len(indexes)>0:
            #write config file
            if self._write(u''.join(lines)):
                return count
            else:
                return 0

        return count

    def replace_line(self, pattern, replace):
        """
        Replace line identified by pattern by replace string

        Args:
            pattern (string): pattern used to detect line
            replace (string): string to replace

        Returns:
            bool: True if line found and replaced
        """
        #check params
        if pattern is None:
            raise Exception(u'Parameter "pattern" must be specified')
        if replace is None:
            raise Exception(u'Parameter "replace" must be specified')
        if not isinstance(replace, str) and not isinstance(replace, unicode):
            raise Exception(u'Parameter "replace" must be a string or unicode (%s)' % type(replace))

        #add new line if necessary
        if replace[len(replace)-1]!='\n':
            replace += u'\n'

        #read content
        fd = self._open()
        lines = fd.readlines()
        self._close()
        
        #search line
        prog = re.compile(pattern)
        new_content = []
        found = False
        for line in lines:
            if re.match(prog, line) is not None:
                #line found, append new one
                new_content.append(replace)
                found = True
            else:
                #append line
                new_content.append(line)

        #write config file
        if found:
            return self._write(u''.join(new_content))
        
        #not found
        return False
        
    def add_lines(self, lines):
        """
        Add new lines at end of file

        Args:
            lines (list): list of lines to add

        Return:
            bool: True if succeed
        """
        #check params
        if not isinstance(lines, list):
            raise Exception('Lines parameter must be list of string')
        if not self.exists():
            self.logger.debug(u'No file found (%s)' % self.__get_path())
            return False

        #read content
        fd = self._open()
        content = fd.readlines()
        self._close()

        #add new line
        if len(lines[len(lines)-1])!=0:
            content.append(u'\n')
        for line in lines:
            content.append(line)

        #write config file
        return self._write(u''.join(content))

    def add(self, content):
        """
        Add specified content at end of file

        Args:
            content (string): string to append

        Returns:
            bool: True if content added
        """
        #check params
        if not isinstance(content, unicode):
            raise Exception('Lines parameter must be list of string')
        if not self.exists():
            self.logger.debug(u'No file found (%s)' % self.__get_path())
            return False

        #read content
        fd = self._open()
        content_ = fd.read()
        self._close()

        #add new content
        content_ += content

        #write config file
        return self._write(content_)

    def get_content(self):
        """
        Get config file content

        Returns:
            list: list of lines
        """
        if not self.exists():
            self.logger.debug(u'No file found (%s)' % self.__get_path())
            return []

        #read content
        fd = self._open()
        lines = fd.readlines()
        self._close()
        
        return lines

    def dump(self): # pragma: no cover
        """
        Dump file content to stdout
        For debug and test purpose only
        """
        if not self.exists():
            self.logger.debug(u'No file found (%s)' % self.__get_path())
            return 

        #read content
        fd = self._open()
        lines = fd.readlines()
        self._close()

        #print lines
        print u''.join(lines)


