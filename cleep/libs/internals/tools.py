#!/usr/bin/env python
# -*- coding: utf-8 -*-

import binascii
import base64
import io
import os
import logging
import sys
import subprocess
import platform
from passlib.utils import pbkdf2
from cleep.libs.internals import __all__ as internals_libs
from cleep.libs.drivers import __all__ as drivers_libs
from cleep.libs.configs import __all__ as configs_libs
from cleep.libs.commands import __all__ as commands_libs

#from https://elinux.org/RPi_HardwareHistory
RASPBERRY_PI_REVISIONS = {
    'unknown': {
        'date': '?',
        'model': '?',
        'pcbrevision': '?',
        'ethernet': False,
        'wireless': False,
        'audio':False,
        'gpiopins': 0,
        'memory': '?',
        'notes': 'Unknown model'
    },
    '0002': {
        'date': 'Q1 2012',
        'model': 'B',
        'pcbrevision': '1.0',
        'ethernet': True,
        'wireless': False,
        'audio': True,
        'gpiopins': 26,
        'memory': '256 MB',
        'notes': ''
    },
    '0003':{
        'date': 'Q3 2012',
        'model': 'B (ECN0001)',
        'pcbrevision': '1.0',
        'ethernet': True,
        'wireless': False,
        'audio': True,
        'gpiopins': 26,
        'memory': '256 MB',
        'notes': 'Fuses mod and D14 removed'
    },
    '0004': {
        'date': 'Q3 2012',
        'model': 'B',
        'pcbrevision': '2.0',
        'ethernet': True,
        'wireless': False,
        'audio': True,
        'gpiopins': 26,
        'memory': '256 MB',
        'notes': '(Mfg by Sony)'
    },
    '0005': {
        'date': 'Q4 2012',
        'model': 'B',
        'pcbrevision': '2.0',
        'ethernet': True,
        'wireless': False,
        'audio': True,
        'gpiopins': 26,
        'memory': '256 MB',
        'notes': '(Mfg by Qisda)'
    },
    '0006': {
        'date': 'Q4 2012',
        'model': 'B',
        'pcbrevision': '2.0',
        'ethernet': True,
        'wireless': False,
        'audio': True,
        'gpiopins': 26,
        'memory': '256 MB',
        'notes': '(Mfg by Egoman)'
    },
    '0007': {
        'date': 'Q1 2013',
        'model': 'A',
        'pcbrevision': '2.0',
        'ethernet': False,
        'wireless': False,
        'audio': True,
        'gpiopins': 26,
        'memory': '256 MB',
        'notes': '(Mfg by Egoman)'
    },
    '0008': {
        'date': 'Q1 2013',
        'model': 'A',
        'pcbrevision': '2.0',
        'ethernet': False,
        'wireless': False,
        'audio': True,
        'gpiopins': 26,
        'memory': '256 MB',
        'notes': '(Mfg by Sony)'
    },
    '0009': {
        'date': 'Q1 2013',
        'model': 'A',
        'pcbrevision': '2.0',
        'ethernet': False,
        'wireless': False,
        'audio': True,
        'gpiopins': 26,
        'memory': '256 MB',
        'notes': '(Mfg by Qisda)'
    },
    '000d': {
        'date': 'Q4 2012',
        'model': 'B',
        'pcbrevision': '2.0',
        'ethernet': True,
        'wireless': False,
        'audio': True,
        'gpiopins': 26,
        'memory': '512 MB',
        'notes': '(Mfg by Egoman)'
    },
    '000e': {
        'date': 'Q4 2012',
        'model': 'B',
        'pcbrevision': '2.0',
        'ethernet': True,
        'wireless': False,
        'audio': True,
        'gpiopins': 26,
        'memory': '512 MB',
        'notes': '(Mfg by Sony)'
    },
    '000f': {
        'date': 'Q4 2012',
        'model': 'B',
        'pcbrevision': '2.0',
        'ethernet': True,
        'wireless': False,
        'audio': True,
        'gpiopins': 26,
        'memory': '512 MB',
        'notes': '(Mfg by Qisda)'
    },
    '0010': {
        'date': 'Q3 2014',
        'model': 'B+',
        'pcbrevision': '1.0',
        'ethernet': True,
        'wireless': False,
        'audio': True,
        'gpiopins': 40,
        'memory': '512 MB',
        'notes': '(Mfg by Sony)'
    },
    '0011': {
        'date': 'Q2 2014',
        'model': 'Compute Module 1',
        'pcbrevision': '1.0',
        'ethernet': False,
        'wireless': False,
        'audio': True,
        'gpiopins': 0,
        'memory': '512 MB',
        'notes': '(Mfg by Sony)'
    },
    '0012': {
        'date': 'Q4 2014',
        'model': 'A+',
        'pcbrevision': '1.1',
        'ethernet': False,
        'wireless': False,
        'audio': True,
        'gpiopins': 40,
        'memory': '256 MB',
        'notes': '(Mfg by Sony)'
    },
    '0013': {
        'date': 'Q1 2015',
        'model': 'B+',
        'pcbrevision': '1.2',
        'ethernet': True,
        'wireless': False,
        'audio': True,
        'gpiopins': 40,
        'memory': '512 MB',
        'notes': '(Mfg by Embest)'
    },
    '0014':{
        'date': 'Q2 2014',
        'model': 'Compute Module 1',
        'pcbrevision': '1.0',
        'ethernet': False,
        'wireless': False,
        'audio': True,
        'gpiopins': 0,
        'memory': '512 MB',
        'notes': '(Mfg by Embest)'
    },
    '0015': {
        'date': '?',
        'model': 'A+',
        'pcbrevision': '1.1',
        'ethernet': False,
        'wireless': False,
        'audio': True,
        'gpiopins': 40,
        'memory': '256 MB/512 MB',
        'notes': '(Mfg by Embest)'
    },
    'a01040': {
        'date': 'Unknown',
        'model': '2 Model B',
        'pcbrevision': '1.0',
        'ethernet': True,
        'wireless': False,
        'audio': True,
        'gpiopins': 40,
        'memory': '1 GB',
        'notes': '(Mfg by Sony)'
    },
    'a01041': {
        'date': 'Q1 2015',
        'model': '2 Model B',
        'pcbrevision': '1.1',
        'ethernet': True,
        'wireless': False,
        'audio': True,
        'gpiopins': 40,
        'memory': '1 GB',
        'notes': '(Mfg by Sony)'
    },
    'a21041': {
        'date': 'Q1 2015',
        'model': '2 Model B',
        'pcbrevision': '1.1',
        'ethernet': True,
        'wireless': False,
        'audio': True,
        'gpiopins': 40,
        'memory': '1 GB',
        'notes': '(Mfg by Embest)'
    },
    'a22042': {
        'date': 'Q3 2016',
        'model': '2 Model B (with BCM2837)',
        'pcbrevision': '1.2',
        'ethernet': True,
        'wireless': False,
        'audio': True,
        'gpiopins': 40,
        'memory': '1 GB',
        'notes': '(Mfg by Embest)'
    },
    '900021': {
        'date': 'Q3 2016',
        'model': 'A+',
        'pcbrevision': '1.1',
        'ethernet': False,
        'wireless': False,
        'audio': True,
        'gpiopins': 40,
        'memory': '512 MB',
        'notes': '(Mfg by Sony)'
    },
    '900032': {
        'date': 'Q2 2016?',
        'model': 'B+',
        'pcbrevision': '1.2',
        'ethernet': True,
        'wireless': False,
        'audio': True,
        'gpiopins': 40,
        'memory': '512 MB',
        'notes': '(Mfg by Sony)'
    },
    '900092': {
        'date': 'Q4 2015',
        'model': 'Zero',
        'pcbrevision': '1.2',
        'ethernet': False,
        'wireless': False,
        'audio': False,
        'gpiopins': 40,
        'memory': '512 MB',
        'notes': '(Mfg by Sony)'
    },
    '900093': {
        'date': 'Q2 2016',
        'model': 'Zero',
        'pcbrevision': '1.3',
        'ethernet': False,
        'wireless': False,
        'audio': False,
        'gpiopins': 40,
        'memory': '512 MB',
        'notes': '(Mfg by Sony)'
    },
    '920093': {
        'date': 'Q4 2016?',
        'model': 'Zero',
        'pcbrevision': '1.3',
        'ethernet': False,
        'wireless': False,
        'audio': False,
        'gpiopins': 40,
        'memory': '512 MB',
        'notes': '(Mfg by Embest)'
    },
    '9000c1': {
        'date': 'Q1 2017',
        'model': 'Zero W',
        'pcbrevision': '1.1',
        'ethernet': False,
        'wireless': True,
        'audio': False,
        'gpiopins': 40,
        'memory': '512 MB',
        'notes': '(Mfg by Sony)'
    },
    'a02082': {
        'date': 'Q1 2016',
        'model': '3 Model B',
        'pcbrevision': '1.2',
        'ethernet': True,
        'wireless': True,
        'audio': True,
        'gpiopins': 40,
        'memory': '1 GB',
        'notes': '(Mfg by Sony)'
    },
    'a020a0': {
        'date': 'Q1 2017',
        'model': 'Compute Module 3 (and CM3 Lite)',
        'pcbrevision': '1.0',
        'ethernet': False,
        'wireless': False,
        'audio': True,
        'gpiopins': 0,
        'memory': '1 GB',
        'notes': '(Mfg by Sony)'
    },
    'a22082': {
        'date': 'Q1 2016',
        'model': '3 Model B',
        'pcbrevision': '1.2',
        'ethernet': True,
        'wireless': True,
        'audio': True,
        'gpiopins': 40,
        'memory': '1 GB',
        'notes': '(Mfg by Embest)'
    },
    'a32082': {
        'date': 'Q4 2016',
        'model': '3 Model B',
        'pcbrevision': '1.2',
        'ethernet': True,
        'wireless': True,
        'audio': True,
        'gpiopins': 40,
        'memory': '1 GB',
        'notes': '(Mfg by Sony Japan)'
    },
    'a020d3': {
        'date': 'Q1 2018',
        'model': '3 Model B+',
        'pcbrevision': '1.3',
        'ethernet': True,
        'wireless': True,
        'audio': True,
        'gpiopins': 40,
        'memory': '1 GB',
        'notes': '(Mfg by Sony)'
    },
    '9020e0': {
        'date': 'Q4 2018',
        'model': '3 Model A+',
        'pcbrevision': '1.0',
        'ethernet': False,
        'wireless': True,
        'audio': True,
        'gpiopins': 40,
        'memory': '512 MB',
        'notes': '(Mfg by Sony)'
    },
    'a03111': {
        'date': 'Q2 2019',
        'model': '4 Model B',
        'pcbrevision': '1.1',
        'ethernet': True,
        'wireless': True,
        'audio': True,
        'gpiopins': 40,
        'memory': '1 GB',
        'notes': '(Mfg by Sony)'
    },
    'b03111': {
        'date': 'Q2 2019',
        'model': '4 Model B',
        'pcbrevision': '1.1',
        'ethernet': True,
        'wireless': True,
        'audio': True,
        'gpiopins': 40,
        'memory': '2 GB',
        'notes': '(Mfg by Sony)'
    },
    'c03111': {
        'date': 'Q2 2019',
        'model': '4 Model B',
        'pcbrevision': '1.1',
        'ethernet': True,
        'wireless': True,
        'audio': True,
        'gpiopins': 40,
        'memory': '4 GB',
        'notes': '(Mfg by Sony)'
    },
}

