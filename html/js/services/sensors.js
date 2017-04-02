/**
 * Sensors service
 * Handle sensors module requests
 */
var sensorsService = function($q, $rootScope, rpcService, raspiotService) {
    var self = this;
    
    /** 
     * Return directive infos
     */
    self.getDirectiveInfos = function() {
        return {
            label: 'Sensors',
            name: 'sensorsConfigDirective'
        };  
    }; 

    /**
     * Init module devices
     */
    self.initDevices = function(devices)
    {   
        for( uuid in devices )
        {   
            if( devices[uuid].type==='motion' )
            {
                //change current color if gpio is on
                if( devices[uuid].on )
                {   
                    devices[uuid].__widget.mdcolors = '{background:"default-accent-400"}';
                }   
            }
        }

        return devices;
    };

    /**
     * Return raspi gpios (according to board version)
     */
    self.getRaspiGpios = function() {
        return rpcService.sendCommand('get_raspi_gpios', 'gpios');
    };

    /**
     * Add new sensor
     */
    self.addSensor = function(name, gpio, reverted, type) {
        if( type==='motion' )
        {
            return rpcService.sendCommand('add_motion', 'sensors', {'name':name, 'gpio':gpio, 'reverted':reverted});
        }
        else
        {
            toast.error('Unknown sensor type "' + type + '". No sensor added');
            var defered = $q.defer();
            defered.reject('bad sensor type');
            return defered.promise;
        }
    };

    /**
     * Delete sensor
     */
    self.deleteSensor = function(uuid) {
        return rpcService.sendCommand('delete_sensor', 'sensors', {'uuid':uuid});
    };

    /**
     * Update sensor
     */
    self.updateSensor = function(uuid, name, reverted) {
        return rpcService.sendCommand('update_sensor', 'sensors', {'uuid':uuid, 'name':name, 'reverted':reverted});
    };

    /**
     * Catch motion on event
     */
    $rootScope.$on('sensors.motion.on', function(event, uuid, params) {
        for( var i=0; i<raspiotService.devices.length; i++ )
        {   
            if( raspiotService.devices[i].uuid===uuid )
            {   
                raspiotService.devices[i].lastupdate = params.lastupdate;
                raspiotService.devices[i].on = true;
                raspiotService.devices[i].__widget.mdcolors = '{background:"default-accent-400"}';
                break;
            }   
        }   
    });

    /**
     * Catch motion off event
     */
    $rootScope.$on('sensors.motion.off', function(event, uuid, params) {

        for( var i=0; i<raspiotService.devices.length; i++ )
        {   
            if( raspiotService.devices[i].uuid===uuid )
            {   
                raspiotService.devices[i].lastupdate = params.lastupdate;
                raspiotService.devices[i].on = false;
                raspiotService.devices[i].__widget.mdcolors = '{background:"default-primary-300"}';
                break;
            }   
        }   
    });
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('sensorsService', ['$q', '$rootScope', 'rpcService', 'raspiotService', sensorsService]);

