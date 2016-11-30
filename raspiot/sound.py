#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import shutil
import logging
import bus
from raspiot import RaspIot
import pygame
from threading import Thread
from gtts import gTTS
import time

__all__ = ['Sound']

#logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(name)s %(levelname)s : %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG);

class PlaySound(Thread):
    """
    Play sound thread
    """
    def __init__(self, filepath, delete=False):
        """
        Constructor
        @param filepath: sound filepath
        @param filedesc: file descriptor. Closed at end of playback
        """
        Thread.__init__(self)
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
            logger.debug('init player')
            pygame.mixer.init()
            pygame.mixer.music.load(self.filepath)

            #play sound
            logger.debug('play sound file "%s"' % self.filepath)
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
                logger.debug('PlaySound: delete sound file "%s"' % self.filepath)
                os.remove(self.filepath)
        except:
            logger.exception('Exception during sound playing:')

class Sound(RaspIot):

    CONFIG_FILE = 'sound.conf'
    DEPS = []
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

    def __init__(self, bus):
        RaspIot.__init__(self, bus)
        #members
        self.__sound_thread = None

        #init config
        config = self._get_config()
        if not config.has_key('lang'):
            config['lang'] = 'en'
            self._save_config(config)

        #make sure sounds path exists
        if not os.path.exists(Sound.SOUNDS_PATH):
            os.makedirs(Sound.SOUNDS_PATH)

    def get_langs(self):
        """
        Return all langs
        """
        return {
            'langs': Sound.TTS_LANGS,
            'lang': self._config['lang']
        }

    def set_lang(self, lang):
        """
        Set tts lang
        """
        #check params
        if lang not in Sound.TTS_LANGS.keys():
            raise bus.InvalidParameter('Specified lang "%s" is invalid' % lang)

        #save lang
        config = self._get_config()
        config['lang'] = lang
        self._save_config(config)

    def get_volume(self):
        """
        Get volume
        """
        pygame.mixer.init()
        volume = pygame.mixer.music.get_volume()
        pygame.quit()
        return volume*100

    def set_volume(self, volume):
        """
        Set volume
        """
        pygame.mixer.init()
        pygame.mixer.music.set_volume(int(volume/100.0))
        pygame.quit()

    def play_sound(self, filepath):
        """
        Play specified file
        """
        #check file validity
        if not filepath.startswith(Sound.SOUNDS_PATH) or not os.path.exists(filepath):
            #invalid file specified
            raise bus.InvalidParameter('Specified file "%s" is invalid' % name)

        #check if sound is already playing
        if self.__sound_thread!=None and self.__sound_thread.is_alive():
            #sound already is playing, reject action
            raise Exception('A sound is already playing')

        #play sound
        self.__sound_thread = PlaySound(filepath)
        self.__sound_thread.start()

    def say_text(self, text, lang):
        """
        Say specified text
        @param text: text to say
        @param lang: spoken lang
        """
        #check parameters
        if not text or not lang:
            raise bus.InvalidParameter('Some parameters are invalid')

        #check if sound is already playing
        if self.__sound_thread!=None and self.__sound_thread.is_alive():
            #sound already is playing, reject action
            raise Exception('A sound is already playing')

        #text to speech
        tts = gTTS(text=text, lang=self._config['lang'])
        path = '/tmp/sound_%d.mp3' % int(time.time())
        tts.save(path)
        
        #play sound
        self.__sound_thread = PlaySound(path, True)
        self.__sound_thread.start()

    def del_sound(self, filepath):
        """
        Delete sound
        """
        for root, dirs, sounds in os.walk(Sound.SOUNDS_PATH):
            for sound in sounds:
                if os.path.join(root, sound)==filepath:
                    os.remove(filepath)
                    return True

        raise bus.InvalidParameter('Sound file not found')

    def get_sounds(self):
        """
        Get sounds
        """
        out = []
        for root, dirs, sounds in os.walk(Sound.SOUNDS_PATH):
            for sound in sounds:
                out.append({
                    'name': os.path.basename(sound),
                    'path': os.path.join(root, sound)
                })
        return out

    def add_sound(self, filepath):
        """
        Add new sound
        @param sound: local sound file path
        """
        #check parameters
        file_ext = os.path.splitext(filepath)
        logger.debug('Add sound of extension: %s' % file_ext[1])
        if file_ext[1][1:] not in Sound.ALLOWED_EXTS:
            raise bus.InvalidParameter('Invalid sound file uploaded (only %s are supported)' % ','.join(Sound.ALLOWED_EXTS))

        #move file to valid dir
        if os.path.exists(filepath):
            name = os.path.basename(filepath)
            path = os.path.join(Sound.SOUNDS_PATH, name)
            logger.debug('Name=%s path=%s' % (name, path))
            shutil.move(filepath, path)
            logger.info('File "%s" uploaded successfully' % name)
        else:
            #file doesn't exists
            logger.error('Sound file "%s" doesn\'t exist' % filepath)
            raise Exception('Sound file "%s"  doesn\'t exists' % filepath)

        return True

