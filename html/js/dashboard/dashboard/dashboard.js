/**
 * Dashboard directive
 * Used to display device widgets dashboard
 */
var dashboardDirective = function() {

    var dashboardController = function($scope, $injector, rpcService, objectsService) {
        var self = this;

        //threshold to display search toolbar
        self.devicesThreshold = 10;
        //devices
        self.devices = objectsService.devices;
        console.log('DEVICES', self.devices);
    };

    return {
        templateUrl: 'js/dashboard/dashboard/dashboard.html',
        replace: true,
        scope: true,
        controller: dashboardController,
        controllerAs: 'dashboardCtl'
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('dashboardDirective', [dashboardDirective]);

