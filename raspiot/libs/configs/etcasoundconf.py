#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.configs.config import Config
from raspiot.exception import InvalidParameter
import logging
import re
import time
import os

class EtcAsoundConf(Config):
    """
    Handles /etc/asound.conf file

    It handles:
     - default playback device configuration
     - default capture device configuration
    """

    CONF = u'/etc/asound.conf'
    ASOUND_STATE = u'/var/lib/alsa/asound.state'

    CACHE_DURATION = 5.0

    DEFAULT_CONF = u"""pcm.!default {
    type hw
    card %(card_id)s
}

ctl.!default {
    type hw
    card %(card_id)s
}"""
    PCM_SECTION = u'pcm.!default'
    CTL_SECTION = u'ctl.!default'
    
    def __init__(self, cleep_filesystem):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
        """
        Config.__init__(self, cleep_filesystem, None, u'', False)

        #members
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)
        self.__cache = None
        self.__last_update = None

    def get_raw_configuration(self):
        """
        Get raw configuration with all sections and their content (only direct objects are handled, sub-ones can be wrong)

        Returns:
            dict: file content as dict::

                {
                    section name (string): {
                        card (int): card id (optional)
                        device (int): device id (optional)
                        other field (string): field value (string),
                        ...
                    }
                }

        """
        #check cache
        if self.__last_update is not None and (time.time()-self.__last_update)<self.CACHE_DURATION:
            return self.__cache

        #search for main sections
        results = self.find(r'(?:^#.*$)|(?:(.*?\..*?)\s+)|(?:\{\r?\n?((?:.*?\r?\n?)*)\})', re.UNICODE | re.MULTILINE)
        self.logger.trace('results: %s' % results)

        entries = {}
        current_section = None
        section_content_pattern = r'^\s*(.*?)\s+(.*?)$'
        for match, groups in results:
            #filter None values
            groups = list(filter(None, groups))
            if len(groups)==0: # pragma: no cover
                continue
            self.logger.trace('groups=%s' % (groups,))

            if match and not match.startswith(u'{'):
                #section
                current_section = groups[0]
                entries[current_section] = {}

            elif current_section is not None:
                #section content, parse it using defined pattern
                sub_results = self.find_in_string(section_content_pattern, groups[0], re.MULTILINE | re.UNICODE)
                for _, sub_groups in sub_results:
                    #filter None values
                    sub_groups = list(filter(None, sub_groups))
                    self.logger.trace('subgroups=%s' % (sub_groups,))

                    if len(sub_groups)==2:
                        entries[current_section][sub_groups[0]] = int(sub_groups[1]) if sub_groups[1].isdigit() else sub_groups[1]

        #cache
        self.__cache = entries
        self.__last_update = time.time()

        return entries

    def get_default_pcm_section(self):
        """
        Return default PCM section

        Returns:
            dict: section content or None if nothing
        """
        raw = self.get_raw_configuration()

        #return only pcm section
        return raw[self.PCM_SECTION] if self.PCM_SECTION in raw else None

    def get_default_ctl_section(self):
        """
        Return default CTL section

        Returns:
            dict: section content or None if nothing
        """
        raw = self.get_raw_configuration()

        #return only pcm section
        return raw[self.CTL_SECTION] if self.CTL_SECTION in raw else None

    def add_default_pcm_section(self, card_id, device_id=0):
        """
        Add default PCM section if not exists

        Args:
            card_id (int): card identifier
            device_id (int): device identifier (default value 0, set negative value to not store device)

        Returns:
            bool: True if section added or already exists in file
        """
        if card_id is None or not isinstance(card_id, int):
            raise InvalidParameter('Parameter "card_id" must be specified and integer')
        if not isinstance(device_id, int):
            raise InvalidParameter('Parameter "device_id" must be an integer')

        if self.PCM_SECTION in self.get_raw_configuration():
            self.logger.debug(u'PCM section already exists in file. Nothing updated.')
            return True

        lines = [
            u'pcm.!default {',
            u'    type hw',
            u'    card %s' % card_id
        ]
        if device_id>=0:
            lines.append(u'    device %s' % device_id)
        lines.append(u'}')
        self.__last_update = 0
        return self.add_lines(lines)

    def add_default_ctl_section(self, card_id, device_id=-1):
        """
        Add default CTL section if not exists

        Args:
            card_id (int): card identifier
            device_id (int): device identifier (default -1 means device field not written)

        Returns:
            bool: True if section added or already exists in file
        """
        if card_id is None or not isinstance(card_id, int):
            raise InvalidParameter('Parameter "card_id" must be specified and integer')
        if not isinstance(device_id, int):
            raise InvalidParameter('Parameter "device_id" must be an integer')

        if self.CTL_SECTION in self.get_raw_configuration():
            self.logger.debug(u'CTL section already exists in file. Nothing updated.')
            return True

        lines = [
            u'ctl.!default {',
            u'    type hw',
            u'    card %s' % card_id,
        ]
        if device_id>=0:
            lines.append(u'    device %s' % device_id)
        lines.append(u'}')
        self.__last_update = 0
        self.logger.trace('Add lines %s' % lines)
        return self.add_lines(lines)

    def save_default_file(self, card_id, device_id=0):
        """
        Save default asound.conf file overwriting existing one.

        Args:
            card_id (int): card identifier as returned by alsa
            device_id (int): device identifier as returned by alsa

        Returns:
            bool: True if config saved successfully
        """
        if card_id is None or not isinstance(card_id, int):
            raise InvalidParameter('Parameter "card_id" must be specified and integer')
        if not isinstance(device_id, int):
            raise InvalidParameter('Parameter "device_id" must be an integer')

        #generate and write new content
        content = self.DEFAULT_CONF % {
            u'card_id': card_id,
            u'device_id': device_id
        }
        self.logger.trace('content=%s' % content)

        return self._write(content)

    def delete(self):
        """
        Delete /etc/asound.conf and /var/lib/alsa/asound.state files to let system using its prefered device

        Returns:
            bool: True if files deleted or if files weren't existing
        """
        conf_deleted = True
        if os.path.exists(self.CONF):
            conf_deleted = self.cleep_filesystem.rm(self.CONF)

        state_deleted = True
        if os.path.exists(self.ASOUND_STATE):
            state_deleted = self.cleep_filesystem.rm(self.ASOUND_STATE)

        return conf_deleted and state_deleted


