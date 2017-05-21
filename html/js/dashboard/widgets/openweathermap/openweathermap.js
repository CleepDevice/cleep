/**
 * Openweather widget directive
 * Display openweathermap dashboard widget
 * @see owm=>weather-icons associations from https://gist.github.com/tbranyen/62d974681dea8ee0caa1
 */
var widgetOpenweathermapDirective = function(raspiotService, $mdDialog, $q) {

    var widgetOpenweathermapController = ['$scope', function($scope) {
        var self = this;
        self.device = $scope.device;
        self.hasDatabase = raspiotService.hasModule('database');
        self.icons = {
            200: 'storm-showers',
            201: 'storm-showers',
            202: 'storm-showers',
            210: 'storm-showers',
            211: 'thunderstorm',
            212: 'thunderstorm',
            221: 'thunderstorm',
            230: 'storm-showers',
            231: 'storm-showers',
            232: 'storm-showers',
            300: 'sprinkle',
            301: 'sprinkle',
            302: 'sprinkle',
            310: 'sprinkle',
            311: 'sprinkle',
            312: 'sprinkle',
            313: 'sprinkle',
            314: 'sprinkle',
            321: 'sprinkle',
            500: 'rain',
            501: 'rain',
            502: 'rain',
            503: 'rain',
            504: 'rain',
            511: 'rain-mix',
            520: 'showers',
            521: 'showers',
            522: 'showers',
            531: 'showers',
            600: 'snow',
            601: 'snow',
            602: 'snow',
            611: 'sleet',
            612: 'sleet',
            615: 'rain-mix',
            616: 'rain-mix',
            620: 'rain-mix',
            621: 'rain-mix',
            622: 'rain-mix',
            701: 'sprinkle',
            711: 'smoke',
            721: 'day-haze',
            731: 'cloudy-gusts',
            741: 'fog',
            751: 'cloudy-gusts',
            761: 'dust',
            762: 'smog',
            771: 'day-windy',
            781: 'tornado',
            800: 'sunny',
            801: 'cloudy',
            802: 'cloudy',
            803: 'cloudy',
            804: 'cloudy',
            900: 'tornado',
            901: 'hurricane',
            902: 'hurricane',
            903: 'snowflake-cold',
            904: 'hot',
            905: 'windy',
            906: 'hail',
            951: 'sunny',
            952: 'cloudy-gusts',
            953: 'cloudy-gusts',
            954: 'cloudy-gusts',
            955: 'cloudy-gusts',
            956: 'cloudy-gusts',
            957: 'cloudy-gusts',
            958: 'cloudy-gusts',
            959: 'cloudy-gusts',
            960: 'thunderstorm',
            961: 'thunderstorm',
            962: 'cloudy-gusts'
        };

        /**
         * Return weather-icons icon
         */
        self.getIconClass = function()
        {
            if( self.icons[self.device.code] )
            {
                if( self.device.icon.endsWith('d.png') )
                {
                    //day icon
                    return 'wi wi-day-' + self.icons[self.device.code];
                }
                else if( self.device.icon.endsWith('n.png') ) 
                {
                    //night icon
                    return 'wi wi-day-' + self.icons[self.device.code];
                }
                else
                {
                    //invariable icon
                    return 'wi wi-' + self.icons[self.device.code];
                }
            }
            else
            {
                return 'wi wi-na';
            }
        };

        /**
         * Return weather-icons wind icon
         */
        self.getWindClass = function()
        {
            if( self.device.wind_direction )
            {
                return 'wi wi-wind wi-towards-' + self.device.wind_direction.toLowerCase();
            }
            else
            {
                return 'wi wi-na';
            }
        };

        /**
         * Cancel dialog
         */
        self.cancelDialog = function()
        {
            $mdDialog.cancel();
        };

        /**
         * Open dialog
         */
        self.openDialog = function() {
            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'owmCtl',
                templateUrl: 'js/dashboard/widgets/openweathermap/openweathermapDialog.html',
                parent: angular.element(document.body),
                clickOutsideToClose: true,
                onComplete: self.loadDialogData
            });
        };

        /**
         * Init controller
         */
        self.init = function()
        {
        };

    }];

    var widgetOpenweathermapLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        restrict: 'EA',
        templateUrl: 'js/dashboard/widgets/openweathermap/openweathermap.html',
        replace: true,
        scope: {
            'device': '='
        },
        controller: widgetOpenweathermapController,
        controllerAs: 'widgetCtl',
        link: widgetOpenweathermapLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('widgetOpenweathermapDirective', ['raspiotService', '$mdDialog', '$q', widgetOpenweathermapDirective]);

