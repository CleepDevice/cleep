/**
 * Parameters config directive
 * Handle parameters configuration
 */
var parametersConfigDirective = function(toast, parametersService, raspiotService, $timeout) {

    var parametersController = ['$scope', function($scope)
    {
        var self = this;
        self.tabIndex = 'hostname';
        self.sunset = null;
        self.sunrise = null;
        self.hostname = '';
        self.hostnamePattern = '^[a-zA-Z][0-9a-zA-Z\-]{3,}[^-]$';
        self.position = {
            latitude: 0,
            longitude: 0
        };
        self.sun = {
            sunrise: 0,
            sunset: 0
        };
        self.country = {
            country: null,
            alpha2: null
        };
        self.timezone = null;

        /**
         * Set hostname
         */
        self.setHostname = function()
        {
            parametersService.setHostname(self.hostname)
                .then(function(resp) {
                    return raspiotService.reloadModuleConfig('parameters');
                })
                .then(function(config) {
                    self.updateConfig(config);
                    toast.success('Device name saved');
                });
        };

        /**
         * Set position
         */
        self.setPosition = function()
        {
            //check values
            if( !$scope.raspiotposition || !$scope.raspiotposition.lat || !$scope.raspiotposition.lng ) {
                toast.info('Please select position before setting position');
                return;
            }
            if( $scope.raspiotposition.lat==self.position.latitude && $scope.raspiotposition.lng==self.position.longitude ) {
                toast.info('Position not changed');
                return;
            }

            toast.loading('Setting localisation...');
            parametersService.setPosition($scope.raspiotposition.lat, $scope.raspiotposition.lng)
                .then(function(resp) {
                    return raspiotService.reloadModuleConfig('parameters');
                })
                .then(function(config) {
                    self.updateConfig(config);
                    toast.success('Localisation saved');
                });
        };

        /**
         * Update controller config
         */
        self.updateConfig = function(config)
        {
            self.position = config.position;
            self.hostname = config.hostname;
            self.sun = config.sun;
            self.country = config.country;
            self.timezone = config.timezone;
        };

        /**
         * Init controller
         */
        self.init = function()
        {
            raspiotService.getModuleConfig('parameters')
                .then(function(config) {
                    //update config
                    self.updateConfig(config);

                    //init leaflet
                    angular.extend($scope, {
                        raspiotposition: {
                            lat: self.position.latitude,
                            lng: self.position.longitude,
                            zoom: 8
                        },
                        raspiotdefaults: {
                            scrollWheelZoom: false,
                            minZoom: 5,
                            maxZoom: 12
                        }
                    });
                });
        };
    }];

    var parametersLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'parameters.directive.html',
        replace: true,
        scope: true,
        controller: parametersController,
        controllerAs: 'parametersCtl',
        link: parametersLink
    };
};

//var RaspIot = angular.module('RaspIot', ['nemLogging','ui-leaflet']);
var RaspIot = angular.module('RaspIot');
RaspIot.directive('parametersConfigDirective', ['toastService', 'parametersService', 'raspiotService', '$timeout', parametersConfigDirective]);

