
var dummyConfigDirective = function(objectsService) {

    var dummyController = function() {
        var self = this;

        /**
         * Init controller
         */
        self.init = function() {
        };

        //init directive
        init();
    }];

    var dummyLink = function(scope, element, attrs, controller) {
        controller.init();
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
RaspIot.directive('dummyConfigDirective', ['objectsService', dummyConfigDirective]);
