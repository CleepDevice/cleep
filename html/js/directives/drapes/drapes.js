/**
 * Drapes config directive
 * Handle drape and switch configuration
 */
var drapesConfigDirective = function(drapesService, $q, growl, blockUI, objectsService) {
    var container = null;

    var drapesConfigController = ['$rootScope', '$scope', function($rootScope, $scope) {
        $scope.raspiGpios = [];
        $scope.devices = objectsService.devices;
        $scope.name = 'drape';
        $scope.drape_open = 'GPIO2';
        $scope.drape_close = 'GPIO4';
        $scope.switch_open = 'GPIO3';
        $scope.switch_close = 'GPIO17';
        $scope.delay = 30;

        /**
         * Return raspberry pi gpios
         */
        function getRaspiGpios() {
            return drapesService.getRaspiGpios()
            .then(function(resp) {
                for( var gpio in resp )
                {
                    resp[gpio].gpio = gpio;
                }
                $scope.raspiGpios = resp;
            });
        }

        /**
         * Add new drape
         */
        $scope.addDrape = function() {
            //check values
            if( $scope.name.length===0 || $scope.delay.length===0 )
            {
                growl.error('All fields are required');
            }
            else
            {
                container.start();
            drapesService.addDrape($scope.name, $scope.drape_open, $scope.drape_close, $scope.delay, $scope.switch_open, $scope.switch_close)
                .then(function(resp) {
                    //reload devices
                    drapesService.loadDevices();
                })
                .finally(function() {
                    container.stop();
                });
            }
        };

        /**
         * Delete drape
         */
        $scope.deleteDrape = function(device) {
            //TODO add confirm dialog
            container.start();
            drapesService.delDrape(device.name)
                .then(function(resp) {
                    //reload devices
                    drapesService.loadDevices();
                })
                .finally(function() {
                    container.stop();
                });
        };

        /**
         * Edit selected drape
         */
        $scope.editDrape = function(device) {
            //set editor's value
            $scope.name = device.name;
            $scope.drape_open = device.drape_open;
            $scope.drape_close = device.drape_close
            $scope.delay = device.delay;
            $scope.switch_open = device.switch_open;
            $scope.switch_close = device.switch_close

            //remove gpio from list
            $scope.deleteDrape(device);
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

    var drapesConfigLink = function(scope, element, attrs) {
        container = blockUI.instances.get('drapesContainer');
        container.reset();
    };

    return {
        templateUrl: 'js/directives/drapes/drapes.html',
        replace: true,
        scope: true,
        controller: drapesConfigController,
        link: drapesConfigLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('drapesConfigDirective', ['drapesService', '$q', 'growl', 'blockUI', 'objectsService', drapesConfigDirective]);