def raspberry_pi_infos():
    """
    Returns infos about current raspberry pi board

    Note:
        https://elinux.org/RPi_HardwareHistory#Board_Revision_History

    Returns:
        dict: raspberry pi board infos::

            {
                date (string): release date
                model (string): raspberry pi model
                pcbrevision (string): PCB revision
                ethernet (bool): True if ethernet is natively available on board
                wireless (bool): True if wifi is natively available on board,
                audio (bool): True if audio is natively available on board
                gpiopins (int): number of pins available on board
                memory (string): memory amount
                notes (string): notes on board
                revision (string): raspberry pi revision
            }

    Raises:
        Exception if platform is not ARM
    """
    if not platform.machine().startswith('arm'):
        raise Exception('Not arm platform')
    cmd = '/usr/bin/awk \'/^Revision/ {sub("^1000", "", $3); print $3}\' /proc/cpuinfo'
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    revision = proc.communicate()[0].decode('utf-8').replace('\n', '')
    logging.trace('Raspberrypi revision=%s' % revision)
    infos = (RASPBERRY_PI_REVISIONS[revision]
            if revision and revision in RASPBERRY_PI_REVISIONS else RASPBERRY_PI_REVISIONS['unknown'])
    infos['revision'] = revision

    return infos

TRACE = logging.DEBUG - 5

