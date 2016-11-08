#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
import glob
import uuid as moduuid
import json
import threading

#logging.basicConfig(filename='agosqueezebox.log', level=logging.INFO, format="%(asctime)s %(levelname)s : %(message)s")
#logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(name)s %(levelname)s : %(message)s")
logger = logging.getLogger(__name__)

class Task:
    def __init__(self, interval, task, args= [], kwargs={}):
        self._args = args
        self._kwargs = kwargs
        self._interval = interval
        self._task = task
        self.__timer = None
  
    def __run(self):
        self.__timer = threading.Timer(self._interval, self.__run)
        self.__timer.start()
        self._task(*self._args, **self._kwargs)
  
    def start(self):
        if self.__timer:
            self.stop()
        self.__timer = threading.Timer(self._interval, self.__run)
        self.__timer.start()
  
    def stop(self):
        if self.__timer:
            self.__timer.cancel()
            self.__timer = None

class Probes():
    BASE_DIR = '/sys/bus/w1/devices/'
    W1_SLAVE = 'w1_slave'
    CONF_DIR = 'probes.conf'

    def __init__(self):
        self.__configLock = threading.Lock()
        self.config = self.__loadConfig()
        self.__tReadTemperatures = Task(60.0, self.__readTemperatures)
        self.__tReadTemperatures.start()

    def __del__(self):
        self.__tReadTemperatures.stop()

    def __loadConfig(self):
        """load config file"""
        self.__configLock.acquire(True)
        out = None
        try:
            if os.path.exists(self.CONF_DIR):
                f = open(self.CONF_DIR, 'r')
                raw = f.read()
                f.close()
            else:
                #no conf file yet. Create default one
                f = open(self.CONF_DIR, 'w')
                default = {}
                raw = json.dumps(default)
                f.write(raw)
                f.close()
            out = json.loads(raw)
        except:
            logger.exception('Unable to load config file %s:' % self.CONF_DIR)
        self.__configLock.release()
        return out

    def __saveConfig(self, config):
        """save config file"""
        self.__configLock.acquire(True)
        out = False
        try:
            f = open(self.CONF_DIR, 'w')
            f.write(json.dumps(config))
            f.close()
            self.config = config
            out = True
        except:
            logger.exception('Unable to write config file %s:' % self.CONF_DIR)
        self.__configLock.release()
        return out

    def __probeExists(self, path):
        """return probe uuid if exists, None otherwise"""
        for uuid in self.config:
            if self.config[uuid]['path']==path:
                return uuid
        return None

    def __getFreeProbeName(self, d=None):
        """return free probe name (probeX where X is a number)
           @param d: if specified search into self.config AND into d too"""
        prefix = 'probe%d'
        cpt = 0
        name = prefix % cpt
        if d and isinstance(d, dict):
            col = dict(self.config.items() + d.items())
        else:
            col = dict(self.config.items())
        while True:
            found = False
            for uuid in col:
                if col[uuid]['name']==name:
                    #name already exists
                    found = True
                    break
            if not found:
                #current name is free
                break
            else:
                cpt += 1
                name = prefix % cpt
        return name

    def __readTemperatures(self):
        try:
            for uuid in self.config:
                if self.config[uuid]['local']:
                    (tempC, tempF) = self.__scanProbe(self.config[uuid]['path'])
                    if tempC and tempF:
                        logger.debug('Read tempC[%f] tempF[%f] from probe %s' % (tempC, tempF, uuid))
                        #update config file
                        self.__configLock.acquire(True)
                        self.config[uuid]['tempC'] = tempC
                        self.config[uuid]['tempF'] = tempF
                        self.__configLock.release()
                        self.__saveConfig(self.config)
        except:
            logging.exception('Unable to read temperatures:')
        return True
            
    def __scanProbe(self, path):
        """scan probe file
           @info https://learn.adafruit.com/adafruits-raspberry-pi-lesson-11-ds18b20-temperature-sensing/software """
        tempC = None
        tempF = None
        try:
            if os.path.exists(path):
                f = open(path, 'r')
                raw = f.readlines()
                f.close()
                equals_pos = raw[1].find('t=')
                if equals_pos != -1:
                    tempString = raw[1][equals_pos+2:]
                    tempC = float(tempString) / 1000.0
                    tempF = tempC * 9.0 / 5.0 + 32.0
        except:
            logger.exception('Unable to read probe file:')
        return tempC, tempF

    def stop(self):
        self.__tReadTemperatures.stop()
            
    def scanLocalProbes(self):
        """Scan probes"""
        probes = {}
        try:
            logger.debug('Scanning local probes:')
            devices = glob.glob(os.path.join(self.BASE_DIR, '28*'))
            for device in devices:
                path = os.path.join(device, self.W1_SLAVE)
                logger.debug(' -> %s' % path)
                (tempC, tempF) = self.__scanProbe(path)
                if tempC and tempF:
                    uuid = self.__probeExists(path)
                    if not uuid:
                        #new probe
                        probes[str(moduuid.uuid4())] = {'path':path, 'tempC':tempC, 'tempF':tempF, 'enabled':False, 'local':True, 'name':self.__getFreeProbeName(probes)}
                    else:
                        #existing probe
                        probes[uuid] = {'path':path, 'tempC':tempC, 'tempF':tempF, 'enabled':self.config[uuid]['enabled'], 'local':True, 'name':self.config[uuid]['name']}
            #save probes
            self.__saveConfig(probes)
        except:
            logger.exception('Unable to scan probes:')
        return False, '', probes

    def addRemoteProbe(self, uri):
        """Add remote probe"""
        #TODO in scanLocalProbes handle remote probes!!!!
        #check if uri already exists
        found = False
        for uuid in self.config:
            if not self.config[uuid]['local']:
                if self.config[uuid]['path']==uri:
                    found = True
                    break;
        if not found:
            self.config[str(moduuid.uuid4())] = {'path':path, 'tempC':tempC, 'tempF':tempF, 'enabled':False, 'local':False, 'name':self.__getFreeProbeName()}
            self.__saveConfig(probes)
            return False, '', None
        else:
            return True, 'Probe already exists', None

    def removeRemoteProbe(self, uri):
        """Remove remote probe"""
        #check if uri already exists
        found = None
        for uuid in self.config:
            if not self.config[uuid]['local']:
                if self.config[uuid]['path']==uri:
                    found = uuid
                    break;
        if found:
            del self.config[found]
            self.__saveConfig(probes)
            return False, '', None
        else:
            return True, 'Probe not found', None

    def getEnabledProbes(self):
        """Return enabled probes"""
        enabled = {}
        for uuid in self.config:
            if self.config[uuid]['enabled']:
                enabled[uuid] = self.config[uuid]
        return False, '', enabled

    def getDisabledProbes(self):
        """Return disabled probes"""
        disabled = {}
        for uuid in self.config:
            if not self.config[uuid]['enabled']:
                disabled[uuid] = self.config[uuid]
        return False, '', disabled

    def getProbes(self):
        """Return all probes"""
        return False, '', self.config

    def enableProbe(self, uuid):
        """monitore specified probe"""
        if self.config.has_key(uuid):
            self.config[uuid]['enabled'] = True
            self.__saveConfig(self.config)
            return False, '', None
        else:
            return True, 'Probe not found', None

    def disableProbe(self, uuid):
        """remove probe from monitoring"""
        if self.config.has_key(uuid):
            self.config[uuid]['enabled'] = False
            self.__saveConfig(self.config)
            return False, '', None
        else:
            return True, 'Probe not found', None
                
    def getTemperatures(self):
        """Return temperatures of all probes"""
        temps = {}
        for uuid in self.config:
            if self.config[uuid]['enabled']:
                temps[uuid] = self.config[uuid]['tempC']
        return False, '', temps

    def getTemperature(self, uuid):
        """Return temperature of specified probe"""
        temp = ''
        if self.config.has_key(uuid) and self.config[uuid]['enabled']:
            temp = self.config[uuid]['tempC']
        return False, '', temp

    def setProbeName(self, uuid, name):
        """Set specified probe name"""
        outErr = False
        outMsg = ''
        oldname = ''
        if self.config.has_key(uuid):
            found = False
            for uu in self.config:
                if self.config[uu]['name']==name:
                    found = True
                    break
            if not found:
                #probe name is valid
                self.config[uuid]['name'] = name
                self.__saveConfig(self.config)
            else:
                #probe name already exists
                outErr = True
                outMsg = 'Probe name already exists'
                oldname = self.config[uuid]['name']
        else:
            #probe not found
            outError = True
            outMsg = 'Probe name already exists'
        return outErr, outMsg, oldname
                

if __name__ == '__main__':
    #testu
    p = Probes()
    print p.scanLocalProbes()
    print p.getEnabledProbes()
    print p.getDisabledProbes()
    print p.getAllProbes()
