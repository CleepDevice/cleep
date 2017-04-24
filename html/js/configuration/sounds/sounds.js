/**
 * Sounds configuration directive
 * Handle sounds module configuration
 */
var soundsConfigDirective = function($rootScope, $q, toast, raspiotService, soundsService, confirm, $mdDialog) {

    var soundsController = ['$scope', function($scope) {
        var self = this;
        self.sounds = [];
        self.ttsLang = 'en';
        self.tts = '';
        self.langs = [];
        self.lang = 'en';
        self.volume = 0;
        self.uploadFile = null;

        /** 
         * Cancel dialog
         */
        self.cancelDialog = function() {
            $mdDialog.cancel();
        };

        /**
         * Open add dialog
         */
        self.openAddDialog = function() {
            return $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'soundsCtl',
                templateUrl: 'js/configuration/sounds/addSound.html',
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
                templateUrl: 'js/configuration/sounds/configSound.html',
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
                toast.loading('Uploading file');
                soundsService.uploadSound(file)
                    .then(function(resp) {
                        return raspiotService.reloadModuleConfig('sounds');
                    })
                    .then(function(config) {
                        $mdDialog.hide();
                        self.sounds = config.sounds;
                        toast.success('Sound file uploaded');
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
                    toast.success('Sounds is playing');
                });
        };

        /**
         * Speak message
         */
        self.speakMessage = function(message, lang) {
            if( angular.isUndefined(lang) )
            {
                lang = self.lang;
            }
            if( message.length>0 )
            {
                toast.loading('Playing sound...');
                soundsService.speakMessage(message, lang)
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
                });

            //add module actions to fabButton
            var actions = [{
                icon: 'add_circle',
                callback: self.openAddDialog,
                tooltip: 'Add sound'
            }, {
                icon: 'build',
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
        templateUrl: 'js/configuration/sounds/sounds.html',
        replace: true,
        scope: true,
        controller: soundsController,
        controllerAs: 'soundsCtl',
        link: soundsLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('soundsConfigDirective', ['$rootScope', '$q', 'toastService', 'raspiotService', 'soundsService', 'confirmService', '$mdDialog', soundsConfigDirective]);