def install_trace_logging_level():
    """
    Install custom log level TRACE for library debugging principaly
    Credits https://gist.github.com/numberoverzero/f803ebf29a0677b6980a5a733a10ca71
    """
    level = logging.TRACE = TRACE

    def log_logger(self, message, *args, **kwargs):
        if self.isEnabledFor(level):
            self._log(level, message, args, **kwargs)
    logging.getLoggerClass().trace = log_logger

    def log_root(msg, *args, **kwargs):
        logging.log(level, msg, *args, **kwargs)
    logging.addLevelName(level, "TRACE")
    logging.trace = log_root

def install_unhandled_exception_handler(crash_report): # pragma: no cover (can test it)
    """
    Overwrite default exception handler to log errors
    @see https://stackoverflow.com/a/16993115

    Args:
        crash_report (CrashReport): crash report instance
    """
    def handle_exception(exc_type, exc_value, exc_traceback):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        if issubclass(exc_type, KeyboardInterrupt):
            return
        if crash_report:
            crash_report.report_exception()
        logging.error('Uncaught exception', exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception

DBM_TO_PERCENT = {
    -1:100, -2:100, -3:100, -4:100, -5:100, -6:100, -7:100, -8:100, -9:100, -10:100, -11:100, -12:100, -13:100, -14:100,
    -15:100, -16:100, -17:100, -18:100, -19:100, -20:100, -21:99, -22:99, -23:99, -24:98, -25:98, -26:98, -27:97, -28:97,
    -29:96, -30:96, -31:95, -32:95, -33:94, -34:93, -35:93, -36:92, -37:91, -38:90, -39:90, -40:89, -41:88, -42:87, -43:86,
    -44:85, -45:84, -46:83, -47:82, -48:81, -49:80, -50:79, -51:78, -52:76, -53:75, -54:74, -55:73, -56:71, -57:70, -58:69,
    -59:67, -60:66, -61:64, -62:63, -63:61, -64:60, -65:58, -66:56, -67:55, -68:53, -69:51, -70:50, -71:48, -72:46, -73:44,
    -74:42, -75:40, -76:38, -77:36, -78:34, -79:32, -80:30, -81:28, -82:26, -83:24, -84:22, -85:20, -86:17, -87:15, -88:13,
    -89:10, -90:8, -91:6, -92:3, -93:1, -94:1, -95:1, -96:1, -97:1, -98:1, -99:1, -100:1
}

def dbm_to_percent(dbm):
    """
    Convert dbm signal level to percentage

    Note:
        Article here https://www.adriangranados.com/blog/dbm-to-percent-conversion

    Args:
        dbm (int): dbm value

    Returns:
        int: percentage value
    """
    if dbm in DBM_TO_PERCENT.keys():
        return DBM_TO_PERCENT[dbm]

    return 0

def wpa_passphrase(ssid, password):
    """
    Python implementation of wpa_passphrase linux utility
    It generates wpa_passphrase for wifi network connection

    Note:
        Copied from https://github.com/julianofischer/python-wpa-psk-rawkey-gen/blob/master/rawkey-generator.py

    Args:
        ssid (string): network ssid
        password (string): password

    Returns:
        string: generated psk
    """
    psk = pbkdf2.pbkdf2(str.encode(password), str.encode(ssid), 4096, 32)
    return binascii.hexlify(psk).decode("utf-8")

def file_to_base64(path):
    """
    Convert specified file to base64 string

    Args:
        path (string): path to file

    Returns:
        string: base64 encoded file content

    Raises:
        Exception of all kind if something wrong occured
    """
    with io.open(path, 'rb') as file_to_convert:
        return base64.b64encode(file_to_convert.read()).decode('utf-8')

def hr_uptime(uptime):
    """
    Human readable uptime (in days/hours/minutes/seconds)

    Note:
        http://unix.stackexchange.com/a/27014

    Args:
        uptime (int): uptime value

    Returns:
        string: human readable string
    """
    # get values
    days = uptime / 60 / 60 / 24
    hours = uptime / 60 / 60 % 24
    minutes = uptime / 60 % 60

    return '%dd %dh %dm' % (days, hours, minutes)

def hr_bytes(num):
    """
    Human readable bytes value

    Note:
        http://code.activestate.com/recipes/578019

    Args:
        n (int): bytes

    Returns:
        string: human readable bytes value
    """
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}

    for i, symbol in enumerate(symbols):
        prefix[symbol] = 1 << (i + 1) * 10

    for symbol in reversed(symbols):
        if num>=prefix[symbol]:
            value = float(num) / prefix[symbol]
            return '%.1f%s' % (value, symbol)

    return '%sB' % num

