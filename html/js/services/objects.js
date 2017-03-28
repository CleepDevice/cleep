/**
 * Objects service
 * Share all needed objects:
 *  - angular services
 *  - angular directives
 *  - devices
 */
var objectsService = function($q, rpcService, toast) {
    var self = this;
    self._initPromise = null;
    //list of devices
    self.devices = [];
    //list of angular services
    self.services = {};
    //list of angular directives
    self.directives = [];

    /**
     * Init service objects
     * Internal usage, do not use
     */
    self._init = function()
    {

        if( self._initPromise!==null )
        {
            //promise already exists, return it
            return self._initPromise;
        }

        self._initPromise = $q.defer();

        //get server modules and inject services. Finally load devices
        rpcService.getModules()
        .then(function(resp) {
            //for(var i=0; i<modules.length; i++)
            for( var module in resp)
            {   
                //prepare angular service and directive
                var serviceName = module; //modules[i];
                var angularService = module + 'Service'; //modules[i]+'Service';
                if( $injector.has(angularService) )
                {   
                    //module has service, inject it then add it
                    objectsService._addService(serviceName, $injector.get(angularService));

                    //load service devices if possible
                    if( typeof objectsService.services[serviceName].loadDevices !== 'undefined' )
                    {   
                        //load service devices
                        objectsService.services[serviceName].loadDevices();
                    }   
     
                    //add module config directives
                    directive = objectsService.services[serviceName].getDirectiveInfos();
                    objectsService._addDirective( directive['label'], directive['name'] );
                }   
                else
                {   
                    //module has no associated service
                    console.warn('Module "'+serviceName+'" has no angular service');
                }  
            }   

            //save modules configurations
            configsService._setConfigs(resp);

            //console.log("DEVICES", objectsService.devices);
            //console.log("SERVICES", objectsService.services);
            //console.log("DIRECTIVES", objectsService.directives);

            self._initPromise.resolve('objects loaded');
        }, function(err) {
            toast.error('Fatal error: unable to load system');
            self._initPromise.reject('');
        }); 

        return self._initPromise;
    };

    /**
     * Add angular service to factory
     * Internal usage, do not use
     */
    self._addService = function(serviceName, service)
    {
        self.services[serviceName] = service;
    };

    /**
     * Add angular directive to factory
     * Internal usage, do not use
     * @param directiveLabel: label that will be displayed on configuration tab
     * @param directiveName: angular directive name
     */
    self._addDirective = function(directiveLabel, directiveName)
    {
        var found = false;
        for( var i=0; i<self.directives.length; i++ )
        {
            if( self.directives[i].directive===directive )
            {
                found = true;
                break;
            }
        }

        if( !found )
        {
            self.directives.push({
                label: directiveLabel,
                cleanLabel: directiveLabel.replace(' ',''),
                directive: directiveName
            });
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

    /*return {
        _initPromise: self._initPromise,
        _addService: self._addService,
        _addDirective: self._addDirective,
        addDevice: self.addDevice
    };*/

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('objectsService', ['$q', 'rpcService', 'toastService', objectsService]);

