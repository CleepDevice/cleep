/**
 * Dveloper widget directive
 * Display developer dashboard widget
 */
var widgetDeveloperDirective = function() {

    var widgetDeveloperController = ['$scope', 'developerService', function($scope, developerService) {
        var self = this;
        self.device = $scope.device;

        self.restartRaspiot = function() {
            developerService.restartRaspiot();
        };
    }];

    return {
        restrict: 'EA',
        templateUrl: 'js/dashboard/widgets/developer/developer.html',
        replace: true,
        scope: {
            'device': '='
        },
        controller: widgetDeveloperController,
        controllerAs: 'widgetCtl'
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('widgetDeveloperDirective', [widgetDeveloperDirective]);

