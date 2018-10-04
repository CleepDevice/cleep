/**
 * Configuration directive
 * Handle all modules configuration
 */
var installDirective = function($q, raspiotService, toast, $mdDialog) {

    var installController = ['$rootScope', '$scope','$element', function($rootScope, $scope, $element) {
        var self = this;
        self.raspiotService = raspiotService;
        self.search = '';
        self.country = null;
        self.countryAlpha = null;
        self.moduleToInstall = null;
        self.moduleLogs = null
        self.moduleNames = [];

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
            raspiotService.modules[module].processing = true;

            //close modal
            self.closeDialog();

            //trigger install
            raspiotService.installModule(module);
        };

        /**
         * Init controller
         */
        self.init = function()
        {
            //update list of module names
            var moduleNames = [];
            for( moduleName in raspiotService.modules )
            {
                //fix module country alpha code
                var countryAlpha = raspiotService.modules[module].country;
                if( countryAlpha===null || countryAlpha===undefined )
                {
                    countryAlpha = "";
                }

                //append module name if necessary
                if( !raspiotService.modules[moduleName].installed && (countryAlpha.length===0 || countryAlpha==raspiotService.modules.parameters.config.country.alpha2))
                {
                    moduleNames.push(moduleName);
                }
            }
            self.moduleNames = moduleNames;
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
            //get system config
            raspiotService.getModuleConfig('system')
                .then(function(config) {
                    //prepare dialog object
                    self.moduleLogs = {
                        name: moduleName,
                        status: config.lastmodulesinstalls[moduleName].status,
                        time: config.lastmodulesinstalls[moduleName].time,
                        stdout: config.lastmodulesinstalls[moduleName].stdout.join('\n'),
                        stderr: config.lastmodulesinstalls[moduleName].stderr.join('\n'),
                        process: config.lastmodulesinstalls[moduleName].process.join('\n'),
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
                return raspiotService.modules;
            },
            function(newValue, oldValue) {
                self.init();
            }
        );

    }];

    var installLink = function(scope, element, attrs, controller) {
        //see watchcollection above !
    };

    return {
        templateUrl: 'js/settings/install/install.html',
        replace: true,
        controller: installController,
        controllerAs: 'installCtl',
        link: installLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('installDirective', ['$q', 'raspiotService', 'toastService', '$mdDialog', installDirective]);

