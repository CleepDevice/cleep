/**
 * Actions configuration directive
 * Handle actions module configuration
 */
var actionsConfigDirective = function($rootScope, toast, raspiotService, actionsService, confirm, $mdDialog) {

    var actionController = ['$scope', function($scope) {
        var self = this;
        self.scripts = [];
        self.uploadFile = null;

        /**
         * Cancel dialog
         */
        self.cancelDialog = function() {
            $mdDialog.cancel();
        };

        /** 
         * Open add dialog
         */
        self.openAddDialog = function() {
            return $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'actionsCtl',
                templateUrl: 'js/configuration/actions/addAction.html',
                parent: angular.element(document.body),
                clickOutsideToClose: false
            }); 
        }; 

        /**
         * Delete script
         */
        self.openDeleteDialog = function(script) {
            confirm.open('Delete script?', null, 'Delete')
                .then(function() {
                    return actionsService.deleteScript(script);
                })
                .then(function() {
                    return raspiotService.reloadModuleConfig('actions');
                })
                .then(function(config) {
                    self.scripts = config.scripts;
                    toast.success('Script deleted');
                });
        };

        /**
         * Watch upload variable to trigger upload
         */
        $scope.$watch(function() {
            return self.uploadFile;
        }, function(file) {
            if( file )
            {
                //launch upload
                toast.loading('Uploading script...');
                actionsService.uploadScript(file)
                    .then(function(resp) {
                        return raspiotService.reloadModuleConfig('actions');
                    })
                    .then(function(config) {
                        $mdDialog.hide();
                        self.scripts = config.scripts;
                        toast.success('Script uploaded');
                    });
            }
        });

        /**
         * Disable/enable specified script
         */
        self.disableScript = function(script, disabled) {
            actionsService.disableScript(script, disabled)
                .then(function(resp) {
                    return raspiotService.reloadModuleConfig('actions');
                })
                .then(function(config) {
                    self.scripts = config.scripts;

                    //message info
                    if( disabled ) {
                        toast.success('Script is disabled');
                    } else {
                        toast.success('Script is enabled');
                    }
                });
        };

        /**
         * Download script
         */
        self.downloadScript = function(script) {
            actionsService.downloadScript(script);
        };

        /**
         * Init controller
         */
        self.init = function() {
            var config = raspiotService.getModuleConfig('actions');
            self.scripts = config.scripts;

            //add module actions to fabButton
            var actions = [{
                icon: 'add_circle',
                callback: self.openAddDialog,
                tooltip: 'Add script'
            }]; 
            $rootScope.$broadcast('enableFab', actions);
        };

    }];

    var actionLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'js/configuration/actions/actions.html',
        replace: true,
        controller: actionController,
        controllerAs: 'actionsCtl',
        link: actionLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('actionsConfigDirective', ['$rootScope', 'toastService', 'raspiotService', 'actionsService', 'confirmService', '$mdDialog', actionsConfigDirective]);

