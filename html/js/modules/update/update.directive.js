/**
 * Update config directive
 * Handle system configuration
 */
var updateConfigDirective = function(toast, updateService, raspiotService, $mdDialog, confirm) {

    var updateController = ['$scope', '$rootScope', function($scope, $rootScope)
    {
        var self = this;
        self.stderr = '';
        self.stdout = '';
        self.version = '';
        self.lastUpdate = null;
        self.lastCheck = null;
        self.raspiotUpdate = false;
        self.modulesUpdate = false;
        self.modules = [];
        self.status = 0;

        /**
         * Check for raspiot updates
         */
        self.checkRaspiotUpdates = function() {
            toast.loading('Checking raspiot update...');
            var message = 'Check update terminated';
            updateService.checkRaspiotUpdates()
                .then(function(resp) {
                    if( resp.data===false )
                    {
                        message = 'No update available.';
                    }
                    else
                    {
                        message = 'New update available, installation will start';
                    }

                    return updateService.getStatus(true);
                })
                .then(function(resp) {
                    self.status = resp.data.status;
                    self.lastCheckRaspiot = resp.data.lastcheckraspiot;
                })
                .finally(function() {
                    toast.info(message);
                });
        };

        /**
         * Check for modules updates
         */
        self.checkModulesUpdates = function() {
            toast.loading('Checking modules updates...');
            var message = 'Check updates terminated';
            updateService.checkModulesUpdates()
                .then(function(resp) {
                    if( resp.data===false )
                    {
                        message = 'No update available';
                    }
                    else
                    {
                        message = 'Update(s) available';
                    }

                    return updateService.getStatus(true);
                })
                .then(function(resp) {
                    /update updatable module flag
                    for( module in resp.data.modules )
                    {
                        self.modules[module].updatable = resp.data.modules[module].updatable;
                    }
                    self.status = resp.data.status;
                    self.lastCheckModules = resp.data.lastcheckmodules;
                })
                .finally(function() {
                    toast.info(message);
                })
        }

        /**
         * Cancel current update
         */
        self.cancelUpdate = function() {
            confirm.open('Cancel update?', null)
                .then(function() {
                    return updateService.cancelUpdate();
                });
        };

        /**
         * Save automatic update
         */
        self.setAutomaticUpdate = function() {
            updateService.setAutomaticUpdate(self.raspiotUpdate, self.modulesUpdate)
                .then(function(resp) {
                    if( resp.data===true )
                    {
                        toast.success('New value saved');
                    }
                    else
                    {
                        toast.error('Unable to save new value');
                    }
                });
        };

        /**
         * Close logs dialog
         */
        self.closeDialog = function() {
            $mdDialog.hide();
        };

        /**
         * Show update logs
         */
        self.showLogs = function(ev) {
            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'updateLogsCtl',
                templateUrl: 'logs.directive.html',
                parent: angular.element(document.body),
                targetEvent: ev,
                clickOutsideToClose: true,
                fullscreen: true
            })
            .then(function() {}, function() {});
        };

        /**
         * Init controller
         */
        self.init = function()
        {
            updateService.getStatus(true)
                .then(function(config) {
                    //save data
                    self.stdout = config.data.laststdout;
                    self.stderr = config.data.laststderr;
                    self.version = config.data.version;
                    self.lastUpdate = config.data.lastupdate;
                    self.lastCheck = config.data.lastcheck;
                    self.raspiotUpdate = config.data.raspiotupdate;
                    self.modulesUpdate = config.data.modulesupdate;
                    self.status = config.data.status;
                    self.modules = config.data.modules;
                });


        };

        /**
         * Catch update events
         */
        $rootScope.$on('update.status.update', function(event, uuid, params) {
            console.log(event, uuid, params);
            self.status = params.status;
            self.downloadPercent = params.downloadpercent;
            self.downloadFilesize = params.downloadfilesize;
        });

    }];

    var updateLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'update.directive.html',
        replace: true,
        scope: true,
        controller: updateController,
        controllerAs: 'updateCtl',
        link: updateLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('updateConfigDirective', ['toastService', 'updateService', 'raspiotService', '$mdDialog', 'confirmService', updateConfigDirective]);

