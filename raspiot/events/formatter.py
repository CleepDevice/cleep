#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import InvalidParameter
from raspiot.events.rendererProfile import RendererProfile

__all__ = ['Formatter']

class Formatter():
    """
    Base formatter class
    """

    def __init__(self, events_factory, event_name, profile):
        """
        Constructor

        Args:
            events_factory (EventsFactory): events factory instance
            event_name (string): event name compatible with formatter
            output_profile (RendererProfile): Renderer profile instance
        """
        if not isinstance(event_name, str) and not isinstance(event_name, unicode):
            raise InvalidParameter(u'Invalid event_name specified (awaited string, found %s)' % (type(event_name)))
        if not issubclass(profile.__class__, RendererProfile):
            raise InvalidParameter(u'Invalid profile specified. Instance must inherits from RendererProfile.')

        #memebers
        self.events_factory = events_factory
        self.event_name = event_name
        self.profile_name = profile.__class__.__name__
        self.profile = profile

        #get event instance
        self.event = self.events_factory.get_event_instance(self.event_name)

    def format(self):
        """
        Format event
        """
        return self._fill_profile(self.event, self.profile)
    
    def _fill_profile(self, event_values, profile):
        """
        Fll profile with event data
  
        Args:
           event_values (dict): event values
           profile (Profile): profile instance
        """
        raise NotImplementedError('_fill_profile method must be implemented')

