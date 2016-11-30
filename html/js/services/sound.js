/**
 * Sound service
 * Handle sound module requests
 */
var soundService = function($q, $rootScope, rpcService, objectsService) {
    var self = this;
    
    /** 
     * Set configuration directive names
     */
    self.setConfigs = function() {
        objectsService.addConfig('Sound', 'soundConfigDirective');
    };

    /**
     * Get sounds
     */
    self.getSounds = function() {
        return rpcService.sendCommand('get_sounds', 'sound')
            .then(function(resp) {
                return resp.data;
            }, function(err) {
                console.error('getSounds:', err);
            });
    };

    /**
     * Get langs
     */
    self.getLangs = function() {
        return rpcService.sendCommand('get_langs', 'sound')
            .then(function(resp) {
                return resp.data;
            }, function(err) {
                console.error('getLangs:', err);
            });
    };

    /**
     * Set lang
     */
    self.setLang = function(lang) {
        return rpcService.sendCommand('set_lang', 'sound', {'lang':lang})
            .then(function(resp) {
            }, function(err)  {
                console.error('setLang', err);
            });
    };

    /**
     * Delete sound
     */
    self.delSound = function(path) {
        return rpcService.sendCommand('del_sound', 'sound', {'filepath':path})
            .then(function(resp) {
            }, function(err) {
                console.error('delSound:', err);
            });
    };

    /**
     * Play sound
     */
    self.playSound = function(path) {
        return rpcService.sendCommand('play_sound', 'sound', {'filepath':path})
            .then(function(resp) {
            }, function(err) {
                console.error('playSound:', err);
            });
    };

    /**
     * Say text
     */
    self.sayText = function(text, lang) {
        return rpcService.sendCommand('say_text', 'sound', {'text':text, 'lang':lang})
            .then(function(resp) {
            }, function(err) {
                console.error('sayText:', err);
            });
    };

    /**
     * Get volume
     */
    self.getVolume = function() {
        return rpcService.sendCommand('get_volume', 'sound')
            .then(function(resp) {
                return resp.data;
            }, function(err) {
                console.error('getVolume:', err);
            });
    };

    /**
     * Set volume
     */
    self.setVolume = function() {
        return rpcService.sendCommand('set_volume', 'sound', {'volume':volume})
            .then(function(resp) {
            }, function(err) {
                console.error('getVolume:', err);
            });
    };
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('soundService', ['$q', '$rootScope', 'rpcService', 'objectsService', soundService]);

