/**
 * OpenWeatherMap service
 * Handle openweathermap module requests
 */
var openweathermapService = function($q, $rootScope, rpcService) {
    var self = this;

    self.setApikey = function(apikey) {
        return rpcService.sendCommand('set_apikey', 'openweathermap', {'apikey':apikey});
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('openweathermapService', ['$q', '$rootScope', 'rpcService', openweathermapService]);

