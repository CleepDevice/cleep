/**
 * Gpios service
 * Handle gpios module requests
 */
var gpiosService = function($q, $rootScope, rpcService, objectsService) {
    var self = this;
    
    /**
     * Return directive infos
     */
    self.getDirectiveInfos = function() {
        return {
            label: 'Gpios',
            name: 'gpiosConfigDirective'
        };
    };

    /**
     * Load service devices (here gpios)
     */
    self.loadDevices = function() {
        var defered = $q.defer();
        rpcService.sendCommand('get_module_devices', 'gpios')
            .then(function(resp) {
                for( var deviceId in resp.data )
                {
                    //set widget props
                    resp.data[deviceId].widget = {
                        mdcolors: '{background:"default-primary-300"}'
                    };
                    if( resp.data[deviceId].on )
                    {
                        resp.data[gpio].widget.mdcolors = '{background:"default-accent-400"}';
                    }
                }
                objectsService.addDevices('gpios', resp.data, 'gpio');
                defered.resolve('devices loaded');
            }, function(err) {
                console.error('loadDevices', err);
                defered.reject('Unable to load devices');
            });
        return defered.promise;
    };

    /**
     * Return template name according to gpio mode
     */
    self.getObjectTemplateName = function(object) {
        if( object.mode==='in') 
        {
            return 'gpioInput';
        }
        return 'gpioOutput';
    };

    /** 
     * Get config
     */
    self.getConfig = function() {
        return rpcService.sendCommand('get_module_config', 'actions');
    };

    /**
     * Return raspi gpios (according to board version)
     */
    self.getRaspiGpios = function() {
        return rpcService.sendCommand('get_raspi_gpios', 'gpios');
    };

    /**
     * Add new gpio
     */
    self.addGpio = function(name, gpio, mode, keep, reverted) {
        return rpcService.sendCommand('add_gpio', 'gpios', {'name':name, 'gpio':gpio, 'mode':mode, 'keep':keep, 'reverted':reverted});
    };

    /**
     * Delete gpio
     */
    self.deleteGpio = function(uuid) {
        return rpcService.sendCommand('delete_gpio', 'gpios', {'uuid':uuid});
    };

    /**
     * Update device
     */
    self.updateGpio = function(uuid, name, keep, reverted) {
        return rpcService.sendCommand('update_gpio', 'gpios', {'uuid':uuid, 'name':name, 'keep':keep, 'reverted':reverted});
    };

    /**
     * Turn on specified gpio
     */
    self.turnOn = function(uuid) {
        return rpcService.sendCommand('turn_on', 'gpios', {'uuid':uuid});
    };

    /**
     * Turn off specified gpio
     */
    self.turnOff = function(uuid) {
        return rpcService.sendCommand('turn_off', 'gpios', {'uuid':uuid});
    };

    /**
     * Catch gpio on events
     */
    $rootScope.$on('gpios.gpio.on', function(event, uuid, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].uuid==uuid )
            {
                if( objectsService.devices[i].on===false )
                {
                    objectsService.devices[i].on = true;
                    objectsService.devices[i].widget.mdcolors = '{background:"default-accent-400"}';
                    break;
                }
            }
        }
    });

    /**
     * Catch gpio off events
     */
    $rootScope.$on('gpios.gpio.off', function(event, uuid, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].uuid==uuid )
            {
                if( objectsService.devices[i]['on']===true )
                {
                    objectsService.devices[i]['on'] = false;
                    objectsService.devices[i].widget.mdcolors = '{background:"default-primary-300"}';
                    break;
                }
            }
        }
    });
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('gpiosService', ['$q', '$rootScope', 'rpcService', 'objectsService', gpiosService]);

