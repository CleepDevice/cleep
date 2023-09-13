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
.directive('dashboardwidget', ['$compile', '$injector', 'cleepService',
function($compile, $injector, cleepService) {
    var dashboardWidgetLink = function(scope, element, attr) {
        cleepService.getModuleDescription(scope.device.module).then((conf) => {
            const directiveName = scope.type + 'Widget';
            const isAngularWidget = $injector.has(directiveName+'Directive');
            const widgetConf = cleepService.getWidgetConfig(scope.type);
            const isConfWidget = Boolean(widgetConf);

            if (!isAngularWidget && !isConfWidget) {
                // non-renderable widget
                console.warn('Widgets of type "'+scope.type+'" is not renderable');
                return;
            }

            const template = isAngularWidget ?
                '<div ' + directiveName.toKebab() + ' device="device"></div>' :
                '<widget-conf cl-device="device" cl-widget-conf="conf" cl-app-icon="' + conf.icon + '"></widget-conf>';

            if (!isAngularWidget) {
                // apply custom widget footer if any
                const customFooter = conf.widgets?.[scope.type]?.footer
                if (customFooter) {
                    widgetConf.footer = customFooter;
                }
                scope.conf = widgetConf;
            }

            const widget = $compile(template)(scope);
            element.append(widget);
        });
    };

    return {
        restrict: 'E',
        scope: {
            type: '@',
            device: '<'
        },
        link: dashboardWidgetLink
    }
}]);

