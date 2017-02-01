
var configurationDirective = function($q, objectsService, $compile, $timeout) {

    var configurationController = ['$scope','$element', function($scope, $element) {
        var self = this;
        self.services = objectsService.services;
        self.configs = [];
        self.configsCount = objectsService.configsCount;

        /**
         * Init controller
         */
        self.init = function() {
            //flatten configs to allow sorting
            angular.forEach(objectsService.configs, function(config, label) {
                config.__label = label;
                self.configs.push(config);
            });

            //wait for ng-repeat digest call
            $timeout(function() {
                //dynamically generate configuration panel according to loaded modules
                var container = $element.find('#configTabContent');
                angular.forEach(self.configs, function(config) {
                    //get container
                    var id = config.cleanLabel+'Config';
                    var container = $element.find('#'+id);

                    //prepare template to inject
                    var template = '<div '+config.directive.toDash()+'></div>';

                    //compile directive
                    var directive = $compile(template)($scope);

                    //append directive to container
                    container.append(directive);
                });
            });
        }
    }];

    var configurationLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'js/directives/configuration/configuration.html',
        replace: true,
        //scope: false,
        controller: configurationController,
        controllerAs: 'configCtl',
        link: configurationLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('configurationDirective', ['$q', 'objectsService', '$compile', '$timeout', configurationDirective]);
