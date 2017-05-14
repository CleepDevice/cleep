/**
 * Message board config directive
 */
var messageboardDirective = function($rootScope, raspiotService, toast, messageboardService, confirm) {

    var messageboardController = ['$scope', function($scope) {
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
        self.boardIsOn = true;

        /**
         * Init controller
         */
        self.init = function() {
            var config = raspiotService.getModuleConfig('messageboard');
            self.duration = config.duration;
            self.unitMinutes = config.units.minutes;
            self.unitHours = config.units.hours;
            self.unitDays = config.units.days;
            self.speed = config.speed;
            self.boardIsOn = !config.status.off;
            self.messages = config.messages;

            //add module actions to fabButton
            var actions = [{
                icon: 'add_circle_outline',
                callback: self.openAddDialog,
                tooltip: 'Add message'
            }, {
                icon: 'build',
                callback: self.openAdvancedDialog,
                tooltip: 'Advanced configuration'
            }]; 
            $rootScope.$broadcast('enableFab', actions);
        };

        /**
         * Open add panel
         */
        self.openAddDialog = function() {
            self.closeAdvancedPanel();
        };

        /**
         * Close add panel
         */
        self.closeAddDialog = function() {
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
         * Add new message
         */
        self.addMessage = function() {
            //get unix timestamp
            var temp = self.startTime.split(':');
            var start = moment(self.startDate).hours(temp[0]).minutes(temp[1]);
            temp = self.endTime.split(':');
            var end = moment(self.endDate).hours(temp[0]).minutes(temp[1]);

            //send command
            messageboardService.addMessage(self.message, start.unix(), end.unix())
                .then(function(resp) {
                    return raspiotService.reloadModuleConfig('messageboard');
                })
                .then(function(config) {
                    self.messages = config.messages;
                    toast.success('Message added');
                    self.closeAddPanel();
                });
        };

        /**
         * Delete message
         */
        self.deleteMessage = function(message) {
            confirm.open('Delete message ?', null, 'Delete')
                .then(function() {
                    return messageboardService.deleteMessage(message.uuid);
                })
                .then(function(resp) {
                    return raspiotService.reloadModuleConfig('messageboard');
                })
                .then(function(config) {
                    self.messages = config.messages;
                    toast.success('Message deleted');
                }); 
        };

        /**
         * Set duration
         */
        self.setDuration = function() {
            messageboardService.setDuration(self.duration)
                .then(function(resp) {
                    toast.success('Duration saved');
                });
        };

        /**
         * Set speed
         */
        self.setSpeed = function() {
            messageboardService.setSpeed(self.speed)
                .then(function(resp) {
                    toast.success('Speed saved');
                });
        };

        /**
         * Set units
         */
        self.setUnits = function() {
            messageboardService.setUnits(self.unitMinutes, self.unitHours, self.unitDays)
                .then(function(resp) {
                    toast.success('Units saved');
                });
        };

        /**
         * Turn on/off board
         */
        self.turnOff = function() {
            if( !self.boardIsOn )
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
        controller.init();
    };

    return {
        templateUrl: 'js/configuration/messageboard/messageboard.html',
        replace: true,
        scope: true,
        controller: messageboardController,
        controllerAs: 'msgboardCtl',
        link: messageboardLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('messageboardConfigDirective', ['$rootScope', 'raspiotService', 'toastService', 'messageboardService', 'confirmService', messageboardDirective]);

