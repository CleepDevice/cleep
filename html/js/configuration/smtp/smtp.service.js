/**
 * Smtp service
 * Handle smtp module requests
 */
var smtpService = function($q, $rootScope, rpcService) {
    var self = this;

    self.setConfig = function(smtpServer, smtpPort, smtpLogin, smtpPassword, smtpTls, smtpSsl, emailSender, recipient) {
        return rpcService.sendCommand('set_config', 'smtp', {'smtp_server':smtpServer, 'smtp_port':smtpPort, 'smtp_login':smtpLogin, 'smtp_password':smtpPassword, 'smtp_tls':smtpTls, 'smtp_ssl':smtpSsl, 'email_sender':emailSender, 'recipient':recipient});
    };

    self.test = function(recipient) {
        return rpcService.sendCommand('test', 'smtp', {'recipient':recipient});
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('smtpService', ['$q', '$rootScope', 'rpcService', smtpService]);

