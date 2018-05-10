/**
 * Pushover service
 * Handle pushover module requests
 */
var pushoverService = function($q, $rootScope, rpcService) {
    var self = this;

    self.setConfig = function(userkey, apikey) {
        return rpcService.sendCommand('set_config', 'pushover', {'userkey':userkey, 'apikey':apikey});
    };

    self.test = function() {
        return rpcService.sendCommand('test', 'pushover');
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('pushoverService', ['$q', '$rootScope', 'rpcService', pushoverService]);

