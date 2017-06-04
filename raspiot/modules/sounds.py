#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import shutil
import logging
from raspiot.utils import InvalidParameter
from raspiot.raspiot import RaspIotRenderer
from raspiot.libs.profiles import TextToSpeechProfile
import pygame
from threading import Thread
from gtts import gTTS
import time

__all__ = [u'Sounds']

class PlaySound(Thread):
    """
    Play sound thread
    """

    def __init__(self, filepath, delete=False):
        """
        Constructor
        
        Params:
            filepath (string): sound filepath
            filedesc (file): file descriptor. Closed at end of playback
        """
        #init
        Thread.__init__(self)
        Thread.daemon = True
        self.logger = logging.getLogger(self.__class__.__name__)

        #members
        self.filepath = filepath
        self.delete = delete
        self.__continu = True

    def stop(self):
        """
        Stop current playing sound
        """
        self.__continu = False

    def run(self):
        """
        Play sound process
        """
        try:
            #init player
            self.logger.debug(u'init player')
            pygame.mixer.init()
            pygame.mixer.music.load(self.filepath)

            #play sound
            self.logger.debug(u'play sound file "%s"' % self.filepath)
            pygame.mixer.music.play()

            #wait until end of playback or if user stop thread
            while pygame.mixer.music.get_busy()==True:
                if not self.__continu:
                    #stop requested
                    pygame.mixer.music.stop()
                    break
                time.sleep(.1)
            pygame.quit()

            #delete file
            if self.delete:
                self.logger.debug(u'PlaySound: delete sound file "%s"' % self.filepath)
                os.remove(self.filepath)
        except:
            self.logger.exception(u'Exception during sound playing:')




