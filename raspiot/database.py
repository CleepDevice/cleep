#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import sqlite3
import logging
from raspiot import RaspIot, CommandError
from bus import MissingParameter, InvalidParameter
import time

__all__ = ['Database']

class Database(RaspIot):

    MODULE_CONFIG_FILE = 'database.conf'
    MODULE_DEPS = []
    DATABASE_PATH = '/var/opt/raspiot/databases'
    DATABASE_NAME = 'raspiot.db'

    def __init__(self, bus, debug_enabled):
        #init
        RaspIot.__init__(self, bus, debug_enabled)

        #member
        self.__cnx = None
        self.__cur = None

        #make sure database path exists
        if not os.path.exists(Database.DATABASE_PATH):
            os.makedirs(Database.DATABASE_PATH)

    def _start(self):
        """
        Start module
        """
        self.logger.debug('_start')
        #make sure database file exists
        if not os.path.exists(os.path.join(Database.DATABASE_PATH, Database.DATABASE_NAME)):
            self.logger.debug('Database file not found')
            self.__init_database()

        self.logger.debug('Connect to database')
        self.__cnx = sqlite3.connect(os.path.join(Database.DATABASE_PATH, Database.DATABASE_NAME))
        self.__cur = self.__cnx.cursor()

    def _stop(self):
        """
        Stop module
        """
        if self.__cnx:
            self.logger.debug('close db')
            self.__cnx.close()

    def __init_database(self):
        """
        Init database
        """
        path = os.path.join(Database.DATABASE_PATH, Database.DATABASE_NAME)
        self.logger.debug('Initialize database "%s"' % path)

        #create database file
        cnx = sqlite3.connect(path)
        cur = cnx.cursor()

        #create device table (handle number of values associated to device)
        cur.execute('CREATE TABLE devices(uuid TEXT PRIMARY KEY UNIQUE, event TEXT, valuescount INTEGER);')

        #create data1 table (contains 1 field to store value, typically light/humidity... sensors)
        cur.execute('CREATE TABLE data1(id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, timestamp INTEGER, uuid TEXT, value TEXT);')
        cur.execute('CREATE INDEX data1_device_index ON data1(uuid);')
        cur.execute('CREATE INDEX data1_timestamp_index ON data1(timestamp);')

        #create data2 table (contains 2 fields to store values, typically gps positions, temperature (C° and F°))
        cur.execute('CREATE TABLE data2(id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, timestamp INTEGER, uuid TEXT, value1 TEXT, value2 TEXT);')
        cur.execute('CREATE INDEX data2_device_index ON data2(uuid);')
        cur.execute('CREATE INDEX data2_timestamp_index ON data2(timestamp);')

        cnx.commit()
        cnx.close()

    def __check_database(self):
        """
        Check database: check if tables exists
        """
        pass

    def save_data(self, uuid, event, values):
        """
        Save data into database
        @param uuid: device uuid
        @param event: event name
        @param values: values to save (must be a tuple)
        """
        self.logger.debug('set_data uuid=%s event=%s values=%s' % (uuid, event, str(values)))
        if uuid is None or len(uuid)==0:
            raise MissingParameter('Uuid parameter is missing')
        if event is None or len(event)==0:
            raise MissingParameter('"event" parameter is missing')
        if values is None:
            raise MissingParameter('"event" parameter is missing')
        if not isinstance(values, tuple):
            raise InvalidParameter('"values" parameter must be a tuple')
        if len(values)==0:
            raise InvalidParameter('No value to save')
        if len(values)>2:
            raise InvalidParameter('Too many values to save. It is limited to 2 values for now.')

        #save uuid infos at first insert
        self.__cur.execute('SELECT * FROM devices WHERE uuid=?', (uuid,))
        row = self.__cur.fetchone()
        if row is None:
            #no infos yet, insert new entry for this device
            self.__cur.execute('INSERT INTO devices(uuid, event, valuescount) VALUES(?,?,?)', (uuid, event, len(values),))
        else:
            #entry exists, check it
            infos = dict((self.__cur.description[i][0], value) for i, value in enumerate(row))
            if infos['event']!=event:
                raise CommandError('Device %s cannot store values from event %s' % (uuid, event))
            if infos['valuescount']!=len(values):
                raise CommandError('Event %s is supposed to store %d values not %d' % (event, infos['valuescount'], len(values)))

        #save values
        if len(values)==1:
            self.__cur.execute('INSERT INTO data1(timestamp, uuid, value) values(?,?,?)', (int(time.time()), uuid, values[0]))
        elif len(values)==2:
            self.__cur.execute('INSERT INTO data1(timestamp, uuid, value1, value2) values(?,?,?,?)', (int(time.time()), uuid, values[0], values[1],))

        #commit changes
        self.__cnx.commit()
        
        return True

    def get_data(self, uuid):
        """
        Return data from data table
        @param uuid: device uuid
        @return dict of rows
        """
        if uuid is None or len(uuid)==0:
            raise MissingParameter('Uuid parameter is missing')

        #get device infos
        self.__cur.execute('SELECT event, valuescount FROM devices WHERE uuid=?', (uuid,))
        row = self.__cur.fetchone()
        if row is None:
            raise CommandError('Device %s not found!' % uuid)
        infos = dict((self.__cur.description[i][0], value) for i, value in enumerate(row))

        if infos['valuescount']==1:
            self.__cur.execute('SELECT timestamp, value FROM data1 WHERE uuid=? ORDER BY timestamp ASC', (uuid,))
        elif infos['valuescount']==2:
            self.__cur.execute('SELECT timestamp, value1, value2 FROM data2 WHERE uuid=? ORDER BY timestamp ASC', (uuid,))
        else:
            raise CommandError('Unable to get data, unknown data source')
        #code from http://stackoverflow.com/a/3287775
        rows = [dict((self.__cur.description[i][0], value) for i, value in enumerate(row)) for row in self.__cur.fetchall()]

        return {
            'uuid': uuid,
            'event': infos['event'],
            'data': rows
        }

    def event_received(self, event):
        """
        Event received
        @param event: event object
        """
        self.logger.debug('Event received %s' % event)
        if event['uuid'] is not None:
            #split event
            (event_module, event_type, event_action) = event['event'].split('.')

            if event_type=='temperature':
                #save temperature event
                self.save_data(event['uuid'], event_type, (event['params']['celsius'], event['params']['fahrenheit']))
            elif event_type=='motion':
                #save motion event
                if event_action=='on':
                    self.save_data(event['uuid'], event_type, (1,))
                else:
                    self.save_data(event['uuid'], event_type, (0,))

        
