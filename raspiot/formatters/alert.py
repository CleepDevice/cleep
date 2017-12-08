#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.formatters.formatter import Formatter
from raspiot.profiles import *
import time

__all__ = [u'EmailFormatter']


class EmailFormatter(Formatter):
    """
    Email data to EmailProfile
    """
    def __init__(self, events_factory):
        """
        Constuctor

        Args:
            events_factory (EventsFactory): events factory instance
        """
        Formatter.__init__(self, events_factory, u'alert.email.send', EmailProfile())

    def _fill_profile(self, event_values, profile):
        """
        Fill profile with event data
        """
        profile.subject = event_values[u'subject']
        profile.message = event_values[u'message']
        profile.attachment = event_values[u'attachment']
        profile.recipients = event_values[u'recipients']

        return profile


class SmsFormatter(Formatter):
    """
    Sms data to SmsProfile
    """
    def __init__(self, events_factory):
        """
        Constuctor

        Args:
            events_factory (EventsFactory): events factory instance
        """
        Formatter.__init__(self, events_factory, u'alert.sms.send', SmsProfile())

    def _fill_profile(self, event_values, profile):
        """
        Fill profile with event data
        """
        profile.message = event_values[u'message']

        return profile


class PushFormatter(Formatter):
    """
    Push data to PushProfile
    """
    def __init__(self, events_factory):
        """
        Constuctor

        Args:
            events_factory (EventsFactory): events factory instance
        """
        Formatter.__init__(self, events_factory, u'alert.push.send', PushProfile())

    def _fill_profile(self, event_values, profile):
        """
        Fill profile with event data
        """
        profile.message = event_values[u'title']
        profile.message = event_values[u'priority']
        profile.message = event_values[u'message']
        profile.message = event_values[u'devices']
        profile.message = event_values[u'attachment']
        profile.message = event_values[u'timestamp']

        return profile

