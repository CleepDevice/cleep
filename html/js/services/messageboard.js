/**
 * MessageBoard service
 * Handle messageboard module requests
 */
var messageboardService = function($q, $rootScope, rpcService, objectsService) {
    var self = this;
    
    /**
     * Set configuration directive names
     */
    self.setConfigs = function() {
        objectsService.addConfig('MessageBoard', 'messageboardConfigDirective');
    };

    /**
     * Add new message
     */
    self.addMessage = function(message, start, end, scroll) {
        return rpcService.sendCommand('add_message', 'messageboard', {'message':message, 'start':start, 'end':end, 'scroll':scroll})
        .then(function(resp) {
            console.log(resp);
        }, function(err) {
            console.log('addMessage:', err);
        });
    };

    /**
     * Delete message
     */
    self.delMessage = function(index) {
        return rpcService.sendCommand('del_message', 'messageboard', {'index':index})
        .then(function(resp) {
        }, function(err) {
            console.log('delMessage:', err);
        });
    };

    /**
     * Set message duration
     */
    self.setDuration = function(duration) {
        return rpcService.sendCommand('set_duration', 'messageboard')
        .then(function(resp) {
            return resp.data;
        });
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('messageboardService', ['$q', '$rootScope', 'rpcService', 'objectsService', messageboardService]);

