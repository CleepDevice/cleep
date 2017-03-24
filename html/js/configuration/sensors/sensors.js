/**
 * Sensors config directive
 * Handle sensors configuration
 */
var sensorsConfigDirective = function($q, toast, objectsService, sensorsService, confirm, $mdDialog) {

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
                templateUrl: 'js/directives/sensors/addSensor.html',
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
                    self._addSensor();
                    sensorsService.loadDevices();
                    toast.success('Sensor added');
                 }, function() {})
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
            self.type = device.type;
            self.reverted = device.reverted;
            if( device.type==='motion' )
            {
                self.gpio = device.gpios[0];
            }

            //open dialog
            self.updateDevice = true;
            self._openDialog()
                .then(function() {
                    self._deleteSensor(device);
                    self._addSensor();
                    toast.success('Sensor updated');
                }, function() {}) 
                .finally(function() {
                    self._resetValues();
                }); 
        }; 

        /** 
         * Delete sensor
         */
        self.openDeleteDialog = function(device) {
            confirm.open('Delete sensor?', null, 'Delete')
                .then(function() {
                    self._deleteSensor();
                    toast.success('Sensor deleted');
                }); 
        };  

        /** 
         * Add sensor (internal use)
         */
        self._addSensor = function() {
            return sensorsService.addSensor(self.name, self.gpio, self.reverted, self.type)
                .then(function(resp) {
                    sensorsService.loadDevices();
                });
        };

        /**
         * Delete sensor (internal use)
         */
        self._deleteSensor = function(device) {
            sensorsService.deleteSensor(device.name)
                .then(function(resp) {
                    sensorsService.loadDevices();
                });
        };

        /**
         * Return raspberry pi gpios
         */
        self.getRaspiGpios = function() {
            return sensorsService.getRaspiGpios()
                .then(function(resp) {
                    for( var gpio in resp )
                    {
                        resp[gpio].gpio = gpio;
                    }
                    self.raspiGpios = resp;
                });
        };

        /**
         * Init controller
         */
        self.init = function() {
            self.getRaspiGpios();
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

var RaspIot = angular.module('RaspIot');
RaspIot.directive('sensorsConfigDirective', ['$q', 'toastService', 'objectsService', 'sensorsService', 'confirmService', '$mdDialog', sensorsConfigDirective]);

