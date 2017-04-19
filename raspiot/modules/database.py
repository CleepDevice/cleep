#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import sqlite3
import logging
from raspiot.raspiot import RaspIotMod
from raspiot.utils import CommandError, MissingParameter, InvalidParameter
import time

__all__ = ['Database']

class Database(RaspIotMod):

    MODULE_CONFIG_FILE = 'database.conf'
    MODULE_DEPS = []

    DATABASE_PATH = '/var/opt/raspiot/databases'
    DATABASE_NAME = 'raspiot.db'

    def __init__(self, bus, debug_enabled):
        """
        Constructor
        @param bus: bus instance
        @param debug_enabled: debug status
        """
        #init
        RaspIotMod.__init__(self, bus, debug_enabled)

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

        #create devices table (handle number of values associated to device)
        #format:
        # - uuid: store device uuid (string) (primary key)
        # - event: event type stored for the device (string)
        # - valuescount: number of values saved for the device
        # - value1: field name for value1
        # - value2: field name for value2
        # - value3: field name for value3
        # - value4: field name for value4
        cur.execute('CREATE TABLE devices(uuid TEXT PRIMARY KEY UNIQUE, event TEXT, valuescount INTEGER, value1 NUMBER DEFAULT NULL, value2 TEXT DEFAULT NULL, value3 TEXT DEFAULT NULL, value4 TEXT DEFAULT NULL);')

        #create data1 table (contains 1 field to store value, typically light/humidity... sensors)
        #format:
        # - id: unique id (primary key)
        # - timestamp: timestamp when value was inserted
        # - uuid: device uuid that pushes values
        # - value, value1, value2, value3, value4: values of device
        cur.execute('CREATE TABLE data1(id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, timestamp INTEGER, uuid TEXT, value1 NUMBER);')
        cur.execute('CREATE INDEX data1_device_index ON data1(uuid);')
        cur.execute('CREATE INDEX data1_timestamp_index ON data1(timestamp);')

        #create data2 table (contains 2 fields to store values, typically gps positions, temperature (C° and F°))
        cur.execute('CREATE TABLE data2(id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, timestamp INTEGER, uuid TEXT, value1 NUMBER, value2 NUMBER);')
        cur.execute('CREATE INDEX data2_device_index ON data2(uuid);')
        cur.execute('CREATE INDEX data2_timestamp_index ON data2(timestamp);')

        #create data3 table (contains 3 fields to store values)
        cur.execute('CREATE TABLE data3(id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, timestamp INTEGER, uuid TEXT, value1 NUMBER, value2 NUMBER, value3 NUMBER);')
        cur.execute('CREATE INDEX data3_device_index ON data3(uuid);')
        cur.execute('CREATE INDEX data3_timestamp_index ON data3(timestamp);')

        #create data4 table (contains 4 fields to store values)
        cur.execute('CREATE TABLE data4(id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, timestamp INTEGER, uuid TEXT, value1 NUMBER, value2 NUMBER, value3 NUMBER, value4 NUMBER);')
        cur.execute('CREATE INDEX data4_device_index ON data4(uuid);')
        cur.execute('CREATE INDEX data4_timestamp_index ON data4(timestamp);')

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
        @param current_field: current field to replace
        @param fields: fields mapping (dict)
        """
        try:
            if current_field=='timestamp':
                #return reduced string of timestamp
                return 'ts'
            else: 
                return fields[current_field]
        except:
            #field name not found
            return current_field

    def save_data(self, uuid, event, values):
        """
        Save data into database
        @param uuid: device uuid
        @param event: event name
        @param values: values to save (must be an list of dict(<field>,<value>))
        """
        self.logger.debug('set_data uuid=%s event=%s values=%s' % (uuid, event, str(values)))
        if uuid is None or len(uuid)==0:
            raise MissingParameter('Uuid parameter is missing')
        if event is None or len(event)==0:
            raise MissingParameter('Event parameter is missing')
        if values is None:
            raise MissingParameter('Values parameter is missing')
        if not isinstance(values, list):
            raise InvalidParameter('Values parameter must be a list')
        if len(values)==0:
            raise InvalidParameter('No value to save')
        if len(values)>4:
            raise InvalidParameter('Too many values to save. It is limited to 2 values for now.')

        #save uuid infos at first insert
        self.__cur.execute('SELECT * FROM devices WHERE uuid=?', (uuid,))
        row = self.__cur.fetchone()
        if row is None:
            #no infos yet, insert new entry for this device
            if len(values)==1:
                self.__cur.execute('INSERT INTO devices(uuid, event, valuescount, value1) VALUES(?,?,?,?)', (uuid, event, len(values), values[0]['field']))
            elif len(values)==2:
                self.__cur.execute('INSERT INTO devices(uuid, event, valuescount, value1, value2) VALUES(?,?,?,?,?)', (uuid, event, len(values), values[0]['field'], values[1]['field']))
            elif len(values)==3:
                self.__cur.execute('INSERT INTO devices(uuid, event, valuescount, value1, value2, value3) VALUES(?,?,?,?,?,?)', (uuid, event, len(values), values[0]['field'], values[1]['field'], values[2]['field']))
            elif len(values)==4:
                self.__cur.execute('INSERT INTO devices(uuid, event, valuescount, value1, value2, value3, value4) VALUES(?,?,?,?,?,?,?)', (uuid, event, len(values), values[0]['field'], values[1]['field'], values[2]['field'], values[3]['values']))
        else:
            #entry exists, check it
            infos = dict((self.__cur.description[i][0], value) for i, value in enumerate(row))
            if infos['event']!=event:
                raise CommandError('Device %s cannot store values from event %s' % (uuid, event))
            if infos['valuescount']!=len(values):
                raise CommandError('Event %s is supposed to store %d values not %d' % (event, infos['valuescount'], len(values)))

        #save values
        if len(values)==1:
            self.__cur.execute('INSERT INTO data1(timestamp, uuid, value1) values(?,?,?)', (int(time.time()), uuid, values[0]['value']))
        elif len(values)==2:
            self.__cur.execute('INSERT INTO data2(timestamp, uuid, value1, value2) values(?,?,?,?)', (int(time.time()), uuid, values[0]['value'], values[1]['value']))
        elif len(values)==3:
            self.__cur.execute('INSERT INTO data3(timestamp, uuid, value1, value2, value3) values(?,?,?,?,?)', (int(time.time()), uuid, values[0]['value'], values[1]['value'], values[2]['value']))
        elif len(values)==4:
            self.__cur.execute('INSERT INTO data4(timestamp, uuid, value1, value2, value3, value4) values(?,?,?,?,?,?)', (int(time.time()), uuid, values[0]['value'], values[1]['value'], values[2]['value'], values[3]['value']))

        #commit changes
        self.__cnx.commit()
        
        return True

    def __get_device_infos(self, uuid):
        """
        Return device infos (read from "devices" table)
        @return list of devices table fields:
            dict(
                'event': event associated to device (string),
                'valuescount': number of values saved for this device (used to get data table) (int),
                'value1': value1 field name (string),
                'value2': value2 field name (string or None),
                'value3': value3 field name (string or None),
                'value4': value4 field name (string or None),
            )
        """
        self.__cur.execute('SELECT event, valuescount, value1, value2, value3, value4 FROM devices WHERE uuid=?', (uuid,))
        row = self.__cur.fetchone()
        if row is None:
            raise CommandError('Device %s not found!' % uuid)
        return dict((self.__cur.description[i][0], value) for i, value in enumerate(row))

    def get_data(self, uuid, timestamp_start, timestamp_end, options=None):
        """
        Return data from data table
        @param uuid: device uuid
        @param timestamp_start: start of range
        @param timestamp_end: end of range
        @param options: command options
                dict(
                    'output': <'list','dict'[default]>,
                    'fields': [<field1>, <field2>, ...],
                    'sort': <'asc'[default],'desc'>,
                    'limit': <number>
                )
        @return data
            dict(
                'uuid': <device uuid>,
                'event': <event type>,
                'names': <list(<data name>,...)>,
                'data': <list(list(<data value,...>|list(dict('data name':<data value>,...))))
            )
        """
        #check parameters
        if uuid is None or len(uuid)==0:
            raise MissingParameter('Uuid parameter is missing')
        if timestamp_start is None:
            raise MissingParameter('Timestamp_start parameter is missing')
        if timestamp_start<0:
            raise InvalidParameter('Timestamp_start value must be positive') 
        if timestamp_end is None:
            raise MissingParameter('Timestamp_end parameter is missing')
        if timestamp_end<0:
            raise InvalidParameter('Timestamp_end value must be positive') 

        #prepare options
        options_fields = []
        options_output = 'dict'
        options_sort = 'asc'
        options_limit = ''
        if options is not None:
            if options.has_key('fields'):
                options_fields = options['fields']
            if options.has_key('output') and options['output'] in ('list', 'dict'):
                options_output = options['output']
            if options.has_key('sort') and options['sort'] in ('asc', 'desc'):
                options_sort = options['sort']
            if options.has_key('limit') and options['limit'].isdigit():
                options_limit = 'LIMIT %d' % options['limit']
        self.logger.debug('options: fields=%s output=%s sort=%s limit=%s' % (options_fields, options_output, options_sort, options_limit))

        #get device infos
        infos = self.__get_device_infos(uuid)
        self.logger.debug('infos=%s' % infos)

        #prepare query options
        columns = []
        names = ['timestamp']
        if len(options_fields)==0:
            #no field filtered, add all existing fields
            columns.append('value1')
            names.append(infos['value1'])
            if infos['value2'] is not None:
                columns.append('value2')
                names.append(infos['value2'])
            if infos['value3'] is not None:
                columns.append('value3')
                names.append(infos['value3'])
            if infos['value4'] is not None:
                columns.append('value4')
                names.append(infos['value4'])
        else:
            #get column associated to field name
            for options_field in options_fields:
                for column in infos.keys():
                    if column.startswith('value') and infos[column]==options_field:
                        columns.append(column)
                        names.append(options_field)

        #get device data for each request columns
        data = None
        if options_output=='dict':
            #output as dict
            query = 'SELECT timestamp,%s FROM data%d WHERE uuid=? AND timestamp>=? AND timestamp<=? ORDER BY timestamp %s %s' % (','.join(columns), infos['valuescount'], options_sort, options_limit)
            self.logger.debug('query=%s' % query)
            self.__cur.execute(query, (uuid, timestamp_start, timestamp_end))
            #@see http://stackoverflow.com/a/3287775
            data = [dict((self.__restore_field_name(self.__cur.description[i][0], infos), value) for i, value in enumerate(row)) for row in self.__cur.fetchall()]

        else:
            #output as list
            data = {}
            for column in columns:
                query = 'SELECT timestamp,%s FROM data%d WHERE uuid=? AND timestamp>=? AND timestamp<=? ORDER BY timestamp %s %s' % (column, infos['valuescount'], options_sort, options_limit)
                self.logger.debug('query=%s' % query)
                self.__cur.execute(query, (uuid, timestamp_start, timestamp_end))
                data[infos[column]] = {
                    'name': infos[column],
                    'values': self.__cur.fetchall()
                }

        return {
            'uuid': uuid,
            'event': infos['event'],
            'names': names,
            'data': data
        }

    def purge_data(self, uuid, timestamp_until):
        """
        Purge device data until specified time
        @param uuid: device uuid (string)
        @param timestamp_until: timestamp to delete data before (int)
        @return always True
        @raise MissingParameter, InvalidParameter
        """
        #check parameters
        if uuid is None or len(uuid)==0:
            raise MissingParameter('Uuid parameter is missing')
        if timestamp_until is None:
            raise MissingParameter('Timestamp_until parameter is missing')
        if timestamp_until<0:
            raise InvalidParameter('Timestamp_until value must be positive') 
        
        #get device infos
        infos = self.__get_device_infos(uuid)
        self.logger.debug('infos=%s' % infos)

        #prepare query parameters
        tablename = ''
        if infos['valuescount']==1:
            tablename = 'data1'
        if infos['valuescount']==2:
            tablename = 'data2'
        if infos['valuescount']==3:
            tablename = 'data3'
        if infos['valuescount']==4:
            tablename = 'data4'

        #prepare sql query
        query = 'DELETE FROM %s WHERE uuid=? AND timestamp<?' % tablename
        self.logger.debug('query=%s' % query)

        #execute query
        self.__cur.execute(query, (uuid, timestamp_until))

        return True

    def __delete_device(self, uuid):
        """
        Purge device data until specified time
        @param uuid: device uuid (string)
        @param timestamp_until: timestamp to delete data before (int)
        @return always True
        @raise MissingParameter, InvalidParameter
        """
        #check parameters
        if uuid is None or len(uuid)==0:
            raise MissingParameter('Uuid parameter is missing')
        
        #get device infos
        infos = self.__get_device_infos(uuid)
        self.logger.debug('infos=%s' % infos)

        #prepare query parameters
        tablename = ''
        if infos['valuescount']==1:
            tablename = 'data1'
        if infos['valuescount']==2:
            tablename = 'data2'
        if infos['valuescount']==3:
            tablename = 'data3'
        if infos['valuescount']==4:
            tablename = 'data4'

        #prepare sql query
        query = 'DELETE FROM %s WHERE uuid=?' % tablename
        self.logger.debug('query=%s' % query)

        #execute query
        self.__cur.execute(query, (uuid,))

        return True

    def event_received(self, event):
        """
        Event received
        @param event: event object
        """
        self.logger.debug('Event received %s' % event)
        if event['uuid'] is not None:
            #split event
            (event_module, event_type, event_action) = event['event'].split('.')

            if event_type=='device' and event_action=='delete':
                #delete device data
                self.__delete_device(event['uuid'])

            elif event_type=='temperature':
                #save temperature event
                self.save_data(event['uuid'], event_type, [
                    {'field':'celsius', 'value':event['params']['celsius']},
                    {'field':'fahrenheit', 'value':event['params']['fahrenheit']}
                ])

            elif event_type=='motion':
                #save motion event
                if event_action=='on':
                    #trick to make graphable motion data (inject 0 just before setting real value)
                    self.save_data(event['uuid'], event_type, [
                        {'field':'on', 'value':0}
                    ])
                    time.sleep(1.0)
                    self.save_data(event['uuid'], event_type, [
                        {'field':'on', 'value':1}
                    ])
                else:
                    self.save_data(event['uuid'], event_type, [
                        {'field':'on', 'value':1}
                    ])
                    time.sleep(1.0)
                    self.save_data(event['uuid'], event_type, [
                        {'field':'on', 'value':0}
                    ])

            elif event_type=='monitoring':
                #save cpu usage
                if event_action=='cpu':
                    raspiot = float(event['params']['raspiot'])
                    system = float(event['params']['system'])
                    others = float('{0:.2f}'.format(system - raspiot))
                    if others<0.0:
                        others = 0.0
                    idle = 100.0 - raspiot - others
                    self.save_data(event['uuid'], event_type, [
                        {'field':'raspiot', 'value':raspiot},
                        {'field':'others', 'value':others},
                        {'field':'idle', 'value':idle}
                    ])

                #save memory usage
                if event_action=='memory':
                    raspiot = float(event['params']['raspiot'])
                    total = float(event['params']['total'])
                    available = float(event['params']['available'])
                    others = total - available - raspiot
                    self.save_data(event['uuid'], event_type, [
                        {'field':'raspiot', 'value':raspiot},
                        {'field':'others', 'value':others},
                        {'field':'available', 'value':available}
                    ])

