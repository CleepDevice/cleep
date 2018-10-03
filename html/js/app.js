/**
 * Main application
 */
var RaspIot = angular.module(
    'RaspIot',
    ['ngMaterial', 'ngAnimate', 'ngMessages', 'ngRoute', 'base64', 'md.data.table', 'nvd3', 'blockUI', 'ui.codemirror', 'oc.lazyLoad']
);

/**
 * Main application controller
 * It holds some generic stuff like polling request, loaded services...
 */
var mainController = function($rootScope, $scope, $injector, rpcService, raspiotService, blockUI, toast) {

    var self = this;
    self.rebooting = false;
    self.restarting = false;
    self.notConnected = false;
    self.reloadConfig = false;
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
                message = '';

                if( self.rebooting || self.restarting )
                {
                    //toast message
                    if( self.rebooting )
                    {
                        message = 'Device has rebooted';
                    }
                    else if( self.restarting )
                    {
                        message = 'Application has restarted';
                    }
                    
                    //system has started
                    self.rebooting = false;
                    self.restarting = false;

                    //reload application config
                    self.reloadConfig = true;
                }
                else if( self.notConnected )
                {
                    //unblock ui
                    blockUI.stop();
                    self.notConnected = false;

                    //toast message
                    message = 'Connection with device restored';

                    //reload application config
                    self.reloadConfig = true;
                }

                //reload application config after restart/reboot/connection loss
                if( self.reloadConfig )
                {
                    self.reloadConfig = false;
                    self.loadConfig(false)
                        .then(function() {
                            //toast message
                            if( message && message.length>0 )
                            {
                                toast.success(message);
                            }

                            //unblock ui
                            blockUI.stop();
                    });
                }

                if( response && response.data && !response.error )
                {
                    if( response.data.event.startsWith('system.system.') )
                    {
                        //handle system events
                        if( response.data.event=='system.system.reboot' )
                        {
                            self.rebooting = true;
                            blockUI.start({message:'System is rebooting...', submessage:'Please wait, it might take some time.', spinner:true, icon:null});
                        }
                        else if( response.data.event=='system.system.restart' )
                        {
                            self.restarting = true;
                            blockUI.start({message:'Application is restarting...', submessage:'Please wait few seconds.', spinner:true, icon:null});
                        }
                        else if( response.data.event=='system.system.halt' )
                        {
                            blockUI.start({message:'System is halting.', submessage:'Your device will disconnect in few seconds.', spinner:true, icon:null});
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
                if( !self.rebooting && !self.restarting )
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
                        blockUI.start({message:'Connection lost with the device.', submessage:null, spinner:false, icon:'close-network'});
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
     * @param withBlockUi (bool): enable or not block ui with message "loading data..."
     * @return promise
     */
    self.loadConfig = function(withBlockUi)
    {
        if( withBlockUi===undefined || withBlockUi===null )
        {
            withBlockUi = true;
        }

        //block ui
        if( withBlockUi )
        {
            blockUI.start({message:'Loading data...', submessage:'Please wait', icon:null, spinner:true});
        }

        return raspiotService.loadConfig()
            .finally(function() {
                //unblock ui
                if( withBlockUi )
                {
                    blockUI.stop();
                }

                console.log('DEVICES', raspiotService.devices);
                console.log('MODULES', raspiotService.modules);
                console.log('RENDERERS', raspiotService.renderers);
                console.log('EVENTS', raspiotService.events);
            });
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
     * Watch for parameters config changes to update device hostname
     */
    $scope.$watchCollection(
        function() {
            return raspiotService.modules['parameters'];
        },
        function(newValue) {
            if( !angular.isUndefined(newValue) )
            {
                self.hostname = newValue.config.hostname;
            }
        }
    );

};

RaspIot.controller('mainController', ['$rootScope', '$scope', '$injector', 'rpcService', 'raspiotService', 'blockUI', 'toastService', mainController]);

