/**
 * Scheduler config directive
 * Handle scheduler configuration
 */
var schedulerDirective = function($q, toast, schedulerService) {
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
            self.getSun();
            self.getCity();
        };

        /**
         * Get configured sunset and sunrise
         */
        self.getSun = function()
        {
            schedulerService.getSun()
                .then(function(res) {
                    self.sunset = moment.unix(res.sunset).format('HH:mm');
                    self.sunrise = moment.unix(res.sunrise).format('HH:mm');
                });
        };

        /**
         * Get configured city
         */
        self.getCity = function()
        {
            schedulerService.getCity()
                .then(function(res) {
                    self.city = res;
                });
        }

        /**
         * Set city
         */
        self.setCity = function()
        {
            toast.loading('Updating city...');
            schedulerService.setCity(self.city)
                .then(function(res) {
                    toast.success('City updated');
                    self.sunset = moment.unix(res.sunset).format('HH:mm');
                    self.sunrise = moment.unix(res.sunrise).format('HH:mm');
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
RaspIot.directive('schedulerDirective', ['$q', 'toastService', 'schedulerService', schedulerDirective]);

