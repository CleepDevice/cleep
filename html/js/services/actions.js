/**
 * Actions service
 * Handle action module requests
 */
var actionsService = function($q, $rootScope, rpcService) {
    var self = this;
    
    /**
     * Return directive infos
     */
    self.getDirectiveInfos = function() {
        return {
            label: 'Actions',
            name: 'actionsConfigDirective'
        };
    };

    /**
     * Delete script
     */
    self.deleteScript = function(script) {
        return rpcService.sendCommand('delete_script', 'actions', {'script':script});
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
RaspIot.service('actionsService', ['$q', '$rootScope', 'rpcService', actionsService]);

