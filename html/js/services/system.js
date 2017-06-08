/**
 * System service
 * Handle system module requests
 */
var systemService = function($rootScope, rpcService, raspiotService) {
    var self = this;
    
    /**
     * Return directive infos
     */
    self.getDirectiveInfos = function() {
        return {
            label: 'System',
            name: 'systemConfigDirective'
        };  
    }; 

    /**
     * Change city
     */
    self.setCity = function(city, country) {
        return rpcService.sendCommand('set_city', 'system', {'city':city, 'country':country});
    };

    /**
     * Get city
     */
    self.getCity = function() {
        return rpcService.sendCommand('get_city', 'system');
    };

    /**
     * Get sunset/sunrise
     */
    self.getSun = function() {
        return rpcService.sendCommand('get_sun', 'system');
    };

    /**
     * Get current time
     */
    self.getTime = function() {
        return rpcService.sendCommand('get_time', 'system');
    };

    /**
     * Get filesystem infos
     */
    self.getFilesystemInfos = function() {
        return rpcService.sendCommand('get_filesystem_infos', 'system');
    };

    /**
     * Get network infos
     */
    self.getNetworkInfos = function() {
        return rpcService.sendCommand('get_network_infos', 'system');
    };

    /**
     * Set monitoring
     */
    self.setMonitoring = function(monitoring) {
        return rpcService.sendCommand('set_monitoring', 'system', {'monitoring': monitoring});
    };

    /**
     * Reboot system
     */
    self.reboot = function() {
        return rpcService.sendCommand('reboot_system', 'system');
    };

    /**
     * Halt system
     */
    self.halt = function() {
        return rpcService.sendCommand('halt_system', 'system');
    };

    /**
     * Restart raspiot
     */
    self.restart = function() {
        return rpcService.sendCommand('restart', 'system');
    };

    /**
     * Install module
     */
    self.installModule = function(module) {
        return rpcService.sendCommand('install_module', 'system', {'module':module});
    };

    /**
     * Uninstall module
     */
    self.uninstallModule = function(module) {
        return rpcService.sendCommand('uninstall_module', 'system', {'module':module});
    };

    /**
     * Download logs
     */
    self.downloadLogs = function() {
        rpcService.download('download_logs', 'system');
    };

    /**
     * Catch system time event
     */
    $rootScope.$on('system.time.now', function(event, uuid, params) {
        for( var i=0; i<raspiotService.devices.length; i++ )
        {
            if( raspiotService.devices[i].uuid==uuid )
            {
                raspiotService.devices[i].time = params.time;
                raspiotService.devices[i].sunset = params.sunset;
                raspiotService.devices[i].sunrise = params.sunrise;
                break;
            }
        }
    });

    /**
     * Catch cpu monitoring event
     */
    $rootScope.$on('system.monitoring.cpu', function(event, uuid, params) {
        for( var i=0; i<raspiotService.devices.length; i++ )
        {
            if( raspiotService.devices[i].type==='monitor' )
            {
                raspiotService.devices[i].cpu = params;
                break;
            }
        }
    });

    /**
     * Catch memory monitoring event
     */
    $rootScope.$on('system.monitoring.memory', function(event, uuid, params) {
        for( var i=0; i<raspiotService.devices.length; i++ )
        {
            if( raspiotService.devices[i].type==='monitor' )
            {
                raspiotService.devices[i].memory = params;
                break;
            }
        }
    });

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('systemService', ['$rootScope', 'rpcService', 'raspiotService', systemService]);

