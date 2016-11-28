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

#logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(name)s %(levelname)s : %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO);

class Message():

    def __init__(self, message=None, start=None, end=None, scroll=False):
        self.message = message
        self.start = start
        self.end = end
        self.scroll = scroll
        self.displayed_time = 0
        self.uuid = str(uuid.uuid4())

    def to_dict(self):
        """
        Return message as dict
        """
        return {
            'uuid': self.uuid,
            'message': self.message,
            'start': self.start,
            'end': self.end,
            'scroll': self.scroll
        }

    def __str__(self):
        return 'Message "%s" [%d:%d] %d' % (self.message, self.start, self.end, self.displayed_time)


class Messageboard(RaspIot):

    CONFIG_FILE = 'messageboard.conf'
    DEPS = []

    def __init__(self, bus):
        RaspIot.__init__(self, bus)
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
        #init display task
        self.duration = 60.0
        self.__display_task = task.BackgroundTask(self.__display_message, self.duration)
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
            if msg!=self.__current_message:
                logger.debug(' ==> Display message %s' % str(msg))
                self.board.display_message(msg.message)
                self.__current_message = msg
                msg.displayed_time = now
        else:
            #no message to display, clear screen
            self.board.clear()

    def set_duration(self, duration):
        """
        Configure message cycle duration
        """
        #stop current task
        if self.__display_task:
            self.__display_task.stop()
        
        #and restart new one
        self.duration = duration
        self.__display_task = task.BackgroundTask(self.__display_message, float(duration))
        self.__display_task.start()

    def add_message(self, message, start, end, scroll):
        """
        Add advertisment (scrolling message) to display
        @param message: message to display
        @param start: date to start displaying message from
        @param end: date to stop displaying message
        @param scroll: scroll message
        """
        msg = Message(message, start, end, scroll)
        logger.debug('add new message: %s' % str(msg))
        self.messages.append(msg)

    def del_message(self, uuid):
        """
        Delete message which uuid is specified
        @param uuid: message uuid
        """
        deleted = False
        for msg in self.messages:
            if msg.uuid==uuid:
                logger.debug('Message "%s" deleted by user' % msg.message)
                self.messages.remove(msg)
                deleted = True
                break
        return deleted

    def get_messages(self):
        """
        Return all messages
        """
        msgs = []
        for msg in self.messages:
            msgs.append(msg.to_dict())
        return msgs


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
