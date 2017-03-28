/**
 * Sounds service
 * Handle sound module requests
 */
var soundsService = function($q, $rootScope, rpcService) {
    var self = this;
    
    /** 
     * Return directive infos
     */
    self.getDirectiveInfos = function() {
        return {
            label: 'Sounds',
            name: 'soundsConfigDirective'
        };  
    }; 

    /**
     * Get sounds
     */
    self.getSounds = function() {
        return rpcService.sendCommand('get_sounds', 'sounds')
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
        return rpcService.sendCommand('get_langs', 'sounds')
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
        return rpcService.sendCommand('set_lang', 'sounds', {'lang':lang})
            .then(function(resp) {
            }, function(err)  {
                console.error('setLang', err);
            });
    };

    /**
     * Delete sound
     */
    self.deleteSound = function(name) {
        return rpcService.sendCommand('delete_sound', 'sounds', {'filename':name})
            .then(function(resp) {
            }, function(err) {
                console.error('deleteSound:', err);
            });
    };

    /**
     * Play sound
     */
    self.playSound = function(name) {
        return rpcService.sendCommand('play_sound', 'sounds', {'filename':name})
            .then(function(resp) {
            }, function(err) {
                console.error('playSound', err);
            });
    };

    /**
     * Speak message
     */
    self.speakMessage = function(text, lang) {
        return rpcService.sendCommand('speak_message', 'sounds', {'text':text, 'lang':lang})
            .then(function(resp) {
            }, function(err) {
                console.error('sayText:', err);
            });
    };

    /**
     * Get volume
     */
    self.getVolume = function() {
        return rpcService.sendCommand('get_volume', 'sounds')
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
        return rpcService.sendCommand('set_volume', 'sounds', {'volume':volume})
            .then(function(resp) {
            }, function(err) {
                console.error('getVolume:', err);
            });
    };

    /**
     * Upload sound
     */
    self.uploadSound = function(file) {
        return rpcService.upload('add_sound', 'sounds', file)
    };
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('soundsService', ['$q', '$rootScope', 'rpcService', soundsService]);

