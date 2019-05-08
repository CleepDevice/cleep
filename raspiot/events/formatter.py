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

        #members
        self.events_factory = events_factory
        self.event_name = event_name
        self.profile_name = profile.__class__.__name__
        self.profile = profile

    def format(self, event_params):
        """
        Format event
        """
        return self._fill_profile(event_params, self.profile)
    
    def _fill_profile(self, event_params, profile):
        """
        Fll profile with event data
  
        Args:
           event_params (dict): event parameters
           profile (Profile): profile instance
        """
        raise NotImplementedError('_fill_profile method must be implemented in "%s"' % self.__class__.__name__)

