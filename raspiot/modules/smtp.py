#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import logging
from raspiot.raspiot import RaspIotRenderer
from raspiot.utils import CommandError, MissingParameter
from raspiot.profiles import EmailProfile
import smtplib
import mimetypes
from email import encoders
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

__all__ = [u'Smtp']


class Smtp(RaspIotRenderer):
    """
    Smtp module
    """
    MODULE_AUTHOR = u'Cleep'
    MODULE_VERSION = u'1.0.0'
    MODULE_PRICE = 0
    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Sends you alerts by email.'
    MODULE_LOCKED = False
    MODULE_TAGS = [u'email', u'smtp', u'alert']
    MODULE_COUNTRY = None
    MODULE_URLINFO = None
    MODULE_URLHELP = None
    MODULE_URLSITE = None
    MODULE_URLBUGS = None

    MODULE_CONFIG_FILE = u'smtp.conf'
    DEFAULT_CONFIG = {
        u'smtp_server': None,
        u'smtp_port': u'',
        u'smtp_login': u'',
        u'smtp_password': u'',
        u'smtp_tls': False,
        u'smtp_ssl': False,
        u'email_sender': u''
    }

    RENDERER_PROFILES = [EmailProfile]
    RENDERER_TYPE = u'alert.email'

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): flag to set debug level to logger
        """
        #init
        RaspIotRenderer.__init__(self, bootstrap, debug_enabled)

    def __send_email(self, smtp_server, smtp_port, smtp_login, smtp_password, smtp_tls, smtp_ssl, email_sender, data):
        """
        Send test email

        Params:
            smtp_server: smtp server address (string)
            smtp_port: smtp server port (int)
            smtp_login: login to connect to smtp server (string)
            smtp_password: password to connect to smtp server (string)
            smtp_tls: tls option (bool)
            smtp_ssl: ssl option (bool)
            email_sender: email sender (string)
            data: email data (EmailProfile instance)

        Returns:
            bool: True if test succeed
        """
        try:
            self.logger.debug(u'Send email: %s:%s@%s:%s from %s SSl:%s TLS:%s' % (smtp_login, smtp_password, smtp_server, unicode(smtp_port), email_sender, unicode(smtp_ssl), unicode(smtp_tls)))
            #make sure port is int
            if isinstance(smtp_port, str) and len(smtp_port)>0:
                smtp_port = int(smtp_port)
            else:
                smtp_port = None

            #prepare email
            mails = None
            if smtp_ssl:
                mails = smtplib.SMTP_SSL(smtp_server, smtp_port)
            else:
                mails = smtplib.SMTP(smtp_server, smtp_port)
            if smtp_tls:
                mails.starttls()
            if len(smtp_login)>0:
                mails.login(smtp_login, smtp_password)
            mail = MIMEMultipart(u'alternative')
            mail[u'Subject'] = data.subject
            mail[u'From'] = email_sender
            mail[u'To'] = data.recipients[0]
            text = u"""%s""" % (data.message)
            html  = u'<html><head></head><body>%s</body>' % (data.message)
            part1 = MIMEText(text, u'plain')
            part2 = MIMEText(html, u'html')
            mail.attach(part1)
            mail.attach(part2)

            #append attachment
            #@see https://docs.python.org/2/library/email-examples.html
            if data.attachment is not None and len(data.attachment)>0:
                #there is something to attach
                #file exists?
                if os.path.isfile(data.attachment):
                    ctype, encoding = mimetypes.guess_type(data.attachment)
                    if ctype is None or encoding is not None:
                        ctype = u'application/octet-stream'
                    maintype, subtype = ctype.split(u'/', 1)
                    if maintype == u'text':
                        fp = open(data.attachment)
                        msg = MIMEText(fp.read(), _subtype=subtype)
                        fp.close()
                    elif maintype == u'image':
                        fp = open(data.attachment, u'rb')
                        msg = MIMEImage(fp.read(), _subtype=subtype)
                        fp.close()
                    elif maintype == u'audio':
                        fp = open(data.attachment, u'rb')
                        msg = MIMEAudio(fp.read(), _subtype=subtype)
                        fp.close()
                    else:
                        fp = open(data.attachment, u'rb')
                        msg = MIMEBase(maintype, subtype)
                        msg.set_payload(fp.read())
                        fp.close()
                        #encode the payload using Base64
                        encoders.encode_base64(msg)
                    #set the filename parameter
                    msg.add_header(u'Content-Disposition', u'attachment', filename=os.path.basename(data.attachment))
                    mail.attach(msg)

            #send email
            mails.sendmail(email_sender, data.recipients, mail.as_string())
            mails.quit()

        except smtplib.SMTPServerDisconnected as e:
            self.logger.exception(u'Failed to send test:')
            raise Exception(u'Server disconnected')

        except smtplib.SMTPSenderRefused as e:
            self.logger.exception(u'Failed to send test:')
            raise Exception(u'Email sender must be a valid email address')

        except smtplib.SMTPRecipientsRefused as e:
            self.logger.exception(u'Failed to send test:')
            raise Exception(u'Some recipients were refused')

        except smtplib.SMTPDataError as e:
            self.logger.exception(u'Failed to send test:')
            raise Exception(u'Problem with email content')

        except smtplib.SMTPConnectError as e:
            self.logger.exception(u'Failed to send test:')
            raise Exception(u'Unable to establish connection with smtp server. Please check server address')

        except smtplib.SMTPAuthenticationError as e:
            self.logger.exception(u'Failed to send test:')
            raise Exception(u'Authentication failed. Please check credentials.')
            
        except Exception as e:
            self.logger.exception(u'Failed to send test:')
            raise Exception(unicode(e))

    def set_config(self, smtp_server, smtp_port, smtp_login, smtp_password, smtp_tls, smtp_ssl, email_sender, recipient):
        """
        Set configuration

        Params:
            smtp_server: smtp server address
            smtp_port: smtp server port
            smtp_login: login to connect to smtp server
            smtp_password: password to connect to smtp server
            smtp_tls: tls option
            smtp_ssl: ssl option
            email_sender: email sender
            recipient: email recipient

        Returns:
            bool: True if config saved successfully
        """
        if smtp_server is None or len(smtp_server)==0:
            raise MissingParameter(u'Smtp_server parameter is missing')
        if smtp_port is None:
            raise MissingParameter(u'Smtp_port parameter is missing')
        if smtp_login is None:
            raise MissingParameter(u'Smtp_login parameter is missing')
        if smtp_password is None:
            raise MissingParameter(u'Smtp_password parameter is missing')
        if smtp_tls is None:
            raise MissingParameter(u'Smtp_tls parameter is missing')
        if smtp_ssl is None:
            raise MissingParameter(u'Smtp_ssl parameter is missing')
        if email_sender is None:
            raise MissingParameter(u'Email_sender parameter is missing')
        if len(email_sender)==0:
            email_sender = u'test@cleep.com'
        if recipient is None or len(recipient)==0:
            raise MissingParameter(u'Recipient parameter is missing')

        #test config
        try:
            self.test(recipient, smtp_server, smtp_port, smtp_login, smtp_password, smtp_tls, smtp_ssl, email_sender)
        except Exception as e:
            raise CommandError(unicode(e))

        #save config
        return self._update_config({
            u'smtp_server': smtp_server,
            u'smtp_port': smtp_port,
            u'smtp_login': smtp_login,
            u'smtp_password': smtp_password,
            u'smtp_tls': smtp_tls,
            u'smtp_ssl': smtp_ssl,
            u'email_sender': email_sender
        })

    def test(self, recipient, smtp_server=None, smtp_port=None, smtp_login=None, smtp_password=None, smtp_tls=None, smtp_ssl=None, email_sender=None):
        """
        Send test email

        Params:
            smtp_server: smtp server address
            smtp_port: smtp server port
            smtp_login: login to connect to smtp server
            smtp_password: password to connect to smtp server
            smtp_tls: tls option
            smtp_ssl: ssl option
            email_sender: email sender
            recipient: test email recipient

        Returns:
            bool: True if test succeed
        """
        if recipient is None or len(recipient)==0:
            raise CommandError(u'Recipient parameter is missing')

        if smtp_server is None or smtp_login is None or smtp_password is None:
            config = self._get_config()
            if config[u'smtp_server'] is None or len(config[u'smtp_server'])==0 or config[u'smtp_login'] is None or len(config[u'smtp_login'])==0 or config[u'smtp_password'] is None or len(config[u'smtp_password'])==0:
                raise CommandError(u'Please fill config first')

            smtp_server = config[u'smtp_server']
            smtp_port = config[u'smtp_port']
            smtp_login = config[u'smtp_login']
            smtp_password = config[u'smtp_password']
            smtp_tls = config[u'smtp_tls']
            smtp_ssl = config[u'smtp_ssl']
            email_sender = config[u'email_sender']

        #prepare data
        data = EmailProfile()
        data.subject = u'Cleep test'
        data.message = u'Hello this is Cleep'
        data.recipients.append(recipient)

        #send email
        self.__send_email(smtp_server, smtp_port, smtp_login, smtp_password, smtp_tls, smtp_ssl, email_sender, data)

        return True

    def _render(self, profile):
        """
        Render profile

        Params:
            profile (EmailProfile): EmailProfile instance

        Returns:
            bool: True if post succeed, False otherwise
        """
        config = self._get_config()
        if config[u'smtp_server'] is None or config[u'email_sender'] is None:
            #not configured
            raise CommandError(u'Can\'t send email because module is not configured')

        #send email
        self.__send_email(config[u'smtp_server'], config[u'smtp_port'], config[u'smtp_login'], config[u'smtp_password'], config[u'smtp_tls'], config[u'smtp_ssl'], config[u'email_sender'], profile)

        return True

