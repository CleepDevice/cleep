/**
 * Developer service
 * Handle developer module requests
 */
var developerService = function($q, $rootScope, rpcService) {
    var self = this;

    self.restartRaspiot = function() {
        return rpcService.sendCommand('restart_raspiot', 'developer');
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('developerService', ['$q', '$rootScope', 'rpcService', developerService]);

