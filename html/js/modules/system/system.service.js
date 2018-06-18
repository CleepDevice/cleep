/**
 * System service
 * Handle system module requests
 */
var systemService = function($rootScope, rpcService, raspiotService) {
    var self = this;
    
    /**
     * Change city
     */
    self.setCity = function(city, country) {
        return rpcService.sendCommand('set_city', 'system', {'city':city, 'country':country}, 20);
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
        return rpcService.sendCommand('get_filesystem_infos', 'system', 30000);
    };

    /**
     * Get network infos
     */
    self.getNetworkInfos = function() {
        return rpcService.sendCommand('get_network_infos', 'system', 30000);
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
        return rpcService.sendCommand('install_module', 'system', {'module':module}, 300);
    };

    /**
     * Uninstall module
     */
    self.uninstallModule = function(module) {
        return rpcService.sendCommand('uninstall_module', 'system', {'module':module}, 300);
    };

    /**
     * Update module
     */
    self.updateModule = function(module) {
        return rpcService.sendCommand('update_module', 'system', {'module':module}, 300);
    };

    /**
     * Download logs
     */
    self.downloadLogs = function() {
        rpcService.download('download_logs', 'system');
    };

    /**
     * Get logs
     */
    self.getLogs = function() {
        return rpcService.sendCommand('get_logs', 'system');
    };

    /**
     * Set module debug
     */
    self.setModuleDebug = function(module, debug) {
        return rpcService.sendCommand('set_module_debug', 'system', {'module':module, 'debug':debug});
    };

    /**
     * Set hostname
     */
    self.setHostname = function(hostname) {
        return rpcService.sendCommand('set_hostname', 'system', {'hostname':hostname});
    };

    /**
     * Set event not rendered
     */
    self.setEventNotRendered = function(renderer, event, disabled) {
        return rpcService.sendCommand('set_event_not_rendered', 'system', {'renderer':renderer, 'event':event, 'disabled':disabled})
            .then(function(resp) {
                //overwrite system event_not_rendered config value
                raspiotService.modules.system.config.eventsnotrendered = resp.data;
            });
    };

    /**
     * Check for raspiot updates
     */
    self.checkRaspiotUpdates = function() {
        return rpcService.sendCommand('check_raspiot_updates', 'system');
    };

    /**
     * Check for modules updates
     */
    self.checkModulesUpdates = function() {
        return rpcService.sendCommand('check_modules_updates', 'system');
    };

    /**
     * Set automatic update
     */
    self.setAutomaticUpdate = function(raspiotUpdateEnabled, modulesUpdateEnabled) {
        return rpcService.sendCommand('set_automatic_update', 'system', {'raspiot_update_enabled':raspiotUpdateEnabled, 'modules_update_enabled':modulesUpdateEnabled});
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

