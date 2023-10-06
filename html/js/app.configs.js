/**
 * Application modules configuration
 * This file configures:
 *  - router
 *  - theme
 *  - fonts provider
 */

var Cleep = angular.module('Cleep');
var currentTimestamp = Date.now();

/**
 * Routes configuration
 */
Cleep.config([
	'$routeProvider',
	'$locationProvider',
	function ($routeProvider, $locationProvider) {
		$locationProvider.hashPrefix('!');
		$routeProvider
			.when('/dashboard', {
				template: '<div dashboard-directive></div>',
			})
			.when('/modules', {
				template: '<div modules-directive></div>',
			})
			.when('/install', {
				template: '<div install-directive></div>',
			})
			.when('/module/:name', {
				template: '<div module-directive></div>',
			})
			.when('/module/:name/:page', {
				template: '<div page-directive></div>',
			})
			.otherwise({
				redirectTo: '/dashboard',
			});
	},
]);

/**
 * Disable aria warnings
 */
Cleep.config(function ($mdAriaProvider) {
	$mdAriaProvider.disableWarnings();
});

/**
 * Http interceptor to resolve cache problems
 */
Cleep.config(function ($templateRequestProvider) {
	$templateRequestProvider.httpOptions({ _isTemplate: true });
})
	.factory('noCacheInterceptor', function ($templateCache) {
		return {
			request: function (config) {
				if (config._isTemplate) {
					return config;
				}
				if (
					config.url.indexOf('.html') !== -1 ||
					config.url.indexOf('.json') !== -1 ||
					config.url.indexOf('.svg') !== -1 ||
					config.url.indexOf('.css') !== -1
				) {
					config.url = config.url + '?t=' + currentTimestamp;
				}
				return config;
			},
		};
	})
	.config(function ($httpProvider) {
		$httpProvider.interceptors.push('noCacheInterceptor');
	});

Cleep.factory('$exceptionHandler', [
	'$log',
	'$injector',
	function ($log, $injector) {
		return function myExceptionHandler(exception, cause) {
			// classic log in console
			$log.error(exception, cause);

			if (typeof exception === 'string' && exception.startsWith('Possibly')) {
				// should be already handled by a service
				return;
			}
			var toastService = $injector.get('toastService');
			var locationService = $injector.get('$location');
			if (
				toastService &&
				locationService &&
				locationService.url().startsWith('/module/')
			) {
				toastService.fatal(
					'Failed to load ' +
						locationService.url().split('/').pop() +
						' application'
				);
			}
		};
	},
]);

/**
 * Theme configuration
 */
Cleep.config([
	'$mdThemingProvider',
	function ($mdThemingProvider) {
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
	},
]);

/**
 * Font configuration
 * Disabled for now, ligatures are not supported by typicons
 */
/*Cleep.config(['$mdIconProvider', function($mdIconProvider) {
    $mdIconProvider
        .iconSet('typicons', 'fonts/typicons.svg', 24)
}]);*/

/**
 * Blockui configuration
 */
Cleep.config([
	'blockUIConfig',
	function (blockUIConfig) {
		tmpl = '<div class="block-ui-overlay"></div>';
		tmpl +=
			'<div layout="column" layout-align="center center" class="block-ui-message-container">';
		tmpl +=
			'  <md-card style="display: inline-block; text-align: left;" md-colors="::{backgroundColor: \'default-primary-100\'}">';
		tmpl += '    <md-card-title>';
		tmpl += '      <md-card-title-media>';
		tmpl += '        <div class="md-media-sm card-media" layout>';
		tmpl +=
			'          <cl-icon ng-if="state.icon!==undefined && state.icon!==null" class="icon-xl" cl-mdi="{{ state.icon }}"></cl-icon>';
		tmpl +=
			'          <md-progress-circular ng-if="state.spinner===undefined || state.spinner===true" md-mode="indeterminate" style="margin-top:14px; margin-left:10px;">';
		tmpl += '        </div>';
		tmpl += '      </md-card-title-media>';
		tmpl += '      <md-card-title-text>';
		tmpl += '        <span class="md-headline">{{state.message}}</span>';
		tmpl +=
			'        <span ng-if="state.submessage" class="md-subhead">{{state.submessage}}</span>';
		tmpl += '      </md-card-title-text>';
		tmpl += '    </md-card-title>';
		tmpl += '  </md-card>';
		tmpl += '</div>';
		blockUIConfig.template = tmpl;
		blockUIConfig.autoBlock = false;
	},
]);

/**
 * Lazyload configuration
 */
Cleep.config([
	'$ocLazyLoadProvider',
	function ($ocLazyLoadProvider) {
		$ocLazyLoadProvider.config({
			debug: false,
			events: false,
		});
	},
]);
