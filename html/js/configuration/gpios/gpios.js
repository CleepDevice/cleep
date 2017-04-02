/**
 * Gpios config directive
 * Handle gpios configuration
 */
var gpiosConfigDirective = function(gpiosService, objectsService, configsService, toast, confirm, $mdDialog) {

    var gpiosConfigController = function() {
        var self = this;
        self.raspiGpios = [];
        self.devices = objectsService.devices;
        self.name = '';
        self.gpio = 'GPIO3';
        self.mode = 'in';
        self.keep = false;
        self.reverted = false;
        self.updateDevice = false;

        /**
         * Reset editor's values
         */
        self._resetValues = function() {
            self.name = '';
            self.gpio = 'GPIO3';
            self.mode = 'in';
            self.keep = false;
            self.reverted = false;
        };

        /**
         * Close dialog
         */
        self.closeDialog = function() {
            //check values
            if( self.name.length===0 )
            {
                toast.error('All fields are required');
            }
            else
            {
                $mdDialog.hide();
            }
        };

        /**
         * Cancel dialog
         */
        self.cancelDialog = function() {
            $mdDialog.cancel();
        };

        /**
         * Open dialog (internal use)
         */
        self._openDialog = function() {
            return $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'gpiosCtl',
                templateUrl: 'js/configuration/gpios/addGpio.html',
                parent: angular.element(document.body),
                clickOutsideToClose: false
            });
        };
        
        /**
         * Add device
         */
        self.openAddDialog = function() {
            self.updateDevice = false;
            self._openDialog()
                .then(function() {
                    return gpiosService.addGpio(self.name, self.gpio, self.mode, self.keep, self.reverted);
                })
                .then(function() {
                    return gpiosService.loadDevices();
                })
                .then(function() {
                    toast.success('Gpio added');
                })
                .finally(function() {
                    self._resetValues();
                });
        }; 

        /**
         * Update device
         */
        self.openUpdateDialog = function(device) {
            //set editor's value
            self.name = device.name;
            self.gpio = device.gpio;
            self.mode = device.mode;
            self.keep = device.keep

            //open dialog
            self.updateDevice = true;
            self._openDialog()
                .then(function() {
                    return gpiosService.updateGpio(device.uuid, self.name, self.keep, self.reverted);
                })
                .then(function(resp) {
                    return gpiosService.loadDevices();
                })
                .then(function() {
                    toast.success('Gpio updated');
                })
                .finally(function() {
                    self._resetValues();
                });
        };

        /**
         * Delete device
         */
        self.openDeleteDialog = function(device) {
            confirm.open('Delete gpio?', null, 'Delete')
                .then(function() {
                    return gpiosService.deleteGpio(device.uuid);
                })
                .then(function() {
                    return gpiosService.loadDevices();
                })
                .then(function() {
                    toast.success('Gpio deleted');
                });
        };

        /**
         * Init controller
         */
        self.init = function() {
            var config = configsService.getConfig('gpios');
            self.raspiGpios = config.raspi_gpios;
        };
    };

    var gpiosConfigLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'js/configuration/gpios/gpios.html',
        replace: true,
        scope: true,
        controller: gpiosConfigController,
        controllerAs: 'gpiosCtl',
        link: gpiosConfigLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('gpiosConfigDirective', ['gpiosService', 'objectsService', 'configsService', 'toastService', 'confirmService', '$mdDialog', gpiosConfigDirective]);

