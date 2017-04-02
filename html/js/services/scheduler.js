/**
 * Scheduler service
 * Handle scheduler module requests
 */
var schedulerService = function($q, $rootScope, rpcService, objectsService) {
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
     * Load service devices (here add static device such as clock)
     */
    self.loadDevices = function() {
        rpcService.sendCommand('get_time', 'scheduler')
            .then(function(resp) {
                resp.data.name = 'Clock';
                objectsService.addDevices('scheduler', {'clock':resp.data}, 'clock');
            }, function(err) {
                console.error('loadDevices', err);
            });
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
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].uuid==uuid )
            {
                objectsService.devices[i].time = params.time;
                objectsService.devices[i].sunset = params.sunset;
                objectsService.devices[i].sunrise = params.sunrise;
                break;
            }
        }
    });
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('schedulerService', ['$q', '$rootScope', 'rpcService', 'objectsService', schedulerService]);

