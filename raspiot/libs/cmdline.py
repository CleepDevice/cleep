#!/usr/bin/env python
# -*- coding: utf-8 -*-

from console import Console
from blkid import Blkid
import re
import time

class Cmdline():

    CACHE_DURATION = 5.0

    def __init__(self):
        self.console = Console()
        self.blkid = Blkid()
        self.timestamp = None
        self.root_device = None

    def __refresh(self):
        #check if refresh is needed
        if self.timestamp is not None and time.time()-self.timestamp<=self.CACHE_DURATION:
            return

        res = self.console.command(u'/bin/cat /proc/cmdline')
        if not res[u'error'] and not res[u'killed']:
            #parse data
            matches = re.finditer(r'root=(.*?)\s', u'\n'.join(res[u'stdout']), re.UNICODE | re.MULTILINE)
            for matchNum, match in enumerate(matches):
                groups = match.groups()
                if len(groups)==1:
                    if groups[0].startswith(u'UUID='):
                        #get device from uuid
                        uuid = groups[0].replace(u'UUID=', u'')
                        self.root_device = self.blkid.get_device(uuid)
                    else:
                        #get device from path
                        self.root_device = groups[0]

        self.timestamp = time.time()

    def get_root_device(self):
        self.__refresh()

        return self.root_device

