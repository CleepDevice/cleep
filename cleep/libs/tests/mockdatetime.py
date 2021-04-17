import datetime
import mock

# Allow to mock datetime object that is not mutable
# code from https://solidgeargroup.com/en/mocking-the-time/
#
# Usage:
# In your source code import base datetime package (not "from datetime import datetime")
# In your unit test code import mock_datetime from cleep and use with statement like this
#   utc_now = datetime.datetime(2020, 6, 8, 19, 50, 8, 0) # specify here date returned by mock
#   with mock_datetime(utc_now, datetime):
#     # perform your test here. now, today and utcnow will return your specified date

real_datetime_class = datetime.datetime

def mock_datetime(target, datetime_module):
    class DatetimeSubclassMeta(type):
        @classmethod
        def __instancecheck__(mcs, obj):
            return isinstance(obj, real_datetime_class)

    class BaseMockedDatetime(real_datetime_class):
        @classmethod
        def now(cls, tz=None):
            return target.replace(tzinfo=tz)

        @classmethod
        def utcnow(cls):
            import logging
            return target

        @classmethod
        def today(cls):
            return target

    # Python2 & Python3-compatible metaclass
    import logging
    MockedDatetime = DatetimeSubclassMeta('datetime', (BaseMockedDatetime,), {})

    return mock.patch.object(datetime_module, 'datetime', MockedDatetime)

