/**
 * Configuration directive
 * Handle all modules configuration
 */
var modulesDirective = function($rootScope, raspiotService, $compile, $timeout, $window) {

    var modulesController = ['$scope','$element', function($scope, $element) {
        var self = this;
        self.modules = [];
        self.search = '';

        /**
         * Clear search input
         */
        self.clearSearch = function() {
            self.search = '';
        };

        /**
         * Redirect to install module page
         */
        self.toInstallPage = function() {
            $window.location.href = '#!install';
        };

        /**
         * Init controller
         */
        self.init = function()
        {
            //flatten modules to array to allow sorting with ngrepeat
            var modules = [];
            for( var module in raspiotService.modules )
            {
                if( raspiotService.modules[module].installed )
                {
                    //add module name as 'name' property
                    raspiotService.modules[module].name = module;
                    //push module to internal array
                    modules.push(raspiotService.modules[module]);
                }
            }

            //save modules list
            self.modules = modules;

            //add fab action
            action = [{
                callback: self.toInstallPage,
                icon: 'add_circle_outline',
                aria: 'Install module',
                tooltip: 'Install module'
            }];
            $rootScope.$broadcast('enableFab', action);
        };

        /**
         * Init controller as soon as modules configuration are loaded
         */
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
RaspIot.directive('modulesDirective', ['$rootScope', 'raspiotService', '$compile', '$timeout', '$window', modulesDirective]);

