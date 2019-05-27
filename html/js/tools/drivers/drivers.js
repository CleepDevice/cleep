/**
 * Drivers
 * Display a list of available drivers and implements all possible actions.
 * You can display all drivers or filter them by type or name
 *
 * Directive example:
 * <drivers types="..." names="..."></drivers>
 * With:
 *  - types (string): comma separated list of types to filter on
 *  - names (string): comma separated list of names to filter on
 */
var driversDirective = function($rootScope, rpcService, raspiotService, confirmService, toastService) {

    var driversController = ['$scope', function($scope) {
        var self = this;
        self.drivers = [];
        self.types = [];
        self.names = [];

        /**
         * Init directive
         */
        self.init = function()
        {
            //fill drivers according to specified filters
            raspiotService.getDrivers()
                .then(function(drivers) {
                    if( self.types.length>0 || self.names.length>0 )
                    {
                        drivers.filter(function(driver) {
                            return (!(driver.drivertype in self.types) && !(driver.drivername in self.names)) ? true : false;
                        });
                    }
                    self.drivers = drivers;
                });
        };

        /**
         * Set drivers
         */
        self.setDrivers = function(drivers)
        {
            self.drivers = drivers;
        };

        /**
         * Install driver
         */
        self.install = function(driver) {
            rpcService.sendCommand('install_driver', 'system', {'driver_type': driver.drivertype, 'driver_name': driver.drivername});
        };

        /**
         * Uninstall driver
         */
        self.uninstall = function(driver) {
            confirmService.open('Uninstall driver', 'Confirm uninstallation of "'+driver.drivername+'" driver?', 'Uninstall', 'Cancel')
                .then(function() {
                    rpcService.sendCommand('uninstall_driver', 'system', {'driver_type': driver.drivertype, 'driver_name': driver.drivername});
                });
        };

        /**
         * Repair driver
         */
        self.repair = function(driver) {
            confirmService.open('Repair driver', 'This will install again "'+driver.drivername+'" driver. Do you confirm ?', 'Reinstall', 'Cancel')
                .then(function() {
                    rpcService.sendCommand('install_driver', 'system', {'driver_type': driver.drivertype, 'driver_name': driver.drivername, 'force': true});
                });
        };

        /** 
         * Watch for config changes
         */
        $rootScope.$watchCollection(function() {
            return raspiotService.drivers;
        }, function(newDrivers, oldDrivers) {
            if( newDrivers )
            {   
                self.setDrivers(newDrivers);
            }   
        });

        /**
         * Watch for driver install event
         */
        $rootScope.$on('system.driver.install', function(event, uuid, params) {
            raspiotService.reloadDrivers();
            console.log('install driver', params);
            if( params && params.success===true )
            {
                toastService.success('Driver installed successfully');
            }
            else if( params && params.success===false )
            {
                toastService.error('Error installing driver: "' + params.message + '"');
            }
        });

        /**
         * Watch for driver install event
         */
        $rootScope.$on('system.driver.uninstall', function(event, uuid, params) {
            raspiotService.reloadDrivers();
            console.log('uninstall driver', params);
            if( params && params.success===true )
            {
                toastService.success('Driver uninstalled successfully');
            }
            else if( params && params.success===false )
            {
                toastService.error('Error uninstalling driver: "' + params.message + '"');
            }
        });

    }];

    var driversLink = function(scope, element, attrs, controller) {
        controller.types = scope.types ? scope.types.split(',') : [];
        controller.names = scope.names ? scope.names.split(',') : [];
    };

    return {
        restrict: 'AE',
        templateUrl: 'js/tools/drivers/drivers.html',
        replace: true,
        scope: {
            types: '=',
            names: '='
        },
        controller: driversController,
        controllerAs: 'driversCtl',
        link: driversLink
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.directive('drivers', ['$rootScope', 'rpcService', 'raspiotService', 'confirmService', 'toastService', driversDirective]);

