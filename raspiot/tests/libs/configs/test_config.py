#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append('/root/cleep/raspiot/libs/configs')
from config import Config
from raspiot.libs.internals.cleepfilesystem import CleepFilesystem
from raspiot.exception import MissingParameter, InvalidParameter, CommandError
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
from pprint import pformat
import io

logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class ConfigTestsWithoutBackup(unittest.TestCase):

    FILE_NAME = 'unittest.conf'

    def setUp(self):
        TestLib()
        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.path = os.path.join(os.getcwd(), self.FILE_NAME)
        logging.debug('Using conf file "%s"' % self.path)

        #fill with default content
        with io.open(self.path, 'w') as f:
            f.write(u"""#this is a comment
key=value
""")

        self.c = Config(self.fs, self.path, '#', backup=False)

    def tearDown(self):
        if os.path.exists('%s' % self.FILE_NAME):
            os.remove('%s' % self.FILE_NAME)

    def test_no_backup_file_created(self):
        self.assertFalse(os.path.exists('%s.backup.conf' % self.FILE_NAME))



class ConfigTestsWithBackup(unittest.TestCase):

    FILE_NAME = 'unittest.conf'
    CONTENT = u"""#this is a comment
key1=value1
key2=value2
value3=key3
"""

    def setUp(self):
        TestLib()
        #logging.root.setLevel(logging.TRACE)
        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.path = os.path.join(os.getcwd(), self.FILE_NAME)
        logging.debug('Using conf file "%s"' % self.path)

        #fill with default content
        with io.open(self.path, 'w') as f:
            f.write(self.CONTENT)

        self.c = Config(self.fs, self.path, '#', backup=True)

    def tearDown(self):
        if os.path.exists('%s.backup.conf' % self.FILE_NAME.replace('.conf', '')):
            os.remove('%s.backup.conf' % self.FILE_NAME.replace('.conf', ''))
        if os.path.exists('%s' % self.FILE_NAME):
            os.remove('%s' % self.FILE_NAME)

    def test_get_content(self):
        self.assertEqual(''.join(self.c.get_content()).strip(), self.CONTENT.strip(), 'Context is different')

    def test_get_content_file_not_found(self):
        os.remove(self.path)
        self.assertEqual(self.c.get_content(), [], 'Should return empty list')

    def test_backup_file_exists(self):
        self.assertTrue(os.path.exists('%s.backup.conf' % self.FILE_NAME.replace('.conf', '')))

    def test_config_file_exists(self):
        self.assertTrue(os.path.exists(self.FILE_NAME))

    def test_config_file_not_exists(self):
        os.remove(self.FILE_NAME)
        self.assertFalse(os.path.exists(self.FILE_NAME))

    def test_find(self):
        res = self.c.find('^(.*?)=(.*?)$')
        self.assertEqual(len(res), 3, 'Result should contains 3 results')
        res = self.c.find('^(value.*)=(.*?)$')
        self.assertEqual(len(res), 1, 'Result should contains 1 result')
        self.assertEqual(res[0][1][0], 'value3', 'Item must be equal to value3')
        self.assertEqual(res[0][1][1], 'key3', 'Item must be equal to key3')

    def test_find_file_not_exists(self):
        os.remove(self.path)
        self.assertFalse(self.c.find('test'), 'Should returns false if file not found')

    def test_find_in_string(self):
        res = self.c.find_in_string('.*([0-9]{3}).*', 'This is a special test for Cleep containing 666 number')
        self.assertEqual(len(res), 1)
        self.assertEqual(len(res[0][1]), 1)
        self.assertEqual(res[0][1][0], '666', 'Item must be equal to 666')

        string = """schema1:
key1=value1
key2=value2

schema2:
key1=value1

schema3:
key2=value2"""
        res = self.c.find_in_string('(schema\d+)|(key2)=(value\d+)', string)
        logging.debug(res)

    def test_comment(self):
        string = 'key2=value2'
        self.assertTrue(self.c.comment(string), 'Line not commented')
        content = '\n'.join(self.c.get_content())
        self.assertNotEqual(content.find('#%s' % string), -1, 'Commented line not found')

    def test_comment_unknown_string(self):
        string = 'key20=value2'
        old_content = self.c.get_content()
        self.assertFalse(self.c.comment(string))
        self.assertEqual('\n'.join(old_content), '\n'.join(self.c.get_content()))

    def test_comment_file_not_found(self):
        os.remove(self.path)
        self.assertFalse(self.c.comment('test'), 'Should returns false if file not found')

    def test_comment_no_comment_tag(self):
        self.c.comment_tag = None
        self.assertFalse(self.c.comment('test'), 'Should returns false is comment tag not set')

    def test_uncomment(self):
        string = 'this is a comment'
        self.assertTrue(self.c.uncomment('#%s' % string), 'Line not uncommented')
        content = '\n'.join(self.c.get_content())
        self.assertNotEqual(content.find(string), -1, 'Uncommented line not found')

    def test_uncomment_file_not_found(self):
        os.remove(self.path)
        self.assertFalse(self.c.uncomment('test'), 'Should returns false if file not found')

    def test_uncomment_no_comment_tag(self):
        self.c.comment_tag = None
        self.assertFalse(self.c.uncomment('test'), 'Should returns false is comment tag not set')

    def test_uncomment_unknown_string(self):
        string = 'this is not the comment'
        old_content = self.c.get_content()
        self.assertFalse(self.c.uncomment(string))
        self.assertEqual('\n'.join(old_content), '\n'.join(self.c.get_content()))

    def test_remove(self):
        string = u'key2=value2'
        self.assertTrue(self.c.remove(string), 'Content not removed')
        content = '\n'.join(self.c.get_content())
        self.assertEqual(content.find(string), -1, 'Removed line should not be found')

    def test_remove_unknown_string(self):
        string = u'key20=value2'
        old_content = self.c.get_content()
        self.assertFalse(self.c.remove(string), 'Content removed while not')
        self.assertEqual('\n'.join(old_content), '\n'.join(self.c.get_content()))

    def test_remove_file_not_found(self):
        os.remove(self.path)
        self.assertFalse(self.c.remove(u'test'), 'Should returns false if file not found')

    def test_restore_backup(self):
        original_content = '\n'.join(self.c.get_content())
        string = u'key2=value2'
        self.c.remove(string)
        self.c.restore_backup()
        self.assertEqual(original_content, '\n'.join(self.c.get_content()), 'Config file not properly restored')

    def test_remove_lines(self):
        lines = ['key1=value1', 'key2=value2']
        self.assertTrue(self.c.remove_lines(lines), 'Lines not removed')
        content = '\n'.join(self.c.get_content())
        self.assertEqual(content.find(lines[0]), -1, 'Removed line should not be found')
        self.assertEqual(content.find(lines[1]), -1, 'Removed line should not be found')

    def test_remove_lines_unknown_all_strings(self):
        content = '\n'.join(self.c.get_content())
        lines = ['key10=value1', 'key20=value2']
        self.assertFalse(self.c.remove_lines(lines), 'It should returns false if all lines were not removed')
        self.assertEqual(content, '\n'.join(self.c.get_content()))

    def test_remove_lines_unknown_one_line(self):
        content = '\n'.join(self.c.get_content())
        lines = ['key1=value1', 'key20=value2']
        self.assertTrue(self.c.remove_lines(lines) , 'Should returns true if at least one line removed')
        self.assertNotEqual(content, '\n'.join(self.c.get_content()))

    def test_remove_lines_file_not_found(self):
        os.remove(self.path)
        self.assertFalse(self.c.remove_lines(['line']), 'Should returns false if file not found')

    def test_remove_pattern(self):
        original_content = '\n'.join(self.c.get_content())
        pattern = '^key\d+=value\d+$'
        self.assertTrue(self.c.remove_pattern(pattern), 'No line removed')
        self.assertNotEqual(original_content, '\n'.join(self.c.get_content()))

    def test_remove_pattern_with_invalid_pattern(self):
        original_content = '\n'.join(self.c.get_content())
        pattern = '^key=value$'
        self.assertFalse(self.c.remove_pattern(pattern), 'Line removed')
        self.assertEqual(original_content, '\n'.join(self.c.get_content()))

    def test_remove_pattern_file_not_found(self):
        os.remove(self.path)
        self.assertFalse(self.c.remove_pattern('pattern'), 'Should returns false if file not found')

    def test_remove_after(self):
        header_pattern = '^#.*$'
        line_pattern = '^key\d+=value\d+$'

        self.assertTrue(self.c.remove_after(header_pattern, line_pattern, 2), 'Content not removed')
        self.assertEqual(''.join(self.c.get_content()).find('key1=value1'), -1, 'Removed line found')
        self.assertNotEqual(''.join(self.c.get_content()).find('key2=value2'), -1, 'Removed line not found')

        self.c.restore_backup()
        self.assertTrue(self.c.remove_after(header_pattern, line_pattern, 3), 'Content not removed')
        self.assertEqual(''.join(self.c.get_content()).find('key1=value1'), -1, 'Removed line found')
        self.assertEqual(''.join(self.c.get_content()).find('key2=value2'), -1, 'Removed line found')

    def test_remove_after_file_not_found(self):
        os.remove(self.path)
        self.assertEqual(self.c.remove_after('header', 'line', 1), 0, 'Should returns 0 as removed lines')

    def test_replace_line(self):
        pattern = u'^key2=value2$'
        replace = u'key20=value20'
        self.assertTrue(self.c.replace_line(pattern, replace), 'Line not replaced')
        self.assertNotEqual('\n'.join(self.c.get_content()).find(replace), -1, 'Line not replaced')

    def test_replace_line_multiple_matches(self):
        pattern = u'^key\d+=value\d+$'
        replace = u'key20=value20'
        self.assertTrue(self.c.replace_line(pattern, replace), 'Line not replaced')
        self.assertEqual('\n'.join(self.c.get_content()).count(replace), 2, 'All occurences not replaced')

    def test_replace_line_invalid_params(self):
        with self.assertRaises(Exception) as cm:
            self.c.replace_line(None, 'test')
        self.assertEqual(cm.exception.message, 'Parameter "pattern" must be specified')

        with self.assertRaises(Exception) as cm:
            self.c.replace_line('test', None)
        self.assertEqual(cm.exception.message, 'Parameter "replace" must be specified')

        with self.assertRaises(Exception) as cm:
            self.c.replace_line(666, 'test')
        self.assertEqual(cm.exception.message, 'Parameter "pattern" must be unicode')

        with self.assertRaises(Exception) as cm:
            self.c.replace_line(u'pattern', 666)
        self.assertEqual(cm.exception.message, 'Parameter "replace" must be a string or unicode')

    def test_add_lines(self):
        line1 = 'key666=value666'
        line2 = 'key999=value999'
        self.assertTrue(self.c.add_lines([line1]), 'Line not added')
        self.assertEqual(self.c.get_content()[-1], line1, 'Line not added at end of file')

        self.c.restore_backup()
        self.assertTrue(self.c.add_lines([line1], False), 'Line not added')
        self.assertEqual(self.c.get_content()[0].strip(), line1, 'Line not added at beginning of file')

        self.c.restore_backup()
        self.assertTrue(self.c.add_lines([line1, line2]), 'Lines not added')
        self.assertEqual(self.c.get_content()[-1].strip(), line2, 'Line2 not added at end of file')
        self.assertEqual(self.c.get_content()[-2].strip(), line1, 'Line1 not added at end of file')

        self.c.restore_backup()
        self.assertTrue(self.c.add_lines([line1, line2], False), 'Lines not added')
        self.assertEqual(self.c.get_content()[0].strip(), line1, 'Line1 not added at beginning of file')
        self.assertEqual(self.c.get_content()[1].strip(), line2, 'Line2 not added at beginning of file')

    def test_add_lines_file_not_found(self):
        os.remove(self.path)
        self.assertFalse(self.c.add_lines(['test']), 'Should returns false if file not found')

    def test_add_lines_invalid_params(self):
        with self.assertRaises(Exception) as cm:
            self.c.add_lines('test')
        with self.assertRaises(Exception) as cm:
            self.c.add_lines(u'test')
        with self.assertRaises(Exception) as cm:
            self.c.add_lines(666)
        self.assertEqual(cm.exception.message, 'Lines parameter must be list of string')

    def test_add(self):
        line1 = u'# code to append'
        line2 = u'# in config file'

        self.assertTrue(self.c.add(line1+u'\n'+line2), 'Content not added')
        self.assertEqual(self.c.get_content()[-2].strip(), line1, 'Line1 not added at correct place')
        self.assertEqual(self.c.get_content()[-1].strip(), line2, 'Line2 not added at correct place')

        self.c.restore_backup()
        self.assertTrue(self.c.add(line1+u'\n'+line2, False), 'Content not added')
        self.assertEqual(self.c.get_content()[0].strip(), line1, 'Line1 not added at correct place')
        self.assertEqual(self.c.get_content()[1].strip(), line2, 'Line2 not added at correct place')

    def test_add_invalid_params(self):
        with self.assertRaises(Exception) as cm:
            self.c.add('lines')
        with self.assertRaises(Exception) as cm:
            self.c.add(666)
        self.assertEqual(cm.exception.message, 'Lines parameter must be unicode string')

    def test_add_file_not_found(self):
        os.remove(self.path)
        self.assertFalse(self.c.add(u'test'), 'Should returns false if file not found')
        

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_config.py
    #coverage report -m
    unittest.main()

