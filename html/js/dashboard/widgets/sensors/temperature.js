/**
 * Temperature widget directive
 * Display temperature dashboard widget
 */
var widgetTemperatureDirective = function(raspiotService) {

    var widgetTemperatureController = ['$scope', function($scope) {
        var self = this;
        self.device = $scope.device;
        self.graphOptions = {
            'type': 'line',
            'fields': ['timestamp', 'celsius']
        };
        self.hasDatabase = raspiotService.hasModule('database');
    }];

    return {
        restrict: 'EA',
        templateUrl: 'js/dashboard/widgets/sensors/temperature.html',
        replace: true,
        scope: {
            'device': '='
        },
        controller: widgetTemperatureController,
        controllerAs: 'widgetCtl'
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('widgetTemperatureDirective', ['raspiotService', widgetTemperatureDirective]);
