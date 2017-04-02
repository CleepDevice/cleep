/**
 * Sensors config directive
 * Handle sensors configuration
 */
var sensorsConfigDirective = function(toast, objectsService, configsService, sensorsService, confirm, $mdDialog) {

    var sensorsController = [function() {
        var self = this;
        self.raspiGpios = [];
        self.devices = objectsService.devices;
        self.name = '';
        self.gpio = 'GPIO2';
        self.reverted = false;
        self.type = 'motion';
        self.updateDevice = false;
        self.types = ['motion'];

        /** 
         * Reset editor's values
         */
        self._resetValues = function() {
            self.name = ''; 
            self.gpio = 'GPIO2';
            self.reverted = false;
            self.type = 'motion';
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
                controllerAs: 'sensorsCtl',
                templateUrl: 'js/configuration/sensors/addSensor.html',
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
                    return sensorsService.addSensor(self.name, self.gpio, self.reverted, self.type);
                })
                .then(function() {
                    return sensorsService.loadDevices();
                })
                .then(function() {
                    toast.success('Sensor added');
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
            var oldName = device.name;
            self.name = device.name;
            self.type = device.type;
            self.reverted = device.reverted;
            if( device.type==='motion' )
            {
                self.gpio = device.gpios[0].gpio;
            }

            //open dialog
            self.updateDevice = true;
            self._openDialog()
                .then(function() {
                    return sensorsService.updateSensor(device.uuid, self.name, self.reverted);
                })
                .then(function() {
                    return sensorsService.loadDevices();
                })
                .then(function() {
                    toast.success('Sensor updated');
                }) 
                .finally(function() {
                    self._resetValues();
                }); 
        }; 

        /** 
         * Delete device
         */
        self.openDeleteDialog = function(device) {
            confirm.open('Delete sensor?', null, 'Delete')
                .then(function() {
                    return sensorsService.deleteSensor(device.uuid);
                })
                .then(function() {
                    return sensorsService.loadDevices();
                })
                .then(function() {
                    toast.success('Sensor deleted');
                }); 
        };  

        /**
         * Init controller
         */
        self.init = function() {
            var config = configsService.getConfig('sensors');
            self.raspiGpios = config.raspi_gpios;
        };

    }];

    var sensorsLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'js/configuration/sensors/sensors.html',
        replace: true,
        scope: true,
        controller: sensorsController,
        controllerAs: 'sensorsCtl',
        link: sensorsLink
    };
};

var sensorGpiosFilter = function($filter) {
    return function(gpios) {
        if( gpios && angular.isArray(gpios) )
        {
            names = [];
            for( var i=0; i<gpios.length; i++)
            {
                names.push(gpios[i].gpio);
            }
            return names.join(',');
        }
    };
}

var RaspIot = angular.module('RaspIot');
RaspIot.directive('sensorsConfigDirective', ['toastService', 'objectsService', 'configsService', 'sensorsService', 'confirmService', '$mdDialog', sensorsConfigDirective]);
RaspIot.filter('displayGpios', sensorGpiosFilter);

