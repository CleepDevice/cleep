/**
 * Modules configurations service
 * It allows easy access to module configuration
 * System is in charge to load modules configurations at application startup
 *
 * You can access module configuration using configsService.configs['<module name>']
 */
var configsService = function($rootScope, $q, toast, rpcService) {
    var self = this;
    //list of configs
    self.configs = [];

    /**
     * Set modules configurations
     * Internal usage, do not use
     */
    self._setConfigs = function(configs)
    {
        self.configs = configs;
    };

    /**
     * Get specified module configuration
     */
    self.getConfig = function(module)
    {
        if( self.configs[module] )
        {
            return self.configs[module];
        }
        else
        {
            console.error('Specified module "' + module + '" has no configuration');
            return {};
        }
    };

    /**
     * Reload configuration of specified module
     */
    self.reloadConfig = function(module)
    {
        var d = $q.defer();

        if( self.configs[module] )
        {
            rpcService.sendCommand('get_module_config', module)
                .then(function(resp) {
                    if( resp.error===false )
                    {
                        //save new config
                        self.configs[module] = resp.data;
                        d.resolve(resp.data);
                    }
                    else
                    {
                        console.error(resp.message);
                        toast.error(resp.message);
                        d.reject(resp.message);
                    }
                }, function(err) {
                    //error occured
                    toast.error('Unable to reload module "' + module + '" configuration');
                    console.error('Unable to reload module "' + module + '" configuration', err);
                    d.reject(err);
                });
        }
        else
        {
            console.error('Specified module "' + module + '" has no configuration');
            d.reject('module has no config');
        }

        return d.promise;
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('configsService', ['$rootScope', '$q', 'toastService', 'rpcService', configsService]);

