/**
 * Main application
 */
var RaspIot = angular.module('RaspIot', ['ngMaterial', 'ngAnimate', 'ngMessages', 'ngRoute', 'angular-growl', /*'ui.bootstrap',*/ 'blockUI', 'base64', /*'daterangepicker', 'lr.upload',*/ 'md.data.table']);

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
        .primaryPalette('teal')
        .accentPalette('yellow')
        .backgroundPalette('grey');
    $mdThemingProvider
        .theme('dark')
        .primaryPalette('teal')
        .accentPalette('yellow')
        .dark();
    $mdThemingProvider
        .theme('alt')
        .primaryPalette('blue-grey')
        .accentPalette('amber');
    $mdThemingProvider
        .theme('alt-dark')
        .primaryPalette('blue-grey')
        .accentPalette('amber')
        .dark();
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
 * BlockUI configuration
 */
RaspIot.config(['blockUIConfig', function(blockUIConfig) {
    blockUIConfig.autoBlock = false;
    blockUIConfig.autoInjectBodyBlock = false;
    blockUIConfig.template = '<div flex><md-progress-circular md-mode="indeterminate" class="md-primary"></md-progress-circular></div>';
}]);

/**
 * Capitalize filter
 * @source http://stackoverflow.com/a/30207330
 */
RaspIot.filter('capitalize', function() {
    return function(str) {
        return (!!str) ? str.charAt(0).toUpperCase() + str.substr(1).toLowerCase() : '';
    };
});

/**
 * Service name filter
 */
RaspIot.filter('serviceName', function() {
    return function(str) {
        var tmp = str.replace('Service','');
        return (!!tmp) ? tmp.charAt(0).toUpperCase() + tmp.substr(1).toLowerCase() : '';
    };
});

/**
 * Device type filter
 */
RaspIot.filter('deviceType', function($filter) {
    return function(devices, type) {
        if( type ) {
            return $filter("filter")(devices, function(device) {
                return device.__type==type;
            });
        }
    };
});

/**
 * Device service filter
 */
RaspIot.filter('deviceService', function($filter) {
    return function(devices, service) {
        if( service ) {
            return $filter("filter")(devices, function(device) {
                return device.__serviceName==service;
            });
        }
    };
});

/**
 * Timestamp to human readable datetime
 */
RaspIot.filter('hrDatetime', function($filter) {
    return function(ts) {
        if( angular.isUndefined(ts) || ts===null )
        {
            return '-';
        }
        else
        {
            return moment.unix(ts).format('DD/MM/YYYY HH:mm:ss');
        }
    };
});

RaspIot.filter('hrTime', function($filter) {
    return function(ts, withSeconds) {
        if( angular.isUndefined(ts) || ts===null )
        {
            return '-';
        }
        else
        {
            if( withSeconds ) {
                return moment.unix(ts).format('HH:mm:ss');
            } else {
                return moment.unix(ts).format('HH:mm');
            }
        }
    };
});

/**
 * http://jamesroberts.name/blog/2010/02/22/string-functions-for-javascript-trim-to-camel-case-to-dashed-and-to-underscore/
 * String functions
 */
String.prototype.toCamel = function(){
        return this.replace(/(\-[a-z])/g, function($1){return $1.toUpperCase().replace('-','');});
};

String.prototype.toDash = function(){
        return this.replace(/([A-Z])/g, function($1){return "-"+$1.toLowerCase();});
};

String.prototype.toUnderscore = function(){
        return this.replace(/([A-Z])/g, function($1){return "_"+$1.toLowerCase();});
};

String.prototype.trim = function(){
        return this.replace(/^\s+|\s+$/g, "");
};
