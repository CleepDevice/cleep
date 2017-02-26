
var actionConfigDirective = function($q, toast, actionService, uploadFile, confirm) {

    var actionController = ['$scope', function($scope) {
        var datetimeFormat = 'DD/MM/YYYY HH:mm:ss';
        var self = this;
        self.scripts = [];
        self.uploadFile = null;
        self.showAddPanel = false;

        $scope.$watch(function() {
            return self.uploadFile;
        }, function(file) {
            if( file )
            {
                //launch upload
                toast.loading('Uploading script...');
                uploadFile.upload('/upload', file, {
                    'command': 'add_script',
                    'to': 'action'
                }, self.onUploadSuccess, self.onUploadFailure);
            }
        });

        /**
         * Open add panel
         */
        self.openAddPanel = function() {
            self.showAddPanel = true;
        };

        self.closeAddPanel = function() {
            self.showAddPanel = false;
        };

        /**
         * Get scripts
         */
        self.getScripts = function() {
            actionService.getScripts()
                .then(function(resp) {
                    self.scripts = resp;
                });
        };

        /**
         * Init controller
         */
        self.init = function() {
            //load scripts
            self.getScripts();
        };

        /**
         * Upload complete callback
         */
        self.onUploadSuccess = function(resp) {
            //toast.hide();
            if( resp && resp.data && typeof(resp.data.error)!=='undefined' && resp.data.error===false )
            {
                toast.success('Script uploaded');
                self.getScripts();
                self.closeAddPanel();
            }
            else
            {
                toast.error(resp.data.message);
            }
        };

        /**
         * Upload failure
         */
        self.onUploadFailure = function(err) {
            toast.error('Upload failed: '+err);
        };

        /**
         * Delete specified script
         */
        self.deleteScript = function(script) {
            confirm.dialog('Delete script ?')
                .then(function() {
                    //delete script
                    actionService.deleteScript(script)
                        .then(function() {
                            //message
                            toast.success('Script deleted');
                            //refresh scripts list
                            self.getScripts();
                        });
                });
        };

        /**
         * Disable/enable specified script
         */
        self.disableScript = function(script, disabled) {
            actionService.disableScript(script, disabled)
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

    }];

    var actionLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'js/directives/action/action.html',
        replace: true,
        controller: actionController,
        controllerAs: 'actionCtl',
        link: actionLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('actionConfigDirective', ['$q', 'toastService', 'actionService', 'uploadFileService', 'confirmService', actionConfigDirective]);
