#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from raspiot.bus import MessageRequest
from raspiot.raspiot import RaspIot
import time
import raspiot.libs.task
from raspiot.libs.ht1632c import HT1632C
import uuid
import socket

__all__ = ['Messageboard']

class Message():

    def __init__(self, message=None, start=None, end=None):
        self.message = message
        self.start = start
        self.end = end
        self.displayed_time = 0
        self.dynamic = False
        self.uuid = str(uuid.uuid4())

    def from_dict(self, message):
        """
        Load message from dict
        """
        self.message = message['message']
        self.start = message['start']
        self.end = message['end']
        self.uuid = message['uuid']

    def to_dict(self):
        """
        Return message as dict
        """
        return {
            'uuid': self.uuid,
            'message': self.message,
            'start': self.start,
            'end': self.end,
            'displayed_time': self.displayed_time
        }

    def __str__(self):
        return 'Message "%s" [%d:%d] %d' % (self.message, self.start, self.end, self.displayed_time)


class Messageboard(RaspIot):

    MODULE_CONFIG_FILE = 'messageboard.conf'
    MODULE_DEPS = []

    DEFAULT_CONFIG = {
        'duration': 60,
        'unit_minutes': 'minutes',
        'unit_hours': 'hours',
        'unit_days': 'days',
        'messages' : [],
        'speed': 0.05
    }

    def __init__(self, bus, debug_enabled):
        #init
        RaspIot.__init__(self, bus, debug_enabled)

        #members
        self.__current_message = None
        self.messages = []

        #init board
        pin_a0 = 15
        pin_a1 = 16
        pin_a2 = 18
        pin_e3 = 22
        panels = 4
        self.board = HT1632C(pin_a0, pin_a1, pin_a2, pin_e3, panels)
        self.__set_board_units()
        self.board.set_scroll_speed(self._config['speed'])

    def _start(self):
        """
        Start module
        """
        #load messages
        for msg in self._config['messages']:
            message = Message()
            message.from_dict(msg)
            self.messages.append(message)

        #init display task
        self.__display_task = task.BackgroundTask(self.__display_message, float(self._config['duration']))
        self.__display_task.start()

        #display ip at startup during 1 minute
        #@see http://stackoverflow.com/a/1267524
        ip = [l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
        now = int(time.time())
        self.add_message('IP: %s' % str(ip), now, now+60)

    def _stop(self):
        """
        Stop module
        """
        #clean board
        self.board.cleanup()

        #stop task
        if self.__display_task:
            self.__display_task.stop()

    def __display_message(self):
        """
        Display messages. Called every seconds by task
        """
        try:
            #now
            now = time.time()
            self.logger.debug('__display_message at %d' % now)

            #get messages to display
            messages_to_display = []
            for msg in self.messages[:]:
                if now>=msg.start and now<=msg.end:
                    #this message could be displayed
                    messages_to_display.append(msg)

                elif now>msg.end:
                    self.logger.debug('Remove obsolete message %s' % unicode(msg))
                    #remove obsolete message from config
                    config = self._get_config()
                    for msg_conf in config['messages']:
                        if msg_conf['uuid']==msg.uuid:
                            config['messages'].remove(msg_conf)
                            self._save_config(config)
                            break

                    #remove message internaly
                    self.messages.remove(msg)

            #sort messages to display by date
            #msg's displayed_time is set when message is displayed
            #message not displayed yet has displayed_time set to 0
            #so naturally oldest messages or not already displayed are sorted at top of list
            messages_to_display.sort(key=lambda msg:msg.displayed_time, reverse=False)

            if self.logger.getEffectiveLevel()==logging.DEBUG:
                self.logger.debug('Messages to display:')
                for msg in messages_to_display:
                    self.logger.debug(' - %s' % str(msg))

            #display first list message
            if len(messages_to_display)>0:
                #get first list message
                msg = messages_to_display[0]
                if msg!=self.__current_message or msg.dynamic==True:
                    self.logger.debug(' ==> Display message %s' % str(msg))
                    msg.dynamic = self.board.display_message(msg.message)
                    msg.displayed_time = now
                    self.__current_message = msg

                    #push event
                    req = MessageRequest()
                    req.event = 'messageboard.message.update'
                    req.params = self.get_current_message()
                    self.push(req)

            else:
                #no message to display, clear screen
                self.__current_message = None
                self.board.clear()

        except:
            self.logger.exception('Exception on message displaying:')

    def __set_board_units(self):
        """
        Set board units
        """
        days = None
        hours = None
        minutes = None
        if self._config.has_key('unit_days') and self._config['unit_days']:
            days = self._config['unit_days']
        if self._config.has_key('unit_hours') and self._config['unit_hours']:
            hours = self._config['unit_hours']
        if self._config.has_key('unit_minutes') and self._config['unit_minutes']:
            minutes = self._config['unit_minutes']

        #set board unit
        self.board.set_time_units(minutes, hours, days)

    def set_duration(self, duration):
        """
        Configure message cycle duration
        @param duration: message cycle duration
        """
        #save duration
        config = self._get_config()
        config['duration'] = duration
        self._save_config(config)

        #stop current task
        if self.__display_task:
            self.__display_task.stop()
        
        #and restart new one
        self.__display_task = task.BackgroundTask(self.__display_message, float(duration))
        self.__display_task.start()

    def get_module_config(self):
        """
        Return module full configuration
        """
        config = {}
        config['messages'] = self.get_messages()
        config['duration'] = self.get_duration()
        config['units'] = self.get_units()
        config['speed'] = self.get_speed()
        config['status'] = self.get_current_message()
        return config;

    def get_duration(self):
        """
        Return message cycle duration
        @return duration
        """
        return self._config['duration']

    def set_speed(self, speed):
        """
        Configure scrolling message speed
        @param speed: message speed
        """
        #save speed
        config = self._get_config()
        config['speed'] = speed
        self._save_config(config)

        #set board scroll speed
        self.board.set_scroll_speed(speed)

    def get_speed(self):
        """
        Return scrolling message speed
        @return speed
        """
        return self._config['speed']

    def add_message(self, message, start, end):
        """
        Add advertisment to display
        @param message: message to display
        @param start: date to start displaying message from
        @param end: date to stop displaying message
        @return message uuid
        """
        #create message object
        msg = Message(message, start, end)
        self.logger.debug('add new message: %s' % unicode(msg))

        #save it to config
        config = self._get_config()
        config['messages'].append(msg.to_dict())
        self._save_config(config)

        #save it to internaly
        self.messages.append(msg)
        
        return msg.uuid

    def delete_message(self, uuid):
        """
        Delete message which uuid is specified
        @param uuid: message uuid
        """
        deleted = False
        #delete message from config
        config = self._get_config()
        for msg in config['messages']:
            if msg['uuid']==uuid:
                config['messages'].remove(msg)
                deleted = True
                break
        if deleted:
            self._save_config(config)

        #and delete it internaly
        for msg in self.messages[:]:
            if msg.uuid==uuid:
                self.messages.remove(msg)
                break

        self.logger.debug('Message "%s" deleted' % msg.message)

        return deleted

    def replace_message(self, uuid, message, start, end):
        """
        Replace message by new specified infos. Useful to cycle message transparently
        @param uuid: message uuid to replace content
        @param message: message to display
        @param start: date to start displaying message from
        @param end: date to stop displaying message
        """
        #replace message in config
        replaced = False
        config = self._get_config()
        for msg in config['messages']:
            if msg['uuid']==uuid:
                #message found, replace infos by new ones
                msg.message = message
                msg.start = start
                msg.end = end
                replaced = True
        if replaced:
            self._save_config(config)

        #replace message internaly
        for msg in self.messages:
            if msg.uuid==uuid:
                msg.message = message
                msg.start = start
                msg.end = end

        self.logger.debug('Message "%s" replaced' % msg.message)

        return replaced

    def get_messages(self):
        """
        Return all messages
        """
        msgs = []
        for msg in self.messages:
            msgs.append(msg.to_dict())
        return msgs

    def get_current_message(self):
        """
        Return current displayed message
        """
        out = {
            'nomessage': False,
            'off': False,
            'message': None
        }

        if self.__current_message is None:
            #no message displayed for now, return empty string
            out['nomessage'] = True
        elif not self.board.is_on():
            #board is off
            out['off'] = True
        else:
            #send message
            out['message'] = self.__current_message.to_dict()

        return out

    def get_units(self):
        """
        Return time units
        @return dict {days, hours, minutes}
        """
        return {
            'days': self._config['unit_days'],
            'hours': self._config['unit_hours'],
            'minutes': self._config['unit_minutes']
        }

    def set_units(self, minutes, hours, days):
        """
        Set board time units
        """
        #save units in config
        if minutes and hours and days:
            config = self._get_config()
            config['unit_days'] = days
            config['unit_hours'] = hours
            config['unit_minutes'] = minutes
            self._save_config(config)

        #set board units
        self.__set_board_units()

    def turn_on(self):
        """
        Turn on board
        """
        #just turn on display
        self.board.turn_on()

        #push event
        req = MessageRequest()
        req.event = 'messageboard.message.update'
        req.params = self.get_current_message()
        self.push(req)

    def turn_off(self):
        """
        Turn off board
        """
        #clear board first
        self.board.clear()

        #and turn off display
        self.board.turn_off()

        #push event
        req = MessageRequest()
        req.event = 'messageboard.message.update'
        req.params = self.get_current_message()
        self.push(req)

    def is_on(self):
        """
        Return board status (on/off)
        """
        return self.board.is_on()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(name)s %(levelname)s : %(message)s")
    board = Messageboard()
    now = int(time.time())
    now_15 = now + 15
    now_30 = now + 30
    now_45 = now + 45
    now_60 = now + 60
    board.add_message('msg0', now, now_15+60, False)
    board.add_message('msg1', now_15, now_15+30, False)
    board.add_message('msg2', now_30, now_30+45, False)
    board.add_message('msg3', now_45, now_45+30, False)
    board.add_message('msg4', now_60, now_60+30, False)
    try:
        while True:
            time.sleep(0.25)
    except:
        pass

    board.stop()
