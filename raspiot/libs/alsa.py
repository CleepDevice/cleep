#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.console import AdvancedConsole
from raspiot.libs.asoundrc import Asoundrc
import logging
import re
import os

class Alsa(AdvancedConsole):
    """
    Alsa commands helper (aplay, arecord, amixer).
    """
    
    OUTPUT_TYPE_JACK = 1
    OUTPUT_TYPE_HDMI = 2
    OUTPUT_TYPE_EXTERNAL = 3 #external soundcard like hifiberry, respeaker...

    __KEY_PLAYBACK = u'playback_volume'
    __KEY_CAPTURE = u'capture_volume'

    #Devices profiles:
    #An entry is composed of:
    # - name (string): the device name as returned by alsa commands (aplay -l)
    # - type (int): the device type (see above OUTPUT_TYPE_XXX, it should be 3 for new devices)
    # - playback_volume (string): alsa control for the playback volume 
    # - playback_volume_data (tuple): key and pattern to get playback volume value
    # - capture_volume (string): alsa control for the capture volume 
    # - capture_volume_data (tuple): key and pattern to get capture volume value
    DEVICES_PROFILES = {
        u'bcm2835 ALSA': {
            u'name': u'bcm2835 ALSA',
            u'type': 1,
            u'playback_volume': u'PCM',
            u'playback_volume_data': (u'Mono', r'\[(\d*)%\]'),
            u'capture_volume': None,
            u'capture_volume_data': None
        },
        u'bcm2835 IEC958/HDMI': {
            u'name': u'bcm2835 IEC958/HDMI',
            u'type': 2,
            u'playback_volume': u'PCM',
            u'playback_volume_data': (u'Mono', r'\[(\d*)%\]'),
            u'capture_volume': None,
            u'capture_volume_data': None
        },
        u'seeed-2mic-voicecard': {
            u'name': u'seeed-2mic-voicecard',
            u'type': 3,
            u'playback_volume': u'Playback',
            u'playback_volume_data': (u'Front Left', r'\[(\d*)%\]'),
            u'capture_volume': u'Capture',
            u'capture_volume_data': (u'Front Left', r'\[(\d*)%\]')
        }
    }

    SIMPLE_MIXER_CONTROL = u'Simple mixer control'

    def __init__(self):
        """
        Constructor
        """
        AdvancedConsole.__init__(self)

        #members
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)
        self.asoundrc = Asoundrc()

    def __command(self, command):
        """
        Execute specified command and return parsed results

        Args:
            command (string): command to execute

        Return:
            dict: dict of outputs::
                {
                    card name: {
                        card name (string),
                        card id (int),
                        device id (id)
                    }
                }
        """
        results = self.find(command, r'^(?:card (\d)):.*\[(.*)\].*(?:device (\d)).*\[(.*)\].*$')
        entries = {}
        for group, groups in results:
            #filter None values
            #groups = filter(None, groups)
            self.logger.debug('groups (%d): %s' % (len(groups), groups))

            if len(groups)==4:
                #card id
                card_id = 0
                try:
                    card_id = int(groups[0])
                except:
                    self.logger.exception('Invalid card id:')

                #device id
                device_id = 0
                try:
                    device_id = int(groups[2])
                except:
                    self.logger.exception('Invalid card id:')

                #names (prefer using 2nd names if not empty)
                if len(groups[3].strip())>0:
                    name = groups[3].strip()
                else:
                    name = groups[1].strip()

                #store entry
                entries[name] = {
                    'name': name,
                    'cardid': card_id,
                    'deviceid': device_id
                }

        return entries

    def get_playback_devices(self):
        """
        Return list of playback devices

        Return:
            dict: dict of outputs::
                {
                    cardname: {
                        cardname (string),
                        cardid (int),
                        deviceid (id),
                        type (int): see OUTPUT_TYPE_XXX
                        supported (bool): supported by raspiot flag
                    }
                }
        """
        entries = self.__command(u'/usr/bin/aplay --list-devices')

        #append card type and supported flag
        for name in entries.keys():
            if name in self.DEVICES_PROFILES.keys():
                #supported device
                entries[name][u'supported'] = True
                entries[name][u'type'] = self.DEVICES_PROFILES[name][u'type']
    
            else:
                #unsupported devices
                entries[name][u'supported'] = False
                entries[name][u'type'] = self.OUTPUT_TYPE_EXTERNAL
                
        return entries

    def get_capture_devices(self):
        """
        Return list of capture devices

        Return:
            dict: dict of outputs::
                {
                    cardname: {
                        cardname (string),
                        cardid (int),
                        deviceid (id),
                    }
                }
        """
        return self.__command(u'/usr/bin/arecord --list-devices')

    def __amixer_command(self, command):
        """
        Execute amixer command and return formatted outputs

        Args:
            command (string): amixer command. No check is performed to make sure it is a amixer command

        Return:
            dict:
        """
        self.logger.debug('Amixer command: %s' % command)
        results = self.find(command, r'^(Simple mixer control \'(.*)\',\d)|\s{3}(.*)\s*:\s*(.*)$')

        entries = {}
        current_control = None
        for group, groups in results:
            #filter None values
            groups = filter(None, groups)
            self.logger.debug(groups)

            if groups[0].startswith(self.SIMPLE_MIXER_CONTROL):
                #new section found
                current_control = groups[1].strip()
                entries[current_control] = {}
            elif current_control is not None and len(groups)==2:
                #append property to current section
                entries[current_control][groups[0]] = groups[1].strip()

        return entries

    def __get_current_audio_profile(self):
        """
        Return profile of current audio device

        Return:
            dict: current profile (see DEVICES_PROFILES) or None if device is not supported
        """
        #TODO handle cache
        config = self.asoundrc.get_raw_configuration()
        self.logger.debug('Asoundrc config: %s' % config)
        
        #we only need pcm data (not ctl)
        if self.asoundrc.PCM_SECTION not in config.keys():
            self.logger.error('Invalid asoundrc file, %s section is mandatory: %s' % (self.asoundrc.PCM_SECTION, config))
            raise Exception('Internal error')
        config = config[self.asoundrc.PCM_SECTION]
        self.logger.debug('Config: %s' % config)

        #check if device is supported
        card_name = self.__get_card_name(config[u'cardid'])
        self.logger.debug('card_name: %s' % card_name)
        if card_name not in self.DEVICES_PROFILES.keys():
            self.logger.error(u'Unable to get volumes: unsupported sound device (card name=%s)' % card_name)
            return None

        #get profile
        profile = self.DEVICES_PROFILES[card_name]
        self.logger.debug('Found profile: %s' % profile)

        return profile

    def __get_card_name(self, card_id):
        """
        Return card name
       
        Args:
            card_id (int): card identifier
       
        Return:
            string or None
        """
        #search for device id
	playback_devices = self.get_playback_devices()
        for device_name in playback_devices.keys():
            if playback_devices[device_name][u'cardid']==card_id:
                return device_name
       
        return None

    def __get_or_set_volume(self, profile, get_key, volume=None):
        """
        Get infos from amixer command, parse results and get volume value
        With volume specified set command is executed, otherwise it is get command

        Args:
            profile (dict): current device profile
            get_key (string): GET_CAPTURE or GET_PLAYBACK
            volume (int): volume percentage or None

        Return:
            int: volume value or None if error occured
        """
        #get control
        control = profile[get_key]

        #execute command
        if volume is None:
            results = self.__amixer_command(u'/usr/bin/amixer get "%s"' % control)
        else:
            results = self.__amixer_command(u'/usr/bin/amixer set "%s" %s%%' % (control, volume))
        self.logger.debug(results)
        if len(results)==0 or control not in results.keys():
            self.logger.error(u'Unable to get volume: no control found in results: %s' % results)
            return None

        #parse result to get volume value
        (key, pattern) = profile[u'%s_data' % get_key]
        if key is None:
            self.logger.debug(u'No pattern specified for %s' % (get_key))
            return None
        elif key not in results[control].keys():
            self.logger.error(u'Unable to get volume: no key "%s" in results: %s' % (key, results))
            return None
        sub_results = self.find_in_string(results[control][key], pattern, re.UNICODE)
        self.logger.debug(u'sub_results=%s' % sub_results)
        if len(sub_results)!=1 or len(sub_results[0])!=2 or len(sub_results[0][1])!=1:
            self.logger.error(u'Unable to get volume: pattern "%s" seems no valid for string "%s"' % (pattern, results[control][key]))

        #cast value to int
        volume = None
        try:
            volume = sub_results[0][1][0]
            volume = int(volume)
        except:
            self.logger.exception(u'Unable to get volume for string "%s"' % sub_results[0][1][0])

        return volume

    def get_volumes(self):
        """
        Return current volume on default playback device

        Return:
            dict: volumes percentages::
                {
                    playback (int or None),
                    capture (int or None)
                }
        """
        #get current profile
        profile = self.__get_current_audio_profile()
        if profile is None:
            raise CommandError(u'Configured sound device is not supported')

        #get volume values
        playback_volume = self.__get_or_set_volume(profile, self.__KEY_PLAYBACK)
        capture_volume = self.__get_or_set_volume(profile, self.__KEY_CAPTURE)
        self.logger.debug('Volumes: playback=%s capture=%s' % (playback_volume, capture_volume))

        return {
            u'playback': playback_volume,
            u'capture': capture_volume,
        }

    def set_volumes(self, playback=None, capture=None):
        """
        Set volumes (individualy or both volumes at the same time)

        Args:
            playback (int): playback volume to set (if None volume is not updated)
            capture (int): capture volume to set (if None volume is not updated)

        Return:
            dict: new volumes percentages::
                {
                    playback (int or None),
                    capture (int or None)
                }
        """
        #check parameters
        if playback is not None and (playback<0 or playback>100):
            raise InvalidParameter(u'Playback volume value must be 0..100')
        if capture is not None and (capture<0 or capture>100):
            raise InvalidParameter(u'Cpature volume value must be 0..100')

        #get current profile
        profile = self.__get_current_audio_profile()
        if profile is None:
            raise CommandError(u'Configured sound device is not supported')

        #set volume values
        playback_volume = None
        capture_volume = None
        if playback is not None:
            playback_volume = self.__get_or_set_volume(profile, self.__KEY_PLAYBACK, playback)
        if capture is not None:
            capture_volume = self.__get_or_set_volume(profile, self.__KEY_CAPTURE, capture)

        return {
            u'playback': playback_volume,
            u'capture': capture_volume,
        }

    def play_sound(self, path):
        """
        Play specified sound using aplay command

        Args:
            path (string): sound file path
        """
        #check params
        if not os.path.exists(path):
            raise InvalidParameter(u'Sound file doesn\'t exist (%s)' % path)

        #play sound
        res = self.command(u'/usr/bin/aplay "%s"' % path)
        if res[u'killed']:
            self.logger.error(u'Unable to play sound file "%s": %s' % (path, res))
            return False
        elif res[u'error'] and len(res[u'stderr'])>0 and not res[u'stderr'][0].startswith(u'Playing WAVE'):
            #for some strange reasons, aplay output is on stderr
            self.logger.error(u'Unable to play sound file "%s": %s' % (path, res))
            return False
        
        return True


