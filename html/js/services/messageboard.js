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
    self.addMessage = function(message, start, end) {
        return rpcService.sendCommand('add_message', 'messageboard', {'message':message, 'start':start, 'end':end})
            .then(function(resp) {
            }, function(err) {
                console.log('addMessage:', err);
            });
    };

    /**
     * Delete message
     */
    self.deleteMessage = function(uuid) {
        return rpcService.sendCommand('delete_message', 'messageboard', {'uuid':uuid})
            .then(function(resp) {
            }, function(err) {
                console.log('deleteMessage:', err);
            });
    };

    /**
     * Get messages
     */
    self.getMessages = function() {
        return rpcService.sendCommand('get_messages', 'messageboard')
            .then(function(resp) {
                return resp.data;
            }, function(err) {
                console.log('getMessages:', err);
            });
    };

    /**
     * Set message duration
     */
    self.setDuration = function(duration) {
        return rpcService.sendCommand('set_duration', 'messageboard', {'duration':duration});
    };

    /**
     * Get duration
     */
    self.getDuration = function() {
        return rpcService.sendCommand('get_duration', 'messageboard')
            .then(function(resp) {
                return resp.data;
            });
    };

    /**
     * Set scrolling message speed
     */
    self.setSpeed = function(speed) {
        return rpcService.sendCommand('set_speed', 'messageboard', {'speed':speed});
    };

    /**
     * Get speed
     */
    self.getSpeed = function() {
        return rpcService.sendCommand('get_speed', 'messageboard')
            .then(function(resp) {
                return resp.data;
            });
    };

    /**
     * Set board units
     */
    self.setUnits = function(minutes, hours, days) {
        return rpcService.sendCommand('set_units', 'messageboard', {'minutes':minutes, 'hours':hours, 'days':days});
    };

    /**
     * Get board units
     */
    self.getUnits = function() {
        return rpcService.sendCommand('get_units', 'messageboard')
            .then(function(resp) {
                return resp.data;
            });
    };

    /**
     * Turn off board
     */
    self.turnOff = function() {
        return rpcService.sendCommand('turn_off', 'messageboard');
    };

    /**
     * Turn on board
     */
    self.turnOn = function() {
        return rpcService.sendCommand('turn_on', 'messageboard');
    };
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('messageboardService', ['$q', '$rootScope', 'rpcService', 'objectsService', messageboardService]);

