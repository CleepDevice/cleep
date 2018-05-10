/**
 * Gpios config directive
 * Handle gpios configuration
 */
var gpiosConfigDirective = function($rootScope, gpiosService, raspiotService, toast, confirm, $mdDialog) {

    var gpiosConfigController = function() {
        var self = this;
        self.raspiGpios = [];
        self.devices = raspiotService.devices;
        self.name = '';
        self.mode = 'input';
        self.keep = false;
        self.reverted = false;
        self.updateDevice = false;
        self.selectedGpios = [{gpio:null, 'label':'wire'}];

        /**
         * Reset editor's values
         */
        self._resetValues = function() {
            self.name = '';
            self.selectedGpios = [{gpio:null, 'label':'wire'}];
            self.mode = 'input';
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
                templateUrl: 'addGpio.directive.html',
                parent: angular.element(document.body),
                clickOutsideToClose: false,
                fullscreen: true
            });
        };
        
        /**
         * Add device
         */
        self.openAddDialog = function() {
            self.updateDevice = false;
            self._openDialog()
                .then(function() {
                    return gpiosService.addGpio(self.name, self.selectedGpios[0].gpio, self.mode, self.keep, self.reverted);
                })
                .then(function() {
                    return raspiotService.reloadDevices();
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
            self.selectedGpios = [{gpio:device.gpio, label:'gpio'}];
            self.mode = device.mode;
            self.keep = device.keep;

            //open dialog
            self.updateDevice = true;
            self._openDialog()
                .then(function() {
                    return gpiosService.updateGpio(device.uuid, self.name, self.keep, self.reverted);
                })
                .then(function(resp) {
                    return raspiotService.reloadDevices();
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
                    return raspiotService.reloadDevices();
                })
                .then(function() {
                    toast.success('Gpio deleted');
                });
        };

        /**
         * Init controller
         */
        self.init = function() {
            raspiotService.getModuleConfig('gpios')
                .then(function(config) {
                    self.raspiGpios = config.raspi_gpios;
                });

            //add module actions to fabButton
            var actions = [{
                icon: 'plus',
                callback: self.openAddDialog,
                tooltip: 'Add gpio'
            }]; 
            $rootScope.$broadcast('enableFab', actions);
        };
    };

    var gpiosConfigLink = function(scope, element, attrs, controller) {
        controller.init();

    };

    return {
        templateUrl: 'gpios.directive.html',
        replace: true,
        scope: true,
        controller: gpiosConfigController,
        controllerAs: 'gpiosCtl',
        link: gpiosConfigLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('gpiosConfigDirective', ['$rootScope', 'gpiosService', 'raspiotService', 'toastService', 'confirmService', '$mdDialog', gpiosConfigDirective]);

