var RaspIot = angular.module('RaspIot');

/**
 * Define main application controller
 * It holds some generic stuff like polling request, loaded services...
 */
RaspIot.controller('mainController', ['$rootScope', '$scope', '$injector', 'rpcService', 'objectsService', function($rootScope, $scope, $injector, rpcService, objectsService) {
    //handle polling
    var pollingTimeout = 0;
    var nextPollingTimeout = 1;
    var polling = function() {
         rpcService.poll()
            .then(function(response) {
                if( response && response.data && !response.error )
                {
                    //broadcast received message
                    $rootScope.$broadcast(response.data.event, response.data.params);
                }

                //reset next polling timeout
                nextPollingTimeout = 1;

                //relaunch polling right now
                window.setTimeout(polling, 0);
            },
            function(err) {
                //error occured, differ next polling
                nextPollingTimeout *= 2;
                if( nextPollingTimeout>300 )
                {
                    //do not exceed polling timeout over 5 minutes
                    nextPollingTimeout /= 2;
                }
                window.setTimeout(polling, nextPollingTimeout*1000);
            });
    }
    window.setTimeout(polling, 0);

    //get server modules and inject services. Finally load devices
    rpcService.getModules()
        .then(function(modules) {
            for(var i=0; i<modules.length; i++)
            {
                //service name
                var serviceName = modules[i];
                var angularService = modules[i]+'Service';
                if( $injector.has(angularService) )
                {
                    //module has service, inject and save it
                    objectsService.addService(serviceName, $injector.get(angularService));

                    //load service devices if possible
                    if( typeof objectsService.services[serviceName].loadDevices !== 'undefined' )
                    {
                        //load service devices
                        objectsService.services[serviceName].loadDevices();

                        //set service config directives
                        objectsService.services[serviceName].setConfigs();
                    }

                    //set service config directives
                    objectsService.services[serviceName].setConfigs();
                }
                else
                {
                    //module has no associated service
                }
            }
            console.log("DEVICES", objectsService.devices);
            console.log("SERVICES", objectsService.services);
            console.log("CONFIGS", objectsService.configs);
        });
}]);
