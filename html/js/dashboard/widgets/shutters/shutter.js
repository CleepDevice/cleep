/**
 * Shutter widget directive
 * Display shutter dashboard widget
 */
var widgetShutterDirective = function(shuttersService) {

    var widgetShutterController = ['$scope', function($scope) {
        var self = this;
        self.device = $scope.device;

        /**
         * Open shutter
         */
        self.openShutter = function()
        {
            shuttersService.openShutter(self.device);
        };

        /**
         * Close shutter
         */
        self.closeShutter = function()
        {
            shuttersService.closeShutter(self.device);
        };

        /**
         * Stop shutter
         */
        self.stopShutter = function()
        {
            shuttersService.stopShutter(self.device);
        };
    }];

    return {
        restrict: 'EA',
        templateUrl: 'js/directives/widgets/shutters/shutter.html',
        replace: true,
        scope: {
            'device': '='
        },
        controller: widgetShutterController,
        controllerAs: 'widgetCtl'
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('widgetShutterDirective', ['shuttersService', widgetShutterDirective]);
