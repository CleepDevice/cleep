
var dummyDirective = function($q, growl, blockUI) {
    var container = null;

    var dummyController = ['$scope', function($scope) {
        /**
         * Init controller
         */
        function init() {
        }

        //init directive
        init();
    }];

    var dummyLink = function(scope, element, attrs) {
        container = blockUI.instances.get('dummyContainer');
        container.reset();
    };

    return {
        templateUrl: 'js/directives/dummy/dummy.html',
        replace: true,
        scope: true,
        controller: dummyController,
        link: dummyLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('dummyDirective', ['$q', 'growl', 'blockUI', dummyDirective]);
