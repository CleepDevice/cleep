/**
 * System config directive
 * Handle system configuration
 */
var systemConfigDirective = function($filter, toast, systemService, raspiotService) {
    var container = null;

    var systemController = function() {
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
                    return raspiotService.reloadConfig('system');
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

        };

        /**
         * Init controller
         */
        self.init = function()
        {
            var config = raspiotService.getConfig('system');
            self.city = config.city;
            self.sunset = $filter('hrTime')(config.sun.sunset);
            self.sunrise = $filter('hrTime')(config.sun.sunrise);
            self.monitoring = config.monitoring;
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
RaspIot.directive('systemConfigDirective', ['$filter', 'toastService', 'systemService', 'raspiotService', systemConfigDirective]);

