import os
import logging
import cleep.libs.internals.tools as tools

tools.install_trace_logging_level()


def get_log_level(default=logging.FATAL):
    """
    Return appropriate log level
    """
    if "DEBUG" in os.environ:
        return logging.DEBUG

    if "TRACE" in os.environ:
        return logging.TRACE

    if "LOGLEVEL" in os.environ:
        if os.environ["LOGLEVEL"].upper() == "TRACE":
            return logging.TRACE
        if os.environ["LOGLEVEL"].upper() == "DEBUG":
            return logging.DEBUG
        if os.environ["LOGLEVEL"].upper() == "INFO":
            return logging.INFO
        if os.environ["LOGLEVEL"].upper() == "WARN":
            return logging.WARN
        if os.environ["LOGLEVEL"].upper() == "ERROR":
            return logging.ERROR
        if os.environ["LOGLEVEL"].upper() == "FATAL":
            return logging.FATAL

    return default


class AnyArg(object):
    """
    Used to perform a "any" params comparison during an assert_called_with
    """

    def __eq__(a, b):
        return True


class PatternArg(object):
    """
    Used to perform a regexp param comparison during assert_called_with
    """

    def __init__(self, pattern):
        self.pattern = pattern

    def __eq__(self, b):
        return True if re.match(self.pattern, b) else False

    def __str__(self):
        return "ContainArg(%s)" % self.pattern
