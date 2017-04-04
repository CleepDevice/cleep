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
     * Add new motion sensor
     */
    self.addGenericMotionSensor = function(name, gpio, reverted) {
        return rpcService.sendCommand('add_motion_generic', 'sensors', {'name':name, 'gpio':gpio, 'reverted':reverted});
    };

    /**
     * Add new onewire temperature sensor
     */
    self.addOnewireTemperatureSensor = function(name, device, path, interval, offset, offsetUnit) {
        return rpcService.sendCommand('add_temperature_onewire', 'sensors', {'name':name, 'device':device, 'path':path, 'interval':interval, 'offset':offset, 'offset_unit':offsetUnit});
    };

    /**
     * Update motion sensor
     */
    self.updateGenericMotionSensor = function(uuid, name, reverted) {
        return rpcService.sendCommand('update_motion_generic', 'sensors', {'uuid':uuid, 'name':name, 'reverted':reverted});
    };

    /**
     * Update onewire temperature sensor
     */
    self.updateOnewireTemperatureSensor = function(uuid, name, interval, offset, offsetUnit) {
        return rpcService.sendCommand('update_temperature_onewire', 'sensors', {'uuid':uuid, 'name':name, 'interval':interval, 'offset':offset, 'offset_unit':offsetUnit});
    };

    /**
     * Reserve onewire bus gpio
     */
    self.reserveOnewireGpio = function(gpio) {
        return rpcService.sendCommand('reserve_onewire_gpio', 'sensors', {'gpio':gpio});
    };

    /**
     * Delete sensor
     */
    self.deleteSensor = function(uuid) {
        return rpcService.sendCommand('delete_sensor', 'sensors', {'uuid':uuid});
    };

    /**
     * Get onewires devices
     */
    self.getOnewires = function() {
        return rpcService.sendCommand('get_onewire_devices', 'sensors');
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

    /**
     * Catch temperature events
     */
    $rootScope.$on('sensors.temperature.update', function(event, uuid, params) {

        for( var i=0; i<raspiotService.devices.length; i++ )
        {   
            if( raspiotService.devices[i].uuid===uuid )
            {   
                raspiotService.devices[i].lastupdate = params.lastupdate;
                raspiotService.devices[i].celsius = params.celsius;
                raspiotService.devices[i].fahrenheit = params.fahrenheit;
                break;
            }   
        }   
    });
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('sensorsService', ['$q', '$rootScope', 'rpcService', 'raspiotService', sensorsService]);

