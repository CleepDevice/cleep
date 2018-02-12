#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
import os
import uuid
from threading import Thread
import copy
from raspiot.raspiot import RaspIotRenderer
from raspiot.profiles import SpeechRecognitionHotwordProfile, SpeechRecognitionCommandProfile
from raspiot.utils import CommandError, InvalidParameter, MissingParameter
import raspiot.libs.drivers.apa102 as apa102

__all__ = ['Respeaker2mic']


class LedsProfileTask(Thread):
    """
    Class in charge of running leds profile
    """
    def __init__(self, respeaker2mic_instance, profile, terminated_callback):
        """
        Constructor

        Args:
            respeaker2mic_instance (Respeaker2mic): respeaker2mic instance
            profile (dict): profile data
        """
        Thread.__init__(self)
        Thread.daemon = True

        #members
        #self.logger = respeaker2mic_instance.logger
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        self.respeaker2mic = respeaker2mic_instance
        self.profile = profile
        self.terminated_callback = terminated_callback
        self.running = True
        self.test = False

    def stop(self):
        """
        Stop task
        """
        self.running = False

    def enable_test(self):
        """
        Set test to True, do not use repeat profile value
        """
        self.test = True

    def get_color(self, color_str):
        if color_str=='white':
            return copy.copy(self.respeaker2mic.COLOR_WHITE)
        elif color_str=='red':
            return copy.copy(self.respeaker2mic.COLOR_RED)
        elif color_str=='green':
            return copy.copy(self.respeaker2mic.COLOR_GREEN)
        elif color_str=='blue':
            return copy.copy(self.respeaker2mic.COLOR_BLUE)
        elif color_str=='yellow':
            return copy.copy(self.respeaker2mic.COLOR_YELLOW)
        elif color_str=='magenta':
            return copy.copy(self.respeaker2mic.COLOR_MAGENTA)
        elif color_str=='cyan':
            return copy.copy(self.respeaker2mic.COLOR_CYAN)
        else:
            return copy.copy(self.respeaker2mic.COLOR_BLACK)

    def __process_animation(self):
        """
        Process profile animation
        """
        for action in self.profile[u'actions']:
            #stop statement if necessary
            if not self.running:
                break

            #run action
            self.logger.debug('Action: %s' % action)
            if action[u'action'] in (1,2,3):
                #set led1 or led2 or led3
                #prepare color and brightness
                color = self.get_color(action[u'color'])
                color.append(action[u'brightness'])
                #turn on leds
                if action[u'action']==1:
                    self.respeaker2mic.turn_on_leds(led1=color)
                elif action[u'action']==2:
                    self.respeaker2mic.turn_on_leds(led2=color)
                else:
                    self.respeaker2mic.turn_on_leds(led3=color)

            elif action[u'action']==4:
                #set all leds
                #prepare color and brightness
                color = self.get_color(action[u'color'])
                color.append(action[u'brightness'])
                #turn on leds
                self.respeaker2mic.turn_on_leds(led1=color, led2=color, led3=color)

            elif action[u'action']==5:
                #pause
                count = int(action[u'pause']/50)
                for i in range(count):
                    if not self.running:
                        break
                    time.sleep(0.05)

    def run(self):
        """
        Run task
        """
        #compute repeat
        if self.test:
            #process animation once
            self.__process_animation()

        elif self.profile[u'repeat']==self.respeaker2mic.REPEAT_INF:
            #process indefinitely
            while self.running:
                self.__process_animation()

        else:
            #process amount of times
            for i in range(self.profile[u'repeat']):
                if not self.running:
                    break
                self.__process_animation()

        #end animation turning off everything
        self.respeaker2mic.turn_off_leds()

        #end of process
        self.terminated_callback()