def compare_versions(old_version, new_version):
    """
    Compare specified version and return True if new version is strictly greater than old one

    Args:
        old_version (string): old version
        new_version (string): new version

    Returns:
        bool: True if new version available
    """
    # check versions
    old_vers = tuple(map(int, (old_version.split('.'))))
    if len(old_vers)!=3:
        raise Exception('Invalid version "%s" format, only 3 digits format allowed' % old_version)

    new_vers = tuple(map(int, (new_version.split('.'))))
    if len(new_vers)!=3:
        raise Exception('Invalid version "%s" format, only 3 digits format allowed' % new_version)

    # compare version
    if old_vers<new_vers:
        return True

    return False

def full_split_path(path):
    """
    Split path completely /home/test/test.txt => ['/', 'home', 'test', 'test.py']

    Note:
        code from https://www.safaribooksonline.com/library/view/python-cookbook/0596001673/ch04s16.html

    Returns:
        list: list of path parts
    """
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        if parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])

    return list(filter(lambda p: len(p)>0, allparts))

def is_core_lib(path):
    """
    Check if specified lib is a core library (provided by cleep)

    Args:
        path (string): lib path

    Returns:
        bool: True if lib is core lib, False otherwise
    """
    # split path
    parts = full_split_path(path)
    if len(parts)<=2:
        # invalid path specified, cannot be a library
        return False

    # get useful infos (supposing libs path is ../../libs/**/*.py
    filename_wo_ext = os.path.splitext(parts[len(parts)-1])[0]
    libs_part = parts[len(parts)-3]
    sublibs_part = parts[len(parts)-2]

    # check
    if libs_part!='libs':
        return False
    if sublibs_part not in ('internals', 'drivers', 'commands', 'configs'):
        return False
    if sublibs_part=='internals' and filename_wo_ext not in internals_libs:
        return False
    if sublibs_part=='drivers' and filename_wo_ext not in drivers_libs:
        return False
    if sublibs_part=='commands' and filename_wo_ext not in commands_libs:
        return False
    if sublibs_part=='configs' and filename_wo_ext not in configs_libs:
        return False

    return True

def netmask_to_cidr(netmask):
    """
    Convert netmask to cidr format

    Note:
        code from https://stackoverflow.com/a/43885814

    Args:
        netmask (string): netmask address

    Returns:
        int: cidr value
    """
    return sum([bin(int(x)).count('1') for x in netmask.split('.')])

def cidr_to_netmask(cidr):
    """
    Convert cidr to netmask

    Note:
        http://www.linuxquestions.org/questions/blog/bittner-195120/cidr-to-netmask-conversion-with-python-convert-short-netmask-to-long-dotted-format-3147/

    Args:
        cidr (int): cidr value

    Returns:
        string: netmask (ie 255.255.255.0)
    """
    mask = ''
    if not isinstance(cidr, int) or cidr<0 or cidr>32: # pragma: no cover
        return None

    for _ in range(4):
        if cidr > 7:
            mask += '255.'
        else:
            dec = 255 - (2**(8 - cidr) - 1)
            mask += str(dec) + '.'
        cidr -= 8
        if cidr < 0:
            cidr = 0

    return mask[:-1]

