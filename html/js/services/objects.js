/**
 * Objects factory
 * Share all needed objects
 */
var objectsService = function($rootScope) {
    var self = this;
    //list of devices stored by service
    //self.devices = {};
    self.devices = [];
    //list of services
    self.services = {};
    //list of configs
    self.configs = {};

    /**
     * Add service
     */
    self.addService = function(serviceName, service)
    {
        self.services[serviceName] = service;
    };

    /**
     * Add config
     */
    self.addConfig = function(configLabel, configDirectiveName)
    {
        if( !self.configs[configLabel] )
        {
            self.configs[configLabel] = {
                'cleanLabel': configLabel.replace(' ',''),
                'directive': configDirectiveName
            }
        }
    };

    /**
     * Add devices to factory
     * It will remove existing service ones before adding new ones
     * @param service: device service
     * @param devices: list of devices
     * @param type: specify devices type (if not specified, use set service name)
     */
    self.addDevices = function(service, devices, type)
    {
        if( !service )
        {
            console.error('Service not specified');
        }
        else
        {
            console.log('add devices for service '+service, devices);

            //clear existing service objects
            var delCount = 0;
            for( var i=self.devices.length-1; i>=0; i--)
            {
                if( self.devices[i].__serviceName===service )
                {
                    self.devices.splice(i, 1);
                    delCount++;
                }
            }
            console.log(delCount+' objects deleted');

            //force devices type
            if( !type )
            {
                type = service;
            }

            //flatten devices and append some stuff:
            // - __service: to easily access to service functions
            // - __serviceName: service name (used internally)
            // - __type: set it to service name if not alreay exist (used to filter devices)
            for( var key in devices )
            {
                devices[key].__type = type;
                devices[key].__service = self.services[service];
                devices[key].__serviceName = service;
                self.devices.push(devices[key]);
            }
        }
    };

    /**
     * Delete specified device
     */
    self.delDevice = function(device)
    {
        if( device )
        {
            for( var i=0; i<self.devices.length; i++ )
            {
                if( self.devices[i]===device )
                {
                    console.log('device found');
                }
            }
        }
    }

    /**
     * Return object template name (without path and file extention)
     */
    self.getObjectTemplateName = function(object)
    {
        if( object )
        {
            //check object service
            if( !object.__serviceName || !self.services[object.__serviceName] )
            {
                //object is not configured properly, return default
                return 'default';
            }

            //var service = object.__service;
            if( typeof self.services[object.__serviceName].getObjectTemplateName==='undefined' )
            {
                //no method to get object template specified in service, return default
                return 'default';
            }

            return self.services[object.__serviceName].getObjectTemplateName(object);
        }
        else
        {
            console.error('Unable to get object template, missing parameter');
            return 'default';
        }
    }
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('objectsService', ['$rootScope', objectsService]);

