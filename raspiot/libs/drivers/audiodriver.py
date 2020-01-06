#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
from raspiot.libs.drivers.driver import Driver
from raspiot.libs.configs.cleepaudio import CleepAudio
from raspiot.libs.commands.alsa import Alsa

class AudioDriver(Driver):
    """
    Audio driver base class

    As mentionned in Driver base class, we implements following methods:
     - _install
     - _uninstall
     - is_installed
    """

    def __init__(self, cleep_filesystem, driver_name, card_name):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
            driver_name (string): driver name
            card_name (string): audio card name (as found by alsa) 
        """
        Driver.__init__(self, cleep_filesystem, Driver.DRIVER_AUDIO, driver_name)
        self.card_name = card_name
        self._cleep_audio = CleepAudio(self.cleep_filesystem)
        self.alsa = Alsa(cleep_filesystem)

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
        card_name = self._get_card_name()
        alsa_infos = self._get_alsa_infos()
        self.logger.debug(u'alsa infos=%s' % alsa_infos)
        card_infos = {
            u'cardid': None,
            u'deviceid': None
        }
        if alsa_infos and u'devices' in alsa_infos and len(alsa_infos[u'devices'])>0:
            card_infos[u'cardid'] = alsa_infos[u'devices'][0][u'cardid']
            card_infos[u'deviceid'] = alsa_infos[u'devices'][0][u'deviceid']
        capabilities = self._get_card_capabilities()
        return {
            u'cardname': card_name,
            u'cardid': card_infos[u'cardid'],
            u'deviceid': card_infos[u'deviceid'],
            u'playback': capabilities[0],
            u'capture': capabilities[1],
        }

    def _is_card_enabled(self, card_name=None):
        """ 
        Is specified card enabled ?

        Args:
            card_name (string): card name to check. If None specified, driver card name is used

        Returns:
            bool: True if enable
        """
        selected_device = self.alsa.get_selected_device()
        self.logger.trace(u'Selected device: %s' % selected_device)

        if card_name is None:
            card_name = self._get_card_name()
        self.logger.trace(u'Card name=%s' % card_name)

        if selected_device and selected_device[u'name']==card_name:
            return True
                
        return False

    def _get_cardid_deviceid(self):
        """
        Returns only cardid/deviceid for current card

        Returns:
            tuple: cardid/deviceid::

                (
                    cardid (int): card id or None if not found
                    deviceid (int): device id or None if not found
                )

        """
        infos = self._get_alsa_infos()
        if infos and u'devices' in infos and len(infos[u'devices'])>0:
            return (infos[u'devices'][0][u'cardid'], infos[u'devices'][0][u'deviceid'])

        return (None, None)

    def _get_alsa_infos(self):
        """
        Return alsa infos for current card

        Returns:
            dict: alsa infos or None if card not found::

                {
                    cardname (string): card name
                    cardid (int): alsa card id
                    deviceid (int): alsa device id
                }

        """
        return self.alsa.get_device_infos(self._get_card_name())

    def _get_card_capabilities(self): # pragma: no cover
        """
        Return card capabilities

        Returns:
            tuple: card capabilities::

                (
                    bool: playback capability,
                    bool: capture capability
                )
        """
        raise NotImplementedError(u'Function "_get_card_capabilities" must be implemented in "%s"' % self.__class__.__name__)

    def _get_card_name(self): # pragma: no cover
        """
        Return card name as returned by alsa

        Returns:
            string: card name
        """
        raise NotImplementedError(u'Function "_get_card_name" must be implemented in "%s"' % self.__class__.__name__)

    def enable(self, params=None): # pragma: no cover
        """ 
        Enable driver

        Args:
            params (dict): additionnal parameters if necessary
        """
        raise NotImplementedError(u'Function "enable" must be implemented in "%s"' % self.__class__.__name__)

    def disable(self, params=None): # pragma: no cover
        """ 
        Disable driver

        Args:
            params (dict): additionnal parameters if necessary
        """
        raise NotImplementedError(u'Function "disable" must be implemented in "%s"' % self.__class__.__name__)

    def get_volumes(self): # pragma: no cover
        """ 
        Get volumes

        Returns:
            dict: volumes level::

                {
                    playback (float): playback volume
                    capture (float): capture volume
                }

        """
        raise NotImplementedError(u'Function "get_volumes" must be implemented in "%s"' % self.__class__.__name__)

    def set_volumes(self, playback=None, capture=None): # pragma: no cover
        """ 
        Set volumes

        Args:
            playback (float): playback volume (None to disable update)
            capture (float): capture volume (None to disable update)
        """
        raise NotImplementedError(u'Function "set_volumes" must be implemented in "%s"' % self.__class__.__name__)

