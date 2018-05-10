/**
 * Configuration directive
 * Handle all module configuration
 */
var moduleDirective = function($q, raspiotService, $compile, $timeout, $routeParams, $ocLazyLoad) {

    var moduleController = ['$scope','$element', function($scope, $element) {
        var self = this;
        self.pluginsPath = 'js/plugins'
        self.module = '';

        /**
         * Get list of config files to lazy load
         * @param desc: desc file content (json)
         * @param module: module name
         */
        self.__getConfigFilesToLoad = function(desc, module)
        {
            //init
            var url = self.pluginsPath + '/' + module + '/';
            var files = [];
            var types = ['js', 'css', 'html'];

            //check desc content
            if( !desc || !desc.config )
            {
                return files;
            }

            //append files by types
            for( var j=0; j<types.length; j++ )
            {
                if( desc.config[types[j]] )
                {
                    for( var i=0; i<desc.config[types[j]].length; i++)
                    {
                        files.push({
                            'type': types[j],
                            'path': url + desc.config[types[j]][i]
                        });
                    }
                }
            }

            return files;
        };

        /**
         * Init controller
         */
        self.init = function(module)
        {
            //save module name
            self.module = module;

            //load module description
            raspiotService.getModuleDescription(module)
                .then(function(desc) {
                    var files = self.__getConfigFilesToLoad(desc, module);
                    console.log('DESC-CONFIG', files);

                    //lazy load module files
                    return $ocLazyLoad.load({
                        'reconfig': false,
                        'rerun': true,
                        'files': files
                    })
                })
                .then(function(resp) {
                    console.log('Module completely loaded', resp);

                    //inject module configuration directive
                    var container = $element.find('#moduleContainer');
                    var template = '<div ' + module + '-config-directive=""></div>';
                    var directive = $compile(template)($scope);
                    $element.append(directive);
                }, function(err) {
                    console.error('Error loading module files:', err);
                });
        };
    }];

    var moduleLink = function(scope, element, attrs, controller) {
        controller.init($routeParams.name);
    };

    return {
        templateUrl: 'js/modules/module/module.html',
        replace: true,
        controller: moduleController,
        controllerAs: 'moduleCtl',
        link: moduleLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('moduleDirective', ['$q', 'raspiotService', '$compile', '$timeout', '$routeParams', '$ocLazyLoad', moduleDirective]);

