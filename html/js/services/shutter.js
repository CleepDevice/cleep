/**
 * Shutter service
 * Handle shutter module requests
 */
var shutterService = function($q, $rootScope, rpcService, objectsService) {
    var self = this;
    
    /** 
     * Set configuration directive names
     */
    self.setConfigs = function() {
        objectsService.addConfig('Shutter', 'shutterConfigDirective');
    };

    /**
     * Load service devices (here shutter)
     */
    self.loadDevices = function() {
        rpcService.sendCommand('get_devices', 'shutter')
            .then(function(resp) {
                objectsService.addDevices('shutter', resp.data);
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
     * Add new shutter
     */
    self.addShutter = function(name, shutter_open, shutter_close, delay, switch_open, switch_close) {
        return rpcService.sendCommand('add_shutter', 'shutter', 
                {'name':name, 'shutter_open':shutter_open, 'shutter_close':shutter_close, 'delay':delay, 'switch_open':switch_open, 'switch_close':switch_close})
        .then(function(resp) {
        }, function(err) {
            console.log('addShutter:', err);
        })
    };

    /**
     * Delete shutter
     */
    self.delShutter = function(name) {
        return rpcService.sendCommand('del_shutter', 'shutter', {'name':name})
        .then(function(resp) {
        }, function(err) {
            console.log('delShutter:', err);
        })
    };

    /**
     * Open shutter
     */
    self.openShutter = function(device) {
        return rpcService.sendCommand('open_shutter', 'shutter', {'name':device['name']})
        .then(function(resp) {
            return resp.data;
        }, function(err) {
            console.log('openShutter:', err);
        });
    };

    /**
     * Close shutter
     */
    self.closeShutter = function(device) {
        return rpcService.sendCommand('close_shutter', 'shutter', {'name':device['name']})
        .then(function(resp) {
            return resp.data;
        }, function(err) {
            console.log('closeShutter:', err);
        });
    };

    /**
     * Stop shutter
     */
    self.stopShutter = function(device) {
        return rpcService.sendCommand('stop_shutter', 'shutter', {'name':device['name']})
        .then(function(resp) {
            return resp.data;
        }, function(err) {
            console.log('stopShutter:', err);
        });
    };

    /**
     * Catch shutter opening event
     */
    $rootScope.$on('event.shutter.opening', function(event, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].__serviceName==='shutter' )
            {
                if( objectsService.devices[i].name===params.shutter )
                {
                    objectsService.devices[i].status = 'opening'
                    break;
                }
            }
        }
    });
    /**
     * Catch shutter closing event
     */
    $rootScope.$on('event.shutter.closing', function(event, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].__serviceName==='shutter' )
            {
                if( objectsService.devices[i].name===params.shutter )
                {
                    objectsService.devices[i].status = 'closing'
                    break;
                }
            }
        }
    });
    /**
     * Catch shutter opened event
     */
    $rootScope.$on('event.shutter.opened', function(event, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].__serviceName==='shutter' )
            {
                if( objectsService.devices[i].name===params.shutter )
                {
                    objectsService.devices[i].status = 'opened'
                    break;
                }
            }
        }
    });
    /**
     * Catch shutter closed event
     */
    $rootScope.$on('event.shutter.closed', function(event, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].__serviceName==='shutter' )
            {
                if( objectsService.devices[i].name===params.shutter )
                {
                    objectsService.devices[i].status = 'closed'
                    break;
                }
            }
        }
    });
    /**
     * Catch shutter partial event
     */
    $rootScope.$on('event.shutter.partial', function(event, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].__serviceName==='shutter' )
            {
                if( objectsService.devices[i].name===params.shutter )
                {
                    objectsService.devices[i].status = 'partial'
                    break;
                }
            }
        }
    });
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('shutterService', ['$q', '$rootScope', 'rpcService', 'objectsService', shutterService]);

