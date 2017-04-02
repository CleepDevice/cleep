/**
 * Sensors service
 * Handle sensors module requests
 */
var sensorsService = function($q, $rootScope, rpcService, objectsService) {
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
     * Load service devices (here sensors)
     */
    self.loadDevices = function() {
        rpcService.sendCommand('get_module_devices', 'sensors')
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
                objectsService.addDevices('sensors', motions, 'motion');
                objectsService.addDevices('sensors', temperatures, 'temperature');
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
        for( var i=0; i<objectsService.devices.length; i++ )
        {   
            if( objectsService.devices[i].uuid===uuid )
            {   
                objectsService.devices[i].lastupdate = params.lastupdate;
                objectsService.devices[i].on = true;
                objectsService.devices[i].widget.mdcolors = '{background:"default-accent-400"}';
                break;
            }   
        }   
    });

    /**
     * Catch motion off event
     */
    $rootScope.$on('sensors.motion.off', function(event, uuid, params) {

        for( var i=0; i<objectsService.devices.length; i++ )
        {   
            if( objectsService.devices[i].uuid===uuid )
            {   
                objectsService.devices[i].lastupdate = params.lastupdate;
                objectsService.devices[i].on = false;
                objectsService.devices[i].widget.mdcolors = '{background:"default-primary-300"}';
                break;
            }   
        }   
    });
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('sensorsService', ['$q', '$rootScope', 'rpcService', 'objectsService', sensorsService]);

