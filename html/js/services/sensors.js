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
                objectsService.addDevices('sensors', resp.data);
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
    self.addMotion = function(name, gpio, onDuration) {
        return rpcService.sendCommand('add_motion', 'sensors', 
                {'name':name, 'gpio':gpio, 'on_duration':onDuration});
    };

    /**
     * Delete sensor
     */
    self.delSensor = function(name) {
        return rpcService.sendCommand('del_sensor', 'sensors', {'name':name})
        .then(function(resp) {
        });
    };

    /**
     * Catch motion on event
     */
    $rootScope.$on('event.motion.on', function(event, params) {
        console.log('motion received', event, params);
        for( var i=0; i<objectsService.devices.length; i++ )
        {   
            console.log(''+objectsService.devices[i].__serviceName+'===sensors');
            if( objectsService.devices[i].__serviceName==='sensors' )
            {   
                console.log(''+objectsService.devices[i].name+'==='+params.sensor);
                if( objectsService.devices[i].name===params.sensor )
                {   
                    objectsService.devices[i]['on'] = true;
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
                    objectsService.devices[i]['on'] = false;
                    break;
                }   
            }   
        }   
    });
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('sensorsService', ['$q', '$rootScope', 'rpcService', 'objectsService', sensorsService]);

