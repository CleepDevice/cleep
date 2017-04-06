/**
 * Main application
 */
var RaspIot = angular.module(
    'RaspIot',
    ['ngMaterial', 'ngAnimate', 'ngMessages', 'ngRoute', 'base64', 'md.data.table', 'nvd3']
);

/**
 * Main application controller
 * It holds some generic stuff like polling request, loaded services...
 */
var mainController = function($rootScope, $scope, $injector, rpcService, objectsService, raspiotService) {

    //handle polling
    var pollingTimeout = 0;
    var nextPollingTimeout = 1;
    var polling = function() {
         rpcService.poll()
            .then(function(response) {
                if( response && response.data && !response.error )
                {
                    //broadcast received message
                    $rootScope.$broadcast(response.data.event, response.data.uuid, response.data.params);
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
            raspiotService._setConfigs(resp);

            //now inject configurations directives
            for( var module in resp)
            {
                //prepare angular service and directive
                var angularService = module + 'Service';
                if( $injector.has(angularService) )
                {
                    //module has service, inject it then add it
                    objectsService._addService(module, $injector.get(angularService));

                    //add module directive
                    directive = objectsService.services[module].getDirectiveInfos();
                    objectsService._addModuleDirective(module, directive['label'], directive['name'] );
                }
                else
                {
                    //module has no associated service
                    console.warn('Module "'+serviceName+'" has no angular service');
                }
            }

            //load devices
            return raspiotService.reloadDevices();
        })
        .finally(function() {
            console.log("DEVICES", raspiotService.devices);
            console.log("SERVICES", objectsService.services);
            console.log("MODULE DIRECTIVES", objectsService.moduleDirectives);
        });

};

RaspIot.controller('mainController', ['$rootScope', '$scope', '$injector', 'rpcService', 'objectsService', 'raspiotService', mainController]);

