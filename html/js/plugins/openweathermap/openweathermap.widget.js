/**
 * Openweather widget directive
 * Display openweathermap dashboard widget
 * @see owm=>weather-icons associations from https://gist.github.com/tbranyen/62d974681dea8ee0caa1
 */
var widgetOpenweathermapDirective = function(raspiotService, $mdDialog, $q, openweathermapService) {

    var widgetOpenweathermapController = ['$scope', function($scope) {
        var self = this;
        self.device = $scope.device;
        self.loading = true;
        self.selection = 'Temperature';
        self.unit = null;
        self.windData = [];
        self.humidityData = [];
        self.temperatureData = [];
        self.pressureData = [];
        self.forecastData = [];
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
        /*self.customTimeFormat = d3.time.format.multi([
            ["%H:%M", function(d) { return d.getMinutes(); }], 
            ["%H", function(d) { return d.getHours(); }], 
            ["%a %d", function(d) { return d.getDay() && d.getDate() != 1; }], 
            ["%b %d", function(d) { return d.getDate() != 1; }], 
            ["%B", function(d) { return d.getMonth(); }], 
            ["%Y", function() { return true; }]
        ]);*/
        self.customTimeFormat = d3.time.format.multi([
            ["%a %H:%M", function(d) { return d.getMinutes(); }], 
            ["%a %H:%M", function() { return true; }]
        ]);
        self.graphOptions = {
            chart: {
                type: 'stackedAreaChart',
                height: 200,
                margin : {
                    top: 20,
                    right: 20,
                    bottom: 30,
                    left: 60
                },
                x: function(d){return d[0];},
                y: function(d){return d[1];},
                useVoronoi: false,
                clipEdge: true,
                duration: 500,
                useInteractiveGuideline: true,
                xAxis: {
                    showMaxMin: false,
                    tickFormat: function(d) {
                        return self.customTimeFormat(moment(d,'X').toDate());
                    }
                },
                yAxis: {
                    axisLabel: '',
                    axisLabelDistance: -15,
                },
                showControls: false,
                showLegend: false
            },
            title: {
                enable: false,
                text: ''
            }
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
         * Load forecast when opening dialog
         */
        self.loadDialogData = function()
        {
            openweathermapService.getForecast()
                .then(function(forecast) {
                    //clear data
                    self.windData = [];
                    self.temperatureData = [];
                    self.pressureData = [];
                    self.humidityData = [];

                    //fill data
                    for( var i=0; i<forecast.data.length; i++ )
                    {
                        var ts = forecast.data[i].dt;
                        self.windData.push([ts, forecast.data[i].wind.speed]);
                        self.humidityData.push([ts, forecast.data[i].main.humidity]);
                        self.pressureData.push([ts, forecast.data[i].main.pressure]);
                        self.temperatureData.push([ts, forecast.data[i].main.temp]);
                    }

                    //set current forecast data (temperature at opening)
                    self.change(null);

                    //disable flag loading
                    self.loading = false;
                });
        };

        /**
         * Change type of charts
         */
        self.change = function(type)
        {
            if( self.selection!==type )
            {
                if( type==='humidity' )
                {
                    self.unit = '%';
                    self.graphOptions.chart.color = ['#3F51B5'];
                    self.graphOptions.chart.yAxis.axisLabel = self.unit;
                    self.forecastData = [{
                        key: 'Humidity',
                        values: self.humidityData
                    }];
                    self.selection = 'Humidity';
                }
                else if( type==='pressure' )
                {
                    self.unit = 'hPa';
                    self.graphOptions.chart.color = ['#CDDC39'];
                    self.graphOptions.chart.yAxis.axisLabel = self.unit;
                    self.forecastData = [{
                        key: 'Pressure',
                        values: self.pressureData
                    }];
                    self.selection = 'Pressure';
                }
                else if( type==='wind' )
                {
                    self.unit = 'm/s';
                    self.graphOptions.chart.color = ['#03A9F4'];
                    self.graphOptions.chart.yAxis.axisLabel = self.unit;
                    self.forecastData = [{
                        key: 'Wind',
                        values: self.windData
                    }];
                    self.selection = 'Wind';
                }
                else
                {
                    self.unit = '°C';
                    self.graphOptions.chart.color = ['#FF9800'];
                    self.graphOptions.chart.yAxis.axisLabel = self.unit;
                    self.forecastData = [{
                        key: 'Temperature',
                        values: self.temperatureData
                    }];
                    self.selection = 'Temperature';
                }
            }
        };

        /**
         * Open dialog
         */
        self.openDialog = function() {
            self.loading = true;
            self.forecastData = [];
            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'owmCtl',
                templateUrl: 'openweathermapDialog.widget.html',
                parent: angular.element(document.body),
                clickOutsideToClose: true,
                onComplete: self.loadDialogData
            });
        };

        $scope.$on('$destroy', function() {
            //workaround to remove tooltips when dialog is closed: dialog is closed before 
            //nvd3 has time to remove tooltips elements
            var tooltips = $("div[id^='nvtooltip']");
            for( var i=0; i<tooltips.length; i++ )
            {
                tooltips[i].remove();
            }
            self.forecastData = [];
        });

        /**
         * Init controller
         */
        self.init = function(el)
        {
        };

    }];

    var widgetOpenweathermapLink = function(scope, element, attrs, controller) {
        controller.init(element);
    };

    return {
        restrict: 'EA',
        templateUrl: 'openweathermap.widget.html',
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
RaspIot.directive('widgetOpenweathermapDirective', ['raspiotService', '$mdDialog', '$q', 'openweathermapService', widgetOpenweathermapDirective]);

