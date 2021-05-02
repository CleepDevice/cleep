/**
 * Cleep services
 * Handles :
 *  - installed modules: module and module helpers (reload config, get config...)
 *  - devices: all devices and devices helpers (reload devices)
 */
angular
.module('Cleep')
.service('cleepService', ['$injector', '$q', 'toastService', 'rpcService', '$http', '$ocLazyLoad', '$templateCache', '$rootScope',
function($injector, $q, toast, rpcService, $http, $ocLazyLoad, $templateCache, $rootScope) {

    var self = this;
    self.__deferredModules = $q.defer();
    self.__deferredEvents = $q.defer();
    self.__deferredRenderers = $q.defer();
    self.__deferredDrivers = $q.defer();
    self.devices = [];
    self.modules = {};
    self.installableModules = {};
    self.modulesUpdates = {};
    self.renderers = {};
    self.events = {};
    self.drivers = {};
    self.modulesPath = 'js/modules/';

    /**
     * Load Cleep config
     */
    self.loadConfig = function() {
        var config;

        return rpcService.getConfig()
            .then(function(resp) {
                // save response as config to use it in next promise step
                config = resp;

                // set and load modules
                return self._setModules(config.modules);
            })  
            .then(function() {
                // set other stuff
                self._setDevices(config.devices);
                self._setRenderers(config.renderers);
                self._setEvents(config.events);
                self._setDrivers(config.drivers);

                // load installable modules if necessary
                if(Object.keys(self.installableModules).length>0) {
                    return rpcService.getModules(true);
                } else {
                    return Promise.resolve(null);
                }
            })
            .then(function(installableModules) {
                if(installableModules) {
                    self.installableModules = installableModules;
                }
            });
    };

    /**
     * Build list of system files
     * @param module: module name
     * @param desc: description content file (json)
     * @return object { js:[], html:[] }
     */
    self.__getModuleGlobalFiles = function(module, desc) {
        // init
        var files = {
            'js': [],
            'html': [],
            'css': []
        };

        if( !desc || !desc.global ) {
            return files;
        }

        // get global files
        if( desc.global && desc.global.js ) {
            for( var i=0; i<desc.global.js.length; i++ ) {
                files.js.push(self.modulesPath + module + '/' + desc.global.js[i]);
            }
        }
        if( desc.global && desc.global.html ) {
            for( var i=0; i<desc.global.html.length; i++ ) {
                files.html.push(self.modulesPath + module + '/' + desc.global.html[i]);
            }
        }
        if( desc.global && desc.global.css ) {
            for( var i=0; i<desc.global.css.length; i++ ) {
                files.css.push(self.modulesPath + module + '/' + desc.global.css[i]);
            }
        }

        return files;
    };

    /**
     * Sync to object updating source with specified update data.
     * This function keep source memory address
     */
    self.__syncObject = function(source, update) {
        // add/update existing items
        Object.assign(source, update);

        // delete non existing items from update
        for( var key of Object.keys(source) ) {
            if( !(key in update) ) {
                delete source[key];
            }
        }
    };

    /**
     * Load js files
     * Use oclazyloader to inject automatically angular stuff
     * @param jsFiles: list of js files (with full path)
     * @return promise
     */
    self.__loadJsFiles = function(jsFiles) {
        // load js files using lazy loader
        return $ocLazyLoad.load({
            'cache': false,
            'reconfig': true,
            'rerun': true,
            'files': jsFiles
        });
    };

    /**
     * Load css files
     * Use oclazyloader to inject automatically css
     * @param cssFiles: list of css files (with full path)
     * @return promise
     */
    self.__loadCssFiles = function(cssFiles) {
        return $ocLazyLoad.load(cssFiles, {
            cache: false
        });
    };

    /**
     * Load html files
     * Html are considerated as templates and saved in angular templateCache for easier usage
     * @param modulePath: module path
     * @param htmlFiles: list of html files (with full path)
     * @return promise
     */
    self.__loadHtmlFiles = function(modulePath, htmlFiles) {
        // init
        var promises = [];
        var d = $q.defer();

        // fill templates promises
        for( var i=0; i<htmlFiles.length; i++ ) {
            promises.push($http.get(htmlFiles[i]));
        }

        // and execute them
        $q.all(promises)
            .then(function(templates) {
                // check if templates available
                if( !templates ) {
                    return $q.resolve();
                }

                // cache templates
                for( var i=0; i<templates.length; i++ ) {
                    var templateName = htmlFiles[i].replace(modulePath, '');
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
    self.__camelize = function(str) {
        return str.replace(/^[_.\- ]+/, '')
                .toLowerCase()
                .replace(/[_.\- ]+(\w|$)/g, (m, p1) => p1.toUpperCase());
    };

    /**
     * Load module
     * @return promise
     */
    self.__loadModule = function(module) {
        // init
        var modulePath = self.modulesPath + module + '/';
        var url = modulePath + 'desc.json';
        var desc = null;
        var d = $q.defer();
        var files = null;

        // do not load data of modules with pending status
        if( self.modules[module].pending ) {
            return;
        }

        // load desc.json file from module folder
        $http.get(url)
            .then(function(resp) {
                // save desc content
                self.modules[module].desc = resp.data;

                // set module icon
                self.modules[module].icon = 'bookmark';
                if( resp.data.icon ) {
                    self.modules[module].icon = resp.data.icon;
                }

                // module "has config" flag
                self.modules[module].hasConfig = Object.keys(resp.data.config).length!==0;

                // load module global objects (components, widgets and services)
                files = self.__getModuleGlobalFiles(module, resp.data);
                if( files.js.length===0 && files.html.length===0 ) {
                    // no file to lazyload, stop chain here
                    return $q.reject('stop-chain');
                };

                // load css files asynchronously (no further process needed)
                if( files.css.length>0 ) {
                    self.__loadCssFiles(files.css);
                }

                // load html files
                return self.__loadHtmlFiles(modulePath, files.html);

            }, function(err) {
                // save empty desc for module
                self.modules[module].desc = {};

                // and reject promise
                console.error('Error occured loading "' + module + '" description file', err);

                // reject final promise
                return $q.reject('stop-chain');
            })
            .then(function(resp) {
                // load js files
                return self.__loadJsFiles(files.js);

            }, function(err) {
                if( err!='stop-chain' ) {
                    // error occured during html or css files loading
                    console.error('Error loading modules html files:', err);
                } else {
                    return $q.reject('stop-chain');
                }
            })
            .then(function() {
                // force getting service from injector to make them executed as soon as possible
                for( var i=0; i<files.js.length; i++ ) {
                    if( files.js[i].indexOf('service')>=0 ) {
                        // guess service name from filename
                        serviceName = files.js[i].replace(/^.*[\\\/]/, '');
                        serviceName = serviceName.replace('.js', '');
                        serviceName = self.__camelize(serviceName);

                        // make sure
                        if( $injector.has(serviceName) ) {
                            $injector.get(serviceName, function(err) {
                                console.error('Error occured during service loading:', err)
                            });
                        }
                    }
                }

            }, function(err) {
                if( err!='stop-chain' ) {
                    // error occured during js files loading
                    console.error('Error loading modules js files:', err);
                } else {
                    return $q.reject('stop-chain');
                }
            })
            .then(function() {
                // all chain was good
                d.resolve();
            },
            function(err) {
                // error occured during chain but resolve chain otherwise devices can be loaded properly
                d.resolve();
            });

        return d.promise;
    };

    /**
     * Return module description (desc.json file content)
     * @return promise<json|null>
     */
    self.getModuleDescription = function(module) {
        // init
        var deferred = $q.defer();

        if( self.__deferredModules===null ) {
            // module config already loaded, resolve it if available
            if( self.modules[module] ) {
                deferred.resolve(self.modules[module].desc);
            } else {
                console.error('Unable to get description of unknown module "' + module + '"');
                deferred.reject(null);
            }
        }
        else {
            // module not loaded, wait for it
            self.__deferredModules.promise
                .then(function() {
                    if( self.modules[module] ) {
                        deferred.resolve(self.modules[module].desc);
                    } else {
                        deferred.reject('Module "' + module + '" does not exist');
                    }
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
    self._setModules = function(modules) {
        // save modules
        self.modules = modules;

        // load description for each local modules
        var promises = [];
        for( module in self.modules ) {
            if( (self.modules[module].installed && self.modules[module].started) || self.modules[module].library ) {
                promises.push(self.__loadModule(module));
            }
        }

        // resolve deferred once all promises terminated
        // TODO sequentially chain promises https://stackoverflow.com/a/43543665 or https://stackoverflow.com/a/24262233
        // $q.all executes final statement as soon as one of promises is rejected
        return $q.all(promises)
            .then(function(resp) {
            }, function(err) {
                // necessary to avoid rejection warning
            })
            .finally(function() {
                // no deferred during reboot/restart, handle this case
                if( self.__deferredModules ) {
                    self.__deferredModules.resolve();
                    self.__deferredModules = null;
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

        if( self.__deferredModules===null ) {
            // module config already loaded, resolve it if available
            if( self.modules[module] ) {
                deferred.resolve(self.modules[module].config);
            } else {
                console.error('Specified module "' + module + '" has no configuration');
                deferred.reject();
            }
        } else {
            // module not loaded, wait for it
            self.__deferredModules.promise
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
        var deferred = $q.defer();

        if( self.modules[module] ) {
            rpcService.sendCommand('get_module_config', module, null, 30)
                .then(function(resp) {
                    if( resp.error===false ) {
                        // save new config
                        self.modules[module].config = resp.data;
                        deferred.resolve(resp.data);
                    } else {
                        console.error(resp.message);
                        toast.error(resp.message);
                        deferred.reject(resp.message);
                    }
                }, function(err) {
                    // error occured
                    toast.error('Unable to reload module "' + module + '" configuration');
                    console.error('Unable to reload module "' + module + '" configuration', err);
                    deferred.reject(err);
                });
        } else {
            console.error('Specified module "' + module + '" has no configuration');
            deferred.reject('module has no config');
        }

        return deferred.promise;
    };

    /**
     * Get list of installable modules
     */
    self.getInstallableModules = function()
    {
        var deferred = $q.defer();

        if( Object.keys(self.installableModules).length>0 ) {
            deferred.resolve(self.installableModules);
        } else {
            // installable modules not loaded, load it
            rpcService.getModules(true)
                .then(function(modules) {
                    self.__syncObject(self.installableModules, modules);
                }, function() {
                    deferred.reject();
                });
        }

        return deferred.promise;
    };

    /**
     * Refresh modules updates infos
     * Use cleepService.modulesUpdates to follow changes
     */
    self.refreshModulesUpdates = function() {
        rpcService.sendCommand('get_modules_updates', 'update')
            .then(function(resp) {
                if(!resp.error) {
                    self.__syncObject(self.modulesUpdates, resp.data);
                }
            });
    };

    /**
     * Set devices
     * Prepare dashboard widgets and init device using associated module
     */
    self._setDevices = function(devices)
    {
        var newDevices = [];
        for( var module in devices ) {
            // add specific ui stuff
            for( var uuid in devices[module] ) {
                // add widget infos
                devices[module][uuid].__widget = {
                    mdcolors: '{background:"default-primary-300"}'
                };

                // add module which handles this device
                devices[module][uuid].module = module;
                // add if widget is hidden or not
                devices[module][uuid].hidden = self.modules[module].library ? true : false;
            }

            // store device
            for( var uuid in devices[module] ) {
                newDevices.push(devices[module][uuid]);
            }
        }

        // clear existing devices
        for( var i=self.devices.length-1; i>=0; i--) {
            self.devices.splice(i, 1);
        }

        // save new devices
        for( var i=0; i<newDevices.length; i++ ) {
            self.devices.push(newDevices[i]);
        }
    };

    /**
     * Reload devices
     * Call getDevices command again and set devices
     */
    self.reloadDevices = function() {
        var deferred = $q.defer();

        rpcService.getDevices()
            .then(function(devices) {
                self._setDevices(devices);
                deferred.resolve(self.devices);
            }, function() {
                deferred.reject();
            });
        
        return deferred.promise;
    };

    /**
     * Set renderers
     * Just set renderers list
     */
    self._setRenderers = function(renderers) {
        self.renderers = renderers;
        // no deferred during reboot/restart, handle this case
        if( self.__deferredRenderers ) {
            self.__deferredRenderers.resolve();
            self.__deferredRenderers = null;
        }
    };

    /**
     * Get renderers
     * @return promise
     */
    self.getRenderers = function() {
        var deferred = $q.defer();

        if( self.__deferredRenderers===null ) {
            // renderers already loaded, return collection
            deferred.resolve(self.renderers);
        } else {
            self.__deferredRenderers.promise
                .then(function() {
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
    self._setEvents = function(events) {
        self.events = events;
        // no deferred during reboot/restart, handle this case
        if( self.__deferredEvents ) {
            self.__deferredEvents.resolve();
            self.__deferredEvents = null;
        }
    };

    /**
     * Get events
     * @return promise
     */
    self.getEvents = function() {
        var deferred = $q.defer();

        if( self.__deferredEvents===null ) {
            // events already loaded, return collection
            deferred.resolve(self.events);
        } else {
            self.__deferredEvents.promise
                .then(function() {
                    deferred.resolve(self.events);
                }, function() {
                    deferred.reject();
                });
        }

        return deferred.promise;
    };

    /**
     * Set drivers
     * Just set drivers list
     */
    self._setDrivers = function(drivers) {
        self.drivers = drivers;
        // no deferred during reboot/restart, handle this case
        if( self.__deferredDrivers ) {
            self.__deferredDrivers.resolve();
            self.__deferredDrivers = null;
        }
    };

    /**
     * Get drivers
     * @return promise
     */
    self.getDrivers = function() {
        var deferred = $q.defer();

        if( self.__deferredDrivers===null ) {
            // drivers already loaded, return collection
            deferred.resolve(self.drivers);
        } else {
            self.__deferredDrivers.promise
                .then(function() {
                    deferred.resolve(self.drivers);
                }, function() {
                    deferred.reject();
                });
        }

        return deferred.promise;
    };

    /**
     * Reload drivers
     * Call getDrivers command again and set drivers
     */
    self.reloadDrivers = function() {
        var deferred = $q.defer();

        rpcService.getDrivers()
            .then(function(drivers) {
                self._setDrivers(drivers);
                deferred.resolve(self.drivers);
            }, function() {
                deferred.reject();
            });
        
        return deferred.promise;
    };

    /**
     * Check if specified application is installed
     * @param app: application name (aka module name)
     * @return true if module is loaded, false otherwise
     */
    self.isAppInstalled = function(app) {
        for( var name in self.modules )  {
            if( name===app && self.modules[name].installed ) {
                return true;
            }
        }
        return false;
    };

    /**
     * Returns renderers of specified type
     */
    self.getRenderersOfType = function(type) {
        if( self.renderers[type] ) {
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
     * Reboot device
     * This function calls system module function to avoid adhesion of system service from angular app
     */
    self.reboot = function() {
        if( delay===null || delay===undefined ) {
            delay = 0;
        }
        return rpcService.sendCommand('reboot_device', 'system', {'delay': delay});
    };

    /**
     * Poweroff device
     * This function calls system module function to avoid adhesion of system service from angular app
     */
    self.poweroff = function() {
        if( delay===null || delay===undefined ) {
            delay = 0;
        }
        return rpcService.sendCommand('poweroff_device', 'system', {'delay': delay});
    };

    /**
     * Restart Cleep
     * This function calls system module function to avoid adhesion of system service from angular app
     */
    self.restart = function(delay) {
        if( delay===null || delay===undefined ) {
            delay = 0;
        }
        return rpcService.sendCommand('restart_cleep', 'system', {'delay': delay});
    };

    /**
     * Install module
     * This function calls system module function to avoid adhesion of update service from angular app
     */
    self.installModule = function(module) {
        return rpcService.sendCommand('install_module', 'update', {
            'module_name': module
        });
    };

    /**
     * Uninstall module
     * This function calls system module function to avoid adhesion of update service from angular app
     */
    self.uninstallModule = function(module) {
        return rpcService.sendCommand('uninstall_module', 'update', {
            'module_name': module
        });
    };

    /**
     * Force uninstall module
     * This function calls system module function to avoid adhesion of update service from angular app
     */
    self.forceUninstallModule = function(module) {
        return rpcService.sendCommand('uninstall_module', 'update', {
            'module_name': module,
            'force':true
        });
    };

    /**
     * Update module
     * This function calls system module function to avoid adhesion of update service from angular app
     */
    self.updateModule = function(module) {
        return rpcService.sendCommand('update_module', 'update', {
            'module_name': module
        });
    };

    /**
     * Catch apps updated event
     */
    $rootScope.$on('core.apps.updated', function(event, uuid, params) {
		// refresh list of installable apps
        rpcService.getModules(true)
            .then(function(modules) {
                self.__syncObject(self.installableModules, modules);
            }, function() {
                deferred.reject();
            });
    });

}]);

