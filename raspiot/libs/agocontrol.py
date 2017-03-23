import agoclient
import os
import logging
import json
from threading import Lock
import threading

#logging.basicConfig(filename='agosqueezebox.log', level=logging.INFO, format="%(asctime)s %(levelname)s : %(message)s")
#logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s : %(message)s")
logger = logging.getLogger(__name__)

agoclient.config.set_config_dir('/etc/opt/agocontrol/')

class AgoRaspiRelays(threading.Thread):
    
    CONF_DIR = 'agocontrol.conf'

    def __init__(self):
        threading.Thread.__init__(self)
        #connect agoclient
        self.client = agoclient.AgoConnection("raspirelays")
        self.client.add_handler(self.message_handler)
        self.client.add_event_handler(self.event_handler)
        self.client.add_device('raspirelays', 'raspirelays')

    def run(self):
        try:
            self.client.run()
        except:
            logger.exception('exception in AgoRaspiRelays')

    def stop(self):
        logger.info('stop agocontrol')
        self.client.stop()
        
    def message_handler(self, internalid, content):
        logger.info('message handler: %s %s' % (internalid, content))


    def event_handler(self, subject, content):
        """
        Event handler
        """
        """
        if subject=="event.environment.temperaturechanged":
            #only catch temperature events
            if self.config.has_key(content["uuid"]):
                #update sensor temperature
                self.config[content['uuid']]['temperature'] = content['level']
            else:
                #add new sensor
                self.config[content['uuid']] = {'monitored':False, 'temperature':0.0}
            self.__saveConfig()
        """
        #logger.info('event handler: %s %s' % (subject, content))
        pass

