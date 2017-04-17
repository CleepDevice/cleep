/**
 * Sensors config directive
 * Handle sensors configuration
 */
var sensorsConfigDirective = function(toast, raspiotService, sensorsService, confirm, $mdDialog) {

    var sensorsController = [function() {
        var self = this;
        self.raspiGpios = [];
        self.devices = raspiotService.devices;
        self.name = '';
        self.gpio = 'GPIO2';
        self.reverted = false;
        self.onewires = [];
        self.onewire = '';
        self.intervals = [
            {label:'5 minutes', value:300},
            {label:'15 minutes', value:900},
            {label:'30 minutes', value:1800},
            {label:'1 hour', value:3600}
        ];
        self.interval = self.intervals[1].value;
        self.offset = 0;
        self.offsetUnits = [
            {label:'Celsius', value:'celsius'},
            {label:'Fahrenheit', value:'fahrenheit'}
        ];
        self.offsetUnit = self.offsetUnits[0].value;
        self.TYPE_MOTION_GENERIC = 'motion_generic';
        self.TYPE_TEMPERATURE_ONEWIRE = 'temperature_onewire';
        self.types = [
            {label:'Motion', value:self.TYPE_MOTION_GENERIC},
            {label:'Temperature (onewire)', value:self.TYPE_TEMPERATURE_ONEWIRE}
        ];
        self.type = self.TYPE_MOTION_GENERIC;
        self.updateDevice = false;

        /**
         * Return sensor type
         */
        self._getSensorType = function(sensor) {
            return sensor.type + '_' + sensor.subtype;
        };

        /** 
         * Reset editor's values
         */
        self._resetValues = function() {
            self.name = ''; 
            self.gpio = 'GPIO2';
            self.reverted = false;
            self.type = self.TYPE_MOTION_GENERIC;
            self.interval = self.intervals[1].value;
            self.offset = 0;
            self.offsetUnit = self.offsetUnits[0].value;
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
                    if( self.type===self.TYPE_MOTION_GENERIC )
                    {
                        return sensorsService.addGenericMotionSensor(self.name, self.gpio, self.reverted);
                    }
                    else if( self.type===self.TYPE_TEMPERATURE_ONEWIRE )
                    {
                        return sensorsService.addOnewireTemperatureSensor(self.name, self.onewire.device, self.onewire.path, self.interval, self.offset, self.offsetUnit, 'GPIO4');
                    }
                })
                .then(function() {
                    return raspiotService.reloadDevices();
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
            self.type = self._getSensorType(device);
            if( self.type===self.TYPE_MOTION_GENERIC )
            {
                self.gpio = device.gpios[0].gpio;
                self.reverted = device.reverted;
            }
            else if( self.type===self.TYPE_TEMPERATURE_ONEWIRE )
            {
                self.interval = device.interval;
                self.offset = device.offset;
                self.offsetUnit = device.offsetunit;
            }

            //open dialog
            self.updateDevice = true;
            self._openDialog()
                .then(function() {
                    if( self.type===self.TYPE_MOTION_GENERIC )
                    {
                        return sensorsService.updateGenericMotionSensor(device.uuid, self.name, self.reverted);
                    }
                    else if( self.type===self.TYPE_TEMPERATURE_ONEWIRE )
                    {
                        return sensorsService.updateOnewireTemperatureSensor(device.uuid, self.name, self.interval, self.offset, self.offsetUnit);
                    }
                })
                .then(function() {
                    return raspiotService.reloadDevices();
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
            confirm.open('Delete sensor?', 'All sensor data will be deleted and you will not be able to restore it!', 'Delete')
                .then(function() {
                    return sensorsService.deleteSensor(device.uuid);
                })
                .then(function() {
                    return raspiotService.reloadDevices();
                })
                .then(function() {
                    toast.success('Sensor deleted');
                }); 
        };

        /**
         * Get onewire devices
         */
        self.getOnewires = function() {
            sensorsService.getOnewires()
                .then(function(resp) {
                    self.onewires = resp.data;
                    self.onewire = self.onewires[0];
                });
        };

        /**
         * Init controller
         */
        self.init = function() {
            var config = raspiotService.getConfig('sensors');
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
RaspIot.directive('sensorsConfigDirective', ['toastService', 'raspiotService', 'sensorsService', 'confirmService', '$mdDialog', sensorsConfigDirective]);
RaspIot.filter('displayGpios', sensorGpiosFilter);

