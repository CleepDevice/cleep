/**
 * Sounds service
 * Handle sound module requests
 */
var soundsService = function($q, $rootScope, rpcService) {
    var self = this;
    
    /**
     * Get sounds
     */
    self.getSounds = function() {
        return rpcService.sendCommand('get_sounds', 'sounds');
    };

    /**
     * Get musics
     */
    self.getMusics = function() {
        return rpcService.sendCommand('get_musics', 'sounds');
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
    self.deleteSound = function(fullname) {
        return rpcService.sendCommand('delete_sound', 'sounds', {'fullname':fullname});
    };

    /**
     * Delete music
     */
    self.deleteMusic = function(fullname) {
        return rpcService.sendCommand('delete_music', 'sounds', {'fullname':fullname});
    };

    /**
     * Play sound
     */
    self.playSound = function(fullname) {
        return rpcService.sendCommand('play_sound', 'sounds', {'fullname':fullname});
    };

    /**
     * Play music
     */
    self.playMusic = function(fullname) {
        return rpcService.sendCommand('play_music', 'sounds', {'fullname':fullname});
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

    /**
     * Upload music
     */
    self.uploadMusic = function(file) {
        return rpcService.upload('add_music', 'sounds', file);
    };
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('soundsService', ['$q', '$rootScope', 'rpcService', soundsService]);

