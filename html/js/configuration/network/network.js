/**
 * Network config directive
 * Handle network configuration
 */
var networkConfigDirective = function(toast, networkService, raspiotService) {

    var networkController = function()
    {
        var self = this;
        self.networkType = 'wifi';

        /**
         * Scan wifi networks
         */
        self.scanWifiNetworks = function()
        {
            networkService.scanWifiNetworks()
                .then(function(resp) {
                    console.log('wifi networks', resp);
                });
        };

        /**
         * Get interfaces configurations
         */
        self.getInterfacesConfigurations = function()
        {
            networkService.getInterfacesConfigurations()
                .then(function(resp) {
                    console.log('network config', resp);
                });
        };

        /**
         * Init controller
         */
        self.init = function()
        {
           //self.getInterfacesConfigurations();
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
RaspIot.directive('networkConfigDirective', ['toastService', 'networkService', 'raspiotService', networkConfigDirective])
