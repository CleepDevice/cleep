
var sensorsConfigDirective = function($q, growl, blockUI, objectsService, sensorsService) {
    var container = null;

    var sensorsController = ['$scope', function($scope) {
        $scope.raspiGpios = [];
        $scope.devices = objectsService.devices;
        $scope.name = '';
        $scope.gpio = 'GPIO2';
        $scope.reverted = false;

        /**
         * Return raspberry pi gpios
         */
        function getRaspiGpios() {
            return sensorsService.getRaspiGpios()
            .then(function(resp) {
                for( var gpio in resp )
                {
                    resp[gpio].gpio = gpio;
                }
                $scope.raspiGpios = resp;
            });
        };

        /**
         * Init controller
         */
        function init() {
            //get gpios
            getRaspiGpios();
        };

        $scope.addMotion = function() {
            sensorsService.addMotion($scope.name, $scope.gpio, $scope.reverted)
                .then(function(resp) {
                    growl.success('Motion sensor added');
                })
        };

        /**
         * Edit specified device
         */
        $scope.editDevice = function(device) {
        };

        /**
         * Delete specified device
         */
        $scope.deleteDevice = function(device) {
        };

        //init directive
        init();
    }];

    var sensorsLink = function(scope, element, attrs) {
        container = blockUI.instances.get('sensorsContainer');
        container.reset();
    };

    return {
        templateUrl: 'js/directives/sensors/sensors.html',
        replace: true,
        scope: true,
        controller: sensorsController,
        link: sensorsLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('sensorsConfigDirective', ['$q', 'growl', 'blockUI', 'objectsService', 'sensorsService', sensorsConfigDirective]);
