/**
 * Main application
 */
var RaspIot = angular.module(
    'RaspIot',
    ['ngMaterial', 'ngAnimate', 'ngMessages', 'ngRoute', 'base64', 'md.data.table', 'nvd3', 'blockUI', 'ui.codemirror']
);

/**
 * Main application controller
 * It holds some generic stuff like polling request, loaded services...
 */
var mainController = function($rootScope, $scope, $injector, rpcService, objectsService, raspiotService, systemService, blockUI, toast) {

    var self = this;
    self.needRestart = false;
    self.needReboot = false;
    self.rebooting = false;
    self.notConnected = false;
    self.hostname = '';
    self.pollingTimeout = 0;
    self.nextPollingTimeout = 1;

    /**
     * Handle polling
     */
    self.polling = function()
    {
         rpcService.poll()
            .then(function(response) {
                if( self.rebooting )
                {
                    //system has started
                    toast.success('System has rebooted.');
                    self.rebooting = false;
                    self.needRestart = false;
                    self.needReboot = false;

                    //reload system module config
                    raspiotService.reloadModuleConfig();

                    //unblock ui
                    blockUI.stop();
                }
                else if( self.notConnected )
                {
                    //unblock ui
                    blockUI.stop();
                    self.notConnected = false;
                }

                if( response && response.data && !response.error )
                {
                    if( response.data.event.startsWith('system.system.') )
                    {
                        //handle system events
                        if( response.data.event.endsWith('reboot') )
                        {
                            self.rebooting = true;
                            blockUI.start('System is rebooting. It might take some time.');
                        }
                        else if( response.data.event.endsWith('restart') )
                        {
                            self.rebooting = true;
                            blockUI.start('System is restarting. Please wait few seconds.');
                        }
                    }
                    else
                    {
                        //broadcast received message
                        $rootScope.$broadcast(response.data.event, response.data.device_id, response.data.params);
                    }
                }

                //reset next polling timeout
                self.nextPollingTimeout = 1;

                //relaunch polling right now
                window.setTimeout(self.polling, 0);
            }, 
            function(err) {
                if( !self.rebooting )
                {
                    //error occured, differ next polling
                    /*self.nextPollingTimeout *= 2;
                    if( self.nextPollingTimeout>300 )
                    {
                        //do not exceed polling timeout over 5 minutes
                        self.nextPollingTimeout /= 2;
                    }*/
                    self.nextPollingTimeout = 2;

                    //handle connection loss
                    if( err=='Connection problem' && !self.notConnected )
                    {
                        blockUI.message = 'Connection lost with the device.';
                        blockUI.start('Connection lost with the device.');
                        self.notConnected = true;
                    }
                }
                else
                {
                    //during reboot try every seconds
                    self.nextPollingTimeout = 1;
                }
                window.setTimeout(self.polling, self.nextPollingTimeout*1000);
            });
    };

    /**
     * Load all config
     */
    self.loadConfig = function()
    {
        rpcService.getConfig()
            .then(function(config) {
                //inject configurations directives
                for( var module in config.modules )
                {
                    //prepare angular service and directive
                    var angularService = module + 'Service';
                    if( $injector.has(angularService) )
                    {
                        //module has service, inject it then register it
                        objectsService._addService(module, $injector.get(angularService));
                    }
                    else
                    {
                        //module has no associated service
                        console.warn('Module "' + angularService + '" has no angular service');
                    }
                }

                //save modules configurations as soon as possible to make sure
                //configurations directives can access their own configs when they start
                raspiotService._setModules(config.modules);

                //set other stuff
                raspiotService._setDevices(config.devices);
                raspiotService._setRenderers(config.renderers);
                raspiotService._setEvents(config.events);
            })
            .finally(function() {
                console.log('DEVICES', raspiotService.devices);
                console.log('SERVICES', objectsService.services);
                console.log('MODULES', raspiotService.modules);
                console.log('RENDERERS', raspiotService.renderers);
                console.log('EVENTS', raspiotService.events);
            });
    };

    /**
     * Restart raspiot
     */
    self.restart = function()
    {
        systemService.restart();
    };

    /**
     * Reboot raspberry
     */
    self.reboot = function()
    {
        systemService.reboot();
    };

    /**
     * Init main controller
     */
    self.init = function()
    {
        //launch polling
        window.setTimeout(self.polling, 0);

        //load config (modules, devices, renderers...)
        self.loadConfig();
    };
    self.init();

    /**
     * Watch for system config changes to add restart button if restart is needed
     */
    $scope.$watchCollection(
        function() {
            return raspiotService.modules['system'];
        },
        function(newValue) {
            if( !angular.isUndefined(newValue) )
            {
                self.needRestart = newValue.config.needrestart;
                self.needReboot = newValue.config.needreboot;
                self.hostname = newValue.config.hostname;
            }
        }
    );

};

RaspIot.controller('mainController', ['$rootScope', '$scope', '$injector', 'rpcService', 'objectsService', 'raspiotService', 'systemService', 'blockUI', 'toastService', mainController]);

