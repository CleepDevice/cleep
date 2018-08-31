#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import sqlite3
import logging
from raspiot.raspiot import RaspIotModule
from raspiot.utils import CommandError, MissingParameter, InvalidParameter
import time

__all__ = [u'Database']

class Database(RaspIotModule):
    """
    Module that provides data storage in local database
    Also unlock sensors and system charts
    """
    MODULE_AUTHOR = u'Cleep'
    MODULE_VERSION = u'1.0.0'
    MODULE_PRICE = 0
    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Database module gives you access to chart feature allowing you to follow easily your devices.'
    MODULE_LOCKED = False
    MODULE_TAGS = [u'sensors', u'graphs', u'charts']
    MODULE_COUNTRY = None
    MODULE_URLINFO = None
    MODULE_URLHELP = None
    MODULE_URLSITE = None
    MODULE_URLBUGS = None

    MODULE_CONFIG_FILE = u'database.conf'

    DATABASE_PATH = u'/var/opt/raspiot/databases'
    DATABASE_NAME = u'raspiot.db'

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): flag to set debug level to logger
        """
        #init
        RaspIotModule.__init__(self, bootstrap, debug_enabled)

        #member
        self.__cnx = None
        self.__cur = None

        #make sure database path exists
        if not os.path.exists(Database.DATABASE_PATH):
            self.cleep_filesystem.mkdir(Database.DATABASE_PATH, True)

    def _configure(self):
        """
        Configure module
        """
        #make sure database file exists
        if not os.path.exists(os.path.join(Database.DATABASE_PATH, Database.DATABASE_NAME)):
            self.logger.debug(u'Database file not found')
            self.__init_database()

        self.logger.debug(u'Connect to database')
        self.__cnx = sqlite3.connect(os.path.join(Database.DATABASE_PATH, Database.DATABASE_NAME))
        self.__cur = self.__cnx.cursor()

    def _stop(self):
        """
        Stop module
        """
        if self.__cnx:
            self.__cnx.close()

    def __init_database(self):
        """
        Init database
        """
        path = os.path.join(Database.DATABASE_PATH, Database.DATABASE_NAME)
        self.logger.debug(u'Initialize database "%s"' % path)

        #create database file
        cnx = sqlite3.connect(path)
        cur = cnx.cursor()

        #create devices table (handle number of values associated to device)
        #format:
        # - uuid: store device uuid (string) (primary key)
        # - event: event type stored for the device (string)
        # - valuescount: number of values saved for the device
        # - value1: field name for value1
        # - value2: field name for value2
        # - value3: field name for value3
        # - value4: field name for value4
        cur.execute(u'CREATE TABLE devices(uuid TEXT PRIMARY KEY UNIQUE, event TEXT, valuescount INTEGER, value1 NUMBER DEFAULT NULL, value2 TEXT DEFAULT NULL, value3 TEXT DEFAULT NULL, value4 TEXT DEFAULT NULL);')

        #create data1 table (contains 1 field to store value, typically light/humidity... sensors)
        #format:
        # - id: unique id (primary key)
        # - timestamp: timestamp when value was inserted
        # - uuid: device uuid that pushes values
        # - value, value1, value2, value3, value4: values of device
        cur.execute(u'CREATE TABLE data1(id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, timestamp INTEGER, uuid TEXT, value1 NUMBER);')
        cur.execute(u'CREATE INDEX data1_device_index ON data1(uuid);')
        cur.execute(u'CREATE INDEX data1_timestamp_index ON data1(timestamp);')

        #create data2 table (contains 2 fields to store values, typically gps positions, temperature (C° and F°))
        cur.execute(u'CREATE TABLE data2(id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, timestamp INTEGER, uuid TEXT, value1 NUMBER, value2 NUMBER);')
        cur.execute(u'CREATE INDEX data2_device_index ON data2(uuid);')
        cur.execute(u'CREATE INDEX data2_timestamp_index ON data2(timestamp);')

        #create data3 table (contains 3 fields to store values)
        cur.execute(u'CREATE TABLE data3(id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, timestamp INTEGER, uuid TEXT, value1 NUMBER, value2 NUMBER, value3 NUMBER);')
        cur.execute(u'CREATE INDEX data3_device_index ON data3(uuid);')
        cur.execute(u'CREATE INDEX data3_timestamp_index ON data3(timestamp);')

        #create data4 table (contains 4 fields to store values)
        cur.execute(u'CREATE TABLE data4(id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, timestamp INTEGER, uuid TEXT, value1 NUMBER, value2 NUMBER, value3 NUMBER, value4 NUMBER);')
        cur.execute(u'CREATE INDEX data4_device_index ON data4(uuid);')
        cur.execute(u'CREATE INDEX data4_timestamp_index ON data4(timestamp);')

        cnx.commit()
        cnx.close()

    def __check_database(self):
        """
        Check database: check if tables exists
        """
        pass

    def __restore_field_name(self, current_field, fields):
        """
        Restore field name as stored in database

        Args:
            current_field (string): current field to replace
            fields (string): fields mapping (dict)

        Returns:
            string: field name
        """
        try:
            if current_field==u'timestamp':
                #return reduced string of timestamp
                return u'ts'
            else: 
                return fields[current_field]
        except:
            #field name not found
            return current_field

    def save_data(self, uuid, event, values):
        """
        Save data into database

        Args:
            uuid (string): device uuid
            event (string): event name
            values (list): values to save (must be an list of dict(<field>,<value>))

        Raises:
            InvalidParameter: if invalid parameter is specified
        """
        self.logger.debug(u'Set_data uuid=%s event=%s values=%s' % (uuid, event, unicode(values)))
        if uuid is None or len(uuid)==0:
            raise MissingParameter(u'Uuid parameter is missing')
        if event is None or len(event)==0:
            raise MissingParameter(u'Event parameter is missing')
        if values is None:
            raise MissingParameter(u'Values parameter is missing')
        if not isinstance(values, list):
            raise InvalidParameter(u'Values parameter must be a list')
        if len(values)==0:
            raise InvalidParameter(u'No value to save')
        if len(values)>4:
            raise InvalidParameter(u'Too many values to save. It is limited to 2 values for now.')

        #save uuid infos at first insert
        self.__cur.execute(u'SELECT * FROM devices WHERE uuid=?', (uuid,))
        row = self.__cur.fetchone()
        if row is None:
            #no infos yet, insert new entry for this device
            if len(values)==1:
                self.__cur.execute(u'INSERT INTO devices(uuid, event, valuescount, value1) VALUES(?,?,?,?)', (uuid, event, len(values), values[0][u'field']))
            elif len(values)==2:
                self.__cur.execute(u'INSERT INTO devices(uuid, event, valuescount, value1, value2) VALUES(?,?,?,?,?)', (uuid, event, len(values), values[0][u'field'], values[1][u'field']))
            elif len(values)==3:
                self.__cur.execute(u'INSERT INTO devices(uuid, event, valuescount, value1, value2, value3) VALUES(?,?,?,?,?,?)', (uuid, event, len(values), values[0][u'field'], values[1][u'field'], values[2][u'field']))
            elif len(values)==4:
                self.__cur.execute(u'INSERT INTO devices(uuid, event, valuescount, value1, value2, value3, value4) VALUES(?,?,?,?,?,?,?)', (uuid, event, len(values), values[0][u'field'], values[1][u'field'], values[2][u'field'], values[3][u'values']))
        else:
            #entry exists, check it
            infos = dict((self.__cur.description[i][0], value) for i, value in enumerate(row))
            if infos[u'event']!=event:
                raise CommandError(u'Device %s cannot store values from event %s' % (uuid, event))
            if infos[u'valuescount']!=len(values):
                raise CommandError(u'Event %s is supposed to store %d values not %d' % (event, infos[u'valuescount'], len(values)))

        #save values
        if len(values)==1:
            self.__cur.execute(u'INSERT INTO data1(timestamp, uuid, value1) values(?,?,?)', (int(time.time()), uuid, values[0][u'value']))
        elif len(values)==2:
            self.__cur.execute(u'INSERT INTO data2(timestamp, uuid, value1, value2) values(?,?,?,?)', (int(time.time()), uuid, values[0][u'value'], values[1][u'value']))
        elif len(values)==3:
            self.__cur.execute(u'INSERT INTO data3(timestamp, uuid, value1, value2, value3) values(?,?,?,?,?)', (int(time.time()), uuid, values[0][u'value'], values[1][u'value'], values[2][u'value']))
        elif len(values)==4:
            self.__cur.execute(u'INSERT INTO data4(timestamp, uuid, value1, value2, value3, value4) values(?,?,?,?,?,?)', (int(time.time()), uuid, values[0][u'value'], values[1][u'value'], values[2][u'value'], values[3][u'value']))

        #commit changes
        self.__cnx.commit()
        
        return True

    def __get_device_infos(self, uuid):
        """
        Return device infos (read from "devices" table)

        Args:
            uuid (string): uuid

        Returns:
            dict: list of devices table fields
                {
                    'event': event associated to device (string),
                    'valuescount': number of values saved for this device (used to get data table) (int),
                    'value1': value1 field name (string),
                    'value2': value2 field name (string or None),
                    'value3': value3 field name (string or None),
                    'value4': value4 field name (string or None),
                }
        """
        self.__cur.execute(u'SELECT event, valuescount, value1, value2, value3, value4 FROM devices WHERE uuid=?', (uuid,))
        row = self.__cur.fetchone()
        if row is None:
            raise CommandError(u'Device %s not found!' % uuid)
        return dict((self.__cur.description[i][0], value) for i, value in enumerate(row))

    def get_data(self, uuid, timestamp_start, timestamp_end, options=None):
        """
        Return data from data table

        Args:
            uuid (string): device uuid
            timestamp_start (int): start of range
            timestamp_end (int): end of range
            options (dict): command options
                {
                    'output': <'list','dict'[default]>,
                    'fields': [<field1>, <field2>, ...],
                    'sort': <'asc'[default],'desc'>,
                    'limit': <number>
                }

        Returns:
            dict: data
                {
                    'uuid': <device uuid>,
                    'event': <event type>,
                    'names': <list(<data name>,...)>,
                    'data': <list(list(<data value,...>|list(dict('data name':<data value>,...))))
                }

        Raises:
            InvalidParameter: if invalid parameter is specified
            MissingParameter: if parameter is missing
        """
        #check parameters
        if uuid is None or len(uuid)==0:
            raise MissingParameter(u'Uuid parameter is missing')
        if timestamp_start is None:
            raise MissingParameter(u'Timestamp_start parameter is missing')
        if timestamp_start<0:
            raise InvalidParameter(u'Timestamp_start value must be positive') 
        if timestamp_end is None:
            raise MissingParameter(u'Timestamp_end parameter is missing')
        if timestamp_end<0:
            raise InvalidParameter(u'Timestamp_end value must be positive') 

        #prepare options
        options_fields = []
        options_output = u'dict'
        options_sort = u'asc'
        options_limit = u''
        if options is not None:
            if options.has_key(u'fields'):
                options_fields = options[u'fields']
            if options.has_key(u'output') and options[u'output'] in (u'list', u'dict'):
                options_output = options[u'output']
            if options.has_key(u'sort') and options[u'sort'] in (u'asc', u'desc'):
                options_sort = options[u'sort']
            if options.has_key(u'limit') and options[u'limit'].isdigit():
                options_limit = 'LIMIT %d' % options['limit']
        self.logger.debug(u'options: fields=%s output=%s sort=%s limit=%s' % (options_fields, options_output, options_sort, options_limit))

        #get device infos
        infos = self.__get_device_infos(uuid)
        self.logger.debug(u'infos=%s' % infos)

        #prepare query options
        columns = []
        names = [u'timestamp']
        if len(options_fields)==0:
            #no field filtered, add all existing fields
            columns.append(u'value1')
            names.append(infos[u'value1'])
            if infos[u'value2'] is not None:
                columns.append(u'value2')
                names.append(infos[u'value2'])
            if infos[u'value3'] is not None:
                columns.append(u'value3')
                names.append(infos[u'value3'])
            if infos[u'value4'] is not None:
                columns.append(u'value4')
                names.append(infos[u'value4'])
        else:
            #get column associated to field name
            for options_field in options_fields:
                for column in infos.keys():
                    if column.startswith(u'value') and infos[column]==options_field:
                        columns.append(column)
                        names.append(options_field)

        #get device data for each request columns
        data = None
        if options_output==u'dict':
            #output as dict
            query = u'SELECT timestamp,%s FROM data%d WHERE uuid=? AND timestamp>=? AND timestamp<=? ORDER BY timestamp %s %s' % (u','.join(columns), infos[u'valuescount'], options_sort, options_limit)
            self.logger.debug(u'query=%s' % query)
            self.__cur.execute(query, (uuid, timestamp_start, timestamp_end))
            #@see http://stackoverflow.com/a/3287775
            data = [dict((self.__restore_field_name(self.__cur.description[i][0], infos), value) for i, value in enumerate(row)) for row in self.__cur.fetchall()]

        else:
            #output as list
            data = {}
            for column in columns:
                query = u'SELECT timestamp,%s FROM data%d WHERE uuid=? AND timestamp>=? AND timestamp<=? ORDER BY timestamp %s %s' % (column, infos[u'valuescount'], options_sort, options_limit)
                self.logger.debug(u'query=%s' % query)
                self.__cur.execute(query, (uuid, timestamp_start, timestamp_end))
                data[infos[column]] = {
                    u'name': infos[column],
                    u'values': self.__cur.fetchall()
                }

        return {
            u'uuid': uuid,
            u'event': infos[u'event'],
            u'names': names,
            u'data': data
        }

    def purge_data(self, uuid, timestamp_until):
        """
        Purge device data until specified time

        Args:
            uuid (string): device uuid (string)
            timestamp_until (int): timestamp to delete data before (int)

        Returns:
            bool: always True

        Raises:
            MissingParameter: if parameter is missing
            InvalidParameter: if invalid parameter is specified
        """
        #check parameters
        if uuid is None or len(uuid)==0:
            raise MissingParameter(u'Uuid parameter is missing')
        if timestamp_until is None:
            raise MissingParameter(u'Timestamp_until parameter is missing')
        if timestamp_until<0:
            raise InvalidParameter(u'Timestamp_until value must be positive') 
        
        #get device infos
        infos = self.__get_device_infos(uuid)
        self.logger.debug(u'infos=%s' % infos)

        #prepare query parameters
        tablename = u''
        if infos[u'valuescount']==1:
            tablename = u'data1'
        if infos[u'valuescount']==2:
            tablename = u'data2'
        if infos[u'valuescount']==3:
            tablename = u'data3'
        if infos[u'valuescount']==4:
            tablename = u'data4'

        #prepare sql query
        query = u'DELETE FROM %s WHERE uuid=? AND timestamp<?' % tablename
        self.logger.debug(u'query=%s' % query)

        #execute query
        self.__cur.execute(query, (uuid, timestamp_until))

        return True

    def __delete_device(self, uuid):
        """
        Purge device data until specified time

        Args:
            uuid (string): device uuid
            timestamp_until (int): timestamp to delete data before
        
        Returns:
            bool: always True

        Raises:
            MissingParameter: if parameter is missing
            InvalidParameter: if invalid parameter is specified
        """
        #check parameters
        if uuid is None or len(uuid)==0:
            raise MissingParameter(u'Uuid parameter is missing')
        
        #get device infos
        infos = self.__get_device_infos(uuid)
        self.logger.debug(u'infos=%s' % infos)

        #prepare query parameters
        tablename = u''
        if infos[u'valuescount']==1:
            tablename = u'data1'
        if infos[u'valuescount']==2:
            tablename = u'data2'
        if infos[u'valuescount']==3:
            tablename = u'data3'
        if infos[u'valuescount']==4:
            tablename = u'data4'

        #prepare sql query
        query = u'DELETE FROM %s WHERE uuid=?' % tablename
        self.logger.debug(u'query=%s' % query)

        #execute query
        self.__cur.execute(query, (uuid,))

        return True

    def event_received(self, event):
        """
        Event received, stored sensor data if possible

        Args:
            event (MessageRequest): event
        """
        self.logger.debug(u'Event received %s' % event)
        if event[u'device_id'] is not None:
            #split event
            (event_module, event_type, event_action) = event[u'event'].split(u'.')

            if event_type==u'device' and event_action==u'delete':
                #delete device data
                self.__delete_device(event[u'device_id'])

            elif event_type==u'temperature':
                #save temperature event
                self.save_data(event[u'device_id'], event_type, [
                    {u'field':u'celsius', u'value':event[u'params'][u'celsius']},
                    {u'field':u'fahrenheit', u'value':event[u'params'][u'fahrenheit']}
                ])

            elif event_type==u'motion':
                #save motion event
                if event_action==u'on':
                    #trick to make graphable motion data (inject 0 just before setting real value)
                    self.save_data(event[u'device_id'], event_type, [
                        {u'field':u'on', u'value':0}
                    ])
                    time.sleep(1.0)
                    self.save_data(event[u'device_id'], event_type, [
                        {u'field':u'on', u'value':1}
                    ])
                else:
                    self.save_data(event[u'device_id'], event_type, [
                        {u'field':u'on', u'value':1}
                    ])
                    time.sleep(1.0)
                    self.save_data(event[u'device_id'], event_type, [
                        {u'field':u'on', u'value':0}
                    ])

            elif event_type==u'monitoring':
                #save cpu usage
                if event_action==u'cpu':
                    raspiot = float(event[u'params'][u'raspiot'])
                    system = float(event[u'params'][u'system'])
                    others = float('{0:.2f}'.format(system - raspiot))
                    if others<0.0:
                        others = 0.0
                    idle = 100.0 - raspiot - others
                    self.save_data(event[u'device_id'], event_type, [
                        {u'field':u'raspiot', u'value':raspiot},
                        {u'field':u'others', u'value':others},
                        {u'field':u'idle', u'value':idle}
                    ])

                #save memory usage
                if event_action==u'memory':
                    raspiot = float(event[u'params'][u'raspiot'])
                    total = float(event[u'params'][u'total'])
                    available = float(event[u'params'][u'available'])
                    others = total - available - raspiot
                    self.save_data(event[u'device_id'], event_type, [
                        {u'field':u'raspiot', u'value':raspiot},
                        {u'field':u'others', u'value':others},
                        {u'field':u'available', u'value':available}
                    ])

