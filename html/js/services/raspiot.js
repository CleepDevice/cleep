/**
 * Raspiot services
 * Handles :
 *  - installed modules: module and module helpers (reload config, get config...)
 *  - devices: all devices and devices helpers (reload devices)
 */
var raspiotService = function($rootScope, $q, toast, rpcService, objectsService) {
    var self = this;
    //initialized
    self.__deferred = $q.defer();
    //list of devices
    self.devices = [];
    //list of installed modules
    self.modules = {};
    //list of renderers
    self.renderers = {};

    /**
     * Set module icon (material icons)
     */
    self.__setModuleIcon = function(module)
    {
        var icons = {
            actions: 'slideshow',
            database: 'storage',
            gpios: 'filter_center_focus',
            messageboard: 'view_comfy',
            sensors: 'leak_add',
            shutters: 'format_line_spacing',
            sounds: 'volume_up',
            system: 'favorite',
            network: 'network_wifi',
            bulksms: 'sms',
            freemobilesms: 'sms',
            smtp: 'mail',
            pushover: 'send',
            openweathermap: 'cloud'
        };

        if( !angular.isUndefined(icons[module]) )
        {
            self.modules[module].icon = icons[module];
        }
        else
        {
            //default icon
            self.modules[module].icon = 'bookmark';
        }
    };

    /**
     * Set modules configurations as returned by rpcserver
     * Internal usage, do not use
     */
    self._setModules = function(modules)
    {
        self.modules = modules;

        //inject module icon in each entry
        for( module in self.modules )
        {
            self.__setModuleIcon(module);

            self.modules[module].hasService = objectsService._moduleHasService(module);
        }

        //resolve deferred
        self.__deferred.resolve();
        self.__deferred = null;
    };

    /**
     * Get specified module configuration
     * @param module: module name to return configuration
     * @return promise: promise is resolved when configuration is loaded
     */
    self.getModuleConfig = function(module)
    {
        var deferred = $q.defer();

        if( self.__deferred===null )
        {
            if( self.modules[module] )
            {
                deferred.resolve(self.modules[module].config);
            }
            else
            {
                console.error('Specified module "' + module + '" has no configuration');
                deferred.reject();
            }
        }
        else
        {
            //module not loaded, wait for it
            self.__deferred.promise
                .then(function() {
                    deferred.resolve(self.modules[module].config);
                }, function() {
                    deferred.reject();
                });
        }

        return deferred.promise;
    };

    /**
     * Reload configuration of specified module
     */
    self.reloadModuleConfig = function(module)
    {
        var d = $q.defer();

        if( self.modules[module] )
        {
            rpcService.sendCommand('get_module_config', module)
                .then(function(resp) {
                    if( resp.error===false )
                    {
                        //save new config
                        self.modules[module].config = resp.data;
                        //self.__setModuleIcon(module);
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
        var uuid = null;
        var i = 0;

        rpcService.getDevices()
            .then(function(devices) {
                var newDevices = [];
                for( var module in devices )
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
                for( i=self.devices.length-1; i>=0; i--)
                {
                    self.devices.splice(i, 1);
                }

                //save new devices
                for( i=0; i<newDevices.length; i++ )
                {
                    self.devices.push(newDevices[i]);
                }

                d.resolve(self.devices);
            });
        
        return d.promise;
    };

    /**
     * Load renderers
     */
    self.loadRenderers = function()
    {
        var d = $q.defer();

        rpcService.getRenderers()
            .then(function(renderers) {
                self.renderers = renderers;

                d.resolve(renderers);
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
        for( var name in self.modules )
        {
            if( name===module && self.modules[name].installed )
            {
                return true;
            }
        }
        return false;
    };

    /**
     * Returns renderers of specified type
     */
    self.getRenderers = function(type)
    {
        if( self.renderers[type] )
        {
            return self.renderers[type];
        }

        return {};
    };

    /** 
     * Get modules debug
     */
    self.getModulesDebug = function() {
        return rpcService.sendCommand('get_modules_debug', 'inventory');
    }; 

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('raspiotService', ['$rootScope', '$q', 'toastService', 'rpcService', 'objectsService', raspiotService]);

