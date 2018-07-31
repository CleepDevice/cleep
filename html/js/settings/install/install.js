/**
 * Configuration directive
 * Handle all modules configuration
 */
var installDirective = function($q, raspiotService, toast) {

    var installController = ['$rootScope', '$scope','$element', function($rootScope, $scope, $element) {
        var self = this;
        self.modules = raspiotService.modules;
        self.search = '';
        self.country = null;
        self.country_alpha = null;

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
            //lock button
            self.updateModuleInstallingStatus(module, true);

            //trigger install
            raspiotService.installModule(module);
        };

        /**
         * Uninstall module
         */
        self.uninstall = function(module)
        {
            raspiotService.uninstallModule(module)
                .then(function(resp) {
                    //reload system config
                    return raspiotService.reloadModuleConfig('system');
                })
                .then(function(config) {
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
         * Update installing module status
         * @param module (string): module name
         * @param installing (bool): installing value
         */
        self.updateModuleInstallingStatus = function(module, installing)
        {
            //update pending status in local modules
            for( var i=0; i<self.modules.length; i++ )
            {
                if( self.modules[i].name===module )
                {
                    self.modules[i].installing = installing;
                }
            }
            
            //update pending status in raspiotService
            raspiotService.modules[module].installing = installing;
        };

        /**
         * Init controller
         */
        self.init = function()
        {
            //get configured user country
            if( raspiotService.modules.system && raspiotService.modules.system.config && raspiotService.modules.system.config.city )
            {
                self.country = raspiotService.modules.system.config.city.country;
                self.country_alpha = raspiotService.modules.system.config.city.alpha2;
            }

            //flatten modules to array to allow sorting with ngrepeat
            var modules = [];
            for( var module in raspiotService.modules )
            {
                //filter not installed modules and modules for user configured country
                var country_alpha = raspiotService.modules[module].country;
                if( country_alpha===null || country_alpha===undefined )
                {
                    country_alpha = "";
                }
                if( !raspiotService.modules[module].installed && (country_alpha.length===0 || country_alpha==self.country_alpha))
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

        /**
         * Handle module install event
         */
        $rootScope.$on('system.module.install', function(event, uuid, params) {
            //drop useless status
            if( !params.status )
            {
                return;
            }

            //drop module install triggered by module update
            if( params.updateprocess===true )
            {
                return;
            }
            
            if( params.status===1 )
            {
                //installing status
            }
            if( params.status===2 )
            { 
                toast.error('Error during module ' + params.module + ' installation');
                self.updateModuleInstallingStatus(params.module, false);
            }
            else if( params.status===4 )
            {
                toast.error('Module ' + params.module + ' installation canceled');
                self.updateModuleInstallingStatus(params.module, false);
            }
            else if( params.status===3 )
            {
                //reload system config to activate restart flag (see main controller)
                raspiotService.reloadModuleConfig('system')
                    .then(function() {
                        //set module pending status
                        self.updateModuleInstallingStatus(params.module, false);
                        self.updateModulePendingStatus(params.module);

                        //info message
                        toast.success('Module ' + params.module + ' installation will be finalized after next restart.');
                    });
            }
        });

    }];

    var installLink = function(scope, element, attrs, controller) {
        //see watchcollection above !
    };

    return {
        templateUrl: 'js/settings/install/install.html',
        replace: true,
        controller: installController,
        controllerAs: 'installCtl',
        link: installLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('installDirective', ['$q', 'raspiotService', 'toastService', installDirective]);

