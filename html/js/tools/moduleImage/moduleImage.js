/**
 * Module image directive
 * Inject appropriate module path
 *
 * Directive example:
 * <img mod-img-src="<module image path>" style="..." class="..."/>
 * @param mod-img-src: image path relative to module path
 *  }
 */
angular
.module('Cleep')
.directive('modImgSrc', ['$location', function($location) {

    var moduleImageLink = function(scope, element, attrs, controller) {
        // members
        var modulesPath = 'js/modules/';

        /**
         * Get current module name analysing current location
         * @return current loaded module name
         */
        function getModuleName() {
            return $location.path().replace('/module/', '');
        }

        /**
         * Watch for changes on image source and update src attribute
         */
        attrs.$observe('modImgSrc', function(src) {
            // build full image path
            var url = modulesPath + getModuleName();
            if( src[0]==='/' ) {
                url += src;
            } else {
                url += '/' + src;
            }

            // update img src
            element.attr('src', url);
        });
    };

    return {
        restrict: 'A',
        scope: {
            'img-src': '@'
        },
        link: moduleImageLink
    };

}]);

