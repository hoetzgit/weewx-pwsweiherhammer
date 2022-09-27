# -*- coding: utf-8 -*-
"""
xcumulative.py

A WeeWX XType to produce cumulative series data with user specified reset times.

This program is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation; either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

Version: 0.1.0                                          Date: ?? September 2022

Revision History
    ?? September 2022   v0.1.0
        - initial release
"""

# python imports
from __future__ import absolute_import
import datetime
import logging
import time

# WeeWX imports
import weewx
import weeutil.weeutil
import weewx.engine
import weewx.xtypes

log = logging.getLogger(__name__)

XCUM_VERSION = '0.1.0'


# ==============================================================================
#                              Class XCumulative
# ==============================================================================

class XCumulative(weewx.xtypes.XType):
    """XType to produce cumulative series data with user specified reset times."""

    def __init__(self):
        pass

    def get_series(self, obs_type, timespan, db_manager, aggregate_type=None,
                   aggregate_interval=None, **option_dict):
        """Obtain a cumulative series with a user specified reset time."""

        # initialise lists to hold the vectors that will make up our result
        start_vec = list()
        stop_vec = list()
        data_vec = list()

        # we only know how to handle the cumulative aggregate type, if we have
        # anything else raise an UnknownAggregation exception
        if aggregate_type != 'cumulative':
            # we don't know this aggregation type so raise an
            # UnknownAggregation exception
            raise weewx.UnknownAggregation
        else:
            # we've been asked for the cumulative aggregation type

            # first look at the reset option (if it exists) and obtain a list
            # of reset timestamps that will occur in our timespan of interest
            reset = self.parse_reset(option_dict.get('reset'), timespan)
            # our unit and unit group are None until we get some data
            unit, unit_group = None, None
            # initialise our running total
            total = 0
            # initialise our reset timestamp index
            reset_index = 0
            # iterate over the aggregate interval timespans in the overall
            # timespan of interest
            for span in weeutil.weeutil.intervalgen(timespan.start,
                                                    timespan.stop,
                                                    aggregate_interval):
                # Get the aggregate as a ValueTuple. We are interested in the
                # sum aggregate, we will do the cumulative part of the xtype
                # later
                agg_vt = weewx.xtypes.get_aggregate(obs_type, span, 'sum', db_manager)
                # if the aggregate is None then continue to the next span
                if agg_vt.value is None:
                    continue
                # check for unit group consistency
                if unit:
                    # we've seen a unit and unit group before but is this unit
                    # and unit group the same ? (it's OK if the unit is unknown,
                    # ie ==None)
                    if agg_vt.unit is not None and (unit != agg_vt.unit or unit_group != agg_vt.group):
                        # the unit group has changed, we cannot handle this so
                        # raise an exception
                        raise weewx.UnsupportedFeature("Cannot change unit groups "
                                                       "within an aggregation.")
                else:
                    # we haven't seen a unit and group yet so set them
                    unit, unit_group = agg_vt.unit, agg_vt.group
                # append the start and stop timestamps of the current span to
                # our vectors
                start_vec.append(span.start)
                stop_vec.append(span.stop)
                # do we need to reset the running total?
                if reset is not None and len(reset) > reset_index:
                    # perhaps, but it depends...
                    if span.stop == reset[reset_index]:
                        # Our stop timestamp falls on the current reset
                        # timestamp so reset the running total. This means we
                        # effectively discard the current aggregate value.
                        total = 0.0
                        # since we encountered a reset timestamp increment the
                        # reset index
                        reset_index += 1
                    elif span.stop > reset[reset_index]:
                        # Our stop timestamp is after the current reset
                        # timestamp, so reset the running total to the current
                        # aggregate value.
                        total = agg_vt.value
                        # since we encountered a reset timestamp increment the
                        # reset index
                        reset_index += 1
                    elif agg_vt.value is not None:
                        # we haven't encountered a reset time so just add the
                        # current aggregate to the running total, no need for
                        # any resets
                        total += agg_vt.value
                else:
                    # we have no reset timestamps, so just add the current
                    # aggregate to the running total
                    total += agg_vt.value
                # append the total to our data vector
                data_vec.append(total)
        # convert our result vectors to ValueTuples and return the ValueTuples
        # as a tuple
        return (weewx.units.ValueTuple(start_vec, 'unix_epoch', 'group_time'),
                weewx.units.ValueTuple(stop_vec, 'unix_epoch', 'group_time'),
                weewx.units.ValueTuple(data_vec, unit, unit_group))

    def parse_reset(self, reset_opt, timespan):
        """Parse a reset option setting.

        We could have a reset option in any of the following:
        - HH:MM - reset occurs at HH:MM daily
        - ddTHH:MM - reset occurs at HH:MM on the dd day of each month
        - mm-ddTHH:MM - reset occurs ate HH:MM on dd-mm of each year
        - YYYY-mm-ddTHH:MM - reset occurs at HH:MM on YYYY-mm-dd

        Defaults and handling of invalid formats:
        - if an invalid time or time format is specified midnight is used as
          the time component of the reset option
        - if an invalid date format is used (eg, 21 December 2021) the date
          component of the reset option is ignored
        - if an invalid date is specified  (eg, 42 or 31 April) then reset
          occurs at midnight at the end of the month concerned
        """

        if reset_opt is None:
            # we have no reset option setting so return None
            return None
        else:
            # first split on 'T'
            _split = reset_opt.split('T')
            if len(_split) == 1:
                # we have no 'T', so assume we have a time in the format HH:MM
                try:
                    _dt = datetime.datetime.strptime(_split[0], '%H:%M')
                except ValueError:
                    # could not convert specified time so log it and default
                    # to 00:00
                    if weewx.debug >= 2:
                        log.debug("Cannot parse reset option '%s', "
                                  "using '00:00' daily" % (reset_opt, ))
                    _split[0] = '00:00'
                # create a dict to hold the date and time components of the
                # reset option
                dt_params = dict()
                # obtain the hour and minute components, first split on ':'
                _split_time = _split[0].split(':')
                # obtain and add the hour and minute components to our dict
                dt_params['hour'] = int(_split_time[0])
                dt_params['minute'] = int(_split_time[1])
                # obtain the list of reset timestamps for the timespan of
                # interest
                reset_list = self.get_ts_list(timespan, **dt_params)
            elif len(_split) == 2:
                # we have a 'T', so we need to look for date and time
                # components
                # create a dict to hold the date and time components of the
                # reset option
                dt_params = dict()
                # first look at the time
                try:
                    _dt = datetime.datetime.strptime(_split[1], '%H:%M')
                except ValueError:
                    # could not convert the specified time so log it and
                    # default to 00:00
                    if weewx.debug >= 2:
                        log.debug("Cannot parse time in reset option '%s', "
                                  "using '00:00'" % (reset_opt, ))
                    _split[1] = '00:00'
                else:
                    # we have a valid time, so split on ':' to obtain the hour
                    # and minute components
                    _split_time = _split[1].split(':')
                    # obtain and add the hour and minute components to our dict
                    dt_params['hour'] = int(_split_time[0])
                    dt_params['minute'] = int(_split_time[1])
                # Now look at the date. We only accept a limited number of date
                # formats so iterate over the acceptable date formats looking
                # for a match
                for date_fmt in ('%d', '%m-%d', '%Y-%m-%d'):
                    # does the date format match, a ValueError will indicate it
                    # does not
                    try:
                        _date_dt = datetime.datetime.strptime(_split[0], date_fmt)
                    except ValueError:
                        # We could not parse the date string using the current
                        # format, so pass and try the next format. A check
                        # later will pick up the case where none of the formats
                        # were successful.
                        pass
                    else:
                        # add the day of the month to our dict
                        dt_params['day'] = _date_dt.timetuple().tm_mday
                        # if we have a month add it to our dict
                        if '%m' in date_fmt:
                            dt_params['month'] = _date_dt.timetuple().tm_mon
                        # if we have a year add it to our dict
                        if '%Y' in date_fmt:
                            dt_params['year'] = _date_dt.timetuple().tm_year
                        # since we have a match we can exit the for loop
                        continue
                    finally:
                        # now we can produce the reset timestamp list
                        reset_list = self.get_ts_list(timespan, **dt_params)
                        # even though we may have already finished parsing the
                        # date-time string, check if we successfully parsed the
                        # date string, we could have arrived here having found
                        # no date format match
                        if 'day' not in dt_params:
                            # we could not parse the date string, so log it
                            if weewx.debug >= 2:
                                log.debug("Cannot parse date in reset "
                                          "option '%s'" % (reset_opt,))
            else:
                # we have a reset option we cannot parse
                _msg = "Cannot parse reset option '%s'"
                raise weewx.ViolatedPrecondition(_msg)
            return reset_list

    @staticmethod
    def get_ts_list(timespan, **dt_params):
        """Obtain a list of matching timestamps.

        Given a timespan and a dictionary of date-time parameters obtain a list
        of timestamps within the timespan that match the date-time parameters.
        If no matching timestamps are found return an empty list.
        """

        ts_list = list()
        # iterate over each day in the timespan of concern
        for day_span in weeutil.weeutil.genDaySpans(timespan.start, timespan.stop):
            # obtain a datetime object based on the timestamp for the start of
            # day
            _dt = datetime.datetime.fromtimestamp(day_span.start)
            # Using the start of day datetime object update that object with
            # the date-time parameters for matching date-times. The resulting
            # date time object may fall within or without the current day.
            _day_reset_dt = _dt.replace(**dt_params)
            # convert the modified datetime object to a timestamp
            _day_reset_ts = time.mktime(_day_reset_dt.timetuple())
            # we are only interested in the resulting timestamp if it falls
            # somewhere within the current day
            if day_span.start <= _day_reset_ts < day_span.stop:
                # the timestamp does fall within the current day, so add it to
                # the list of matching timestamps
                ts_list.append(_day_reset_ts)
        # return the list of matching timestamps
        return ts_list


# ==============================================================================
#                           Class StdCumulativeType
# ==============================================================================

class StdCumulativeType(weewx.engine.StdService):
    """Instantiate and register the XCumulative XType."""

    def __init__(self, engine, config_dict):
        super(StdCumulativeType, self).__init__(engine, config_dict)

        # obtain an XCumulative XType object
        self.xcumulative = XCumulative()
        # Add the XCumulative XType object to the front of the WeeWX XType
        # list. This is necessary so that the XCumulative XType is chosen in
        # preference to any other XTypes when a cumulative series aggregate is
        # being sought.
        weewx.xtypes.xtypes.insert(0, self.xcumulative)

    def shutDown(self):

        # remove the XCumulative XType from the list of XTypes
        weewx.xtypes.xtypes.remove(self.xcumulative)
