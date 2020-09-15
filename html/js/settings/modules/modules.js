/**
 * Configuration directive
 * Handle all modules configuration
 */
var modulesDirective = function($rootScope, cleepService, $window, toast, confirm, $mdDialog, $sce) {

    var modulesController = ['$scope','$element', function($scope, $element) {
        var self = this;
        self.cleepService = cleepService;
        self.search = '';
        // self.moduleToUpdate = null;
        // self.moduleToNotStarted = null;
        self.updates = [];
        self.modulesNames = [];
        // self.moduleLogs = null;

        /**
         * Clear search input
         */
        self.clearSearch = function()
        {
            self.search = '';
        };

        /**
         * Redirect to install module page
         */
        self.toInstallPage = function()
        {
            $window.location.href = '#!install';
        };

        /**
         * Uninstall module
         */
        self.uninstall = function(module)
        {
            confirm.open('Uninstall module?', 'Do you want to remove this module? Its config will be kept.', 'Uninstall', 'Cancel')
                .then(function() {
                    //lock button asap
                    cleepService.modules[module].processing = 'uninstall';

                    //uninstall module
                    return cleepService.uninstallModule(module);
                }, function() {});
        };

        /**
         * Force module uninstall
         */
        self.forceUninstall = function(module)
        {
            //lock button
            cleepService.modules[module].processing = 'uninstall';

            //close dialog
            self.closeDialog();

            //uninstall module
            return cleepService.forceUninstallModule(module);
        };

        /**
         * Update module
         */
        self.update = function(module)
        {
            //lock button asap
            cleepService.modules[module].processing = 'update';

            //close dialog
            self.closeDialog();

            //update module
            cleepService.updateModule(module);
        };

        /**
         * Init controller
         */
        self.init = function() {
            // load module updates
            cleepService.getModulesUpdates()
                .then(function(resp) {
                    if (resp.error) {
                        toast.error('Error getting updates');
                        return;
                    }
                    self.updates = resp.data;
                })
                .finally(function() {
                    // fill modules name
                    var modulesNames = [];
                    for( var moduleName in cleepService.modules ) {
                        // keep only installed modules
                        if( cleepService.modules[moduleName].installed && !cleepService.modules[moduleName].library ) {
                            modulesNames.push(moduleName);
                        }
                    }
                    self.modulesNames = modulesNames;
                });

            //add fab action
            action = [{
                callback: self.toInstallPage,
                icon: 'plus',
                aria: 'Install module',
                tooltip: 'Install module'
            }];
            $rootScope.$broadcast('enableFab', action);
        };

        /**
         * Init controller as soon as modules configuration are loaded
         */
        $scope.$watchCollection(
            function() {
                return cleepService.modules;
            },
            function(newValue, oldValue) {
                if (!angular.equals(newValue, {})) {
                    self.init();
                }
            }
        );

        /**
         * Close update dialog
         */
        self.closeDialog = function() {
            $mdDialog.hide();
        };

        /**
         * Show update dialog
         */
        self.showUpdateDialog = function(module, ev) {
            self.moduleToUpdate = module;

            //trust html content
            self.sceChangelog = $sce.trustAsHtml(self.moduleToUpdate.changelog);

            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'updateCtl',
                templateUrl: 'js/settings/modules/update.dialog.html',
                parent: angular.element(document.body),
                targetEvent: ev,
                clickOutsideToClose: true,
                fullscreen: true
            })
            .then(function() {}, function() {});
        };

        /**
         * Show not started dialog
         */
        self.showNotStartedDialog = function(module, ev) {
            self.moduleNotStarted = module;
            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'notstartedCtl',
                templateUrl: 'js/settings/modules/notstarted.dialog.html',
                parent: angular.element(document.body),
                targetEvent: ev,
                clickOutsideToClose: true,
                fullscreen: true
            })
            .then(function() {}, function() {});
        };

        /** 
         * Show logs dialog
         */
        self.showLogsDialog = function(moduleName, ev) {
            //get last module processing
            cleepService.getLastModuleProcessing(moduleName)
                .then(function(resp) {
                    //prepare dialog object
                    self.moduleLogs = { 
                        name: moduleName,
                        status: resp.data.status,
                        time: resp.data.time,
                        stdout: resp.data.stdout.join('\n'),
                        stderr: resp.data.stderr.join('\n'),
                        process: resp.data.process.join('\n')
                    };  

                    //display dialog
                    $mdDialog.show({
                        controller: function() { return self; },
                        controllerAs: 'modulesCtl',
                        templateUrl: 'js/settings/modules/logs.dialog.html',
                        parent: angular.element(document.body),
                        targetEvent: ev, 
                        clickOutsideToClose: true,
                        fullscreen: true
                    })  
                    .then(function() {}, function() {});
                }); 
        };

    }];

    var modulesLink = function(scope, element, attrs, controller) {
        //see watchcollection above !
    };

    return {
        templateUrl: 'js/settings/modules/modules.html',
        replace: true,
        controller: modulesController,
        controllerAs: 'modulesCtl',
        link: modulesLink
    };
};

var Cleep = angular.module('Cleep');
Cleep.directive('modulesDirective', ['$rootScope', 'cleepService', '$window', 'toastService', 'confirmService', '$mdDialog', '$sce', modulesDirective]);

