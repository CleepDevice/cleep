#!/usr/bin/env python
# -*- coding: utf-8 -*-
   
import binascii
from passlib.utils import pbkdf2
import base64
import io
import os

from raspiot.libs.internals import __all__ as internals_libs
from raspiot.libs.externals import __all__ as externals_libs
from raspiot.libs.drivers import __all__ as drivers_libs
from raspiot.libs.configs import __all__ as configs_libs
from raspiot.libs.commands import __all__ as commands_libs


DBM_TO_PERCENT = {-1:100, -2:100, -3:100, -4:100, -5:100, -6:100, -7:100, -8:100, -9:100, -10:100, -11:100, -12:100, -13:100, -14:100, -15:100, -16:100, -17:100, -18:100, -19:100, -20:100, -21:99, -22:99, -23:99, -24:98, -25:98, -26:98, -27:97, -28:97, -29:96, -30:96, -31:95, -32:95, -33:94, -34:93, -35:93, -36:92, -37:91, -38:90, -39:90, -40:89, -41:88, -42:87, -43:86, -44:85, -45:84, -46:83, -47:82, -48:81, -49:80, -50:79, -51:78, -52:76, -53:75, -54:74, -55:73, -56:71, -57:70, -58:69, -59:67, -60:66, -61:64, -62:63, -63:61, -64:60, -65:58, -66:56, -67:55, -68:53, -69:51, -70:50, -71:48, -72:46, -73:44, -74:42, -75:40, -76:38, -77:36, -78:34, -79:32, -80:30, -81:28, -82:26, -83:24, -84:22, -85:20, -86:17, -87:15, -88:13, -89:10, -90:8, -91:6, -92:3, -93:1, -94:1, -95:1, -96:1, -97:1, -98:1, -99:1, -100:1}

def dbm_to_percent(dbm):
    """
    Convert dbm signal level to percentage

    Note:
        Article here https://www.adriangranados.com/blog/dbm-to-percent-conversion

    Args:
        dbm (int): dbm value

    Return:
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

    Return:
        string: generated psk
    """
    psk = pbkdf2.pbkdf2(str.encode(password), str.encode(ssid), 4096, 32)
    return binascii.hexlify(psk).decode("utf-8")

def file_to_base64(path):
    """
    Convert specified file to base64 string

    Args:
        path (string): path to file

    Return:
        string: base64 encoded file content
    """
    with io.open(path, u'rb') as file_to_convert:
        return base64.b64encode(file_to_convert.read())

def hr_uptime(uptime):
    """  
    Human readable uptime (in days/hours/minutes/seconds)

    Note:
        http://unix.stackexchange.com/a/27014

    Params:
        uptime (int): uptime value

    Returns:
        string: human readable string
    """
    #get values
    days = uptime / 60 / 60 / 24 
    hours = uptime / 60 / 60 % 24 
    minutes = uptime / 60 % 60 

    return u'%dd %dh %dm' % (days, hours, minutes)

def hr_bytes(n):
    """  
    Human readable bytes value

    Note:
        http://code.activestate.com/recipes/578019

    Args:
        n (int): bytes

    Returns:
        string: human readable bytes value
    """
    symbols = (u'K', u'M', u'G', u'T', u'P', u'E', u'Z', u'Y')
    prefix = {} 

    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i + 1) * 10 

    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return u'%.1f%s' % (value, s)

    return u'%sB' % n

def compare_versions(old_version, new_version):
    """ 
    Compare specified version and return True if new version is greater than old one

    Args:
        old_version (string): old version
        new_version (string): new version

    Return:
        bool: True if new version available
    """
    #check versions
    try:
        old_vers = tuple(map(int, (old_version.split(u'.'))))
        if len(old_vers)!=3:
            raise Exception('Invalid version format for "%s"' % old_version)
    except:
        self.logger.exception(u'Invalid version format, only 3 digits format allowed:')
        return False
    try:
        new_vers = tuple(map(int, (new_version.split(u'.'))))
        if len(new_vers)!=3:
            raise Exception('Invalid version format for "%s"' % new_version)
    except:
        self.logger.exception(u'Invalid version format, only 3 digits format allowed:')
        return False

    #compare version
    if old_vers<new_vers:
        return True

    return False

def split_all(path):
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
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])

    return allparts

def is_system_lib(path):
    """ 
    Check if specified lib is a system one (provided by raspiot)

    Args:
        path (string): lib path

    Returns:
        bool: True if lib is system lib, False otherwise
    """
    #split path
    parts = split_all(path)
    if len(parts)<=2:
        #invalid path specified, cannot be a library
        return False

    #get useful infos (supposing libs path is ../../libs/XXXX/libname.py
    filename_wo_ext = os.path.splitext(parts[len(parts)-1])[0]
    libs_part = parts[len(parts)-3]
    sublibs_part = parts[len(parts)-2]

    #check
    if libs_part!=u'libs':
        return False
    if sublibs_part not in (u'internals', u'externals', u'drivers', u'commands', u'configs'):
        return False
    if sublibs_part==u'internals' and filename not in internals_libs:
        return False
    elif sublibs_part==u'externals' and filename not in externals_libs:
        return False
    elif sublibs_part==u'drivers' and filename not in drivers_libs:
        return False
    elif sublibs_part==u'commands' and filename not in commands_libs:
        return False
    elif sublibs_part==u'configs' and filename not in configs_libs:
        return False

    return True

