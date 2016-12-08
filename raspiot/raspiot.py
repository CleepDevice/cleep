import logging
import os
import json
from bus import BusClient
from threading import Lock, Thread
import time
import copy

__all__ = ['RaspIot', 'CommandError']

class CommandError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class RaspIot(BusClient):
    """
    Base raspiot class
    It implements :
     - configuration saving
     - message bus access
    """
    CONFIG_DIR = '/etc/raspiot/'
    MODULE_DEPS = []

    def __init__(self, bus):
        #init
        BusClient.__init__(self, bus)
        self.logger = logging.getLogger(self.__class__.__name__)

        #load module configuration
        self.__configLock = Lock()
        self._config = self._load_config()

    def __del__(self):
        self.stop()

    def __file_is_empty(self, path):
        """
        Return True if file is empty
        """
        return os.path.isfile(path) and not os.path.getsize(path)>0

    def _load_config(self):
        """
        Load config file
        """
        self.__configLock.acquire(True)
        out = None
        try:
            path = os.path.join(RaspIot.CONFIG_DIR, self.MODULE_CONFIG_FILE)
            self.logger.debug('Loading conf file %s' % path)
            if os.path.exists(path) and not self.__file_is_empty(path):
                f = open(path, 'r')
                raw = f.read()
                f.close()
            else:
                #no conf file yet. Create default one
                f = open(path, 'w')
                default = {}
                raw = json.dumps(default)
                f.write(raw)
                f.close()
                time.sleep(.25) #make sure file is written
            self._config = json.loads(raw)
            out = self._config
        except:
            self.logger.exception('Unable to load config file %s:' % path)
        self.__configLock.release()
        return out
 
    def _save_config(self, config):
        """
        Save config file
        """
        self.__configLock.acquire(True)
        out = False
        force_reload = False
        try:
            path = os.path.join(RaspIot.CONFIG_DIR, self.MODULE_CONFIG_FILE)
            f = open(path, 'w')
            f.write(json.dumps(config))
            f.close()
            force_reload = True
        except:
            self.logger.exception('Unable to write config file %s:' % path)
        self.__configLock.release()
        if force_reload:
            #reload config
            out = self._load_config()
        return out

    def _reload_config(self):
        """
        Reload configuration
        Just an alias to _load_configuration
        """
        self._load_config()

    def _get_config(self):
        """
        Return copy of config dict
        """
        self.__configLock.acquire(True)
        copy_ = copy.deepcopy(self._config)
        self.__configLock.release()
        return copy_

    def _check_config(self, keys):
        """
        Check config files looking for specified keys.
        If key not found, key is added with specified default value
        @param keys: dict {'key1':'default value1', ...}
        """
        config = self._get_config()
        fixed = False
        for key in keys:
            if not config.has_key(key):
                #fix missing key
                config[key] = keys[key]
                fixed = True
        if fixed:
            self.logger.debug('Config file fixed')
            self._save_config(config)

    def _get_dependencies(self):
        """
        Return module dependencies
        """
        return self.DEPS

    def stop(self):
        """
        Stop process
        """
        BusClient.stop(self)

    def __get_public_methods(self, obj):
        """
        Return "public" methods of specified object
        @return array
        """
        ms = dir(obj)
        for m in ms[:]:
            if m.startswith('_') or not callable(getattr(obj, m)):
                ms.remove(m)
        return ms

