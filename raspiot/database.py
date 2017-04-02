#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import sqlite3
import logging
from raspiot import RaspIot, CommandError
from bus import MissingParameter, InvalidParameter

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
        cur.execute('CREATE TABLE devices(device TEXT PRIMARY KEY UNIQUE, event TEXT, valuescount INTEGER);')

        #create data1 table (contains 1 field to store value, typically temp/light/... sensors)
        cur.execute('CREATE TABLE data1(id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, timestamp INTEGER, device TEXT, value TEXT);')
        cur.execute('CREATE INDEX data1_device_index ON data1(device);')
        cur.execute('CREATE INDEX data1_timestamp_index ON data1(timestamp);')

        #create data2 table (contains 2 fields to store values, typically gps positions)
        cur.execute('CREATE TABLE data2(id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, timestamp INTEGER, device TEXT, value1 TEXT, value2 TEXT);')
        cur.execute('CREATE INDEX data2_device_index ON data2(device);')
        cur.execute('CREATE INDEX data2_timestamp_index ON data2(timestamp);')

        cnx.commit()
        cnx.close()

    def __check_database(self):
        """
        Check database: check if tables exists
        """
        pass

    def save_data(self, device, event, values):
        """
        Save data into database
        @param device: device id
        @param event: event name
        @param values: values to save (must be a tuple)
        """
        self.logger.debug('set_data device=%s event=%s values=%s' % (device, event, str(values)))
        if device is None or len(device)==0:
            raise MissingParameter('"device" parameter is missing')
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

        #save device infos at first insert
        self.__cur.execute('SELECT * FROM devices WHERE device=?', (device,))
        row = self.__cur.fetchone()
        if row is None:
            #no infos yet, insert new entry for this device
            self.__cur.execute('INSERT INTO devices(device, event, valuescount) VALUES(?,?,?)', (device, event, len(values),))

        #save values
        if len(values)==1:
            self.__cur.execute('INSERT INTO data1(timestamp, device, value) values(?,?,?)', (int(time.time()), device, values[0]))
        elif len(values)==2:
            self.__cur.execute('INSERT INTO data1(timestamp, device, value1, value2) values(?,?,?,?)', (int(time.time()), device, values[0], values[1],))
        
        return True

    def get_data(self, device):
        """
        Return data from data table
        @param device: device id
        @return dict of rows
        """
        if device is None or len(device)==0:
            raise MissingParameter('"device" parameter is missing')

        #get device infos
        self.__cur.execute('SELECT event, valuescount FROM devices WHERE device=?', (device,))
        row = self.__cur.fetchone()
        if row is None:
            raise CommandError('Device not found!')
        infos = dict((self.__cur.description[i][0], value) for i, value in enumerate(row))

        if infos['valuescount']==1:
            self.__cur.execute('SELECT timestamp, value FROM data1 WHERE device=? ORDER BY timestamp ASC', (device,))
        elif infos['valuescount']==2:
            self.__cur.execute('SELECT timestamp, value1, value2 FROM data2 WHERE device=? ORDER BY timestamp ASC', (device,))
        else:
            raise CommandError('Unable to get data, unknown data source')
        #code from http://stackoverflow.com/a/3287775
        rows = [dict((self.__cur.description[i][0], value) for i, value in enumerate(row)) for row in self.__cur.fetchall()]

        return {
            'device': device,
            'event': infos['event'],
            'data': rows
        }

    def event_received(self, event):
        """
        Event received
        @param event object
        """
        #if event['device'] is not None:
        #    #automatically save event data
        #    self.set_data(event['device'], event['event'], event['params'])
        pass
            
        
