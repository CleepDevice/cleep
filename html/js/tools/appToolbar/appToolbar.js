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
    
var RaspIot = angular.module('RaspIot');
RaspIot.directive('appToolbar', ['appToolbarService', appToolbarDirective]);

