
var schedulerDirective = function($q, growl, blockUI, schedulerService) {
    var container = null;

    var schedulerController = ['$scope', function($scope) {
        $scope.sunset = null;
        $scope.sunrise = null;
        $scope.city = null;

        /**
         * Init controller
         */
        function init() {
            getSun();
            getCity();
        };

        /**
         * Get configured sunset and sunrise
         */
        function getSun()
        {
            schedulerService.getSun()
            .then(function(res) {
                $scope.sunset = moment.unix(res.sunset).format('HH:mm');
                $scope.sunrise = moment.unix(res.sunrise).format('HH:mm');
            });
        };

        /**
         * Get configured city
         */
        function getCity()
        {
            schedulerService.getCity()
            .then(function(res) {
                $scope.city = res;
            });
        }

        /**
         * Set city
         */
        $scope.setCity = function()
        {
            container.start();
            schedulerService.setCity($scope.city)
            .then(function(res) {
                $scope.sunset = moment.unix(res.sunset).format('HH:mm');
                $scope.sunrise = moment.unix(res.sunrise).format('HH:mm');
            })
            .finally(function() {
                container.stop();
            });
        };

        //init directive
        init();
    }];

    var schedulerLink = function(scope, element, attrs) {
        container = blockUI.instances.get('schedulerContainer');
        container.reset();
    };

    return {
        templateUrl: 'js/directives/scheduler/scheduler.html',
        replace: true,
        scope: true,
        controller: schedulerController,
        link: schedulerLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('schedulerDirective', ['$q', 'growl', 'blockUI', 'schedulerService', schedulerDirective]);
