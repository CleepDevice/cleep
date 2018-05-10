/**
 * Speechrecogniton service
 * Handle speechrecognition module requests
 */
var speechrecognitionService = function($q, $rootScope, rpcService, raspiotService, toast) {
    var self = this;

    self.setProvider = function(providerId, apikey) {
        return rpcService.sendCommand('set_provider', 'speechrecognition', {'provider_id':providerId, 'apikey':apikey})
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
        return rpcService.sendCommand('reset_hotword', 'speechrecognition', null, 10)
            .then(function() {
                return raspiotService.reloadModuleConfig('speechrecognition');
            });
    };

    self.buildHotword = function() {
        return rpcService.sendCommand('build_hotword', 'speechrecognition');
    };

    self.enableService = function() {
        return rpcService.sendCommand('enable_service', 'speechrecognition')
            .then(function() {
                return raspiotService.reloadModuleConfig('speechrecognition');
            });
    };

    self.disableService = function() {
        return rpcService.sendCommand('disable_service', 'speechrecognition')
            .then(function() {
                return raspiotService.reloadModuleConfig('speechrecognition');
            });
    };

    self.startHotwordTest = function() {
        return rpcService.sendCommand('start_hotword_test', 'speechrecognition')
            .then(function() {
                return raspiotService.reloadModuleConfig('speechrecognition');
            });
    };

    self.stopHotwordTest = function() {
        return rpcService.sendCommand('stop_hotword_test', 'speechrecognition')
            .then(function() {
                return raspiotService.reloadModuleConfig('speechrecognition');
            });
    };

    $rootScope.$on('speechrecognition.training.ok', function(event, uuid, params) {
		toast.success('Your hotword voice model has been built successfully');
    });

    $rootScope.$on('speechrecognition.training.ko', function(event, uuid, params) {
		toast.error('Error occured during hotword voice model generation');
    });

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('speechrecognitionService', ['$q', '$rootScope', 'rpcService', 'raspiotService', 'toastService', speechrecognitionService]);

