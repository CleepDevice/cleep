#!/usr/bin/env python
# -*- coding: utf-8 -*-

class RendererProfile():
    """ 
    Base renderer profile class
    It implements to_dict and __str__ functions
    """
    def __init__(self):
        pass

    def __str__(self):
        """ 
        Returns printable profile string
        """
        #exclude private members
        members = {k:v for k,v in self.__dict__.items() if not k.startswith(u'_') and not callable(k)}
        return u'%s: %s' % (self.__class__.__name__, members)

    def to_dict(self):
        """ 
        Returns profile as dictionary (with member values and without private members)

        Returns:
            dict: profile
        """
        return {k:v for k,v in self.__dict__.items() if not k.startswith(u'_')}

