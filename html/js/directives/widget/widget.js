
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
        templateUrl: 'js/directives/widget/widget.html',
        replace: true,
        link: widgetLink,
        scope: {
            'device': '=widgetDirective'
        },
        controller: widgetController,
        controllerAs: 'widgetCtl'
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('widgetDirective', [widgetDirective]);
