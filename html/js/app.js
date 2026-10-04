/*global angular*/
/**
 * Main application
 */
var Cleep = angular.module(
    'Cleep',
    ['ngMaterial', 'ngAnimate', 'ngMessages', 'ngRoute', 'ngSanitize', 'base64', 'md.data.table', 'blockUI',
     'ui.codemirror', 'oc.lazyLoad', 'konami', 'hc.marked', 'ngMdBadge', 'angularjs-gauge']
);

/**
 * Main application controller
 * It holds some generic stuff like polling request, loaded services...
 */
Cleep
.controller('mainController', ['$rootScope', '$scope', 'rpcService', 'cleepService', 'blockUI', 'toastService', '$mdDialog', '$timeout', '$window',
function($rootScope, $scope, rpcService, cleepService, blockUI, toast, $mdDialog, $timeout, $window) {

    var self = this;
    self.rebooting = false;
    self.restarting = false;
    self.notConnected = false;
    self.reloadConfig = false;
    self.uiReloadScheduled = false;
    self.hostname = '';
    self.pollingTimeout = 0;
    self.nextPollingTimeout = 1;

    /**
     * Hard-reload the UI once (resets Angular injector / ocLazyLoad singletons).
     */
    self.__hardReloadUi = function() {
        if (self.uiReloadScheduled) {
            return;
        }
        self.uiReloadScheduled = true;
        $window.location.reload();
    };

    /**
     * Reload config after reconnect/restart with a short grace period and retries.
     * Avoids racing asset loads against a device that is still coming back up.
     * Ends with a full page reload so updated app frontends are picked up.
     */
    self.__reloadAfterReconnect = function(message) {
        // Wait for nginx/Cleep to accept connections again after restart/sync
        return $timeout(angular.noop, 1500)
            .then(function() {
                return cleepService.withLoadRetry(function() {
                    return self.loadConfig(false);
                }, {
                    label: 'application config',
                    maxAttempts: 5,
                    delayMs: 1000,
                });
            })
            .then(function() {
                if (message && message.length > 0) {
                    toast.success(message);
                }
                blockUI.stop();
                self.__hardReloadUi();
            }, function(err) {
                console.error('Unable to reload application config after reconnect:', err);
                blockUI.stop();
                toast.error('Unable to reload device configuration');
            });
    };

    /**
     * Handle polling
     */
    self.polling = function() {
         rpcService.poll()
            .then(function(response) {
                message = '';

                if (self.rebooting || self.restarting) {
                    // toast message
                    if (self.rebooting) {
                        message = 'Device has rebooted';
                    } else if (self.restarting) {
                        message = 'Application has restarted';
                    }
                    
                    // system has started
                    self.rebooting = false;
                    self.restarting = false;

                    // reload application config
                    self.reloadConfig = true;
                } else if (self.notConnected) {
                    // unblock ui
                    self.notConnected = false;
                    $mdDialog.cancel();

                    // toast message
                    message = 'Connection with device restored';

                    // reload application config
                    self.reloadConfig = true;
                }

                // reload application config after restart/reboot/connection loss
                if (self.reloadConfig) {
                    self.reloadConfig = false;
                    self.__reloadAfterReconnect(message);
                }

                if (response && response.data && !response.error) {
                    // handle system events
                    if (response.data.event === 'system.device.reboot') {
                        self.rebooting = true;
                        blockUI.start({message:'Device is rebooting...', submessage:'Please wait, it might take some time.', spinner:true, icon:null});
                    } else if (response.data.event=='system.cleep.restart') {
                        self.restarting = true;
                        blockUI.start({message:'Cleep is restarting...', submessage:'Please wait few seconds.', spinner:true, icon:null});
                    } else if (response.data.event === 'system.device.poweroff') {
                        blockUI.start({message:'Device is powering off.', submessage:'Device will disconnect in few seconds.', spinner:true, icon:null});
                    } else {
                        // broadcast received message
                        $rootScope.$broadcast(response.data.event, response.data.device_id, response.data.params);

                        // Replace device reference so one-way bindings / $watchCollection see the change
                        cleepService.updateDevice(response.data.device_id, response.data.params);
                    }
                }

                // reset next polling timeout
                self.nextPollingTimeout = 1;

                // relaunch polling right now (inside Angular digest)
                $timeout(self.polling, 0);
            }, 
            function(err) {
                if (!self.rebooting && !self.restarting) {
                    // error occured, differ next polling
                    /*self.nextPollingTimeout *= 2;
                    if (self.nextPollingTimeout>300) {
                        // do not exceed polling timeout over 5 minutes
                        self.nextPollingTimeout /= 2;
                    }*/
                    self.nextPollingTimeout = 2;

                    // handle connection loss
                    if (err=='Connection problem' && !self.notConnected) {
                        blockUI.start({message:'Connection lost with the device.', submessage:null, spinner:false, icon:'close-network'});
                        self.notConnected = true;
                    }
                } else {
                    // during reboot try every seconds
                    self.nextPollingTimeout = 1;
                }
                $timeout(self.polling, self.nextPollingTimeout*1000);
            });
    };

    /**
     * Load all config
     * @param withBlockUi (bool): enable or not block ui with message "loading data..."
     * @return promise
     */
    self.loadConfig = function(withBlockUi) {
        if (withBlockUi===undefined || withBlockUi===null) {
            withBlockUi = true;
        }

        // block ui
        if (withBlockUi) {
            blockUI.start({message:'Loading data...', submessage:'Please wait', icon:null, spinner:true});
        }

        return cleepService.loadConfig()
            .finally(function() {
                //unblock ui
                if (withBlockUi) {
                    blockUI.stop();
                }

                console.log('DEVICES', cleepService.devices);
                console.log('MODULES', cleepService.modules);
                console.log('RENDERERS', cleepService.renderers);
                console.log('EVENTS', cleepService.events);
                console.log('DRIVERS', cleepService.drivers);
            });
    };

    /**
     * Init main controller
     */
    self.init = function() {
        // System lifecycle only: hard-reload UI after needrestart (emitted by update/system).
        // Shell must not listen to update.* events.
        $rootScope.$on('system.cleep.needrestart', function() {
            if (self.uiReloadScheduled) {
                return;
            }
            self.uiReloadScheduled = true;
            toast.info('Update applied, reloading interface...');
            $timeout(function() {
                $window.location.reload();
            }, 700);
        });

        // launch polling
        $timeout(self.polling, 0);

        // load config (modules, devices, renderers...)
        self.loadConfig();
    };
    self.init();

    /**
     * Watch for parameters config changes to update device hostname
     */
    $scope.$watchCollection(
        function() {
            return cleepService.modules['parameters'];
        },
        function(newValue) {
            if (!angular.isUndefined(newValue)) {
                self.hostname = newValue.config.hostname;
            }
        }
    );

}]);

