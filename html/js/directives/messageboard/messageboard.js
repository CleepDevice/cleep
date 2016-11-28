
var messageboardDirective = function($q, growl, blockUI, messageboardService) {
    var container = null;

    var messageboardController = ['$scope', function($scope) {
        var datetimeFormat = 'DD/MM/YYYY HH:mm';
        $scope.message = '';
        $scope.start = {startDate:moment(), endDate:moment()};
        $scope.end = {startDate:moment().add(1,'hour'), endDate:moment().add(1,'hour')};
        $scope.scroll = false;
        $scope.messages = [];
        $scope.pickerOptions = {
            singleDatePicker: true,
            timePicker: true,
            timePicker24Hour: true,
            autoApply: true,
            locale: {
                format: datetimeFormat
            }
        };

        /**
         * Init controller
         */
        function init()
        {
            //load messages
            loadMessages();
        }

        /**
         * Load messages
         */
        function loadMessages()
        {
            messageboardService.getMessages()
                .then(function(messages) {
                    console.log('MESSAGES', messages.length, messages);
                    var msgs = [];
                    for( var i=0; i<messages.length; i++) {
                        messages[i].startStr = moment.unix(messages[i].start).format(datetimeFormat);
                        messages[i].endStr = moment.unix(messages[i].end).format(datetimeFormat);
                        msgs.push(messages[i]);
                    }
                    $scope.messages = msgs;
                });
        };

        /**
         * Add new message
         */
        $scope.addMessage = function() {
            container.start();
            messageboardService.addMessage($scope.message, $scope.start.unix(), $scope.end.unix(), $scope.scroll)
                .then(function(resp) {
                    growl.success('Message added');
                    //reload messages
                    loadMessages();
                })
                .finally(function() {
                    container.stop();
                });
        };

        /**
         * Delete message
         */
        $scope.delMessage = function(message) {
            //confirmation
            if( !confirm('Delete message?') )
            {
                return;
            }

            container.start();
            //convert moment datetime to timestamp
            messageboardService.delMessage(message.uuid)
                .then(function(resp) {
                    growl.success('Message deleted');
                    //reload messages
                    loadMessages();
                })
                .finally(function() {
                    container.stop();
                });
        };

        //init directive
        init();
    }];

    var messageboardLink = function(scope, element, attrs) {
        container = blockUI.instances.get('messageboardContainer');
        container.reset();
    };

    return {
        templateUrl: 'js/directives/messageboard/messageboard.html',
        replace: true,
        scope: true,
        controller: messageboardController,
        link: messageboardLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('messageboardConfigDirective', ['$q', 'growl', 'blockUI', 'messageboardService', messageboardDirective]);
