/**
 * Gpio widget directive
 * Display gpio dashboard widget
 */
var widgetGpioDirective = function() {

    var widgetGpioController = ['$scope', function($scope) {
        var self = this;
        self.device = $scope.device;
    }];

    return {
        restrict: 'EA',
        templateUrl: 'js/dashboard/widgets/gpios/gpio.html',
        replace: true,
        scope: {
            'device': '='
        },
        controller: widgetGpioController,
        controllerAs: 'widgetCtl'
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('widgetGpioDirective', [widgetGpioDirective]);

