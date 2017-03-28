/**
 * File upload directive.
 * Inject a hidden file input and material type input (button + text input)
 * Directive code adapted from http://codepen.io/juniper/pen/LGEOVb
 */
var uploadFileDirective = function(rpcService) {

    var uploadFileLink = function(scope, element, attrs, controller) {
        var input = $(element[0].querySelector('#fileInput'));
        var button = $(element[0].querySelector('#uploadButton'));
        var textInput = $(element[0].querySelector('#textInput'));

        //add label
        if( angular.isUndefined(scope.label) || scope.label===null )
        {
            scope.label = 'Select file';
        }

        //bind file input event to input and button
        if (input.length && button.length && textInput.length)
        {
            button.click(function (e) {
                input.click();
            });

            textInput.click(function (e) {
                input.click();
            });
        }

        //define event
        input.on('change', function (e) {
            if( rpcService._uploading===false )
            {
                var files = e.target.files;
                if( files[0] )
                {
                    scope.filename = files[0].name;
                    scope.selectedFile = files[0];
                }
                else
                {
                    scope.filename = null;
                    scope.selectedFile = null;
                }
                scope.$apply();
            } else {
                console.log('locked');
            }
        });

        //handle end of upload to reset directive content
        scope.$watch(function() {
            return rpcService._uploading;
        }, function(newVal, oldVal) {
            if( newVal===false && oldVal===true ) {
                input.val('');
                textInput.val('');
                scope.filename = null;
                scope.selectedFile = null;
            }
        });
    };

    return {
        restrict: 'AE',
        templateUrl: 'js/directives/uploadfile/uploadfile.html',
        scope: {
            selectedFile: '=',
            label: '@'
        },
        link: uploadFileLink
    }
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('uploadFile', ['rpcService', uploadFileDirective]);

