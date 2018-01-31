#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
import time
import pyaudio
import wave
import pygame
from fuzzywuzzy import fuzz
from threading import Thread
from raspiot.raspiot import RaspIotModule

__all__ = [u'Niccolo']


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

    def bpm_to_seconds(self, bpm):
        """
        Convert BPM (Beat Per Minute) to real seconds

        Args:
            bpm (int): Beat Per Minute

        Return:
            float: number of seconds
        """
        return 60.0 / float(bpm)

    def stop(self):
        """
        Stop process
        """
        self.running = False

    def set_bpm(self, bpm):
        """
        Change current bpm
        Process will automatically adjust to new bpm
        """
        self.__pause = self.bpm_to_seconds(bpm)
        self.__sync_gap = float(self.__pause * 0.1)
        self.logger.debug('New pause of %s for %sBPM' % (self.__pause, bpm))

    def run(self):
        """
        Metronome process
        """
        self.logger.debug(u'Metronome process started')

        #prepare audio
        wf = wave.open(self.sound, 'rb')
        channels = wf.getnchannels()
        framerate = wf.getframerate()
        wf.close()
        self.logger.debug('channels=%s framerate=%s' % (channels, framerate))
        pygame.mixer.init(frequency=framerate, channels=channels)
        audio = pygame.mixer.Sound(file=self.sound)

        #differ startup
        time.sleep(2.0)

        #start metronome
        next_sync = divmod(time.time() + self.__pause, 1)[1]
        while self.running:
            #play sound
            self.logger.debug('Metronome tick')
            start_playback = time.time()
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

    def run_pyaudio(self):
        """
        Metronome process
        """
        self.logger.debug(u'Metronome process started')

        #prepare audio
        audio = pyaudio.PyAudio()
        sound_file = wave.open(self.sound, 'rb')
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
            self.logger.debug('Metronome tick')
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

    MODULE_CONFIG_FILE = u'niccolo.conf'
    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Niccolo metronome'
    MODULE_LOCKED = True
    MODULE_TAGS = [u'niccolo', u'metronome']
    MODULE_COUNTRY = None
    MODULE_LINK = None

    DEFAULT_CONFIG = {
        u'bpm': 60
    }

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

    def _configure(self):
        """
        Configure module
        """
        #start metronome
        #self.__start_metronome_task()

    def __start_metronome_task(self):
        """
        Start metronome task
        """
        if self.__metronome_task is None:
            self.logger.debug(u'Start Niccolo metronome')
            self.__metronome_task = MetronomeTask(self.logger, u'/opt/raspiot/sounds/metronome1.wav', 60)
            self.__metronome_task.start()

    def __stop_metronome_task(self):
        """
        Stop metronome task
        """
        if self.__metronome_task is not None:
            self.logger.debug(u'Stop Niccolo metronome')
            self.__metronome_task.stop()
            self.__metronome_task = None

    def set_bpm(self, bpm):
        """
        Set current bpm
        """
        config = self._get_config()
        config[u'bpm'] = bpm
        return self._save_config(config)

    def event_received(self, event):
        self.logger.debug('Event received: %s' % event)
        if event[u'event']==u'speechrecognition.command.received':
            if fuzz.ratio(u'démarre', event[u'params'][u'command'])>=70:
                self.logger.debug(u'"démarre" command detected')
                self.__start_metronome_task()

            elif fuzz.ratio(u'éteins', event[u'params'][u'command'])>=70:
                self.logger.debug(u'"éteins" command detected')
                self.__stop_metronome_task()

