/**
 * Main application
 */
var RaspIot = angular.module('RaspIot', ['ngMaterial', 'ngAnimate', 'angular-growl', 'ui.bootstrap', 'blockUI', 'base64', 'daterangepicker', 'lr.upload', 'md.data.table', 'ngMaterialDatePicker']);

/**
 * Materiel configuration
 */
RaspIot.config(['$mdThemingProvider', function($mdThemingProvider) {
    $mdThemingProvider.theme('default')
        .primaryPalette('teal')
        .accentPalette('deep-orange')
        .warnPalette('red')
        .backgroundPalette('grey');
    $mdThemingProvider.theme('dark')
        .primaryPalette('teal')
        .dark();
    $mdThemingProvider.theme('alt')
        .primaryPalette('deep-orange');
    $mdThemingProvider.theme('alt-dark')
        .primaryPalette('deep-orange')
        .dark();
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
