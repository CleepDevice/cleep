/**
 * Openweather widget directive
 * Display openweathermap dashboard widget
 */
var widgetOpenweathermapDirective = function(raspiotService, $mdDialog, $q) {

    var widgetOpenweathermapController = ['$scope', function($scope) {
        var self = this;
        self.device = $scope.device;
        self.hasDatabase = raspiotService.hasModule('database');

        /**
         * Cancel dialog
         */
        self.cancelDialog = function()
        {
            $mdDialog.cancel();
        };

        /**
         * Open dialog
         */
        self.openDialog = function() {
            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'owmCtl',
                templateUrl: 'js/dashboard/widgets/openweathermap/openweathermapDialog.html',
                parent: angular.element(document.body),
                clickOutsideToClose: true,
                onComplete: self.loadDialogData
            });
        };

        /**
         * Init controller
         */
        self.init = function()
        {
        };

    }];

    var widgetOpenweathermapLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        restrict: 'EA',
        templateUrl: 'js/dashboard/widgets/openweathermap/openweathermap.html',
        replace: true,
        scope: {
            'device': '='
        },
        controller: widgetOpenweathermapController,
        controllerAs: 'widgetCtl',
        link: widgetOpenweathermapLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('widgetOpenweathermapDirective', ['raspiotService', '$mdDialog', '$q', widgetOpenweathermapDirective]);

