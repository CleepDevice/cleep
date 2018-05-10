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
        self.automaticUpdate = false;
        self.status = 0;

        /**
         * Check for updates
         */
        self.checkUpdates = function() {
            toast.loading('Checking update...');
            var message = '';
            updateService.checkUpdates()
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
                    self.lastCheck = resp.data.last_check;
                })
                .finally(function() {
                    toast.info(message);
                });
        };

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
        self.setAutomaticUpdate = function(automaticUpdate) {
            updateService.setAutomaticUpdate(automaticUpdate)
                .then(function(resp) {
                    if( resp.data===true )
                    {
                        toast.success('Automatic update saved');
                    }
                    else
                    {
                        toast.error('Unable to save automatic update');
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

            console.log(self.stdout);

            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'updateLogsCtl',
                templateUrl: 'js/configuration/update/logs.html',
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
                    console.log(config);
                    //save data
                    self.stdout = config.data.last_stdout;
                    self.stderr = config.data.last_stderr;
                    self.version = config.data.version;
                    self.lastUpdate = config.data.last_update;
                    self.lastCheck = config.data.last_check;
                    self.automaticUpdate = config.data.automatic_update;
                    self.status = config.data.status;
                });


        };

        /**
         * Catch update events
         */
        $rootScope.$on('update.status.update', function(event, uuid, params) {
            console.log(event, uuid, params);
            self.status = params.status;
            self.downloadPercent = params.download_percent;
            self.downloadFilesize = params.download_filesize;
        });

    }];

    var updateLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'js/configuration/update/update.html',
        replace: true,
        scope: true,
        controller: updateController,
        controllerAs: 'updateCtl',
        link: updateLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('updateConfigDirective', ['toastService', 'updateService', 'raspiotService', '$mdDialog', 'confirmService', updateConfigDirective]);

