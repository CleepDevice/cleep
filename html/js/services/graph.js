/**
 * Graph service
 * Handle graph displaying
 */
var graphService = function($q, $rootScope, rpcService) {
    var self = this;
    
    /**
     * Get graph data for specified device
     */
    self.getDeviceData = function(uuid, timestampStart, timestampEnd, options) {
        return rpcService.sendCommand('get_data', 'database', {'uuid':uuid, 'timestamp_start':timestampStart, 'timestamp_end':timestampEnd, 'options':options});
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('graphService', ['$q', '$rootScope', 'rpcService', graphService]);

