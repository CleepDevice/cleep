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
    tmpl =  '<div class="block-ui-overlay"></div>';
    tmpl += '<div layout="column" layout-align="center center" class="block-ui-message-container">';
    tmpl += '  <md-card style="display: inline-block; text-align: left;" md-colors="::{backgroundColor: \'default-primary-100\'}">';
    tmpl += '    <md-card-title>';
    tmpl += '      <md-card-title-media>';
    tmpl += '        <div class="md-media-sm card-media" layout>';
    tmpl += '          <md-icon ng-if="state.icon!==undefined && state.icon!==null" class="icon-xl" md-svg-icon="{{state.icon}}"></md-icon>';
    tmpl += '          <md-progress-circular ng-if="state.spinner===undefined || state.spinner===true" md-mode="indeterminate" style="margin-top:14px; margin-left:10px;">';
    tmpl += '        </div>';
    tmpl += '      </md-card-title-media>';
    tmpl += '      <md-card-title-text>';
    tmpl += '        <span class="md-headline">{{state.message}}</span>';
    tmpl += '        <span ng-if="state.submessage" class="md-subhead">{{state.submessage}}</span>';
    tmpl += '      </md-card-title-text>';
    tmpl += '    </md-card-title>';
    tmpl += '  </md-card>';
    tmpl += '</div>';
    blockUIConfig.template = tmpl;
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

