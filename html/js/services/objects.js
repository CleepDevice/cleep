/**
 * Objects service
 * Handle all angular dynamic stuff (services, module directives...)
 */
var objectsService = function($q, rpcService, toast) {
    var self = this;
    //list of angular services
    self.services = {};
    //list of modules
    //self.modules = [];
    //list of angular module directives
    //self.moduleDirectives = [];

    /**
     * Register angular service to factory
     * Internal usage, do not use
     */
    self._addService = function(module, service)
    {
        self.services[module] = service;
    };

    /**
     * Return true if module has angular service
     * @param module: module name
     * @return true if module has associated service
     */
    self._moduleHasService = function(module)
    {
        return !angular.isUndefined(self.services[module]);
    };

    /**
     * Register module with angular config directive
     * Internal usage, do not use
     * @param directiveLabel: label that will be displayed on configuration tab
     * @param directiveName: angular directive name
     * @param description: module description
     * @param locked: module is locked by system or not
     */
    /*self._addModuleWithConfig = function(module, directiveLabel, directiveName, description, locked)
    {
        //save config directive
        directive = {
            label: directiveLabel,
            cleanLabel: directiveLabel.replace(' ',''),
            directive: directiveName,
            description: description,
            locked: locked
        };
        self.moduleDirectives.push(directive);

        //register module
        self._addModule(module);
    };*/

    /**
     * Register module name
     * Internal usage, do not use
     * @param module: module name
     */
    /*self._addModule = function(module)
    {
        if( self.modules.indexOf(module)===-1 )
        {
            self.modules.push(module);
        }
    };*/

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('objectsService', ['$q', 'rpcService', 'toastService', objectsService]);

