#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import shutil
import logging
from raspiot.utils import InvalidParameter
from raspiot.raspiot import RaspIotModule
import pygame
from threading import Thread
from gtts import gTTS
import time

__all__ = ['Sounds']

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
            self.logger.debug('init player')
            pygame.mixer.init()
            pygame.mixer.music.load(self.filepath)

            #play sound
            self.logger.debug('play sound file "%s"' % self.filepath)
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
                self.logger.debug('PlaySound: delete sound file "%s"' % self.filepath)
                os.remove(self.filepath)
        except:
            self.logger.exception('Exception during sound playing:')




class Sounds(RaspIotModule):

    MODULE_CONFIG_FILE = 'sounds.conf'
    MODULE_DEPS = []
    MODULE_DESCRIPTION = 'Plays sounds or speech text you want'
    MODULE_LOCKED = False
    MODULE_URL = None
    MODULE_TAGS = []

    DEFAULT_CONFIG = {
        'lang': 'en'
    }
    SOUNDS_PATH = '/var/opt/raspiot/sounds'
    ALLOWED_EXTS = ['mp3', 'wav', 'ogg']
    TTS_LANGS = {
        'af' : 'Afrikaans',
        'sq' : 'Albanian',
        'ar' : 'Arabic',
        'hy' : 'Armenian',
        'bn' : 'Bengali',
        'ca' : 'Catalan',
        'zh' : 'Chinese',
        'zh-cn' : 'Chinese (Mandarin/China)',
        'zh-tw' : 'Chinese (Mandarin/Taiwan)',
        'zh-yue' : 'Chinese (Cantonese)',
        'hr' : 'Croatian',
        'cs' : 'Czech',
        'da' : 'Danish',
        'nl' : 'Dutch',
        'en' : 'English',
        'en-au' : 'English (Australia)',
        'en-uk' : 'English (United Kingdom)',
        'en-us' : 'English (United States)',
        'eo' : 'Esperanto',
        'fi' : 'Finnish',
        'fr' : 'French',
        'de' : 'German',
        'el' : 'Greek',
        'hi' : 'Hindi',
        'hu' : 'Hungarian',
        'is' : 'Icelandic',
        'id' : 'Indonesian',
        'it' : 'Italian',
        'ja' : 'Japanese',
        'ko' : 'Korean',
        'la' : 'Latin',
        'lv' : 'Latvian',
        'mk' : 'Macedonian',
        'no' : 'Norwegian',
        'pl' : 'Polish',
        'pt' : 'Portuguese',
        'pt-br' : 'Portuguese (Brazil)',
        'ro' : 'Romanian',
        'ru' : 'Russian',
        'sr' : 'Serbian',
        'sk' : 'Slovak',
        'es' : 'Spanish',
        'es-es' : 'Spanish (Spain)',
        'es-us' : 'Spanish (United States)',
        'sw' : 'Swahili',
        'sv' : 'Swedish',
        'ta' : 'Tamil',
        'th' : 'Thai',
        'tr' : 'Turkish',
        'vi' : 'Vietnamese',
        'cy' : 'Welsh'
    }

    def __init__(self, bus, debug_enabled):
        """
        Constructor

        Args:
            bus (MessageBus): MessageBus instance
            debug_enabled (bool): flag to set debug level to logger
        """
        #init
        RaspIotModule.__init__(self, bus, debug_enabled)

        #disable urllib info logs
        url_log = logging.getLogger("urllib3")
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
        config['langs'] = self.get_langs()
        config['volume'] = self.get_volume()
        config['sounds'] = self.get_sounds()
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
            'langs': Sounds.TTS_LANGS,
            'lang': self._config['lang']
        }

    def set_lang(self, lang):
        """
        Set tts lang

        Params:
            lang (string): tts lang (see TTS_LANGS)
        """
        #check params
        if lang not in Sounds.TTS_LANGS.keys():
            raise InvalidParameter('Specified lang "%s" is invalid' % lang)

        #save lang
        config = self._get_config()
        config['lang'] = lang
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
            raise InvalidParameter('Specified file "%s" is invalid' % filename)

        #check if sound is already playing
        if self.__sound_thread!=None and self.__sound_thread.is_alive():
            #sound already is playing, reject action
            raise Exception('A sound is already playing')

        #play sound
        self.__sound_thread = PlaySound(filepath)
        self.__sound_thread.start()

    def speak_message(self, text, lang):
        """
        Speak specified message

        Params:
            text (string): text to say
            lang (string): spoken lang

        Raises:
            Exception, InvalidParameter
        """
        #check parameters
        if not text or not lang:
            raise InvalidParameter('Some parameters are invalid')

        #check if sound is already playing
        if self.__sound_thread!=None and self.__sound_thread.is_alive():
            #sound already is playing, reject action
            raise Exception('A sound is already playing')

        #text to speech
        try:
            tts = gTTS(text=text, lang=lang)
            path = '/tmp/sound_%d.mp3' % int(time.time())
            tts.save(path)
        
            #play sound
            self.__sound_thread = PlaySound(path, True)
            self.__sound_thread.start()
            return True
        except:
            self.logger.exception('Exception when TTSing text "%s":' % text)

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

        raise InvalidParameter('Invalid sound file')

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
                    'name': os.path.basename(sound)
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
        self.logger.debug('Add sound of extension: %s' % file_ext[1])
        if file_ext[1][1:] not in Sounds.ALLOWED_EXTS:
            raise InvalidParameter('Invalid sound file uploaded (only %s are supported)' % ','.join(Sounds.ALLOWED_EXTS))

        #move file to valid dir
        if os.path.exists(filepath):
            name = os.path.basename(filepath)
            path = os.path.join(Sounds.SOUNDS_PATH, name)
            self.logger.debug('Name=%s path=%s' % (name, path))
            shutil.move(filepath, path)
            self.logger.info('File "%s" uploaded successfully' % name)
        else:
            #file doesn't exists
            self.logger.error('Sound file "%s" doesn\'t exist' % filepath)
            raise Exception('Sound file "%s"  doesn\'t exists' % filepath)

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


