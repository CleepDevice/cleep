/**
 * Configuration directive
 * Handle all modules configuration
 */
angular
.module('Cleep')
.directive('modulesDirective', ['$rootScope', 'cleepService', '$window', 'toastService', 'confirmService', '$mdDialog', '$sce', '$location', '$anchorScroll',
function($rootScope, cleepService, $window, toast, confirm, $mdDialog, $sce, $location, $anchorScroll) {

    var modulesController = ['$scope','$element', function($scope, $element) {
        var self = this;
        self.cleepService = cleepService;
        self.search = '';
        self.updates = [];
        self.modulesNames = [];
        self.moduleUpdate = {};

        /**
         * Clear search input
         */
        self.clearSearch = function() {
            self.search = '';
        };

        /**
         * Redirect to install module page
         */
        self.gotoInstallPage = function() {
            $window.location.href = '#!install';
        };

        /**
         * Uninstall module
         */
        self.uninstallModule = function(module) {
            confirm.open('Module uninstallation', 'Do you want to uninstall this module?<br/>Its config will be kept.', 'Uninstall', 'Cancel')
                .then(function() {
                    // uninstall module
                    return cleepService.uninstallModule(module);
                }, function() {});
        };

        /**
         * Force module uninstall
         */
        self.forceUninstallModule = function(module) {
            // close dialog
            self.closeDialog();

            // uninstall module
            return cleepService.forceUninstallModule(module);
        };

        /**
         * Update module
         */
        self.updateModule = function(module) {
            // close dialog
            self.closeDialog();

            // update module
            cleepService.updateModule(module);
        };

        /**
         * Init controller
         */
        self.$onInit = function() {
            // scroll to app
            if( $location.search().app ) {
                $location.hash('mod-' + $location.search().app);
                $anchorScroll();
            }

            // load mandatory stuff
            cleepService.getInstallableModules();
            cleepService.refreshModulesUpdates();

            // add fab action
            action = [{
                callback: self.gotoInstallPage,
                icon: 'plus',
                aria: 'Install module',
                tooltip: 'Install module'
            }];
            $rootScope.$broadcast('enableFab', action);
        };

        /**
         * Fill modules
         */
        self.fillModules = function() {
            var modulesNames = [];
            for( var moduleName in cleepService.modules ) {
                modulesNames.push(moduleName);
            }
            self.modulesNames = modulesNames;
        };

        /**
         * Fill modules as soon as cleep configuration is loaded
         */
        $scope.$watchCollection(
            function() {
                return cleepService.modules;
            },
            function(newValue, oldValue) {
                if( newValue && Object.keys(newValue).length ) {
                    self.fillModules();
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
         * Show module update dialog
         */
        self.showModuleUpdateDialog = function(module, ev) {
            self.moduleUpdate = module;

            // trust html content
            self.sceChangelog = $sce.trustAsHtml(self.moduleUpdate.update.changelog);

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
                templateUrl: 'js/settings/modules/not-started.dialog.html',
                parent: angular.element(document.body),
                targetEvent: ev,
                clickOutsideToClose: true,
                fullscreen: true
            })
            .then(function() {}, function() {});
        };

        /** 
         * Catch module uninstall events
         */
        $rootScope.$on('update.module.uninstall', function(event, uuid, params) {
            // module uninstall event received, refresh modules updates infos
            cleepService.refreshModulesUpdates();
        });

        /** 
         * Catch module update events
         */
        $rootScope.$on('update.module.update', function(event, uuid, params) {
            // module update event received, refresh modules updates infos
            cleepService.refreshModulesUpdates();
        });

    }];

    return {
        templateUrl: 'js/settings/modules/modules.html',
        replace: true,
        controller: modulesController,
        controllerAs: 'modulesCtl',
    };
}]);

