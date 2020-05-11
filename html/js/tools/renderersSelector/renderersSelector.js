/**
 * Renderers selector directive
 *
 * Usage:
 * <div renderers-selector selected-renderers="" allowed-renderer-types=""></div>
 *
 * Params:
 * selected-renderers (array<string>): list of selected renderers (input and output parameter)
 * allowed-renderer-types (array <string>): list of allowed renderers
 */
var renderersSelectorDirective = function($q, $rootScope, cleepService) {

    var renderersSelectorController = ['$scope', function($scope) {
        var self = this;
        self.allRenderers = [];
        self.renderers = [];
        self.groups = [];
        self.allowedRendererTypes = [];
        self.initialized = false;

        /**
         * Init controller
         */
        self.init = function()
        {
            //prepare renderers list splitting type.subtype
            var renderers = [];
            var groups = [];
            for( var group in cleepService.renderers )
            {
                if( self.allowedRendererTypes.indexOf(group)>=0 )
                {
                    groups.push(group);
                    for( var i=0; i<cleepService.renderers[group].length; i++ )
                    {
                        renderers.push({
                            group: group,
                            label: cleepService.renderers[group][i],
                            value: cleepService.renderers[group][i]
                        });
                    }
                }
            }
            self.groups = groups;
            self.allRenderers = renderers;

            //set selected renderers
            self.renderers = $scope.selectedRenderers;
            
            //set initialized flag
            self.initialized = true;
        };

        /**
         * Update selected renderers each time user select a renderer
         */
        $scope.$watchCollection(
            function() {
                return self.renderers;
            },
            function(newVal, oldVal) {
                //update input parameter
                if( self.initialized )
                {
                    $scope.selectedRenderers = newVal
                }
            }
        );

        /**
         * Init controller as soon as renderers are loaded
         */
        $scope.$watchCollection(
            function() {
                return cleepService.renderers;
            },
            function(newValue, oldValue) {
                self.init();
            }
        );

    }];

    var renderersSelectorLink = function(scope, element, attrs, controller) {
        if( !angular.isUndefined(scope.allowedRendererTypes) )
        {
            controller.allowedRendererTypes = scope.allowedRendererTypes;
        }
    };

    return {
        restrict: 'AE',
        templateUrl: 'js/tools/renderersSelector/renderersSelector.html',
        replace: true,
        scope: {
            selectedRenderers: '=',
            allowedRendererTypes: '='
        },
        controller: renderersSelectorController,
        controllerAs: 'rendererCtl',
        link: renderersSelectorLink
    };

};
    
var Cleep = angular.module('Cleep');
Cleep.directive('renderersSelector', ['$q', '$rootScope', 'cleepService', renderersSelectorDirective]);

