var toastService = function($mdToast) {
    var self = this;

    self.error = function(message, duration) {
        self.toast(message, 5000, 'error');
    };

    self.warning = function(message, duration) {
        self.toast(message, 3000, 'warning');
    };

    self.success = function(message, duration) {
        self.toast(message, 3000, 'success');
    };

    self.toast = function(message, duration, class_) {
        $mdToast.show(
            $mdToast.simple()
                .textContent(message)
                .toastClass(class_)
                .position('top right')
                .hideDelay(duration)
        );
    }
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('toastService', ['$mdToast', toastService]);

