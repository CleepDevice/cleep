/**
 * Clock widget directive
 * Display clock dashboard widget
 */
var widgetClockDirective = function(parametersService) {

    var widgetClockController = ['$scope', function($scope) {
        var self = this;
        self.device = $scope.device;
    }];

    return {
        restrict: 'EA',
        templateUrl: 'clock.widget.html',
        replace: true,
        scope: {
            'device': '='
        },
        controller: widgetClockController,
        controllerAs: 'widgetCtl'
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('widgetClockDirective', ['parametersService', widgetClockDirective]);

