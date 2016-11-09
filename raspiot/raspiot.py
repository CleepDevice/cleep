import logging
import os
import json
from bus import BusClient
from threading import Lock
import time
import copy

__all__ = ['RaspIot']

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class RaspIot(BusClient):
    """
    Base raspiot class
    It implements :
     - configuration saving
     - message bus access
    """
    CONFIG_DIR = '/etc/raspiot/'

    def __init__(self, bus):
        BusClient.__init__(self, bus)
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
            path = os.path.join(RaspIot.CONFIG_DIR, self.CONFIG_FILE)
            logger.debug('Loading conf file %s' % path)
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
            logger.exception('Unable to load config file %s:' % path)
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
            path = os.path.join(RaspIot.CONFIG_DIR, self.CONFIG_FILE)
            f = open(path, 'w')
            f.write(json.dumps(config))
            f.close()
            force_reload = True
        except:
            logger.exception('Unable to write config file %s:' % path)
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
        return copy.deepcopy(self._config)

    def _get_dependencies(self):
        """
        Return module dependencies
        """
        return []

    def stop(self):
        """
        Stop process
        """
        BusClient.stop(self)

