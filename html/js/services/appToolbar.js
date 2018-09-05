/**
 * AppToolbar service allows any angular components to push button on main application toolbar (top toolbar)
 * It is used to add restart/reboot buttons but can be used to add other custom buttons
 */
var appToolbarService = function() {
    var self = this;
    self.buttons = [];

    /**
     * Generate unique id
     * @see https://gist.github.com/gordonbrander/2230317
     */
    self.__getId = function()
    {
         return '' + Math.random().toString(36).substr(2, 9);
    };

    /**
     * Add new button to toolbar
     * Buttons are appended to list, no order can be specified
     * @param label: button label
     * @param icon: icon to display near label
     * @param click: callback on button click
     * @param style: style to apply to button ('md-primary'<default>|'md-warn'|'md-accent')
     * @return button id to allow removing it from toolbar
     */
    self.addButton = function(label, icon, click, style) {
        if( style===undefined || style===null )
        {
            style = 'md-primary';
        }

        var id = self.__getId();
        self.buttons.push({
            'id': id,
            'label': label,
            'icon': icon,
            'click': click,
            'style': style
        });

        return id;
    };

    /**
     * Remove specified button
     * @param id: button identifier
     */
    self.removeButton = function(id)
    {
        for( var i=0; i<self.buttons.length; i++ )
        {
            if( self.buttons[i].id===id )
            {
                self.buttons.splice(i, 1);
                return true;
            }
        }

        //button not found
        return false;
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('appToolbarService', [appToolbarService]);

