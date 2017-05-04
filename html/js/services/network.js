/**
 * Network service
 * Handle network module requests
 */
var networkService = function($q, $rootScope, rpcService) {
    var self = this;

    self.saveWiredStaticConfiguration = function(interface, ipAddress, routerAddress, nameServer, fallback) {
        return rpcService.sendCommand('save_wired_static_configuration', 'network', {'interface':interface, 'ip_address':ipAddress, 'router_address':routerAddress, 'name_server':nameServer, 'fallback':fallback});
    };

    self.saveWiredDhcpConfiguration = function(interface) {
        return rpcService.sendCommand('save_wired_dhcp_configuration', 'network', {'interface':interface});
    };

    self.scanWifiNetworks = function() {
        return rpcService.sendCommand('scan_wifi_networks', 'network');
    };

    self.getInterfacesConfigurations = function() {
        return rpcService.sendCommand('get_interfaces_configurations', 'network');
    };

    self.testWifiNetwork = function(interface, network, encryption, password, hidden) {
        return rpcService.sendCommand('test_wifi_network', 'network', {'interface':interface, 'network':network, 'encryption':encryption, 'password':password, 'hidden':hidden}, 30);
    };

    self.saveWifiNetwork = function(interface, network, encryption, password, hidden) {
        return rpcService.sendCommand('save_wifi_network', 'network', {'interface':interface, 'network':network, 'encryption':encryption, 'password':password, 'hidden':hidden}, 20);
    };

    self.disconnectWifi = function(network) {
        return rpcService.sendCommand('disconnect_wifi', 'network', {'network':network}, 20);
    };
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('networkService', ['$q', '$rootScope', 'rpcService', networkService]);

