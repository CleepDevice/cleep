/**
 * Fab button
 * Display a button that opens graph dialog
 */
var fabButtonDirective = function($rootScope) {

    var fabButtonController = ['$scope', function($scope) {
        var self = this;
        self.actions = [];
        
        /**
         * Enable fab button on demand
         */
        $rootScope.$on('enableFab', function(event, actions) {
            if( !angular.isArray(actions) )
            {
                console.error('Actions received on fabButton is not an array');
                return;
            }
            self.actions = actions;
        });

        /**
         * Disable fab button
         */
        $rootScope.$on('$routeChangeSuccess', function() {
            //disable button each time route change
            self.actions = [];
        });

    }];

    var fabButtonLink = function(scope, element, attrs, controller) {
        console.log('init fab');
    };

    return {
        restrict: 'AE',
        templateUrl: 'js/tools/fabButton/fabButton.html',
        replace: true,
        controller: fabButtonController,
        controllerAs: 'fabButtonCtl',
        link: fabButtonLink
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.directive('fabButton', ['$rootScope', fabButtonDirective]);

