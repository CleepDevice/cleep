/**
 * Drapes service
 * Handle drapes module requests
 */
var drapesService = function($q, $rootScope, rpcService, objectsService) {
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
     * Return template name
     */
    self.getObjectTemplateName = function(object) {
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
    self.openDrape = function(device) {
        console.log('open drape', device);
        return rpcService.sendCommand('open_drape', 'drapes', {'name':device['name']})
        .then(function(resp) {
            return resp.data;
        }, function(err) {
            console.log('openDrape:', err);
        });
    };

    /**
     * Close drape
     */
    self.closeDrape = function(device) {
        return rpcService.sendCommand('close_drape', 'drapes', {'name':device['name']})
        .then(function(resp) {
            return resp.data;
        }, function(err) {
            console.log('closeDrape:', err);
        });
    };

    /**
     * Stop drape
     */
    self.stopDrape = function(device) {
        return rpcService.sendCommand('stop_drape', 'drapes', {'name':device['name']})
        .then(function(resp) {
            return resp.data;
        }, function(err) {
            console.log('stopDrape:', err);
        });
    };

    /**
     * Catch drapes opening event
     */
    $rootScope.$on('event.drape.opening', function(event, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].__serviceName==='drapes' )
            {
                if( objectsService.devices[i].name===params.drape )
                {
                    objectsService.devices[i].status = 'opening'
                }
            }
        }
    });
    /**
     * Catch drapes closing event
     */
    $rootScope.$on('event.drape.closing', function(event, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].__serviceName==='drapes' )
            {
                if( objectsService.devices[i].name===params.drape )
                {
                    objectsService.devices[i].status = 'closing'
                }
            }
        }
    });
    /**
     * Catch drapes opened event
     */
    $rootScope.$on('event.drape.opened', function(event, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].__serviceName==='drapes' )
            {
                if( objectsService.devices[i].name===params.drape )
                {
                    objectsService.devices[i].status = 'opened'
                }
            }
        }
    });
    /**
     * Catch drapes closed event
     */
    $rootScope.$on('event.drape.closed', function(event, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].__serviceName==='drapes' )
            {
                if( objectsService.devices[i].name===params.drape )
                {
                    objectsService.devices[i].status = 'closed'
                }
            }
        }
    });
    /**
     * Catch drapes partial event
     */
    $rootScope.$on('event.drape.partial', function(event, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].__serviceName==='drapes' )
            {
                if( objectsService.devices[i].name===params.drape )
                {
                    objectsService.devices[i].status = 'partial'
                }
            }
        }
    });
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('drapesService', ['$q', '$rootScope', 'rpcService', 'objectsService', drapesService]);

