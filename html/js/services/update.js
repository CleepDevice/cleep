/**
 * Update service
 * Handle update module requests
 */
var updateService = function($rootScope, rpcService, raspiotService) {
    var self = this;
    
    /**
     * Get status
     */
    self.getStatus = function(full) {
        if( full )
        {
            //return full status (maybe huge!)
            return rpcService.sendCommand('get_full_status', 'update');
        }
        else
        {
            //return light status
            return rpcService.sendCommand('get_status', 'update');
        }
    };

    /**
     * Check for available updates
     */
    self.checkUpdates = function() {
        return rpcService.sendCommand('check_updates', 'update');
    };

    /**
     * Cancel current update
     */
    self.cancelUpdate = function() {
        return rpcService.sendCommand('cancel', 'update');
    };

    /**
     * Set automatic update
     */
    self.setAutomaticUpdate = function(automaticUpdate) {
        return rpcService.sendCommand('set_automatic_update', 'update', {'automatic_update':automaticUpdate});
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('updateService', ['$rootScope', 'rpcService', 'raspiotService', updateService]);

