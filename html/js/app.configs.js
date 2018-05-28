/**
 * Application modules configuration
 * This file configures:
 *  - router
 *  - theme
 *  - fonts provider
 */

var RaspIot = angular.module('RaspIot');

/**
 * Routes configuration
 */
RaspIot.config(['$routeProvider', '$locationProvider', function($routeProvider, $locationProvider) {
    $locationProvider.hashPrefix('!');
    $routeProvider
        .when('/dashboard', {
            template: '<div dashboard-directive></div>'
        })
        .when('/modules', {
            template: '<div modules-directive></div>'
        })
        .when('/install', {
            template: '<div install-directive></div>'
        })
        .when('/module/:name', {
            template: '<div module-directive></div>'
        })
        .when('/module/actions/edit/:script', {
            template: '<div codemirror-python-directive></div>'
        })
        .otherwise({
            redirectTo: '/dashboard'
        });
}]);

/**
 * Theme configuration
 */
RaspIot.config(['$mdThemingProvider', function($mdThemingProvider) {
    $mdThemingProvider
        .theme('default')
        .primaryPalette('blue-grey')
        .accentPalette('red')
        .backgroundPalette('grey');
    $mdThemingProvider
        .theme('dark')
        .primaryPalette('amber')
        .accentPalette('blue')
        .dark();

    /*$mdThemingProvider
        .theme('default')
        .primaryPalette('blue')
        .accentPalette('orange')
        .backgroundPalette('grey');
    $mdThemingProvider
        .theme('dark')
        .primaryPalette('blue')
        .accentPalette('orange')
        .backgroundPalette('grey')
        .dark();*/
}]);

/**
 * Font configuration
 * Disabled for now, ligatures are not supported by typicons
 */
/*RaspIot.config(['$mdIconProvider', function($mdIconProvider) {
    $mdIconProvider
        .iconSet('typicons', 'fonts/typicons.svg', 24)
}]);*/

/**
 * Fix issue with md-datepicker with angular 1.6 and angular-material 1.1.1
 * @see https://github.com/angular/material/issues/10280
 */
RaspIot.config(['$compileProvider', function($compileProvider) {
    $compileProvider.preAssignBindingsEnabled(true);
}]);

/**
 * MDI font configuration
 */
RaspIot.config(['$mdIconProvider', function($mdIconProvider) {
    $mdIconProvider.defaultIconSet('fonts/mdi.svg')
}]);


/**
 * Blockui configuration
 */
RaspIot.config(['blockUIConfig', function(blockUIConfig) {
    //use md-colors to set text color: md-colors="{color:'primary'}"
    blockUIConfig.template = '<div class="block-ui-overlay"></div><div layout="column" layout-align="center center" class="block-ui-message-container"><div ng-if="state.spinner===undefined || state.spinner===true"><md-progress-circular class="md-accent" md-mode="indeterminate"></md-progress-circular></div><div ng-if="state.icon!==undefined"><md-icon class="icon-xl md-accent" md-svg-icon="{{state.icon}}"></md-icon></div><div>&nbsp;</div><div><span class="md-subhead">{{ state.message }}</span></div></div>';
    blockUIConfig.autoBlock = false;
}]);

/**
 * Lazyload configuration
 */
RaspIot.config(['$ocLazyLoadProvider', function($ocLazyLoadProvider) {
    $ocLazyLoadProvider.config({
       debug: false,
       events: false
    });
}]);

