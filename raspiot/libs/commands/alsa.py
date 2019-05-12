#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.internals.console import AdvancedConsole
from raspiot.utils import CommandError, MissingParameter, InvalidParameter
import logging
import re
import os
import uuid

class Alsa(AdvancedConsole):
    """
    Alsa commands helper (aplay, arecord, amixer).
    """
    
    FORMAT_S16LE = u'S16_LE'
    FORMAT_S24LE = u'S24_LE'
    FORMAT_S32LE = u'S32_LE'

    CHANNELS_MONO = 1
    CHANNELS_STEREO = 2
    CHANNELS_DOLBY = 5

    RATE_22K = 22050
    RATE_44K = 44100
    RATE_48K = 48000

    SIMPLE_MIXER_CONTROL = u'Simple mixer control'

    CGET = u'cget'
    CSET = u'cset'

    def __init__(self):
        """
        Constructor
        """
        AdvancedConsole.__init__(self)

        #members
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)

    def __command(self, command):
        """
        Execute specified command and return parsed results

        Args:
            command (string): command to execute

        Returns:
            dict: dict of outputs::

                {
                    card id (int): {
                        name (string): card name
                        devices (dict): {
                            deviceid (int): {
                                name (string): device name
                                cardid (int): card id
                                deviceid (int): device id
                            },
                            ...
                        }
                    },
                    ...
                }

        """
        results = self.find(command, r'^(?:card (\d)):.*\[(.*)\].*(?:device (\d)).*\[(.*)\].*$')
        entries = {}
        for group, groups in results:
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
                if card_id not in entries:
                    entries[card_id] = {
                        u'name': name,
                        u'devices': {}
                    }
                entries[card_id][u'devices'][device_id] = {
                    u'deviceid': device_id,
                    u'cardid': card_id,
                    u'name': name
                }

        return entries

    def get_selected_device(self):
        """
        Return selected device info

        Returns:
            dict: selected device info or None if nothing found::

                {
                    cardname (string): caard name
                    cardid (int): card id
                    deviceid (int): device id
                }

        """
        #get selected device name
        cmd = u'amixer info | grep "Card default"'
        resp = self.command(cmd)
        if resp[u'error'] or resp[u'killed']:
            return None
        try:
            selected_device_name = resp[u'stdout'][0].split('/')[1].replace('\'','')
        except:
            self.logger.exception(u'Error parsing amixer command result:')
            selected_device_name = None

        #get selected device info
        for _, device in self.get_playback_devices().items():
            if device[u'name']==selected_device_name:
                return device

        return None

    def get_playback_devices(self):
        """
        Return list of playback devices

        Returns:
            dict: dict of outputs::
                {
                    cardname: {
                        cardname (string),
                        cardid (int),
                        deviceid (id)
                    }
                }
        """
        return self.__command(u'/usr/bin/aplay --list-devices')

    def get_capture_devices(self):
        """
        Return list of capture devices

        Returns:
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

        Returns:
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

    def __amixer_control_command(self, command):
        """
        Execute amixer control command and return formatted outputs

        Args:
            command (string): amixer command. No check is performed to make sure it is a amixer command

        Returns:
            dict:
        """
        self.logger.debug('Amixer control command: %s' % command)
        results = self.find(command, r'(?:(iface)=(.*),)|(?:(name)=\'(.*)\')|(?:(min)=(\d))|(?:(max)=(\d))|(?:(step)=(\d))|(?:: (values)=(.*))')

        values = {}
        for group, groups in results:
            #filter None values
            groups = filter(None, groups)
            self.logger.debug(groups)

            values[groups[0]] = groups[1]

        return values

    def amixer_control(self, command, numid, value=None):
        """
        Execute amixer control

        Args:
            command (string): Alsa.CGET or Alsa.CSET
            numid (int): amixer numid
            value (string): value to use with CSET

        Raises:
            InvalidParameter: if parameter is invalid
            MissingParameter: if parameter is missing
        """
        #check parameters
        if command is None:
            raise MissingParameter(u'Parameter "command" is missing')
        if command not in (self.CSET, self.CGET):
            raise InvalidParameter(u'Parameter "command" must be Alsa.CGET or Alsa.CSET')
        if not isinstance(numid, int):
            raise InvalidParameter(u'Parameter "numid" must be a string')
        if command==self.CSET and (value is None or not isinstance(value, str) or len(value)==0):
            raise MissingParameter(u'Parameter "value" is missing')

        cmd = u'/usr/bin/amixer %s numid=%s %s' % (command, numid, value if value is not None else '')
        self.logger.debug(u'amixer command: "%s"' % cmd)

        return self.__amixer_control_command(cmd)

    def __get_or_set_volume(self, control, pattern, volume=None):
        """
        Get infos from amixer command, parse results and get volume value
        With volume specified set command is executed, otherwise it is get command

        Args:
            control (string): amixer control to find
            pattern (string): pattern to use to extract float value from amixer result
            volume (int): volume percentage or None

        Returns:
            int: volume value or None if error occured
        """
        #check parameters
        if control is None or len(control)==0:
            raise MissingParameter(u'Parameter "control" is missing')
        if pattern is None or len(pattern)==0:
            raise MissingParameter(u'Parameter "pattern" is missing')

        #execute command
        if volume is None:
            results = self.__amixer_command(u'/usr/bin/amixer get "%s"' % control)
        else:
            results = self.__amixer_command(u'/usr/bin/amixer set "%s" %s%%' % (control, volume))
        self.logger.debug('Amixer command results: %s' % results)
        if len(results)==0 or control not in results.keys():
            self.logger.warning(u'Unable to get volume: no control "%s" found in results, maybe device does not support it' % control)
            return None

        #parse result to get volume value
        sub_results = self.find_in_string(results[control][pattern[0]], pattern[1], re.UNICODE)
        self.logger.debug(u'sub_results=%s' % sub_results)
        if len(sub_results)!=1 or len(sub_results[0])!=2 or len(sub_results[0][1])!=1:
            self.logger.error(u'Unable to get volume: pattern "%s" seems no valid for string "%s"' % (pattern[1], results[control][pattern[0]]))

        #cast value to int
        volume = None
        try:
            volume = sub_results[0][1][0]
            volume = int(volume)
        except:
            self.logger.exception(u'Unable to get volume for string "%s"' % sub_results[0][1][0])

        return volume

    def get_volume(self, control, pattern):
        """
        Return current playback volume on current device

        Args:
            control (string): amixer control that contains volume level
            pattern (string): pattern to use to parse volume level

        Returns:
            float: volume or None if not found

        Raises:
            MissingParameter: if parameter is missing
        """
        #check parameters done in __get_or_set_volume

        volume = self.__get_or_set_volume(control, pattern)
        self.logger.debug('Volume: %s' % volume)

        return volume

    def set_volume(self, control, pattern, volume):
        """
        Set volume

        Args:
            control (string): amixer control that contains volume level
            pattern (string): pattern to use to parse volume level
            volume (float): volume level to set (in percentage)

        Returns:
            float: new volume or None if failed

        Raises:
            InvalidParameter: if parameter is invalid
            MissingParameter: if parameter is missing
        """
        #check parameters
        if volume is None:
            raise MissingParameter(u'Parameter "volume" is missing')
        if volume<0.0 or volume>100.0:
            raise InvalidParameter(u'Parameter "volume" must be 0...100')

        #set volume values
        volume = self.__get_or_set_volume(control, pattern, volume)
        self.logger.debug(u'New volume: %s' % volume)

        return volume

    def play_sound(self, path, timeout=5.0):
        """
        Play specified sound using aplay command

        Args:
            path (string): sound file path
            timeout (float): max playing duration. If you want to play longer sound file, increase the timeout

        Returns:
            bool: True if command succeed

        Raises:
            InvalidParameter: if parameter is invalid
        """
        #check params
        if not os.path.exists(path):
            raise InvalidParameter(u'Sound file doesn\'t exist (%s)' % path)

        #play sound
        res = self.command(u'/usr/bin/aplay "%s"' % path, timeout=timeout)
        if res[u'error'] and len(res[u'stderr'])>0 and not res[u'stderr'][0].startswith(u'Playing WAVE'):
            #for some strange reasons, aplay output is on stderr
            self.logger.error(u'Unable to play sound file "%s": %s' % (path, res))
            return False
        
        return True

    def record_sound(self, channels=2, rate=44100, format=u'S32_LE', timeout=5.0):
        """
        Record sound

        Args:
            format (string): RECORD_FORMAT_XXX (default S32_LE)
            channels (int): number of channels to record (default 2 for stereo)
            timeout (float): max recording duration

        Returns:
            string: path of recording file (wav format)

        Raises:
            MissingParameter: if parameter is missing
            InvalidParameter: if parameter is invalid
            CommandError: if error occured during command execution
        """
        #check params
        if format is None:
            raise MissingParameter(u'Parameter format is missing')
        if format not in (self.FORMAT_S16LE, self.FORMAT_S24LE, self.FORMAT_S32LE):
            raise InvalidParameter(u'Parameter format is invalid. Please check supported value.')
        if channels is None:
            raise MissingParameter(u'Parameter channels is missing')
        if channels not in (self.CHANNELS_MONO, self.CHANNELS_STEREO, self.CHANNELS_DOLBY):
            raise InvalidParameter(u'Parameter channels is invalid. Please check supported value.')
        if rate is None:
            raise MissingParameter(u'Parameter rate is missing')
        if rate not in (self.RATE_22K, self.RATE_44K, self.RATE_48K):
            raise InvalidParameter(u'Parameter rate is invalid. Please check supported value.')

        #record sound
        out = u'%s.wav' % os.path.join('/tmp', str(uuid.uuid4()))
        cmd = u'/usr/bin/arecord -f %s -c%d -r%d "%s"' % (format, channels, rate, out)
        self.logger.debug(u'Command: %s' % cmd)
        res = self.command(cmd, timeout=timeout)
        
        #check errors
        if res[u'error']:
            self.logger.error(u'Error occured during recording %s: %s' % (cmd, res))
            raise CommandError(u'Error during recording')

        return out


