/**
 *
 */
var soundConfigDirective = function($q, toast, soundService, confirm) {

    var soundController = ['$scope', function($scope) {
        var self = this;
        self.sounds = [];
        self.uploadData = {
            'command': 'add_sound',
            'to': 'sound'
        };
        self.ttsConfig = '';
        self.ttsLang = 'en';
        self.tts = '';
        self.langs = [];
        self.lang = 'en';
        self.volume = 0;
        self.showAddPanel = false;
        self.showAdvancedPanel = false;
        self.uploadFile = null;

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
                soundService.uploadSound(file, self.onUploadSuccess, self.onUploadFailure);
                /*uploadFile.upload('/upload', file, {
                    'command': 'add_sound',
                    'to': 'sound'
                }, self.onUploadSuccess, self.onUploadFailure);*/
            }
        });

        /**
         * Open add panel
         */
        self.openAddPanel = function() {
            self.showAddPanel = true;
            self.closeAdvancedPanel();
        };

        /**
         * Close add panel
         */
        self.closeAddPanel = function() {
            self.showAddPanel = false;
        };

        /**
         * Open advanced panel
         */
        self.openAdvancedPanel = function() {
            self.showAdvancedPanel = true;
            self.closeAddPanel();
        };

        /**
         * Close advanced panel
         */
        self.closeAdvancedPanel = function() {
            self.showAdvancedPanel = false;
        };

        /**
         * Get sounds
         */
        self.getSounds = function() {
            soundService.getSounds()
                .then(function(resp) {
                    self.sounds = resp;
                });
        };

        /**
         * Get langs and selected lang
         */
        self.getLangs = function() {
            soundService.getLangs()
                .then(function(resp) {
                    var temp = [];
                    angular.forEach(resp.langs, function(label, lang) {
                        temp.push({'lang':lang, 'label':label});
                    });
                    self.langs = temp;
                    self.lang = resp.lang;
                    self.ttsLang = resp.lang;
                });
        };

        /**
         * Return current volume (pygame mixer not system volume)
         */
        self.getVolume = function() {
            soundService.getVolume()
                .then(function(resp) {
                    self.volume = resp;
                });
        };

        /**
         * Init controller
         */
        self.init = function() {
            self.getLangs();
            self.getSounds();
            self.getVolume();
        };

        /**
         * Upload successful
         */
        self.onUploadSuccess = function(resp) {
            toast.hide();
            if( resp && resp.data && typeof(resp.data.error)!=='undefined' && resp.data.error===false )
            {
                self.getSounds();
                toast.success('Sound file uploaded');
                self.closeAddPanel();
            }
            else
            {
                toast.error(resp.data.message);
            }
        };

        /**
         * Upload failed
         */
        self.onUploadFailure = function(err) {
            toast.hide();
            toast.error('Upload failed: '+err);
        };

        /**
         * Delete specified sound
         */
        self.deleteSound = function(filename) {
            confirm.dialog('Delete sound ?', null, 'Delete')
                .then(function() {
                    //delete sound
                    soundService.deleteSound(filename)
                        .then(function() {
                            toast.success('Sound file deleted');
                            self.getSounds();
                        });
                });
        };

        /**
         * Play sound
         */
        self.playSound = function(filename) {
            soundService.playSound(filename);
        };

        /**
         * Speak message from config
         */
        self.speakMessageConfig = function() {
            if( self.ttsConfig.length>0 )
            {
                toast.loading('Playing sound...');
                soundService.speakMessage(self.ttsConfig, self.ttsLang)
                    .then(function() {
                        toast.hide();
                    });
            }
            else
            {
                toast.error('Please set message to speak');
            }
        };

        /**
         * Speak message from main
         */
        self.speakMessage = function() {
            if( self.tts.length>0 )
            {
                soundService.speakMessage(self.tts, self.lang);
            }
            else
            {
                toast.error('Please set message to speak');
            }
        };

        /**
         * Set lang
         */
        self.setLang = function() {
            soundService.setLang(self.lang)
                .then(function() {
                    toast.success('Lang saved');
                });
        };
    }];

    var soundLink = function(scope, element, attrs, controller) {
        //init controller
        controller.init();
    };

    return {
        templateUrl: 'js/directives/sound/sound.html',
        replace: true,
        scope: true,
        controller: soundController,
        controllerAs: 'soundCtl',
        link: soundLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('soundConfigDirective', ['$q', 'toastService', 'soundService', 'confirmService', soundConfigDirective]);
