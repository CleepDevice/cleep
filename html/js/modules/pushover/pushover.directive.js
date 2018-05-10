/**
 * Pushover config directive
 * Handle pushover configuration
 */
var pushoverConfigDirective = function(toast, pushoverService, raspiotService) {

    var pushoverController = function()
    {
        var self = this;
        self.userkey = '';
        self.apikey = '';

        /**
         * Set credentials
         */
        self.setConfig = function()
        {
            pushoverService.setConfig(self.userkey, self.apikey)
                .then(function(resp) {
                    return raspiotService.reloadModuleConfig('pushover');
                })
                .then(function(config) {
                    self.userkey = config.userkey;
                    self.apikey = config.apikey;
                    toast.success('Configuration saved. You should receive a push message soon.');
                });
        };

        /**
         * Test
         */
        self.test = function()
        {
            pushoverService.test()
                .then(function(resp) {
                    toast.success('Sms sent. Check your phone.');
                });
        };

        /**
         * Init controller
         */
        self.init = function()
        {
            raspiotService.getModuleConfig('pushover')
                .then(function(config) {
                    self.userkey = config.userkey;
                    self.apikey = config.apikey;
                });
        };

    };

    var pushoverLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'pushover.directive.html',
        replace: true,
        scope: true,
        controller: pushoverController,
        controllerAs: 'pushoverCtl',
        link: pushoverLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('pushoverConfigDirective', ['toastService', 'pushoverService', 'raspiotService', pushoverConfigDirective])

