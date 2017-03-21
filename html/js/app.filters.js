/**
 * Application filters definitions
 */

var RaspIot = angular.module('RaspIot');

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
RaspIot.filter('filterDeviceByService', function($filter) {
    return function(devices, service) {
        if( service ) {
            return $filter("filter")(devices, function(device) {
                return device.__serviceName==service;
            });
        }
    };
});

/**
 * Timestamp to human readable string
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

/**
 * Time to human readable string
 */
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

