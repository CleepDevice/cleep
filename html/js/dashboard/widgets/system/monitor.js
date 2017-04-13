/**
 * Monitor widget directive
 * Display system monitor dashboard widget
 */
var widgetMonitorDirective = function(raspiotService, $mdDialog) {

    var widgetMonitorController = ['$scope', function($scope) {
        var self = this;
        self.device = $scope.device;
        self.hasDatabase = raspiotService.hasModule('database');
        self.monitorCpu = null;
        self.monitorMemory = null;
        self.graphCpuOptions = {
            type: 'line',
            label: 'Memory (Mo)',
            height: 200,
            format: function(v) {
                return d3.format(".1")(v);
            }
        };
        self.graphMemoryOptions = {
            type: 'line',
            format: function(v) {
                //convert to Mo/Mb
                return v >> 20;
            },
            label: 'CPU (%)',
            height: 200
        };

        /**
         * Cancel dialog
         */
        self.cancelDialog = function() {
            $mdDialog.cancel();
        };

        /**
         * Open dialog
         */
        self.openDialog = function() {
            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'monitorCtl',
                templateUrl: 'js/dashboard/widgets/system/monitorDialog.html',
                parent: angular.element(document.body),
                clickOutsideToClose: true
            });
        };

        /**
         * Init controller
         */
        self.init = function()
        {
            //get cpu and memory devices
            for( var i=0; i<raspiotService.devices.length; i++ )
            {
                if( raspiotService.devices[i].type==='monitorcpu' )
                {
                    self.monitorCpu = raspiotService.devices[i];
                }
                else if( raspiotService.devices[i].type==='monitormemory' )
                {
                    self.monitorMemory = raspiotService.devices[i];
                }
                if( self.monitorCpu!==null && self.monitorMemory!==null )
                {
                    console.log('cpu:', self.monitorCpu, 'mem', self.monitorMemory);
                    break;
                }
            }
        };

    }];

    var widgetMonitorLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        restrict: 'EA',
        templateUrl: 'js/dashboard/widgets/system/monitor.html',
        replace: true,
        scope: {
            'device': '='
        },
        controller: widgetMonitorController,
        controllerAs: 'widgetCtl',
        link: widgetMonitorLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('widgetMonitorDirective', ['raspiotService', '$mdDialog', widgetMonitorDirective]);

