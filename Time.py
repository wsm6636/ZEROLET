""" 
Functions to define time values. The base time unit is 1us, but can be changed if needed. 
Source: https://github.com/boschresearch/ros2_response_time_analysis/blob/master/case_study/move_base.py
"""
import math

""" Base period of the time in us. """
timeBase = 1

def useconds(n):
    """ Time in micro seconds. """
    frac, i = math.modf(n / timeBase)
    assert frac == 0
    return int(i)

def mseconds(n):
    """ Time in milli seconds. """
    return useconds(1000 * n)

def seconds(n):
    """ Time in seconds. """
    return mseconds(1000 * n)

"""
Functions to print time values.
"""

def printTime(value):
    value_ms = value / (1000 / timeBase)
    return "%s ms" % (value_ms)
