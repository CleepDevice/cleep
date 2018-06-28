#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
import os
import collections
import pyaudio
import audioop
import uuid
from threading import Thread, Lock, Timer
from raspiot.raspiot import RaspIotResource
from raspiot.libs.commands.sox import Sox
from raspiot.libs.internals.console import Console
from raspiot.libs.externals.snowboy import Snowboy
from raspiot.libs.externals.snowboylib import snowboydetect, snowboydecoder
from raspiot.utils import MissingParameter, InvalidParameter, CommandError
import speech_recognition as speechrecognition


__all__ = ['Speechrecognition']


class BuildPersonalVoiceModelTask(Thread):
    """
    Build snowboy personal voice model can take more than 1 minute, so we must parallelize its process
    """

    TMP = u'/tmp/'

    def __init__(self, token, recordings, end_of_training_callback, logger):
        """
        Constructor

        Args:
            token (string): api token
            recordings (list): list of 3 recordings
            end_of_training_callback (callback): function called when training is terminated (params: error (bool), model filepath (string))
            logger (logger): logger instance
        """
        Thread.__init__(self)
        Thread.daemon = True

        #members
        self.logger = logger
        self.callback = end_of_training_callback
        self.token = token
        self.recordings = recordings
        self.sox = Sox()

    def run(self):
        """
        Task
        """
        #remove silence in recordings
        #command from https://unix.stackexchange.com/a/293868
        trimmed_recordings = [
            os.path.join(self.TMP, '%s.wav' % str(uuid.uuid4())),
            os.path.join(self.TMP, '%s.wav' % str(uuid.uuid4())),
            os.path.join(self.TMP, '%s.wav' % str(uuid.uuid4()))
        ]
        for i in range(len(self.recordings)):
            if not self.sox.trim_audio(self.recordings[i], trimmed_recordings[i]):
                #error during trimming fall back to original file
                trimmed_recordings[i] = self.recordings[i]

        #build personal voice model
        error = None
        voice_model = None
        snowboy = Snowboy(self.cleep_filesystem, self.token)
        try:
            voice_model = snowboy.train(trimmed_recordings[0], trimmed_recordings[1], trimmed_recordings[2])
            self.logger.debug(u'Generated voice model: %s' % voice_model)

        except:
            self.logger.exception('Error during snowboy training:')
            error = snowboy.get_last_error()

        #end of process callback
        self.callback(error, voice_model)


