/**
 * Main application
 */
var RaspIot = angular.module(
    'RaspIot',
    ['ngMaterial', 'ngAnimate', 'ngMessages', 'ngRoute', 'base64', 'md.data.table', 'nvd3', 'blockUI']
);

/**
 * Main application controller
 * It holds some generic stuff like polling request, loaded services...
 */
var mainController = function($rootScope, $scope, $injector, rpcService, objectsService, raspiotService, blockUI, toast) {

    //handle polling
    var pollingTimeout = 0;
    var nextPollingTimeout = 1;
    var reboot = false;
    var polling = function() {
         rpcService.poll()
            .then(function(response) {
                if( reboot )
                {
                    //system has started
                    toast.success('System has rebooted.');
                    reboot = false;
                    blockUI.stop();
                }

                if( response && response.data && !response.error )
                {
                    if( response.data.event.startsWith('system.system.') )
                    {
                        //handle system events
                        if( response.data.event.endsWith('reboot') )
                        {
                            reboot = true;
                            blockUI.start('System is rebooting. It might take some time.');
                        }
                        else if( response.data.event.endsWith('restart') )
                        {
                            reboot = true;
                            blockUI.start('System is restarting. Please wait few seconds.');
                        }
                    }
                    else
                    {
                        //broadcast received message
                        $rootScope.$broadcast(response.data.event, response.data.uuid, response.data.params);
                    }
                }

                //reset next polling timeout
                nextPollingTimeout = 1;

                //relaunch polling right now
                window.setTimeout(polling, 0);
            }, 
            function(err) {
                if( !reboot )
                {
                    //error occured, differ next polling
                    nextPollingTimeout *= 2;
                    if( nextPollingTimeout>300 )
                    {
                        //do not exceed polling timeout over 5 minutes
                        nextPollingTimeout /= 2;
                    }
                }
                else
                {
                    //during reboot try every seconds
                    nextPollingTimeout = 1;
                }
                window.setTimeout(polling, nextPollingTimeout*1000);
            });
    };
    window.setTimeout(polling, 0);

    //get server modules and inject services. Finally load devices
    rpcService.getModules()
        .then(function(resp) {

            //now inject configurations directives
            for( var module in resp)
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
            raspiotService._setModules(resp);

            //load devices
            return raspiotService.reloadDevices();
        })
        .finally(function() {
            console.log("DEVICES", raspiotService.devices);
            console.log("SERVICES", objectsService.services);
            console.log("MODULES", raspiotService.modules);
        });

};

RaspIot.controller('mainController', ['$rootScope', '$scope', '$injector', 'rpcService', 'objectsService', 'raspiotService', 'blockUI', 'toastService', mainController]);

