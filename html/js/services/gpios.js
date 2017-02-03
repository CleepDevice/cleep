/**
 * Gpios service
 * Handle gpios module requests
 */
var gpiosService = function($q, $rootScope, rpcService, objectsService) {
    var self = this;
    
    /**
     * Set configuration directive names
     */
    self.setConfigs = function() {
        objectsService.addConfig('Gpios', 'gpiosConfigDirective');
    };

    /**
     * Load service devices (here gpios)
     */
    self.loadDevices = function() {
        rpcService.sendCommand('get_gpios', 'gpios')
            .then(function(resp) {
                //add key to device structure
                for( var gpio in resp.data )
                {
                    resp.data[gpio].gpio = gpio;
                }
                objectsService.addDevices('gpios', resp.data);
            }, function(err) {
                console.error('loadDevices', err);
            });
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
     * Return raspi gpios (according to board version)
     */
    self.getRaspiGpios = function() {
        return rpcService.sendCommand('get_raspi_gpios', 'gpios')
            .then(function(resp) {
                return resp.data;
            }, function(err) {
                console.log('getRaspiGpios:', err);
            });
    };

    /**
     * Add new gpio
     */
    self.addGpio = function(name, gpio, mode, keep) {
        return rpcService.sendCommand('add_gpio', 'gpios', {'name':name, 'gpio':gpio, 'mode':mode, 'keep':keep})
            .then(function(resp) {
            }, function(err) {
                console.log('addGpio:', err);
            });
    };

    /**
     * Delete gpio
     */
    self.deleteGpio = function(gpio) {
        console.log('delete '+gpio);
        return rpcService.sendCommand('delete_gpio', 'gpios', {'gpio':gpio})
            .then(function(resp) {
            }, function(err) {
                console.log('deleteGpio:', err);
            });
    };

    /**
     * Turn on specified gpio
     */
    self.turnOn = function(gpio) {
        return rpcService.sendCommand('turn_on', 'gpios', {'gpio':gpio})
            .then(function(resp) {
                return resp.data;
            }, function(err) {
                console.log('turnOn:', err);
            });
    };

    /**
     * Turn off specified gpio
     */
    self.turnOff = function(gpio) {
        return rpcService.sendCommand('turn_off', 'gpios', {'gpio':gpio})
            .then(function(resp) {
                return resp.data;
            }, function(err) {
                console.log('turnOff:', err);
            });
    };

    /**
     * Catch gpio on events
     */
    $rootScope.$on('event.gpio.on', function(event, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].__serviceName==='gpios' )
            {
                if( objectsService.devices[i].gpio===params.gpio )
                {
                    if( objectsService.devices[i]['on']===false )
                    {
                        objectsService.devices[i]['on'] = true;
                    }
                    break;
                }
            }
        }
    });

    /**
     * Catch gpio off events
     */
    $rootScope.$on('event.gpio.off', function(event, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].__serviceName==='gpios' )
            {
                if( objectsService.devices[i].gpio===params.gpio )
                {
                    if( objectsService.devices[i]['on']===true )
                    {
                        objectsService.devices[i]['on'] = false;
                    }
                    break;
                }
            }
        }
    });
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('gpiosService', ['$q', '$rootScope', 'rpcService', 'objectsService', gpiosService]);

