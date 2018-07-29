/**
 * Parameters service
 * Handle parameters module requests
 */
var parametersService = function($rootScope, rpcService, raspiotService) {
    var self = this;
    
    /**
     * Get sunset/sunrise
     */
    self.getSun = function() {
        return rpcService.sendCommand('get_sun', 'parameters');
    };

    /**
     * Set hostname
     */
    self.setHostname = function(hostname) {
        return rpcService.sendCommand('set_hostname', 'parameters', {'hostname':hostname});
    };

    /**
     * Set position
     */
    self.setPosition = function(lat, long) {
        return rpcService.sendCommand('set_position', 'parameters', {'latitude':lat, 'longitude':long}, 20);
    };

    /**
     * Catch time event
     */
    $rootScope.$on('system.time.now', function(event, uuid, params) {
        for( var i=0; i<raspiotService.devices.length; i++ )
        {
            if( raspiotService.devices[i].uuid==uuid )
            {
                raspiotService.devices[i].timestamp = params.timestamp;
                raspiotService.devices[i].sunset = params.sunset;
                raspiotService.devices[i].sunrise = params.sunrise;
                break;
            }
        }
    });

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('parametersService', ['$rootScope', 'rpcService', 'raspiotService', parametersService]);

