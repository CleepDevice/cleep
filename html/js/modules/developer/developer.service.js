/**
 * Developer service
 * Handle developer module requests
 */
var developerService = function($q, $rootScope, rpcService, raspiotService) {
    var self = this;

    /**
     * Restart raspiot
     */
    self.restartRaspiot = function() {
        return rpcService.sendCommand('restart_raspiot', 'developer');
    };

    /**
     * Start pyremotedev
     */
    self.startPyremotedev = function() {
        return rpcService.sendCommand('start_pyremotedev', 'developer');
    };

    /**
     * Stop pyremotedev
     */
    self.stopPyremotedev = function() {
        return rpcService.sendCommand('stop_pyremotedev', 'developer');
    };

    /**
     * Analyze module
     */
    self.analyzeModule = function(module) {
        return rpcService.sendCommand('analyze_module', 'developer', {'module':module}, 30);
    };

    /**
     * Generate desc.json file
     */
    self.generateDescJson = function(jsFiles, icon) {
        return rpcService.sendCommand('generate_desc_json', 'developer', {'js_files': jsFiles, 'icon':icon});
    };

    /**
     * Build module package
     */
    self.buildPackage = function(module, data) {
        return rpcService.sendCommand('build_package', 'developer', {'module': module, 'data': data});
    };

    /**
     * Download module package
     */
    self.downloadPackage = function() {
        return rpcService.download('download_package', 'developer');
    };

    /**
     * Catch pyremotedev started events
     */
    $rootScope.$on('developer.pyremotedev.started', function(event, uuid, params) {
        for( var i=0; i<raspiotService.devices.length; i++ )
        {
            if( raspiotService.devices[i].uuid==uuid )
            {
                if( raspiotService.devices[i].running===false )
                {
                    raspiotService.devices[i].running = true;
                    break;
                }
            }
        }
    });

    /**
     * Catch pyremotedev stoped events
     */
    $rootScope.$on('developer.pyremotedev.stopped', function(event, uuid, params) {
        for( var i=0; i<raspiotService.devices.length; i++ )
        {
            if( raspiotService.devices[i].uuid==uuid )
            {
                if( raspiotService.devices[i].running===true )
                {
                    raspiotService.devices[i].running = false;
                    break;
                }
            }
        }
    });
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('developerService', ['$q', '$rootScope', 'rpcService', 'raspiotService', developerService]);

