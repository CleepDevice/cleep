
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
        $scope.duration = 60;
        $scope.speed = 0.05;
        $scope.unitDays = 'days';
        $scope.unitHours = 'hours';
        $scope.unitMinutes = 'minutes';

        /**
         * Init controller
         */
        function init()
        {
            //load messages
            loadMessages();
            //get duration
            getDuration();
            //get units
            getUnits();
            //get speed
            getSpeed();
        }

        /**
         * Load messages
         */
        function loadMessages()
        {
            messageboardService.getMessages()
                .then(function(messages) {
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
         * Get duration
         */
        function getDuration()
        {
            messageboardService.getDuration()
                .then(function(resp) {
                    $scope.duration = resp;
                });
        };

        /**
         * Get speed
         */
        function getSpeed()
        {
            messageboardService.getSpeed()
                .then(function(resp) {
                    $scope.speed = resp;
                });
        };

        /**
         * Get units
         */
        function getUnits()
        {
            messageboardService.getUnits()
                .then(function(resp) {
                    $scope.unitMinutes = resp.minutes;
                    $scope.unitHours = resp.hours;
                    $scope.unitDays = resp.days;
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

        /**
         * Set duration
         */
        $scope.setDuration = function() {
            container.start();
            messageboardService.setDuration($scope.duration)
                .then(function(resp) {
                    growl.success('Duration saved');
                })
                .finally(function() {
                    container.stop();
                });
        };

        /**
         * Set speed
         */
        $scope.setSpeed = function() {
            container.start();
            messageboardService.setSpeed($scope.speed)
                .then(function(resp) {
                    growl.success('Speed saved');
                })
                .finally(function() {
                    container.stop();
                });
        };

        /**
         * Set units
         */
        $scope.setUnits = function() {
            container.start();
            messageboardService.setUnits($scope.unitMinutes, $scope.unitHours, $scope.unitDays)
                .then(function(resp) {
                    growl.success('Units saved');
                })
                .finally(function() {
                    container.stop();
                });
        };

        /**
         * Turn on/off board
         */
        $scope.turnOff = function(off) {
            if( off )
            {
                messageboardService.turnOff();
            }
            else
            {
                messageboardService.turnOn();
            }
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
