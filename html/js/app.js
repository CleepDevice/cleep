/**
 * Main application
 */
var RaspIot = angular.module(
    'RaspIot',
    ['ngMaterial', 'ngAnimate', 'ngMessages', 'ngRoute', 'base64', 'md.data.table']
);

/**
 * Main application controller
 * It holds some generic stuff like polling request, loaded services...
 */
var mainController = function($rootScope, $scope, $injector, rpcService, objectsService, configsService) {

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
        .then(function(resp) {
            //save modules configurations as soon as possible to make sure
            //configurations directives can access their own configs when they start
            configsService._setConfigs(resp);

            //now inject configurations directives
            for( var module in resp)
            {
                //prepare angular service and directive
                var serviceName = module; //modules[i];
                var angularService = module + 'Service'; //modules[i]+'Service';
                if( $injector.has(angularService) )
                {
                    //module has service, inject it then add it
                    objectsService._addService(serviceName, $injector.get(angularService));

                    //load service devices if possible
                    if( typeof objectsService.services[serviceName].loadDevices !== 'undefined' )
                    {
                        //load service devices
                        objectsService.services[serviceName].loadDevices();
                    }
                    
                    //add module config directives
                    directive = objectsService.services[serviceName].getDirectiveInfos();
                    objectsService._addDirective( directive['label'], directive['name'] );
                }
                else
                {
                    //module has no associated service
                    console.warn('Module "'+serviceName+'" has no angular service');
                }
            }


            //console.log("DEVICES", objectsService.devices);
            //console.log("SERVICES", objectsService.services);
            //console.log("DIRECTIVES", objectsService.directives);
        });

};

RaspIot.controller('mainController', ['$rootScope', '$scope', '$injector', 'rpcService', 'objectsService', 'configsService', mainController]);

