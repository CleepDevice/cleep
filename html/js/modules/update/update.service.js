/**
 * Update service
 * Handle update module requests
 */
var updateService = function($rootScope, rpcService, raspiotService $q) {
    var self = this;
    
    /**
     * Get status
     */
    self.getStatus = function(full) {
        if( full )
        {
            //return full status (maybe huge!)
            return rpcService.sendCommand('get_full_status', 'update');
        }
        else
        {
            //return light status
            return rpcService.sendCommand('get_status', 'update');
        }
    };

    /**
     * Check for raspiot updates
     */
    self.checkRaspiotUpdates = function() {
        return rpcService.sendCommand('check_raspiot_updates', 'update');
    };

    /**
     * Cancel current update
     */
    self.cancelUpdate = function() {
        return rpcService.sendCommand('cancel', 'update');
    };

    /**
     * Check for modules updates
     */
    self.checkModulesUpdates = function() {
        return rpcService.sendCommand('check_modules_updates', 'update');
    };

    /**
     * Set automatic update
     */
    self.setAutomaticUpdate = function(raspiotUpdate, modulesUpdate) {
        return rpcService.sendCommand('set_automatic_update', 'update', {'raspiot_update':raspiotUpdate, 'modules_update':modulesUpdate});
    };

    /**
     * Install module update
     */
    self.updateModule = function(module) {
        var defer = $q.defer();
        
        rpcService.sendCommand('update_module', 'update', {'module': module});
            .then(function(resp) {
                self.updatingModules.push(module);
                defer.resolve(resp);
            }, function(err) {
                defer.reject(err);
            });
    };

    /** 
     * Handle module uninstall event
     */
    $rootScope.$on('system.module.uninstall', function(event, uuid, params) {
        if( !params.status )
        {   
            //idle state, drop event
            return;
        }

        if( self.updatingModules.indexOf(params.module)===-1 )
        {
            //module not updating, drop event
            return;
        }
     
        if( params.status==2 )
        {   
            toast.error('Error during module ' + params.module + ' uninstallation');
        }   
        else if( params.status==4 )
        {   
            toast.error('Module ' + params.module + ' uninstallation canceled');
        }   
        else if( params.status==3 )
        {   
            //reload system config to activate restart flag (see main controller)
            raspiotService.reloadModuleConfig('system')
                .then(function() {
                    toast.success('Module ' + params.module + ' is uninstalled. Please restart raspiot' );
                }); 
        }   
    }); 

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('updateService', ['$rootScope', 'rpcService', 'raspiotService', '$q', updateService]);

