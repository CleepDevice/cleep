/**
 * System config directive
 * Handle system configuration
 */
var systemConfigDirective = function($filter, $timeout, $q, toast, systemService, raspiotService, confirm) {

    var systemController = ['$scope', function($scope)
    {
        var self = this;
        self.tabIndex = 'general';
        self.sunset = null;
        self.sunrise = null;
        self.city = null;
        self.country = '';
        self.monitoring = false;
        self.logs = '';
        self.hostname = '';
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
        self.renderings = [];
        self.eventsNotRendered = [];

        /*************
         * General tab
         *************/

        /**
         * Set city
         */
        self.setCity = function() {
            toast.loading('Updating city...');
            systemService.setCity(self.city, self.country)
                .then(function(resp) {
                    return raspiotService.reloadModuleConfig('system');
                })
                .then(function(config) {
                    toast.success('City updated');
                    self.city = config.city.city;
                    self.country = config.city.country;
                    self.sunset = $filter('hrTime')(config.sun.sunset);
                    self.sunrise = $filter('hrTime')(config.sun.sunrise);
                });
        };

        /**
         * Set hostname
         */
        self.setHostname = function()
        {
            systemService.setHostname(self.hostname)
                .then(function(resp) {
                    return raspiotService.reloadModuleConfig('system');
                })
                .then(function() {
                    toast.success('Device name saved');
                });
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
                    .then(function(resp) {
                        toast.success('Monitoring updated');
                    });
            }, 250);
        };

        /**
         * Reboot system
         */
        self.reboot = function() {
            confirm.open('Confirm device reboot?', null, 'Reboot')
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
            confirm.open('Confirm device shutdown?', null, 'Reboot')
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
            confirm.open('Confirm application restart?', null, 'Reboot')
                .then(function() {
                    systemService.restart();
                })
                .then(function() {
                    toast.success('Raspiot will restart');
                });
        };

        
        /************
         * Renderings
         ************/

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
                    });
            }, 250);
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
                    self.logs = resp.data;
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
         * Debug changed
         */
        self.debugChanged = function(module)
        {
            systemService.setModuleDebug(module, self.debugs[module].debug);
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

        /**
         * Init controller
         */
        self.init = function()
        {
            //init
            $q.all([raspiotService.getEvents(), raspiotService.getRenderers()])
                .then(function(resps) {
                    self._initRenderings(resps[0], resps[1]);
                }, 
                function(error) {
                });

            //get system config
            raspiotService.getModuleConfig('system')
                .then(function(config) {
                    //save data
                    self.city = config.city.city;
                    self.country = config.city.country;
                    self.sunset = $filter('hrTime')(config.sun.sunset);
                    self.sunrise = $filter('hrTime')(config.sun.sunrise);
                    self.monitoring = config.monitoring;
                    self.hostname = config.hostname;
                    self.eventsNotRendered = config.eventsnotrendered;

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
        templateUrl: 'js/configuration/system/system.html',
        replace: true,
        scope: true,
        controller: systemController,
        controllerAs: 'systemCtl',
        link: systemLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('systemConfigDirective', ['$filter', '$timeout', '$q', 'toastService', 'systemService', 'raspiotService', 'confirmService', systemConfigDirective]);

