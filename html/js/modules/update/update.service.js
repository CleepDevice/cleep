/**
 * Update service
 * Handle update module requests
 */
var updateService = function($rootScope, rpcService, raspiotService, toast) {
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
     * Update module
     */
    self.updateModule = function(module) {
        return rpcService.sendCommand('update_module', 'update', {'module': module});
    };

    /** 
     * Handle module install event
     */
    $rootScope.$on('system.module.install', function(event, uuid, params) {
        //drop useless status
        if( !params.status )
        {   
            return;
        }   

        //drop install not triggered by update
        if( params.updateprocess===false )
        {   
            return;
        }   
     
        if( params.status==2 )
        {   
            toast.error('Error during module ' + params.module + ' update');
        }   
        else if( params.status==4 )
        {   
            toast.error('Module ' + params.module + ' update canceled');
        }   
        else if( params.status==3 )
        {   
            //reload system config to activate restart flag (see main controller)
            raspiotService.reloadModuleConfig('system')
                .then(function() {
                    //set module pending status
                    toast.success('Module ' + params.module + ' update will be finalized after next restart');
                }); 
        }   
    }); 

    /** 
     * Handle module uninstall event
     */
    $rootScope.$on('system.module.uninstall', function(event, uuid, params) {
        //drop useless status
        if( !params.status )
        {   
            return;
        }

        //drop uninstall not triggered by update
        if( params.updateprocess===false )
        {
            return;
        }
     
        //only catch error status code. Restart flag will be turned on after complete install
        if( params.status==2 )
        {   
            toast.error('Error during module ' + params.module + ' uninstallation. Update canceled');
        }   
    });

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('updateService', ['$rootScope', 'rpcService', 'raspiotService', 'toastService', updateService]);

