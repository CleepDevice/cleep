
var messageboardDirective = function($q, toast, blockUI, messageboardService) {
    var container = null;

    var messageboardController = ['$scope', '$filter', function($scope, $filter) {
        var datetimeFormat = 'DD/MM/YYYY HH:mm';
        var self = this;
        self.message = '';
        self.startDate = moment().toDate();
        self.startTime = moment().format('HH:mm');
        self.endDate = moment().add(2, 'hours').toDate();
        self.endTime = moment().add(2, 'hours').format('HH:mm');
        self.messages = [];
        self.duration = 30;
        self.speed = 0.005;
        self.unitDays = 'days';
        self.unitHours = 'hours';
        self.unitMinutes = 'minutes';
        self.showAddPanel = false;
        self.showAdvancedPanel = false;

        /**
         * Init controller
         */
        self.init = function()
        {
            //load messages
            self.loadMessages();
            //get duration
            self.getDuration();
            //get units
            self.getUnits();
            //get speed
            self.getSpeed();
        };

        /**
         * Open add panel
         */
        self.openAddPanel = function() {
            self.showAddPanel = true;
            self.closeAdvancedPanel();
        };

        /**
         * Close add panel
         */
        self.closeAddPanel = function() {
            self.showAddPanel = false;
        };

        /**
         * Open advanced panel
         */
        self.openAdvancedPanel = function() {
            self.showAdvancedPanel = true;
            self.closeAddPanel();
        };

        /**
         * Close advanced panel
         */
        self.closeAdvancedPanel = function() {
            self.showAdvancedPanel = false;
        };

        /**
         * Load messages
         */
        self.loadMessages = function()
        {
            messageboardService.getMessages()
                .then(function(messages) {
                    self.messages = messages;
                });
        };

        /**
         * Get duration
         */
        self.getDuration = function()
        {
            messageboardService.getDuration()
                .then(function(resp) {
                    self.duration = resp;
                });
        };

        /**
         * Get speed
         */
        self.getSpeed = function()
        {
            messageboardService.getSpeed()
                .then(function(resp) {
                    self.speed = resp;
                });
        };

        /**
         * Get units
         */
        self.getUnits = function()
        {
            messageboardService.getUnits()
                .then(function(resp) {
                    self.unitMinutes = resp.minutes;
                    self.unitHours = resp.hours;
                    self.unitDays = resp.days;
                });
        };

        /**
         * Add new message
         */
        self.addMessage = function() {
            //get unix timestamp
            var temp = self.startTime.split(':');
            var start = moment(self.startDate).hours(temp[0]).minutes(temp[1]);
            var temp = self.endTime.split(':');
            var end = moment(self.endDate).hours(temp[0]).minutes(temp[1]);

            //send command
            messageboardService.addMessage(self.message, start.unix(), end.unix())
                .then(function(resp) {
                    toast.success('Message added');
                    //reload messages
                    self.loadMessages();
                    //close panel
                    self.closeAddPanel();
                })
                .finally(function() {
                    container.stop();
                });
        };

        /**
         * Delete message
         */
        self.deleteMessage = function(message) {
            //confirmation
            if( !confirm('Delete message?') )
            {
                return;
            }

            container.start();
            messageboardService.deleteMessage(message.uuid)
                .then(function(resp) {
                    toast.success('Message deleted');
                    //reload messages
                    self.loadMessages();
                })
                .finally(function() {
                    container.stop();
                });
        };

        /**
         * Set duration
         */
        self.setDuration = function() {
            container.start();
            messageboardService.setDuration(self.duration)
                .then(function(resp) {
                    toast.success('Duration saved');
                })
                .finally(function() {
                    container.stop();
                });
        };

        /**
         * Set speed
         */
        self.setSpeed = function() {
            container.start();
            messageboardService.setSpeed(self.speed)
                .then(function(resp) {
                    toast.success('Speed saved');
                })
                .finally(function() {
                    container.stop();
                });
        };

        /**
         * Set units
         */
        self.setUnits = function() {
            container.start();
            messageboardService.setUnits(self.unitMinutes, self.unitHours, self.unitDays)
                .then(function(resp) {
                    toast.success('Units saved');
                })
                .finally(function() {
                    container.stop();
                });
        };

        /**
         * Turn on/off board
         */
        self.turnOff = function(off) {
            if( off )
            {
                messageboardService.turnOff();
            }
            else
            {
                messageboardService.turnOn();
            }
        };
    }];

    var messageboardLink = function(scope, element, attrs, controller) {
        container = blockUI.instances.get('messageboardContainer');
        container.reset();

        controller.init();
    };

    return {
        templateUrl: 'js/directives/messageboard/messageboard.html',
        replace: true,
        scope: true,
        controller: messageboardController,
        controllerAs: 'msgboardCtl',
        link: messageboardLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('messageboardConfigDirective', ['$q', 'toastService', 'blockUI', 'messageboardService', messageboardDirective]);

