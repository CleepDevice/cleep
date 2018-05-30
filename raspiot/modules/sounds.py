#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import shutil
import logging
from raspiot.utils import InvalidParameter
from raspiot.raspiot import RaspIotRenderer
from raspiot.profiles import TextToSpeechProfile
import pygame
from threading import Thread
from gtts import gTTS
import time

__all__ = [u'Sounds']

class PlayMusic(Thread):
    """
    Play music thread
    """

    def __init__(self, filepath, volume, delete=False):
        """
        Constructor
        
        Args:
            filepath (string): music filepath
            volume (int): mixer volume (0..100)
            delete (bool): delete filepath after playing it
        """
        #init
        Thread.__init__(self)
        Thread.daemon = True
        self.logger = logging.getLogger(self.__class__.__name__)

        #members
        self.filepath = filepath
        self.delete = delete
        self.volume = volume
        self.__continu = True

    def stop(self):
        """
        Stop current playing music
        """
        self.__continu = False

    def run(self):
        """
        Play music process
        """
        try:
            #init player
            self.logger.debug(u'Init player')
            #pygame.mixer.init()
            pygame.mixer.music.set_volume(float(self.volume)/100.0)
            pygame.mixer.music.load(self.filepath)

            #play music
            self.logger.debug(u'Play music file "%s"' % self.filepath)
            pygame.mixer.music.play()

            #wait until end of playback or if user stop thread
            while pygame.mixer.music.get_busy()==True:
                if not self.__continu:
                    #stop requested
                    pygame.mixer.music.stop()
                    break
                time.sleep(.1)
            #pygame.quit()

            #delete file
            if self.delete:
                self.logger.debug(u'PlayMusic: delete music file "%s"' % self.filepath)
                os.remove(self.filepath)

        except:
            self.logger.exception(u'Exception during music playing:')




