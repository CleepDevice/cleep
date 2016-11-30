
var soundConfigDirective = function($q, growl, blockUI, soundService) {
    var container = null;

    var soundController = ['$scope', function($scope) {
        $scope.sounds = [];
        $scope.uploadData = {
            'command': 'add_sound',
            'to': 'sound'
        };
        $scope.tts = '';
        $scope.langs = [];
        $scope.lang = 'en';

        /**
         * Get sounds
         */
        function getSounds() {
            soundService.getSounds()
                .then(function(resp) {
                    $scope.sounds = resp;
                });
        };

        /**
         * Get langs and selected lang
         */
        function getLangs() {
            soundService.getLangs()
                .then(function(resp) {
                    $scope.langs = resp.langs;
                    $scope.lang = resp.lang;
                });
        };

        function getVolume() {
            soundService.getVolume()
                .then(function(resp) {
                    console.log(resp);
                });
        };

        /**
         * Init controller
         */
        function init() {
            getLangs();
            getSounds();
            getVolume();
        };

        /**
         * Upload started
         */
        $scope.uploadStarted = function() {
            container.start();
        };

        /**
         * Upload complete callback
         */
        $scope.uploadComplete = function(resp) {
            console.log('updcomplete', resp);
            if( resp && resp.data && typeof(resp.data.error)!=='undefined' && resp.data.error===false )
            {
                growl.success('Sound file uploaded');
                getSounds();
            }
            else
            {
                growl.error(resp.data.message);
            }
            container.stop();
        };

        /**
         * Delete specified sound
         */
        $scope.delSound = function(path) {
            //confirmation
            if( !confirm('Delete sound?') )
            {
                return;
            }

            //delete sound
            container.start();
            soundService.delSound(path)
                .then(function() {
                    growl.success('Sound file deleted');
                    getSounds();
                })
                .finally(function() {
                    container.stop();
                });
        };

        /**
         * Play sound
         */
        $scope.playSound = function(path) {
            soundService.playSound(path);
        };

        /**
         * Say text
         */
        $scope.sayText = function() {
            if( $scope.tts.length>0 )
            {
                soundService.sayText($scope.tts, 'fr');
            }
            else
            {
                growl.error('Please specify');
            }
        };

        /**
         * Set lang
         */
        $scope.setLang = function() {
            container.start();
            soundService.setLang($scope.lang)
                .then(function() {
                    growl.success('Lang saved');
                })
                .finally(function() {
                    container.stop();
                });
        };

        //init directive
        init();
    }];

    var soundLink = function(scope, element, attrs) {
        container = blockUI.instances.get('soundContainer');
        container.reset();
    };

    return {
        templateUrl: 'js/directives/sound/sound.html',
        replace: true,
        scope: true,
        controller: soundController,
        link: soundLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('soundConfigDirective', ['$q', 'growl', 'blockUI', 'soundService', soundConfigDirective]);
