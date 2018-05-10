/**
 * Smtp config directive
 * Handle smtp configuration
 */
var smtpConfigDirective = function(toast, smtpService, raspiotService) {

    var smtpController = ['$scope', function($scope)
    {
        var self = this;
        self.providers = [{
            key: 'gmail',
            name: 'Google Gmail',
            smtp: 'smtp.gmail.com',
            port: 465,
            tls: false,
            ssl: true
        }, {
            key: 'yahoo',
            name: 'Yahoo! mail',
            smtp: 'smtp.mail.yahoo.com',
            port: 465,
            tls: false,
            ssl: true
        }, {
            key: 'custom',
            name: 'Custom email provider',
            smtp: null,
            port: '',
            tls: false,
            ssl: false
        }];
        self.provider = null;
        self.smtpServer = '';
        self.smtpPort = '';
        self.smtpLogin = '';
        self.smtpPassword = '';
        self.smtpTls = '';
        self.smtpSsl = '';
        self.emailSender = '';
        self.recipient = '';
        self.defaultConfig = null;

        /**
         * Load values from specified config
         */
        self.__loadFromConfig = function(config)
        {
            self.smtpServer = config.smtp_server;
            self.smtpPort = config.smtp_port;
            self.smtpLogin = config.smtp_login;
            self.smtpPassword = config.smtp_password;
            self.smtpTls = config.smtp_tls;
            self.smtpSsl = config.smtp_ssl;
            self.emailSender = config.email_sender;
        };

        /**
         * Set config
         */
        self.setConfig = function()
        {
            smtpService.setConfig(self.smtpServer, self.smtpPort, self.smtpLogin, self.smtpPassword, self.smtpTls, self.smtpSsl, self.emailSender, self.recipient)
                .then(function(resp) {
                    return raspiotService.reloadModuleConfig('smtp');
                })
                .then(function(config) {
                    self.__loadFromConfig(config);
                    toast.success('Configuration saved. You should receive an email soon.');
                });
        };

        /**
         * Test
         */
        self.test = function()
        {
            smtpService.test(self.recipient)
                .then(function(resp) {
                    toast.success('Email sent. Check your mailbox.');
                });
        };

        /**
         * Init controller
         */
        self.init = function()
        {
            raspiotService.getModuleConfig('smtp')
                .then(function(config) {
                    for( var i=0; i<self.providers.length; i++ )
                    {
                        if( config.smtp_server===self.providers[i].smtp )
                        {
                            self.provider = self.providers[i].key;
                            break;
                        }
                    }
                    if( self.provider===null )
                    {
                        self.provider = 'custom';
                    }
                    self.defaultConfig = config;
                    self.defaultConfig.provider = self.provider;
                    self.__loadFromConfig(config);
                });
        };

        $scope.$watch(function() {
            return self.provider
        }, function(newVal, oldVal) {
            if( newVal && oldVal )
            {
                if( newVal==self.defaultConfig.provider )
                {
                    //load user values from config
                    self.__loadFromConfig(self.defaultConfig);
                }
                else
                {
                    //erase inputs
                    self.smtpServer = '';
                    self.smtpPort = '';
                    self.smtpLogin = '';
                    self.smtpPassword = '';
                    self.smtpTls = '';
                    self.smtpSsl = '';
                    self.emailSender = '';
                }
            }
        });

    }];

    var smtpLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'smtp.directive.html',
        scope: true,
        controller: smtpController,
        controllerAs: 'smtpCtl',
        link: smtpLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('smtpConfigDirective', ['toastService', 'smtpService', 'raspiotService', smtpConfigDirective])

