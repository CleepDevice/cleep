var toastService = function($mdToast) {
    var self = this;

    self.error = function(message, duration) {
        self.__toast(message, 5000, 'error');
    };

    self.warning = function(message, duration) {
        self.__toast(message, 3000, 'warning');
    };

    self.success = function(message, duration) {
        self.__toast(message, 3000, 'success');
    };

    self.info = function(message, duration) {
        self.__toast(message, 3000, 'info');
    };

    self.__toast = function(message, duration, class_) {
        $mdToast.show(
            $mdToast.simple()
                .textContent(message)
                .toastClass(class_)
                .position('top right')
                .hideDelay(duration)
        );
    };

    self.loading = function(message, class_) {
        if( angular.isUndefined(class_) )
        {
            class_ = 'info';
        }

        $mdToast.show({
            template: '<md-toast><span class="md-toast-text">'+message+'</span><md-progress-circular md-mode="indeterminate" md-diameter="30" class="md-accent"></md-progress-circular></md-toast>',
            position: 'top right',
            toastClass: class_,
            hideDelay: 0
        });
    };

    self.hide = function() {
        $mdToast.hide();
    };
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('toastService', ['$mdToast', toastService]);

