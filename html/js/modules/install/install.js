/**
 * Configuration directive
 * Handle all modules configuration
 */
var installDirective = function($q, raspiotService, $compile) {

    var installController = ['$scope','$element', function($scope, $element) {
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
         * Init controller
         */
        self.init = function()
        {
            //flatten modules to array to allow sorting with ngrepeat
            var modules = [];
            for( var module in raspiotService.modules )
            {
                if( !raspiotService.modules[module].installed )
                {
                    //add module name as 'name' property
                    raspiotService.modules[module].name = module;
                    //push module to internal array
                    modules.push(raspiotService.modules[module]);
                }
            }

            //save modules list
            self.modules = modules;
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

    var installLink = function(scope, element, attrs, controller) {
        //see watchcollection above !
    };

    return {
        templateUrl: 'js/modules/install/install.html',
        replace: true,
        controller: installController,
        controllerAs: 'installCtl',
        link: installLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('installDirective', ['$q', 'raspiotService', '$compile', installDirective]);

