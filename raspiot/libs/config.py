#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import InvalidParameter, MissingParameter, CommandError
import unittest
import os
import re
import io

class Config():
    """
    Helper class to read and write any configuration file.
    Give you methods:
     - to get file entries (regexp)
     - to set entry
     - to load and save file content
     - to backup and restore configuration file
    It also ensures to read file content as unicode
    """

    MODE_WRITE = u'w'
    MODE_READ = u'r'
    MODE_APPEND = u'a'

    def __init__(self, path, comment_tag):
        """
        Constructor

        Args:
            path (string): configuration file path
            comment_tag (string): comment tag
        """
        self.path = path
        self.backup_path = self.__get_backup_path(path)
        self.comment_tag = comment_tag
        self.__fd = None

    def __del__(self):
        """
        Destructor
        """
        self.__close()

    def __get_backup_path(self, path):
        """
        """
        base_path = os.path.dirname(path)
        base, ext = os.path.splitext(path)
        filename = os.path.split(base)[1]
        return os.path.join(base_path, '%s.backup%s' % (filename, ext))

    def __open(self, mode=u'r'):
        """
        Open config file

        Returns:
            file: file descriptor as returned by open() function

        Raises:
            Exception if file doesn't exist
        """
        if not os.path.exists(self.CONF):
            raise Exception(u'config.txt file does not exist')

        self.__fd = io.open(self.CONF, mode, encoding=u'utf-8')
        return self.__fd

    def __close(self):
        """
        Close file descriptor is still opened
        """
        if self.__fd:
            self.__fd.close()
            self.__fd = None

    def search(self, pattern):
        """
        """
        results = {}
        fd = self.__open()
        content = fd.read()
        self.__close()
        matches = re.finditer(pattern, content, re.UNICODE | re.MULTILINE)

        for matchNum, match in enumerate(matches):
            if len(match.groups())>0:
                results[match.group()] = match.groups()

        return results

    def uncomment(self, comment):
        """
        Uncomment specified line

        Args:
            comment (string): full line to search and uncomment

        Returns:
            bool: True if line commented
        """
        if not comment.startswith(self.comment_tag):
            return False

        #read file content
        fd = self.__open()
        lines = fd.readlines()
        self.__close()

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
            fd = self.__open(self.MODE_WRITE)
            fd.write(u''.join(lines))
            self.__close()

            return True

        else:
            return False

    def comment(self, comment):
        """
        Comment specified line

        Args:
            comment (string): full line to search and comment

        Returns:
            bool: True if line commented
        """
        if comment.startswith(self.comment_tag):
            return False

        #read file content
        fd = self.__open()
        lines = fd.readlines()
        self.__close()

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
            fd = self.__open(self.MODE_WRITE)
            fd.write(u''.join(lines))
            self.__close()

            return True

        else:
            return False

    def remove(self, removes):
        """
        Remove specified lines

        Args:
            removes (list): list of lines to remove. Line must be exactly the same

        Returns:
            bool: True if at least one line removed, False otherwise
        """
        fd = self.__open()
        lines = fd.readlines()
        self.__close()

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
            fd = self.__open(self.MODE_WRITE)
            fd.write(u''.join(lines))
            self.__close()

            return True

        else:
            return False

    def remove_after(self, header_pattern, line_pattern):
        """
        Remove line matching pattern after header pattern found

        Args:
            header_pattern (pattern): regexp header pattern
            line_pattern (pattern): regexp line pattern

        Returns:
            int: number of lines deleted (blank and commented lines not counted)
        """
        #read content
        fd = self.__open()
        lines = fd.readlines()
        self.__close()

        #get line indexes to remove
        start = False
        indexes = []
        index = 0
        count = 0
        for line in lines:
            if re.match(regex_header, line):
                #header found, start
                indexes.append(index)
                start = True
                count += 1
            elif count==4:
                #number of line to delete reached, stop
                break
            elif start and line.strip().startswith(self.comment_tag):
                #commented line
                continue
            elif start and re.match(regex_line, line):
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
            fd = self.__open(self.MODE_WRITE)
            fd.write(u''.join(lines))
            self.__close()

        return count
        
    def add(self, lines):
        """
        Add new line at end of file

        Args:
            lines (list): list of lines to add
        """
        #read content
        fd = self.__open()
        content = fd.readlines()
        self.__close()

        #add new line
        if len(lines[len(lines)-1])!=0:
            content.append('\n')
        for line in lines:
            content.append(line)

        #write config file
        fd = self.__open(self.MODE_WRITE)
        fd.write(u''.join(content))
        self.__close()

        return True

