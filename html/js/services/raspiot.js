/**
 * Raspiot services
 * Handles :
 *  - module configurations: base module configs and config helpers (reload config, get config...)
 *  - devices: all devices and devices helpers (reload devices)
 */
var raspiotService = function($rootScope, $q, toast, rpcService, objectsService) {
    var self = this;
    //list of configs
    self.configs = [];
    //list of devices
    self.devices = [];
    //list of modules
    self.modules = [];

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

    /**
     * Load devices
     */
    self.reloadDevices = function()
    {
        var d = $q.defer();

        rpcService.getDevices()
            .then(function(devices) {
                var newDevices = [];
                for( module in devices )
                {
                        //add specific ui stuff
                        for( uuid in devices[module] )
                        {
                            //add widget infos
                            devices[module][uuid].__widget = {
                                mdcolors: '{background:"default-primary-300"}'
                            };

                            //add service infos
                            devices[module][uuid].__service = module;
                        }

                        //request module service to update specifically its device
                        if( objectsService.services[module] && typeof(objectsService.services[module].initDevices)!=='undefined' )
                        {
                            moduleDevices = objectsService.services[module].initDevices(devices[module]);
                        }
                        else
                        {
                            moduleDevices = devices[module];
                        }

                        //store device
                        for( uuid in moduleDevices )
                        {
                            newDevices.push(moduleDevices[uuid]);
                        }
                }

                //clear existing devices
                for( var i=self.devices.length-1; i>=0; i--)
                {
                    self.devices.splice(i, 1);
                }

                //save new devices
                for( var i=0; i<newDevices.length; i++ )
                {
                    self.devices.push(newDevices[i]);
                }

                d.resolve(self.devices);
            });
        
        return d.promise;
    };

    /**
     * Check if specified module name is loaded
     * @param module: module name
     * @return true if module is loaded, false otherwise
     */
    self.hasModule = function(module)
    {
        return objectsService.modules.indexOf(module)!==-1;
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('raspiotService', ['$rootScope', '$q', 'toastService', 'rpcService', 'objectsService', raspiotService]);

