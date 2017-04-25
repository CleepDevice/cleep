/**
 * Network config directive
 * Handle network configuration
 */
var networkConfigDirective = function($filter, $timeout, toast, networkService, raspiotService) {

    var networkController = function()
    {
        var self = this;
        self.type = 'wired';
        self.wiredType = 'auto';

        /**
         * Init controller
         */
        self.init = function()
        {
        };

    };

    var networkLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'js/configuration/network/network.html',
        replace: true,
        scope: true,
        controller: networkController,
        controllerAs: 'networkCtl',
        link: networkLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('networkConfigDirective', ['$filter', '$timeout', 'toastService', 'systemService', 'raspiotService', networkConfigDirective]);

