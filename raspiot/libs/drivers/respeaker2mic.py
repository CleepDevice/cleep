#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.console import Console
from raspiot.utils import InvalidParameter, MissingParameter
import raspiot.libs.drivers.respeaker2mic.apa102 as apa102
import logging
import os
import shutil

class Respeaker2mic(AdvancedConsole):
    """
    Respeaker 2mic hardware support
    """

    COLOR_BLACK = [0, 0, 0]
    COLOR_WHITE = [255,255,255]
    COLOR_RED = [255, 0, 0]
    COLOR_GREEN = [0, 255, 0]
    COLOR_BLUE = [0, 0, 255]
    COLOR_YELLOW = [255, 255, 0]
    COLOR_CYAN = [0, 255, 255]
    COLOR_MAGENTA = [255, 0, 255]

    LED_OFF = COLOR_BLACK

    RESPEAKER_REPO = u'https://github.com/respeaker/seeed-voicecard.git'
    TMP_DIR = u'/tmp/respeaker'
    DRIVER_PATH = u'/boot/overlays/seeed-2mic-voicecard.dtbo'
    
    def __init__(self):
        """
        Constructor
        """
        AdvancedConsole.__init__(self)

        #members
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)
        self.leds_driver = apa102.APA102(num_led=3)
        self.leds_colors = [
            [0,0,0],
            [0,0,0],
            [0,0,0]
        ]
        self.__driver_process = None
        self.__process_status_callback = None
        self.__process_terminated_callback = None

    def is_installing(self):
        """
        Return True if driver process (install or uninstall) is running

        Return:
            bool: True if driver process is running
        """
        if self.__driver_process is None:
            return False

        return True

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
            self.logger.debug(u'Driver installation stderr: %s' % stderr)

        #callback
        self.__process_status_callback(stdout, stderr)

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

        #callback
        self.__process_terminated_callback(return_code, killed)

        #reset
        self.__driver_process = None
        self.__process_status_callback = None
        self.__process_terminated_callback = None

    def __prepare_driver_process(self):
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
            raise Exception(u'Unable to install respeaker driver: respeaker repository seems no available.')
        if not os.path.exists(os.path.join(self.TMP_DIR, u'uninstall.sh')):
            self.logger.error('Install.sh script does not exists. Unable to install respeaker 2mic driver')
            raise Exception(u'Unable to install respeaker driver: install script does not exist.')

    def install_driver(self, install_status_callback, install_terminated_callback):
        """
        Install respeaker 2mic driver. At end of installation device reboot is required

        Args:
            install_status_callback (function): callback during installation process (useful to save output) (args: stdout(string), stderr(string))
            install_terminated_callback (function): callback when installation is over (args: command return code(string), killed status (bool))

        Return:
            bool: True if driver installation is running
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
        if self.__driver_process is not None:
            raise Exception(u'Driver process is already running. Stop it before launching installation')

        #save parameters
        self.__process_status_callback = install_status_callback
        self.__process_terminated_callback = install_terminated_callback

        #prepare install
        self.__prepare_driver_process()
        if not os.path.exists(os.path.join(self.TMP_DIR, u'install.sh')):
            self.logger.error('Install.sh script does not exists. Unable to install respeaker 2mic driver')
            raise Exception(u'Unable to install respeaker driver: install script does not exist.')

        #build and install driver
        command = u'%s 2mic' % (os.path.join(self.TMP_DIR, u'install.sh'))
        self.logger.debug('Respeaker driver install command: %s' % command)
        self.__driver_process = EndlessConsole(command, self.__process_status_callback, self.__process_terminated_callback)
        self.__driver_process.start()

    def uninstall_driver(self, uninstall_status_callback, uninstall_terminated_callback):
        """
        Uninstall respeaker 2mic driver. At end of uninstallation device reboot is required

        Args:
            uninstall_status_callback (function): callback during uninstallation process (useful to save output) (args: stdout(string), stderr(string))
            uninstall_terminated_callback (function): callback when uninstallation is over (args: command return code(string), killed status (bool))

        Return:
            bool: True if driver installation is running
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
        if self.__driver_process is not None:
            raise Exception(u'Driver process is already running. Stop it before launching uninstallation')

        #save parameters
        self.__process_status_callback = uninstall_status_callback
        self.__process_terminated_callback = uninstall_terminated_callback

        #prepare uninstall
        self.__prepare_driver_process()
        if not os.path.exists(os.path.join(self.TMP_DIR, u'uninstall.sh')):
            self.logger.error('Uninstall.sh script does not exists. Unable to install respeaker 2mic driver')
            raise Exception(u'Unable to uninstall respeaker driver: uninstall script does not exist.')

        #uninstall driver
        command = u'%s 2mic' % (os.path.join(self.TMP_DIR, u'uninstall.sh'))
        self.logger.debug('Respeaker driver uninstall command: %s' % command)
        self.__driver_process = EndlessConsole(command, self.__process_status_callback, self.__process_terminated_callback)
        self.__driver_process.start()

    def stop_driver_process(self):
        """
        Stop running driver process (install or uninstall) if running

        Return:
            bool: True if running process was stopped, False if no process was running
        """
        if self.__driver_process is not None:
            self.__driver_process.kill()
            self.__driver_process = None

            return True

        #no driver process running
        return False

    def configure_button(self, send_command_callback):
        """
        Configure button on GPIOs module

        Return:
            uuid: button device uuid, useful to catch its event on module event_received function

        Raise:
            Exception
        """
	#configure gpio
        params = {
            u'name': u'respeaker_button',
            u'gpio': u'GPIO17',
            u'mode': u'in',
            u'keep': False,
            u'reverted': False
        }
        resp_gpio = send_command_callback(u'add_gpio', u'gpios', { u'mode':u'out', u'keep':False, u'reverted':False})
        if resp_gpio[u'error']:
            raise Exception(resp_gpio[u'message'])

        return resp_gpio[u'data'][u'uuid']

    def __set_led(self, led_id, color, brightness=10):
        """
        Configure led color and brightness

        Args:
            led_id (int): led identifier
            color (list): RGB tuple [0,0,0]
            brightness (int): brightness percentage (default 10%)
        """
        if led_id<0 or led_id>2:
            raise InvalidParameter(u'Led_id must be 0..2')
        if brightness<0 or brightness>100:
            raise InvalidParameter(u'Brightness must be 0..100')
        if len(color)==4 and (color[3]<0 or color[3]>100):
            raise InvalidParameter(u'Brightness must be 0..100')

        #set led color
        if len(color)==4:
            #force brightness
            brightness = color[3]
        self.logger.debug(u'Set led%s color R=%s G=%s B=%s with Brightness=%s' % (led_id, color[0], color[1], color[2], brightness))
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


