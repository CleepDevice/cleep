/**
 * Raspberry config directive
 * Handle raspberry configuration
 */
var raspberryConfigDirective = function($filter, toast, raspberryService, raspiotService) {
    var container = null;

    var raspberryController = function() {
        var self = this;
        self.sunset = null;
        self.sunrise = null;
        self.city = null;

        /**
         * Set city
         */
        self.setCity = function()
        {
            toast.loading('Updating city...');
            raspberryService.setCity(self.city)
                .then(function(resp) {
                    return raspiotService.reloadConfig('raspberry');
                })
                .then(function(resp) {
                    toast.success('City updated');
                    self.sunset = $filter('hrTime')(resp.sun.sunset);
                    self.sunrise = $filter('hrTime')(resp.sun.sunrise);
                });
        };

        /**
         * Init controller
         */
        self.init = function()
        {
            var config = raspiotService.getConfig('raspberry');
            self.city = config.city;
            self.sunset = $filter('hrTime')(config.sun.sunset);
            self.sunrise = $filter('hrTime')(config.sun.sunrise);
        };

    };

    var raspberryLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'js/configuration/raspberry/raspberry.html',
        replace: true,
        scope: true,
        controller: raspberryController,
        controllerAs: 'raspberryCtl',
        link: raspberryLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('raspberryConfigDirective', ['$filter', 'toastService', 'raspberryService', 'raspiotService', raspberryConfigDirective]);

