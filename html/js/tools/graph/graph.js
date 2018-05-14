/**
 * Graph directive
 * Display graph of specified device values
 *
 * Directive example:
 * <chart device="<device>" options="<options>"></div>
 *
 * @param device: device object
 * @param options: chart options. An object with the following format
 *  {
 *    type (bar|line)     : type of graph (optional, default line)
 *    filters (array)     : list of field names to display (optional, default all fields)
 *    timerange (obj)     : timerange to display at opening (optional, default 1 day until now)
 *                          { 
 *                              start (timestamp): start range timestamp
 *                              end (timestamp)  : end range timestamp
 *                          }
 *    format (callback)   : callback to convert value to specific format (optional, default is raw value) 
 *                          Format infos available here https://github.com/d3/d3-format
 *    label (string)      : value label,
 *    height (int)        : graph height (optional, default 400px)
 *    color (string)      : color hex code (starting with #). Only used for single data
 *    loadData (callback) : callback that returns data to display (mandatory for pie chart).
 *                          Callback parameters:
 *                              - start (timestamp): start timestamp
 *                              - end (timestamp)  : end timestamp
 *                          Returns: callback must return a promise
 *    showControls (bool) : display or not controls (time range...) (optional, default is true)
 *  }
 */
var graphDirective = function($q, $rootScope, graphService, toast) {

    var graphController = ['$scope', function($scope) {
        var self = this;
        self.device = null;
        self.options = null;
        self.loading = true;
        self.graphHeight = '400px';
        self.rangeSelector = 86400;
        self.rangeStart = 0;
        self.rangeEnd = 0;
        self.timestampStart = 0;
        self.timestampEnd = 0;
        self.showControls = true;

        //dynamic time format according to zoom
        /*self.customTimeFormat = d3.time.format.multi([
            ["%H:%M", function(d) { return d.getMinutes(); }], 
            ["%H", function(d) { return d.getHours(); }], 
            ["%a %d", function(d) { return d.getDay() && d.getDate() != 1; }], 
            ["%b %d", function(d) { return d.getDate() != 1; }], 
            ["%B", function(d) { return d.getMonth(); }], 
            ["%Y", function() { return true; }]
        ]);*/
        self.customTimeFormat = d3.time.format.multi([
            ["%m/%d/%y %H:%M", function(d) { return true; }], 
        ]);

        //bar graph default options
        self.historicalBarGraphOptions = {
            chart: {
                type: "historicalBarChart",
                height: 400,
                margin: {
                    top: 20,
                    right: 20,
                    bottom: 65,
                    left: 50
                },
                x: function(d){return d[0];},
                y: function(d){return d[1];},
                showValues: true,
                duration: 500,
                xAxis: {
                    //axisLabel: "X Axis",
                    //rotateLabels: 30,
                    showMaxMin: false,
                    tickFormat: function(d) {
                        return self.customTimeFormat(moment(d,'X').toDate());
                    },
                    scale: d3.time.scale()
                },
                yAxis: {
                    axisLabel: '',
                    axisLabelDistance: -15,
                    tickFormat: function(v) {
                        return self.defaultFormat(v);
                    }
                },
                tooltip: {
                    keyFormatter: function(d) {
                        return self.customTimeFormat(moment(d,'X').toDate());
                    }
                },
                zoom: {
                    enabled: true,
                    scaleExtent: [1,10],
                    useFixedDomain: true,
                    useNiceScale: false,
                    horizontalOff: false,
                    verticalOff: true,
                    unzoomEventType: "dblclick.zoom"
                }
            },
            title: {
                enable: false,
                text: ''
            }
        };

        //line graph default options
        self.stackedAreaGraphOptions = {
            chart: {
                type: 'stackedAreaChart',
                height: 400,
                margin : {
                    top: 20,
                    right: 20,
                    bottom: 30,
                    left: 40
                },
                x: function(d){return d[0];},
                y: function(d){return d[1];},
                useVoronoi: false,
                clipEdge: true,
                duration: 100,
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
                    tickFormat: function(v) {
                        return self.defaultFormat(v);
                    }
                },
                zoom: {
                    enabled: true,
                    scaleExtent: [1, 10],
                    useFixedDomain: false,
                    useNiceScale: false,
                    horizontalOff: false,
                    verticalOff: true,
                    unzoomEventType: 'dblclick.zoom'
                },
                showControls: false,
                showLegend: false
            },
            title: {
                enable: false,
                text: ''
            }
        };

        //pie graph default options
        self.pieGraphOptions = {
            chart: {
                type: "pieChart",
                height: 400,
                showLabels: true,
                duration: 500,
                labelThreshold: 0.05,
                labelType: 'percent',
                donut: true,
                donutRatio: 0.35,
                x: function(d) {
                    return d.key;
                },
                y: function(d) {
                    return self.defaultFormat(d.value);
                },
                legend: {
                    margin: {
                        top: 5,
                        right: 35,
                        bottom: 5,
                        left: 0
                    }
                }
            },
            title: {
                enable: false,
                text: ''
            }
        };

        //default value format callback
        self.defaultFormat = function(v) {
            return v;
        };

        //graph types<=>options mapping
        self.graphOptionsByType = {
            'line': self.stackedAreaGraphOptions,
            'bar': self.historicalBarGraphOptions,
            'pie': self.pieGraphOptions
        };

        //graph data and options
        self.graphData = [];
        self.graphOptions = {};

        //data for graph values request
        self.graphRequestOptions = {
            output: 'list',
            fields: [],
            sort: 'ASC'
        };

        /**
         * Prepare graph options according to directive options
         */
        self.__prepareGraphOptions = function() {
            //set graph request options and graph options
            if( !angular.isUndefined(self.options) && self.options!==null )
            {
                //graph type
                if( !angular.isUndefined(self.options.type) && self.options.type!==null )
                {
                    if( self.options.type=='line' )
                    {
                        self.graphRequestOptions.fields.output = 'list';
                        self.graphOptions = self.graphOptionsByType[self.options.type];
                    }
                    else if( self.options.type=='bar' )
                    {
                        self.graphRequestOptions.fields.output = 'list';
                        self.graphOptions = self.graphOptionsByType[self.options.type];
                    }
                    else if( self.options.type=='pie' )
                    {
                        self.graphRequestOptions.fields.output = 'dict';
                        self.graphOptions = self.graphOptionsByType[self.options.type];
                    }
                    else
                    {
                        //invalid type specified
                        toast.error('Invalid graph type specified');
                    }
                }

                //force graph height
                if( !angular.isUndefined(self.options.height) && self.options.height!==null )
                {
                    self.graphOptions.chart.height = self.options.height;
                    self.graphHeight = '' + self.options.height + 'px';
                }

                //fields filtering
                if( !angular.isUndefined(self.options.fields) && self.options.fields!==null )
                {
                    self.graphRequestOptions.fields = self.options.fields;
                }

                //force values format
                if( !angular.isUndefined(self.options.format) && self.options.format!==null )
                {
                    self.defaultFormat = self.options.format;
                }

                //force Y label
                if( !angular.isUndefined(self.options.label) && self.options.label!==null )
                {
                    self.graphOptions.chart.yAxis.axisLabel = self.options.label;
                    self.graphOptions.chart.margin.left = 60;
                }

                //force title
                if( !angular.isUndefined(self.options.title) && self.options.title!==null )
                {
                    self.graphOptions.title.enable = true;
                    self.graphOptions.title.text = self.options.title;
                }

                //force color
                if( !angular.isUndefined(self.options.color) && self.options.color!==null )
                {
                    self.graphOptions.chart.color = [self.options.color];
                }
            }
        };

        /**
         * Finalize graph options according to directive options
         * @param count: number of items in graph. Used to disable/enable legend
         */
        self.__finalizeGraphOptions = function(data) {
            var graphData = [];
            var count = 0;
            var name = null;

            if( self.options.type=='line' )
            {
                for( name in data )
                {
                    graphData.push({
                        'key': data[name].name,
                        'values': data[name].values
                    });
                    count++;
                }
            }
            else if( self.options.type=='bar' )
            {
                for( name in data )
                {
                    graphData.push({
                        'key': self.device[name].name,
                        'bar': true,
                        'values': data[name].values
                    });
                    count++;
                }
            }
            else if( self.options.type=='pie' )
            {
                for( name in data )
                {
                    graphData.push({
                        'key': data[name].name,
                        'value': data[name].value
                    });
                }
            }

            //force legend displaying
            if( count>1 && self.options.type!=='pie' )
            {
                self.graphOptions.chart.showLegend = true;
                self.graphOptions.chart.margin.top = 30;
            }   

            //set graph data and loading flag
            self.graphData = graphData;
            self.loading = false;
        };
    
        /**
         * Load graph data
         */
        self.loadGraphData = function(scope, el) {
            //set loading flag
            self.loading = true;

            //prepare graph options
            self.__prepareGraphOptions();

            //load graph data
            if( !angular.isUndefined(self.options.loadData) && self.options.loadData!==null )
            {
                //load user data
                self.options.loadData(self.timestampStart, self.timestampEnd)
                    .then(function(resp) {
                        self.__finalizeGraphOptions(resp);
                    }, function(err) {
                        //toast.error(err);
                    });
            }
            else
            {
                //load device data
                graphService.getDeviceData(self.device.uuid, self.timestampStart, self.timestampEnd, self.graphRequestOptions)
                    .then(function(resp) {
                        self.__finalizeGraphOptions(resp.data.data);
                    });
            }
        };

        /**
         * Change time range
         */
        self.changeRange = function()
        {
            //compute new timestamp range
            self.timestampEnd = Number(moment().format('X'));
            self.timestampStart = self.timestampEnd - self.rangeSelector;

            //load new graph data
            self.loadGraphData();
        };

        /**
         * Init controller
         */
        self.init = function()
        {
            //force user timestamp if provided
            if( !angular.isUndefined(self.options.timestamp) && self.options.timestamp!==null )
            {
                self.timestampStart = self.options.timestamp.start;
                self.timestampEnd = self.options.timestamp.end;
            }
            else
            {
                //set default timestamp range
                self.timestampEnd = Number(moment().format('X'));
                self.timestampStart = self.timestampEnd - self.rangeSelector;
            }

            //show controls
            if( !angular.isUndefined(self.options.showControls) )
            {
                self.showControls = self.options.showControls;
            }

            //load graph data
            self.loadGraphData();
        };

        /**
         * Destroy directive
         */
        $scope.$on('$destroy', function() {
            //workaround to remove tooltips when dialog is closed: dialog is closed before 
            //nvd3 has time to remove tooltips elements
            var tooltips = $("div[id^='nvtooltip']");
            for( var i=0; i<tooltips.length; i++ )
            {
                tooltips[i].remove();
            }
        });

    }];

    var graphLink = function(scope, element, attrs, controller) {
        controller.device = scope.device;
        controller.options = scope.options;
        controller.init();
    };

    return {
        restrict: 'AE',
        templateUrl: 'js/tools/graph/graph.html',
        replace: true,
        scope: {
            device: '=',
            options: '=options',
        },
        controller: graphController,
        controllerAs: 'graphCtl',
        link: graphLink
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.directive('graph', ['$q', '$rootScope', 'graphService', 'toastService', graphDirective]);
