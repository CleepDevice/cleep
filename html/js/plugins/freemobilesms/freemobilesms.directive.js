/**
 * FreemobileSms config directive
 * Handle freemobilesms configuration
 */
var freemobilesmsConfigDirective = function(toast, freemobilesmsService, raspiotService) {

    var freemobilesmsController = function()
    {
        var self = this;
        self.userid = '';
        self.apikey = '';

        /**
         * Set credentials
         */
        self.setCredentials = function()
        {
            freemobilesmsService.setCredentials(self.userid, self.apikey)
                .then(function(resp) {
                    return raspiotService.reloadModuleConfig('freemobilesms');
                })
                .then(function(config) {
                    self.userid = config.userid;
                    self.apikey = config.apikey;
                    toast.success('Configuration saved. You should receive a sms soon.');
                });
        };

        /**
         * Test
         */
        self.test = function()
        {
            freemobilesmsService.test()
                .then(function(resp) {
                    toast.success('Sms sent. Check your phone.');
                });
        };

        /**
         * Init controller
         */
        self.init = function()
        {
            raspiotService.getModuleConfig('freemobilesms')
                .then(function(config) {
                    self.userid = config.userid;
                    self.apikey = config.apikey;
                });
        };

    };

    var freemobilesmsLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'freemobilesms.directive.html',
        replace: true,
        scope: true,
        controller: freemobilesmsController,
        controllerAs: 'freemobilesmsCtl',
        link: freemobilesmsLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('freemobilesmsConfigDirective', ['toastService', 'freemobilesmsService', 'raspiotService', freemobilesmsConfigDirective])

