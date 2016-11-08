
var configurationDirective = function($q, growl, blockUI, objectsService, $compile) {

    var configurationController = ['$scope','$element', function($scope, $element) {
        $scope.services = objectsService.services;
        $scope.configs = objectsService.configs;

        /**
         * Init controller
         */
        function init() {
            //dynamically generate configuration panel according to load modules
            var active = 'in active';
            var container = $element.find('#configTabContent');
            for( var label in $scope.configs )
            {
                //prepare template to inject
                var template = '<div id="'+$scope.configs[label].cleanLabel+'Config" class="tab-pane fade '+active+'">';
                template += '    <div '+$scope.configs[label].directive.toDash()+'></div>';
                template += '</div>';

                //compile directive
                var directive = $compile(template)($scope);

                //append directive to DOM
                container.append(directive);

                //disable active tab on next tab (only first tab)
                active = '';
            }
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
RaspIot.directive('configurationDirective', ['$q', 'growl', 'blockUI', 'objectsService', '$compile', configurationDirective]);
