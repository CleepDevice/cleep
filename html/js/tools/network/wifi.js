var wifiDirective = function(networkService, toast, raspiotService) {

    var wifiController = ['$scope', function($scope) {
        var self = this;
        self.loaded = false;
        self.wifis = [];
        self.wifi = null;
        self.showPassword = false;
        self.password = '';
        self.hidden = false;
        self.network = '';
        self.networkType = 'wpa2';
        self.interfaces = [];
        self.interface = '';
        self.testing = false;
        self.scanning = false;
        self.saving = false;

        /**
         * Load config
         */
        self.__loadConfig = function(config)
        {
            //fill wifi interfaces first to flag connected wifi network after
            self.__fillInterfaces(config.interfaces);

            //fill wifi networks
            self.__fillWifis(config.wifi_networks);
        };

        /**
         * Fill wifi networks list
         */
        self.__fillWifis = function(wifis)
        {
            var wifis_ = [];
            for( name in wifis )
            {
                //is interface connected to this wifi network?
                var connected = false;
                for( var i=0; i<self.interfaces.length; i++ )
                {
                    if( self.interfaces[i].wifi_network==name )
                    {
                        connected = true;
                        break;
                    }
                }
                wifis[name].connected = connected;
                wifis_.push(wifis[name]);
            }
            self.wifis = wifis_;

            if( wifis_.length>0 )
            {
                self.wifi = self.wifis[0];
            }
        };

        /**
         * Fill wifi interfaces list
         */
        self.__fillInterfaces = function(interfaces)
        {
            var interfaces_ = [];
            for( name in interfaces )
            {
                if( interfaces[name].wifi )
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
         * Scan wifi networks
         */
        self.scanWifiNetworks = function()
        {
            self.password = '';
            self.scanning = true;
            networkService.scanWifiNetworks()
                .then(function(resp) {
                    if( resp.data.length===0 )
                    {
                        toast.warning('No wifi network found');
                    }
                    else
                    {
                        self.__fillWifis(resp.data);
                    }
                })
                .finally(function() {
                    self.scanning = false;
                });
        };

        /**
         * Hide password input
         */
        self.disablePassword = function()
        {
            if( !self.loaded || self.scanning || self.testing || self.saving ) 
            {
                return true;
            }
            else if( self.wifi && self.wifi.network_type==='unsecured' )
            {
                return true;
            }
            else if( self.wifi && self.wifi.connected )
            {
                return true;
            }
            else if( self.hidden && self.networkType==='unsecured' )
            {
                return true;
            }
            return false;
        };

        self.disableDisconnectButton = function()
        {
            if( !self.loaded || self.scanning || self.testing || self.saving )
            {
                return true;
            }
            else if( self.wifi && !self.wifi.connected )
            {
                return true;
            }
            return false;
        };

        /**
         * Disable action buttons
         */
        self.disableButtons = function()
        {
            if( !self.loaded || self.scanning || self.testing || self.saving )
            {
                return true;
            }
            else if( self.interfaces.length===0 )
            {
                return true;
            }
            else if( !self.hidden && !self.wifi )
            {
                return true;
            }
            else if( !self.hidden && self.wifi && self.wifi.network_type!=='unsecured' && self.password.length==0 )
            {
                return true;
            }
            else if( self.hidden && self.network.length===0 )
            {
                return true;
            }
            else if( self.hidden && self.networkType!=='unsecured' && self.password.length===0 )
            {
                return true;
            }
            return false;
        };

        /**
         * Get connection parameter according to user configuration
         */
        self.__getConnectionParameters = function()
        {
            var output = {
                interface: self.interface,
                network: self.network,
                networkType: self.networkType,
                password: self.password,
                hidden: self.hidden
            };

            if( !self.hidden )
            {
                output.interface = self.wifi.interface;
                output.network = self.wifi.network;
                output.networkType = self.wifi.network_type;
            }

            return output;
        };

        /**
         * Try to connect to selected wifi network
         */
        self.testConnection = function()
        {
            self.testing = true;
            var params = self.__getConnectionParameters();

            //execute test
            networkService.testWifiNetwork(params.interface, params.network, params.networkType, params.password, params.hidden)
                .finally(function() {
                    self.testing = false;
                });
        };

        /**
         * Disconnect specified network
         */
        self.disconnect = function()
        {
            self.saving = true;
            networkService.disconnectWifi(self.wifi.network)
                .then(function() {
                    //reload network config
                    return raspiotService.reloadModuleConfig('network');
                })
                .then(function(config) {
                    self.__loadConfig(config);
                })
                .finally(function() {
                    self.saving = false;
                });

        };

        /**
         * Save connection configuration
         */
        self.saveConnection = function()
        {
            self.saving = true;
            var params = self.__getConnectionParameters();

            //execute test
            networkService.saveWifiNetwork(params.interface, params.network, params.networkType, params.password, params.hidden)
                .then(function() {
                    //reload network config
                    return raspiotService.reloadModuleConfig('network');
                })
                .then(function(config) {
                    self.__loadConfig(config);
                })
                .finally(function() {
                    self.saving = false;
                });
        };

        /**
         * Get wifi interfaces
         */
        /*self.getWifiInterfaces = function()
        {
            networkService.getInterfacesConfigurations()
                .then(function(resp) {
                    //store wifi interfaces
                    for( interface in resp.data )
                    {
                        if( resp.data[interface].wifi )
                        {
                            self.interfaces.push(interface);
                        }
                    }
                    //by default select first wifi interface (used for hidden network)
                    if( self.interfaces.length>0 )
                    {
                        self.interface = self.interfaces[0];
                    }
                    //loaded flag
                    self.loaded = true;
                });
        };*/

        /**
         * Controller init
         */
        self.init = function()
        {
            raspiotService.getModuleConfig('network')
                .then(function(config) {
                    self.__loadConfig(config);
                    self.loaded = true;
                });
        };

    }];

    var wifiLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        restrict: 'AE',
        templateUrl: 'js/tools/network/wifi.html',
        replace: true,
        controller: wifiController,
        controllerAs: 'wifiCtl',
        link: wifiLink
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.directive('wifiConfig', ['networkService', 'toastService', 'raspiotService', wifiDirective]);

