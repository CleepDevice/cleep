/**
 * Configuration directive
 * Handle all modules configuration
 */
var configurationDirective = function($q, objectsService, $compile, $timeout) {

    var configurationController = ['$scope','$element', function($scope, $element) {
        var self = this;
        self.directives = objectsService.moduleDirectives;

        /**
         * Init controller
         */
        self.init = function()
        {
            //debugger;
            //save directives
            //self.directives = raspiotService.directives;

            //wait for ng-repeat digest call
            $timeout(function() {
                //dynamically generate configuration panel according to loaded modules
                var container = $element.find('#configTabContent');
                //angular.forEach(self.directives, function(item) {
                for( module in self.directives )
                {
                    //get container
                    //var id = item.cleanLabel+'Config';
                    var id = self.directives[module].cleanLabel + 'Config';
                    var container = $element.find('#'+id);

                    //prepare template to inject
                    //var template = '<div '+item.directive.toDash()+'></div>';
                    var template = '<div ' + self.directives[module].directive.toDash() + '></div>';

                    //compile directive
                    var directive = $compile(template)($scope);

                    //append directive to container
                    container.append(directive);
                };
            });
        };

        //refresh module directives as soon as modules are loaded (see mainController)
        $scope.$watchCollection(
            function() {
                return objectsService.moduleDirectives;
            },
            function(newValue, oldValue) {
                self.init();
            }
        );
    }];

    var configurationLink = function(scope, element, attrs, controller) {
        //see watchcollection above !
        //controller.init();
    };

    return {
        templateUrl: 'js/configuration/configuration/configuration.html',
        replace: true,
        controller: configurationController,
        controllerAs: 'configCtl',
        link: configurationLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('configurationDirective', ['$q', 'objectsService', '$compile', '$timeout', configurationDirective]);