class Sounds(RaspIotRenderer):
    """
    Add capability to play sounds or music and speech some text
    """
    MODULE_AUTHOR = u'Cleep'
    MODULE_VERSION = u'1.0.0'
    MODULE_PRICE = 0
    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Plays sounds or speech text you want'
    MODULE_LOCKED = False
    MODULE_TAGS = [u'audio', u'sound', u'music', u'speech']
    MODULE_COUNTRY = None
    MODULE_URLINFO = None
    MODULE_URLHELP = None
    MODULE_URLBUGS = None
    MODULE_URLSITE = None

    MODULE_CONFIG_FILE = u'sounds.conf'
    DEFAULT_CONFIG = {
        u'lang': u'en'
    }

    RENDERER_PROFILES = [TextToSpeechProfile]
    RENDERER_TYPE = u'sound'

    MUSICS_PATH = u'/var/opt/raspiot/musics'
    SOUNDS_PATH = u'/var/opt/raspiot/sounds'
    ALLOWED_MUSIC_EXTS = [u'mp3', u'wav', u'ogg']
    ALLOWED_SOUND_EXTS = [u'ogg', u'wav']
    MIXER_FREQUENCY = 44100
    MIXER_CHANNEL = 2
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

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): flag to set debug level to logger
        """
        #init
        RaspIotRenderer.__init__(self, bootstrap, debug_enabled)

        #disable urllib info logs
        url_log = logging.getLogger(u'urllib3')
        if url_log:
            url_log.setLevel(logging.WARNING)

        #members
        self.__music_thread = None
        self.volume = 50
        self.sounds_buffer = {}

        #make sure paths exist
        if not os.path.exists(Sounds.SOUNDS_PATH):
            self.cleep_filesystem.mkdir(Sounds.SOUNDS_PATH, True)
        if not os.path.exists(Sounds.MUSICS_PATH):
            self.cleep_filesystem.mkdir(Sounds.MUSICS_PATH, True)

    def _configure(self):
        """
        Configure module
        """
        #init mixer
        pygame.mixer.init(frequency=self.MIXER_FREQUENCY, channels=self.MIXER_CHANNELS)

        #bufferize sounds
        sounds = self._get_sounds()
        for sound in sounds:
            path = os.path.join(self.SOUNDS_PATH, sound[u'fullname'])
            if not self.__bufferize_sound(path):
                #invalid file, delete it
                self.delete_sound(sound[u'fullname'])

    def get_module_config(self):
        """
        Get full module configuration
        """
        config = {}
        config[u'langs'] = self.get_langs()
        config[u'volume'] = self.get_volume()
        config[u'musics'] = self.get_musics()
        config[u'sounds'] = self.get_sounds()

        return config

    def __bufferize_sound(self, path):
        """
        Bufferize specified file

        Args:
            path (string): file full path

        Return:
            bool: True if file bufferized
        """
        try:
            self.sounds_buffer[sound[u'fullname']] = pygame.mixer.Sound(file=path)
            return True
        except:
            self.logger.exception('Unable to bufferize file:')

        return False

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
        if lang is None or len(lang)==0:
            raise MissingParameter(u'Lang parameter is missing')
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
        return self.volume

    def set_volume(self, volume):
        """
        Set volume

        Args:
            volume (int): volume value
        """
        if volume is None:
            raise MissingParameter(u'Volume parameter is missing')
        if volume<0 or volume>100:
            raise InvalidParameter(u'Volume value must be 0..100')

        self.volume = volume

    def play_sound(self, fullname):
        """
        Play sound. Multiple sound can be played simultaneously

        Args:
            fullname (string): sound file to play
        """
        if fullname is None or len(fullname)==0:
            raise MissingParameter(u'Parameter fullname is missing')

        #build filepath
        filepath = os.path.join(Sounds.SOUNDS_PATH, fullname)

        #check file validity
        if not os.path.exists(filepath):
            #invalid file specified
            raise InvalidParameter(u'Specified sound file "%s" is invalid' % fullname)
        if fullname not in self.sounds_buffer.keys():
            raise CommandError(u'Unable to play sound: sound "%s" not found')

        #play sound
        self.sounds_buffer[fullname].set_volume(float(self.volume)/100.0)
        self.sounds_buffer[fullname].play()

    def play_music(self, fullname, force=False):
        """
        Play specified file. Only one music can be played at once, use force to stop current playback

        Args:
            fullname (string): music file to play
            force (bool): force playing music and stop currently playing music 

        Raises:
            Exception, InvalidParameter
        """
        if fullname is None or len(fullname)==0:
            raise MissingParameter(u'Parameter fullname is missing')

        #build filepath
        filepath = os.path.join(Sounds.MUSICS_PATH, fullname)

        #check file validity
        if not os.path.exists(filepath):
            #invalid file specified
            raise InvalidParameter(u'Specified music file "%s" is invalid' % fullname)

        #check if music is already playing
        if self.__music_thread!=None and self.__music_thread.is_alive():
            #music already is playing
            if not force:
                #rejct action
                raise Exception(u'Can\'t play 2 musics at the same time')
            else:
                #stop current music
                self.__music_thread.stop()

        #play music
        self.__music_thread = PlayMusic(filepath, self.volume)
        self.__music_thread.start()

    def speak_text(self, text, lang, force=False):
        """
        Speak specified message

        Args:
            text (string): text to say
            lang (string): spoken lang
            force (bool): force text speak even if music is already playing (stop music)

        Raises:
            Exception, InvalidParameter
        """
        #check parameters
        if text is None or len(text)==0:
            raise MissingParameter(u'Text parameter is missing')
        if lang is None or len(lang)==0:
            raise MissingParameter(u'Lang parameter is missing')

        #check if music is already playing
        if self.__music_thread!=None and self.__music_thread.is_alive():
            #music already is playing
            if not force:
                #reject action
                raise Exception(u'Can\'t play 2 musics at the same time')
            else:
                #stop current music
                self.__music_thread.stop()

        #text to speech
        try:
            tts = gTTS(text=text, lang=lang)
            path = u'/tmp/music_%d.mp3' % int(time.time())
            tts.save(path)
        
            #play music
            self.__music_thread = PlayMusic(path, self.volume, True)
            self.__music_thread.start()
            return True

        except:
            self.logger.exception(u'Exception when converting text to music for text "%s":' % text)

        return False

    def delete_sound(self, fullname):
        """
        Delete sound

        Args:
            fullname (string): sound file (with file extension) to delete

        Raises:
            InvalidParameter
        """
        if fullname is None or len(fullname)==0:
            raise MissingParameter(u'Fullname parameter is missing')
        #build filepath
        filepath = os.path.join(Sounds.SOUNDS_PATH, fullname)
    
        #delete file
        if os.path.exists(filepath):
            os.remove(filepath)
            return True

        raise InvalidParameter(u'Invalid sound file')

    def delete_music(self, fullname):
        """
        Delete music

        Args:
            fullname (string): music file (with file extension) to delete

        Raises:
            InvalidParameter
        """
        if fullname is None or len(fullname)==0:
            raise MissingParameter(u'Fullname parameter is missing')
        #build filepath
        filepath = os.path.join(Sounds.MUSICS_PATH, fullname)
    
        #delete file
        if os.path.exists(filepath):
            os.remove(filepath)
            return True

        raise InvalidParameter(u'Invalid music file')

    def get_musics(self):
        """
        Get musics

        Returns:
            list: list of musics::
                [
                    {
                        name (string): filename without extension
                        fullname (string): filename with file extension
                    },
                    ...
                ]
        """
        out = []
        for root, dirs, musics in os.walk(Sounds.MUSICS_PATH):
            for music in musics:
                out.append({
                    u'name': os.path.splitext(os.path.basename(music))[0],
                    u'fullname': os.path.basename(music)
                })

        return out

    def get_sounds(self):
        """
        Get all sounds

        Returns:
            list: list of sounds::
                [
                    {
                        name (string): filename without extension
                        fullname (string): filename with file extension
                    },
                    ...
                ]
        """
        out = []
        for root, dirs, sounds in os.walk(Sounds.SOUNDS_PATH):
            for sound in sounds:
                out.append({
                    u'name': os.path.splitext(os.path.basename(sound))[0],
                    u'fullname': os.path.basename(sound)
                })

        return out

    def add_sound(self, filepath):
        """
        Add new sound

        Args:
            filepath (string): uploaded and local filepath

        Returns:
            bool: True if file uploaded successfully
            
        Raises:
            Exception, InvalidParameter
        """
        #check parameters
        file_ext = os.path.splitext(filepath)
        self.logger.debug(u'Add sound of extension: %s' % file_ext[1])
        if file_ext[1][1:] not in Sounds.ALLOWED_SOUND_EXTS:
            raise InvalidParameter(u'Invalid sound file uploaded (only %s are supported)' % ','.join(Sounds.ALLOWED_SOUND_EXTS))

        #move file to valid dir
        if os.path.exists(filepath):
            name = os.path.basename(filepath)
            path = os.path.join(Sounds.MUSICS_PATH, name)
            self.logger.debug(u'Name=%s path=%s' % (name, path))
            shutil.move(filepath, path)
            self.logger.info(u'Sound file "%s" uploaded successfully' % name)

            #once copied, try to bufferize file
            path = os.path.join(self.SOUNDS_PATH, sound[u'fullname'])
            if not self.__bufferize_sound(path):
                #invalid file, delete it
                self.delete_sound(sound[u'fullname'])
                raise Exception(u'Sound file format is not supported')

        else:
            #file doesn't exists
            self.logger.error(u'Sound file "%s" doesn\'t exist' % filepath)
            raise Exception(u'Sound file "%s"  doesn\'t exists' % filepath)

        return True
            

    def add_music(self, filepath):
        """
        Add new music

        Args:
            filepath (string): uploaded and local filepath

        Returns:
            bool: True if file uploaded successfully
            
        Raises:
            Exception, InvalidParameter
        """
        #check parameters
        file_ext = os.path.splitext(filepath)
        self.logger.debug(u'Add music of extension: %s' % file_ext[1])
        if file_ext[1][1:] not in Sounds.ALLOWED_MUSIC_EXTS:
            raise InvalidParameter(u'Invalid music file uploaded (only %s are supported)' % ','.join(Sounds.ALLOWED_MUSIC_EXTS))

        #move file to valid dir
        if os.path.exists(filepath):
            name = os.path.basename(filepath)
            path = os.path.join(Sounds.MUSICS_PATH, name)
            self.logger.debug(u'Name=%s path=%s' % (name, path))
            shutil.move(filepath, path)
            self.logger.info(u'File "%s" uploaded successfully' % name)
        else:
            #file doesn't exists
            self.logger.error(u'Music file "%s" doesn\'t exist' % filepath)
            raise Exception(u'Music file "%s"  doesn\'t exists' % filepath)

        return True

    def play_random_music(self):
        """
        Play random music from list of musics
        """
        musics = self.get_musics()

        if len(musics)>0:
            num = random.randrange(0, len(musics), 1)
            self.play_music(musics[num][u'fullname'])

        return True

    def _render(self, profile):
        """
        TextToSpeech specified profile

        Args:
            profile (any supported profile): profile to speech
        """
        self.speak_text(profile.text, self._config[u'lang'])

