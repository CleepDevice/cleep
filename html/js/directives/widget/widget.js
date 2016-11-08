
var widgetDirective = function($rootScope, $q, growl, blockUI) {

    var widgetController = ['$scope', '$injector', 'rpcService', 'objectsService', function($scope, $injector, rpcService, objectsService) {
        /**
         * Init controller
         */
        function init()
        {
        };

        $scope.getTemplate = function()
        {
            return 'views/widgets/' + objectsService.getObjectTemplateName($scope.device) + '.html';
        };

        //init directive
        init();
    }];

    return {
        restrict: 'EA',
        templateUrl: 'js/directives/widget/widget.html',
        replace: true,
        scope: {
            'device': '=widgetDirective'
        },
        controller: widgetController
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('widgetDirective', ['$rootScope', '$q', 'growl', 'blockUI', widgetDirective]);
