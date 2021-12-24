#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
from cleep.libs.drivers.driver import Driver
from cleep.libs.configs.cleepaudio import CleepAudio
from cleep.libs.commands.alsa import Alsa

class AudioDriver(Driver):
    """
    Audio driver base class

    As mentionned in Driver base class, we implements following methods:
     - _install
     - _uninstall
     - is_installed
    """

    def __init__(self, driver_name):
        """
        Constructor

        Args:
            driver_name (string): driver name
        """
        Driver.__init__(self, Driver.DRIVER_AUDIO, driver_name)

        self.__card_name = None

    def _on_registered(self):
        """
        Driver registered
        """
        self._cleep_audio = CleepAudio(self.cleep_filesystem)
        self.alsa = Alsa(self.cleep_filesystem)

        self._on_audio_registered()

        self.__card_name = self.__get_card_name()
        self.logger.debug('Found card_name=%s' , self.__card_name)

    def _on_audio_registered(self): # pragma: no cover
        """
        Audio driver registered
        """
        raise NotImplementedError('Function "_on_audio_registered" must be implemented in "%s"' % self.__class__.__name__)

    def __get_card_name(self):
        """
        Request for associated driver card name

        Returns:
            string: driver card name
        """
        devices = self.alsa.get_playback_devices()
        devices_names = []
        for _, card in devices.items():
            data = {
                'card_name': card['name'],
                'card_desc': card['desc'],
                'device_name': None,
                'device_desc': None,
            }
            for _, device in card['devices'].items():
                data['device_name'] = device['name']
                data['device_desc'] = device['desc']
                devices_names.append(data)

        return self._get_card_name(devices_names)

    def _get_card_name(self, devices_names): # pragma: no cover
        """
        Get card name to be able to identify the card associated to the driver.
        You must return a string found in one of devices_names strings.

        Args:
            devices_names (list): list of devices names installed on device::

                [
                    {
                        card_name (string): card name
                        card_desc (string): card description
                        device_name (string): device name
                        device_desc (string): device description
                    },
                    ...
                ]

        Returns:
            string: card name used to identify the card associated to the driver

        """
        raise NotImplementedError('Function "_get_card_name" must be implemented in "%s"' % self.__class__.__name__)

    def get_card_name(self):
        """
        Return card name

        Returns:
            string: card name
        """
        return self.__card_name

    def get_device_infos(self):
        """
        Returns infos about device associated to driver

        Returns:
            dict: device infos::

                {
                    cardname (string): handled card name
                    cardid (int): card id
                    deviceid (int): device id
                    playback (bool): True if audio playback is possible
                    capture (bool): True if audio capture is possible
                }

        """
        if not self.__card_name:
            raise Exception('No hardware found for driver "%s"' % self.__class__.__name__)

        alsa_infos = self.get_alsa_infos()
        self.logger.debug('alsa_infos=%s' % alsa_infos)
        card_infos = {
            'cardid': None,
            'deviceid': None
        }
        if alsa_infos and 'devices' in alsa_infos and len(alsa_infos['devices'])>0:
            card_infos['cardid'] = alsa_infos['devices'][0]['cardid']
            card_infos['deviceid'] = alsa_infos['devices'][0]['deviceid']
        capabilities = self.get_card_capabilities()

        return {
            'cardname': self.__card_name,
            'cardid': card_infos['cardid'],
            'deviceid': card_infos['deviceid'],
            'playback': capabilities[0],
            'capture': capabilities[1],
        }

    def is_card_enabled(self):
        """ 
        Is specified card enabled ?

        Returns:
            bool: True if enable
        """
        selected_device = self.alsa.get_selected_device()
        self.logger.debug('card name=%s selected device=%s', self.__card_name, selected_device)

        is_enabled = selected_device and selected_device['name'] == self.__card_name

        if is_enabled:
            self._set_volumes_controls()

        return is_enabled

    def get_cardid_deviceid(self):
        """
        Returns only cardid/deviceid for current card

        Returns:
            tuple: cardid/deviceid::

                (
                    cardid (int): card id or None if not found
                    deviceid (int): device id or None if not found
                )

        """
        infos = self.get_alsa_infos()
        self.logger.debug('alsa infos: %s', infos)
        return (infos['devices'][0]['cardid'], infos['devices'][0]['deviceid']) if infos else (None, None)

    def get_alsa_infos(self):
        """
        Return alsa infos for current card

        Returns:
            dict: alsa infos or None if card not found::

                {
                    name (string): card name
                    desc (string): card description
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
        return self.alsa.get_device_infos(self.__card_name)

    def get_control_numid(self, control_name):
        """
        Return numid for specified control name. Control name has not to be exact but contains the specified string
        to match result. Search is not case sensitive.

        Args:
            control_name (string): control name to search for

        Returns:
            int: control numid or None if control not found
        """
        found_controls = [control['numid'] for control in self.alsa.get_controls() if control['name'].lower().find(control_name.lower()) >= 0]
        self.logger.debug('Found controls: %s', found_controls)

        return found_controls[0] if len(found_controls) > 0 else None

    def get_card_capabilities(self): # pragma: no cover
        """
        Return card capabilities

        Warning:
            This function must be implemented in audio driver

        Returns:
            tuple: card capabilities::

                (
                    bool: playback capability,
                    bool: capture capability
                )
        """
        raise NotImplementedError('Function "get_card_capabilities" must be implemented in "%s"' % self.__class__.__name__)

    def enable(self, params=None): # pragma: no cover
        """ 
        Enable driver

        Warning:
            This function must be implemented in audio driver

        Args:
            params (dict): additionnal parameters if necessary
        """
        raise NotImplementedError('Function "enable" must be implemented in "%s"' % self.__class__.__name__)

    def disable(self, params=None): # pragma: no cover
        """ 
        Disable driver

        Warning:
            This function must be implemented in audio driver

        Args:
            params (dict): additionnal parameters if necessary
        """
        raise NotImplementedError('Function "disable" must be implemented in "%s"' % self.__class__.__name__)

    def _set_volumes_controls(self): # pragma: no cover
        """
        Set controls to configure volumes

        Warning:
            This function must be implemented in audio driver
        """
        raise NotImplementedError('Function "_set_volumes_controls" must be implemented in "%s"' % self.__class__.__name__)

    def get_volumes(self): # pragma: no cover
        """ 
        Get volumes

        Warning:
            This function must be implemented in audio driver

        Returns:
            dict: volumes level::

                {
                    playback (float): playback volume
                    capture (float): capture volume
                }

        """
        raise NotImplementedError('Function "get_volumes" must be implemented in "%s"' % self.__class__.__name__)

    def set_volumes(self, playback=None, capture=None): # pragma: no cover
        """ 
        Set volumes

        Warning:
            This function must be implemented in audio driver

        Args:
            playback (float): playback volume (None to disable update)
            capture (float): capture volume (None to disable update)
        """
        raise NotImplementedError('Function "set_volumes" must be implemented in "%s"' % self.__class__.__name__)

