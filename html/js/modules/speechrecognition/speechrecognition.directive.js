/**
 * Speechrecognition config directive
 * Handle speech recognition configuration
 */
var speechrecognitionConfigDirective = function($rootScope, toast, speechrecognitionService, raspiotService, confirm) {

    var speechrecognitionController = function()
    {
        var self = this;
        self.providers = null;
        self.provider = null;
        self.hotwordToken = null;
        self.newHotwordToken = null;
        self.hotwordRecordings = [false, false, false];
        self.hotwordModel = false;
        self.hotwordTraining = false;
        self.providerApiKey = null;
        self.serviceEnabled = false;
        self.serviceStatus = 'notrunning';
        self.isRecording = false;
        self.testing = false;
        self.truthTable = {
            0b000: [false, true, true, true, true],
            0b100: [true, false, true, true, false],
            0b110: [true, true, false, true, false],
            0b111: [true, true, true, false, false]
        };

        /**
         * Return button disabled status
         */
        self.isRecordButtonDisabled = function(id)
        {
            if( self.isRecording || self.hotwordToken===null )
            {
                //disable button during recording and if token not specified
                return true;
            }
            else if( id===3 && self.hotwordModel )
            {
                //special case for build model button. Disable only if model is generated
                //return true;
                return false;
            }
            else
            {
                if( id==0 )
                {
                    //record1
                    if( self.hotwordRecordings[0] )
                        return true;
                    return false;
                }
                else if( id==1 )
                {
                    //record2
                    if( self.hotwordRecordings[0] && self.hotwordRecordings[1] )
                        return true;
                    return false;
                }
                else if( id==2 )
                {
                    //record3
                    if( self.hotwordRecordings[0] && self.hotwordRecordings[1] && self.hotwordRecordings[2] )
                        return true;
                    return false;
                }
                else if( id==3 )
                {
                    //manual build
                    //if( !self.hotwordRecordings[0] || !self.hotwordRecordings[1]  || !self.hotwordRecordings[2] || self.hotwordModel )
                    //    return true;
                    return false;
                }
                else if( id==4 )
                {
                    //reset
                    if( self.hotwordRecordings[0] && self.hotwordRecordings[1] && self.hotwordRecordings[2] && self.hotwordModel )
                        return false;
                    return true;
                }
                //console.log(id, self.hotwordRecordings[0]*0b001 + self.hotwordRecordings[1]*0b010 + self.hotwordRecordings[2]*0b100)
                //return self.truthTable[self.hotwordRecordings[0]*0b001 + self.hotwordRecordings[1]*0b010 + self.hotwordRecordings[2]*0b100][id];
            }
        };

        /**
         * Launch manual hotword voice model build
         */
        self.buildHotword = function()
        {
            speechrecognitionService.buildHotword()
                .then(function() {
                    toast.loading('Building your hotword voice model (can last few minutes)...');
                });
        };

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
            self.isRecording = true;
            toast.loading('Recording hotword (5 seconds)...');

            speechrecognitionService.recordHotword()
                .then(function(resp) {
                    self.reloadConfig();
                    if( self.hotwordTraining )
                    {
                        toast.loading('Building your hotword voice model (can last few minutes)...');
                    }
                    else
                    {
                        toast.success('Recording terminated');
                    }
                })
                .finally(function() {
                    self.isRecording = false;
                });
        };

        /**
         * Reset hotword settings
         */
        self.resetHotword = function()
        {
            confirm.open('Reset hot-word?', 'Your hot-word voice model and all recordings will be deleted and not recoverable!', 'Reset')
                .then(function() {
                    return speechrecognitionService.resetHotword();
                })
                .then(function() {
                    toast.success('Hotword resetted');
                    self.reloadConfig();
                });
        };

        /**
         * Toggle service activation
         */
        self.toggleServiceActivation = function()
        {
            var promise = null;
            if( self.serviceEnabled )
            {
                promise = speechrecognitionService.disableService();
            }
            else
            {
                promise = speechrecognitionService.enableService();
            }

            promise.then(function() {
                self.reloadConfig()
                    .then(function() {
                        if( self.serviceEnabled )
                        {
                            toast.success('Speech recognition service enabled');
                        }
                        else
                        {
                            toast.success('Speech recognition service disabled');
                        }
                    });
            });
        };

        /**
         * Set provider
         */
        self.setProvider = function()
        {
            speechrecognitionService.setProvider(self.provider.id, self.provider.apikey)
                .then(function() {
                    toast.success('Provider saved');
                });
        };

        /**
         * Start hotword test
         */
        self.startHotwordTest = function()
        {
            speechrecognitionService.startHotwordTest()
                .then(function() {
                    self.testing = true;
                    toast.success('Hotword test started: say your hotword and you should see notification');
                    self.reloadConfig();
                });
        };

        /**
         * Stop hotword test
         */
        self.stopHotwordTest = function()
        {
            speechrecognitionService.stopHotwordTest()
                .then(function() {
                    self.testing = false;
                    toast.success('Hotword test stopped');
                    self.reloadConfig();
                });
        };

        /**
         * Handle hotword detected event during test only
         */
        $rootScope.$on('speechrecognition.hotword.detected', function(event, uuid, params) {
            if( self.testing )
            {
                toast.info('Hotword detected');
            }
        }); 

        /**
         * Reload config internally
         */
        self.reloadConfig = function()
        {
            return raspiotService.getModuleConfig('speechrecognition')
                .then(function(config) {
                    //other members
                    self.hotwordToken = config.hotwordtoken;
                    self.newHotwordToken = self.hotwordToken;
                    self.hotwordRecordings = config.hotwordrecordings;
                    self.hotwordModel = config.hotwordmodel;
                    self.serviceEnabled = config.serviceenabled;
                    self.hotwordTraining = config.hotwordtraining;
                    self.providers = config.providers;

                    //service status
                    if( config.testing )
                    {
                        self.serviceStatus = 'testing';
                    }
                    else if( config.servicerunning ) 
                    {
                        self.serviceStatus = 'running';
                    }
                    else
                    {
                        self.serviceStatus = 'notrunning';
                    }

                    //select current provider
                    self.provider = null;
                    for( var i=0; i<self.providers.length; i++ )
                    {
                        if( self.providers[i].id===config.providerid )
                        {
                            self.provider = self.providers[i];
                        }
                    }
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
        templateUrl: 'speechrecognition.directive.html',
        replace: true,
        scope: true,
        controller: speechrecognitionController,
        controllerAs: 'speechCtl',
        link: speechrecognitionLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('speechrecognitionConfigDirective', ['$rootScope', 'toastService', 'speechrecognitionService', 'raspiotService', 'confirmService', speechrecognitionConfigDirective])

