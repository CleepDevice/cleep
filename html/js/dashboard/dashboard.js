/**
 * Dashboard directive
 * Used to display device widgets dashboard
 */
angular
.module('Cleep')
.directive('dashboardDirective', [
function() {

    var dashboardController = function($scope, cleepService) {
        var self = this;
        self.loading = true;
        self.devices = cleepService.devices;

        // only used to know when initial loading is terminated
        cleepService.getModuleConfig('system')
            .then(function() {
                self.loading = false;
            });
    };

    return {
        templateUrl: 'js/dashboard/dashboard.html',
        replace: true,
        scope: true,
        controller: ['$scope', 'cleepService', dashboardController],
        controllerAs: 'dashboardCtl'
    };
}]);

/**
 * Dashboard widget
 * Used to display dynamically device widgets
 * @see https://stackoverflow.com/a/41427771
 */
angular
.module('Cleep')
.directive('dashboardwidget', ['$compile',
function($compile) {
    var dashboardWidgetLink = function(scope, element, attr) {
        const template = '<div '+scope.type+'-widget device="device" style="height:100%;"></div>';
        var widget = $compile(template)(scope);
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
}]);