class Sounds(RaspIotRenderer):

    MODULE_CONFIG_FILE = u'sounds.conf'
    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Plays sounds or speech text you want'
    MODULE_LOCKED = False
    MODULE_URL = None
    MODULE_TAGS = []

    RENDERER_PROFILES = [TextToSpeechProfile()]
    RENDERER_TYPE = u'sound'

    DEFAULT_CONFIG = {
        u'lang': u'en'
    }
    SOUNDS_PATH = u'/var/opt/raspiot/sounds'
    ALLOWED_EXTS = [u'mp3', u'wav', u'ogg']
    TTS_LANGS = {
        u'af' : u'Afrikaans',
        u'sq' : u'Albanian',
        u'ar' : u'Arabic',
        u'hy' : u'Armenian',
        u'bn' : u'Bengali',
        u'ca' : u'Catalan',
        u'zh' : u'Chinese',
        u'zh-cn' : u'Chinese (Mandarin/China)',
        u'zh-tw' : u'Chinese (Mandarin/Taiwan)',
        u'zh-yue' : u'Chinese (Cantonese)',
        u'hr' : u'Croatian',
        u'cs' : u'Czech',
        u'da' : u'Danish',
        u'nl' : u'Dutch',
        u'en' : u'English',
        u'en-au' : u'English (Australia)',
        u'en-uk' : u'English (United Kingdom)',
        u'en-us' : u'English (United States)',
        u'eo' : u'Esperanto',
        u'fi' : u'Finnish',
        u'fr' : u'French',
        u'de' : u'German',
        u'el' : u'Greek',
        u'hi' : u'Hindi',
        u'hu' : u'Hungarian',
        u'is' : u'Icelandic',
        u'id' : u'Indonesian',
        u'it' : u'Italian',
        u'ja' : u'Japanese',
        u'ko' : u'Korean',
        u'la' : u'Latin',
        u'lv' : u'Latvian',
        u'mk' : u'Macedonian',
        u'no' : u'Norwegian',
        u'pl' : u'Polish',
        u'pt' : u'Portuguese',
        u'pt-br' : u'Portuguese (Brazil)',
        u'ro' : u'Romanian',
        u'ru' : u'Russian',
        u'sr' : u'Serbian',
        u'sk' : u'Slovak',
        u'es' : u'Spanish',
        u'es-es' : u'Spanish (Spain)',
        u'es-us' : u'Spanish (United States)',
        u'sw' : u'Swahili',
        u'sv' : u'Swedish',
        u'ta' : u'Tamil',
        u'th' : u'Thai',
        u'tr' : u'Turkish',
        u'vi' : u'Vietnamese',
        u'cy' : u'Welsh'
    }

    def __init__(self, bus, debug_enabled):
        """
        Constructor

        Args:
            bus (MessageBus): MessageBus instance
            debug_enabled (bool): flag to set debug level to logger
        """
        #init
        RaspIotRenderer.__init__(self, bus, debug_enabled)

        #disable urllib info logs
        url_log = logging.getLogger(u'urllib3')
        if url_log:
            url_log.setLevel(logging.WARNING)

        #members
        self.__sound_thread = None

        #make sure sounds path exists
        if not os.path.exists(Sounds.SOUNDS_PATH):
            os.makedirs(Sounds.SOUNDS_PATH)

    def get_module_config(self):
        """
        Get full module configuration
        """
        config = {}
        config[u'langs'] = self.get_langs()
        config[u'volume'] = self.get_volume()
        config[u'sounds'] = self.get_sounds()
        return config

    def get_langs(self):
        """
        Return all langs

        Returns:
            dict: languages infos::
                {
                    langs (dict): list of all langs,
                    lang (string): selected lang
                }
        """
        return {
            u'langs': Sounds.TTS_LANGS,
            u'lang': self._config[u'lang']
        }

    def set_lang(self, lang):
        """
        Set tts lang

        Params:
            lang (string): tts lang (see TTS_LANGS)
        """
        #check params
        if lang not in Sounds.TTS_LANGS.keys():
            raise InvalidParameter(u'Specified lang "%s" is invalid' % lang)

        #save lang
        config = self._get_config()
        config[u'lang'] = lang
        self._save_config(config)

    def get_volume(self):
        """
        Get volume

        Returns:
            int: volume value
        """
        pygame.mixer.init()
        volume = pygame.mixer.music.get_volume()
        pygame.quit()
        return volume*100

    def set_volume(self, volume):
        """
        Set volume

        Params:
            volume (int): volume value
        """
        pygame.mixer.init()
        pygame.mixer.music.set_volume(int(volume/100.0))
        pygame.quit()

    def play_sound(self, filename):
        """
        Play specified file

        Params:
            filename: filename to play

        Raises:
            Exception, InvalidParameter
        """
        #build filepath
        filepath = os.path.join(Sounds.SOUNDS_PATH, filename)

        #check file validity
        if not os.path.exists(filepath):
            #invalid file specified
            raise InvalidParameter(u'Specified file "%s" is invalid' % filename)

        #check if sound is already playing
        if self.__sound_thread!=None and self.__sound_thread.is_alive():
            #sound already is playing, reject action
            raise Exception(u'A sound is already playing')

        #play sound
        self.__sound_thread = PlaySound(filepath)
        self.__sound_thread.start()

    def speak_text(self, text, lang):
        """
        Speak specified message

        Params:
            text (string): text to say
            lang (string): spoken lang

        Raises:
            Exception, InvalidParameter
        """
        #check parameters
        if text is None:
            raise MissingParameter(u'Text parameter is missing')
        if lang is None:
            raise MissingParameter(u'Lang parameter is missing')

        #check if sound is already playing
        if self.__sound_thread!=None and self.__sound_thread.is_alive():
            #sound already is playing, reject action
            raise Exception(u'A sound is already playing')

        #text to speech
        try:
            tts = gTTS(text=text, lang=lang)
            path = u'/tmp/sound_%d.mp3' % int(time.time())
            tts.save(path)
        
            #play sound
            self.__sound_thread = PlaySound(path, True)
            self.__sound_thread.start()
            return True
        except:
            self.logger.exception(u'Exception when TTSing text "%s":' % text)

        return False

    def delete_sound(self, filename):
        """
        Delete sound

        Params:
            filename (string): filename to delete

        Raises:
            InvalidParameter
        """
        #build filepath
        filepath = os.path.join(Sounds.SOUNDS_PATH, filename)
    
        #delete file
        if os.path.exists(filepath):
            os.remove(filepath)
            return True

        raise InvalidParameter(u'Invalid sound file')

    def get_sounds(self):
        """
        Get sounds

        Returns:
            list: list of sounds::
                [
                    {
                        name (string): filename
                    },
                    ...
                ]
        """
        out = []
        for root, dirs, sounds in os.walk(Sounds.SOUNDS_PATH):
            for sound in sounds:
                out.append({
                    u'name': os.path.basename(sound)
                })
        return out

    def add_sound(self, filepath):
        """
        Add new sound

        Params:
            filepath (string): uploaded and local filepath

        Returns:
            bool: True if file uploaded successfully
            
        Raises:
            Exception, InvalidParameter
        """
        #check parameters
        file_ext = os.path.splitext(filepath)
        self.logger.debug(u'Add sound of extension: %s' % file_ext[1])
        if file_ext[1][1:] not in Sounds.ALLOWED_EXTS:
            raise InvalidParameter(u'Invalid sound file uploaded (only %s are supported)' % ','.join(Sounds.ALLOWED_EXTS))

        #move file to valid dir
        if os.path.exists(filepath):
            name = os.path.basename(filepath)
            path = os.path.join(Sounds.SOUNDS_PATH, name)
            self.logger.debug(u'Name=%s path=%s' % (name, path))
            shutil.move(filepath, path)
            self.logger.info(u'File "%s" uploaded successfully' % name)
        else:
            #file doesn't exists
            self.logger.error(u'Sound file "%s" doesn\'t exist' % filepath)
            raise Exception(u'Sound file "%s"  doesn\'t exists' % filepath)

        return True

    def play_random_sound(self):
        """
        Play random sound from list of sounds
        """
        sounds = self.get_sounds()

        if len(sounds)>0:
            num = random.randrange(0, len(sounds), 1)
            self.play_sound(sounds[num])

        return True

    def _render(self, data):
        """
        TextToSpeech specified data

        Args:
            data (any supported profile): data to speech
        """
        self.speak_text(data.text, self._config[u'lang'])

