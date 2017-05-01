var wiredDirective = function(networkService, toast) {

    var wiredController = ['$scope', function($scope) {
        var self = this;
        self.loaded = false;
        self.wifis = [];
        self.wifi = null;
        self.showPassword = false;
        self.password = '';
        self.hidden = false;
        self.network = '';
        self.networkType = 'wpa2';
        self.wifiInterfaces = [];
        self.interface = '';
        self.testing = false;
        self.scanning = false;

        /**
         * Scan wifi networks
         */
        self.scanWifiNetworks = function()
        {
            self.password = '';
            self.scanning = true;
            networkService.scanWifiNetworks()
                .then(function(resp) {
                    wifis = []
                    for( network in resp['data'] )
                    {
                        wifis.push(resp['data'][network]);
                    }

                    if( wifis.length>0 )
                    {
                        self.wifis = wifis;
                        self.wifi = self.wifis[0];
                    }
                    else
                    {
                        toast.warning('No wifi network found');
                    }
                })
                .finally(function() {
                    self.scanning = false;
                });
        };

        /**
         * Disable action buttons
         */
        self.disableButtons = function()
        {
            if( self.scanning || self.testing )
            {
                return true;
            }
            else if( self.wifiInterfaces.length===0 )
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
        self.__getConnectionParameter = function()
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
         * Save connection configuration
         */
        self.saveConnection = function()
        {
            self.saving = true;
            var params = self.__getConnectionParameters();

            //execute test
            networkService.saveWifiNetwork(params.interface, params.network, params.networkType, params.password, params.hidden)
                .finally(function() {
                    self.saving = false;
                });
        };

        /**
         * Get wifi interfaces
         */
        self.getWifiInterfaces = function()
        {
            networkService.getInterfacesConfigurations()
                .then(function(resp) {
                    //store wifi interfaces
                    for( interface in resp.data )
                    {
                        if( resp.data[interface].wired )
                        {
                            self.wifiInterfaces.push(interface);
                        }
                    }
                    //by default select first wifi interface (used for hidden network)
                    if( self.wifiInterfaces.length>0 )
                    {
                        self.interface = self.wifiInterfaces[0];
                    }
                    //loaded flag
                    self.loaded = true;
                });
        };

        /**
         * Controller init
         */
        self.init = function()
        {
            self.getWifiInterfaces();
        };

    }];

    var wifiLink = function(scope, element, attrs, controller) {
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
RaspIot.directive('wiredConfig', ['networkService', 'toastService', wiredDirective]);

