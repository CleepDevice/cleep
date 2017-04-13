/**
 * Motion widget directive
 * Display motion dashboard widget
 */
var widgetMotionDirective = function(raspiotService) {

    var widgetMotionController = ['$scope', function($scope) {
        var self = this;
        self.device = $scope.device;
        self.graphOptions = {
            'type': 'line',
            'color': '#24A222'
        };
        self.hasDatabase = raspiotService.hasModule('database');
    }];

    return {
        restrict: 'EA',
        templateUrl: 'js/dashboard/widgets/sensors/motion.html',
        replace: true,
        scope: {
            'device': '='
        },
        controller: widgetMotionController,
        controllerAs: 'widgetCtl'
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('widgetMotionDirective', ['raspiotService', widgetMotionDirective]);

