/**
 * OpenWeatherMap service
 * Handle openweathermap module requests
 */
var openweathermapService = function($q, $rootScope, rpcService) {
    var self = this;

    self.setApikey = function(apikey) {
        return rpcService.sendCommand('set_apikey', 'openweathermap', {'apikey':apikey});
    };

    /**
     * Catch openweathermap event
     */
    $rootScope.$on('openweathermap.weather.update', function(event, uuid, params) {

        for( var i=0; i<raspiotService.devices.length; i++ )
        {   
            if( raspiotService.devices[i].uuid===uuid )
            {   
                raspiotService.devices[i].lastupdate = params.lastupdate;
                raspiotService.devices[i].celsius = params.celsius;
                raspiotService.devices[i].fahrenheit = params.fahrenheit;
                raspiotService.devices[i].humidity = params.humidity;
                raspiotService.devices[i].pressure = params.pressure;
                raspiotService.devices[i].wind_speed = params.wind_speed;
                raspiotService.devices[i].wind_direction = params.wind_direction;
                break;
            }   
        }   
    });

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('openweathermapService', ['$q', '$rootScope', 'rpcService', openweathermapService]);

