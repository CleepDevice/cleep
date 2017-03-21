/**
 * Dialog service
 * Used to open a material dialog
 */
var dialogService = function($mdDialog) {
    var self = this;

    self.dialogController = ['$scope', '$mdDialog', function($scope, $mdDialog) {
        var cancel = function() {
            $mdDialog.cancel();
        };

        var valid = function() {
            $mdDialog.hide();
        };
    }];

    /**
     * Open dialog
     * @param controller: controller object. Usually dialogService caller (object)
     * @param controllerAs: name of controller (string)
     * @param templateUrl: dialog content url (string)
     */
    self.open = function(options, controllerAs, templateUrl) {
        //extend specified controller with dialog function helpers
        var controller = angular.extend(self.dialogController, options || {});
        console.log(controller);
        return $mdDialog.show({
            /*controller: function($scope, $mdDialog) {
                $scope.cancel = function() {
                    $mdDialog.cancel();
                };
                $scope.hide = function() {
                    $mdDialog.hide();
                };
            },*/
            controller: controller,
            controllerAs: controllerAs,
            templateUrl: templateUrl,
            parent: angular.element(document.body),
            clickOutsideToClose: false,
        });
    };
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('dialogService', ['$mdDialog', dialogService]);
