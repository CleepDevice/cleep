/**
 * Configuration directive
 * Handle all modules configuration
 */
var modulesDirective = function($q, raspiotService, $compile, $timeout) {

    var modulesController = ['$scope','$element', function($scope, $element) {
        var self = this;
        self.modules = [];
        self.search = '';

        /**
         * Init controller
         */
        /*self.init = function()
        {
            //wait for ng-repeat digest call
            $timeout(function() {
                //dynamically generate configuration panel according to loaded modules
                for( var module in self.directives )
                {
                    //get container
                    var id = self.directives[module].cleanLabel + 'Config';
                    var container = $element.find('#'+id);

                    //prepare template to inject
                    var template = '<div ' + self.directives[module].directive.toDash() + '></div>';

                    //compile directive
                    var directive = $compile(template)($scope);

                    //append directive to container
                    container.append(directive);
                }
            });
        };*/

        self.init = function()
        {
            //flatten modules to array to allow sorting with ngrepeat
            var modules = [];
            for( var module in raspiotService.modules )
            {
                //add module name as 'name' property
                raspiotService.modules[module].name = module;
                //push module to internal array
                modules.push(raspiotService.modules[module]);
            }

            //add dummy module to add new "install module" card in dashboard
            
            //save modules list
            self.modules = modules;
        };

        //refresh module directives as soon as modules are loaded (see mainController)
        $scope.$watchCollection(
            function() {
                return raspiotService.modules;
            },
            function(newValue, oldValue) {
                self.init();
            }
        );
    }];

    var modulesLink = function(scope, element, attrs, controller) {
        //see watchcollection above !
    };

    return {
        templateUrl: 'js/modules/modules/modules.html',
        replace: true,
        controller: modulesController,
        controllerAs: 'modulesCtl',
        link: modulesLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('modulesDirective', ['$q', 'raspiotService', '$compile', '$timeout', modulesDirective]);

