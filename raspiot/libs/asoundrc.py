#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.config import Config
#from raspiot.libs.alsa import Alsa
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

    """pcm.!default {
    type asym
    playback.pcm {
        type plug
            slave.pcm "hw:1,0"
        }   
        capture.pcm {
            type plug
            slave.pcm "hw:1,0"
        }   
    }
    """

    DEFAULT = u"""pcm.!default {
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
    
    def __init__(self):
        """
        Constructor
        """
        Config.__init__(self, self.CONF, u'', False)

        #members
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)
        self.__playback_devices = {}
        self.timestamp = None
        #self.alsa = Alsa()

    #def get_card_name(self, card_id):
    #    """
    #    Return card name
    #
    #    Args:
    #        card_id (int): card identifier
    #
    #    Return:
    #        string or None
    #    """
    #    if self.timestamp is None or time.time()-self.timestamp>self.CACHE_DURATION:
    #        #get installed devices
    #        self.__playback_devices = self.alsa.get_playback_devices()
    #        
    #    #search for device id
    #    for device_name in self.__playback_devices.keys():
    #        if self.__playback_devices[device_name][u'cardid']==card_id:
    #            return device_name
    #
    #    return None

    def get_configuration(self):
        """
        Execute specified command and return parsed results

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

    def set_default_card(self, card_id, device_id):
        """
        Set default card for both controller and playback

        Args:
            card_id (int): card identifier as returned by get_configuration
            device_id (int): device identifier as returned by get_configuration

        Return:
            bool: True if config saved successfully
        """
        #check if specified card_id and device_id exists
        #card_name = self.get_card_name(card_id)
        #if card_name is None:
        #    self.logger.error(u'Specified card_id %d doesn\'t exist' % card_id)
        #    return False
        #found = False
        #for device_name in self.__playback_devices.keys():
        #    if self.__playback_devices[device_name][u'cardid']==card_id and self.__playback_devices[device_name][u'deviceid']==device_id:
        #        found = True
        #        break
        #if not found:
        #    self.logger.error(u'Specified device_id %d doesn\'t exist' % device_id)
        #    return False

        #generate and write new content
        content = self.DEFAULT % {
            u'card_id': card_id,
            u'device_id': device_id
        }
        self.logger.debug('content=%s' % content)
        return self._write(content)



