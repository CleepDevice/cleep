
var sensorsConfigDirective = function($q, growl, blockUI, objectsService, sensorsService, $mdBottomSheet) {
    var container = null;

    var sensorsController = [function() {
        var self = this;
        self.raspiGpios = [];
        self.devices = objectsService.devices;
        self.name = '';
        self.gpio = 'GPIO2';
        self.reverted = false;
        self.showAddPanel = false;
        self.currentDevice = null;

        self.openAddPanel = function(ev) {
            self.showAddPanel = true;
        };

        self.closeAddPanel = function(ev) {
            self.showAddPanel = false;
        };

        /**
         * Return raspberry pi gpios
         */
        function getRaspiGpios() {
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
            getRaspiGpios();
        };

        /**
         * Add motion
         */
        self.addMotion = function() {
            sensorsService.addMotion(self.name, self.gpio, self.reverted)
                .then(function(resp) {
                    growl.success('Motion sensor added');
                });
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
        };

    }];

    var sensorsLink = function(scope, element, attrs, controller) {
        container = blockUI.instances.get('sensorsContainer');
        container.reset();

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
RaspIot.directive('sensorsConfigDirective', ['$q', 'growl', 'blockUI', 'objectsService', 'sensorsService', '$mdBottomSheet', sensorsConfigDirective]);
