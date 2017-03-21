/**
 * Objects factory
 * Share all needed objects
 */
var objectsService = function($rootScope) {
    var self = this;
    //list of devices stored by service
    self.devices = [];
    //list of services
    self.services = {};
    //list of configs
    self.configs = {};
    self.configsCount = 0;

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
            self.configsCount++;
        }
    };

    /**
     * Add devices to factory
     * It will remove existing service ones before adding new ones
     * @param service: device service name
     * @param devices: list of devices (must be an associative container (js object), not an array 
     *                 and it can contains object directly)
     * @param type: specify devices type (if not specified, use service name)
     * @param widget: specify user widget customization
     */
    self.addDevices = function(service, devices, type, widget)
    {
        if( angular.isUndefined(service) || service===null )
        {
            console.error('Service not specified');
        }
        else if( angular.isUndefined(devices) || service===null ) {
            console.warn('No device specified for service "' + service + "'");
        }
        else
        {
            //force devices type
            if( angular.isUndefined(type) || type===null )
            {
                type = service;
            }

            //set empty widget structure
            if( angular.isUndefined(widget) || widget===null )
            {
                //set default widget values like background color
                widget = {
                    mdcolors: '{background:"default-primary-300"}'
                };
            }

            //clear existing service objects
            var delCount = 0;
            for( var i=self.devices.length-1; i>=0; i--)
            {
                if( self.devices[i].__type===type )
                {
                    self.devices.splice(i, 1);
                    delCount++;
                }
            }

            //flatten devices and append some stuff:
            // - __service: to easily access to service functions
            // - __serviceName: service name (used internally)
            // - __type: set it to service name if not alreay exist (used to filter devices)
            // - __widgetCtlName: set name of device widget controller (based on device type)
            // - widget: set object to store user widget customization
            for( var key in devices )
            {
                devices[key].__type = type;
                devices[key].__service = self.services[service];
                devices[key].__serviceName = service;
                devices[key].__widgetCtlName = type + 'Ctl';
                //add widget properties if necessary
                if( angular.isUndefined(devices[key].widget) || devices[key].widget===null )
                {
                    devices[key].widget = {};
                    for( var prop in widget ) {
                        devices[key].widget[prop] = widget[prop];
                    }
                }
                self.devices.push(devices[key]);
            }
        }
    };

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