class SpeechRecognitionProcess(Thread):
    """
    Speech recognition process
    """
    def __init__(self, logger, voice_model, events, provider_token, sensitivity=0.4, audio_gain=1):
        """
        Constructor

        Args:
            logger (logger): logger instance
            voice_model (string): voice model file path (pmdl or umdl)
            events (dict): events instances (keys: ('hotword_detected', 'hotword_released', 'command_detected', 'command_error'))
            sensitivity (float): great value make detector more sensitive to false positive
            audio_gain (int): decrease volume (<1) or boost volume (>1)
        """
        Thread.__init__(self)
        Thread.daemon = True

        #members
        self.logger = logger
        self.running = True
        self.hotword_detected_event = events[u'hotword_detected']
        self.hotword_released_event = event = events[u'hotword_released']
        self.command_detected_event = events[u'command_detected']
        self.command_error_event = events[u'command_error']
        self.detector = snowboydecoder.HotwordDetector(voice_model, sensitivity=sensitivity, audio_gain=audio_gain)
        self.recognizer = speechrecognition.Recognizer()
        self.provider_token = provider_token
        self.voice_model = voice_model
        self.sensitivity = sensitivity
        self.audio_gain = audio_gain
        self.test = False

    def stop(self):
        """
        Stop recognition process
        """
        self.running = False

    def enable_test(self):
        """
        Enable test (disable command recognition)
        """
        self.test = True

    def disable_test(self):
        """
        Disable test
        """
        self.test = False

    def is_test_enabled(self):
        """
        Return True if test mode is enabled

        Return:
            bool: True if test is running
        """
        return self.test

    def need_to_stop(self):
        """
        Return running status
        """
        return not self.running

    def record_command(self, recording):
        """
        Record command after hotword detected

        Args:
            recording (string): recorded file path
        """
        if self.test:
            #drop recording during test
            return

        #get recorded audio
        try:
            with speechrecognition.AudioFile(recording) as source:
                audio = self.recognizer.record(source)
        except:
            self.logger.exception(u'Error during speech recognition')
        finally:
            #release hotword
            self.hotword_released_event.send()
            self.hotword_released_event.render(u'leds')

        #check audio
        if not audio:
            self.command_error_event.send()
            self.command_error_event.render(u'leds')
            self.logger.debug(u'No audio recorded')
            return

        #TODO handle STT provider
	try:
            self.logger.debug('Recognizing audio... (token: %s)' % self.provider_token)
            command = self.recognizer.recognize_bing(audio, key=self.provider_token.encode(), language='fr-FR')
            self.logger.debug('Done: command=%s' % command)

        except speechrecognition.UnknownValueError:
            self.command_error_event.send()
            self.command_error_event.render(u'leds')
            self.logger.warning(u'STT provider doesn\'t understand audio')
            return

        except speechrecognition.RequestError as e:
            self.command_error_event.send()
            self.command_error_event.render(u'leds')
            self.logger.error(u'STT provider service seems to be unreachable: %s' % str(e))
            return

        #check command
        if not command:
            self.command_error_event.send()
            self.command_error_event.render(u'leds')
            self.logger.debug(u'No command recognized')
            return

        #send command detected event
        self.command_detected_event.send(params={
            u'hotword': 'not implemented',
            u'command': command
        })

        #purge recorded file
        if os.path.exists(recording):
            try:
                os.remove(recording)
            except:
                self.logger.exception('Unable to delete recording:')

    def hotword_detected(self):
        """
        Called when hotword is detected
        """
        self.logger.debug('-> hotword detected')

        #send hotword detected event
        if self.test:
            #send hotword test only to rpc during tests
            self.hotword_detected_event.send(to=u'rpc')
        else:
            self.hotword_detected_event.render(u'leds')
            self.hotword_detected_event.send()

    def run(self):
        """
        Speech recognition process
        """
        self.logger.debug(u'Speech recognition thread started')

        while self.running:
            try:
                #detect hotword
                self.detector.start(
                        detected_callback=self.hotword_detected, 
                        interrupt_check=self.need_to_stop,
                        audio_recorder_callback=self.record_command,
                        sleep_time=0.01
                )
            except KeyboardInterrupt:
                self.logger.debug(u'Word detection stopped by user')

            except:
                self.logger.exception(u'Exception during hotword detection:')

        #clean everything
        try:
            self.detector.terminate()
        except:
            self.logger.exception(u'Exception during hotword dectection deallocation')

        self.logger.debug(u'Speech recognition thread stopped')

class RingBuffer(object):
    """Ring buffer to hold audio from PortAudio"""
    def __init__(self, size = 4096):
        self._buf = collections.deque(maxlen=size)

    def extend(self, data):
        """Adds data to the end of buffer"""
        self._buf.extend(data)

    def get(self):
        """Retrieves data from the beginning of buffer and clears it"""
        tmp = bytes(bytearray(self._buf))
        self._buf.clear()
        return tmp

