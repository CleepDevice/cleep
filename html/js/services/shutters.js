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
        var defered = $q.defer();
        rpcService.sendCommand('get_module_devices', 'shutters')
            .then(function(resp) {
                objectsService.addDevices('shutters', resp.data, 'shutter');
                defered.resolve('devices loaded');
            }, function(err) {
                console.log('loadDevices', err);
                defered.reject('Unable to load devices');
            });
        return defered.promise;
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
        return rpcService.sendCommand('get_raspi_gpios', 'gpios');
    };

    /**
     * Add new shutter
     */
    self.addShutter = function(name, shutter_open, shutter_close, delay, switch_open, switch_close) {
        return rpcService.sendCommand('add_shutter', 'shutters', {'name':name, 'shutter_open':shutter_open, 'shutter_close':shutter_close, 'delay':delay, 'switch_open':switch_open, 'switch_close':switch_close});
    };

    /**
     * Delete shutter
     */
    self.deleteShutter = function(uuid) {
        return rpcService.sendCommand('delete_shutter', 'shutters', {'uuid':uuid});
    };

    /**
     * Update shutter
     */
    self.updateShutter = function(uuid, name, delay) {
        return rpcService.sendCommand('update_shutter', 'shutters', {'uuid':uuid, 'name':name, 'delay':delay});
    };

    /**
     * Open shutter
     */
    self.openShutter = function(uuid) {
        return rpcService.sendCommand('open_shutter', 'shutters', {'uuid':uuid});
    };

    /**
     * Close shutter
     */
    self.closeShutter = function(uuid) {
        return rpcService.sendCommand('close_shutter', 'shutters', {'uuid':uuid});
    };

    /**
     * Stop shutter
     */
    self.stopShutter = function(uuid) {
        return rpcService.sendCommand('stop_shutter', 'shutters', {'uuid':uuid});
    };

    /**
     * Catch shutter opening event
     */
    $rootScope.$on('shutters.shutter.opening', function(event, uuid, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].uuid==uuid )
            {
                objectsService.devices[i].status = 'opening'
                objectsService.devices[i].lastupdate = params.lastupdate;
                objectsService.devices[i].widget.mdcolors = '{background:"default-accent-400"}';
                break;
            }
        }
    });

    /**
     * Catch shutter closing event
     */
    $rootScope.$on('shutters.shutter.closing', function(event, uuid, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].uuid==uuid )
            {
                objectsService.devices[i].status = 'closing'
                objectsService.devices[i].lastupdate = params.lastupdate;
                objectsService.devices[i].widget.mdcolors = '{background:"default-accent-400"}';
                break;
            }
        }
    });
    /**
     * Catch shutter opened event
     */
    $rootScope.$on('shutters.shutter.opened', function(event, uuid, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].uuid==uuid )
            {
                objectsService.devices[i].status = 'opened'
                objectsService.devices[i].lastupdate = params.lastupdate;
                objectsService.devices[i].widget.mdcolors = '{background:"default-primary-300"}';
                break;
            }
        }
    });
    /**
     * Catch shutter closed event
     */
    $rootScope.$on('shutters.shutter.closed', function(event, uuid, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].uuid==uuid )
            {
                objectsService.devices[i].status = 'closed'
                objectsService.devices[i].lastupdate = params.lastupdate;
                objectsService.devices[i].widget.mdcolors = '{background:"default-primary-300"}';
                break;
            }
        }
    });
    /**
     * Catch shutter partial event
     */
    $rootScope.$on('shutters.shutter.partial', function(event, uuid, params) {
        for( var i=0; i<objectsService.devices.length; i++ )
        {
            if( objectsService.devices[i].uuid==uuid )
            {
                objectsService.devices[i].status = 'partial'
                objectsService.devices[i].lastupdate = params.lastupdate;
                objectsService.devices[i].widget.mdcolors = '{background:"default-primary-300"}';
                break;
            }
        }
    });
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('shuttersService', ['$q', '$rootScope', 'rpcService', 'objectsService', shuttersService]);

