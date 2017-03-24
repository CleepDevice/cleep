/**
 * Actions configuration directive
 * Handle actions module configuration
 */
var actionsConfigDirective = function($q, toast, actionsService, confirm, $mdDialog) {

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
         * Delete dialog
         */
        self.openDeleteDialog = function(script) {
            confirm.open('Delete script?', null, 'Delete')
                .then(function() {
                    actionsService.deleteScript(script)
                        .then(function() {
                            toast.success('Script deleted');
                            self.getScripts();
                        });
                });
        };

        /** 
         * Open add dialog
         */
        self.openAddDialog = function() {
            return $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'actionsCtl',
                templateUrl: 'js/directives/actions/addAction.html',
                parent: angular.element(document.body),
                clickOutsideToClose: false
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
                        if( resp && resp.data && typeof(resp.data.error)!=='undefined' && resp.data.error===false )
                        {
                            toast.success('Script uploaded');
                            $mdDialog.hide();
                            self.getScripts();
                        }
                        else
                        {
                            toast.error(resp.data.message);
                        }
                    }, function(err) {
                        toast.error('Upload failed: '+err);
                    });
            }
        });

        /**
         * Get scripts
         */
        self.getScripts = function() {
            actionsService.getScripts()
                .then(function(resp) {
                    self.scripts = resp;
                });
        };

        /**
         * Disable/enable specified script
         */
        self.disableScript = function(script, disabled) {
            actionsService.disableScript(script, disabled)
                .then(function(resp) {
                    //message info
                    if( disabled ) {
                        toast.success('Script is disabled');
                    } else {
                        toast.success('Script is enabled');
                    }

                    //refresh scripts
                    self.getScripts();
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
            //load scripts
            self.getScripts();
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
RaspIot.directive('actionsConfigDirective', ['$q', 'toastService', 'actionsService', 'confirmService', '$mdDialog', actionsConfigDirective]);

