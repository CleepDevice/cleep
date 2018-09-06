/**
 * System config directive
 * Handle system configuration
 */
var systemConfigDirective = function($filter, $timeout, $q, toast, systemService, raspiotService, confirm, $mdDialog) {

    var systemController = ['$scope', function($scope)
    {
        var self = this;
        self.systemService = systemService;
        self.tabIndex = 'update';
        self.monitoring = false;
        self.uptime = 0;
        self.needRestart = false;
        self.needReboot = false;
        self.logs = '';
        self.codemirrorInstance = null;
        self.codemirrorOptions = {
            lineNumbers: true,
            tabSize: 2,
            readOnly: true,
            onLoad: function(cmInstance) {
                self.codemirrorInstance = cmInstance;
                cmInstance.focus();
            }
        };
        self.debugs = {};
        self.debugSystem = false;
        self.debugTrace = false;
        self.renderings = [];
        self.eventsNotRendered = [];
        self.raspiotUpdateEnabled = false;
        self.modulesUpdateEnabled = false;
        self.raspiotUpdateAvailable = false;
        self.modulesUpdateAvailable = false;
        self.lastRaspiotUpdate = null;
        self.lastCheckRaspiot = null;
        self.lastCheckModules = null;
        self.version = '';
        self.crashReport = false;
        self.lastModulesInstalls = {};
        self.raspiotUpdatePending = false;
        self.backupDelay = 15;

        /************
         * Update tab
         ************/

        /**
         * Set automatic update
         */
        self.setAutomaticUpdate = function(row)
        {
            //toggle value if row clicked
            if( row==='raspiot' )
            {
                self.raspiotUpdateEnabled = !self.raspiotUpdateEnabled;
            }
            else if( row==='modules' )
            {
                self.modulesUpdateEnabled = !self.modulesUpdateEnabled;
            }

            //perform update
            systemService.setAutomaticUpdate(self.raspiotUpdateEnabled, self.modulesUpdateEnabled)
                .then(function(resp) {
                    if( resp.data===true )
                    {
                        toast.success('New value saved');
                    }
                    else
                    {
                        toast.error('Unable to save new value');
                    }
                });
        };

        /**
         * Check for raspiot updates
         */
        self.checkRaspiotUpdates = function() {
            toast.loading('Checking raspiot update...');
            var message = null;
            systemService.checkRaspiotUpdates()
                .then(function(resp) {
                     
                    if( resp.data.updateavailable===false )
                    {
                        message = 'No update available';
                    }
                    else
                    {
                        message = 'Update available';
                    }

                    //refresh system module config
                    return raspiotService.reloadModuleConfig('system');
                })
                .then(function(config) {
                    //set config
                    self.setConfig(config);
                })
                .finally(function() {
                    if( message )
                    {
                        toast.info(message);
                    }
                });
        };

        /**
         * Check for modules updates
         */
        self.checkModulesUpdates = function() {
            toast.loading('Checking modules updates...');
            var message = null;
            systemService.checkModulesUpdates()
                .then(function(resp) {
                    if( resp.data.updateavailable===false )
                    {
                        message = 'No update available';
                    }
                    else
                    {
                        message = 'Update(s) available. Please check installed modules list in settings';
                    }

                    //refresh system module config
                    return raspiotService.reloadModuleConfig('system');
                })
                .then(function(config) {
                    //set config
                    self.setConfig(config);
                })
                .finally(function() {
                    if( message )
                    {
                        toast.info(message);
                    }
                })
        };

        /**
         * Close logs dialog
         */
        self.closeDialog = function() {
            $mdDialog.hide();
        };

        /**
         * Show update logs
         */
        self.showLogs = function(ev) {
            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'updateLogsCtl',
                templateUrl: 'logs.directive.html',
                parent: angular.element(document.body),
                targetEvent: ev,
                clickOutsideToClose: true,
                fullscreen: true
            })
            .then(function() {}, function() {});
        };

        /**
         * Update raspiot
         */
        self.updateRaspiot = function() {
            toast.loading('Updating device application...');
            systemService.updateRaspiot();
        };

        /**
         * Refresh config when raspiot update terminated
         */
        $scope.$watch(function() {
            return systemService.raspiotInstallStatus;
        }, function(newValue, oldValue) {
            if( newValue<oldValue ) {
                //update terminated
                raspiotService.reloadModuleConfig('system')
                    .then(function(config) {
                        self.setConfig(config);
                    });
            }
        });

        /**************
         * Backup tab
         **************/

        /**
         * Trigger configuration backup
         */
        self.backupConfiguration = function() {
            systemService.backupRaspiotConfig()
                .then(function() {
                    toast.success('Configuration saved');
                });
        };

        /**
         * Set backup config delay
         */
        self.setBackupDelay = function() {
            systemService.setRaspiotBackupDelay(Number(self.backupDelay))
                .then(function() {
                    toast.success('Delay saved');
                });
        };

        /**
         * Set filesystem protection
         */
        self.setFilesystemProtection = function() {
            //TODO
        };

        /**************
         * Advanced tab
         **************/

        /**
         * Save monitoring
         */
        self.updateMonitoring = function(fromCheckbox) {
            if( !fromCheckbox )
            {
                //row clicked, we need to update flag
                self.monitoring = !self.monitoring;
            }

            //delay update to make sure model value is updated
            $timeout(function() {
                systemService.setMonitoring(self.monitoring)
                    .then(function(resp) {
                        return raspiotService.reloadModuleConfig('system');
                    })
                    .then(function(config) {
                        //set config
                        self.setConfig(config);
                    })
                    .finally(function() {
                        //user message
                        toast.success('Monitoring updated');
                    });
            }, 250);
        };

        /**
         * Save crash report
         */
        self.updateCrashReport = function(fromCheckbox) {
            if( !fromCheckbox )
            {
                //row clicked, we need to update flag
                self.crashReport = !self.crashReport;
            }

            //delay update to make sure model value is updated
            $timeout(function() {
                systemService.setCrashReport(self.crashReport)
                    .then(function(resp) {
                        return raspiotService.reloadModuleConfig('system');
                    })
                    .then(function(config) {
                        //set config
                        self.setConfig(config);
                    })
                    .finally(function() {
                        //user message
                        if( self.crashReport )
                        {
                            toast.success('Crash report enabled');
                        }
                        else
                        {
                            toast.success('Crash report disabled');
                        }
                    });
            }, 250);
        };


        /**
         * Reboot system
         */
        self.reboot = function() {
            confirm.open('Confirm device reboot?', null, 'Reboot device')
                .then(function() {
                    return systemService.reboot();
                })
                .then(function() {
                    toast.success('System will reboot');
                });
        };

        /**
         * Halt system
         */
        self.halt = function() {
            confirm.open('Confirm device shutdown?', null, 'Halt device')
                .then(function() {
                    systemService.halt();
                })
                .then(function() {
                    toast.success('System will halt');
                });
        };

        /**
         * Restart raspiot
         */
        self.restart = function() {
            confirm.open('Confirm application restart?', null, 'Restart software')
                .then(function() {
                    systemService.restart();
                })
                .then(function() {
                    toast.success('Software will restart');
                });
        };

        
        /************
         * Renderings
         ************/

        /**
         * Update renderings
         */
        self.updateRendering = function(rendering, fromCheckbox) {
            if( !fromCheckbox )
            {
                //row clicked, we need to update flag
                rendering.disabled = !rendering.disabled;
            }

            //update events not rendered status
            $timeout(function() {
                systemService.setEventNotRendered(rendering.renderer, rendering.event, rendering.disabled)
                    .then(function(resp) {
                        return raspiotService.reloadModuleConfig('system');
                    })
                    .then(function(config) {
                        //set config
                        self.setConfig(config);
                    });
            }, 250);
        };

        /**
         * Is event not rendered ?
         * @param renderer: renderer name
         * @param event: event name
         * @return: true if event is not rendered, false otherwise
         */
        self._isEventNotRendered = function(renderer, event)
        {
            for( var i=0; i<self.eventsNotRendered.length; i++ )
            {
                if( self.eventsNotRendered[i].renderer===renderer && self.eventsNotRendered[i].event===event )
                {
                    //found
                    return true;
                }
            }

            return false;
        };

        /**
         * Init useable renderings list
         * @param events: list of events
         * @param renderers: list of renderers
         */
        self._initRenderings = function(events, renderers)
        {
            //prepare renderings list
            //for each renderer search handled events via profile matching
            for( var renderer in renderers )
            {
                for( i=0; i<renderers[renderer].length; i++ )
                {
                    var renderer_profile = renderers[renderer][i];
                    for( var event in events )
                    {
                        for( var j=0; j<events[event]['profiles'].length; j++ )
                        {
                            var event_profile = events[event]['profiles'][j];
                            if( event_profile===renderer_profile )
                            {
                                //match found, save new entry
                                self.renderings.push({
                                    'renderer': renderer,
                                    'event': event,
                                    'disabled': self._isEventNotRendered(renderer, event)
                                });
                                break;
                            }
                        }
                    }
                }
            }
        };

        /******************
         * Troubleshoot tab
         ******************/

        /**
         * Download logs
         */
        self.downloadLogs = function() {
            systemService.downloadLogs();
        };

        /**
         * Get logs
         */
        self.getLogs = function() {
            systemService.getLogs()
                .then(function(resp) {
                    self.logs = resp.data.join('');
                    self.refreshEditor();
                });
        };

        /**
         * Refresh editor
         */
        self.refreshEditor = function()
        {
            self.codemirrorInstance.refresh();
        };

        /**
         * Module debug changed
         */
        self.moduleDebugChanged = function(module)
        {
            systemService.setModuleDebug(module, self.debugs[module].debug);
        };

        /**
         * System debug changed
         */
        self.systemDebugChanged = function()
        {
            systemService.setSystemDebug(self.debugSystem);
        };

        /**
         * Trace changed
         */
        self.traceChanged = function()
        {
            systemService.setTrace(self.debugTrace)
                .then(function() {
                    var message = 'Trace enabled';
                    if( !self.debugTrace )
                        message = 'Trace disabled';
                        
                    toast.success('' + message +'. Please restart application');
                });
        };

        /**
         * Set module config
         */
        self.setConfig = function(config)
        {
            //save data
            self.monitoring = config.monitoring;
            self.uptime = config.uptime;
            self.needRestart = config.needrestart;
            self.needReboot = config.needreboot;
            self.crashReport = config.crashreport;
            self.version = config.version;
            self.eventsNotRendered = config.eventsnotrendered;
            self.debugSystem = config.debug.system;
            self.debugTrace = config.debug.trace;
            self.lastCheckRaspiot = config.lastcheckraspiot;
            self.lastCheckModules = config.lastcheckmodules;
            self.raspiotUpdateEnabled = config.raspiotupdateenabled;
            self.modulesUpdateEnabled = config.modulesupdateenabled;
            self.raspiotUpdateAvailable = config.raspiotupdateavailable;
            self.modulesUpdateAvailable = config.modulesupdateavailable;
            self.lastRaspiotUpdate = config.lastraspiotupdate;
            self.lastRaspiotUpdate.stdoutStr = config.lastraspiotupdate.stdout.join('\n');
            self.lastRaspiotUpdate.stderrStr = config.lastraspiotupdate.stderr.join('\n');
            self.lastModulesInstalls = config.lastmodulesinstalls;
            self.raspiotUpdatePending = config.raspiotupdatepending;
            self.backupDelay = config.raspiotbackupdelay;
        };

        /**
         * Init controller
         */
        self.init = function()
        {
            //init
            $q.all([raspiotService.getEvents(), raspiotService.getRenderers()])
                .then(function(resps) {
                    self._initRenderings(resps[0], resps[1]);

                    //get system config
                    return raspiotService.getModuleConfig('system');
                })
                .then(function(config) {
                    //set module config
                    self.setConfig(config);
                    
                    //request for modules debug status
                    return raspiotService.getModulesDebug();
                })
                .then(function(debug) {
                    self.debugs = debug.data;
                });
        };

    }];

    var systemLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'system.directive.html',
        replace: true,
        scope: true,
        controller: systemController,
        controllerAs: 'systemCtl',
        link: systemLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('systemConfigDirective', ['$filter', '$timeout', '$q', 'toastService', 'systemService', 'raspiotService', 'confirmService', '$mdDialog', systemConfigDirective]);

