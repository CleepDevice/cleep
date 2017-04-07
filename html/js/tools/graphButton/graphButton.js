/**
 * Graph button
 * Display a button that opens graph dialog
 *
 * Directive example:
 * <div graph-button device="<device>" options="<options>"></div
 * @param device: device object
 * @param options: graph options. An object with the following format:
 *  {
 *      'type': <'stack', 'line'> : type of graph (string) (mandatory)
 *      'filters': ['fieldname1', ...]: list of field names to display (array) (optional)
 *      'timerange': { (optional)
 *          'start': <timestamp>: start range timestamp (integer)
 *          'end': <timestamp>: end range timestamp (integer)
 *      }
 *  }
 */
var graphButtonDirective = function($q, $rootScope, graphService, $mdDialog) {

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
        self.barGraphOptions = {
            chart: {
                type: "historicalBarChart",
                height: 400,
                margin: {
                    top: 20,
                    right: 20,
                    bottom: 65,
                    left: 50
                },
                showValues: true,
                duration: 100,
                xAxis: {
                    axisLabel: "X Axis",
                    rotateLabels: 30,
                    showMaxMin: false
                },
                yAxis: {
                    axisLabel: "Y Axis",
                    axisLabelDistance: -10
                },
                tooltip: {},
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
        self.stackGraphOptions = {
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
        self.types = {
            'stack': self.stackGraphOptions,
            'line': self.barGraphOptions
        };
        self.graphData = [];
        self.graphRequestOptions = {
            'output': 'list',
            'fields' : []
        };
    
        /**
         * Load graph data
         */
        self.loadGraphData = function() {
            //prepare timestamp range
            var timestampEnd = Number(moment().format('X'));
            var timestampStart = timestampEnd - 86400;

            //prepare request options
            if( angular.isUndefined(self.options) && self.options!==null )
            {
                //fields filtering
                if( angular.isUndefined(self.options.filters) && self.options.filters!==null )
                {
                    self.graphRequestOptions.fields = self.options.filters;
                }

                //force timestamp range
                if( angular.isUndefined(self.options.timestamp) && self.options.timestamp!==null )
                {
                    timestampStart = self.options.timestamp.start;
                    timestampEnd = self.options.timestamp.end;
                }
            }

            graphService.getDeviceData(self.device.uuid, timestampStart, timestampEnd, self.options)
                .then(function(resp) {
                    self.graphData = [{
                        'key': self.device.name,
                        'values': resp.data.data
                    }];
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
                templateUrl: 'js/tools/graph/graphDialog.html',
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
        templateUrl: 'js/tools/graph/graph.html',
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
RaspIot.directive('graphButton', ['$q', '$rootScope', 'graphService', '$mdDialog', graphButtonDirective]);

