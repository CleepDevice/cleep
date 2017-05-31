#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import logging
from raspiot.raspiot import RaspIotProvider
from raspiot.utils import CommandError, MissingParameter
from raspiot.libs.profiles import EmailProfile
import smtplib
import mimetypes
from email import encoders
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

__all__ = ['Smtp']


class Smtp(RaspIotProvider):
    """
    Smtp module
    """

    MODULE_CONFIG_FILE = 'smtp.conf'
    MODULE_DEPS = []
    MODULE_DESCRIPTION = 'Sends you alerts by email.'
    MODULE_LOCKED = False
    MODULE_URL = 'https://github.com/tangb/Cleep/wiki/ModuleSmtp'
    MODULE_TAGS = ['email', 'smtp', 'alert']

    DEFAULT_CONFIG = {
        'smtp_server': None,
        'smtp_port': '',
        'smtp_login': '',
        'smtp_password': '',
        'smtp_tls': False,
        'smtp_ssl': False,
        'email_sender':''
    }

    PROVIDER_PROFILE = [EmailProfile()]
    PROVIDER_TYPE = 'alert.email'

    def __init__(self, bus, debug_enabled):
        """
        Constructor

        Args:
            bus (MessageBus): MessageBus instance
            debug_enabled (bool): flag to set debug level to logger
        """
        #init
        RaspIotProvider.__init__(self, bus, debug_enabled)

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
            self.logger.debug('Send email: %s:%s@%s:%s from %s SSl:%s TLS:%s' % (smtp_login, smtp_password, smtp_server, str(smtp_port), email_sender, str(smtp_ssl), str(smtp_tls)))
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
            mail = MIMEMultipart('alternative')
            mail['Subject'] = data.subject
            mail['From'] = email_sender
            mail['To'] = data.recipients[0]
            text = """%s""" % (data.message)
            html  = "<html><head></head><body>%s</body>" % (data.message)
            part1 = MIMEText(text, 'plain')
            part2 = MIMEText(html, 'html')
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
                        ctype = 'application/octet-stream'
                    maintype, subtype = ctype.split('/', 1)
                    if maintype == 'text':
                        fp = open(data.attachment)
                        msg = MIMEText(fp.read(), _subtype=subtype)
                        fp.close()
                    elif maintype == 'image':
                        fp = open(data.attachment, 'rb')
                        msg = MIMEImage(fp.read(), _subtype=subtype)
                        fp.close()
                    elif maintype == 'audio':
                        fp = open(data.attachment, 'rb')
                        msg = MIMEAudio(fp.read(), _subtype=subtype)
                        fp.close()
                    else:
                        fp = open(data.attachment, 'rb')
                        msg = MIMEBase(maintype, subtype)
                        msg.set_payload(fp.read())
                        fp.close()
                        #encode the payload using Base64
                        encoders.encode_base64(msg)
                    #set the filename parameter
                    msg.add_header('Content-Disposition', 'attachment', filename=os.path.basename(data.attachment))
                    mail.attach(msg)

            #send email
            mails.sendmail(email_sender, data.recipients, mail.as_string())
            mails.quit()

        except smtplib.SMTPServerDisconnected as e:
            self.logger.exception('Failed to send test:')
            raise Exception('Server disconnected')

        except smtplib.SMTPSenderRefused as e:
            self.logger.exception('Failed to send test:')
            raise Exception('Email sender must be a valid email address')

        except smtplib.SMTPRecipientsRefused as e:
            self.logger.exception('Failed to send test:')
            raise Exception('Some recipients were refused')

        except smtplib.SMTPDataError as e:
            self.logger.exception('Failed to send test:')
            raise Exception('Problem with email content')

        except smtplib.SMTPConnectError as e:
            self.logger.exception('Failed to send test:')
            raise Exception('Unable to establish connection with smtp server. Please check server address')

        except smtplib.SMTPAuthenticationError as e:
            self.logger.exception('Failed to send test:')
            raise Exception('Authentication failed. Please check credentials.')
            
        except Exception as e:
            self.logger.exception('Failed to send test:')
            raise Exception(str(e))

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
            raise MissingParameter('Smtp_server parameter is missing')
        if smtp_port is None:
            raise MissingParameter('smtp_port parameter is missing')
        if smtp_login is None:
            raise MissingParameter('Smtp_login parameter is missing')
        if smtp_password is None:
            raise MissingParameter('Smtp_password parameter is missing')
        if smtp_tls is None:
            raise MissingParameter('Smtp_tls parameter is missing')
        if smtp_ssl is None:
            raise MissingParameter('Smtp_ssl parameter is missing')
        if email_sender is None:
            raise MissingParameter('Email_sender parameter is missing')
        if len(email_sender)==0:
            email_sender = 'test@cleep.com'
        if recipient is None or len(recipient)==0:
            raise MissingParameter('Recipient parameter is missing')

        #test config
        try:
            self.test(recipient, smtp_server, smtp_port, smtp_login, smtp_password, smtp_tls, smtp_ssl, email_sender)
        except Exception as e:
            raise CommandError(str(e))

        #save config
        config = self._get_config()
        config['smtp_server'] = smtp_server
        config['smtp_port'] = smtp_port
        config['smtp_login'] = smtp_login
        config['smtp_password'] = smtp_password
        config['smtp_tls'] = smtp_tls
        config['smtp_ssl'] = smtp_ssl
        config['email_sender'] = email_sender

        return self._save_config(config)

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
            raise CommandError('Recipient parameter is missing')

        if smtp_server is None or smtp_login is None or smtp_password is None:
            config = self._get_config()
            if config['smtp_server'] is None or len(config['smtp_server'])==0 or config['smtp_login'] is None or len(config['smtp_login'])==0 or config['smtp_password'] is None or len(config['smtp_password'])==0:
                raise CommandError('Please fill config first')

            smtp_server = config['smtp_server']
            smtp_port = config['smtp_port']
            smtp_login = config['smtp_login']
            smtp_password = config['smtp_password']
            smtp_tls = config['smtp_tls']
            smtp_ssl = config['smtp_ssl']
            email_sender = config['email_sender']

        #prepare data
        data = EmailProfile()
        data.subject = 'Cleep test'
        data.message = 'Hello this is Cleep'
        data.recipients.append(recipient)

        #send email
        self.__send_email(smtp_server, smtp_port, smtp_login, smtp_password, smtp_tls, smtp_ssl, email_sender, data)

        return True

    def _post(self, data):
        """
        Post data

        Params:
            data (EmailProfile): EmailProfile instance

        Returns:
            bool: True if post succeed, False otherwise
        """
        config = self._get_config()
        if config['smtp_server'] is None or config['email_sender'] is None:
            #not configured
            raise CommandError('Can\'t send email because module is not configured')

        #send email
        self.__send_email(config['smtp_server'], config['smtp_port'], config['smtp_login'], config['smtp_password'], config['smtp_tls'], config['smtp_ssl'], config['email_sender'], data)

        return True

