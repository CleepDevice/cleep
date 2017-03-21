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
        .when('/configuration', {
            template: '<div configuration-directive></div>'
        })
        .otherwise({
            redirectTo: '/dashboard'
        });
    //$locationProvider.html5Mode(true);
}]);

/**
 * Theme configuration
 */
RaspIot.config(['$mdThemingProvider', function($mdThemingProvider) {
    $mdThemingProvider
        .theme('default')
        .primaryPalette('blue-grey')
        .accentPalette('orange');
        //.backgroundPalette('grey')
        //.dark();
    $mdThemingProvider
        .theme('dark')
        .primaryPalette('blue-grey')
        .accentPalette('orange')
        .dark();
    /*$mdThemingProvider
        .theme('alt')
        .primaryPalette('blue-grey')
        .accentPalette('amber');
    $mdThemingProvider
        .theme('alt-dark')
        .primaryPalette('blue-grey')
        .accentPalette('amber')
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

