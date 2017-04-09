/**
 * Graph button
 * Display a button that opens graph dialog
 *
 * Directive example:
 * <div graph-button device="<device>" options="<options>"></div
 * @param device: device object
 * @param options: graph options. An object with the following format:
 *  {
 *      'type': <'bar', 'line'> : type of graph (string) (mandatory)
 *      'filters': ['fieldname1', ...]: list of field names to display (array) (optional)
 *      'timerange': { (optional)
 *          'start': <timestamp>: start range timestamp (integer)
 *          'end': <timestamp>: end range timestamp (integer)
 *      }
 *  }
 */
var graphButtonDirective = function($q, $rootScope, graphService, $mdDialog, toast) {

    var graphButtonController = ['$scope', function($scope) {
        var self = this;
        self.customTimeFormat = d3.time.format.multi([
            ["%H:%M", function(d) { return d.getMinutes(); }], 
            ["%H", function(d) { return d.getHours(); }], 
            ["%a %d", function(d) { return d.getDay() && d.getDate() != 1; }], 
            ["%b %d", function(d) { return d.getDate() != 1; }], 
            ["%B", function(d) { return d.getMonth(); }], 
            ["%Y", function() { return true; }]
        ]);
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
                duration: 100,
                xAxis: {
                    //axisLabel: "X Axis",
                    //rotateLabels: 30,
                    showMaxMin: false,
                    tickFormat: function(d) {
                        return self.customTimeFormat(moment(d,'X').toDate());
                    }
                },
                yAxis: {
                    //axisLabel: "Y Axis",
                    axisLabelDistance: -10,
                    tickFormat: function(d){
                        return d3.format(',.2f')(d);
                    }
                },
                tooltip: {
                    keyFormatter: function(d) {
                        return self.customTimeFormat(moment(d,'X').toDate());
                    }
                },
                zoom: {
                    enabled: true,
                    scaleExtent: [
                        1,
                        10
                    ],
                    useFixedDomain: false,
                    useNiceScale: false,
                    horizontalOff: false,
                    verticalOff: true,
                    unzoomEventType: "dblclick.zoom"
                }
            }
        }
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
                    tickFormat: function(d){
                        return d3.format(',.2f')(d);
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
            }
        };
        self.graphOptionsByType = {
            'line': self.stackedAreaGraphOptions,
            'bar': self.historicalBarGraphOptions
        };
        self.graphData = [];
        self.graphOptions = {};
        self.graphRequestOptions = {
            output: 'list',
            fields: [],
            sort: 'ASC'
        };
    
        /**
         * Load graph data
         */
        self.loadGraphData = function() {
            //prepare default timestamp range
            var timestampEnd = Number(moment().format('X'));
            var timestampStart = timestampEnd - 86400;

            //set graph request options and graph options
            if( !angular.isUndefined(self.options) && self.options!==null )
            {
                //fields filtering
                if( !angular.isUndefined(self.options.fields) && self.options.fields!==null )
                {
                    self.graphRequestOptions.fields = self.options.fields;
                }

                //force timestamp range
                if( !angular.isUndefined(self.options.timestamp) && self.options.timestamp!==null )
                {
                    timestampStart = self.options.timestamp.start;
                    timestampEnd = self.options.timestamp.end;
                }

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
                    else
                    {
                        //invalid type specified
                        toast.error('Invalid graph type specified');
                    }
                }

                //graph color
                if( self.device.type==='temperature' )
                    self.graphOptions.chart.color = ['#FF7F00'];
                else if( self.device.type==='motion' )
                    self.graphOptions.chart.color = ['#24A222'];
                else if( self.device.type==='humidity' )
                    self.graphOptions.chart.color = ['#1776B6'];
                else if( self.device.type==='energy' )
                    self.graphOptions.chart.color = ['#D8241F'];
            }

            graphService.getDeviceData(self.device.uuid, timestampStart, timestampEnd, self.graphRequestOptions)
                .then(function(resp) {
                    if( self.options.type=='line' )
                    {
                        self.graphData = [{
                            'key': self.device.name,
                            'values': resp.data.data
                        }];
                    }
                    else if( self.options.type=='bar' )
                    {
                        self.graphData = [{
                            'key': self.device.name,
                            'bar': true,
                            'values': resp.data.data
                        }];
                    }
                });
        };

        /**
         * Clear graph data
         */
        self.clearGraphData = function() {
            self.graphData = [];
        };

        /**
         * Cancel dialog
         */
        self.cancelDialog = function() {
            $mdDialog.cancel();
        };

        /**
         * Open graph dialog
         */
        self.openGraphDialog = function() {
            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'graphCtl',
                templateUrl: 'js/tools/graphButton/graphDialog.html',
                parent: angular.element(document.body),
                clickOutsideToClose: true,
                onComplete: self.loadGraphData(),
                onRemoving: self.clearGraphData()
            });
        };
    
    }];

    var graphButtonLink = function(scope, element, attrs, controller) {
        controller.device = scope.device;
        controller.options = scope.options;
    };

    return {
        restrict: 'AE',
        templateUrl: 'js/tools/graphButton/graphButton.html',
        replace: true,
        scope: {
            device: '=',
            options: '='
        },
        controller: graphButtonController,
        controllerAs: 'graphButtonCtl',
        link: graphButtonLink
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.directive('graphButton', ['$q', '$rootScope', 'graphService', '$mdDialog', 'toastService', graphButtonDirective]);

