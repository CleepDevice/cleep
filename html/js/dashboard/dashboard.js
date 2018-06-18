/**
 * Dashboard directive
 * Used to display device widgets dashboard
 */
var dashboardDirective = function() {

    var dashboardController = function($scope, raspiotService) {
        var self = this;
        self.loading = true;
        self.devices = raspiotService.devices;

        //only used to know when initial loading is terminated
        raspiotService.getModuleConfig('system')
            .then(function() {
                self.loading = false;
            });
    };

    return {
        templateUrl: 'js/dashboard/dashboard.html',
        replace: true,
        scope: true,
        controller: ['$scope', 'raspiotService', dashboardController],
        controllerAs: 'dashboardCtl'
    };
};

/**
 * Dashboard widget
 * Used to display dynamically device widgets
 * @see https://stackoverflow.com/a/41427771
 */
var dashboardWidget = function($compile) {

    var dashboardWidgetLink = function(scope, element, attr) {
        var widget = $compile('<div widget-' + scope.type + '-directive device="device"></div>')(scope);
        element.append(widget);
    };

    return {
        restrict: 'E',
        scope: {
          type: '@',
          device: '='
        },
        link: dashboardWidgetLink
    }
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('dashboardDirective', [dashboardDirective]);
RaspIot.directive('dashboardwidget', ['$compile', dashboardWidget]);

