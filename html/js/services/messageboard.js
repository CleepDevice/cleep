/**
 * MessageBoard service
 * Handle messageboard module requests
 */
var messageboardService = function($q, $rootScope, rpcService, raspiotService) {
    var self = this;
    
    /**
     * Return directive infos
     */
    self.getDirectiveInfos = function() {
        return {
            label: 'MessageBoard',
            name: 'messageboardConfigDirective'
        };
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
        return rpcService.sendCommand('get_speed', 'messageboard');
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

    /**
     * Get board status (on/off)
     */
    self.isOn = function() {
        return rpcService.sendCommand('is_on', 'messageboard');
    };

    /**
     * Catch message updated
     */
    $rootScope.$on('messageboard.message.update', function(event, uuid, params) {
        for( var i=0; i<raspiotService.devices.length; i++ )
        {
            if( raspiotService.devices[i].uuid==uuid )
            {
                var message = self._formatMessageData(params);
                raspiotService.devices[i].message = message.message;
                raspiotService.devices[i].lastupdate = message.lastupdate;
            }
        }
    });

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('messageboardService', ['$q', '$rootScope', 'rpcService', 'raspiotService', messageboardService]);

