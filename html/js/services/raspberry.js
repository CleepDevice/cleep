/**
 * Raspberry service
 * Handle raspberry module requests
 */
var raspberryService = function($rootScope, rpcService, raspiotService) {
    var self = this;
    
    /**
     * Return directive infos
     */
    self.getDirectiveInfos = function() {
        return {
            label: 'Raspberry',
            name: 'raspberryConfigDirective'
        };  
    }; 

    /**
     * Change city
     */
    self.setCity = function(city) {
        return rpcService.sendCommand('set_city', 'raspberry', {'city':city});
    };

    /**
     * Get city
     */
    self.getCity = function() {
        return rpcService.sendCommand('get_city', 'raspberry');
    };

    /**
     * Get sunset/sunrise
     */
    self.getSun = function() {
        return rpcService.sendCommand('get_sun', 'raspberry');
    };

    /**
     * Get messages
     */
    self.getTime = function() {
        return rpcService.sendCommand('get_time', 'raspberry');
    };

    /**
     * Catch raspberry time event
     */
    $rootScope.$on('raspberry.time.now', function(event, uuid, params) {
        for( var i=0; i<raspiotService.devices.length; i++ )
        {
            if( raspiotService.devices[i].uuid==uuid )
            {
                raspiotService.devices[i].time = params.time;
                raspiotService.devices[i].sunset = params.sunset;
                raspiotService.devices[i].sunrise = params.sunrise;
                break;
            }
        }
    });
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('raspberryService', ['$rootScope', 'rpcService', 'raspiotService', raspberryService]);

