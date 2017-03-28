/**
 * Scheduler config directive
 * Handle scheduler configuration
 */
var schedulerConfigDirective = function($filter, toast, schedulerService, configsService) {
    var container = null;

    var schedulerController = function() {
        var self = this;
        self.sunset = null;
        self.sunrise = null;
        self.city = null;

        /**
         * Init controller
         */
        self.init = function()
        {
            var config = configsService.getConfig('scheduler');
            self.city = config.city;
            self.sunset = $filter('hrTime')(config.sun.sunset);
            self.sunrise = $filter('hrTime')(config.sun.sunrise);
        };

        /**
         * Set city
         */
        self.setCity = function()
        {
            toast.loading('Updating city...');
            schedulerService.setCity(self.city)
                .then(function(resp) {
                    return configsService.reloadConfig('scheduler');
                })
                .then(function(resp) {
                    toast.success('City updated');
                    self.sunset = $filter('hrTime')(resp.sun.sunset);
                    self.sunrise = $filter('hrTime')(resp.sun.sunrise);
                });
        };
    };

    var schedulerLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'js/configuration/scheduler/scheduler.html',
        replace: true,
        scope: true,
        controller: schedulerController,
        controllerAs: 'schedulerCtl',
        link: schedulerLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('schedulerConfigDirective', ['$filter', 'toastService', 'schedulerService', 'configsService', schedulerConfigDirective]);

