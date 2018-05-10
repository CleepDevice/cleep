/**
 * BulkSms config directive
 * Handle bulksms configuration
 */
var bulksmsConfigDirective = function(toast, bulksmsService, raspiotService) {

    var bulksmsController = function()
    {
        var self = this;
        self.username = '';
        self.password = '';
        self.phoneNumbers = '';
        self.credits = 0;

        /**
         * Set credentials
         */
        self.setCredentials = function()
        {
            bulksmsService.setCredentials(self.username, self.password, self.phoneNumbers)
                .then(function(resp) {
                    return raspiotService.reloadModuleConfig('bulksms');
                })
                .then(function(config) {
                    self.username = config.username;
                    self.password = '';
                    self.phoneNumbers = config.phoneNumbers;
                    self.credits = config.credits;

                    toast.success('Credentials saved');
                });
        };

        /**
         * Get credits
         */
        self.getCredits = function()
        {
            bulksmsService.getCredits()
                .then(function(resp) {
                    self.credits = resp.data;
                    toast.success('Credits refreshed');
                });
        };

        /**
         * Init controller
         */
        self.init = function()
        {
            raspiotService.getModuleConfig('bulksms')
                .then(function(config) {
                    self.username = config.username;
                    self.phoneNumbers = config.phone_numbers;
                    self.credits = config.credits;
                });
        };

    };

    var bulksmsLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'bulksms.directive.html',
        replace: true,
        scope: true,
        controller: bulksmsController,
        controllerAs: 'bulksmsCtl',
        link: bulksmsLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('bulksmsConfigDirective', ['toastService', 'bulksmsService', 'raspiotService', bulksmsConfigDirective])