class SpeechRecognitionProcessOld1(Thread):
    """
    Speech recognition process
    """
    def __init__(self, logger, voice_model, command_event, provider_token, sensitivity=0.45, audio_gain=1.2, record_duration=5.0):
        """
        Constructor

        Args:
            logger (logger): logger instance
            voice_model (string): voice model file path (pmdl or umdl)
            command_event (Speechrecognitioncommand): event instance which will be sent when command is received
            provider_token (string): STT provider token
            sensitivity (float): great value make detector more sensitive to false positive
            audio_gain (int): decrease volume (<1) or boost volume (>1)
            record_duration (float): when hotword is detected, duration or command recording
        """
        Thread.__init__(self)
        Thread.daemon = True

        #members
        self.logger = logger
        self.running = True
        self.command_event = command_event
        self.sensitivity = sensitivity
        self.audio_gain = audio_gain
        self.provider_token = provider_token #'d16985f039b34c1cb0a90658787b109d'
        self.voice_model = voice_model
        self.record_duration = record_duration

        #STT stuff
        self.detector = snowboydetect.SnowboyDetect(resource_filename='/opt/raspiot/snowboy/resources/common.res', model_str='/opt/raspiot/speechrecognition/voice_model.pmdl')
	self.detector.SetAudioGain(self.audio_gain)
	self.num_hotwords = self.detector.NumHotwords()
	self.detector.SetSensitivity(str(self.sensitivity))
        self.rate = self.detector.SampleRate()
        self.channels = self.detector.NumChannels()
        self.recognizer = speechrecognition.Recognizer()

        #audio stuff
	self.buffer = RingBuffer(self.detector.NumChannels() * self.detector.SampleRate() * 5)
	self.audio = pyaudio.PyAudio()
        self.stream_in = self.audio.open(
            input=True, output=False,
            format=self.audio.get_format_from_width(self.detector.BitsPerSample() / 8),
            channels=self.channels,
            rate=self.rate,
            frames_per_buffer=2048,
            stream_callback=self.__audio_callback)

    def __audio_callback(self, in_data, frame_count, time_info, status):
        """
        Audio callback used to store data from microphone
        """
        self.buffer.extend(in_data)
        play_data = chr(0) * len(in_data)

        return play_data, pyaudio.paContinue

    def __write_wav(self, data, output_file):
        """
        Write audio data to wav file

        Args:
            data (binary): audio data recorded with pyaudio
            output_file (string): path to wav file
        """
        try:
            import wave
            wavefile = wave.open(output_file, u'wb')
            wavefile.setnchannels(self.channels)
            wavefile.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
            wavefile.setframerate(self.rate)
            wavefile.writeframes(data)
            wavefile.close()
            self.logger.debug('Recording wav file written to %s' % output_file)
        except:
            self.logger.exception('Error during recording writing:')

    def stop():
        """
        Stop hotword process
        """
        self.running = False

    def __hotword_detected(self, hotword_index):
        """
        Hotword detected process:
         1) record audio until timeout
         2) convert audio to AudioData instance
         3) send AudioData to STT provider
         4) finally send event to raspiot

        Args:
            hotword_index (int): indicate voice_model detected in case of multiple models (not implemented yet)
        """
        #record audio until timeout
        self.logger.debug('Recordings audio during %d seconds...' % self.record_duration)
        start = time.time()
        recorded_data = bytes()
        while True:
            data = self.buffer.get()
            if len(data)>0:
                #append buffer
                recorded_data += data

            #check timeout
            if time.time()>(start+self.record_duration):
                #stop recording
                self.logger.debug(u'Stop recording')
                break
            else:
                #pause
                time.sleep(0.03)
        self.logger.debug(u'Recording finished')

        #check recorded data
        if len(recorded_data)==0:
            self.logger.debug('Nothing said during recording')
        elif self.logger.getEffectiveLevel()==logging.DEBUG:
            #write audio to file only during debug
            self.__write_wav(recorded_data, '/tmp/recording.wav')

        #speech to text recording
	try:
            #create audiodata object to use speechrecognition library
            audio = speechrecognition.AudioData(recorded_data, self.rate, 2)

            #recognize audio
            self.logger.debug(u'Recognizing audio...')
            command = self.recognizer.recognize_bing(audio, key=self.provider_token, language='fr-FR')
            self.logger.debug(u'Done: command=%s' % command)

        except speechrecognition.UnknownValueError:
            self.logger.warning(u'STT provider doesn\'t understand command')

        except speechrecognition.RequestError as e:
            self.logger.error(u'STT provider service seems to be unreachable: %s' % str(e))

        #send event
        params = {
            u'hotword': 'hello',
            u'command': command
        }
        self.command_event.send(params=params);

    def run(self):
        """
        Run hotword detection process
        """
        self.logger.debug(u'SpeechRecognitionProcess started')
        while self.running:
            #get audio
            data = self.buffer.get()
            if len(data) == 0:
                time.sleep(0.03)
                continue

            #detect hotword
            resp = self.detector.RunDetection(data)
            if resp==-1:
                #error occured
                self.logger.error(u'Error initializing streams or reading audio data')
            elif resp>0:
                self.logger.debug(u'Hotword detected #%s' % resp)
                #send event that hotword was detected
                self.hotword_event.send()

                #process command detection
                self.__hotword_detected(resp)

        #clean everything
        self.logger.debug(u'Clean audio stuff')
        self.stream_in.stop_stream()
        self.stream_in.close()
        self.audio.terminate()

        self.logger.debug(u'SpeechRecognitionProcess stopped')


