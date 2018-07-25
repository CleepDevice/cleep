#!/usr/bin/env python
# -*- coding: utf-8 -*

"""
Code from https://michelanders.blogspot.com/2010/12/calulating-sunrise-and-sunset-in-python.html
"""

from math import cos,sin,acos,asin,tan
from math import degrees as deg, radians as rad
from datetime import date, datetime, time, tzinfo, timedelta
import time as _time
import logging
from pytz import timezone
from tzlocal import get_localzone

ZERO = timedelta(0)
HOUR = timedelta(hours=1)
STDOFFSET = timedelta(seconds = -_time.timezone)
if _time.daylight:
    DSTOFFSET = timedelta(seconds = -_time.altzone)
else:
    DSTOFFSET = STDOFFSET
DSTDIFF = DSTOFFSET - STDOFFSET

class LocalTimezone(tzinfo):
    """
    Code from https://docs.python.org/2.7/library/datetime.html#datetime.tzinfo.fromutc
    """
    def utcoffset(self, dt):
        if self._isdst(dt):
            return DSTOFFSET
        else:
            return STDOFFSET

    def dst(self, dt):
        if self._isdst(dt):
            return DSTDIFF
        else:
            return ZERO

    def tzname(self, dt):
        return _time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
              dt.hour, dt.minute, dt.second,
              dt.weekday(), 0, 0)
        stamp = _time.mktime(tt)
        tt = _time.localtime(stamp)
        return tt.tm_isdst > 0

