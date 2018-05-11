/**
 * Dashboard directive
 * Used to display device widgets dashboard
 */
var dashboardDirective = function() {

    var dashboardController = function($scope, raspiotService) {
        var self = this;
        self.devices = raspiotService.devices;
    };

    return {
        templateUrl: 'js/dashboard/dashboard.html',
        replace: true,
        scope: true,
        controller: ['$scope', 'raspiotService', dashboardController],
        controllerAs: 'dashboardCtl'
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('dashboardDirective', [dashboardDirective]);