class Respeaker2mic(RaspIotRenderer):
    """
    Respeaker2mic module handles respeaker2mic configuration:
        - led effect,
        - button behaviour,
        - driver installation/uninstallation

    Resources:
        - http://wiki.seeed.cc/ReSpeaker_2_Mics_Pi_HAT/
    """

    MODULE_CONFIG_FILE = u'respeaker2mic.conf'
    MODULE_DEPS = [u'gpios']
    MODULE_DESCRIPTION = u'Configure your Respeaker2mic hardware'
    MODULE_LOCKED = False
    MODULE_TAGS = [u'audio', u'mic']
    MODULE_COUNTRY = None
    MODULE_LINK = None

    RENDERER_PROFILES = [SpeechRecognitionHotwordProfile, SpeechRecognitionCommandProfile]
    RENDERER_TYPE = u'leds'

    LEDS_PROFILE_BREATHE_BLUE = u'1'
    LEDS_PROFILE_BLINK_RED = u'2'
    LEDS_PROFILE_OK_GREEN = u'3'
    LEDS_PROFILE_SEARCH_YELLOW = u'4'

    DEFAULT_CONFIG = {
        u'button_gpio_uuid': None,
        u'leds_profiles' : [
            {
                u'name': 'Breathe (blue)',
                u'uuid': u'1',
                u'repeat': 99,
                u'default': True,
                u'actions': [
                    {"action": 4, "color": "blue", "pause": 0, "brightness": 10}, 
                    {"action": 5, "color": None, "pause": 100, "brightness": 0}, 
                    {"action": 4, "color": "blue", "pause": 0, "brightness": 20}, 
                    {"action": 5, "color": None, "pause": 100, "brightness": 0}, 
                    {"action": 4, "color": "blue", "pause": 0, "brightness": 30}, 
                    {"action": 5, "color": None, "pause": 100, "brightness": 0}, 
                    {"action": 4, "color": "blue", "pause": 0, "brightness": 40}, 
                    {"action": 5, "color": None, "pause": 100, "brightness": 0}, 
                    {"action": 4, "color": "blue", "pause": 0, "brightness": 50}, 
                    {"action": 5, "color": None, "pause": 100, "brightness": 0}, 
                    {"action": 4, "color": "blue", "pause": 0, "brightness": 60}, 
                    {"action": 5, "color": None, "pause": 100, "brightness": 0}, 
                    {"action": 4, "color": "blue", "pause": 0, "brightness": 70}, 
                    {"action": 5, "color": None, "pause": 100, "brightness": 0}, 
                    {"action": 4, "color": "blue", "pause": 0, "brightness": 80}, 
                    {"action": 5, "color": None, "pause": 100, "brightness": 0}, 
                    {"action": 4, "color": "blue", "pause": 0, "brightness": 90}, 
                    {"action": 5, "color": None, "pause": 100, "brightness": 0}, 
                    {"action": 4, "color": "blue", "pause": 0, "brightness": 100}, 
                    {"action": 5, "color": None, "pause": 100, "brightness": 0}, 
                    {"action": 4, "color": "blue", "pause": 0, "brightness": 90}, 
                    {"action": 5, "color": None, "pause": 100, "brightness": 0}, 
                    {"action": 4, "color": "blue", "pause": 0, "brightness": 80}, 
                    {"action": 5, "color": None, "pause": 100, "brightness": 0}, 
                    {"action": 4, "color": "blue", "pause": 0, "brightness": 70}, 
                    {"action": 5, "color": None, "pause": 100, "brightness": 0}, 
                    {"action": 4, "color": "blue", "pause": 0, "brightness": 60}, 
                    {"action": 5, "color": None, "pause": 100, "brightness": 0}, 
                    {"action": 4, "color": "blue", "pause": 0, "brightness": 50}, 
                    {"action": 5, "color": None, "pause": 100, "brightness": 0}, 
                    {"action": 4, "color": "blue", "pause": 0, "brightness": 40}, 
                    {"action": 5, "color": None, "pause": 100, "brightness": 0}, 
                    {"action": 4, "color": "blue", "pause": 0, "brightness": 30}, 
                    {"action": 5, "color": None, "pause": 100, "brightness": 0}, 
                    {"action": 4, "color": "blue", "pause": 0, "brightness": 20}, 
                    {"action": 5, "color": None, "pause": 100, "brightness": 0}, 
                    {"action": 4, "color": "blue", "pause": 0, "brightness": 10}
                ]
            }, {
                u'name': 'Blink (red)',
                u'uuid': u'2',
                u'repeat': 8,
                u'default': True,
                u'actions': [
                    {"action": 4, "color": "red", "pause": 0, "brightness": 60},
                    {"action": 5, "color": None, "pause": 100, "brightness": 0}, 
                    {"action": 4, "color": "black", "pause": 0, "brightness": 60},
                    {"action": 5, "color": None, "pause": 100, "brightness": 0}
                ]
            }, {
                u'name': 'Ok (green)',
                u'uuid': u'3',
                u'repeat': 3,
                u'default': True,
                u'actions': [
                    {"action": 4, "color": "green", "pause": 0, "brightness": 60},
                    {"action": 5, "color": None, "pause": 500, "brightness": 0}
                ]
            }, {
                u'name': 'Search (yellow)',
                u'uuid': u'4',
                u'repeat': 99,
                u'default': True,
                u'actions': [
                    {"action": 1, "color": "yellow", "pause": 0, "brightness": 60},
                    {"action": 5, "color": None, "pause": 100, "brightness": 0},
                    {"action": 1, "color": "black", "pause": 0, "brightness": 60},
                    {"action": 2, "color": "yellow", "pause": 0, "brightness": 60},
                    {"action": 5, "color": None, "pause": 100, "brightness": 0},
                    {"action": 2, "color": "black", "pause": 0, "brightness": 60},
                    {"action": 3, "color": "yellow", "pause": 0, "brightness": 60},
                    {"action": 5, "color": None, "pause": 100, "brightness": 0},
                    {"action": 3, "color": "black", "pause": 0, "brightness": 60},
                    {"action": 2, "color": "yellow", "pause": 0, "brightness": 60},
                    {"action": 5, "color": None, "pause": 100, "brightness": 0},
                    {"action": 2, "color": "black", "pause": 0, "brightness": 60}
                ]
            }
        ]
    }

    RESPEAKER_REPO = u'https://github.com/respeaker/seeed-voicecard.git'
    TMP_DIR = u'/tmp/respeaker'
    DRIVER_PATH = u'/boot/overlays/seeed-2mic-voicecard.dtbo'

    COLOR_BLACK = [0, 0, 0]
    COLOR_WHITE = [255,255,255]
    COLOR_RED = [255, 0, 0]
    COLOR_GREEN = [0, 255, 0]
    COLOR_BLUE = [0, 0, 255]
    COLOR_YELLOW = [255, 255, 0]
    COLOR_CYAN = [0, 255, 255]
    COLOR_MAGENTA = [255, 0, 255]

    LED_OFF = COLOR_BLACK
    LED_ON = COLOR_WHITE

    REPEAT_NONE = 0
    REPEAT_1 = 1
    REPEAT_2 = 2
    REPEAT_3 = 3
    REPEAT_4 = 4
    REPEAT_5 = 5
    REPEAT_INF = 99

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): flag to set debug level to logger
        """
        #init
        RaspIotRenderer.__init__(self, bootstrap, debug_enabled)

        #members
        self.leds_driver = apa102.APA102(num_led=3)
        self.__driver_task = None
        self.__leds_profile_task = None

    def _configure(self):
        """
        Configure module
        """
        #configure button
        if self._config[u'button_gpio_uuid'] is None:
            self.__configure_button()

        #turn off leds at startup
        self.turn_off_leds()

    def __configure_button(self):
        """
        Configure embedded respeaker button reserving GPIO12 on gpio module

        Note:
            https://github.com/respeaker/seeed-voicecard

        Return:
            bool: True if button configured
        """
        #configure gpio
        params = { 
            u'name': u'button_respeaker2mic',
            u'gpio': u'GPIO17',
            u'mode': u'input',
            u'keep': False,
            u'reverted': False
        }   
        resp_gpio = self.send_command(u'add_gpio', u'gpios', params)
        if resp_gpio[u'error']:
	    self.logger.error(u'Respeaker2mic button not configured: %s' % resp_gpio)
            return False
        resp_gpio = resp_gpio[u'data'] 

        #save device uuid in config
        config = self._get_config()
        config[u'button_gpio_uuid'] = resp_gpio[u'uuid']
        if not self._save_config(config):
            self.logger.error(u'Unable to save config')
            return False

        return True

    def get_module_config(self):
        """
        Return module configuration
        """
        return {
            u'driverprocessing': self.__driver_task is not None,
            u'driverinstalled': self.is_installed(),
            u'ledsprofiles': self._config[u'leds_profiles']
        }

    def is_installed(self):
        """ 
        Return driver installation status

        Return:
            bool: True if driver already installed
        """
        #check if drivers installed
        if os.path.exists(self.DRIVER_PATH):
            return True

        return False

    def __prepare_driver_task(self):
        """
        Prepare driver process (install or uninstall).
        It downloads source and make sure everything is clean before starting

        Raise:
            Exception
        """
        #make sure directory does not exist
        if os.path.exists(self.TMP_DIR):
            shutil.rmtree(self.TMP_DIR)

        #get sources
        console = Console()
        res = console.command(u'/usr/bin/git "%s" /tmp/respeaker-driver' % self.RESPEAKER_REPO, timeout=30)
        if res[u'error'] or res[u'killed']:
            self.logger.error(u'Error occured during git command: %s' % res)
            raise Exception(u'Unable to install or uninstall respeaker driver: respeaker repository seems no available.')
        if not os.path.exists(os.path.join(self.TMP_DIR, u'install.sh')) or not os.path.exists(os.path.join(self.TMP_DIR, u'uninstall.sh')):
            self.logger.error('Install.sh or uninstall.sh scripts do not exists.')
            raise Exception(u'Unable to install or uninstall respeaker driver: some scripts do not exist.')

    def __process_status_callback(self, stdout, stderr):
        """
        Called when running process received something on stdout/stderr

        Args:
            stdout (string): command stdout string
            stderr (string): command stderr string
        """
        #log for debug installation logs
        if stdout:
            self.logger.debug(u'Driver installation stdout: %s' % stdout)
        if stderr:
            self.logger.error(u'Driver installation stderr: %s' % stderr)

    def __process_terminated_callback(self, return_code, killed):
        """
        Called when running process is terminated

        Args:
            return_code (string): command return code
            killed (bool): if True command was killed
        """
        #clean everything
        if os.path.exists(self.TMP_DIR):
            shutil.rmtree(self.TMP_DIR)

        #reset
        self.__driver_task = None

	#send terminated event
	#TODO

    def install_driver(self):
        """
        Install respeaker 2mic driver. At end of installation device reboot is required
        """
        #check params
        if install_status_callback is None:
            raise MissingParameter(u'Parameter install_status_callback is missing')
        if not callable(install_status_callback):
            raise InvalidParameter(u'Parameter install_status_callback must be a callback')
        if install_terminated_callback is None:
            raise MissingParameter(u'Parameter install_terminated_callback is missing')
        if not callable(install_terminated_callback):
            raise InvalidParameter(u'Parameter install_terminated_callback must be a callback')
        if self.__driver_task is not None:
            raise Exception(u'Driver process is already running. Stop it before launching installation')
         
        #prepare install
        self.__prepare_driver_task()
  
        #build and install driver
        command = u'%s 2mic' % (os.path.join(self.TMP_DIR, u'install.sh'))
        self.logger.debug('Respeaker driver install command: %s' % command)
        self.__driver_task = EndlessConsole(command, self.__process_status_callback, self.__process_terminated_callback)
        self.__driver_task.start()

    def uninstall_driver(self):
        """
        Uninstall respeaker 2mic driver. At end of uninstallation device reboot is required
        """
        #check params
        if uninstall_status_callback is None:
            raise MissingParameter(u'Parameter uninstall_status_callback is missing')
        if not callable(uninstall_status_callback):
            raise InvalidParameter(u'Parameter uninstall_status_callback must be a callback')
        if uninstall_terminated_callback is None:
            raise MissingParameter(u'Parameter uninstall_terminated_callback is missing')
        if not callable(uninstall_terminated_callback):
            raise InvalidParameter(u'Parameter uninstall_terminated_callback must be a callback')
        if self.__driver_task is not None:
            raise Exception(u'Driver process is already running. Stop it before launching uninstallation')

        #prepare uninstall
        self.__prepare_driver_task()

        #uninstall driver
        command = u'%s 2mic' % (os.path.join(self.TMP_DIR, u'uninstall.sh'))
        self.logger.debug('Respeaker driver uninstall command: %s' % command)
        self.__driver_task = EndlessConsole(command, self.__process_status_callback, self.__process_terminated_callback)
        self.__driver_task.start()

    def stop_driver_task(self):
        """
        Stop running driver task (install or uninstall) if running

        Return:
            bool: True if running process was stopped, False if no process was running
        """
        if self.__driver_task is not None:
            self.__driver_task.kill()
            self.__driver_task = None

            return True

        #no driver process running
        return False

    def __set_led(self, led_id, color, brightness=10):
        """
        Configure led color and brightness

        Args:
            led_id (int): led identifier (0..2)
            color (list): RGB tuple (0,0,0) or RGB+brightness value (0,0,0,0) [0..255]
            brightness (int): brightness percentage (default 10%) [0..100]
        """
        if led_id<0 or led_id>2:
            raise InvalidParameter(u'Led_id must be 0..2')
        if brightness<0 or brightness>100:
            raise InvalidParameter(u'Brightness must be 0..100')
        if len(color)==4 and (color[3]<0 or color[3]>100):
            raise InvalidParameter(u'Brightness must be 0..100')

	#handle brightness within color value
        if len(color)==4:
            #force brightness
            brightness = color[3]

        #set led color
        #self.logger.debug(u'Set led%s color R=%s G=%s B=%s with Brightness=%s' % (led_id, color[0], color[1], color[2], brightness))
        self.leds_driver.set_pixel(led_id, color[0], color[1], color[2], brightness)

    def turn_on_leds(self, led1=None, led2=None, led3=None):
        """
        Turn on leds with specified color. None value does nothing on led

        Args:
            led1 (list): RGB<Brightness> list [0..255, 0..255, 0.255, <0..100>]
            led2 (list): RGB<Brightness> list [0..255, 0..255, 0.255, <0..100>]
            led3 (list): RGB<Brightness> list [0..255, 0..255, 0.255, <0..100>]
        """
        if led1 is not None:
            self.__set_led(0, led1)
        if led2 is not None:
            self.__set_led(1, led2)
        if led3 is not None:
            self.__set_led(2, led3)

        #show leds
        self.leds_driver.show()

    def turn_off_leds(self, led1=True, led2=True, led3=True):
        """
        Turn off leds

        Args:
            led1 (bool): True to turn off led1
            led2 (bool): True to turn off led2
            led3 (bool): True to turn off led3
        """
        if led1:
            self.__set_led(0, self.LED_OFF)
        if led2:
            self.__set_led(1, self.LED_OFF)
        if led3:
            self.__set_led(2, self.LED_OFF)

        #show leds
        self.leds_driver.show()

    def add_leds_profile(self, name, repeat, actions):
        """
        Add leds profile

        Args:
            name (string): profile name
            repeat (int): repeat value (see REPEAT_XXX)
            actions (list): list of actions (see ACTION_XXX)
        """
        #check params
        if name is None or len(name)==0:
            raise MissingParameter(u'Parameter name is missing')
        if repeat is None:
            raise MissingParameter(u'Parameter repeat is missing')
        if repeat not in (self.REPEAT_0, self.REPEAT_1, self.REPEAT_2, self.REPEAT_3, self.REPEAT_4, self.REPEAT_5, self.REPEAT_INF):
            raise InvalidParameter(u'Parameter repeat is not valid. See available values')
        if actions is None:
            raise MissingParameter(u'Parameter actions is missing')
        if len(actions)==0:
            raise InvalidParameter(u'You must add at least one action in leds profile')

        #check name
        for profile in self._config[u'leds_profiles']:
            if profile[u'name']==name:
                raise InvalidParameter(u'Profile with same name already exists')

        #append new profile
        config = self._get_config()
        config[u'leds_profiles'].append({
            u'name': name,
            u'repeat': repeat,
            u'uuid': str(uuid.uuid4()),
            u'actions': actions,
            u'default': False
        })

        #save config
        if not self._save_config(config):
            raise CommandError(u'Unable to save leds profile')

        return True

    def remove_leds_profile(self, profile_uuid):
        """
        Remove specified leds profile

        Args:
            profile_uuid (string): leds profile uuid
        """
        #check parameters
        if self.__leds_profile_task is not None:
            raise CommandError(u'Leds profile is running. Please wait until end of it.')
        if profile_uuid is None or len(profile_uuid)==0:
            raise MissingParameter(u'Parameter profile_uuid is missing')
        if profile_uuid.isdigit():
            raise InvalidParameter(u'You can\'t delete default leds profiles')

        #get profile
        found = False
        config = self._get_config()
        for profile in config[u'leds_profiles']:
            if profile[u'uuid']==profile_uuid:
                #profile found, remove it
                found = True
                config[u'leds_profiles'].remove(profile)
                break

        #check found
        if not found:
            self.logger.error(u'Unable to remove profile with uuid %s' % profile_uuid)
            raise CommandError(u'Unable to remove profile')

        #save config
        if not self._save_config(config):
            raise CommandError(u'Unable to save config')

        return True

    def __leds_profile_task_terminated(self):
        """
        Reset leds profile task member when task is terminated
        """
        self.__leds_profile_task = None

    def test_leds_profile(self, profile_uuid):
        """
        Test specified leds profile (play once)

        Args:
            profile_uuid (string): leds profile uuid
        """
        #check parameters
        if self.__leds_profile_task is not None:
            raise CommandError(u'Leds profile is running. Please wait until end of it.')
        if profile_uuid is None or len(profile_uuid)==0:
            raise MissingParameter(u'Parameter profile_uuid is missing')

        #get profile
        selected_profile = None
        for profile in self._config[u'leds_profiles']:
            if profile[u'uuid']==profile_uuid:
                #profile found, stop statement
                selected_profile = profile
                break

        #check profile
        if selected_profile is None:
            self.logger.error(u'Unable to test leds profile with uuid %s' % profile_uuid)
            raise CommandError(u'Unable to test leds profile')

        #play profile
        self.__leds_profile_task = LedsProfileTask(self, selected_profile, self.__leds_profile_task_terminated)
        self.__leds_profile_task.enable_test()
        self.__leds_profile_task.start()

        return True

    def play_leds_profile(self, profile_uuid):
        """
        Play specified leds profile

        Args:
            profile_uuid (string): leds profile uuid
        """
        #check parameters
        if self.__leds_profile_task is not None:
            raise CommandError(u'Leds profile is running. Please wait until end of it.')
        if profile_uuid is None or len(profile_uuid)==0:
            raise MissingParameter(u'Parameter profile_uuid is missing')

        #get profile
        selected_profile = None
        for profile in self._config[u'leds_profiles']:
            if profile[u'uuid']==profile_uuid:
                #profile found, stop statement
                selected_profile = profile
                break

        #check profile
        if selected_profile is None:
            self.logger.error(u'Unable to play leds profile with uuid %s' % profile_uuid)
            raise CommandError(u'Unable to play leds profile')

        #play profile
        self.__leds_profile_task = LedsProfileTask(self, selected_profile, self.__leds_profile_task_terminated)
        self.__leds_profile_task.start()

        return True

    def __stop_leds_profile_task(self):
        """
        Stop leds profile task
        """
        if self.__leds_profile_task is not None:
            self.__leds_profile_task.stop()
            #make sure task is stopped (variable is resetted at end of task, see __leds_profile_task_terminated)
            time.sleep(0.25)

    def _render(self, profile):
        """
        Render handled profiles

        Args:
            profile (Profile): profile instance
        """
        self.logger.debug('Render profile: %s' % profile)
        if isinstance(profile, SpeechRecognitionHotwordProfile):
            #render hotword profile
            if profile.detected:
                #hotword detected: breathe
                self.__stop_leds_profile_task()
                self.play_leds_profile(self.LEDS_PROFILE_BREATHE_BLUE)
            else:
                #hotword released: search command
                self.__stop_leds_profile_task()
                self.play_leds_profile(self.LEDS_PROFILE_SEARCH_YELLOW)
        
        elif isinstance(profile, SpeechRecognitionCommandProfile):
            #render command profile
            self.__stop_leds_profile_task()
            if not profile.error:
                #command detected: ok green
                self.play_leds_profile(self.LEDS_PROFILE_OK_GREEN)
            else:
                #command error: blink red
                self.play_leds_profile(self.LEDS_PROFILE_BLINK_RED)
            

