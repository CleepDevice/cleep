/**
 * Raspiot services
 * Handles :
 *  - installed modules: module and module helpers (reload config, get config...)
 *  - devices: all devices and devices helpers (reload devices)
 */
var raspiotService = function($injector, $q, toast, rpcService, $http, $ocLazyLoad, $templateCache) {
    var self = this;
    self.__deferred_modules = $q.defer();
    self.__deferred_events = $q.defer();
    self.__deferred_renderers = $q.defer();
    self.devices = [];
    self.modules = {};
    self.renderers = {};
    self.events = {};
    self.modulesPath = 'js/modules/';

    /**
     * Build list of system files
     * @param module: module name
     * @param desc: description content file (json)
     * @return object { js:[], html:[] }
     */
    self.__getModuleSystemFiles = function(module, desc)
    {
        //init
        var files = {
            'js': [],
            'html': []
        };
        var entries = ['widgets', 'services'];

        if( !desc || !desc.system )
        {
            return files;
        }

        //get widget files
        if( desc.system.widgets && desc.system.widgets.js )
        {
            for( var i=0; i<desc.system.widgets.js.length; i++ )
            {
                files.js.push(self.modulesPath + module + '/' + desc.system.widgets.js[i]);
            }
        }
        if( desc.system.widgets && desc.system.widgets.html )
        {
            for( var i=0; i<desc.system.widgets.html.length; i++ )
            {
                files.html.push(self.modulesPath + module + '/' + desc.system.widgets.html[i]);
            }
        }

        //get services
        if( desc.system.services )
        {
            for( var i=0; i<desc.system.services.length; i++ )
            {
                files.js.push(self.modulesPath + module + '/' + desc.system.services[i]);
            }
        }

        return files;
    };

    /**
     * Load js files
     * Use oclazyloader to inject automatically angular stuff
     * @param jsFiles: list of js files (with full path)
     * @return promise
     */
    self.__loadJsFiles = function(jsFiles)
    {
        //load js files using lazy loader
        return $ocLazyLoad.load({
            'reconfig': true,
            'rerun': true,
            'files': jsFiles
        });
    };

    /**
     * Load html files
     * Html are considerated as templates and saved in angular templateCache for easy use
     * @param htmlFiles: list of html files (with full path)
     * @return promise
     */
    self.__loadHtmlFiles = function(htmlFiles)
    {
        //init
        var promises = [];
        var d = $q.defer();

        //fill templates promises
        for( var i=0; i<htmlFiles.length; i++ )
        {
            promises.push($http.get(htmlFiles[i]));
        }

        //and execute them
        $q.all(promises)
            .then(function(templates) {
                //check if templates available
                if( !templates ) 
                    return $q.resolve();

                //cache templates
                for( var i=0; i<templates.length; i++ )
                {
                    var templateName = htmlFiles[i].substring(htmlFiles[i].lastIndexOf('/')+1);
                    $templateCache.put(templateName, templates[i].data);
                }
            }, function(err) {
                console.error('Error occured loading html files:', err);
            })
            .finally(function() {
                d.resolve();
            });

        return d.promise;
    };

    /**
     * Convert to camelcase specified string (with dot)
     */
    self.__camelize = function(str)
    {
        return str.replace(/^[_.\- ]+/, '')
                .toLowerCase()
                .replace(/[_.\- ]+(\w|$)/g, (m, p1) => p1.toUpperCase());
    };

    /**
     * Load module
     * @return promise
     */
    self.__loadModule = function(module)
    {
        //init
        var url = self.modulesPath + module + '/desc.json';
        var desc = null;
        var d = $q.defer();
        var files = null;

        //do not load data of modules with pending status
        if( self.modules[module].pending )
        {
            return;
        }

        //load desc.json file from module folder
        $http.get(url)
            .then(function(resp) {
                //save desc content
                self.modules[module].desc = resp.data;

                //set module icon
                self.modules[module].icon = 'bookmark';
                if( resp.data.icon )
                {
                    self.modules[module].icon = resp.data.icon;
                }

                //module "has config" flag
                self.modules[module].hasConfig = false;
                if( resp.data.config )
                {
                    self.modules[module].hasConfig = true;
                }

                //load module system objects (widgets and services)
                files = self.__getModuleSystemFiles(module, resp.data);
                if( files.js.length==0 && files.html.length==0 )
                {
                    //no files to lazyload, stop chain here
                    return $q.reject('no-files');
                };

                //load html files first
                return self.__loadHtmlFiles(files.html);

            }, function(err) {
                //save empty desc for module
                self.modules[module].desc = {};

                //and reject promise
                console.error('Error occured loading "' + module + '" description file', err);

                //reject final promise
                d.reject();
            })
            .then(function(resp) {
                //load js files
                return self.__loadJsFiles(files.js);

            }, function(err) {
                if( err!='no-files' )
                {
                    console.error('Error loading modules html files:', err);
                }
            })
            .then(function() {
                //force getting service from injector to make them executed as soon as possible
                for( var i=0; i<files.js.length; i++ )
                {
                    if( files.js[i].indexOf('service')>=0 )
                    {
                        //guess service name from filename
                        serviceName = files.js[i].replace(/^.*[\\\/]/, '');
                        serviceName = serviceName.replace('.js', '');
                        serviceName = self.__camelize(serviceName);

                        //make sure
                        if( $injector.has(serviceName) )
                        {
                            $injector.get(serviceName, function(err) {
                                console.error('Error occured during service loading:', err)
                            });
                        }
                    }
                }

            }, function(err) {
                console.error('Error loading modules js files:', err);
            })
            .finally(function() {
                //modules are completely loaded
                d.resolve();
            });

        return d.promise;
    };

    /**
     * Return module description (desc.json file content)
     * @return promise<json|null>
     */
    self.getModuleDescription = function(module)
    {
        //init
        var deferred = $q.defer();

        if( self.__deferred_modules===null )
        {
            //module config already loaded, resolve it if available
            if( self.modules[module] )
            {
                deferred.resolve(self.modules[module].desc);
            }
            else
            {
                console.error('Unable to get description of unknown module "' + module + '"');
                deferred.reject(null);
            }
        }
        else
        {
            //module not loaded, wait for it
            self.__deferred_modules.promise
                .then(function() {
                    deferred.resolve(self.modules[module].desc);
                }, function() {
                    deferred.reject(null);
                });
        }

        return deferred.promise;
    };

    /**
     * Set modules configurations as returned by rpcserver
     * Internal usage, do not use
     */
    self._setModules = function(modules)
    {
        //save modules
        self.modules = modules;

        //load description for each local modules
        var promises = [];
        for( module in self.modules )
        {
            if( self.modules[module].installed && !self.modules[module].library )
            {
                promises.push(self.__loadModule(module));
            }
        }

        //resolve deferred once all promises terminated
        //TODO sequentially chain promises https://stackoverflow.com/a/43543665 or https://stackoverflow.com/a/24262233
        //$q.all execute finally statement as soon as one of promises is rejected
        return $q.all(promises)
            .then(function(resp) {
            }, function(err) {
                //necessary to avoid rejection warning
            })
            .finally(function() {
                //no deferred during reboot/restart, handle this case
                if( self.__deferred_modules )
                {
                    self.__deferred_modules.resolve();
                    self.__deferred_modules = null;
                }
            });
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
     * @param module: module name
     * @return promise
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

            //store device
            for( uuid in devices[module] )
            {
                newDevices.push(devices[module][uuid]);
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
        //no deferred during reboot/restart, handle this case
        if( self.__deferred_renderers )
        {
            self.__deferred_renderers.resolve();
            self.__deferred_renderers = null;
        }
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
        //no deferred during reboot/restart, handle this case
        if( self.__deferred_events )
        {
            self.__deferred_events.resolve();
            self.__deferred_events = null;
        }
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

    /**
     * Reboot system
     * This function calls system module function to avoid adhesion of system service from angular app
     */
    self.reboot = function() {
        return rpcService.sendCommand('reboot_system', 'system');
    };

    /**
     * Halt system
     * This function calls system module function to avoid adhesion of system service from angular app
     */
    self.halt = function() {
        return rpcService.sendCommand('halt_system', 'system');
    };

    /**
     * Restart raspiot
     * This function calls system module function to avoid adhesion of system service from angular app
     */
    self.restart = function(delay) {
        return rpcService.sendCommand('restart', 'system', {'delay': delay});
    };

    /**
     * Install module
     * This function calls system module function to avoid adhesion of system service from angular app
     */
    self.installModule = function(module) {
        return rpcService.sendCommand('install_module', 'system', {'module':module}, 300);
    };

    /**
     * Uninstall module
     * This function calls system module function to avoid adhesion of system service from angular app
     */
    self.uninstallModule = function(module) {
        return rpcService.sendCommand('uninstall_module', 'system', {'module':module}, 300);
    };

    /**
     * Update module
     * This function calls system module function to avoid adhesion of system service from angular app
     */
    self.updateModule = function(module) {
        return rpcService.sendCommand('update_module', 'system', {'module':module}, 300);
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('raspiotService', ['$injector', '$q', 'toastService', 'rpcService', '$http', '$ocLazyLoad', '$templateCache', raspiotService]);
