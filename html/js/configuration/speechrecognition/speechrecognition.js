/**
 * Speechrecognition config directive
 * Handle speech recognition configuration
 */
var speechrecognitionConfigDirective = function(toast, speechrecognitionService, raspiotService, confirm) {

    var speechrecognitionController = function()
    {
        var self = this;
        self.providers = null;
        self.provider = null;
        self.hotwordToken = null;
        self.newHotwordToken = null;
        self.hotwordRecordings = [false, false, false];
        self.hotwordModel = false;

        /**
         * Set snowboy api token
         */
        self.setHotwordToken = function()
        {
            speechrecognitionService.setHotwordToken(self.newHotwordToken)
                .then(function() {
                    toast.success('Snowboy token saved');
                });
        };

        /**
         * Record hot-word
         */
        self.recordHotword = function()
        {
            toast.loading('Recording hotword...');

            speechrecognitionService.recordHotword()
                .then(function(resp) {
                    toast.success('Recording terminated');
                    self.reloadConfig();
                });
        };

        self.resetHotword = function()
        {
            confirm.open('Reset hot-word?', 'Your hot-word voice model and all recordings will be deleted and not recoverable!', 'Reset')
                .then(function() {
                    return speechrecognitionService.resetHotword();
                })
                .then(function() {
                    self.reloadConfig();
                });
        };

        /**
         * Reload config internally
         */
        self.reloadConfig = function()
        {
            raspiotService.getModuleConfig('speechrecognition')
                .then(function(config) {
                    console.log(config);

                    //fill list of providers
                    self.providers = [];
                    var current = null;
                    for( var i=0; i<config.providers.length; i++ )
                    {
                        if( config.apikeys[self.providers[i]] )
                        {
                            current = self.providers.push({
                                provider: config.providers[i],
                                apikey: config.apikeys[self.providers[i]]
                            });
                        }
                        else
                        {
                            current = self.providers.push({
                                provider: config.providers[i],
                                apikey: null
                            });
                        }

                        //set current provider
                        if( self.providers[i]===config.provider )
                        {
                            self.provider = current;
                        }
                    }

                    //other members
                    self.hotwordToken = config.hotwordtoken;
                    self.newHotwordToken = self.hotwordToken;
                    self.hotwordRecordings = config.hotwordrecordings;
                    self.hotwordModel = config.hotwordmodel;
                });
        };

        /**
         * Init controller
         */
        self.init = function()
        {
            self.reloadConfig();
        };

    };

    var speechrecognitionLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'js/configuration/speechrecognition/speechrecognition.html',
        replace: true,
        scope: true,
        controller: speechrecognitionController,
        controllerAs: 'speechCtl',
        link: speechrecognitionLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('speechrecognitionConfigDirective', ['toastService', 'speechrecognitionService', 'raspiotService', 'confirmService', speechrecognitionConfigDirective])

