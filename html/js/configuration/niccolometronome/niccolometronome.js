/**
 * Niccolo metronome config directive
 * Handle niccolo metronome configuration
 */
var niccolometronomeConfigDirective = function(toast, niccolometronomeService, raspiotService) {

    var niccolometronomeController = function()
    {
        var self = this;

        self.playSound = function()
        {
            niccolometronomeService.playSound();
        };

        /**
         * Init controller
         */
        self.init = function()
        {
            /*raspiotService.getModuleConfig('bulksms')
                .then(function(config) {
                    self.username = config.username;
                    self.phoneNumbers = config.phone_numbers;
                    self.credits = config.credits;
                });*/
        };

    };

    var niccolometronomeLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'js/configuration/niccolometronome/niccolometronome.html',
        replace: true,
        scope: true,
        controller: niccolometronomeController,
        controllerAs: 'niccolometronomeCtl',
        link: niccolometronomeLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('niccolometronomeConfigDirective', ['toastService', 'niccolometronomeService', 'raspiotService', niccolometronomeConfigDirective])

