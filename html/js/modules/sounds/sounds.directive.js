/**
 * Sounds configuration directive
 * Handle sounds module configuration
 */
var soundsConfigDirective = function($rootScope, $q, toast, raspiotService, soundsService, confirm, $mdDialog) {

    var soundsController = ['$scope', function($scope) {
        var self = this;
        self.sounds = [];
        self.musics = [];
        self.ttsLang = 'en';
        self.tts = '';
        self.langs = [];
        self.lang = 'en';
        self.volume = 0;
        self.uploadFile = null;
        self.type = null;

        /** 
         * Cancel dialog
         */
        self.cancelDialog = function() {
            $mdDialog.cancel();
        };

        /**
         * Open add dialog
         * @param type: file type ('music', 'sound')
         */
        self.openAddDialog = function(type) {
            self.type = type
            return $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'soundsCtl',
                templateUrl: 'addSound.directive.html',
                parent: angular.element(document.body),
                clickOutsideToClose: false,
                fullscreen: true
            });
        };

        /**
         * Open config dialog
         */
        self.openConfigDialog = function() {
            return $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'soundsCtl',
                templateUrl: 'configSound.directive.html',
                parent: angular.element(document.body),
                clickOutsideToClose: false,
                fullscreen: true
            });
        };

        /**
         * Trigger upload when file selected
         */
        $scope.$watch(function() {
            return self.uploadFile;
        }, function(file) {
            if( file )
            {
                //launch upload
                if( self.type=='sound' )
                {
                    toast.loading('Uploading sound file');
                }
                else
                {
                    toast.loading('Uploading music file');
                }

                soundsService.uploadSound(file)
                    .then(function(resp) {
                        return raspiotService.reloadModuleConfig('sounds');
                    })
                    .then(function(config) {
                        $mdDialog.hide();
                        self.sounds = config.sounds;
                        self.musics = config.musics;
                        if( self.type=='sound' )
                        {
                            toast.success('Sound file uploaded');
                        }
                        else
                        {
                            toast.success('Music file uploaded');
                        }
                    });
            }
        });

        /**
         * Delete sound
         */
        self.openDeleteDialog = function(soundfile) {
            confirm.open('Delete sound?', null, 'Delete')
                .then(function() {
                    return soundsService.deleteSound(soundfile);
                })
                .then(function() {
                    return raspiotService.reloadModuleConfig('sounds');
                })
                .then(function(config) {
                    self.sounds = config.sounds;
                    toast.success('Sound file deleted');
                });
        };

        /**
         * Delete music
         */
        self.openDeleteDialog = function(musicfile) {
            confirm.open('Delete music?', null, 'Delete')
                .then(function() {
                    return soundsService.deleteMusic(musicfile);
                })
                .then(function() {
                    return raspiotService.reloadModuleConfig('sounds');
                })
                .then(function(config) {
                    self.musics = config.musics;
                    toast.success('Music file deleted');
                });
        };

        /**
         * Set lang
         */
        self.setLang = function() {
            soundsService.setLang(self.lang)
                .then(function() {
                    toast.success('Lang saved');
                });
        };

        /**
         * Play sound
         */
        self.playSound = function(filename) {
            soundsService.playSound(filename)
                .then(function() {
                    toast.success('Sound is playing');
                });
        };

        /**
         * Play music
         */
        self.playMusic = function(filename) {
            soundsService.playMusic(filename)
                .then(function() {
                    toast.success('Music is playing');
                });
        };

        /**
         * Speak message
         */
        self.speakText = function(message, lang) {
            if( angular.isUndefined(lang) )
            {
                lang = self.lang;
            }
            if( message.length>0 )
            {
                toast.loading('Playing sound...');
                soundsService.speakText(message, lang)
                    .then(function() {
                        self.tts = '';
                        toast.hide();
                    });
            }
            else
            {
                toast.error('Please set message to speak');
            }
        };

        /**
         * Init controller
         */
        self.init = function() {
            raspiotService.getModuleConfig('sounds')
                .then(function(config) {
                    var langs = [];
                    angular.forEach(config.langs.langs, function(label, lang) {
                        langs.push({'lang':lang, 'label':label});
                    });
                    self.langs = langs;
                    self.lang = config.langs.lang;
                    self.ttsLang = config.langs.lang;
                    self.volume = config.volume;
                    self.sounds = config.sounds;
                    self.musics = config.musics;
                });

            //add module actions to fabButton
            var actions = [{
                icon: 'plus',
                callback: self.openAddDialog,
                tooltip: 'Add sound'
            }, {
                icon: 'wrench',
                callback: self.openConfigDialog,
                tooltip: 'Advanced configuration '
            }]; 
            $rootScope.$broadcast('enableFab', actions);
        };

    }];

    var soundsLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'sounds.directive.html',
        replace: true,
        scope: true,
        controller: soundsController,
        controllerAs: 'soundsCtl',
        link: soundsLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('soundsConfigDirective', ['$rootScope', '$q', 'toastService', 'raspiotService', 'soundsService', 'confirmService', '$mdDialog', soundsConfigDirective]);

