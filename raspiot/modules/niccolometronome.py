#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
import time
import pyaudio
import wave
import pygame
import pyglet
import uuid
from fuzzywuzzy import fuzz
from threading import Thread
from raspiot.libs.sox import Sox
from raspiot.raspiot import RaspIotModule
from raspiot.utils import InvalidParameter, MissingParameter

__all__ = [u'Niccolometronome']


class MetronomeTask(Thread):
    """
    Metronome task
    """
    def __init__(self, logger, sound, bpm):
        """
        Constructor

        Args:
            logger (Logger): logger instance
            sound (string): path to metronome sound file
            bpm (int): beats per minute
        """
        Thread.__init__(self)
        Thread.daemon = True

        #members
        self.logger = logger
        self.running = True
        self.sound = sound
        self.set_bpm(bpm)
        self.__mute = False

    def stop(self):
        """
        Stop process
        """
        self.running = False

    def mute(self):
        """
        Mute sound playback
        """
        self.__mute = True

    def unmute(self):
        """
        Unmute sound playback
        """
        self.__mute = False

    def set_bpm(self, bpm):
        """
        Change current bpm
        Process will automatically adjust to new bpm
        """
        self.bpm = bpm
        self.__pause = 60.0 / float(bpm)
        self.__sync_gap = float(self.__pause * 0.1)
        self.logger.debug(u'New pause of %s for %sBPM' % (self.__pause, bpm))

    def run(self):
        """
        Metronome process
        """
        self.logger.debug(u'Metronome process started')

        #start sox metronome sound
        sox = Sox()
        console = sox.metronome_sound(self.bpm)

        #start metronome
        last_bpm = self.bpm
        while self.running:
            if (self.__mute or last_bpm!=self.bpm) and console:
                #kill metronome process because bpm changed or mute enabled
                self.logger.debug(u'Stop playing metronome sound')
                console.kill()
                console = None
            elif not self.__mute and not console:
                #unmute metronome starting new process
                self.logger.debug(u'Start playing metronome sound')
                console = sox.metronome_sound(self.bpm)
            else:
                #nothing to do
                pass

            #pause
            time.sleep(0.25)

            #update last bpm
            last_bpm = self.bpm

        #stop metronome
        if console:
            console.kill()

        self.logger.debug(u'Metronome process stopped')

    def run_pyglet(self):
        """
        Metronome process
        """
        self.logger.debug(u'Metronome process started')

        #prepare audio
        audio = pyglet.media.load(self.sound, streaming=False)
        audio.play()

        #start metronome
        next_sync = divmod(time.time() + self.__pause, 1)[1]
        while self.running:
            #play sound
            self.logger.debug(u'Metronome tick')
            start_playback = time.time()
            if not self.__mute:
                audio.play()
            end_playback = time.time()

            #major pause adjustment (0.1 it's just for precision adjustment) and pause
            playback_duration = end_playback - start_playback
            pause = self.__pause - playback_duration - self.__sync_gap
            time.sleep(pause)
            
            #precise pause adjustment
            while divmod(time.time(),1)[1]<next_sync:
                pass
            next_sync = divmod(next_sync + self.__pause, 1)[1]

        #clean stuff
        pygame.quit()

        self.logger.debug(u'Metronome process stopped')

    def run_pygame(self):
        """
        Metronome process
        """
        self.logger.debug(u'Metronome process started')

        #prepare audio
        wf = wave.open(self.sound, u'rb')
        channels = wf.getnchannels()
        frequency = wf.getframerate()
        wf.close()
        self.logger.debug(u'channels=%s frequency=%s' % (channels, frequency))
        pygame.mixer.pre_init(frequency, -16, channels, 2048)
        pygame.mixer.init()
        pygame.init()
        audio = pygame.mixer.Sound(file=self.sound)

        #start metronome
        next_sync = divmod(time.time() + self.__pause, 1)[1]
        while self.running:
            #play sound
            self.logger.debug(u'Metronome tick')
            start_playback = time.time()
            if not self.__mute:
                audio.play()
            end_playback = time.time()

            #major pause adjustment (0.1 it's just for precision adjustment) and pause
            playback_duration = end_playback - start_playback
            pause = self.__pause - playback_duration - self.__sync_gap
            time.sleep(pause)
            
            #precise pause adjustment
            while divmod(time.time(),1)[1]<next_sync:
                pass
            next_sync = divmod(next_sync + self.__pause, 1)[1]

        #clean stuff
        pygame.quit()

        self.logger.debug(u'Metronome process stopped')

    def run_pyaudio(self):
        """
        Metronome process
        """
        self.logger.debug(u'Metronome process started')

        #prepare audio
        audio = pyaudio.PyAudio()
        sound_file = wave.open(self.sound, u'rb')
        sound_buffer = sound_file.readframes(sound_file.getnframes())
        sound_format = audio.get_format_from_width(sound_file.getsampwidth())
        sound_channels = sound_file.getnchannels()
        #sound_sample_width = sound_file.getsampwidth()
        sound_framerate = sound_file.getframerate()

        #start metronome
        end_playback = time.time()
        sync_milliseconds = divmod(time.time(),1)[1]
        while self.running:
            #play sound
            self.logger.debug(u'Metronome tick')
            start_playback = time.time()
            stream = audio.open(
                format=sound_format,
                channels=sound_channels,
                rate=sound_framerate,
                output=True
            )
            stream.write(sound_buffer)
            stream.stop_stream()
            stream.close()
            end_playback = time.time()

            #major pause adjustment (0.1 it's just for precision adjustment) and pause
            playback_duration = end_playback - start_playback
            time.sleep(self.pause - playback_duration - 0.1)
            
            #precise pause adjustment
            while divmod(time.time(),1)[1]<sync_milliseconds:
                pass

        #clean stuff
        audio.terminate()

        self.logger.debug(u'Metronome process stopped')


