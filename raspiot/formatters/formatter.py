#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ['Formatter']

class Formatter():
    """
    Base class formatter
    """

    def __init__(self, input, output):
        self.input = input
        self.output = output.__class__.__name__


