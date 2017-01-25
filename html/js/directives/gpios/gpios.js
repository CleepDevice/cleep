/**
 * Gpios config directive
 * Handle gpios configuration
 */
var gpiosConfigDirective = function(gpiosService, $q, blockUI, objectsService, toastService, $mdPanel, $mdSidenav, $mdBottomSheet) {
    var container = null;

    var gpiosConfigController = function() {
        var self = this;
        self.raspiGpios = [];
        self.devices = objectsService.devices;
        self.name = '';
        self.gpio = 'GPIO3';
        self.mode = 'in';
        self.keep = true;
        self.list = [];
        self.currentDevice = null;
        self.showAddPanel = false;
        self.showAdvancedPanel = false;

        /**
         * Open adding panel
         */
        self.openAddPanel = function() {
            self.showAddPanel = true;
        };

        /**
         * Close adding panel and reset current device
         */
        self.closeAddPanel = function() {
            self.currentDevice = null;
            self.showAddPanel = false;
        };

        /**
         * Open advanced config panel
         */
        self.openAdvancedPanel = function() {
            self.showAdvancedPanel = true;
        };

        /**
         * Close advanced config panel
         */
        self.closeAdvancedPanel = function() {
            self.showAdvancedPanel = false;
        };

        /**
         * Return raspberry pi gpios
         */
        self.getRaspiGpios = function() {
            return gpiosService.getRaspiGpios()
            .then(function(resp) {
                self.raspiGpios = resp;
            });
        }

        /**
         * Add new gpio
         */
        self.addGpio = function() {
            //check values
            if( self.name.length==0 )
            {
                toastService.error('All fields are required');
            }
            else
            {
                container.start();

                if( self.currentDevice )
                {
                    //edition mode: first of all delete current device if edition
                    gpiosService.delGpio(self.currentDevice.gpio)
                        .then(function() {
                            self.currentDevice = null;
                            gpiosService.addGpio(self.name, self.gpio, self.mode, self.keep)
                                .then(function(resp) {
                                    //reload devices
                                    gpiosService.loadDevices();
                                })
                                .finally(function() {
                                    self.closeAddPanel();
                                    container.stop();
                                });
                        })
                        .finally(function() {
                            container.stop();
                        });
                }
                else
                {
                    //adding mode
                    gpiosService.addGpio(self.name, self.gpio, self.mode, self.keep)
                        .then(function(resp) {
                            //reload devices
                            gpiosService.loadDevices();
                        })
                        .finally(function() {
                            self.closeAddPanel();
                            container.stop();
                        });
                }
            }
        };

        /**
         * Delete gpio
         */
        self.deleteGpio = function(device, warning) {
            if( (warning===undefined || warning===true) && !confirm('Delete gpio?') ) {
                return;
            }

            container.start();
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
        self.editGpio = function(device) {
            //save current device
            self.currentDevice = device;
            
            //set editor's value
            self.name = device.name;
            self.gpio = device.gpio;
            self.mode = device.mode;
            self.keep = device.keep;

            //open adding panel
            self.openAddPanel();
        };

        /**
         * Show advanced configuration panel
         */
        self.showAdvanced = function() {
            toastService.success('successful message');
            $mdBottomSheet.show({
                templateUrl: 'js/directives/gpios/gpiosAdvanced.html',
                parent: angular.element('#GpiosConfig'),
                controller: function($scope, $mdBottomSheet) {
                }
            });
        };

        /**
         * Init controller
         */
        self.init = function() {
            //get list of raspberry pi gpios
            self.getRaspiGpios();
        }
    };

    var gpiosConfigLink = function(scope, element, attrs, controller) {
        //init blockui
        container = blockUI.instances.get('gpiosContainer');
        container.reset();

        //init controller
        controller.init();
    };

    return {
        templateUrl: 'js/directives/gpios/gpios.html',
        replace: true,
        scope: true,
        controller: gpiosConfigController,
        controllerAs: 'gpiosCtl',
        link: gpiosConfigLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('gpiosConfigDirective', ['gpiosService', '$q', 'blockUI', 'objectsService', 'toastService', '$mdPanel', '$mdSidenav', '$mdBottomSheet', gpiosConfigDirective]);
