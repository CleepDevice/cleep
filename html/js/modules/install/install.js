/**
 * Configuration directive
 * Handle all modules configuration
 */
var installDirective = function($q, raspiotService, systemService, toast) {

    var installController = ['$scope','$element', function($scope, $element) {
        var self = this;
        self.modules = raspiotService.modules;
        self.search = '';

        /**
         * Clear search input
         */
        self.clearSearch = function()
        {
            self.search = '';
        };

        /**
         * Install module
         * @param module: module name (string)
         */
        self.install = function(module)
        {
            systemService.installModule(module)
                .then(function(resp) {
                    //reload system config to activate restart flag (see main controller)
                    return raspiotService.reloadModuleConfig('system');
                })
                .then(function(config) {
                    self.updateModulePendingStatus(module);
                    toast.success('Module ' + module + ' will be installed after next restart.' );
                });
        };

        /**
         * Uninstall module
         */
        self.uninstall = function(module)
        {
            systemService.uninstallModule(module)
                .then(function(resp) {
                    //reload system config
                    return raspiotService.reloadModuleConfig('system');
                })
                .then(function(config) {
                    toast.success('Module ' + module + ' is uninstalled. Please restart raspiot' );
                });
        };

        /**
         * Update pending module status after install
         * Everything will be reloaded automatically after page reloading
         * @param module: module name
         */
        self.updateModulePendingStatus = function(module)
        {
            //update pending status in local modules
            for( var i=0; i<self.modules.length; i++ )
            {
                if( self.modules[i].name===module )
                {
                    self.modules[i].pending = true;
                }
            }
            
            //update pending status in raspiotService
            raspiotService.modules[module].pending = true;
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
RaspIot.directive('installDirective', ['$q', 'raspiotService', 'systemService', 'toastService', installDirective]);

