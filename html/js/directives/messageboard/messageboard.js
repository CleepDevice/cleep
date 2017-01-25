
var messageboardDirective = function($q, toast, blockUI, messageboardService) {
    var container = null;

    var messageboardController = ['$scope', function($scope) {
        var datetimeFormat = 'DD/MM/YYYY HH:mm';
        var self = this;
        self.message = '';
        self.start = moment();
        self.end = moment().add(1,'hour')
        self.messages = [];
        self.duration = 60;
        self.speed = 50;
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
                    var msgs = [];
                    for( var i=0; i<messages.length; i++) {
                        messages[i].startStr = moment.unix(messages[i].start).format(datetimeFormat);
                        messages[i].endStr = moment.unix(messages[i].end).format(datetimeFormat);
                        msgs.push(messages[i]);
                    }
                    self.messages = msgs;
                });
        };

        /**
         * Get duration
         */
        self.duration = function()
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
            container.start();
            messageboardService.addMessage(self.message, self.start.unix(), self.end.unix(), self.scroll)
                .then(function(resp) {
                    toast.success('Message added');
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
                    loadMessages();
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

        //init directive
        init();
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