if __name__ == "__main__":
    #driver tests. Tests are not in tests directory because hardware is not always connected
    import time
    respeaker = Respeaker2mic()
    respeaker.turn_on_leds(respeaker.COLOR_WHITE, respeaker.COLOR_WHITE, respeaker.COLOR_WHITE)
    time.sleep(1.0)
    respeaker.turn_on_leds(respeaker.COLOR_RED, respeaker.COLOR_RED, respeaker.COLOR_RED)
    time.sleep(1.0)
    respeaker.turn_on_leds(respeaker.COLOR_GREEN, respeaker.COLOR_GREEN, respeaker.COLOR_GREEN)
    time.sleep(1.0)
    respeaker.turn_on_leds(respeaker.COLOR_BLUE, respeaker.COLOR_BLUE, respeaker.COLOR_BLUE)
    time.sleep(1.0)
    respeaker.turn_on_leds(respeaker.COLOR_YELLOW, respeaker.COLOR_YELLOW, respeaker.COLOR_YELLOW)
    time.sleep(1.0)
    respeaker.turn_on_leds(respeaker.COLOR_CYAN, respeaker.COLOR_CYAN, respeaker.COLOR_CYAN)
    time.sleep(1.0)
    respeaker.turn_on_leds(respeaker.COLOR_MAGENTA, respeaker.COLOR_MAGENTA, respeaker.COLOR_MAGENTA)
    time.sleep(1.0)
    respeaker.turn_off_leds()

    for i in range(3):
        respeaker.turn_on_leds(respeaker.COLOR_RED, respeaker.LED_OFF, respeaker.LED_OFF)
        time.sleep(1.0)
        respeaker.turn_on_leds(respeaker.LED_OFF, respeaker.COLOR_RED, respeaker.LED_OFF)
        time.sleep(1.0)
        respeaker.turn_on_leds(respeaker.LED_OFF, respeaker.LED_OFF, respeaker.COLOR_RED)
        time.sleep(1.0)
    respeaker.turn_off_leds()