class Speechrecognition(RaspIotResource):
    """
    Speechrecognition module implements SpeechToText feature using snowboy for local hotword detection
    and online services to translate user speech to text
    """
    MODULE_AUTHOR = u'Cleep'
    MODULE_VERSION = u'1.0.0'
    MODULE_PRICE = 0
    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Control your device using voice'
    MODULE_LOCKED = False
    MODULE_TAGS = [u'audio', u'speech', u'stt', 'speechtotext']
    MODULE_COUNTRY = None
    MODULE_URLINFO = None
    MODULE_URLHELP = None
    MODULE_URLBUGS = None
    MODULE_URLSITE = None

    MODULE_CONFIG_FILE = u'speechrecognition.conf'
    DEFAULT_CONFIG = {
        u'hotwordtoken': None,
        u'hotwordfiles': [None, None, None],
        u'hotwordmodel': None,
        u'providerid': None,
        u'providerapikeys': {},
        u'serviceenabled': True
    }

    RESOURCES = {
        u'audio.capture': 15.0
    }

    PROVIDERS = [
        {u'id':0, u'label':u'Microsoft Bing Speech', u'enabled':True},
        {u'id':1, u'label':u'Google Cloud Speech', u'enabled':False},
    ]

    VOICE_MODEL_PATH = u'/opt/raspiot/speechrecognition'

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): flag to set debug level to logger
        """
        #init
        RaspIotResource.__init__(self, self.RESOURCES, bootstrap, debug_enabled)

        #members
        self.sox = Sox()
        self.__training_task = None
        self.__speech_recognition_task = None
        self.__stop_task_after_test = False

        #events
        self.training_ok_event = self._get_event('speechrecognition.training.ok')
        self.training_ko_event = self._get_event('speechrecognition.training.ko')
        self.hotword_detected_event = self._get_event('speechrecognition.hotword.detected')
        self.hotword_released_event = self._get_event('speechrecognition.hotword.released')
        self.command_detected_event = self._get_event('speechrecognition.command.detected')
        self.command_error_event = self._get_event('speechrecognition.command.error')
        self.events = {
            u'hotword_detected': self.hotword_detected_event,
            u'hotword_released': self.hotword_released_event,
            u'command_detected': self.command_detected_event,
            u'command_error': self.command_error_event
        }

    def _configure(self):
        """
        Configure module
        """
        #make sure voice model path exists
        if not os.path.exists(self.VOICE_MODEL_PATH):
            self.cleep_filesystem.mkdir(self.VOICE_MODEL_PATH, True)
    
        #start voice recognition process if possible
        self.acquire_resource(u'audio.capture')

    def get_module_config(self):
        """
        Return module configuration
        """
        #build provider list (with apikey)
        providers = []
        config = self._get_config()
        for provider in self.PROVIDERS:
            #deep copy entry
            entry = {
                u'id': provider[u'id'],
                u'provider': provider[u'label'],
                u'enabled': provider[u'enabled'],
                u'apikey': None
            }

            #fill apikey if configured
            if str(provider[u'id']) in config[u'providerapikeys'].keys():
                entry[u'apikey'] = config[u'providerapikeys'][str(provider[u'id'])]

            #save entry
            providers.append(entry)

        return {
            u'providerid': config[u'providerid'],
            u'providers': providers,
            u'hotwordtoken': config[u'hotwordtoken'],
            u'hotwordrecordings': self.__get_hotword_recording_status(),
            u'hotwordmodel': config[u'hotwordmodel'] is not None,
            u'serviceenabled': config[u'serviceenabled'],
            u'servicerunning': self.__speech_recognition_task is not None,
            u'testing': self.__speech_recognition_task is not None and self.__speech_recognition_task.is_test_enabled(),
            u'hotwordtraining': self.__training_task is not None
        }

    def __start_speech_recognition_task(self, test=False):
        """
        Start spech recognition task if everything is configured

        Args:
            test (bool): True if test is enabled

        Return:
            bool: True if speech recognition started
        """
        #get config
        config = self._get_config()

        #check params
        if not config[u'serviceenabled'] and not test:
            self.logger.debug(u'Unable to start speech recognition: service is disabled')
            return False
        if self.__speech_recognition_task is not None:
            self.logger.debug(u'Unable to start speech recognition: process is already running')
            return False
        if config[u'hotwordmodel'] is None or not os.path.exists(config[u'hotwordmodel']):
            self.logger.debug(u'Unable to start speech recognition: invalid voice model')
            return False
        if config[u'providerid'] is None:
            self.logger.debug(u'Unable to start speech recognition: STT provider is not configured')
            return False

        #start speech recognition
        #TODO handle audio gain and sensitivity
        provider_token = config[u'providerapikeys'][str(config[u'providerid'])]
        self.logger.debug(u'provider_token=%s' % provider_token)
        self.logger.debug(u'apikeys:%s providerid:%s' % (config[u'providerapikeys'], config[u'providerid']))
        self.__speech_recognition_task = SpeechRecognitionProcess(self.logger, config[u'hotwordmodel'], self.events, provider_token)
        if test:
            #enable test mode
            self.__speech_recognition_task.enable_test(self.hotwordDetectedEvent)
        self.__speech_recognition_task.start()

        return True

    def __stop_speech_recognition_task(self):
        """
        Stop speech recognition task

        Return:
            bool: True if speech recognition was running
        """
        if self.__speech_recognition_task is not None:
            self.__speech_recognition_task.stop()
            self.__speech_recognition_task = None

            return True

        return False

    def __restart_speech_recognition_task(self):
        """
        Restart speech recognition task (doesn't start if it wasn't started)
        """
        if self.__speech_recognition_task is not None:
            #stop task
            self.__stop_speech_recognition_task()
            #start task differing startup to make sure audio resource is free
            t = Timer(10.0, self.__start_speech_recognition_task)
            t.start()

    def __get_hotword_recording_status(self):
        """
        Return hotword recording status

        Return:
            tuple: tuple of 3 values representing current hotword recording status::
                (True, False, False)
        """
        config = self._get_config()
        record1 = config[u'hotwordfiles'][0] is not None and os.path.exists(config[u'hotwordfiles'][0])
        record2 = False
        record3 = False
        if record1:
            record2 = config[u'hotwordfiles'][1] is not None and os.path.exists(config[u'hotwordfiles'][1])
            if record2:
                record3 = config[u'hotwordfiles'][2] is not None and os.path.exists(config[u'hotwordfiles'][2])

        return (record1, record2, record3)

    def __check_provider(self, provider_id):
        """
        Check if provider is valid

        Args:
            provider_id (int): provider id

        Return:
            bool: True if provider is valid
        """
        for provider in self.PROVIDERS:
            if provider[u'id']==provider_id and provider[u'enabled']:
                #provider is valid
                return True

        #provider was not found or is not enabled
        return False

    def set_provider(self, provider_id, apikey):
        """
        Set speechtotext provider

        Args:
            provider_id (int): provider id
            apikey (string): provider apikey

        Return:
            bool: True if action succeed
        """
        if provider_id is None:
            raise MissingParameter(u'Parameter provider is missing')
        if not self.__check_provider(provider_id):
            raise InvalidParameter(u'Specified provider is not valid. Please check list of supported provider.')
        if apikey is None or len(apikey.strip())==0:
            raise MissingParameter(u'Parameter apikey is missing')

        #save config
        config = self._get_config()
        #need to convert provider id to string because json does not support int as map/dict key
        provider_id_str = str(provider_id)
        providersapikeys = self._get_config_field(u'providerapikeys')
        providersapikeys[provider_id_str] = apikey
        config = {
            u'providerid': provider_id_str,
            u'providerapikeys': providersapikeys
        }
        if not self._update_config(config):
            return False

        #restart speech recognition task
        self.__restart_speech_recognition_task()

        return True

    def set_hotword_token(self, token):
        """
        Set hot-word api token

        Args:
            token (string): snowboy api token

        Return:
            bool: True if token saved successfully
        """
        #check params
        if self.__training_task is not None:
            raise CommandError(u'This action is disabled during voice model building')

        #save token
        if not self._set_config_field(u'hotwordtoken', token):
            return False

        return True

    def __build_hotword(self):
        """
        Launch hotword training process
        """
        #check params
        if self.__training_task is not None:
            self.logger.debug(u'Try to launch voice model training while one is already running')
            raise CommandError(u'This action is disabled during voice model building')

        #get config
        config = self._get_config()

        #launch model training
        self.__training_task = BuildPersonalVoiceModelTask(config[u'hotwordtoken'], config[u'hotwordfiles'], self.__end_of_training, self.logger)
        self.__training_task.start()

    def __end_of_training(self, error, voice_model_path):
        """
        Called when training process is terminated

        Args:
            error (string): Error message if error occured, None if no error occured
            voice_model_path (string): path to generated voice model
        """
        #reset variables
        self.__training_task = None

        #check errors
        if error is not None:
            #send error event to ui
            self.training_ko_event.send(to=u'rpc', params={u'error': error})
            return
            
        #finalize training
        try:
            #get hotwords config
            hotwords_files = self._get_config_field(u'hotwordsfiles')

            #move files
            model = os.path.join(self.VOICE_MODEL_PATH, 'voice_model.pmdl')
            os.rename(voice_model_path, model)
            record1 = os.path.join(self.VOICE_MODEL_PATH, 'record1.wav')
            os.rename(hotwords_files[0], record1)
            record2 = os.path.join(self.VOICE_MODEL_PATH, 'record2.wav')
            os.rename(hotwords_files[1], record2)
            record3 = os.path.join(self.VOICE_MODEL_PATH, 'record3.wav')
            os.rename(hotwords_files[2], record3)

            #update config
            hotwords_files[0] = record1
            hotwords_files[1] = record2
            hotwords_files[2] = record3
            config = {
                u'hotwordsfiles': hotwords_files,
                u'hotwordmodel': model
            }
            if not self._update_config(config):
                raise Exception(u'Unable to update config')

            #send event to ui model is generated
            self.training_ok_event.send(to=u'rpc')

        except:
            self.logger.exception('Exception during model training:')

            #send error event to ui
            self.training_ko_event.send(to=u'rpc', params={u'error': u'Error occured during model training'})
            return

    def record_hotword(self):
        """
        Record hot-word and when all recordings are done, train personal model

        Return:
            tuple: status of hotword recordings::
                (True, False, False)
        """
        #check params
        if self.__training_task is not None:
            raise CommandError(u'This action is disabled during voice model building')

        #stop speech recognition thread if running
        in_use = self.__stop_speech_recognition_task()

        #record sound
        if not in_use:
            #claim for resource
            self.acquire_resource(u'audio.capture')
        record = self.sox.record_sound(Sox.CHANNELS_STEREO, Sox.RATE_16K, timeout=5.0)
        if not in_use:
            #release resource
            self.release_resource(u'audio.capture')

        #save recording
        record1, record2, record3 = self.__get_hotword_recording_status()
        train = False
        hotwords_files = self._get_config_field(u'hotwordsfiles')
        if not record1:
            hotword_files[0] = record
        elif not record2:
            hotword_files[1] = record
        elif not record3:
            hotword_files[2] = record
            train = True
        self._set_config_field(u'hotwordsfiles', hotwords_files)

        #train if all recordings are ready
        if train:
            #launch hotword building
            self.__build_hotword()

        return self.__get_hotword_recording_status()

    def build_hotword(self):
        """
        Launch hotword model training manually
        """
        #check params
        if self.__training_task is not None:
            raise CommandError(u'This action is disabled during voice model building')

        #launch hotword building
        self.__build_hotword()

    def reset_hotword(self):
        """
        Clear all recorded file and personnal model
        """
        #check params
        if self.__training_task is not None:
            raise CommandError(u'This action is disabled during voice model building')

        #stop speech recognition task
        self.__stop_speech_recognition_task()

        #reset hotword
        try:
            config = self._get_config()
            if config[u'hotwordfiles'][0] and os.path.exists(config[u'hotwordfiles'][0]):
                os.remove(config[u'hotwordfiles'][0])
                config[u'hotwordfiles'][0] = None
            if config[u'hotwordfiles'][1] and os.path.exists(config[u'hotwordfiles'][1]):
                os.remove(config[u'hotwordfiles'][1])
                config[u'hotwordfiles'][1] = None
            if config[u'hotwordfiles'][2] and os.path.exists(config[u'hotwordfiles'][2]):
                os.remove(config[u'hotwordfiles'][2])
                config[u'hotwordfiles'][2] = None
            if config[u'hotwordmodel'] and os.path.exists(config[u'hotwordmodel']):
                os.remove(config[u'hotwordmodel'])
                config[u'hotwordmodel'] = None

            #update config
            if not self._update_config(config):
                raise Exception(u'Unable to update config')

        except:
            self.logger.exception(u'Error occured during hotword resetting:')
            raise CommandError(u'Internal error during reset')

        return True

    def start_hotword_test(self):
        """
        Test hotword detection
        """
        if not self.__speech_recognition_task:
            #speechrecognition task is not running, start it
            if not self.acquire_resource(u'audio.capture'):
                raise CommandError(u'Unable to start test')
            self.__stop_task_after_test = True

        #and enable test
        self.__speech_recognition_task.enable_test()

    def stop_hotword_test(self):
        """
        Stop hotword test
        """
        #disable test
        self.__speech_recognition_task.disable_test()

        #and stop task if necessary 
        if self.__stop_task_after_test:
            #task wasn't running before test, stop it
            self.release_resource(u'audio.capture')
            self.__stop_task_after_test = False

    def enable_service(self):
        """
        Enable service
        """
        #update configuration
        if not self._set_config_field(u'serviceenabled', True):
            return False

        #start speech recognition
        self.acquire_resource(u'audio.capture')

        return True

    def disable_service(self):
        """
        Disable service
        """
        #update configuration
        if not self._set_config_field(u'serviceenabled', False):
            return False

        #start speech recognition
        self.release_resource(u'audio.capture')

        return True

    def _release_resource(self, resource, extra):
        """
        Release resource

        Args:
            resource (string): resource name
            extra (dict): extra parameters

        Return:
            bool: True if resource released
        """
        self.__stop_speech_recognition_task()
        #wait few time to make sure resource is released
        time.sleep(1.0)

        return True

    def _acquire_resource(self, resource, extra):
        """
        Acquire resource

        Args:
            resource (string): resource name
            extra (dict): extra parameters

        Return:
            bool: True if resource acquired
        """
        return self.__start_speech_recognition_task()



