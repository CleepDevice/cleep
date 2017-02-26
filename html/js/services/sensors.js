/**
 * Sensors service
 * Handle sensors module requests
 */
var sensorsService = function($q, $rootScope, rpcService, objectsService) {
    var self = this;
    
    /** 
     * Set configuration directive names
     */
    self.setConfigs = function() {
        objectsService.addConfig('Sensors', 'sensorsConfigDirective');
    };

    /**
     * Load service devices (here sensors)
     */
    self.loadDevices = function() {
        rpcService.sendCommand('get_sensors', 'sensors')
            .then(function(resp) {
                var motions = [];
                var temperatures = [];
                var device = null;
                for( var name in resp.data )
                {
                    device = resp.data[name];
                    if( device.type==='motion' )
                    {
                        //add widget properties
                        device.widget = {
                            mdcolors: '{background:"default-primary-300"}'
                        };
                        if( device.on )
                        {
                            device.widget.mdcolors = '{background:"default-accent-400"}';
                        }
                        motions.push(device);
                    }
                    else if( device.type==='temperature' )
                    {
                        temperatures.push(device);
                    }
                }
                objectsService.addDevices('sensors', motions);
                objectsService.addDevices('sensors', temperatures);
            }, function(err) {
                console.log('loadDevices', err);
            });
    };

    /**
     * Return template name
     */
    self.getObjectTemplateName = function(object) {
        return object.type;
    };

    /**
     * Return raspi gpios (according to board version)
     */
    self.getRaspiGpios = function() {
        return rpcService.sendCommand('get_raspi_gpios', 'sensors')
            .then(function(resp) {
                return resp.data;
            });
    };

    /**
     * Add new motion sensor
     */
    self.addMotion = function(name, gpio, reverted) {
        return rpcService.sendCommand('add_motion', 'sensors', 
                {'name':name, 'gpio':gpio, 'reverted':reverted});
    };

    /**
     * Delete sensor
     */
    self.deleteSensor = function(name) {
        return rpcService.sendCommand('del_sensor', 'sensors', {'name':name})
            .then(function(resp) {
            });
    };

    /**
     * Catch motion on event
     */
    $rootScope.$on('event.motion.on', function(event, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {   
            if( objectsService.devices[i].__serviceName==='sensors' )
            {   
                if( objectsService.devices[i].name===params.sensor )
                {   
                    objectsService.devices[i].lastupdate = params.lastupdate;
                    objectsService.devices[i].on = true;
                    objectsService.devices[i].widget.mdcolors = '{background:"default-accent-400"}';
                    break;
                }   
            }   
        }   
    });

    /**
     * Catch motion off event
     */
    $rootScope.$on('event.motion.off', function(event, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {   
            if( objectsService.devices[i].__serviceName==='sensors' )
            {   
                if( objectsService.devices[i].name===params.sensor )
                {   
                    objectsService.devices[i].lastupdate = params.lastupdate;
                    objectsService.devices[i].on = false;
                    objectsService.devices[i].widget.mdcolors = '{background:"default-primary-300"}';
                    break;
                }   
            }   
        }   
    });
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('sensorsService', ['$q', '$rootScope', 'rpcService', 'objectsService', sensorsService]);

