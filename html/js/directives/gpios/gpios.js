/**
 * Gpios config directive
 * Handle gpios configuration
 */
var gpiosConfigDirective = function(gpiosService, $q, objectsService, toast, confirm) {

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

        /**
         * Open add panel
         */
        self.openAddPanel = function() {
            self.showAddPanel = true;
        };

        /**
         * Close add panel and reset current device
         */
        self.closeAddPanel = function() {
            //hide panel
            self.showAddPanel = false;

            //reset field content
            self.name = '';
            self.gpio = 'GPIO3';
            self.mode = 'in';
            self.keep = true;
            self.currentDevice = null;
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
         * Add/update gpio
         */
        self.addGpio = function() {
            //check values
            if( self.name.length==0 )
            {
                toast.error('All fields are required');
                return;
            }

            if( self.currentDevice )
            {
                //edition mode: first of all delete current device if edition
                gpiosService.deleteGpio(self.currentDevice.gpio)
                    .then(function() {
                            self.currentDevice = null;
                            return gpiosService.addGpio(self.name, self.gpio, self.mode, self.keep)
                            .then(function(resp) {
                                toast.success('Gpio updated');
                                gpiosService.loadDevices();
                             })
                            .finally(function() {
                                self.closeAddPanel();
                                });
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
                    });
            }
        };

        /**
         * Delete gpio
         */
        self.deleteGpio = function(device) {
            confirm.dialog('Delete gpio ?', null, 'Delete')
                .then(function() {
                    gpiosService.deleteGpio(device.gpio)
                        .then(function(resp) {
                            //reload devices
                            gpiosService.loadDevices();
                        });
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
         * Init controller
         */
        self.init = function() {
            //get list of raspberry pi gpios
            self.getRaspiGpios();
        }
    };

    var gpiosConfigLink = function(scope, element, attrs, controller) {
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
RaspIot.directive('gpiosConfigDirective', ['gpiosService', '$q', 'objectsService', 'toastService', 'confirmService', gpiosConfigDirective]);
