/**
 * Configuration directive
 * Handle all modules configuration
 */
var installDirective = function($q, cleepService, toast, $mdDialog, $sce) {

    var installController = ['$rootScope', '$scope','$element', function($rootScope, $scope, $element) {
        var self = this;
        self.cleepService = cleepService;
        self.search = '';
        self.country = null;
        self.countryAlpha = null;
        self.moduleToInstall = null;
        self.modulesName = [];

        /**
         * Clear search input
         */
        self.clearSearch = function() {
            self.search = '';
        };

        /**
         * Install module
         * @param module: module name (string)
         */
        self.install = function(module) {
            // close modal
            self.closeDialog();

            // launch install
            cleepService.installModule(module);
        };

        /**
         * Fill modules list
         */
        self.fillModules = function() {
            // update list of modules name
            var modulesName = [];
            for( moduleName in cleepService.installableModules ) {
                // fix module country alpha code
                var countryAlpha = cleepService.installableModules[moduleName].country;
                if( countryAlpha===null || countryAlpha===undefined ) {
                    countryAlpha = '';
                }

                // append module name if necessary
                if(
                    (!cleepService.installableModules[moduleName].installed || (cleepService.installableModules[moduleName].installed && cleepService.installableModules[moduleName].library)) &&
                    (countryAlpha.length===0 || countryAlpha==cleepService.installableModules.parameters.config.country.alpha2)
                ) {
                    modulesName.push(moduleName);
                }
            }
            self.modulesName = modulesName;
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
         * Redirect to update module page
         */
        self.gotoUpdateModule = function() {   
            $window.location.href = '#!/module/update?tab=modules';
        };

        /**
         * Fill modules as soon as cleep configuration is loaded
         */
        $scope.$watchCollection(
            function() {
                return cleepService.installableModules;
            },
            function(newValue, oldValue) {
                if( newValue && Object.keys(newValue).length ) {
                    self.fillModules();
                }
            }
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

