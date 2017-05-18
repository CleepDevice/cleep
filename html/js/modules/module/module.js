/**
 * Configuration directive
 * Handle all module configuration
 */
var moduleDirective = function($q, raspiotService, $compile, $timeout, $routeParams) {

    var moduleController = ['$scope','$element', function($scope, $element) {
        var self = this;
        self.module = '';

        /**
         * Init controller
         */
        self.init = function(module)
        {
            //save module name
            self.module = module;

            //inject module configuration directive
            var container = $element.find('#moduleContainer');
            var template = '<div ' + module + '-config-directive=""></div>';
            var directive = $compile(template)($scope);
            $element.append(directive);
        };
    }];

    var moduleLink = function(scope, element, attrs, controller) {
        controller.init($routeParams.name);
    };

    return {
        templateUrl: 'js/modules/module/module.html',
        replace: true,
        controller: moduleController,
        controllerAs: 'moduleCtl',
        link: moduleLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('moduleDirective', ['$q', 'raspiotService', '$compile', '$timeout', '$routeParams', moduleDirective]);

