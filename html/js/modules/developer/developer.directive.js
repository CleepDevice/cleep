/**
 * Developer configuration directive
 * Helps developer to analyze and publish module to cleep store
 */
var developerConfigDirective = function($rootScope, toast, raspiotService, developerService) {

    var developerController = ['$scope', function($scope) {
        var self = this;
        self.modules = [];
        self.selectedModule = null;
        self.data = null;
        self.selectedNav = 'buildmodule';
        self.loading = false;

        /**
         * Init controller
         */
        self.init = function(modules)
        {
            //keep only modules names
            var temp = [];
            for( var module in modules )
            {
                temp.push(module);
            }
            self.modules = temp.sort();
        };

        /**
         * Analyze selected module
         */
        self.analyzeModule = function()
        {
            //reset members
            self.data = null;
            self.loading = true;

            //check params
            if( !self.selectedModule )
            {
                toast.error('Please select a module');
                self.loading = false;
                return;
            }

            //analyze module
            developerService.analyzeModule(self.selectedModule)
                .then(function(resp) {
                    console.log(resp);
                    //save module content
                    self.data = resp.data;
            
                    //select first nav tab
                    self.selectedNav = 'buildmodule';
                })
                .finally(function() {
                    self.loading = false;
                });
        };

        /**
         * Generate desc.json file
         */
        self.generateDescJson = function()
        {
            if( !self.data )
                return;

            developerService.generateDescJson(self.data.js.files, self.data.js.icon)
                .then(function(resp) {
                    if( resp.data )
                        toast.success('Desc.json file generated in module directory');
                    else
                        toast.error('Problem generating desc.json file. Please check logs');
                });
        };

        /**
         * Build package
         */
        self.buildPackage = function()
        {
            //check data
            if( !self.data )
                return;
    
            self.loading = true;
            developerService.buildPackage(self.selectedModule, self.data, 30)
                .then(function(resp) {
                    //build generation completed, download package now
                    return developerService.downloadPackage();
                })
                .then(function(resp) {
                    console.log('download done?', resp);
                }, function(err) {
                    console.error('Download failed', err);
                })
                .finally(function() {
                    self.loading = false;
                });
        };
    }];

    var developerLink = function(scope, element, attrs, controller) {
        controller.init(raspiotService.modules);
    };

    return {
        templateUrl: 'developer.directive.html',
        replace: true,
        controller: developerController,
        controllerAs: 'devCtl',
        link: developerLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('developerConfigDirective', ['$rootScope', 'toastService', 'raspiotService', 'developerService', developerConfigDirective]);

