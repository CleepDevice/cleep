/**
 * Dveloper widget directive
 * Display developer dashboard widget
 */
var widgetDeveloperDirective = function() {

    var widgetDeveloperController = ['$scope', 'developerService', function($scope, developerService) {
        var self = this;
        self.device = $scope.device;

        //restart raspiot
        self.restartRaspiot = function() {
            developerService.restartRaspiot();
        };

        //start pyremotedev
        self.startPyremotedev = function() {
            developerService.startPyremotedev()
                .then(function(resp) {
                    if( resp.data )
                        self.device.running = true;
                });
        };

        //stop pyremotedev
        self.stopPyremotedev = function() {
            developerService.stopPyremotedev()
                .then(function(resp) {
                    if( resp.data )
                        self.device.running = false;
                });
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
