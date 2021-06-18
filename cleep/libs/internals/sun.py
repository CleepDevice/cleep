#!/usr/bin/env python
# -*- coding: utf-8 -*-

import calendar
import math
import datetime
from dateutil import tz
import logging


class Sun:
    """
    Sunset/sunrise times computation according to geographic position

    See:
        Code copied and adapted for Cleep from https://github.com/SatAgro/suntime/blob/master/suntime/suntime.py

    Note:
        Approximated calculation of sunrise and sunset datetimes. Adapted from:
        https://stackoverflow.com/questions/19615350/calculate-sunrise-and-sunset-times-for-a-given-gps-coordinate-within-postgresql
    """

    def __init__(self):
        """
        Constructor
        """
        self.latitude = 0.0
        self.longitude = 0.0
        self.logger = logging.getLogger(self.__class__.__name__)

    def set_position(self, latitude, longitude):
        """
        Set latitude and longitude for sunset/sunrise times computation

        Args:
            latitude (float): latitude
            longitude( float): longitude
        """
        self.latitude = latitude
        self.longitude = longitude

    def get_sunrise_time(self, date=None):
        """
        Calculate the sunrise time for given date.

        Args:
            date (datetime): reference date (default is today if nothing specified)

        Returns:
            datetime: UTC sunrise datetime

        Raises:
            Exception when there is no sunrise and sunset on given location and date
        """
        date = datetime.date.today() if date is None else date
        sr = self._calc_sun_time(date, True)
        if sr is None:
            raise Exception(
                "The sun never rises on this location (on the specified date)"
            )
        else:
            return sr

    def get_local_sunrise_time(self, date=None, local_time_zone=tz.tzlocal()):
        """
        Get sunrise time for local or custom time zone.

        Args:
            date (datetime): reference date (default is today if nothing specified)
            local_time_zone (tzlocal): local or custom time zone.

        Returns:
            datetime: local time zone sunrise datetime

        Raises:
            Exception if error occured
        """
        date = datetime.date.today() if date is None else date
        sr = self._calc_sun_time(date, True)
        if sr is None:
            raise Exception(
                "The sun never rises on this location (on the specified date)"
            )
        else:
            return sr.astimezone(local_time_zone)

    def sunrise(self):
        """
        Returns locale sunrise time
        Alias to get_local_sunrise_time for current date

        Returns:
            datetime: local sunrise datetime
        """
        return self.get_local_sunrise_time()

    def get_sunset_time(self, date=None):
        """
        Calculate the sunset time for given date.

        Args:
            date (datetime): custom date used for computation (default is today if not specified)

        Returns:
            datetime: UTC sunset datetime

        Raises:
            Exception if error occured
        """
        date = datetime.date.today() if date is None else date
        ss = self._calc_sun_time(date, False)
        if ss is None:
            raise Exception(
                "The sun never sets on this location (on the specified date)"
            )
        else:
            return ss

    def get_local_sunset_time(self, date=None, local_time_zone=tz.tzlocal()):
        """
        Get sunset time for local or custom time zone.

        Args:
            date (datetime): reference date (default to today if nothing specified)
            local_time_zone (tzlocal): local or custom time zone.

        Returns:
            datetime: local time zone sunset datetime

        Raises:
            Exception if error occured
        """
        date = datetime.date.today() if date is None else date
        ss = self._calc_sun_time(date, False)
        if ss is None:
            raise Exception(
                "The sun never sets on this location (on the specified date)"
            )
        else:
            return ss.astimezone(local_time_zone)

    def sunset(self):
        """
        Returns locale sunset time
        Alias to get_local_sunset_time for current date

        Returns:
            datetime: local sunset datetime
        """
        return self.get_local_sunset_time()

    def _calc_sun_time(self, date, is_rise_time=True, zenith=90.8):
        """
        Calculate sunrise or sunset date.

        Args:
            date (datetime): reference date
            is_rise_time (bool): True if you want to calculate sunrise time.
            zenith (float): sun reference zenith

        Returns:
            datetime: UTC sunset or sunrise datetime

        Raises:
            Exception when there is no sunrise and sunset on given location and date
        """
        day = date.day
        month = date.month
        year = date.year

        TO_RAD = math.pi / 180.0

        # 1. first calculate the day of the year
        N1 = math.floor(275 * month / 9)
        N2 = math.floor((month + 9) / 12)
        N3 = 1 + math.floor((year - 4 * math.floor(year / 4) + 2) / 3)
        N = N1 - (N2 * N3) + day - 30

        # 2. convert the longitude to hour value and calculate an approximate time
        lngHour = self.longitude / 15

        if is_rise_time:
            t = N + ((6 - lngHour) / 24)
        else:  # sunset
            t = N + ((18 - lngHour) / 24)

        # 3. calculate the Sun's mean anomaly
        M = (0.9856 * t) - 3.289

        # 4. calculate the Sun's true longitude
        L = (
            M
            + (1.916 * math.sin(TO_RAD * M))
            + (0.020 * math.sin(TO_RAD * 2 * M))
            + 282.634
        )
        L = self._force_range(L, 360)  # NOTE: L adjusted into the range [0,360)

        # 5a. calculate the Sun's right ascension

        RA = (1 / TO_RAD) * math.atan(0.91764 * math.tan(TO_RAD * L))
        RA = self._force_range(RA, 360)  # NOTE: RA adjusted into the range [0,360)

        # 5b. right ascension value needs to be in the same quadrant as L
        Lquadrant = (math.floor(L / 90)) * 90
        RAquadrant = (math.floor(RA / 90)) * 90
        RA = RA + (Lquadrant - RAquadrant)

        # 5c. right ascension value needs to be converted into hours
        RA = RA / 15

        # 6. calculate the Sun's declination
        sinDec = 0.39782 * math.sin(TO_RAD * L)
        cosDec = math.cos(math.asin(sinDec))

        # 7a. calculate the Sun's local hour angle
        cosH = (
            math.cos(TO_RAD * zenith) - (sinDec * math.sin(TO_RAD * self.latitude))
        ) / (cosDec * math.cos(TO_RAD * self.latitude))

        if cosH > 1:
            return None  # The sun never rises on this location (on the specified date)
        if cosH < -1:  # pragma: no cover - hard to test
            return None  # The sun never sets on this location (on the specified date)

        # 7b. finish calculating H and convert into hours

        if is_rise_time:
            H = 360 - (1 / TO_RAD) * math.acos(cosH)
        else:  # setting
            H = (1 / TO_RAD) * math.acos(cosH)

        H = H / 15

        # 8. calculate local mean time of rising/setting
        T = H + RA - (0.06571 * t) - 6.622

        # 9. adjust back to UTC
        UT = T - lngHour
        UT = self._force_range(UT, 24)  # UTC time in decimal format (e.g. 23.23)

        # 10. Return
        hr = self._force_range(int(UT), 24)
        min = round((UT - int(UT)) * 60, 0)
        if min == 60:
            hr += 1
            min = 0

        # 10. check corner case https://github.com/SatAgro/suntime/issues/1
        if hr == 24:
            hr = 0
            day += 1

            if day > calendar.monthrange(year, month)[1]:
                day = 1
                month += 1

                if month > 12:
                    month = 1
                    year += 1

        return datetime.datetime(year, month, day, int(hr), int(min), tzinfo=tz.tzutc())

    @staticmethod
    def _force_range(v, max):
        # force v to be >= 0 and < max
        if v < 0:
            return v + max
        elif v >= max:
            return v - max

        return v
