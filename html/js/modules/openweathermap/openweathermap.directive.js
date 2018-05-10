/**
 * OpenWeatherMap config directive
 * Handle openweathermap configuration
 */
var openweathermapConfigDirective = function(toast, openweathermapService, raspiotService) {

    var openweathermapController = function()
    {
        var self = this;
        self.apikey = '';

        /**
         * Set api key
         */
        self.setApikey = function()
        {
            openweathermapService.setApikey(self.apikey)
                .then(function(resp) {
                    return raspiotService.reloadModuleConfig('openweathermap');
                })
                .then(function(config) {
                    self.apikey = config.apikey;
                    toast.success('Configuration saved.');
                });
        };

        /**
         * Init controller
         */
        self.init = function()
        {
            raspiotService.getModuleConfig('openweathermap')
                .then(function(config) {
                    self.apikey = config.apikey;
                });
        };

    };

    var openweathermapLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'openweathermap.directive.html',
        replace: true,
        scope: true,
        controller: openweathermapController,
        controllerAs: 'openweathermapCtl',
        link: openweathermapLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('openweathermapConfigDirective', ['toastService', 'openweathermapService', 'raspiotService', openweathermapConfigDirective])

