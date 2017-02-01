/**
 * Code adapted from http://codepen.io/juniper/pen/LGEOVb
 */
var RaspIot = angular.module('RaspIot');
RaspIot.directive('uploadFile', uploadFile);
RaspIot.service('uploadFileService', ['$http', uploadFileService]);

function uploadFile() {
    var directive = {
        restrict: 'AE',
        scope: {
            selectedFile: '=',
            label: '@'
        },
        templateUrl: 'js/directives/uploadfile/uploadfile.html',
        link: uploadFileLink
    };
    return directive;
}

function uploadFileLink(scope, element, attrs) {
    var input = $(element[0].querySelector('#fileInput'));
    var button = $(element[0].querySelector('#uploadButton'));
    var textInput = $(element[0].querySelector('#textInput'));

    if( !scope.label ) {
        scope.label = 'Select file';
    }

    if (input.length && button.length && textInput.length) {
        button.click(function (e) {
            input.click();
        });
        textInput.click(function (e) {
            input.click();
        });
    }

    input.on('change', function (e) {
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
    });
}

/**
 * Upload file service
 * Give an unique function to upload single file
 * @param url: url to post data
 * @param file: file object from input type file
 * @param extra: extra parameters to post (object)
 * @param onSuccess: on success callback (function)
 * @param onError: on error callback (function)
 */
function uploadFileService($http) {
    var self = this;

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
        });
    };
}
