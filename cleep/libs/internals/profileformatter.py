#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.exception import InvalidParameter
from cleep.libs.internals.rendererprofile import RendererProfile

__all__ = ['ProfileFormatter']

class ProfileFormatter():
    """
    Base ProfileFormatter class
    Used to format profile with specified event parameters
    """

    def __init__(self, params, event_name, profile):
        """
        Constructor

        Args:
            params (dict): ProfileFormatter parameters::

                {
                    events_broker (EventsBroker): EventsBroker instance
                }

            event_name (string): event name compatible with formatter
            profile (RendererProfile): Renderer profile instance
        """
        if not isinstance(event_name, str):
            raise InvalidParameter('Invalid event_name specified')
        if not issubclass(profile.__class__, RendererProfile):
            raise InvalidParameter('Invalid profile specified. Instance must inherits from RendererProfile')

        # members
        self.events_broker = params['events_broker']
        self.event_name = event_name
        self.profile_name = profile.__class__.__name__
        self.profile = profile

        # get event instance (it also registers event usage and trigger error if specified event does not exist)
        self.event = self.events_broker.get_event_instance(event_name)

    def format(self, event_params):
        """
        Format event

        Args:
            event_params (dict): list of event parameters as received from internal bus. Can be None.

        Returns:
            Profile instance filled with appropriate values
        """
        if not isinstance(event_params, dict) and not event_params is None:
            raise InvalidParameter('Parameter "event_params" must be a dict not %s' % type(event_params))

        return self._fill_profile(event_params or {}, self.profile)
    
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

