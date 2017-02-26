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
            if( rpcService.uploading===false )
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
            return rpcService.uploading;
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

/**
 * Upload file service
 * Give an unique function to upload single file
 * @param url: url to post data
 * @param file: file object from input type file
 * @param extra: extra parameters to post (object)
 * @param onSuccess: on success callback (function)
 * @param onError: on error callback (function)
 */
/*function uploadFileService($http) {
    var self = this;
    self.uploading = false;

    self.upload = function(url, file, extra, onSuccess, onError) {
        //check input file
        if( !file ) {
            return;
        }

        //prepare data
        var formData = new FormData();
        formData.append('file', file);
        formData.append('filename', file.name);
        if( angular.isObject(extra) )
        {
            //append extra parameters
            angular.forEach(extra, function(value, key) {
                formData.append(key, value);
            });
        }

        //flag to reset upload directive
        self.uploading = true;
        
        //post data
        $http.post(url, formData, {
            transformRequest: angular.identity,
            headers: {'Content-Type': undefined}
        }).then(function(response) {
            if( angular.isFunction(onSuccess) ) {
                onSuccess(response);
            }
        }, function(err) {
            if( angular.isFunction(onError) ) {
                onError(response);
            }
        })
        .finally(function() {
            //reset
            self.uploading = false;
        });
    };
}*/

var RaspIot = angular.module('RaspIot');
//RaspIot.service('uploadFileService', ['$http', uploadFileService]);
RaspIot.directive('uploadFile', ['rpcService', uploadFileDirective]);

