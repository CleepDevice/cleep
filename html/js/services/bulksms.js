/**
 * BulkSms service
 * Handle bulksms module requests
 */
var bulksmsService = function($q, $rootScope, rpcService) {
    var self = this;

    self.setCredentials = function(username, password, phoneNumbers) {
        return rpcService.sendCommand('set_credentials', 'bulksms', {'username':username, 'password':password, 'phone_numbers':phoneNumbers});
    };

    self.getCredits = function() {
        return rpcService.sendCommand('get_credits', 'bulksms');
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('bulksmsService', ['$q', '$rootScope', 'rpcService', bulksmsService]);

