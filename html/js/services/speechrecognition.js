/**
 * Speechrecogniton service
 * Handle speechrecognition module requests
 */
var speechrecognitionService = function($q, $rootScope, rpcService, raspiotService) {
    var self = this;

    self.setProvider = function(provider, apikey) {
        return rpcService.sendCommand('set_provider', 'speechrecognition', {'provider':provider, 'apikey':apikey})
            .then(function() {
                return raspiotService.reloadModuleConfig('speechrecognition');
            });
    };

    self.setHotwordToken = function(token) {
        return rpcService.sendCommand('set_hotword_token', 'speechrecognition', {'token':token})
            .then(function() {
                return raspiotService.reloadModuleConfig('speechrecognition');
            });
    };

    self.recordHotword = function() {
        return rpcService.sendCommand('record_hotword', 'speechrecognition', null, 20)
            .then(function() {
                return raspiotService.reloadModuleConfig('speechrecognition');
            });
    };

    self.resetHotword = function() {
        return rpcService.sendCommand('reset_hotword', 'speechrecognition', null, 20)
            .then(function() {
                return raspiotService.reloadModuleConfig('speechrecognition');
            });
    };
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('speechrecognitionService', ['$q', '$rootScope', 'rpcService', 'raspiotService', speechrecognitionService]);

