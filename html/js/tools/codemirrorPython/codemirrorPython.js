/**
 * Codemirror python directive
 *
 * Usage: <div codemirror-python-directive></div>
 */
var codemirrorPythonDirective = function($rootScope, actionsService, toast, raspiotService, confirm, $routeParams, $mdDialog, $window) {

    var codemirrorPythonController = ['$scope', function($scope) {
        var self = this;
        self.script = null;
        self.header = '';
        self.code = '';
        self.codemirrorInstance = null;
        self.debugs = [];
        self.modified = false;
        self.debugging = false;
        self.showHeader = false;
        self.options = {
            mode : { 
                name: "python",
                version: 2,
                singleLineStringErrors: false
            },
            matchClosing: true,
            lineNumbers: true,
            tabSize: 2,
            readOnly: false,
            onLoad: function (cmInstance) {
                self.codemirrorInstance = cmInstance;
            
                //focus on editor
                cmInstance.focus();

                //add info until user saves its work
                cmInstance.on('change', function() {
                    self.modified = true;
                });
            }
        };

        /**
         * Launch debugging
         */
        self.debug = function()
        {
            //clear debug output
            self.debugs = [];
            self.debugging = true;

            if( self.modified )
            {
                //save source code first
                actionsService.saveScript(self.script, 'manual', self.header, self.code)
                    .then(function() {
                        self.modified = false;

                        //launch debug
                        actionsService.debugScript(self.script);
                    });
            }
            else
            {
                //launch debug
                actionsService.debugScript(self.script);
            }
        };

        /**
         * Save script
         */
        self.save = function()
        {
            actionsService.saveScript(self.script, 'manual', self.header, self.code)
                .then(function() {
                    toast.success('Action script saved');
                    self.modified = false;
                });
        };

        /**
         * Save as
         */
        self.saveAs = function(ev)
        {
            var dial = $mdDialog.prompt()
                .title('Save as')
                .textContent('Give new name to your action script')
                .placeholder('Name')
                .ariaLabel('Name')
                .initialValue(self.script)
                .targetEvent(ev)
                .ok('Save as')
                .cancel('Cancel');

            var newScript = null;

            $mdDialog.show(dial)
                .then(function(script) {
                    //check script name
                    if( !script.endsWith('.py') )
                    {
                        script += '.py';
                    }

                    //first of all save current script
                    newScript = script;
                    return actionsService.saveScript(self.script, 'manual', self.header, self.code);
                })
                .then(function() {
                    //then rename it
                    return actionsService.renameScript(self.script, newScript);
                })
                .then(function() {
                    //reload actions configuration
                    return raspiotService.reloadModuleConfig('actions');
                })
                .then(function() {
                    //and change page editor
                    $window.location.href = '#!/module/actions/edit/' + newScript;
                });
        }

        /**
         * Refresh editor
         */
        self.refreshEditor = function()
        {
            self.codemirrorInstance.refresh();
        };

        /**
         * Controller init
         */
        self.init = function(script)
        {
            //save script name
            self.script = script;

            //load script content
            actionsService.getScript(script)
                .then(function(resp) {
                    self.code = resp.data.code;
                    self.header = resp.data.header;
                    self.refreshEditor();
                });

            //catch debug message
            $rootScope.$on('actions.debug.message', function(event, uuid, params) {
                self.debugs.push(params);
            });

            $rootScope.$on('actions.debug.end', function(event, uuid, params) {
                self.debugging = false;
            });
        };

    }];

    var codemirrorPythonLink = function(scope, element, attrs, controller) {
        controller.init($routeParams.script);
    };

    return {
        restrict: 'AE',
        templateUrl: 'js/tools/codemirrorPython/codemirrorPython.html',
        replace: true,
        controller: codemirrorPythonController,
        controllerAs: 'codeCtl',
        link: codemirrorPythonLink
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.directive('codemirrorPythonDirective', ['$rootScope', 'actionsService', 'toastService', 'raspiotService', 'confirmService', '$routeParams', '$mdDialog', '$window', codemirrorPythonDirective]);

