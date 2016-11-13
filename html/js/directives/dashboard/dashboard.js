
var dashboardDirective = function($rootScope, $q, growl, blockUI) {
    var container = null;

    var dashboardController = ['$scope', '$injector', 'rpcService', 'objectsService', function($scope, $injector, rpcService, objectsService) {
        //threshold to display search toolbar
        $scope.devicesThreshold = 10;
        //devices
        $scope.devices = objectsService.devices;
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
