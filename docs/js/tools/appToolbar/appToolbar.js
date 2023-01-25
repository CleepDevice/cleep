/**
 * AppToolbar
 * Display a toolbar of buttons in top application toolbar
 *
 * Directive example:
 * <app-toolbar></app-toolbar>
 */
var appToolbarDirective = function(appToolbarService) {

    var appToolbarController = ['$scope', function($scope) {
        var self = this;
        self.buttons = appToolbarService.buttons;

        /**
         * Action button click
         */
        self.click = function(btn) {
            btn.click();
        };
    }];

    var appToolbarLink = function(scope, element, attrs, controller) {
        //nothing to do here
    };

    return {
        restrict: 'AE',
        templateUrl: 'js/tools/appToolbar/appToolbar.html',
        replace: true,
        scope: {
        },
        controller: appToolbarController,
        controllerAs: 'appToolbarCtl',
        link: appToolbarLink
    };

};
    
var Cleep = angular.module('Cleep');
Cleep.directive('appToolbar', ['appToolbarService', appToolbarDirective]);

