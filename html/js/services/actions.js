/**
 * Actions service
 * Handle action module requests
 */
var actionsService = function($q, $rootScope, rpcService, objectsService) {
    var self = this;
    
    /**
     * Set configuration directive names
     */
    self.setConfigs = function() {
        objectsService.addConfig('Actions', 'actionsConfigDirective');
    };

    /**
     * Delete script
     */
    self.deleteScript = function(script) {
        return rpcService.sendCommand('delete_script', 'actions', {'script':script});
    };

    /**
     * Get scripts
     */
    self.getScripts = function() {
        return rpcService.sendCommand('get_scripts', 'actions')
            .then(function(resp) {
                return resp.data;
            });
    };

    /**
     * Disable script
     */
    self.disableScript = function(script, disabled) {
        return rpcService.sendCommand('disable_script', 'actions', {'script':script, 'disabled':disabled});
    };

    /**
     * Download script
     */
    self.downloadScript = function(script) {
        rpcService.download('download_script', 'actions', {'script': script});
    };

    /**
     * Upload script
     */
    self.uploadScript = function(file, onSuccess, onError) {
        return rpcService.upload('add_script', 'actions', file, onSuccess, onError);
    };
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('actionsService', ['$q', '$rootScope', 'rpcService', 'objectsService', actionsService]);

