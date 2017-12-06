#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import InvalidParameter
from raspiot.rendering.profiles import RendererProfile

__all__ = ['Formatter']

class Formatter():
    """
    Base formatter class
    """

    def __init__(self, input_event, output_profile):
        """
        Constructor

        Args:
            input_event (string): input event compatible with formatter
            output_profile (RendererProfile): Renderer profile instance
        """
        if not isinstance(input_event, str) and not isinstance(input_event, unicode):
            raise InvalidParameter(u'Invalid input_event specified (awaited string, found %s)' % (type(input_event)))
        if not issubclass(output_profile.__class__, RendererProfile):
            raise InvalidParameter(u'Invalid output_profile specified. Instance must inherits from RendererProfile.')

        self.input_event = input_event
        self.output_profile = output_profile.__class__.__name__


