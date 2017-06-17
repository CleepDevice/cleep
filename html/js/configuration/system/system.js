/**
 * System config directive
 * Handle system configuration
 */
var systemConfigDirective = function($filter, $timeout, toast, systemService, raspiotService, confirm) {

    var systemController = ['$scope', function($scope)
    {
        var self = this;
        self.tabIndex = 'general';
        self.sunset = null;
        self.sunrise = null;
        self.city = null;
        self.country = '';
        self.monitoring = false;
        self.logs = '';
        self.hostname = '';
        self.codemirrorInstance = null;
        self.codemirrorOptions = {
            lineNumbers: true,
            tabSize: 2,
            readOnly: true,
            onLoad: function(cmInstance) {
                self.codemirrorInstance = cmInstance;
                cmInstance.focus();
            }
        };
        self.debugs = {};

        /**
         * Set city
         */
        self.setCity = function() {
            toast.loading('Updating city...');
            systemService.setCity(self.city, self.country)
                .then(function(resp) {
                    return raspiotService.reloadModuleConfig('system');
                })
                .then(function(config) {
                    toast.success('City updated');
                    self.city = config.city.city;
                    self.country = config.city.country;
                    self.sunset = $filter('hrTime')(config.sun.sunset);
                    self.sunrise = $filter('hrTime')(config.sun.sunrise);
                });
        };

        /**
         * Save monitoring
         */
        self.setMonitoring = function() {
            //delay update to make sure model value is updated
            $timeout(function() {
                systemService.setMonitoring(self.monitoring)
                    .then(function(resp) {
                        return raspiotService.reloadModuleConfig('system');
                    })
                    .then(function(resp) {
                        toast.success('Monitoring updated');
                    });
            }, 250);
        };

        /**
         * Reboot system
         */
        self.reboot = function() {
            confirm.open('Confirm device reboot?', null, 'Reboot')
                .then(function() {
                    return systemService.reboot();
                })
                .then(function() {
                    toast.success('System will reboot');
                });
        };

        /**
         * Halt system
         */
        self.halt = function() {
            confirm.open('Confirm device shutdown?', null, 'Reboot')
                .then(function() {
                    systemService.halt();
                })
                .then(function() {
                    toast.success('System will halt');
                });
        };

        /**
         * Restart raspiot
         */
        self.restart = function() {
            confirm.open('Confirm application restart?', null, 'Reboot')
                .then(function() {
                    systemService.restart();
                })
                .then(function() {
                    toast.success('Raspiot will restart');
                });
        };

        /**
         * Download logs
         */
        self.downloadLogs = function() {
            systemService.downloadLogs();
        };

        /**
         * Get logs
         */
        self.getLogs = function() {
            systemService.getLogs()
                .then(function(resp) {
                    self.logs = resp.data;
                    self.refreshEditor();
                });
        };

        /**
         * Refresh editor
         */
        self.refreshEditor = function()
        {
            self.codemirrorInstance.refresh();
        };

        /**
         * Debug changed
         */
        self.debugChanged = function(module)
        {
            systemService.setModuleDebug(module, self.debugs[module].debug);
        };

        /**
         * Set hostname
         */
        self.setHostname = function()
        {
            systemService.setHostname(self.hostname)
                .then(function(resp) {
                    return raspiotService.reloadModuleConfig('system');
                })
                .then(function() {
                    toast.success('Device name saved');
                });
        };

        /**
         * Init controller
         */
        self.init = function()
        {
            raspiotService.getModuleConfig('system')
                .then(function(config) {
                    //save data
                    self.city = config.city.city;
                    self.country = config.city.country;
                    self.sunset = $filter('hrTime')(config.sun.sunset);
                    self.sunrise = $filter('hrTime')(config.sun.sunrise);
                    self.monitoring = config.monitoring;
                    self.hostname = config.hostname;

                    //request for modules debug status
                    return raspiotService.getModulesDebug();
                })
                .then(function(debug) {
                    self.debugs = debug.data;
                });
        };

    }];

    var systemLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'js/configuration/system/system.html',
        replace: true,
        scope: true,
        controller: systemController,
        controllerAs: 'systemCtl',
        link: systemLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('systemConfigDirective', ['$filter', '$timeout', 'toastService', 'systemService', 'raspiotService', 'confirmService', systemConfigDirective]);

