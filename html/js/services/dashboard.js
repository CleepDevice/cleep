/**
 * Dashboard service
 * Helper to handle dashboard widgets
 */
var dashboardService = function($rootScope) {
    var self = this;
    
    /**
     * Return raspi gpios (according to board version)
     */
    /*self.getRaspiGpios = function() {
        return rpc.sendCommand('get_raspi_gpios', 'gpios')
        .then(function(resp) {
            return resp.data;
        }, function(err) {
            console.log('gpios.getRaspiGpios:', err);
        });
    };*/

    /**
     * Add widget to dashboard
     */
    self.addWidget = function(id, type) {
        $rootScope.$emit('dashboard.widget.add', {'id':id, 'type':type});
    };

    /**
     * Remove widget from dashboard
     */
    self.removeWidget = function(id) {
        $rootScope.$emit('dashboard.widget.remove', {'id':id});
    };
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('dashboardService', ['$rootScope', dashboardService]);

