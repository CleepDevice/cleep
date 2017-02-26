/**
 * Scheduler service
 * Handle scheduler module requests
 */
var schedulerService = function($q, $rootScope, rpcService, objectsService) {
    var self = this;
    
    /**
     * Set configuration directive names
     */
    self.setConfigs = function() {
        objectsService.addConfig('Scheduler', 'schedulerDirective');
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
        return rpcService.sendCommand('set_city', 'scheduler', {'city':city})
            .then(function(resp) {
                return resp.data
            }, function(err) {
                console.log('setCity:', err);
            });
    };

    /**
     * Get city
     */
    self.getCity = function() {
        return rpcService.sendCommand('get_city', 'scheduler')
            .then(function(resp) {
                return resp.data;
            }, function(err) {
                console.log('getCity:', err);
            });
    };

    /**
     * Get sunset/sunrise
     */
    self.getSun = function() {
        return rpcService.sendCommand('get_sun', 'scheduler')
            .then(function(resp) {
                return resp.data;
            }, function(err) {
                console.log('getSun:', err);
            });
    };

    /**
     * Get messages
     */
    self.getTime = function() {
        return rpcService.sendCommand('get_time', 'scheduler')
            .then(function(resp) {
                return resp.data;
            }, function(err) {
                console.log('getMessages:', err);
            });
    };

    /**
     * Catch scheduler time event
     */
    $rootScope.$on('event.time.now', function(event, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].__serviceName==='scheduler' && objectsService.devices[i].__type=='clock' )
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

