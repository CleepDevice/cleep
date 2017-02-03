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

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('schedulerService', ['$q', '$rootScope', 'rpcService', 'objectsService', schedulerService]);

