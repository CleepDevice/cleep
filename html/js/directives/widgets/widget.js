
var widgetDirective = function() {

    var widgetController = ['$scope', function($scope) {
        var self = this;
        self.device = $scope.device;

        /**
         * Init controller
         */
        self.init = function()
        {
            //nothing to init yet
        };
    }];

    var widgetLink = function(scope, element, attrs, controller) {
        //init controller
        controller.init();
    };

    return {
        restrict: 'EA',
        template: '<div ng-include="getTemplateUrl()"></div>',
        //templateUrl: 'js/directives/widget/test.html',
        /*templateUrl: function(element, attrs) {
            console.log('ELEMENT', element);
            console.log('ATTRS', attrs);
            return 'js/directives/widget/test.html';
        },*/
        replace: true,
        link: function(scope, element, attrs) {
            scope.getTemplateUrl = function()
            {
                if( scope.device.__type==='motion' ) {
                    return 'js/directives/widget/sensors/motion.html';
                } else if ( scope.device.__type==='gpios' ) {
                    return 'js/directives/widget/gpios/gpio.html';
                } else if ( scope.device.__type==='clock' ) {
                    return 'js/directives/widget/scheduler/clock.html';
                } else if ( scope.device.__type==='shutter' ) {
                    return 'js/directives/widget/shutters/shutter.html';
                } else if ( scope.device.__type==='messageboard' ) {
                    return 'js/directives/widget/messageboard/messageboard.html';
                } else {
                    console.error('Widget template for device type "'+scope.device.__type+'" not found');
                }
            };
        },
        scope: {
            'device': '=widgetDirective'
        },
        controller: '@',
        controllerAs: 'widgetCtl',
        name: 'widgetControllerName'
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('widgetDirective', [widgetDirective]);
