
var actionConfigDirective = function($q, growl, blockUI, actionService) {
    var container = null;

    var actionController = ['$scope', function($scope) {
        var datetimeFormat = 'DD/MM/YYYY HH:mm:ss';
        $scope.scripts = [];
        $scope.uploadData = {
            'command': 'add_script',
            'to': 'action'
        };

        /**
         * Get scripts
         */
        function getScripts() {
            actionService.getScripts()
                .then(function(resp) {
                    var scripts = [];
                    for(var i=0; i<resp.length; i++) {
                        resp[i].last = moment.unix(resp[i].last_execution).format(datetimeFormat);
                        scripts.push(resp[i]);
                    }
                    $scope.scripts = resp;
                });
        };

        /**
         * Init controller
         */
        function init() {
            //load scripts
            getScripts();
        };

        /**
         * Upload started
         */
        $scope.uploadStarted = function() {
            container.start();
        };

        /**
         * Upload complete callback
         */
        $scope.uploadComplete = function(resp) {
            if( resp && resp.data && typeof(resp.data.error)!=='undefined' && resp.data.error===false )
            {
                growl.success('Script uploaded');
                getScripts();
            }
            else
            {
                growl.error(resp.data.message);
            }
            container.stop();
        };

        /**
         * Delete specified script
         */
        $scope.delScript = function(script) {
            //confirmation
            if( !confirm('Delete script?') )
            {
                return;
            }

            //delete script
            container.start();
            actionService.delScript(script)
                .then(function() {
                    //message
                    growl.success('Script deleted');

                    //refresh scripts
                    getScripts();
                })
                .finally(function() {
                    container.stop();
                });
        };

        /**
         * Disable/enable specified script
         */
        $scope.disableScript = function(script, disabled) {
            container.start();
            actionService.disableScript(script, disabled)
                .then(function(resp) {
                    //message info
                    if( disabled ) {
                        growl.success('Script is disabled');
                    } else {
                        growl.success('Script is enabled');
                    }

                    //refresh scripts
                    getScripts();
                })
                .finally(function() {
                    container.stop();
                });
        };

        //init directive
        init();
    }];

    var actionLink = function(scope, element, attrs) {
        container = blockUI.instances.get('actionContainer');
        container.reset();
    };

    return {
        templateUrl: 'js/directives/action/action.html',
        replace: true,
        scope: true,
        controller: actionController,
        link: actionLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('actionConfigDirective', ['$q', 'growl', 'blockUI', 'actionService', actionConfigDirective]);
