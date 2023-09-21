/**
 * Configuration directive
 * Handle all modules configuration
 */
var installDirective = function($q, cleepService, toast, $mdDialog, $sce) {

    var installController = ['$rootScope', '$scope','$element', '$window', function($rootScope, $scope, $element, $window) {
        var self = this;
        self.cleepService = cleepService;
        self.search = {'$': ''};
        self.country = null;
        self.countryAlpha = null;
        self.moduleToInstall = null;
        self.loading = true;
        self.displayedModules = [];
        self.gaugeThreshold = {
            '0': { color: '#000000' },
            '5': { color: '#d32f2f' },
            '6': { color: '#f57c00' },
            '7': { color: '#fbc02d' },
            '8': { color: '#0288d1' },
            '9': { color: '#689f38' },
        };
        self.moduleIncompatible = null;

        /**
         * Clear search input
         */
        self.clearSearch = function() {
            self.search['$'] = '';
        };

        /**
         * Install module
         * @param module: module name (string)
         */
        self.install = function(module) {
            self.closeDialog();
            cleepService.installModule(module);
        };

        /**
         * Fill modules list
         */
        self.fillModules = function() {
            cleepService.getModuleConfig('parameters')
                .then((parametersConfig) => {
                    // update list of modules names
                    var modules = [];
                    for (const module of Object.values(cleepService.installableModules)) {
                        // fix module country alpha code
                        var countryAlpha = module.country;
                        if( countryAlpha===null || countryAlpha===undefined ) {
                            countryAlpha = '';
                        }

                        // append module if necessary
                        if ((!module.installed || (module.installed && module.library)) &&
                            (countryAlpha.length===0 || countryAlpha.toUpperCase()==parametersConfig.country.alpha2) ) {
                            modules.push(module);
                        }
                    }
                    self.displayedModules = modules;
                    self.loading = false;
                });
        };

        /**
         * Show incompatible dialog
         */
        self.showIncompatibleDialog = function(module, ev) {
            self.moduleIncompatible = module;
            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'incompatibleCtl',
                templateUrl: 'js/settings/install/incompatible.dialog.html',
                parent: angular.element(document.body),
                targetEvent: ev,
                clickOutsideToClose: true,
                fullscreen: true
            })
            .then(function() {}, function() {});
        };

        /**
         * Close update dialog
         */
        self.closeDialog = function() {
            $mdDialog.hide();
        };

        /**
         * Show install dialog
         */
        self.showInstallDialog = function(module, ev) {
            self.moduleToInstall = module;

            // trust html content
            self.sceLongDescription = $sce.trustAsHtml(self.moduleToInstall.longdescription);
            self.sceChangelog = $sce.trustAsHtml(self.moduleToInstall.changelog);

            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'installCtl',
                templateUrl: 'js/settings/install/install.dialog.html',
                parent: angular.element(document.body),
                targetEvent: ev, 
                clickOutsideToClose: true,
                fullscreen: true
            })  
            .then(function() {}, function() {});
        };

        /**
         * Redirect to update module logs page
         */
        self.gotoUpdateLogs = function() {
            $window.location.href = '#!/module/update?tab=logs';
        };

        /** 
         * Redirect to update module page
         */
        self.gotoUpdateCleep = function() {
            self.closeDialog();
            $window.location.href = '#!/module/update?tab=cleep';
        };

        /**
         * Fill modules as soon as cleep configuration is loaded
         */
        $scope.$watch(
            function() {
                return cleepService.installableModules;
            },
            function(newValue) {
                if( newValue && Object.keys(newValue).length ) {
                    self.fillModules();
                }
            },
            true
        );

        /**
         * Catch module install events
         */
        $rootScope.$on('update.module.install', function(event, uuid, params) {
            // module install event received, refresh modules updates infos
            cleepService.refreshModulesUpdates();
        });

        /**
         * Init component
         */
        self.$onInit = function() {
            // load mandatory data
            cleepService.getInstallableModules();
            cleepService.refreshModulesUpdates();
        };

    }];

    return {
        templateUrl: 'js/settings/install/install.html',
        replace: true,
        controller: installController,
        controllerAs: 'installCtl',
    };
};

var Cleep = angular.module('Cleep');
Cleep.directive('installDirective', ['$q', 'cleepService', 'toastService', '$mdDialog', '$sce', installDirective]);

