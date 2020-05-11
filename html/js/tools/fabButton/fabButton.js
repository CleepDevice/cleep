/**
 * Fab button
 * Directive that adds an actions FAB button at bottom right of page.
 * 
 * By definition the FAB button always stays on position of its container.
 * So if we want having a FAB button always on the same position everywhere on the application,
 * we need to inject it on main container that doesn't have access to other directives actions.
 *
 * Usage:
 *  - Add this directive on your main container (typically on your index.html file)
 *    <div fab-button></div>
 *  - Emit event 'enableFab' with your array of actions and the directive will fill the button options
 *    If your array contains single action, the FAB button will be directly clickable
 *    If your array contains more than one action, FAB button will deploy multiple buttons
 *  - The directive automatically removes the button when user change page
 *
 * This directive only works with angular ngRoute
 *
 * Action object description:
 * {
 *   callback: function called when user click on button (function)
 *   tooltip: label displayed on tooltip (string)
 *   icon: icon on the action button
 *   aria: aria label of button
 * }
 * All action properties are mandatory and not checked.
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

    return {
        restrict: 'AE',
        templateUrl: 'js/tools/fabButton/fabButton.html',
        replace: true,
        controller: fabButtonController,
        controllerAs: 'fabButtonCtl'
    };

};
    
var Cleep = angular.module('Cleep');
Cleep.directive('fabButton', ['$rootScope', fabButtonDirective]);

