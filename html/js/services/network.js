/**
 * Network service
 * Handle network module requests
 */
var networkService = function($q, $rootScope, rpcService, raspiotService) {
    var self = this;

    self.saveWiredStaticConfiguration = function(interface, ipAddress, gateway, netmask, fallback) {
        return rpcService.sendCommand('save_wired_static_configuration', 'network', {'interface':interface, 'ip_address':ipAddress, 'gateway':gateway, 'netmask':netmask, 'fallback':fallback});
    };

    self.saveWiredDhcpConfiguration = function(interface) {
        return rpcService.sendCommand('save_wired_dhcp_configuration', 'network', {'interface':interface});
    };

    self.getInterfacesConfigurations = function() {
        return rpcService.sendCommand('get_interfaces_configurations', 'network');
    };

    /*self.testWifiNetwork = function(network, password, encryption, hidden) {
        return rpcService.sendCommand('test_wifi_network', 'network', {'network':network, 'encryption':encryption, 'password':password, 'hidden':hidden}, 30);
    };*/

    self.saveWifiNetwork = function(network, password, encryption, hidden) {
        return rpcService.sendCommand('save_wifi_network', 'network', {'network':network, 'encryption':encryption, 'password':password, 'hidden':hidden}, 20)
            .then(function() {
                return self.refreshWifiNetworks();
            });
    };

    self.deleteWifiNetwork = function(network) {
        return rpcService.sendCommand('delete_wifi_network', 'network', {'network':network})
            .then(function() {
                return self.refreshWifiNetworks();
            });
    };

    self.enableWifiNetwork = function(interface, network) {
        return rpcService.sendCommand('enable_wifi_network', 'network', {'network':network})
            .then(function(resp) {
                return raspiotService.getModuleConfig('network')
            })
            .then(function(config) {
                //update disabled flag
                config.wifinetworks[interface][network].disabled = false;
            });
    };

    self.disableWifiNetwork = function(interface, network) {
        return rpcService.sendCommand('disable_wifi_network', 'network', {'network':network})
            .then(function(resp) {
                return raspiotService.getModuleConfig('network')
            })
            .then(function(config) {
                //update disabled flag
                config.wifinetworks[interface][network].disabled = true;
            });
    };

    self.updateWifiNetworkPassword = function(network, password) {
        return rpcService.sendCommand('update_wifi_network_password', 'network', {'network':network, 'password':password});
    };

    self.reconfigureWifiNetwork = function(interface) {
        return rpcService.sendCommand('reconfigure_interface', 'network', {'interface':interface}, 30);
    };

    self.refreshWifiNetworks = function() {
        var wifiNetworks = null;
        return rpcService.sendCommand('refresh_wifi_networks', 'network', null, 30)
            .then(function(resp) {
                //reload module config
                return raspiotService.reloadModuleConfig('network')
            })
            .then(function(config) {
                return config;
            });
    };
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('networkService', ['$q', '$rootScope', 'rpcService', 'raspiotService', networkService]);

