/**
 * System service
 * Handle system module requests
 */
var systemService = function($rootScope, rpcService, raspiotService, toast, appToolbarService)
{
    var self = this;
    self.raspiotInstallStatus = 0; //idle status
    self.restartButtonId = null;
    self.rebootButtonId = null;
    
    /**
     * Get filesystem infos
     */
    self.getFilesystemInfos = function()
    {
        return rpcService.sendCommand('get_filesystem_infos', 'system', 30000);
    };

    /**
     * Get network infos
     */
    self.getNetworkInfos = function()
    {
        return rpcService.sendCommand('get_network_infos', 'system', 30000);
    };

    /**
     * Set monitoring
     */
    self.setMonitoring = function(monitoring)
    {
        return rpcService.sendCommand('set_monitoring', 'system', {'monitoring': monitoring});
    };

    /**
     * Reboot system
     */
    self.reboot = function()
    {
        return rpcService.sendCommand('reboot_system', 'system');
    };

    /**
     * Halt system
     */
    self.halt = function()
    {
        return rpcService.sendCommand('halt_system', 'system');
    };

    /**
     * Restart raspiot
     */
    self.restart = function()
    {
        return rpcService.sendCommand('restart', 'system');
    };

    /**
     * Install module
     */
    self.installModule = function(module)
    {
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
    self.updateModule = function(module)
    {
        return rpcService.sendCommand('update_module', 'system', {'module':module}, 300);
    };

    /**
     * Update raspiot
     */
    self.updateRaspiot = function()
    {
        return rpcService.sendCommand('update_raspiot', 'system', {}, 300);
    };

    /**
     * Download logs
     */
    self.downloadLogs = function()
    {
        rpcService.download('download_logs', 'system');
    };

    /**
     * Get logs
     */
    self.getLogs = function()
    {
        return rpcService.sendCommand('get_logs', 'system');
    };

    /**
     * Set module debug
     */
    self.setModuleDebug = function(module, debug)
    {
        return rpcService.sendCommand('set_module_debug', 'system', {'module':module, 'debug':debug});
    };

    /**
     * Set system debug
     */
    self.setSystemDebug = function(debug)
    {
        return rpcService.sendCommand('set_system_debug', 'system', {'debug':debug});
    };

    /**
     * Set trace
     */
    self.setTrace = function(trace)
    {
        return rpcService.sendCommand('set_trace', 'system', {'trace':trace})
            .then(function() {
                return raspiotService.reloadModuleConfig('system');
            });
    };

    /**
     * Set hostname
     */
    self.setHostname = function(hostname)
    {
        return rpcService.sendCommand('set_hostname', 'system', {'hostname':hostname});
    };

    /**
     * Set event not rendered
     */
    self.setEventNotRendered = function(renderer, event, disabled)
    {
        return rpcService.sendCommand('set_event_not_rendered', 'system', {'renderer':renderer, 'event':event, 'disabled':disabled})
            .then(function(resp) {
                //overwrite system event_not_rendered config value
                raspiotService.modules.system.config.eventsnotrendered = resp.data;
            });
    };

    /**
     * Check for raspiot updates
     */
    self.checkRaspiotUpdates = function()
    {
        return rpcService.sendCommand('check_raspiot_updates', 'system');
    };

    /**
     * Check for modules updates
     */
    self.checkModulesUpdates = function()
    {
        return rpcService.sendCommand('check_modules_updates', 'system');
    };

    /**
     * Set automatic update
     */
    self.setAutomaticUpdate = function(raspiotUpdateEnabled, modulesUpdateEnabled)
    {
        return rpcService.sendCommand('set_automatic_update', 'system', {'raspiot_update_enabled':raspiotUpdateEnabled, 'modules_update_enabled':modulesUpdateEnabled});
    };

    /**
     * Enable/disable crash report
     */
    self.setCrashReport = function(enable)
    {
        return rpcService.sendCommand('set_crash_report', 'system', {'enable':enable});
    };

    /**
     * Set backup update time
     */
    self.setRaspiotBackupDelay = function(delay)
    {
        return rpcService.sendCommand('set_raspiot_backup_delay', 'system', {'delay': delay});
    };

    /**
     * Make backup of raspiot configuration files
     */
    self.backupRaspiotConfig = function()
    {
        return rpcService.sendCommand('backup_raspiot_config', 'system', {});
    };

    /**
     * Watch for system config changes to add restart/reboot buttons if restart/reboot is needed
     */
    $rootScope.$watchCollection(
        function() {
            return raspiotService.modules['system'];
        },
        function(newConfig) {
            if( !angular.isUndefined(newConfig) && newConfig.config )
            {
                //handle restart button
                if( !newConfig.config.needrestart && self.restartButtonId )
                {
                    appToolbarService.addButton(self.restartButtonId);
                    self.restartButtonId = null;
                }
                else if( newConfig.config.needrestart && !self.restartButtonId )
                {
                    self.restartButtonId = appToolbarService.addButton('Restart to apply changes', 'restart', raspiotService.restart, 'md-accent');
                }

                //handle reboot button
                if( !newConfig.config.needreboot && self.rebootButtonId )
                {
                    appToolbarService.addButton(self.rebootButtonId);
                    self.rebootButtonId = null;
                }
                else if( newConfig.config.needreboot && !self.rebootButtonId )
                {
                    self.rebootButtonId = appToolbarService.addButton('Reboot to apply changes', 'restart', raspiotService.reboot, 'md-accent');
                }
            }
        }
    );

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

    /**
     * Handle raspiot update event
     */
    $rootScope.$on('system.raspiot.update', function(event, uuid, params) {
        if( params.status===null || params.status===undefined )
        {
            return;
        }

        self.raspiotInstallStatus = params.status;
        if( params.status==0 || params.status==1 )
        {
            //idle status or installing update
        }
        else if( params.status==2 )
        {   
            toast.success('Application has been installed. Please reboot device.');
            //reset install status to remove item from ui
            self.raspiotInstallStatus = 0;
        }   
        else
        {   
            toast.error('Error during application update. See logs for details.');
            //reset install status to remove item from ui
            self.raspiotInstallStatus = 0;
        }   
    });

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('systemService', ['$rootScope', 'rpcService', 'raspiotService', 'toastService', 'appToolbarService', systemService]);
