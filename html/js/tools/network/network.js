var wiredDirective = function(raspiotService, networkService, toast, confirm, $mdDialog, blockUI) {

    var wiredController = ['$scope', function($scope) {
        var self = this;
        self.networkBlockui = null;
        self.networks = [];
        self.wifiInterfaces = [];
        self.newConfig = null;
        self.selectedNetwork = null;
        self.wifiPassword = null;
        self.testing = false;

        /**
         * Update config
         * @param networks: list of networks returned by rpc
         */
        self.__updateConfig = function(config)
        {
            self.networks = config.networks;
            self.wifiInterfaces = config.wifiinterfaces;
        };

        /**
         * Block ui when loading stuff
         */
        self.networkLoading = function(block)
        {
            if( block )
            {
                self.networkBlockui.start();
            }
            else
            {
                self.networkBlockui.stop();
            }
        };

        /**
         * Reset dialog variables
         */
        self.resetDialogVariables = function()
        {
            self.newConfig = null;
            self.selectedNetwork = null;
            self.wifiPassword = null;
        };

        /**
         * Cancel dialog (close modal and reset variables)
         */
        self.cancelDialog = function()
        {
            if( self.testing )
            {
                //test in progress, cancel action
                return;
            }

            self.resetDialogVariables()
            $mdDialog.cancel();
        };

        /**
         * Valid dialog (only close modal)
         * Note: don't forget to reset variables !
         */
        self.validDialog = function() {
            if( self.testing )
            {
                //test in progress, cancel action
                return;
            }

            $mdDialog.hide();
        };

        /**
         * Show interface configuration
         * @param item: selected item
         * @param type: type of network (wifi|wired)
         */
        self.showConfig = function(item, type)
        {
            self.selectedNetwork = item;

            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'dialogCtl',
                templateUrl: 'js/tools/network/networkInfosDialog.html',
                parent: angular.element(document.body),
                clickOutsideToClose: true,
                fullscreen: true
            });

        };

        /**
         * Fill new config class member with specified interface configuration
         * @param network: selected network
         */
        self.__fillNewConfig = function(network)
        {
            self.newConfig = {
                interface: network.interface,
                dhcp: network.config.mode=='dhcp'? true : false,
                ipv4: network.config.address,
                gateway_ipv4: network.config.gateway,
                netmask_ipv4: network.config.netmask
            };
        };

        /**
         * Show wired edition dialog
         * @param network: selected network
         */
        self.editWiredConfig = function(network)
        {
            self.selectedNetwork = network;

            //get interfaces and fill new class config member
            self.__fillNewConfig(network);

            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'dialogCtl',
                templateUrl: 'js/tools/network/wiredEditDialog.html',
                parent: angular.element(document.body),
                clickOutsideToClose: true,
                fullscreen: true
            }).then(function() {
                //save edition
                var promise = null;
                if( self.newConfig.dhcp )
                {
                    //save wired dhcp
                    promise = networkService.saveWiredDhcpConfiguration(self.newConfig.interface);
                }
                else
                {
                    //save wired static
                    //TODO handle fallback option when dhcpcd is installed
                    promise = networkService.saveWiredStaticConfiguration(self.newConfig.interface, self.newConfig.ipv4, self.newConfig.gateway_ipv4, self.newConfig.netmask_ipv4, false);
                }

                //execute promise
                promise
                    .then(function() {
                        toast.success('Configuration saved');
                    }, function() {
                        toast.error('Problem during configuration saving');
                    })
                    .finally(function() {
                        self.resetDialogVariables();
                    });
            });
        };

        /**
         * Show wifi edition dialog
         * @param network: selected network
         */
        self.editWifiConfig = function(network)
        {
            //self.selectedConfig = item;
            self.selectedNetwork = network;

            //prepare new config
            self.__fillNewConfig(network);

            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'dialogCtl',
                templateUrl: 'js/tools/network/wifiEditDialog.html',
                parent: angular.element(document.body),
                clickOutsideToClose: true,
                fullscreen: true
            });
        };

        /**
         * Refresh wifi networks
         */
        self.refreshWifiNetworks = function()
        {
            //lock ui
            self.networkLoading(true);
            toast.loading('Updating network informations...');

            networkService.refreshWifiNetworks()
                .then(function(config) {
                    //update config
                    self.__updateConfig(config);
                })
                .finally(function() {
                    self.networkLoading(false);
                    toast.hide();
                });
        };

        /**
         * Change wifi password
         */
        self.changeWifiPassword = function()
        {
            //lock ui
            self.validDialog();
            self.networkLoading(true);
            toast.loading('Changing password...');

            networkService.updateWifiNetworkPassword(self.selectedNetwork.interface, self.selectedNetwork.network, self.wifiPassword)
                .then(function(config) {
                    //update config
                    self.__updateConfig(config);

                    //user message
                    toast.success('Password updated');
                })
                .finally(function() {
                    self.resetDialogVariables();
                    self.networkLoading(false);
                });
        };

        /**
         * Enable wifi network
         */
        self.enableWifiNetwork = function()
        {
            //lock ui
            self.validDialog();
            self.networkLoading(true);
            toast.loading('Enabling network...');

            networkService.enableWifiNetwork(self.selectedNetwork.interface, self.selectedNetwork.network)
                .then(function(config) {
                    //update config
                    self.__updateConfig(config);
                    
                    //user message
                    toast.success('Network enabled');
                })
                .finally(function() {
                    self.resetDialogVariables();
                    self.networkLoading(false);
                });
        };

        /**
         * Disable wifi network
         */
        self.disableWifiNetwork = function()
        {
            //lock ui
            self.validDialog();
            self.networkLoading(true);
            toast.loading('Disabling network...');

            networkService.disableWifiNetwork(self.selectedNetwork.interface, self.selectedNetwork.network)
                .then(function(config) {
                    //update config
                    self.__updateConfig(config);
                    
                    //user message
                    toast.success('Network disabled');
                })
                .finally(function() {
                    self.resetDialogVariables();
                    self.networkLoading(false);
                });
        };

        /**
         * Forget wifi network
         */
        self.forgetWifiNetwork = function()
        {
            //only 1 modal allowed, close properly current one before opening confirm dialog
            //it keeps all variables
            self.validDialog();

            //open confirm dialog
            confirm.open('Forget network', 'All wifi network configuration will be deleted', 'Forget')
                .then(function() {
                    //block ui
                    self.networkLoading(true);
                    toast.loading('Forgetting network...');

                    //perform deletion
                    return networkService.deleteWifiNetwork(self.selectedNetwork.interface, self.selectedNetwork.network)
                        .then(function(config) {
                            //update config
                            self.__updateConfig(config);

                            //user message
                            toast.success('Network configuration has been forgotten')
                        })
                        .finally(function() {
                            self.networkLoading(false);
                        });
                })
                .finally(function() {
                    self.resetDialogVariables();
                });
        };

        /**
         * Connect to wifi network
         * Open password dialog and try to connect
         */
        self.connectWifiNetwork = function(network)
        {
            self.selectedNetwork = network;

            if( self.selectedNetwork.config.encryption!=='unsecured' )
            {
                //encrypted connection, prompt network password
                $mdDialog.show({
                    controller: function() { return self; },
                    controllerAs: 'dialogCtl',
                    templateUrl: 'js/tools/network/wifiConnectionDialog.html',
                    parent: angular.element(document.body),
                    clickOutsideToClose: false,
                    escapeToClose: false,
                    fullscreen: true
                })
                    .then(function() {
                        //lock ui
                        self.networkLoading(true);
                        toast.loading('Connecting to network...');

                        //perform action
                        networkService.saveWifiNetwork(self.selectedNetwork.interface, self.selectedNetwork.network, self.wifiPassword, self.selectedNetwork.config.encryption)
                            .then(function(config) {
                                //update config
                                self.__updateConfig(config);

                                //user message
                                toast.success('Wifi network configuration saved. Device should be able to connect to this network');
                            })
                            .finally(function() {
                                //unlock ui
                                self.networkLoading(false);
                            });
                    })
                    .finally(function() {
                        self.resetDialogVariables();
                    });
            }
            else
            {
                //unsecured network, directly add network
                self.networkLoading(true);
                toast.loading('Connecting to network...');

                networkService.saveWifiNetwork(self.selectedNetwork.interface, self.selectedNetwork.network, self.wifiPassword, self.selectedNetwork.config.encryption)
                    .then(function(config) {
                        //update config
                        self.__updateConfig(config);

                        //user message
                        toast.success('Wifi network configuration saved. Device should be able to connect to this network');
                    })
                    .finally(function() {
                        //unlock ui
                        self.networkLoading(false);
                    });
            }
        };

        /**
         * Reconfigure network interface
         */
        self.reconfigureWifiNetwork = function()
        {
            //only 1 modal allowed, close properly current one before opening confirm dialog
            //it keeps all variables
            self.validDialog();

            //open confirm dialog
            confirm.open('Reconfigure network', 'This action can disconnect the device temporarly. Please wait until it connects again.', 'Reconfigure')
                .then(function() {
                    //block ui
                    self.networkLoading(true);
                    toast.loading('Reconfiguring network...');

                    //execute action
                    return networkService.reconfigureWifiNetwork(self.selectedNetwork.interface)
                        .then(function(config) {
                            //update config
                            self.__updateConfig(config);

                            //user message
                            toast.success('Network has been reconfigured')
                        })
                        .finally(function() {
                            //unblock ui
                            self.networkLoading(false);
                        });
                })
                .finally(function() {
                    self.resetDialogVariables();
                });

        };

        /**
         * Test wifi connection
         */
        self.testWifiNetwork = function()
        {
            //testing flag
            self.testing = true;
            
            //perform action
            networkService.testWifiNetwork(self.selectedNetwork.interface, self.selectedNetwork.network, self.wifiPassword, self.selectedNetwork.config.encryption)
                .then(function() {
                    //user message
                    toast.success('Test successful. You can connect safely now');
                 })
                .finally(function() {
                    //unlock ui
                    self.testing = false;
                });
        };

        /**
         * Controller init
         */
        self.init = function()
        {
            //init blockui
            self.networkBlockui = blockUI.instances.get('networkBlockui');
            self.networkLoading(true);

            //load config
            raspiotService.getModuleConfig('network')
                .then(function(config) {
                    self.__updateConfig(config);
                })
                .finally(function() {
                    self.networkLoading(false);
                });
        };

    }];

    var wiredLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        restrict: 'AE',
        templateUrl: 'js/tools/network/network.html',
        replace: true,
        controller: wiredController,
        controllerAs: 'networkCtl',
        link: wiredLink
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.directive('networkWidget', ['raspiotService', 'networkService', 'toastService', 'confirmService', '$mdDialog', 'blockUI', wiredDirective]);

