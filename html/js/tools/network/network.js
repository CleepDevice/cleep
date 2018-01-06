var wiredDirective = function(raspiotService, networkService, toast, confirm, $mdDialog, blockUI) {

    var wiredController = ['$scope', function($scope) {
        var self = this;

        self.wiredInterfaces = [];
        self.wiredInterfaceNames = [];
        self.wiredConfig = [];

        self.wifiInterfaces = [];
        self.wifiInterfaceNames = [];
        self.wifiConfig = [];
        self.wifiNetworks = [];

        self.networkBlockui = null;
        self.networks = [];
        self.newConfig = null;
        self.selectedNetwork = null;
        self.wifiPassword = null;

        /**
         * Load configuration
         */
        self.__loadConfig = function(config)
        {
            //fill networks
            self.__fillNetworks(config.networks);
        };

        /**
         * Fill networks
         * @param networks: list of networks returned by rpc
         */
        self.__fillNetworks = function(networks)
        {
            self.networks = [];
            for( var network in networks )
            {
                self.networks.push(networks[network]);
            }
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
         * Cancel dialog
         */
        self.cancelDialog = function()
        {
            self.resetDialogVariables()
            $mdDialog.cancel();
        };

        /**
         * Valid dialog
         * Note: don't forget to clear data !
         */
        self.validDialog = function() {
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

            networkService.refreshWifiNetworks()
                .then(function(config) {
                    //update networks internally
                    self.__fillNetworks(config.networks);
                })
                .finally(function() {
                    self.networkLoading(false);
                });
        };

        /**
         * Change wifi password
         */
        self.changeWifiPassword = function()
        {
            networkService.updateWifiNetworkPassword(self.selectedNetwork.network, self.wifiPassword)
                .then(function() {
                    toast.success('Password updated');
                })
                .finally(function() {
                    self.wifiPassword = '';
                });
        };

        /**
         * Enable wifi network
         */
        self.enableWifiNetwork = function()
        {
            networkService.enableWifiNetwork(self.selectedNetwork.interface, self.selectedNetwork.network)
                .then(function() {
                    self.selectedNetwork.config.disabled = false;
                    toast.success('Network enabled');
                });
        };

        /**
         * Disable wifi network
         */
        self.disableWifiNetwork = function()
        {
            networkService.disableWifiNetwork(self.selectedNetwork.interface, self.selectedNetwork.network)
                .then(function() {
                    self.selectedNetwork.config.disabled = true;
                    toast.success('Network disabled');
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

                    //perform deletion
                    return networkService.deleteWifiNetwork(self.selectedNetwork.network)
                        .then(function(config) {
                            //update networks internally
                            self.__fillNetworks(config.networks);

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
                    clickOutsideToClose: true,
                    fullscreen: true
                })
                    .then(function() {
                        //lock ui
                        self.networkLoading(true);

                        //perform action
                        networkService.saveWifiNetwork(self.selectedNetwork.network, self.wifiPassword, self.selectedNetwork.config.encryption)
                            .then(function(config) {
                                //update network internally
                                self.__fillNetworks(config.networks);

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
                networkService.saveWifiNetwork(self.selectedNetwork.network, self.wifiPassword, self.selectedNetwork.config.encryption)
                    .then(function(config) {
                        //update networks internally
                        self.__fillNetworks(config.networks);

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
                    //self.networkLoading(true);

                    //perform deletion
                    return networkService.reconfigureWifiNetwork(self.selectedNetwork.interface)
                        .then(function(config) {
                            //user message
                            toast.success('Network has been reconfigured')
                        })
                        .finally(function() {
                            //self.networkLoading(false);
                        });
                })
                .finally(function() {
                    self.resetDialogVariables();
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
                    self.__loadConfig(config);
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

