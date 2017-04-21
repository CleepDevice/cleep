/**
 * Configuration directive
 * Handle all modules configuration
 */
var modulesDirective = function($q, raspiotService, $compile, $timeout) {

    var modulesController = ['$scope','$element', function($scope, $element) {
        var self = this;
        self.modules = [];
        self.search = '';

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
            //dummy name is used to always have this item at end of list
            //dummy description is used to find this item using search
            modules.push({
                name: 'zzzzz',
                description: 'install new module',
                installmodule: true
            });
            
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

