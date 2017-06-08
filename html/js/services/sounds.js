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
        return rpcService.sendCommand('get_sounds', 'sounds');
    };

    /**
     * Get langs
     */
    self.getLangs = function() {
        return rpcService.sendCommand('get_langs', 'sounds');
    };

    /**
     * Set lang
     */
    self.setLang = function(lang) {
        return rpcService.sendCommand('set_lang', 'sounds', {'lang':lang});
    };

    /**
     * Delete sound
     */
    self.deleteSound = function(name) {
        return rpcService.sendCommand('delete_sound', 'sounds', {'filename':name});
    };

    /**
     * Play sound
     */
    self.playSound = function(name) {
        return rpcService.sendCommand('play_sound', 'sounds', {'filename':name});
    };

    /**
     * Speak text
     */
    self.speakText = function(text, lang) {
        return rpcService.sendCommand('speak_text', 'sounds', {'text':text, 'lang':lang});
    };

    /**
     * Get volume
     */
    self.getVolume = function() {
        return rpcService.sendCommand('get_volume', 'sounds');
    };

    /**
     * Set volume
     */
    self.setVolume = function() {
        return rpcService.sendCommand('set_volume', 'sounds', {'volume':volume});
    };

    /**
     * Upload sound
     */
    self.uploadSound = function(file) {
        return rpcService.upload('add_sound', 'sounds', file);
    };
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('soundsService', ['$q', '$rootScope', 'rpcService', soundsService]);

