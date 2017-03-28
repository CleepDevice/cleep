/**
 * Shutters service
 * Handle shutters module requests
 */
var shuttersService = function($q, $rootScope, rpcService, objectsService) {
    var self = this;
    
    /** 
     * Return directive infos
     */
    self.getDirectiveInfos = function() {
        return {
            label: 'Shutters',
            name: 'shuttersConfigDirective'
        };  
    }; 

    /**
     * Load service devices (here shutter)
     */
    self.loadDevices = function() {
        rpcService.sendCommand('get_devices', 'shutters')
            .then(function(resp) {
                objectsService.addDevices('shutters', resp.data, 'shutter');
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
        return rpcService.sendCommand('add_shutter', 'shutters', 
                {'name':name, 'shutter_open':shutter_open, 'shutter_close':shutter_close, 'delay':delay, 'switch_open':switch_open, 'switch_close':switch_close})
        .then(function(resp) {
        }, function(err) {
            console.log('addShutter:', err);
        });
    };

    /**
     * Delete shutter
     */
    self.deleteShutter = function(name) {
        return rpcService.sendCommand('delete_shutter', 'shutters', {'name':name})
            .then(function(resp) {
            }, function(err) {
                console.log('deleteShutter:', err);
            });
    };

    /**
     * Open shutter
     */
    self.openShutter = function(device) {
        return rpcService.sendCommand('open_shutter', 'shutters', {'name':device['name']})
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
        return rpcService.sendCommand('close_shutter', 'shutters', {'name':device['name']})
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
        return rpcService.sendCommand('stop_shutter', 'shutters', {'name':device['name']})
            .then(function(resp) {
                return resp.data;
            }, function(err) {
                console.log('stopShutter:', err);
            });
    };

    /**
     * Catch shutter opening event
     */
    $rootScope.$on('shutters.shutter.opening', function(event, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].__serviceName==='shutters' )
            {
                if( objectsService.devices[i].name===params.shutter )
                {
                    objectsService.devices[i].status = 'opening'
                    objectsService.devices[i].lastupdate = params.lastupdate;
                    objectsService.devices[i].widget.mdcolors = '{background:"default-accent-400"}';
                    break;
                }
            }
        }
    });
    /**
     * Catch shutter closing event
     */
    $rootScope.$on('shutters.shutter.closing', function(event, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].__serviceName==='shutters' )
            {
                if( objectsService.devices[i].name===params.shutter )
                {
                    objectsService.devices[i].status = 'closing'
                    objectsService.devices[i].lastupdate = params.lastupdate;
                    objectsService.devices[i].widget.mdcolors = '{background:"default-accent-400"}';
                    break;
                }
            }
        }
    });
    /**
     * Catch shutter opened event
     */
    $rootScope.$on('shutters.shutter.opened', function(event, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].__serviceName==='shutters' )
            {
                if( objectsService.devices[i].name===params.shutter )
                {
                    objectsService.devices[i].status = 'opened'
                    objectsService.devices[i].lastupdate = params.lastupdate;
                    objectsService.devices[i].widget.mdcolors = '{background:"default-primary-300"}';
                    break;
                }
            }
        }
    });
    /**
     * Catch shutter closed event
     */
    $rootScope.$on('shutters.shutter.closed', function(event, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].__serviceName==='shutters' )
            {
                if( objectsService.devices[i].name===params.shutter )
                {
                    objectsService.devices[i].status = 'closed'
                    objectsService.devices[i].lastupdate = params.lastupdate;
                    objectsService.devices[i].widget.mdcolors = '{background:"default-primary-300"}';
                    break;
                }
            }
        }
    });
    /**
     * Catch shutter partial event
     */
    $rootScope.$on('shutters.shutter.partial', function(event, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].__serviceName==='shutters' )
            {
                if( objectsService.devices[i].name===params.shutter )
                {
                    objectsService.devices[i].status = 'partial'
                    objectsService.devices[i].lastupdate = params.lastupdate;
                    objectsService.devices[i].widget.mdcolors = '{background:"default-primary-300"}';
                    break;
                }
            }
        }
    });
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('shuttersService', ['$q', '$rootScope', 'rpcService', 'objectsService', shuttersService]);

