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
        self.showPassword = false;
        self.interfaces = [];
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
            var wifis_ = []

            //fill wifis list and add useful properties
            for( name in wifis )
            {
                wifis[name].sort = name;
                wifis[name].dummy = false;
                wifis[name].label = wifis[name].network+' ('+wifis[name].encryption+', '+wifis[name].signal_level+'% signal)';
                wifis_.push(wifis[name]);
            }

            //add dummy option to add hidden network
            wifis_.push({
                label: 'Connect to hidden network',
                sort: 'ZZZZZZZZZZ999',
                network: 'hidden',
                dummy: true
            });

            //add dummy option to add hidden network
            wifis_.push({
                label: 'Not connected',
                sort: '_______000',
                network: 'notconnected',
                dummy: true
            });

            self.wifis = wifis_;
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
                    interfaces[name].wifi_new_network = interfaces[name].wifi_network;
                    interfaces[name].wifi_hidden_encryption = 'WPA2';
                    interfaces[name].wifi_hidden_network = '';
                    interfaces[name].password = null;
                    if( interfaces[name].wifi_network===null )
                    {
                        interfaces[name].wifi_network = 'notconnected';
                        interfaces[name].wifi_new_network = 'notconnected';
                    }
                    interfaces_.push(interfaces[name]);
                }
            }
            self.interfaces = interfaces_;
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
         * Show disconnect button
         * @param interface: interface object
         */
        self.disablePasswordInput = function(interface)
        {
            if( self.processing )
            {
                return true;
            }
            else if( interface.wifi_new_network==='notconnected' )
            {
                return true;
            }
            else if( interface.wifi_new_network==='hidden' && interface.wifi_hidden_encryption==='unsecured' )
            {
                return true;
            }
            else if( interface.wifi_new_network===interface.wifi_network )
            {
                return true;
            }
            else
            {
                for( var i=0; i<self.wifis.length; i++ )
                {
                    if( self.wifis[i].network===interface.wifi_new_network )
                    {
                        if( self.wifis[i].encryption==='unsecured' )
                        {
                            return true;
                        }
                        else
                        {
                            break;
                        }
                    }
                }
            }
            return false;
        };

        /**
         * Show disconnect button
         * @param interface: interface object
         */
        self.showDisconnectButton = function(interface)
        {
            if( interface.wifi_network===interface.wifi_new_network )
            {
                return true;
            }
            return false;
        };

        /**
         * Disable disconnect button
         * @param interface: interface object
         */
        self.disableDisconnectButton = function(interface)
        {
            if( self.processing )
            {
                return true;
            }
            else if( interface.wifi_new_network==='notconnected' || interface.wifi_network!==interface.wifi_new_network )
            {
                return true;
            }
            return false;
        };

        /**
         * Disable connect button
         * @param interface: interface object
         */
        self.disableConnectButton = function(interface)
        {
            if( self.processing )
            {
                return true;
            }
            else if( interface.wifi_new_network==='notconnected' || interface.wifi_network===interface.wifi_new_network )
            {
                return true;
            }
            return false;
        };

        /**
         * Disconnect specified network
         */
        self.disconnect = function(interface)
        {
            self.processing = true;
            self.showPassword = false;
            confirm.open('Confirm disconnection?', null, 'Disconnect')
                .then(function() {
                    return networkService.disconnectWifi(interface.wifi_network);
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
        self.saveConnection = function(interface)
        {
            self.processing = true;
            self.showPassword = false;

            //get parameters
            var network = null;
            var encryption = null;
            var hidden = false;
            if( interface.wifi_new_network==='hidden' )
            {
                //get parameters from interface fields
                hidden = true;
                network = interface.wifi_hidden_network;
                encryption = interface.wifi_hidden_encryption;
            }
            else
            {
                //get parameters from selected network
                hidden = false;
                network = interface.wifi_new_network;
                for( var i=0; i<self.wifis.length; i++ )
                {
                    if( self.wifis[i].network===network )
                    {
                        encryption = self.wifis[i].encryption;
                    }
                }
            }

            //execute test
            networkService.saveWifiNetwork(interface.interface, network, encryption, interface.password, hidden)
                .then(function() {
                    //reload network config
                    return raspiotService.reloadModuleConfig('network');
                })
                .then(function(config) {
                    self.__loadConfig(config);
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

