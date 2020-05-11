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
        self.moduleLogs = null
        self.modulesName = [];

        /**
         * Clear search input
         */
        self.clearSearch = function()
        {
            self.search = '';
        };

        /**
         * Install module
         * @param module: module name (string)
         */
        self.install = function(module)
        {
            //lock button asap
            cleepService.installableModules[module].processing = true;

            //close modal
            self.closeDialog();

            //trigger install
            cleepService.installModule(module)
                .catch(function(error) {
                    //toast should be already displayed, just cancel install
                    cleepService.installableModules[module].processing = false;
                });
        };

        /**
         * Init controller
         */
        self.init = function()
        {
            //update list of modules name
            var modulesName = [];
            for( moduleName in cleepService.installableModules )
            {
                //fix module country alpha code
                var countryAlpha = cleepService.installableModules[moduleName].country;
                if( countryAlpha===null || countryAlpha===undefined )
                {
                    countryAlpha = "";
                }

                //append module name if necessary
                if(
                    (!cleepService.installableModules[moduleName].installed || (cleepService.installableModules[moduleName].installed && cleepService.installableModules[moduleName].library)) &&
                    (countryAlpha.length===0 || countryAlpha==cleepService.installableModules.parameters.config.country.alpha2)
                )
                {
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

            //trust html content
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
                        controllerAs: 'installCtl',
                        templateUrl: 'js/settings/install/logs.dialog.html',
                        parent: angular.element(document.body),
                        targetEvent: ev, 
                        clickOutsideToClose: true,
                        fullscreen: true
                    })  
                    .then(function() {}, function() {});
                });
        };

        /**
         * Init controller as soon as modules configuration are loaded
         */
        $scope.$watchCollection(
            function() {
                return cleepService.installableModules;
            },
            function(newValue, oldValue) {
                if( newValue ) {
                    self.init();
                }
            }
        );

    }];

    var installLink = function(scope, element, attrs, controller) {
        //get installable modules. Once loaded, watchCollection above will trigger
        //init() function of this controller
        cleepService.getInstallableModules();
    };

    return {
        templateUrl: 'js/settings/install/install.html',
        replace: true,
        controller: installController,
        controllerAs: 'installCtl',
        link: installLink
    };
};

var Cleep = angular.module('Cleep');
Cleep.directive('installDirective', ['$q', 'cleepService', 'toastService', '$mdDialog', '$sce', installDirective]);

