#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import InvalidParameter
from raspiot.libs.internals.rendererprofile import RendererProfile

__all__ = ['ProfileFormatter']

class ProfileFormatter():
    """
    Base ProfileFormatter class
    Used to format profile with specified event parameters
    """

    def __init__(self, events_broker, event_name, profile):
        """
        Constructor

        Args:
            events_broker (EventsBroker): events broker instance
            event_name (string): event name compatible with formatter
            profile (RendererProfile): Renderer profile instance
        """
        if not isinstance(event_name, str) and not isinstance(event_name, unicode):
            raise InvalidParameter(u'Invalid event_name specified')
        if not issubclass(profile.__class__, RendererProfile):
            raise InvalidParameter(u'Invalid profile specified. Instance must inherits from RendererProfile')

        # members
        self.events_broker = events_broker
        self.event_name = event_name
        self.profile_name = profile.__class__.__name__
        self.profile = profile

    def format(self, event_params):
        """
        Format event

        Args:
            event_params (list): list of event parameters as received from internal bus

        Returns:
            Profile instance filled with appropriate values
        """
        if not isinstance(event_params, list):
            raise InvalidParameter(u'Parameter "event_params" must be a list')

        return self._fill_profile(event_params, self.profile)
    
    def _fill_profile(self, event_params, profile):
        """
        Fll profile with event data
  
        Args:
           event_params (dict): event parameters
           profile (Profile): profile instance

        Returns:
            Profile instance filled with appropriate values
        """
        raise NotImplementedError('_fill_profile method must be implemented in "%s"' % self.__class__.__name__)

