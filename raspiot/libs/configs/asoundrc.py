#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.configs.config import Config
import logging
import re

class Asoundrc(Config):
    """
    Handles .asoundrc file from connected account

    It handles:
     - default playback device configuration
     - default capture device configuration
    """

    CONF = u'~/.asoundrc'

    CACHE_DURATION = 5.0

    DEFAULT_CONF = u"""pcm.!default {
    type hw
    card %(card_id)s
    device %(device_id)s
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
        Config.__init__(self, cleep_filesystem, self.CONF, u'', False)

        #members
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)
        self.__playback_devices = {}
        self.timestamp = None

    def get_raw_configuration(self):
        """
        Get raw configuration with all sections

        Args:
            command (string): command to execute

        Return:
            dict: dict of outputs::
                {
                    config section: {
                        section (string),
                        type (string),
                        cardid (int),
                        deviceid (int)
                    }
                }
        """
        #search for main sections
        results = self.find(r'(.*?)\s*{\s*(.*?)\s*}\s*', re.UNICODE | re.DOTALL)
        self.logger.debug('results: %s' % results)

        #first parse to identify sections and their content
        entries = {}
        default_card_id = None
        pcm_default_found = False
        pattern = r'(type\s+(.*)\s*)|(card\s+(\d))|(device\s+(\d))'
        for _, groups in results:
            #filter None values
            groups = filter(None, groups)
            self.logger.debug(groups)

            if len(groups)==2:
                #prepare values
                section, content = groups
                section = section.strip()
                entry = {
                    u'section': section,
                    u'type': None,
                    u'cardid': None,
                    u'deviceid': None
                }

                #parse section  content
                sub_results = self.find_in_string(pattern, content, re.UNICODE | re.MULTILINE)
                for _, sub_groups in sub_results:
                    #filter None values
                    sub_groups = filter(None, sub_groups)
                    self.logger.debug('section:%s => %s' % (section, sub_groups))

                    if len(sub_groups)==2:
                        if sub_groups[0].startswith(u'type'):
                            #type <string>
                            entry[u'type'] = sub_groups[1].strip()
                        elif sub_groups[0].startswith(u'card'):
                            #card <int>
                            try:
                                entry[u'cardid'] = int(sub_groups[1])
                            except:
                                self.logger.exception(u'Unable to get card id: "%s"' % sub_groups[1])
                        elif sub_groups[0].startswith(u'device'):
                            #device <int>
                            try:
                                entry[u'deviceid'] = int(sub_groups[1])
                            except:
                                self.logger.exception(u'Unable to get device id: "%s"' % sub_groups[1])

                #save entry
                entries[section] = entry

        return entries

    def get_configuration(self):
        """
        Return current configuration

        Return:
            dict: current pcm configuration or None if pcm section not found::
                {
                    section (string),
                    type (string),
                    cardid (int),
                    deviceid (int)
                }
        """
        raw = self.get_raw_configuration()

        #return only pcm section
        if self.PCM_SECTION in raw.keys():
            return raw[self.PCM_SECTION]

        return None

    def set_default_device(self, card_id, device_id):
        """
        Set default card for both controller and playback
        Please be aware that no verification is done

        Args:
            card_id (int): card identifier as returned by get_configuration
            device_id (int): device identifier as returned by get_configuration

        Return:
            bool: True if config saved successfully
        """
        #generate and write new content
        content = self.DEFAULT_CONF % {
            u'card_id': card_id,
            u'device_id': device_id
        }
        self.logger.debug('content=%s' % content)
        return self._write(content)



