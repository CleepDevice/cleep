var confirmService = function($mdDialog) {
    var self = this;

    /**
     * Confirm dialog helper
     * @param title: dialog title
     * @param message: dialog message
     * @param ok: ok message (default 'Ok')
     * @param cancel: ok message (default 'Cancel')
     */
    self.dialog = function(title, message, ok, cancel, container) {
        //container
        var container_ = angular.element(document.body);
        if( !angular.isUndefined(container) )
        {
            if( !container.startsWith('#') )
            {
                container = '#' + container;
            }
            _container = angular.element(document.querySelector(container));
        }

        //check strings
        if( angular.isUndefined(ok) || ok===null ) {
            ok = 'Ok';
        }
        if( angular.isUndefined(cancel) || cancel===null ) {
            cancel = 'Cancel';
        }

        var confirm_ = $mdDialog.confirm()
            .title(title)
            .textContent(message)
            .ariaLabel('Confirm dialog')
            .ok(ok)
            .cancel(cancel);

        return $mdDialog.show(confirm_);
    };
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('confirmService', ['$mdDialog', confirmService]);

