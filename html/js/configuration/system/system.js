/**
 * System config directive
 * Handle system configuration
 */
var systemConfigDirective = function($filter, $timeout, toast, systemService, raspiotService, confirm) {

    var systemController = function()
    {
        var self = this;
        self.sunset = null;
        self.sunrise = null;
        self.city = null;
        self.monitoring = false;

        /**
         * Set city
         */
        self.setCity = function() {
            toast.loading('Updating city...');
            systemService.setCity(self.city)
                .then(function(resp) {
                    return raspiotService.reloadModuleConfig('system');
                })
                .then(function(resp) {
                    toast.success('City updated');
                    self.sunset = $filter('hrTime')(resp.sun.sunset);
                    self.sunrise = $filter('hrTime')(resp.sun.sunrise);
                });
        };

        /**
         * Save monitoring
         */
        self.setMonitoring = function() {
            //delay update to make sure model value is updated
            $timeout(function() {
                systemService.setMonitoring(self.monitoring)
                    .then(function(resp) {
                        return raspiotService.reloadModuleConfig('system');
                    })
                    .then(function(resp) {
                        toast.success('Monitoring updated');
                    });
            }, 250);
        };

        /**
         * Reboot system
         */
        self.reboot = function() {
            confirm.open('Confirm device reboot?', null, 'Reboot')
                .then(function() {
                    return systemService.reboot();
                })
                .then(function() {
                    toast.success('System will reboot');
                });
        };

        /**
         * Halt system
         */
        self.halt = function() {
            confirm.open('Confirm device shutdown?', null, 'Reboot')
                .then(function() {
                    systemService.halt();
                })
                .then(function() {
                    toast.success('System will halt');
                });
        };

        /**
         * Restart raspiot
         */
        self.restart = function() {
            confirm.open('Confirm application restart?', null, 'Reboot')
                .then(function() {
                    systemService.restart();
                })
                .then(function() {
                    toast.success('Raspiot will restart');
                });
        };

        /**
         * Init controller
         */
        self.init = function()
        {
            raspiotService.getModuleConfig('system')
                .then(function(config) {
                    self.city = config.city;
                    self.sunset = $filter('hrTime')(config.sun.sunset);
                    self.sunrise = $filter('hrTime')(config.sun.sunrise);
                    self.monitoring = config.monitoring;
                });
        };

    };

    var systemLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'js/configuration/system/system.html',
        replace: true,
        scope: true,
        controller: systemController,
        controllerAs: 'systemCtl',
        link: systemLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('systemConfigDirective', ['$filter', '$timeout', 'toastService', 'systemService', 'raspiotService', 'confirmService', systemConfigDirective]);

