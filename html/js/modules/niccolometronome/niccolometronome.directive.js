/**
 * Niccolo metronome config directive
 * Handle niccolo metronome configuration
 */
var niccolometronomeConfigDirective = function($rootScope, toast, niccolometronomeService, raspiotService, $mdDialog)
{

    var niccolometronomeController = function()
    {
        var self = this;
        self.metronomeRunning = false;
        self.phrases = [];
        self.currentBpm = 0;
        self.newBpm = 0;
        self.newPhrase = '';
        self.newPhraseCommand = 1;
        self.newPhraseBpm = 60;
        self.commands = [
            {label:'Start metronome', value:1},
            {label:'Stop metronome', value:2},
            {label:'Set BPM to', value:3},
            {label:'Increase BPM of', value:4},
            {label:'Decrease BPM of', value:5}
        ];

        /**
         * Set BPM
         */
        self.setBpm = function()
        {
            niccolometronomeService.setBpm(self.newBpm)
                .then(function() {
                    toast.success('BPM changes');
                });
        };

        /**
         * Toggle metronome
         */
        self.toggleMetronome = function()
        {
            var promise = null;
            if( self.metronomeRunning )
            {
                promise = niccolometronomeService.stopMetronome();
            }
            else
            {
                promise = niccolometronomeService.startMetronome();
            }

            promise.then(function() {
                self.reloadConfig();
                if( self.metronomeRunning )
                {
                    toast.success('Metronome started');
                }
                else
                {
                    toast.success('Metronome stopped');
                }
            });
        };

        /**
         * Add phrase
         */
        self.addPhrase = function()
        {
            niccolometronomeService.addPhrase(self.newPhrase, self.newPhraseCommand, self.newPhraseBpm)
                .then(function() {
                    self.reloadConfig();
                    toast.success('New phrase added');
                });
        };

        /**
         * Remove phrase
         */
        self.removePhrase = function(phrase)
        {
            niccolometronomeService.removePhrase(phrase.id)
                .then(function() {
                    self.reloadConfig();
                    toast.success('Phrase removed');
                });
        };

        /**
         * Reload config
         */
        self.reloadConfig = function()
        {
            raspiotService.getModuleConfig('niccolometronome')
                .then(function(config) {
                    self.metronomeRunning = config.metronomerunning;
                    self.phrases = config.phrases;
                    self.currentBpm = self.newBpm = config.bpm;
                });
        };

        /**
         * Init controller
         */
        self.init = function()
        {
            //load configuration
            self.reloadConfig();

            //add action button
            var actions = [{
                icon: 'plus',
                callback: self.openAddDialog,
                tooltip: 'Add phrase'
            }]; 
            $rootScope.$broadcast('enableFab', actions);
        };

        /**
         * Cancel dialog (close modal and reset variables)
         */
        self.cancelDialog = function()
        {
            if( self.testing )
            {
                //test in progress, cancel action
                return;
            }

            $mdDialog.cancel();
        };

        /**
         * Valid dialog (only close modal)
         * Note: don't forget to reset variables !
         */
        self.validDialog = function() {
            if( self.testing )
            {
                //test in progress, cancel action
                return;
            }

            $mdDialog.hide();
        };

        /**
         * Open add phrase dialog
         */
        self.openAddDialog = function()
        {
            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'dialogCtl',
                templateUrl: 'addPhraseDialog.directive.html',
                parent: angular.element(document.body),
                clickOutsideToClose: true,
                fullscreen: true
            }).then(function() {
                self.addPhrase();
            });
        };

        /**
         * Disable BPM field from add phrase dialog
         */
        self.disableBpmField = function()
        {
            if( self.newPhraseCommand==1 || self.newPhraseCommand==2 )
            {
                return true;
            }

            return false;
        };

    };

    var niccolometronomeLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'niccolometronome.directive.html',
        replace: true,
        scope: true,
        controller: niccolometronomeController,
        controllerAs: 'niccolometronomeCtl',
        link: niccolometronomeLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('niccolometronomeConfigDirective', ['$rootScope', 'toastService', 'niccolometronomeService', 'raspiotService', '$mdDialog', niccolometronomeConfigDirective])

