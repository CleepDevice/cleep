/**
 * Motion widget directive
 * Display motion dashboard widget
 */
var widgetMotionDirective = function() {

    var widgetMotionController = ['$scope', function($scope) {
        var self = this;
        self.device = $scope.device;
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
RaspIot.directive('widgetMotionDirective', [widgetMotionDirective]);

