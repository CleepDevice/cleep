#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.internals.console import AdvancedConsole, EndlessConsole
import logging
import os
import uuid

class Sox(AdvancedConsole):
    """
    Sox commands helper (rec, sox, play).
    """
    
    CHANNELS_MONO = 1
    CHANNELS_STEREO = 2
    CHANNELS_DOLBY = 5

    RATE_8K = 8000
    RATE_16K = 16000
    RATE_22K = 22050
    RATE_44K = 44100
    RATE_48K = 48000

    FORMAT_8_BIT = u'-1'
    FORMAT_16_BIT = u'-2'
    FORMAT_24_BIT = u'-3'
    FORMAT_32_BIT = u'-4'
    FORMAT_64_BIT = u'-8'

    def __init__(self):
        """
        Constructor
        """
        AdvancedConsole.__init__(self)

        #members
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)

    def is_installed(self):
        """
        Return True if sox binaries are installed
        """
        return os.path.exists('/usr/bin/sox')

    def play_sound(self, path, timeout=5.0):
        """
        Play specified sound using rec command

        Args:
            path (string): sound file path
            timeout (float): max playing duration. If you want to play longer sound file, increase the timeout
        """
        #check params
        if not os.path.exists(path):
            raise Exception(u'Sound file doesn\'t exist (%s)' % path)

        #play sound
        res = self.command(u'/usr/bin/play "%s"' % path, timeout=timeout)
        if res[u'error'] and len(res[u'stderr'])>0 and not res[u'stderr'][0].startswith(u'Playing WAVE'):
            #for some strange reasons, aplay output is on stderr
            self.logger.error(u'Unable to play sound file "%s": %s' % (path, res))
            return False
        
        return True

    def record_sound(self, channels=2, rate=44100, format=u'-2', timeout=5.0):
        """
        Record sound

        Args:
            channels (int): number of channels to record (default 2 for stereo) (see CHANNELS_XXX)
            rate (int): rate (or frequency) to record (see RATE_XXX)
            format (string): encoding format (see FORMAT_XXX)
            timeout (float): max recording duration

        Return:
            string: path of recorded file (wav format)
        """
        #check params
        if channels is None:
            raise Exception(u'Parameter channels is missing')
        if channels not in (self.CHANNELS_MONO, self.CHANNELS_STEREO, self.CHANNELS_DOLBY):
            raise Exception(u'Parameter channels is invalid. Please check supported values.')
        if rate is None:
            raise Exception(u'Parameter rate is missing')
        if rate not in (self.RATE_8K, self.RATE_16K, self.RATE_22K, self.RATE_44K, self.RATE_48K):
            raise Exception(u'Parameter rate is invalid. Please check supported values.')
        if format is None:
            raise Exception(u'Parameter format is missing')
        if format not in (self.FORMAT_8_BIT, self.FORMAT_16_BIT, self.FORMAT_24_BIT, self.FORMAT_32_BIT, self.FORMAT_64_BIT):
            raise Exception(u'Parameter format is invalid. Please check supported values.')

        #record sound
        out = u'%s.wav' % os.path.join('/tmp', str(uuid.uuid4()))
        cmd = u'/usr/bin/rec -c %d -r %d %s -e signed-integer "%s"' % (channels, rate, format, out)
        self.logger.debug(u'Command: %s' % cmd)
        res = self.command(cmd, timeout=timeout)
        
        #check errors
        if res[u'error']:
            self.logger.error(u'Error occured during recording %s: %s' % (cmd, res))
            raise Exception(u'Error during recording')

        return out

    def trim_audio(self, audio, output=None, duration=0.1, threshold=10, timeout=5.0):
        """
        Remove silence at beginning and end of specified audio file

        Args:
            audio (string): audio file path
            output (string): if None input file will be overwriten, otherwise specified path will be used
            duration (float): duration of minimum silence to remove
            threshold (int): signal threshold above or below to detect silence in percentage (default 10%)
            timeout (float): timeout of trim command. If your file takes too much time to be trimmed increase this value

        Return:
            string: trimmed audio file or None if error occured
        """
        #check parameters
        if audio is None or len(audio)==0:
            raise Exception(u'Parameter audio is missing')
        if duration is None:
            raise Exception(u'Parameter duration is missing')
        if duration<0.0:
            raise Exception(u'Parameter duration is invalid, must be greater than 0')
        if threshold is None:
            raise Exception(u'Parameter threshold is missing')
        if threshold<0 or threshold>100:
            raise Exception(u'Parameter threshold is invalid: must be 0..100')

        #prepare output file
        if output is None:
            output = audio

        #prepare command
        cmd = u'/usr/bin/sox %(input)s %(output)s silence 1 %(duration).2f %(threshold)d%% -1 %(duration).2f %(threshold)d%%' % {'input':audio, 'output':output, 'threshold':threshold, 'duration':duration}
        self.logger.debug(u'Command: %s' % cmd)
        res = self.command(cmd)

        #check errors
        if res[u'error']:
            self.logger.error(u'Error occured during trimming %s: %s' % (cmd, res))
            return None

        return output

    def metronome_sound(self, bpm):
        """
        Play metronome sound at specified bpm using sox. Metronome sound is tone generated by sox

        Note:
            credits to https://www.reddit.com/r/bash/comments/2xv6r9/i_created_a_metronome_in_bash_seems_to_work/cp3qjnn/

        Args:
            bpm (int): beats per second

        Return:
            EndlessConsole: instance of EndlessConsole
        """
        if bpm is None:
            raise Exception(u'Parameter bpm is missing')
        if bpm<=0 or bpm>1000:
            raise Exception(u'Parameter bpm is invalid: must be 0..1000')

        #prepare command line
        cmd = u'bpm=%d; /usr/bin/play -q -n -c2 -r44100 synth 0.001 sine 1000 pad `awk "BEGIN { print 60/$bpm -.001 }"` vol 40 repeat 9999999' % bpm
        self.logger.debug('Command: %s' % cmd)

        #launch playback
        endless = EndlessConsole(cmd, lambda stdout, stderr: None)
        endless.start()

        return endless



