#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.console import AdvancedConsole
from raspiot.utils import InvalidParameter, CommandError
import raspiot.libs.drivers.respeaker2mic.apa102 as apa102
import logging

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

    def is_installed(self):
        """
        Return driver installation status

        Return:
            bool: True if driver already installed
        """
        pass

    def install_driver(self):
        """
        Install respeaker 2mic driver

        Return:
            bool: True if driver installed successfully
        """
        pass

    def configure_button(self, send_command_callback):
        """
        Configure button on GPIOs module

        Return:
            uuid: button device uuid, useful to catch its event on module event_received function

        Raise:
            CommandError
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
            raise CommandError(resp_gpio[u'message'])

        return resp_gpio[u'data'][u'uuid']

    def __set_led(self, led_id, color, brightness=10):
        """
        Configure led color and brightness

        Args:
            led_id (int): led identifier
            color (list): RGB tuple [0,0,0]
            brightness (int): percentage
        """
        if led_id<0 or led_id>2:
            raise InvalidParameter(u'Led_id must be 0..2')
        if brightness<0 or brightness>100:
            raise InvalidParameter(u'Brightness must be 0..100')

        #set led color
        self.logger.debug(u'Set led%s color R=%s G=%s B=%s with Bright=%s' % (led_id, color[0], color[1], color[2], brightness))
        self.leds_driver.set_pixel(led_id, color[0], color[1], color[2], brightness)

    def turn_on_leds(self, led1=None, led2=None, led3=None):
        """
        Turn on leds with specified color. None value does nothing on led

        Args:
            led1 (list): RGB tuple [0,0,0]
            led2 (list): RGB tuple [0,0,0]
            led3 (list): RGB tuple [0,0,0]
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
