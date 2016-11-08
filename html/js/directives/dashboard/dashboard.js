
var dashboardDirective = function($rootScope, $q, growl, blockUI) {
    var container = null;

    var dashboardController = ['$scope', '$injector', 'rpcService', 'objectsService', function($scope, $injector, rpcService, objectsService) {
        //threshold to display search toolbar
        $scope.devicesThreshold = 10;
        //devices
        $scope.devices = objectsService.devices;

        $scope.test = function()
        {
            //console.log('test');
            //$rootScope.$broadcast('event.gpio.on')
            objectsService.services['gpios'].loadDevices();
        };

        /**
         * Get device template path
         */
        $scope.getTemplate = function(object)
        {
            return 'views/widgets/' + objectsService.getObjectTemplateName(object) + '.html';
        };

        /**
         * Init controller
         */
        function init()
        {
        };

        //init directive
        init();
    }];

    var dashboardLink = function(scope, element, attrs) {
        container = blockUI.instances.get('dashboardContainer');
        container.reset();
    };

    return {
        templateUrl: 'js/directives/dashboard/dashboard.html',
        replace: true,
        scope: true,
        controller: dashboardController,
        link: dashboardLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('dashboardDirective', ['$rootScope', '$q', 'growl', 'blockUI', dashboardDirective]);
