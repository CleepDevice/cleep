/**
 * Shutters config directive
 * Handle shutter configuration
 */
var shuttersConfigDirective = function(shuttersService, configsService, toast, objectsService, $mdDialog, confirm) {

    var shuttersConfigController = function() {
        var self = this;
        self.raspiGpios = [];
        self.devices = objectsService.devices;
        self.name = '';
        self.shutter_open = 'GPIO2';
        self.shutter_close = 'GPIO4';
        self.switch_open = 'GPIO3';
        self.switch_close = 'GPIO17';
        self.delay = 30;
        self.updateDevice = false;

        /**
         * Reset editor's values
         */
        self._resetValues = function() {
            self.name = '';
            self.shutter_open = 'GPIO2';
            self.shutter_close = 'GPIO4';
            self.switch_open = 'GPIO3';
            self.switch_close = 'GPIO17';
            self.delay = 30;
        };

        /**
         * Close dialog
         */
        self.closeDialog = function() {
            //check values
            if( self.name.length===0 || self.delay.length===0 )
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
                controllerAs: 'shuttersCtl',
                templateUrl: 'js/configuration/shutters/addShutter.html',
                parent: angular.element(document.body),
                clickOutsideToClose: false
            });
        };

        /**
         * Open add dialog
         */
        self.openAddDialog = function() {
            self.updateDevice = false;
            self._openDialog()
                .then(function() {
                    return shuttersService.addShutter(self.name, self.shutter_open, self.shutter_close, self.delay, self.switch_open, self.switch_close);
                })
                .then(function() {
                    return shuttersService.loadDevices();
                })
                .then(function() {
                    toast.success('Shutter added');
                })
                .finally(function() {
                    self._resetValues();
                });
        };

        /**
         * Open update dialog
         */
        self.openUpdateDialog = function(device) {
            //set editor's value
            self.name = device.name;
            self.shutter_open = device.shutter_open;
            self.shutter_close = device.shutter_close
            self.delay = device.delay;
            self.switch_open = device.switch_open;
            self.switch_close = device.switch_close

            //open dialog
            self.updateDevice = true;
            self._openDialog()
                .then(function() {
                    return shuttersService.deleteShutter(device.name);
                })
                .then(function() {
                    return shuttersService.addShutter(self.name, self.shutter_open, self.shutter_close, self.delay, self.switch_open, self.switch_close);
                })
                .then(function() {
                    return shuttersService.loadDevices();
                })
                .then(function() {
                    toast.success('Shutter updated');
                })
                .finally(function() {
                    self._resetValues();
                });
        };

        /**
         * Delete shutter
         */
        self.openDeleteDialog = function(device) {
            confirm.open('Delete shutter?', null, 'Delete')
                .then(function() {
                    return shuttersService.deleteShutter(device.name);
                })
                .then(function() {
                    return shuttersService.loadDevices();
                })
                .then(function() {
                    toast.success('Shutter deleted');
                });
        };

        /**
         * Controller init
         */
        self.init = function() {
            var config = configsService.getConfig('shutters');
            self.raspiGpios = config.raspi_gpios;
        };

    };

    var shuttersConfigLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'js/configuration/shutters/shutters.html',
        replace: true,
        scope: true,
        controller: shuttersConfigController,
        controllerAs: 'shuttersCtl',
        link: shuttersConfigLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('shuttersConfigDirective', ['shuttersService', 'configsService', 'toastService', 'objectsService', '$mdDialog', 'confirmService', shuttersConfigDirective]);

