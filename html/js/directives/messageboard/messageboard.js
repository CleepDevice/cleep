
var messageboardDirective = function($q, growl, blockUI, messageboardService) {
    var container = null;

    var messageboardController = ['$scope', function($scope) {
        $scope.message = '';
        $scope.start = 0;
        $scope.end = 0;
        $scope.scroll = false;

        /**
         * Init controller
         */
        function init() {
        }

        $scope.addMessage = function(device) {
            container.start();
            messageboardService.addMessage($scope.message, $scope.start, $scope.end, $scope.scroll)
                .then(function(resp) {
                    //reload messages
                })
                .finally(function() {
                    container.stop();
                });
        };

        //init directive
        init();
    }];

    var messageboardLink = function(scope, element, attrs) {
        container = blockUI.instances.get('messageboardContainer');
        container.reset();
    };

    return {
        templateUrl: 'js/directives/messageboard/messageboard.html',
        replace: true,
        scope: true,
        controller: messageboardController,
        link: messageboardLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('messageboardConfigDirective', ['$q', 'growl', 'blockUI', 'messageboardService', messageboardDirective]);
