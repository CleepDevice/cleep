/**
 * Raspiot services
 * Handles :
 *  - installed modules: module and module helpers (reload config, get config...)
 *  - devices: all devices and devices helpers (reload devices)
 */
var raspiotService = function($rootScope, $q, toast, rpcService, objectsService) {
    var self = this;
    self.__deferred_modules = $q.defer();
    self.__deferred_events = $q.defer();
    self.__deferred_renderers = $q.defer();
    self.devices = [];
    self.modules = {};
    self.renderers = {};
    self.events = {};

    /**
     * Set module icon (material icons)
     */
    self.__setModuleIcon = function(module)
    {
        var icons = {
            actions: 'play-box-outline',
            database: 'database',
            gpios: 'video-input-component',
            messageboard: 'counter',
            sensors: 'chip',
            shutters: 'unfold-more-horizontal',
            sounds: 'volume-high',
            system: 'heart-pulse',
            network: 'ethernet',
            bulksms: 'message-processing',
            freemobilesms: 'message-processing',
            smtp: 'email',
            pushover: 'send',
            openweathermap: 'cloud',
            cleepbus: 'video-input-antenna',
            developer: 'worker',
            update: 'update',
            audio: 'speaker',
            speechrecognition: 'text-to-speech',
            niccolometronome: 'metronome'
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
        self.__deferred_modules.resolve();
        self.__deferred_modules = null;
    };

    /**
     * Get specified module configuration
     * @param module: module name to return configuration
     * @return promise: promise is resolved when configuration is loaded
     */
    self.getModuleConfig = function(module)
    {
        var deferred = $q.defer();

        if( self.__deferred_modules===null )
        {
            //module config already loaded, resolve it if available
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
            self.__deferred_modules.promise
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
     * Set devices
     * Prepare dashboard widgets and init device using associated module
     */
    self._setDevices = function(devices)
    {
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
    };

    /**
     * Reload devices
     * Call getDevices command again and set devices
     */
    self.reloadDevices = function()
    {
        var d = $q.defer();
        var uuid = null;
        var i = 0;

        rpcService.getDevices()
            .then(function(devices) {
                self._setDevices(devices);
                d.resolve(self.devices);
            });
        
        return d.promise;
    };

    /**
     * Set renderers
     * Just set renderers list
     */
    self._setRenderers = function(renderers)
    {
        self.renderers = renderers;
        self.__deferred_renderers.resolve();
        self.__deferred_renderers = null;
    };

    /**
     * Get renderers
     * @return promise
     */
    self.getRenderers = function()
    {
        var deferred = $q.defer();

        if( self.__deferred_renderers===null )
        {
            //renderers already loaded, return collection
            deferred.resolve(self.renderers);
        }
        else
        {
            self.__deferred_renderers.promise
                .then(function() {
                    console.log('resolve renderers');
                    deferred.resolve(self.renderers);
                }, function() {
                    deferred.reject();
                });
        }

        return deferred.promise;
    };

    /**
     * Set events
     * Just set events list
     */
    self._setEvents = function(events)
    {
        self.events = events;
        self.__deferred_events.resolve();
        self.__deferred_events = null;
    };

    /**
     * Get events
     * @return promise
     */
    self.getEvents = function()
    {
        var deferred = $q.defer();

        if( self.__deferred_events===null )
        {
            //events already loaded, return collection
            deferred.resolve(self.events);
        }
        else
        {
            self.__deferred_events.promise
                .then(function() {
                    console.log('resolve events');
                    deferred.resolve(self.events);
                }, function() {
                    deferred.reject();
                });
        }

        return deferred.promise;
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
    self.getRenderersOfType = function(type)
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
        return rpcService.sendCommand('get_modules_debug', 'inventory', null, 20);
    }; 

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('raspiotService', ['$rootScope', '$q', 'toastService', 'rpcService', 'objectsService', raspiotService]);

