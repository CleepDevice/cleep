/**
 * Scheduler service
 * Handle scheduler module requests
 */
var schedulerService = function($rootScope, rpcService, raspiotService) {
    var self = this;
    
    /**
     * Return directive infos
     */
    self.getDirectiveInfos = function() {
        return {
            label: 'Scheduler',
            name: 'schedulerConfigDirective'
        };  
    }; 

    /**
     * Change city
     */
    self.setCity = function(city) {
        return rpcService.sendCommand('set_city', 'scheduler', {'city':city});
    };

    /**
     * Get city
     */
    self.getCity = function() {
        return rpcService.sendCommand('get_city', 'scheduler');
    };

    /**
     * Get sunset/sunrise
     */
    self.getSun = function() {
        return rpcService.sendCommand('get_sun', 'scheduler');
    };

    /**
     * Get messages
     */
    self.getTime = function() {
        return rpcService.sendCommand('get_time', 'scheduler');
    };

    /**
     * Catch scheduler time event
     */
    $rootScope.$on('scheduler.time.now', function(event, uuid, params) {
        for( var i=0; i<raspiotService.devices.length; i++ )
        {
            if( raspiotService.devices[i].uuid==uuid )
            {
                console.log('update clock');
                raspiotService.devices[i].time = params.time;
                raspiotService.devices[i].sunset = params.sunset;
                raspiotService.devices[i].sunrise = params.sunrise;
                break;
            }
        }
    });
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('schedulerService', ['$rootScope', 'rpcService', 'raspiotService', schedulerService]);

