
var configurationDirective = function($q, growl, blockUI, objectsService, $compile, $timeout) {

    var configurationController = ['$scope','$element', function($scope, $element) {
        $scope.services = objectsService.services;
        $scope.configs = objectsService.configs;
        $scope.configsCount = objectsService.configsCount;

        $scope.newInit = function() {
            var el = $element.find('#sensorsconfig');
            console.log('new init', el.length);
        };

        /**
         * Init controller
         */
        function init() {
            //wait for ng-repeat digest call
            $timeout(function() {
                //dynamically generate configuration panel according to load modules
                var container = $element.find('#configTabContent');
                for( var label in $scope.configs )
                {
                    //get container
                    var id = $scope.configs[label].cleanLabel+'Config';
                    var container = $element.find('#'+id);

                    //prepare template to inject
                    var template = '<div '+$scope.configs[label].directive.toDash()+'></div>';

                    //compile directive
                    var directive = $compile(template)($scope);

                    //append directive to container
                    container.append(directive);
                }
            });
        }

        //init directive
        init();
    }];

    return {
        templateUrl: 'js/directives/configuration/configuration.html',
        replace: true,
        scope: true,
        controller: configurationController
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('configurationDirective', ['$q', 'growl', 'blockUI', 'objectsService', '$compile', '$timeout', configurationDirective]);
