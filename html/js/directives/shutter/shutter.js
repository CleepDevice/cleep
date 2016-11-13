/**
 * Shutter config directive
 * Handle shutter configuration
 */
var shutterConfigDirective = function(shutterService, $q, growl, blockUI, objectsService) {
    var container = null;

    var shutterConfigController = ['$rootScope', '$scope', function($rootScope, $scope) {
        $scope.raspiGpios = [];
        $scope.devices = objectsService.devices;
        $scope.name = '';
        $scope.shutter_open = 'GPIO2';
        $scope.shutter_close = 'GPIO4';
        $scope.switch_open = 'GPIO3';
        $scope.switch_close = 'GPIO17';
        $scope.delay = 30;

        /**
         * Return raspberry pi gpios
         */
        function getRaspiGpios() {
            return shutterService.getRaspiGpios()
            .then(function(resp) {
                for( var gpio in resp )
                {
                    resp[gpio].gpio = gpio;
                }
                $scope.raspiGpios = resp;
            });
        }

        /**
         * Add new shutter
         */
        $scope.addShutter = function() {
            //check values
            if( $scope.name.length===0 || $scope.delay.length===0 )
            {
                growl.error('All fields are required');
            }
            else
            {
                container.start();
                shutterService.addShutter($scope.name, $scope.shutter_open, $scope.shutter_close, $scope.delay, $scope.switch_open, $scope.switch_close)
                    .then(function(resp) {
                        //reload devices
                        shutterService.loadDevices();
                    })
                    .finally(function() {
                        container.stop();
                    });
            }
        };

        /**
         * Delete shutter
         */
        $scope.deleteShutter = function(device) {
            //TODO add confirm dialog
            container.start();
            shutterService.delShutter(device.name)
                .then(function(resp) {
                    //reload devices
                    shutterService.loadDevices();
                })
                .finally(function() {
                    container.stop();
                });
        };

        /**
         * Edit selected shutter
         */
        $scope.editShutter = function(device) {
            //set editor's value
            $scope.name = device.name;
            $scope.shutter_open = device.shutter_open;
            $scope.shutter_close = device.shutter_close
            $scope.delay = device.delay;
            $scope.switch_open = device.switch_open;
            $scope.switch_close = device.switch_close

            //remove gpio from list
            $scope.deleteShutter(device);
        };

        /**
         * Turn on/off specified gpio
         */
        /*$scope.turnGpio = function(index) {
            console.log('turn gpio', $scope.devices[index]);
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
                $scope.turnGpio(index);
            }
        };*/

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

    var shutterConfigLink = function(scope, element, attrs) {
        container = blockUI.instances.get('shutterContainer');
        container.reset();
    };

    return {
        templateUrl: 'js/directives/shutter/shutter.html',
        replace: true,
        scope: true,
        controller: shutterConfigController,
        link: shutterConfigLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('shutterConfigDirective', ['shutterService', '$q', 'growl', 'blockUI', 'objectsService', shutterConfigDirective]);