class Sun:
    """
    Calculate sunrise and sunset based on equations from NOAA
    http://www.srrb.noaa.gov/highlights/sunrise/calcdetails.html
    
    typical use, calculating the sunrise at the present day:
    
    import datetime
    import sunrise
    s = sun(lat=49,long=3)
    print('sunrise at ',s.sunrise(when=datetime.datetime.now())
    """
    def __init__(self):
        """
        Constructor
        """
        #member
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)

    def setPosition(self, lat, long, timezone_name=None):
        """
        Set position to use for computation
    
        Args:
            lat (float): latitude
            long (flat): longitude
        """
        self.lat = lat
        self.long = long
        self.timezone_name = timezone_name

        if not timezone_name:
            self.timezone_obj = get_localzone()
        else:
            self.timezone_obj = timezone(timezone_name)

    def sunrise(self, when=None):
        """
        return the time of sunrise as a datetime.time object
        when is a datetime.datetime object. If none is given
        a local time zone is assumed (including daylight saving
        if present)
        """
        #if self.timezone_name is not None:
        #    when = datetime.now(tz=timezone(self.timezone_name))
        #elif when is None:
        #    when = datetime.now(tz=LocalTimezone())
        when = self.timezone_obj.localize(datetime.now())
        self.__preptime(when)
        self.__calc()

        return self.__to_datetime(self.sunrise_t)

    def sunset(self, when=None):
        #if self.timezone_name is not None:
        #    when = datetime.now(tz=timezone(self.timezone_name))
        #elif when is None:
        #    when = datetime.now(tz=LocalTimezone())
        when = self.timezone_obj.localize(datetime.now())
        self.__preptime(when)
        self.__calc()

        return self.__to_datetime(self.sunset_t)

    def solarnoon(self):
        #if self.timezone_name is not None:
        #    when = datetime.now(tz=timezone(self.timezone_name))
        #elif when is None:
        #    when = datetime.now(tz=LocalTimezone())
        when = self.timezone_obj.localize(datetime.now())
        self.__preptime(when)
        self.__calc()

        return self.__to_datetime(self.solarnoon_t)

    def __timefromdecimalday(self, day):
        """
        returns a datetime.time object.

        day is a decimal day between 0.0 and 1.0, e.g. noon = 0.5
        """ 
        hours = 24.0*day
        h = int(hours)
        minutes = (hours-h)*60
        m = int(minutes)
        seconds = (minutes-m)*60
        s = int(seconds)

        return time(hour=h,minute=m,second=s)

    def __to_datetime(self, day):
        """
        Convert time instance to timestamp

        Returns:
            float: timestamp
        """
        try:
            hours = 24.0 * day
            h = int(hours)
            minutes = (hours-h)*60
            m = int(minutes)
            seconds = (minutes-m)*60
            s = int(seconds)
            t = time(hour=h,minute=m,second=s)

            now = self.timezone_obj.localize(datetime.now())
            now_str = '%d/%0.2d/%0.2d %0.2d:%0.2d:%0.2d' % (now.day, now.month, now.year, t.hour, t.minute, t.second)

            dt = datetime.strptime(now_str, '%d/%m/%Y %H:%M:%S')
            dt_localized = self.timezone_obj.localize(dt)
            #self.logger.error(when.tzinfo.dst(when))
            return dt_localized

        except ValueError:
            raise Exception(u'Trying to convert time from invalid position')

    def __preptime(self, when):
        """
        Extract information in a suitable format from when,
        a datetime.datetime object.
        """
        # datetime days are numbered in the Gregorian calendar
        # while the calculations from NOAA are distibuted as
        # OpenOffice spreadsheets with days numbered from
        # 1/1/1900. The difference are those numbers taken for
        # 18/12/2010
        self.day = when.toordinal()-(734124-40529)
        t=when.time()
        self.time = (t.hour + t.minute/60.0 + t.second/3600.0)/24.0

        self.timezone = 0
        offset = when.utcoffset()
        if not offset is None:
            #self.timezone=offset.seconds/3600.0
            self.timezone = offset.seconds/3600.0 + (offset.days * 24)

    def __calc(self):
        """
        Perform the actual calculations for sunrise, sunset and
        a number of related quantities.

        The results are stored in the instance variables
        sunrise_t, sunset_t and solarnoon_t
        """
        timezone = self.timezone # in hours, east is positive
        longitude = self.long     # in decimal degrees, east is positive
        latitude = self.lat      # in decimal degrees, north is positive

        time = self.time # percentage past midnight, i.e. noon  is 0.5
        day = self.day     # daynumber 1=1/1/1900

        Jday = day+2415018.5+time-timezone/24 # Julian day
        Jcent = (Jday-2451545)/36525    # Julian century

        Manom = 357.52911+Jcent*(35999.05029-0.0000001267*Jcent)
        Mlong = 280.46646+Jcent*(36000.76983+Jcent*0.0003032)%360
        Eccent = 0.016708634-Jcent*(0.000042037+0.0000001267*Jcent)
        Mobliq = 23+(26+((21.448-Jcent*(46.815+Jcent*(0.00059-Jcent*0.001813))))/60)/60
        obliq = Mobliq+0.00256*cos(rad(125.04-1934.136*Jcent))
        vary = tan(rad(obliq/2))*tan(rad(obliq/2))
        Seqcent = sin(rad(Manom))*(1.914602-Jcent*(0.004817+0.000014*Jcent))+sin(rad(2*Manom))*(0.019993-0.000101*Jcent)+sin(rad(3*Manom))*0.000289
        Struelong = Mlong+Seqcent
        Sapplong = Struelong-0.00569-0.00478*sin(rad(125.04-1934.136*Jcent))
        declination = deg(asin(sin(rad(obliq))*sin(rad(Sapplong)))) 

        eqtime = 4*deg(vary*sin(2*rad(Mlong))-2*Eccent*sin(rad(Manom))+4*Eccent*vary*sin(rad(Manom))*cos(2*rad(Mlong))-0.5*vary*vary*sin(4*rad(Mlong))-1.25*Eccent*Eccent*sin(2*rad(Manom)))

        hourangle = deg(acos(cos(rad(90.833))/(cos(rad(latitude))*cos(rad(declination)))-tan(rad(latitude))*tan(rad(declination))))

        self.solarnoon_t = (720-4*longitude-eqtime+timezone*60)/1440
        self.sunrise_t = self.solarnoon_t-hourangle*4/1440
        self.sunset_t = self.solarnoon_t+hourangle*4/1440

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

    s = Sun()
    #rennes
    s.setPosition(47.9832, -1.6236)
    #WDC
    #s.setPosition(38.89958342598271, -77.01278686523439)
    #fiji
    #s.setPosition(-18.1279, 178.4492)
    #NY USA
    #s.setPosition(40.6971, -73.9796)
    logging.info(datetime.today())
    sunrise = s.sunrise()
    logging.info('SUNRISE=%s - %s - %s' % (sunrise, sunrise.strftime('%s'), sunrise.hour))
    sunset = s.sunset()
    logging.info('SUNSET=%s' % (sunset))

