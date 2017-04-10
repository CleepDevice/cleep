/**
 * Shutter widget directive
 * Display shutter dashboard widget
 */
var widgetShutterDirective = function(shuttersService) {

    var widgetShutterController = ['$scope', '$mdDialog', function($scope, $mdDialog) {
        var self = this;
        self.device = $scope.device;
        self.level = 0;

        /**
         * Open shutter
         */
        self.openShutter = function()
        {
            shuttersService.openShutter(self.device.uuid);
        };

        /**
         * Close shutter
         */
        self.closeShutter = function()
        {
            shuttersService.closeShutter(self.device.uuid);
        };

        /**
         * Stop shutter
         */
        self.stopShutter = function()
        {
            shuttersService.stopShutter(self.device.uuid);
        };

        /**
         * Open dialog (internal use)
         */
        self._openDialog = function() {
            return $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'levelCtl',
                templateUrl: 'js/dashboard/widgets/shutters/levelDialog.html',
                parent: angular.element(document.body),
                clickOutsideToClose: true
            });
        };

        /**
         * Change shutter level
         */
        self.openLevelDialog = function() {
            self._openDialog()
                .then(function() {
                    return shuttersService.levelShutter(self.device.uuid, self.level);
                });
        };

        /**
         * Cancel dialog
         */
        self.cancelDialog = function() {
            $mdDialog.cancel();
        };

        /**
         * Close dialog
         */
        self.closeDialog = function() {
            $mdDialog.hide();
        };

    }];

    return {
        restrict: 'EA',
        templateUrl: 'js/dashboard/widgets/shutters/shutter.html',
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

