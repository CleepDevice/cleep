/**
 * Network service
 * Handle network module requests
 */
var networkService = function($q, $rootScope, rpcService) {
    var self = this;

    self.addWiredStaticInterface = function(interface, ipAddress, routers, domainNameServers) {
        return rpcService.sendCommand('add_wired_static_interface', 'network', {'interface':interface, 'ip_address':ipAddress, 'routers':routers, 'domain_name_servers':domainNameServers});
    };

    self.deleteWiredStaticInterface = function(interface) {
        return rpcService.sendCommand('delete_wired_static_interface', 'network', {'interface':interface});
    };

    self.addWifiNetwork = function(network, networkType, password, hidden) {
        return rpcService.sendCommand('add_wifi_network', 'network', {'network':network, 'network_type':networkType, 'password':password, 'hidden':hidden});
    };

    self.deleteWifiNetwork = function(network) {
        return rpcService.sendCommand('delete_wifi_network', 'network', {'network':network});
    };

    self.scanWifiNetworks = function() {
        return rpcService.sendCommand('scan_wifi_networks', 'network');
    };

    self.getInterfacesConfigurations = function() {
        return rpcService.sendCommand('get_interfaces_configurations', 'network');
    };

    self.testWifiNetwork = function(interface, network, networkType, password, hidden) {
        return rpcService.sendCommand('test_wifi_network', 'network', {'interface':interface, 'network':network, 'network_type':networkType, 'password':password, 'hidden':hidden}, 30);
    };

    self.saveWifiNetwork = function(interface, network, networkType, password, hidden) {
        return rpcService.sendCommand('save_wifi_network', 'network', {'interface':interface, 'network':network, 'network_type':networkType, 'password':password, 'hidden':hidden}, 20);
    };

    self.disconnectWifi = function(network) {
        return rpcService.sendCommand('disconnect_wifi', 'network', {'network':network}, 20);
    };
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('networkService', ['$q', '$rootScope', 'rpcService', networkService]);

