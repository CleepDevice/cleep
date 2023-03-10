/**
 * File upload directive.
 * Inject a hidden file input and material type input (button + text input)
 * Directive code adapted from http://codepen.io/juniper/pen/LGEOVb
 *
 * Directive example:
 * <div upload-file selected-file="" label="<button label>" placeholder="<input placeholder>" icon="<mdi icon name>">
 * @param selected-file: data-binded value to watch for changes
 * @param label: text displayed on upload button (default "Select file")
 * @param placeholder: text displayed on input. If not specified input is hidden
 * @param icon: mdi icon name (default "upload")
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
angular
.module('Cleep')
.directive('uploadFile', ['rpcService',
function(rpcService) {

    var uploadFileLink = function(scope, element, attrs, controller) {
        var input = $(element[0].querySelector('#fileInput'));
        var button = $(element[0].querySelector('#uploadButton'));
        var textInput = $(element[0].querySelector('#textInput'));

        // params
        if (angular.isUndefined(scope.label) || scope.label===null) {
            scope.label = 'Select file';
        }
        if (angular.isUndefined(scope.icon) || scope.icon===null) {
            scope.icon = 'upload';
        }

        // bind file input event to input and button
        if (input.length && button.length && textInput.length) {
            button.click(function (e) {
                input.click();
            });
            textInput.click(function (e) {
                input.click();
            });
        }

        // define event
        input.on('change', function (e) {
            if (rpcService._uploading===false) {
                var files = e.target.files;
                if (files[0]) {
                    scope.filename = files[0].name;
                    scope.selectedFile = files[0];
                } else {
                    scope.filename = null;
                    scope.selectedFile = null;
                }
                scope.$apply();
            }
        });

        // handle end of upload to reset directive content
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
            label: '@',
            placeholder: '@',
            icon: '@',
        },
        link: uploadFileLink
    };
}]);
