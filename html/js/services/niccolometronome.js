/**
 * Niccolo Metronome service
 * Handle Niccolometronome module requests
 */
var niccolometronomeService = function($q, $rootScope, rpcService) {
    var self = this;

    self.playSound = function() {
        return rpcService.sendCommand('play_sound', 'niccolometronome');
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('niccolometronomeService', ['$q', '$rootScope', 'rpcService', niccolometronomeService]);

