/**
 * Configuration directive
 * Handle all modules configuration
 */
var modulesDirective = function($rootScope, raspiotService, $window, toast, confirm) {

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
                    self.updateModuleProcessingStatus(module, true);
                    return raspiotService.uninstallModule(module);
                });
        };

        /**
         * Update module
         */
        self.update = function(module)
        {
            self.updateModuleProcessingStatus(module, true);
            raspiotService.updateModule(module);
        };

        /** 
         * Update pending module status after install
         * Everything will be reloaded automatically after page reloading
         * @param module (string): module name
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
         * Module is processing (uninstall, update)
         * @param module (string): module name
         * @param processing (bool): processing value
         */
        self.updateModuleProcessingStatus = function(module, processing)
        {
            //update pending status in local modules
            for( var i=0; i<self.modules.length; i++ )
            {   
                if( self.modules[i].name===module )
                {   
                    self.modules[i].processing = processing;
                }
            }

            //update pending status in raspiotService
            raspiotService.modules[module].processing = processing;
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

        /** 
         * Handle module uninstall event
         */
        $rootScope.$on('system.module.uninstall', function(event, uuid, params) {
            if( !params.status )
            {
                return;
            }

            if( params.status==2 )
            {
                self.updateModuleProcessingStatus(params.module, false);
                toast.error('Error during module ' + params.module + ' uninstallation');
            }
            else if( params.status==4 )
            {
                self.updateModuleProcessingStatus(params.module, false);
                toast.error('Module ' + params.module + ' uninstallation canceled');
            }
            else if( params.status==3 )
            {
                //reload system config to activate restart flag (see main controller)
                raspiotService.reloadModuleConfig('system')
                    .then(function() {
                        //force pending status of uninstalled module. This avoid reloading complete config
                        self.updateModuleProcessingStatus(params.module, false);
                        self.updateModulePendingStatus(params.module);

                        //info message
                        toast.success('Module ' + params.module + ' is uninstalled. Please restart raspiot' );
                    });
            }
        });

        /**
         * Handle module update event
         */
        $rootScope.$on('system.module.update', function(event, uuid, params) {
            if( !params.status )
            {
                return;
            }

            if( params.status==2 )
            {
                self.updateModuleProcessingStatus(params.module, false);
                toast.error('Error during module ' + params.module + ' update');
            }
            else if( params.status==4 )
            {
                self.updateModuleProcessingStatus(params.module, false);
                toast.error('Module ' + params.module + ' update canceled');
            }
            else if( params.status==3 )
            {
                //reload system config to activate restart flag (see main controller)
                raspiotService.reloadModuleConfig('system')
                    .then(function() {
                        //force pending status of updated module. This avoid reloading complete config
                        self.updateModuleProcessingStatus(params.module, false);
                        self.updateModulePendingStatus(params.module);

                        //info message
                        toast.success('Module ' + params.module + ' is updated. Please restart raspiot' );
                    });
            }
        });

    }];

    var modulesLink = function(scope, element, attrs, controller) {
        //see watchcollection above !
    };

    return {
        templateUrl: 'js/settings/modules/modules.html',
        replace: true,
        controller: modulesController,
        controllerAs: 'modulesCtl',
        link: modulesLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('modulesDirective', ['$rootScope', 'raspiotService', '$window', 'toastService', 'confirmService', modulesDirective]);

