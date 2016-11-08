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
                gpiosService.addGpio($scope.name, $scope.gpio, $scope.mode)
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

            //remove gpio from list
            $scope.deleteGpio(device);
        };

        /**
         * Turn on/off specified gpio
         */
        /*$scope.turnGpio = function(index) {
            console.log('turnGpio', $scope.devices[index]);
            container.start();

            //is gpio an input?
            if( $scope.devices[index]['mode']!=='out' )
            {
                //do not perform action
                console.log('action no performed');
                $scope.devices[index]['on'] = !$scope.devices[index]['on'];
                container.stop();
                return;
            }

            if( $scope.devices[index]['on'] )
            {
                gpiosService.turnOn($scope.devices[index]['__key'])
                //.then(function(resp) {
                //    return getConfiguredGpios();
                //})
                .finally(function() {
                    container.stop();
                });
            }
            else
            {
                gpiosService.turnOff($scope.devices[index]['__key'])
                //.then(function(resp) {
                //    return getConfiguredGpios();
                //})
                .finally(function() {
                    container.stop();
                });
            }
        };*/

        /**
         * Output gpio changed by user
         */
        /*$scope.onchange = function(index) {
            //is gpio an input?
            if( $scope.devices[index]['mode']!=='out' )
            {
                //do not perform action
                //console.log('action performed');
                //$scope.devices['gpiosService'][index]['on'] = !$scope.devices['gpiosService'][index]['on'];
                //container.stop();
                //return;
            }
            else
            {
                //perform action
                console.log('onchange');
                $scope.turnGpio(index);
            }
        };*/

        /**
         * Catch gpios on event
         */
        /*$scope.$on('event.gpio.on', function(event, params) {
            for( var i=0; i<$scope.devices.length; i++ )
            {
                if( $scope.devices[i]['__key']===params.gpio )
                {
                    if( $scope.devices[i]['on']===false )
                    {
                        $scope.devices[i]['on'] = true;
                    }
                    break;
                }
            }
        });*/

        /**
         * Catch gpios off event
         */
        /*$scope.$on('event.gpio.off', function(event, params) {
            for( var i=0; i<$scope.devices.length; i++ )
            {
                if( $scope.devices[i]['__key']===params.gpio )
                {
                    if( $scope.devices[i]['on']===true )
                    {
                        $scope.devices[i]['on'] = false;
                    }
                    break;
                }
            }
        });*/

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
