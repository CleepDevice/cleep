/**
 * Graph button
 * Display a button that opens graph dialog
 *
 * Directive example:
 * <div graph-button device="<device>" options="<options>"></div
 * @param device: device object
 * @param options: graph options. An object with the following format:
 *  {
 *      'type': <'bar', 'line'> : type of graph (string) (mandatory)
 *      'filters': ['fieldname1', ...]: list of field names to display (array) (optional)
 *      'timerange': { (optional)
 *          'start': <timestamp>: start range timestamp (integer)
 *          'end': <timestamp>: end range timestamp (integer)
 *      }
 *  }
 */
var graphButtonDirective = function($q, $rootScope, graphService, $mdDialog, toast) {

    var graphButtonController = ['$scope', function($scope) {
        var self = this;
        self.buttonLabel = '';
        self.buttonClass = 'md-fab md-mini';

        /**
         * Cancel dialog
         */
        self.cancelDialog = function() {
            $mdDialog.cancel();
        };

        /**
         * Open graph dialog
         */
        self.openGraphDialog = function() {
            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'graphButtonCtl',
                templateUrl: 'js/tools/graphButton/graphDialog.html',
                parent: angular.element(document.body),
                clickOutsideToClose: true,
                fullscreen: true,
                escapeToClose: false //disable esc key to avoid tooltip issue
            });
        };
    
    }];

    var graphButtonLink = function(scope, element, attrs, controller) {
        controller.device = scope.device;
        controller.graphOptions = scope.graphOptions;
        if( !angular.isUndefined(scope.buttonLabel) )
        {
            controller.buttonLabel = scope.buttonLabel;
        }
        if( !angular.isUndefined(scope.buttonClass) )
        {
            controller.buttonClass = scope.buttonClass;
        }
    };

    return {
        restrict: 'AE',
        templateUrl: 'js/tools/graphButton/graphButton.html',
        replace: true,
        scope: {
            device: '=',
            graphOptions: '=graphOptions',
            buttonLabel: '@',
            buttonClass: '@'
        },
        controller: graphButtonController,
        controllerAs: 'graphButtonCtl',
        link: graphButtonLink
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.directive('graphButton', ['$q', '$rootScope', 'graphService', '$mdDialog', 'toastService', graphButtonDirective]);

