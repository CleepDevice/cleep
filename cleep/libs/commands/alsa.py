#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import os
import uuid
from cleep.libs.internals.console import AdvancedConsole
from cleep.exception import CommandError, MissingParameter, InvalidParameter

class Alsa(AdvancedConsole):
    """
    Alsa commands helper (aplay, arecord, amixer).
    """

    FORMAT_S16LE = 'S16_LE'
    FORMAT_S24LE = 'S24_LE'
    FORMAT_S32LE = 'S32_LE'

    CHANNELS_MONO = 1
    CHANNELS_STEREO = 2
    CHANNELS_DOLBY = 5

    RATE_22K = 22050
    RATE_44K = 44100
    RATE_48K = 48000

    SIMPLE_MIXER_CONTROL = 'Simple mixer control'

    CGET = 'cget'
    CSET = 'cset'

    def __init__(self, cleep_filesystem):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): cleep filesystem instance
        """
        AdvancedConsole.__init__(self)

        # members
        self.logger = logging.getLogger(self.__class__.__name__)
        # self.logger.setLevel(logging.DEBUG)
        self.cleep_filesystem = cleep_filesystem

    def __devices_command(self, command):
        """
        Execute specified command for devices and return parsed results

        Args:
            command (string): command to execute

        Returns:
            dict: dict of outputs::

                {
                    card id (int): {
                        name (string): card name
                        desc (string): card description
                        devices (dict): {
                            deviceid (int): {
                                name (string): device name
                                desc (string): device description
                                cardid (int): card id
                                deviceid (int): device id
                            },
                            ...
                        }
                    },
                    ...
                }

        """
        results = self.find(command, r'^(?:card (\d)): (.*) \[(.*)\].*(?:device (\d)): (.*).\[(.*)\].*$')
        entries = {}
        for _, groups in results:
            self.logger.trace('groups (%d): %s' % (len(groups), groups))

            if len(groups) != 6: # pragma: no cover
                continue

            # card id
            card_id = 0
            try:
                card_id = int(groups[0])
            except Exception: # pragma: no cover
                self.logger.exception('Invalid card id:')

            # device id
            device_id = 0
            try:
                device_id = int(groups[3])
            except Exception: # pragma: no cover
                self.logger.exception('Invalid device id:')

            # names (prefer using 2nd name in [] if not empty)
            card_name = groups[1].strip()
            card_desc = groups[2].strip()
            device_name = groups[4].strip() if len(groups[4].strip()) > 0 else card_name
            device_desc = groups[5].strip() if len(groups[5].strip()) > 0 else card_name

            # store entry
            if card_id not in entries:
                entries[card_id] = {
                    'name': card_name,
                    'desc': card_desc,
                    'devices': {}
                }
            entries[card_id]['devices'][device_id] = {
                'deviceid': device_id,
                'cardid': card_id,
                'name': device_name,
                'desc': device_desc,
            }

        return entries

    def get_selected_device(self):
        """
        Return selected device info

        Returns:
            dict: selected device info or None if nothing found::

                {
                    name (string): device name (first device name)
                    devices (list): list of devices
                        [
                            {
                                cardid (string): card id
                                deviceid (string): device id
                                name (string): device name
                                desc (string): device description
                            },
                            ...
                        ]
                }

        """
        # get selected device name
        cmd = '/usr/bin/amixer info | grep "Card default"'
        resp = self.command(cmd)
        if resp['error'] or resp['killed']:
            return None # pragma: no cover
        try:
            stdout = resp['stdout'][0].replace('Card default ', '')
            parts = stdout.split('/')
            self.logger.debug('amixer info output and splits: %s - %s', resp['stdout'], parts)
            return self.get_device_infos(parts[0].replace('\'', ''), parts[1].replace('\'', ''))

        except Exception: # pragma: no cover
            self.logger.exception('Error parsing amixer command result:')

        return None

    def get_device_infos(self, device_name, device_desc=None):
        """
        Get device infos

        Args:
            device_name (string): device name to retrieve infos from
            device_desc (string): device description. If specified use device description to find a match

        Returns:
            dict: selected device info or None if nothing found::

                {
                    name (string): device name (first device name)
                    devices (list): list of devices
                        [
                            {
                                cardid (string): card id
                                deviceid (string): device id
                                name (string): device name
                                desc (string): device description
                            },
                            ...
                        ]
                }

        """
        if not device_name:
            self.logger.warning('No device name specified, unable to get device infos')
            return None

        playback_devices = self.get_playback_devices()
        name_pattern = re.compile(device_name, re.IGNORECASE)
        desc_pattern = re.compile(device_desc, re.IGNORECASE) if device_desc else None

        for _, card in playback_devices.items():
            if name_pattern.match(card['name']):
                return card
            if desc_pattern and desc_pattern.match(card['desc']):
                return card
            for _, device in card['devices'].items():
                if name_pattern.match(device['name']):
                    return card
                if desc_pattern and desc_pattern.match(device['desc']):
                    return card

        return None

    def get_simple_controls(self):
        """
        Get device controls (simple controls)

        Returns:
            list: list of controls
        """
        results = self.find('/usr/bin/amixer scontrols', r"^.*'(.*)',\d+$")
        controls = []
        for _, groups in results:
            self.logger.trace('groups (%d): %s' % (len(groups), groups))
            controls.append(groups[0])

        return controls

    def get_controls(self):
        """
        Get device controls

        Returns:
            list: list of controls for current card::

                [
                    {
                        numid (int): control identifier
                        iface (string): control iface
                        name (string): control name
                    },
                    ...
                ]

        """
        results = self.find('/usr/bin/amixer controls', r"^numid=(\d+),iface=(.*?),name='(.*)'$")
        controls = []
        for _, groups in results:
            self.logger.trace('groups (%d): %s' % (len(groups), groups))
            if len(groups) != 3: # pragma: no cover
                continue
            controls.append({
                'numid': int(groups[0]),
                'iface': groups[1],
                'name': groups[2],
            })

        return controls

    def get_playback_devices(self):
        """
        Return list of playback devices

        Returns:
            dict: dict of outputs::

                {
                    card id (int): {
                        name (string): card name
                        desc (string): card description
                        devices (dict): {
                            deviceid (int): {
                                name (string): device name
                                desc (string): device description
                                cardid (int): card id
                                deviceid (int): device id
                            },
                            ...
                        }
                    },
                    ...
                }

        """
        return self.__devices_command('/usr/bin/aplay --list-devices')

    def get_capture_devices(self):
        """
        Return list of capture devices

        Returns:
            dict: dict of outputs::

                {
                    card id (int): {
                        name (string): card name
                        desc (string): card description
                        devices (dict): {
                            deviceid (int): {
                                name (string): device name
                                desc (string): device description
                                cardid (int): card id
                                deviceid (int): device id
                            },
                            ...
                        }
                    },
                    ...
                }

        """
        return self.__devices_command('/usr/bin/arecord --list-devices')

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
        for _, groups in results:
            # filter None values
            groups = list(filter(None, groups))
            self.logger.trace('groups (%d): %s' % (len(groups), groups))

            if groups[0].startswith(self.SIMPLE_MIXER_CONTROL):
                # new section found
                current_control = groups[1].strip()
                entries[current_control] = {}
            elif current_control is not None and len(groups) == 2:
                # append property to current section
                entries[current_control][groups[0]] = groups[1].strip()

        return entries

    def __amixer_control_command(self, command):
        """
        Execute amixer control command and return formatted outputs

        Args:
            command (string): amixer command. No check is performed to make sure it is a amixer command

        Returns:
            dict: amixer output command::

                {
                    iface (string),
                    name (string),
                    min (string),
                    max (string),
                    step (string),
                    values (string)
                }

        """
        self.logger.debug('Amixer control command: %s' % command)
        results = self.find(
            command,
            r'(?:(iface)=(.*),)|(?:(name)=\'(.*)\')|(?:(min)=(\d))|(?:(max)=(\d))|(?:(step)=(\d))|(?:: (values)=(.*))'
        )

        values = {}
        for _, groups in results:
            # filter None values
            groups = list(filter(None, groups))
            self.logger.trace('groups (%d): %s' % (len(groups), groups))

            values[groups[0]] = groups[1]

        return values

    def amixer_control(self, command, numid, value=None):
        """
        Execute amixer control

        Args:
            command (string): Alsa.CGET or Alsa.CSET
            numid (int): amixer numid. Use command "amixer controls" to get available numids
            value (string): value to use with CSET

        Raises:
            InvalidParameter: if parameter is invalid
            MissingParameter: if parameter is missing
        """
        # check parameters
        if command is None:
            raise MissingParameter('Parameter "command" is missing')
        if command not in (Alsa.CSET, Alsa.CGET):
            raise InvalidParameter('Parameter "command" must be Alsa.CGET or Alsa.CSET (specified="%s")' % command)
        if not isinstance(numid, int):
            raise InvalidParameter('Parameter "numid" must be a string')
        if command == self.CSET and value is None:
            raise MissingParameter('Parameter "value" is missing')
        if command == self.CSET and not isinstance(value, int) and not isinstance(value, str):
            raise InvalidParameter('Parameter "value" is invalid. Int or str awaited')

        cmd = '/usr/bin/amixer %s numid=%s %s' % (command, numid, value if value is not None else '')
        self.logger.trace('amixer command: "%s"' % cmd)

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
        # check parameters
        if control is None or len(control) == 0:
            raise MissingParameter('Parameter "control" is missing')
        if pattern is None or len(pattern) == 0:
            raise MissingParameter('Parameter "pattern" is missing')

        # execute command
        if volume is None:
            results = self.__amixer_command('/usr/bin/amixer get "%s"' % control)
        else:
            results = self.__amixer_command('/usr/bin/amixer set "%s" %s%%' % (control, volume))
        self.logger.trace('Amixer command results: %s' % results)
        if len(results) == 0 or control not in results.keys():
            self.logger.warning('Unable to get volume: no control "%s" found in results, maybe device is not the default card' % control)
            return None

        # parse result to get volume value
        sub_results = self.find_in_string(results[control][pattern[0]], pattern[1], re.UNICODE)
        self.logger.trace('sub_results=%s' % sub_results)
        if len(sub_results) != 1 or len(sub_results[0]) != 2 or len(sub_results[0][1]) != 1:
            self.logger.error('Unable to get volume: pattern "%s" seems no valid for string "%s"' % (pattern[1], results[control][pattern[0]])) # pragma: no cover

        # cast value to int
        volume = None
        try:
            volume = sub_results[0][1][0]
            volume = int(volume)
        except Exception: # pragma: no cover
            self.logger.exception('Unable to get volume for string "%s"' % sub_results[0][1][0])

        return volume

    def get_volume(self, control, pattern):
        """
        Return current playback volume on current device

        Args:
            control (string): amixer control that contains volume level. To get list of controls execute "amixer scontrols"
            pattern (string): pattern to use to parse volume level

        Returns:
            float: volume or None if not found

        Raises:
            MissingParameter: if parameter is missing
        """
        # all parameters checked in __get_or_set_volume
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
        # check parameters
        # other parameters checked in __get_or_set_volume
        if volume is None:
            raise MissingParameter('Parameter "volume" is missing')
        if volume < 0.0 or volume > 100.0:
            raise InvalidParameter('Parameter "volume" must be 0...100')

        # set volume values
        volume = self.__get_or_set_volume(control, pattern, volume)
        self.logger.debug('New volume: %s' % volume)

        return volume

    def play_sound(self, path, timeout=5.0):
        """
        Play specified sound using aplay command. Please take care of setting timeout accordingly to your duration!

        Args:
            path (string): sound file path
            timeout (float): max playing duration. If you want to play longer sound file, increase the timeout

        Returns:
            bool: True if command succeed

        Raises:
            InvalidParameter: if parameter is invalid
            MissingParameter
        """
        # check params
        if path is None or len(path) == 0:
            raise MissingParameter('Parameter "path" is missing')
        if not os.path.exists(path):
            raise InvalidParameter('Sound file doesn\'t exist (%s)' % path)

        # play sound
        cmd = '/usr/bin/aplay "%s"' % path
        resp = self.command(cmd, timeout=timeout)
        self.logger.debug('Command "%s" resp: %s"' % (cmd, resp))
        if self.get_last_return_code() != 0: # pragma: no cover
            self.logger.error('Unable to play sound file "%s": %s' % (path, resp['error']))
            return False

        return True

    def record_sound(self, channels=2, rate=44100, format='S32_LE', timeout=5.0):
        """
        Record sound. In charge of function caller to remove properly generated file
        After timeout command is killed so use timeout to record specific duration.

        Args:
            channels (int): number of channels to record. Default CHANNELS_STEREO.
            rate (int): record rate. Default RATE_44K.
            format (string): RECORD_FORMAT_XXX. Default FORMAT_S32LE.
            timeout (float): max recording duration

        Returns:
            string: path of recording file (wav format)

        Raises:
            MissingParameter: if parameter is missing
            InvalidParameter: if parameter is invalid
            CommandError: if error occured during command execution
        """
        # check params
        if channels is None:
            raise MissingParameter('Parameter "channels" is missing')
        if channels not in (self.CHANNELS_MONO, self.CHANNELS_STEREO, self.CHANNELS_DOLBY):
            raise InvalidParameter('Parameter "channels" is invalid. Please check supported value.')
        if rate is None:
            raise MissingParameter('Parameter "rate" is missing')
        if rate not in (self.RATE_22K, self.RATE_44K, self.RATE_48K):
            raise InvalidParameter('Parameter "rate" is invalid. Please check supported value.')
        if format is None:
            raise MissingParameter('Parameter "format" is missing')
        if format not in (self.FORMAT_S16LE, self.FORMAT_S24LE, self.FORMAT_S32LE):
            raise InvalidParameter('Parameter "format" is invalid. Please check supported value.')

        # record sound
        record_path = '%s.wav' % os.path.join('/tmp', str(uuid.uuid4()))
        cmd = '/usr/bin/arecord -f %s -c%d -r%d "%s"' % (format, channels, rate, record_path)
        resp = self.command(cmd, timeout=timeout)
        self.logger.debug('Command "%s" resp: %s' % (cmd, resp))

        if self.get_last_return_code() != 0:
            raise CommandError('Unable to record audio')

        return record_path # pragma: no cover

    def save(self):
        """
        Save alsa configuration in /var/lib/alsa/asound.state

        Returns:
            bool: True if configuration saved successfully, False otherwise
        """
        self.cleep_filesystem.enable_write()

        try:
            cmd = '/usr/sbin/alsactl store'
            resp = self.command(cmd)
            self.logger.debug('Command "%s" resp: %s' % (cmd, resp))
            return True if self.get_last_return_code() == 0 else False

        except Exception: # pragma: no cover
            self.logger.exception('Error occured during alsa config saving:')
            return False

        finally:
            self.cleep_filesystem.disable_write()