class Niccolometronome(RaspIotModule):
    """
    Niccolo metronome module. Implement a voice controlled metronome
    """
    MODULE_AUTHOR = u'Niccolo'
    MODULE_VERSION = u'0.0.0'
    MODULE_PRICE = 0
    MODULE_DEPS = [u'speechrecognition']
    MODULE_DESCRIPTION = u'Niccolo metronome'
    MODULE_LOCKED = True
    MODULE_TAGS = [u'niccolo', u'metronome']
    MODULE_COUNTRY = None
    MODULE_URLINFO = None
    MODULE_URLHELP = None
    MODULE_URLSITE = None
    MODULE_URLBUGS = None

    MODULE_CONFIG_FILE = u'niccolo.conf'
    DEFAULT_CONFIG = {
        u'bpm': 60,
        u'phrases': []
    }

    COMMAND_START_METRONOME = 1
    COMMAND_STOP_METRONOME = 2
    COMMAND_SET_BPM = 3
    COMMAND_INCREASE_BPM = 4
    COMMAND_DECREASE_BPM = 5

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): flag to set debug level to logger
        """
        RaspIotModule.__init__(self, bootstrap, debug_enabled)

        #members
        self.__metronome_task = None
        self.__phrases = {}

        #events
        self.speech_command_detected_event = self._get_event('speechrecognition.command.detected')
        self.speech_command_error_event = self._get_event('speechrecognition.command.error')

    def _configure(self):
        """
        Configure module
        """
        #load phrases
        self.__load_phrases()

    def get_module_config(self):
        """
        Return module configuration
        """
        return {
            u'bpm': self._config[u'bpm'],
            u'phrases': self._config[u'phrases'],
            u'metronomerunning': not self.__metronome_task is None
        }

    def __load_phrases(self):
        """
        Load phrases internally (from config)
        """
        self.__phrases = {}
        for phrase in self._config[u'phrases']:
            if phrase[u'command']==self.COMMAND_START_METRONOME:
                self.logger.debug(u'"%s" phrase triggers __start_metronome_task' % phrase[u'phrase'])
                self.__phrases[phrase[u'phrase']] = lambda: self.__start_metronome_task()
            elif phrase[u'command']==self.COMMAND_STOP_METRONOME:
                self.logger.debug(u'"%s" phrase triggers __stop_metronome_task' % phrase[u'phrase'])
                self.__phrases[phrase[u'phrase']] = lambda: self.__stop_metronome_task()
            elif phrase[u'command']==self.COMMAND_INCREASE_BPM:
                self.logger.debug(u'"%s" phrase triggers __increase_bpm of %d' % (phrase[u'phrase'], phrase[u'bpm']))
                self.__phrases[phrase[u'phrase']] = lambda bpm=phrase[u'bpm']: self.__increase_bpm(bpm)
            elif phrase[u'command']==self.COMMAND_DECREASE_BPM:
                self.logger.debug(u'"%s" phrase triggers __decrease_bpm of %d' % (phrase[u'phrase'], phrase[u'bpm']))
                self.__phrases[phrase[u'phrase']] = lambda bpm=phrase[u'bpm']: self.__decrease_bpm(bpm)
            elif phrase[u'command']==self.COMMAND_SET_BPM:
                self.logger.debug(u'"%s" phrase triggers __set_bpm to %d' % (phrase[u'phrase'], phrase[u'bpm']))
                self.__phrases[phrase[u'phrase']] = lambda bpm=phrase[u'bpm']: self.__set_bpm(bpm)
            else:
                self.logger.error(u'Invalid command id %s specified' % phrase[u'command'])

        self.logger.debug(u'%d phrases loaded' % len(self.__phrases))

    def __start_metronome_task(self):
        """
        Start metronome task

        Return:
            bool: True if metronome already running
        """
        if self.__metronome_task is None:
            self.logger.debug(u'Start metronome')
            self.logger.debug(u'Start Niccolo metronome')
            self.__metronome_task = MetronomeTask(self.logger, u'/opt/raspiot/sounds/metronome1.wav', self._config[u'bpm'])
            self.__metronome_task.start()

            return True

        return False

    def __stop_metronome_task(self):
        """
        Stop metronome task
        """
        if self.__metronome_task is not None:
            self.logger.debug(u'Stop metronome')
            self.logger.debug(u'Stop Niccolo metronome')
            self.__metronome_task.stop()
            self.__metronome_task = None

    def __set_bpm(self, bpm):
        """
        Set current bpm

        Args:
            bpm (int): new bpm to set
        """
        #check param
        if bpm<40 or bpm>220:
            #no exception here to not raise exception when user increase or decrease bpm using voice
            self.logger.debug(u'New %d BPM value is invalid: must be 40..220 ' % bpm)

        #save bpm to config
        config = self._get_config()
        config[u'bpm'] = bpm

        #update metronome task bpm
        if self.__metronome_task:
            self.__metronome_task.set_bpm(bpm)
 
        if self._save_config(config):
            return True

        return False

    def __increase_bpm(self, bpm):
        """
        Increase current bpm

        Args:
            bpm (int): bpm to use to increase current one
        """
        self.logger.debug(u'Increase BPM of %d' % bpm)
        self.__set_bpm(self._config[u'bpm'] + bpm)

    def __decrease_bpm(self, bpm):
        """
        Decrease current bpm

        Args:
            bpm (int): bpm to use to increase current one
        """
        self.logger.debug(u'Decrease BPM of %d' % bpm)
        self.__set_bpm(self._config[u'bpm'] - bpm)

    def add_phrase(self, phrase, command, bpm):
        """
        Add new phrase

        Args:
            phrase (string): phrase to detect
            command (int): command id (see COMMAND_XXX)
            bpm (int): associated bpm
        """
        #check params
        if phrase is None or len(phrase)==0:
            raise MissingParameter(u'Parameter phrase is missing')
        if bpm is None:
            raise MissingParameter(u'Parameter bpm is missing')
        if command is None:
            raise MissingParameter(u'Parameter command is missing')
        #if bpm>=0 and (bpm<40 or bpm>220):
        #    raise InvalidParameter(u'Parameter bpm must be 40..220')
        #elif bpm<0 and bpm<-50:
        #    raise InvalidParameter(u'Parameter bpm must negative')

        #save phrase
        config = self._get_config()
        config[u'phrases'].append({
            u'id': str(uuid.uuid4()),
            u'phrase': phrase,
            u'command': command,
            u'bpm': bpm
        })
        
        if self._save_config(config):
            self.__load_phrases()

    def remove_phrase(self, id):
        """
        Remove specified phrase id

        Args:
            id (uuid): phrase id
        """
        #check params
        if id is None or len(id)==0:
            raise MissingParameter(u'Parameter id is missing')

        #search for phrase and delete it
        config = self._get_config()
        config[u'phrases'] = filter(lambda x: x[u'id']!=id, config[u'phrases'])

        #save config
        if self._save_config(config):
            self.__load_phrases()

    def start_metronome(self):
        """
        Start metronome
        """
        self.__start_metronome_task()

    def stop_metronome(self):
        """
        Stop metronome
        """
        self.__stop_metronome_task()

    def set_bpm(self, bpm):
        """
        Set bpm

        Args:
            bpm (int): new bpm
        """
        #check params
        if bpm is None:
            raise MissingParameter(u'Parameter bpm is missing')
        if bpm<40 or bpm>220:
            raise InvalidParameter(u'Parameter bpm must be 40..220')

        self.__set_bpm(bpm)

    def event_received(self, event):
        """
        Event received

        Args:
            event (dict): params of event
        """
        self.logger.debug(u'Event received: %s' % event)
        found = False
        if event[u'event']==u'speechrecognition.command.detected':
            #search and execute command
            for phrase in self.__phrases.keys():
                ratio = fuzz.ratio(phrase, event[u'params'][u'command'])
                self.logger.debug(u'Ratio for %s<=>%s: %s' % (phrase, event[u'params'][u'command'], ratio))
                if fuzz.ratio(phrase, event[u'params'][u'command'])>=70:
                    #command found, execute it
                    self.logger.debug(u'Detected command "%s"' % phrase)
                    found = True
                    self.__phrases[phrase]()
                    break

            #render command result
            if found:
                #command successful
                self.speech_command_detected_event.render(u'leds')
            else:
                #command error: no command found
                self.speech_command_error_event.render(u'leds')

            #finally unmute metronome
            if self.__metronome_task:
                self.__metronome_task.unmute()

        elif event[u'event']==u'speechrecognition.hotword.detected':
            #mute metronome to improve command recording
            self.logger.debug(u'Mute metronome')
            if self.__metronome_task:
                self.__metronome_task.mute()


