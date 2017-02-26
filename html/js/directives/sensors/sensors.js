
var sensorsConfigDirective = function($q, toast, objectsService, sensorsService, confirm) {

    var sensorsController = [function() {
        var self = this;
        self.raspiGpios = [];
        self.devices = objectsService.devices;
        self.name = '';
        self.gpio = 'GPIO2';
        self.reverted = false;
        self.showAddPanel = false;
        self.currentDevice = null;

        /**
         * Open add panel
         */
        self.openAddPanel = function(ev) {
            self.showAddPanel = true;
        };

        /**
         * Close add panel
         */
        self.closeAddPanel = function(ev) {
            //close panel
            self.showAddPanel = false;

            //reset fields
            self.name = '';
            self.gpio = 'GPIO2';
            self.reverted = false;
            self.currentDevice = null;
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
            //get gpios
            self.getRaspiGpios();
        };

        /**
         * Add/update motion sensor
         */
        self.addMotion = function() {
            //check parameters
            if( self.name.length===0 )
            {
                toast.error('All fields are required');
                return;
            }

            if( self.currentDevice!==null )
            {
                //update device, first of all delete existing sensor
                sensorsService.deleteSensor(device.name)
                    .then(function(resp) {
                        //then add updated one
                        sensorsService.addSensor(self.name, self.gpio, self.reverted)
                            .then(function(resp) {
                                toast.success('Sensor updated');
                                sensorsService.loadDevices();
                            });
                    });
            }
            else
            {
                //add new device
                sensorsService.addMotion(self.name, self.gpio, self.reverted)
                    .then(function(resp) {
                        toast.success('Sensor added');
                        sensorsService.loadDevices();
                    });
            }
        };

        /**
         * Edit specified device
         */
        self.editDevice = function(device) {
            self.currentDevice = device;
        };

        /**
         * Delete specified device
         */
        self.deleteDevice = function(device) {
            confirm.dialog('Delete sensor ?', null, 'Delete')
                .then(function() {
                    sensorsService.deleteSensor(device.name)
                        .then(function(resp) {
                            sensorsService.loadDevices();
                        });
                });
        };

    }];

    var sensorsLink = function(scope, element, attrs, controller) {
        //init controller
        controller.init();
    };

    return {
        templateUrl: 'js/directives/sensors/sensors.html',
        replace: true,
        scope: true,
        controller: sensorsController,
        controllerAs: 'sensorsCtl',
        link: sensorsLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('sensorsConfigDirective', ['$q', 'toastService', 'objectsService', 'sensorsService', 'confirmService', sensorsConfigDirective]);
