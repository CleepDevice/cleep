/**
 * Wifi directive adds panel to configure wifi network
 *
 * Usage: <div wifi-config></div>
 * No parameter needed. The directive gets all it needs from raspiotService
 */
var wifiDirective = function(networkService, toast, raspiotService, confirm) {

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
        self.processing = false;

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
            self.processing = true;
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
                    self.processing = false;
                });
        };

        /**
         * Hide password input
         */
        self.disablePassword = function()
        {
            if( !self.loaded || self.processing ) 
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
            if( !self.loaded || self.processing )
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
            if( !self.loaded || self.processing )
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
            self.processing = true;
            var params = self.__getConnectionParameters();

            //execute test
            networkService.testWifiNetwork(params.interface, params.network, params.networkType, params.password, params.hidden)
                .finally(function() {
                    self.processing = false;
                });
        };

        /**
         * Disconnect specified network
         */
        self.disconnect = function()
        {
            self.processing = true;
            confirm.open('Confirm disconnection?', null, 'Disconnect')
                .then(function() {
                    return networkService.disconnectWifi(self.wifi.network);
                })
                .then(function() {
                    //reload network config
                    return raspiotService.reloadModuleConfig('network');
                })
                .then(function(config) {
                    self.__loadConfig(config);
                })
                .finally(function() {
                    self.processing = false;
                });

        };

        /**
         * Save connection configuration
         */
        self.saveConnection = function()
        {
            self.processing = true;
            var params = self.__getConnectionParameters();

            //execute test
            networkService.saveWifiNetwork(params.interface, params.network, params.networkType, params.password, params.hidden)
                .then(function() {
                    //reload network config
                    return raspiotService.reloadModuleConfig('network');
                })
                .then(function(config) {
                    self.__loadConfig(config);
                    //force connected flag because ip takes some time to be retrieved
                    self.wifi.connected = true;
                    //clear password
                    self.password = '';
                })
                .finally(function() {
                    self.processing = false;
                });
        };

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
RaspIot.directive('wifiConfig', ['networkService', 'toastService', 'raspiotService', 'confirmService', wifiDirective]);

