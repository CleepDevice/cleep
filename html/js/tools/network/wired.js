var wiredDirective = function(raspiotService, networkService, toast, confirm) {

    var wiredController = ['$scope', function($scope) {
        var self = this;
        self.interfaces = [];
        self.saving = false;

        /**
         * Load configuration
         */
        self.__loadConfig = function(config)
        {
            //fill available wired interfaces
            self.__fillInterfaces(config.interfaces);

            //fill current configuration
            if( !config.wired_config.dhcp )
            {
                if( !config.wired_config.dhcp )
                {
                    self.type = 'static';
                }
                else
                {
                    self.type = 'auto';
                }

                self.__fillConfigurations(config.wired_config.interfaces);
            }
        };

        /**
         * Fill interfaces
         */
        self.__fillInterfaces = function(interfaces)
        {
            var interfaces_ = [];
            for( name in interfaces )
            {
                if( !interfaces[name].wifi )
                {
                    interfaces_.push(interfaces[name]);
                }
            }
            self.interfaces = interfaces_;

            if( interfaces_.length>0 )
            {
                self.interface = self.interfaces[0];
            } 
        };

        /**
         * Fill configured static interfaces
         */
        self.__fillConfigurations = function(configs)
        {
            for( var config in configs )
            {
                //check if configured interface is among available ones
                found = false;
                for( var i=0; i<self.interfaces.length; i++ )
                {
                    if( self.interfaces[i].interface===config )
                    {
                        found = true;
                        break;
                    }
                }

                //keep only first configured interface for now
                if( found ) 
                {
                    self.ipAddress = configs[config].ip_address;
                    self.routerAddress = configs[config].router_address;
                    self.nameServer = configs[config].name_server;
                }
            }
        };

        /**
         * Save static configuration
         */
        self.saveStatic = function(interface)
        {
            self.saving = true;
            confirm.open('Confirmation', 'Forcing ip manually can break your remote access. Please make sure of what you do!', 'Save')
                .then(function() {
                    return networkService.saveWiredStaticConfiguration(interface.interface, interface.ip_address, interface.router_address, interface.name_server, interface.fallback);
                })
                .then(function() {
                    return raspiotService.reloadModuleConfig('network');
                })
                .then(function(config) {
                    self.__loadConfig(config);
                    toast.success('Configuration saved');
                })
                .finally(function() {
                    self.saving = false;
                });
        };

        /**
         * Save dhcp configuration
         */
        self.saveAuto = function(interface)
        {
            self.saving = true;
            networkService.saveWiredDhcpConfiguration(interface.interface)
                .then(function() {
                    return raspiotService.reloadModuleConfig('network');
                })
                .then(function(config) {
                    self.__loadConfig(config);
                    toast.success('Configuration saved');
                })
                .finally(function() {
                    self.saving = false;
                });
        };

        /**
         * Save action
         */
        self.save = function(interface)
        {
            if( interface.dhcp )
            {
                self.saveAuto(interface);
            }
            else
            {
                self.saveStatic(interface);
            }
        };

        /**
         * Controller init
         */
        self.init = function()
        {
            raspiotService.getModuleConfig('network')
                .then(function(config) {
                    self.__loadConfig(config);
                });
        };

    }];

    var wiredLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        restrict: 'AE',
        templateUrl: 'js/tools/network/wired.html',
        replace: true,
        controller: wiredController,
        controllerAs: 'wiredCtl',
        link: wiredLink
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.directive('wiredConfig', ['raspiotService', 'networkService', 'toastService', 'confirmService', wiredDirective]);

