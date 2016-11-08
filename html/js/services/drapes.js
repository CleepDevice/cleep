/**
 * Drapes service
 * Handle drapes module requests
 */
var drapesService = function($q, rpcService, objectsService) {
    var self = this;
    
    /** 
     * Set configuration directive names
     */
    self.setConfigs = function() {
        objectsService.addConfig('Drapes', 'drapesConfigDirective');
    };

    /**
     * Load service devices (here drapes)
     */
    self.loadDevices = function() {
        rpcService.sendCommand('get_devices', 'drapes')
            .then(function(resp) {
                objectsService.addDevices('drapes', resp.data);
            }, function(err) {
                console.log('loadDevices', err);
            });
    };

    /**
     * Return template name according to gpio mode
     */
    self.getObjectTemplateName = function(object) {
        /*if( object.mode==='in') 
        {
            return 'gpioInput';
        }
        return 'gpioOutput';*/
        return object.__type;
    };

    /**
     * Return raspi gpios (according to board version)
     */
    self.getRaspiGpios = function() {
        return rpcService.sendCommand('get_raspi_gpios', 'gpios')
        .then(function(resp) {
            return resp.data;
        }, function(err) {
            console.log('getRaspiGpios:', err);
        });
    };

    /**
     * Add new drape
     */
    self.addDrape = function(name, drape_open, drape_close, delay, switch_open, switch_close) {
        return rpcService.sendCommand('add_drape', 'drapes', 
                {'name':name, 'drape_open':drape_open, 'drape_close':drape_close, 'delay':delay, 'switch_open':switch_open, 'switch_close':switch_close})
        .then(function(resp) {
        }, function(err) {
            console.log('addDrape:', err);
        })
    };

    /**
     * Delete drape
     */
    self.delDrape = function(name) {
        return rpcService.sendCommand('del_drape', 'drapes', {'name':name})
        .then(function(resp) {
        }, function(err) {
            console.log('delDrape:', err);
        })
    };

    /**
     * Open drape
     */
    self.openDrape = function(name) {
        console.log('open drape', name);
        return rpcService.sendCommand('open_drape', 'drapes', {'name':name})
        .then(function(resp) {
            return resp.data;
        }, function(err) {
            console.log('openDrape:', err);
        });
    };

    /**
     * Close drape
     */
    self.closeDrape = function(name) {
        return rpcService.sendCommand('close_drape', 'drapes', {'name':name})
        .then(function(resp) {
            return resp.data;
        }, function(err) {
            console.log('closeDrape:', err);
        });
    };
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('drapesService', ['$q', 'rpcService', 'objectsService', drapesService]);

