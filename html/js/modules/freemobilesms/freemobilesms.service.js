/**
 * FreemobileSms service
 * Handle freemobilesms module requests
 */
var freemobilesmsService = function($q, $rootScope, rpcService) {
    var self = this;

    self.setCredentials = function(userid, apikey) {
        return rpcService.sendCommand('set_credentials', 'freemobilesms', {'userid':userid, 'apikey':apikey});
    };

    self.test = function() {
        return rpcService.sendCommand('test', 'freemobilesms');
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('freemobilesmsService', ['$q', '$rootScope', 'rpcService', freemobilesmsService]);

