
var dashboardDirective = function($rootScope, $q, growl, blockUI) {
    var container = null;

    var dashboardController = ['$scope', '$injector', 'rpcService', 'objectsService', function($scope, $injector, rpcService, objectsService) {
        var self = this;
        //threshold to display search toolbar
        self.devicesThreshold = 10;
        //devices
        self.devices = objectsService.devices;
    }];

    var dashboardLink = function(scope, element, attrs, controller) {
    };

    return {
        templateUrl: 'js/directives/dashboard/dashboard.html',
        replace: true,
        scope: true,
        controller: dashboardController,
        controllerAs: 'dashboardCtl',
        link: dashboardLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('dashboardDirective', ['$rootScope', '$q', 'growl', 'blockUI', dashboardDirective]);
