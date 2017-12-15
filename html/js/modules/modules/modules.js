/**
 * Configuration directive
 * Handle all modules configuration
 */
var modulesDirective = function($rootScope, raspiotService, systemService, $window, toast, confirm) {

    var modulesController = ['$scope','$element', function($scope, $element) {
        var self = this;
        self.modules = [];
        self.search = '';

        /**
         * Clear search input
         */
        self.clearSearch = function()
        {
            self.search = '';
        };

        /**
         * Redirect to install module page
         */
        self.toInstallPage = function()
        {
            $window.location.href = '#!install';
        };

        /**
         * Uninstall module
         */
        self.uninstall = function(module)
        {
            confirm.open('Uninstall module?', 'Do you want to remove this module? Its config will be kept.', 'Uninstall', 'Cancel')
                .then(function() {
                    return systemService.uninstallModule(module);
                })
                .then(function(resp) {
                    //reload system config to activate restart flag (see main controller)
                    return raspiotService.reloadModuleConfig('system');
                })  
                .then(function(config) {
                    self.updateModulePendingStatus(module);
                    toast.success('Module ' + module + ' will be uninstalled after next restart.' );
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
                //keep only installed modules
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
                icon: 'plus',
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
RaspIot.directive('modulesDirective', ['$rootScope', 'raspiotService', 'systemService', '$window', 'toastService', 'confirmService', modulesDirective]);

