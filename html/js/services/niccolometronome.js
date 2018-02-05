/**
 * Niccolo Metronome service
 * Handle Niccolometronome module requests
 */
var niccolometronomeService = function($q, $rootScope, rpcService, raspiotService) {
    var self = this;

    self.addPhrase = function(phrase, command, bpm) {
        return rpcService.sendCommand('add_phrase', 'niccolometronome', {'phrase':phrase, 'command':parseInt(command), 'bpm':parseInt(bpm)})
            .then(function() {
                return raspiotService.reloadModuleConfig('niccolometronome');
            });
    };

    self.removePhrase = function(id) {
        return rpcService.sendCommand('remove_phrase', 'niccolometronome', {'id':id})
            .then(function() {
                return raspiotService.reloadModuleConfig('niccolometronome');
            });
    };

    self.setBpm = function(bpm) {
        return rpcService.sendCommand('set_bpm', 'niccolometronome', {'bpm':parseInt(bpm)})
            .then(function() {
                return raspiotService.reloadModuleConfig('niccolometronome');
            });
    };

    self.startMetronome = function() {
        return rpcService.sendCommand('start_metronome', 'niccolometronome')
            .then(function() {
                return raspiotService.reloadModuleConfig('niccolometronome');
            });
    };

    self.stopMetronome = function() {
        return rpcService.sendCommand('stop_metronome', 'niccolometronome')
            .then(function() {
                return raspiotService.reloadModuleConfig('niccolometronome');
            });
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('niccolometronomeService', ['$q', '$rootScope', 'rpcService', 'raspiotService', niccolometronomeService]);

