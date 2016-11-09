/**
 * Gpios config directive
 * Handle gpios configuration
 */
var gpiosConfigDirective = function(gpiosService, $q, growl, blockUI, objectsService) {
    var container = null;

    var gpiosConfigController = ['$rootScope', '$scope', function($rootScope, $scope) {
        $scope.raspiGpios = [];
        $scope.devices = objectsService.devices;
        $scope.name = '';
        $scope.gpio = 'GPIO3';
        $scope.mode = 'in';
        $scope.keep = true;
        $scope.list = [];

        /**
         * Return raspberry pi gpios
         */
        function getRaspiGpios() {
            return gpiosService.getRaspiGpios()
            .then(function(resp) {
                $scope.raspiGpios = resp;
            });
        }

        /**
         * Add new gpio
         */
        $scope.addGpio = function() {
            //check values
            if( $scope.name.length==0 )
            {
                growl.error('All fields are required');
            }
            else
            {
                container.start();
                gpiosService.addGpio($scope.name, $scope.gpio, $scope.mode, $scope.keep)
                .then(function(resp) {
                    //reload devices
                    gpiosService.loadDevices();
                })
                .finally(function() {
                    container.stop();
                });
            }
        };

        /**
         * Delete gpio
         */
        $scope.deleteGpio = function(device) {
            //TODO add confirm dialog
            container.start();
            console.log('delete '+device);
            gpiosService.delGpio(device.gpio)
                .then(function(resp) {
                    //reload devices
                    gpiosService.loadDevices();
                })
                .finally(function() {
                    container.stop();
                });
        };

        /**
         * Edit selected gpios
         */
        $scope.editGpio = function(device) {
            //set editor's value
            $scope.name = device.name;
            $scope.gpio = device.gpio;
            $scope.mode = device.mode;
            $scope.keep = device.keep;

            //remove gpio from list
            $scope.deleteGpio(device);
        };

        /**
         * Init controller
         */
        function init() {
            //get list of raspberry pi gpios
            getRaspiGpios();
        }

        //init directive
        init();
    }];

    var gpiosConfigLink = function(scope, element, attrs) {
        container = blockUI.instances.get('gpiosContainer');
        container.reset();
    };

    return {
        templateUrl: 'js/directives/gpios/gpios.html',
        replace: true,
        scope: true,
        controller: gpiosConfigController,
        link: gpiosConfigLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('gpiosConfigDirective', ['gpiosService', '$q', 'growl', 'blockUI', 'objectsService', gpiosConfigDirective]);
