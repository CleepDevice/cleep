/**
 * Action service
 * Handle action module requests
 */
var actionService = function($q, $rootScope, rpcService, objectsService) {
    var self = this;
    
    /**
     * Set configuration directive names
     */
    self.setConfigs = function() {
        objectsService.addConfig('Action', 'actionConfigDirective');
    };

    /**
     * Delete script
     */
    self.deleteScript = function(script) {
        return rpcService.sendCommand('delete_script', 'action', {'script':script});
    };

    /**
     * Get scripts
     */
    self.getScripts = function() {
        return rpcService.sendCommand('get_scripts', 'action')
        .then(function(resp) {
            return resp.data;
        });
    };

    /**
     * Disable script
     */
    self.disableScript = function(script, disabled) {
        return rpcService.sendCommand('disable_script', 'action', {'script':script, 'disabled':disabled});
    };
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('actionService', ['$q', '$rootScope', 'rpcService', 'objectsService', actionService]);

