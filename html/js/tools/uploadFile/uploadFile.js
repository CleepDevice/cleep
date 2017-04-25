/**
 * File upload directive.
 * Inject a hidden file input and material type input (button + text input)
 * Directive code adapted from http://codepen.io/juniper/pen/LGEOVb
 *
 * Directive example:
 * <div upload-file selected-file="" label="<button label>">
 * @param selected-file: data-binded value to watch for changes
 * @param label: text displayed on upload button
 *
 * How to use:
 * Inject directive in your template.
 * Set selected-file value with a variable of your controller
 * Add a watcher on this variable to detect changes:
 *     $scope.$watch(function() {
 *         return self.uploadFile;
 *     }, function(file) {
 *         if( file ) {
 *             //file data is ready to be uploaded
 *             //now call rpcService upload function
 *             rpcService.upload('<your module command>','<your module name>', file, <more data to send with command>)
 *                  .then(function(<command result>) {
 *                      //upload successful
 *                  }, function(<error message>) {
 *                      //upload failed
 *                  });
 *         }
 *     });
 *
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
        templateUrl: 'js/tools/uploadFile/uploadFile.html',
        scope: {
            selectedFile: '=',
            label: '@'
        },
        link: uploadFileLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('uploadFile', ['rpcService', uploadFileDirective]);

