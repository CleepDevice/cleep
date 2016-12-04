#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
import bus
from raspiot import RaspIot
import time
import task
from ht1632c import HT1632C
import uuid

__all__ = ['Messageboard']

logger = logging.getLogger(__name__)
#logger.setLevel(logging.INFO);

class Message():

    def __init__(self, message=None, start=None, end=None):
        self.message = message
        self.start = start
        self.end = end
        self.displayed_time = 0
        self.dynamic = False
        self.uuid = str(uuid.uuid4())

    def to_dict(self):
        """
        Return message as dict
        """
        return {
            'uuid': self.uuid,
            'message': self.message,
            'start': self.start,
            'end': self.end
        }

    def __str__(self):
        return 'Message "%s" [%d:%d] %d' % (self.message, self.start, self.end, self.displayed_time)


class Messageboard(RaspIot):

    CONFIG_FILE = 'messageboard.conf'
    DEPS = []
    DEFAULT_CONFIG = {
        'duration': 60,
        'unit_minutes': 'minutes',
        'unit_hours': 'hours',
        'unit_days': 'days'
    }

    def __init__(self, bus):
        RaspIot.__init__(self, bus)

        #check config
        self._check_config(Messageboard.DEFAULT_CONFIG)

        #messages aren't saved in config
        self.messages = []
        self.__current_message = None

        #init board
        pin_a0 = 15
        pin_a1 = 16
        pin_a2 = 18
        pin_e3 = 22
        panels = 4
        self.board = HT1632C(pin_a0, pin_a1, pin_a2, pin_e3, panels)
        self.__set_board_units()

        #init display task
        self.__display_task = task.BackgroundTask(self.__display_message, float(self._config['duration']))
        self.__display_task.start()

    def stop(self):
        RaspIot.stop(self)
        #stop task
        if self.__display_task:
            self.__display_task.stop()

    def __display_message(self):
        """
        Display messages. Called every seconds by task
        """
        #now
        now = time.time()
        logger.debug('__display_message at %d' % now)

        #TODO add mutex to protect messages member

        #get message to display
        messages_to_display = []
        for msg in self.messages[:]:
            if now>=msg.start and now<=msg.end:
                #this message could be displayed
                messages_to_display.append(msg)
            elif now>msg.end:
                #remove obsolete message
                logger.debug('Remove obsolete message %s' % str(msg))
                self.messages.remove(msg)

        #sort messages to display by date
        #msg's displayed_time is set when message is displayed
        #message not displayed yet has displayed_time set to 0
        #so naturally oldest messages or not already displayed are sorted at top of list
        messages_to_display.sort(key=lambda msg:msg.displayed_time, reverse=False)

        if logger.getEffectiveLevel()==logging.DEBUG:
            logger.debug('Messages to display:')
            for msg in messages_to_display:
                logger.debug(' - %s' % str(msg))

        #display first list message
        if len(messages_to_display)>0:
            #get first list message
            msg = messages_to_display[0]
            if msg!=self.__current_message or msg.dynamic==True:
                logger.debug(' ==> Display message %s' % str(msg))
                msg.dynamic = self.board.display_message(msg.message)
                self.__current_message = msg
                msg.displayed_time = now
        else:
            #no message to display, clear screen
            self.board.clear()

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

    def get_duration(self):
        """
        Return message cycle duration
        @param duration
        """
        return self._config['duration']

    def add_message(self, message, start, end):
        """
        Add advertisment to display
        @param message: message to display
        @param start: date to start displaying message from
        @param end: date to stop displaying message
        @return message uuid
        """
        msg = Message(message, start, end)
        logger.debug('add new message: %s' % str(msg))
        self.messages.append(msg)
        return msg.uuid

    def del_message(self, uuid):
        """
        Delete message which uuid is specified
        @param uuid: message uuid
        """
        deleted = False
        for msg in self.messages:
            if msg.uuid==uuid:
                self.messages.remove(msg)
                deleted = True
                logger.debug('Message "%s" deleted' % msg.message)
                break
        return deleted

    def replace_message(self, uuid, message, start, end):
        """
        Replace message by new specified infos. Useful to cycle message transparently
        @param uuid: message uuid to replace content
        @param message: message to display
        @param start: date to start displaying message from
        @param end: date to stop displaying message
        """
        #search for message
        replaced = False
        for msg in self.messages:
            if msg.uuid==uuid:
                #message found, replace infos by new ones
                msg.message = message
                msg.start = start
                msg.end = end
                replaced = True
        return replaced

    def get_messages(self):
        """
        Return all messages
        """
        msgs = []
        for msg in self.messages:
            msgs.append(msg.to_dict())
        return msgs

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
