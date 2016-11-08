/**
 * Drapes Switches config directive
 * Handle drapes switches configuration
 */
var drapesSwitchesConfigDirective = function(drapesService, $q, growl, blockUI, objectsService) {
    var container = null;

    var drapesSwitchesConfigController = ['$rootScope', '$scope', function($rootScope, $scope) {
        $scope.raspiGpios = [];
        $scope.devices = objectsService.devices;
        $scope.name = 'switch';
        $scope.gpio_open = 'GPIO4';
        $scope.gpio_close = 'GPIO17';
        $scope.drape = '';

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
        };

        /**
         * Add new switch
         */
        $scope.addSwitch = function() {
            //check values
            if( $scope.name.length===0 || $scope.drape.length===0 )
            {
                growl.error('All fields are required');
            }
            else
            {
                container.start();
                drapesService.addSwitch($scope.name, $scope.gpio_open, $scope.gpio_close, $scope.drape)
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
         * Delete switch
         */
        $scope.deleteSwitch = function(device) {
            //TODO add confirm dialog
            container.start();
            drapesService.delSwitch(device.name)
                .then(function(resp) {
                    //reload devices
                    drapesService.loadDevices();
                })
                .finally(function() {
                    container.stop();
                });
        };

        /**
         * Edit selected switch
         */
        $scope.editSwitch = function(device) {
            //set editor's value
            $scope.name = device.name;
            $scope.gpio_open = device.open;
            $scope.gpio_close = device.close
            $scope.drape = device.drape;

            //remove switch from list
            $scope.deleteSwitch(device);
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

    var drapesSwitchesConfigLink = function(scope, element, attrs) {
        container = blockUI.instances.get('drapesSwitchesContainer');
        container.reset();
    };

    return {
        templateUrl: 'js/directives/drapesSwitches/drapesSwitches.html',
        replace: true,
        scope: true,
        controller: drapesSwitchesConfigController,
        link: drapesSwitchesConfigLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('drapesSwitchesConfigDirective', ['drapesService', '$q', 'growl', 'blockUI', 'objectsService', drapesSwitchesConfigDirective]);
