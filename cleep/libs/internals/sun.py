#!/usr/bin/env python
# -*- coding: utf-8 -*-

import calendar
import math
import datetime
import logging
from dateutil import tz


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
        sunrise = self._calc_sun_time(date, True)
        if sunrise is None:
            raise Exception(
                "The sun never rises on this location (on the specified date)"
            )
        return sunrise

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
        sunrise = self._calc_sun_time(date, True)
        if sunrise is None:
            raise Exception(
                "The sun never rises on this location (on the specified date)"
            )
        return sunrise.astimezone(local_time_zone)

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
        sunset = self._calc_sun_time(date, False)
        if sunset is None:
            raise Exception(
                "The sun never sets on this location (on the specified date)"
            )
        return sunset

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
        sunset = self._calc_sun_time(date, False)
        if sunset is None:
            raise Exception(
                "The sun never sets on this location (on the specified date)"
            )
        return sunset.astimezone(local_time_zone)

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

        to_rad = math.pi / 180.0

        # 1. first calculate the day of the year
        temp1 = math.floor(275 * month / 9)
        temp2 = math.floor((month + 9) / 12)
        temp3 = 1 + math.floor((year - 4 * math.floor(year / 4) + 2) / 3)
        day_of_year = temp1 - (temp2 * temp3) + day - 30

        # 2. convert the longitude to hour value and calculate an approximate time
        lng_hour = self.longitude / 15

        if is_rise_time:
            time = day_of_year + ((6 - lng_hour) / 24)
        else:  # sunset
            time = day_of_year + ((18 - lng_hour) / 24)

        # 3. calculate the Sun's mean anomaly
        mean = (0.9856 * time) - 3.289

        # 4. calculate the Sun's true longitude
        longitude = (
            mean
            + (1.916 * math.sin(to_rad * mean))
            + (0.020 * math.sin(to_rad * 2 * mean))
            + 282.634
        )
        longitude = self._force_range(longitude, 360)  # NOTE: longitude adjusted into the range [0,360)

        # 5a. calculate the Sun's right ascension
        right_ascension = (1 / to_rad) * math.atan(0.91764 * math.tan(to_rad * longitude))
        right_ascension = self._force_range(right_ascension, 360)  # NOTE: RA adjusted into the range [0,360)

        # 5b. right ascension value needs to be in the same quadrant as longitude
        longitude_quadrant = (math.floor(longitude / 90)) * 90
        right_ascension_quadrant = (math.floor(right_ascension / 90)) * 90
        right_ascension = right_ascension + (longitude_quadrant - right_ascension_quadrant)

        # 5c. right ascension value needs to be converted into hours
        right_ascension = right_ascension / 15

        # 6. calculate the Sun's declination
        sin_dec = 0.39782 * math.sin(to_rad * longitude)
        cos_dec = math.cos(math.asin(sin_dec))

        # 7a. calculate the Sun's local hour angle
        cos_h = (
            math.cos(to_rad * zenith) - (sin_dec * math.sin(to_rad * self.latitude))
        ) / (cos_dec * math.cos(to_rad * self.latitude))

        if cos_h > 1:
            return None  # The sun never rises on this location (on the specified date)
        if cos_h < -1:  # pragma: no cover - hard to test
            return None  # The sun never sets on this location (on the specified date)

        # 7b. finish calculating H and convert into hours
        if is_rise_time:
            hours = 360 - (1 / to_rad) * math.acos(cos_h)
        else:  # setting
            hours = (1 / to_rad) * math.acos(cos_h)
        hours = hours / 15

        # 8. calculate local mean time of rising/setting
        mean_time = hours + right_ascension - (0.06571 * time) - 6.622

        # 9. adjust back to UTC
        universal_time = mean_time - lng_hour
        universal_time = self._force_range(universal_time, 24)  # UTC time in decimal format (e.g. 23.23)

        # 10. Return
        hour = self._force_range(int(universal_time), 24)
        minute = round((universal_time - int(universal_time)) * 60, 0)
        if minute == 60:
            hour += 1
            minute = 0

        # 10. check corner case https://github.com/SatAgro/suntime/issues/1
        if hour == 24:
            hour = 0
            day += 1

            if day > calendar.monthrange(year, month)[1]:
                day = 1
                month += 1

                if month > 12:
                    month = 1
                    year += 1

        return datetime.datetime(year, month, day, int(hour), int(minute), tzinfo=tz.tzutc())

    @staticmethod
    def _force_range(value, maximum):
        # force value to be >= 0 and < maximum
        if value < 0:
            return value + maximum
        if value >= maximum:
            return value - maximum
        return value
