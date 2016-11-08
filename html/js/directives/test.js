var RaspIot = angular.module('RaspIot');

RaspIot.directive("testTest", function(){
    return {
        replace: true,
        template: '<div>' +
        'coucou directive' +
        '</div>',
        link: function(scope, element, attrs){
            console.log(arguments);
        }
    };
});
