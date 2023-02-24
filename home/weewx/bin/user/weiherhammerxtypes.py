"""
    Copyright (C) 2022 Henry Ott

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
# python imports
import time

# WeeWX imports
import weewx
import weewx.units
import weewx.xtypes
import weeutil.config
from weewx.engine import StdService
from weeutil.weeutil import to_int, to_float, to_bool
from weewx.units import ValueTuple, CtoK, CtoF, FtoC, mph_to_knot, kph_to_knot, mps_to_knot

# user imports
import user.weiherhammerformulas
# external Routines
# Source: https://github.com/smartlixx/WetBulb
import user.external.WetBulb
# Source: https://github.com/hoetzgit/weatherlink-python/blob/master/weatherlink/utils.py
import user.external.weatherlink

try:
    # Test for new-style weewx logging by trying to import weeutil.logger
    import weeutil.logger
    import logging
    log = logging.getLogger(__name__)

    def logdbg(msg):
        log.debug(msg)

    def loginf(msg):
        log.info(msg)

    def logerr(msg):
        log.error(msg)

except ImportError:
    # Old-style weewx logging
    import syslog

    def logmsg(level, msg):
        syslog.syslog(level, 'weiherhammerxtypes: %s' % msg)

    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)

DEFAULTS_INI = """
[WeiherhammerWXCalculate]
    [[WXXTypes]]
        [[[solar_heatindex]]]
            algorithm = new
        [[[sunshineThreshold]]]
            debug = 0
            [[[[coeff]]]]
                1 = 1.0
                2 = 1.0
                3 = 1.0
                4 = 1.0
                5 = 1.0
                6 = 1.0
                7 = 1.0
                8 = 1.0
                9 = 1.0
                10 = 1.0
                11 = 1.0
                12 = 1.0
        [[[sunshine]]]
            debug = 0
            radiation_min = 0.0
            threshold_min = 0.0
            # valid values radiation or threshold
            evaluate_min = radiation
    [[PressureCooker]]
        max_delta_12h = 1800
        [[[altimeter]]]
            algorithm = aaASOS    # Case-sensitive!
"""
defaults_dict = weeutil.config.config_from_str(DEFAULTS_INI)

# unit system new observations
weewx.units.obs_group_dict['thswIndex'] = "group_temperature"
weewx.units.obs_group_dict['thwIndex'] = "group_temperature"
weewx.units.obs_group_dict['wetBulb'] = "group_temperature"
weewx.units.obs_group_dict['sunshine'] = "group_count"
weewx.units.obs_group_dict['sunshineRadiationMin'] = "group_radiation"
weewx.units.obs_group_dict['sunshineThreshold'] = "group_radiation"
weewx.units.obs_group_dict['sunshineThresholdMin'] = "group_radiation"
# battery status
weewx.units.obs_group_dict['wh31_ch1_batt_percent'] = "group_percent"
weewx.units.obs_group_dict['wh31_ch2_batt_percent'] = "group_percent"
weewx.units.obs_group_dict['wh31_ch3_batt_percent'] = "group_percent"
weewx.units.obs_group_dict['wh51_ch1_batt_percent'] = "group_percent"
weewx.units.obs_group_dict['wh65_batt_percent'] = "group_percent"
weewx.units.obs_group_dict['wh57_batt_percent'] = "group_percent"
# solar station
weewx.units.obs_group_dict['solar_altimeter'] = "group_pressure"
weewx.units.obs_group_dict['solar_appTemp'] = "group_temperature"
weewx.units.obs_group_dict['solar_barometer'] = "group_pressure"
weewx.units.obs_group_dict['solar_batt_percent'] = "group_percent"
weewx.units.obs_group_dict['solar_dewpoint'] = "group_temperature"
weewx.units.obs_group_dict['solar_heatindex'] = "group_temperature"
weewx.units.obs_group_dict['solar_humidex'] = "group_temperature"
weewx.units.obs_group_dict['solar_pressure'] = "group_pressure"
weewx.units.obs_group_dict['solar_thswIndex'] = "group_temperature"
weewx.units.obs_group_dict['solar_thwIndex'] = "group_temperature"
weewx.units.obs_group_dict['solar_wetBulb'] = "group_temperature"
weewx.units.obs_group_dict['solar_windchill'] = "group_temperature"
# AllSky camera
weewx.units.obs_group_dict['asky_box_altimeter'] = 'group_pressure'
weewx.units.obs_group_dict['asky_box_barometer'] = 'group_pressure'
weewx.units.obs_group_dict['asky_box_dewpoint'] = "group_temperature"
weewx.units.obs_group_dict['asky_box_pressure'] = 'group_pressure'
weewx.units.obs_group_dict['asky_dome_dewpoint'] = 'group_temperature'
#
# Tests
weewx.units.obs_group_dict['thswIndex2'] = "group_temperature"
weewx.units.obs_group_dict['thwIndex2'] = "group_temperature"
weewx.units.obs_group_dict['wetBulb2'] = "group_temperature"
weewx.units.obs_group_dict['solar_thswIndex2'] = "group_temperature"
weewx.units.obs_group_dict['solar_thwIndex2'] = "group_temperature"
weewx.units.obs_group_dict['solar_wetBulb2'] = "group_temperature"


VERSION = '0.4'

class WXXTypes(weewx.xtypes.XType):
    """Weiherhammer weather extensions to the WeeWX xtype system"""

    def __init__(self, altitude, latitude, longitude,
                 sunshineThreshold_debug,
                 sunshineThreshold_coeff_dict,
                 sunshine_debug,
                 sunshine_radiation_min,
                 sunshine_threshold_min,
                 sunshine_evaluate_min,
                 solar_heatindex_algo
                 ):
        self.alt = altitude
        self.lat = latitude
        self.lon = longitude
        self.solar_heatindex_algo = solar_heatindex_algo.lower()
        self.sunshineThreshold_debug = to_int(sunshineThreshold_debug)
        self.sunshineThreshold_coeff_dict = sunshineThreshold_coeff_dict
        self.sunshine_debug = to_int(sunshine_debug)
        self.sunshine_radiation_min = to_float(sunshine_radiation_min)
        self.sunshine_threshold_min = to_float(sunshine_threshold_min)
        self.sunshine_evaluate_min = sunshine_evaluate_min.lower()

        if self.sunshineThreshold_debug > 0:
            logdbg("sunshineThreshold, monthly coeff is %s" % str(self.sunshineThreshold_coeff_dict))
        if self.sunshine_debug > 0:
            logdbg("sunshine, radiation_min is %.2f" % self.sunshine_radiation_min)
            logdbg("sunshine, threshold_min is %.2f" % self.sunshine_threshold_min)
            logdbg("sunshine, evaluate_min is '%s'" % self.sunshine_evaluate_min)

    def get_scalar(self, obs_type, record, db_manager, **option_dict):
        """Invoke the proper method for the desired observation type."""
        try:
            # Form the method name, then call it with arguments
            return getattr(self, 'calc_%s' % obs_type)(obs_type, record, db_manager)
        except AttributeError:
            raise weewx.UnknownType(obs_type)

    @staticmethod
    def calc_wetBulb(key, data, db_manager=None):
        if 'outTemp' not in data or 'outHumidity' not in data or 'pressure' not in data:
            raise weewx.CannotCalculate(key)

        if data['usUnits'] == weewx.US:
            val = user.weiherhammerformulas.wetbulbF(data['outTemp'], data['outHumidity'], data['pressure'])
            u = 'degree_F'
        else:
            val = user.weiherhammerformulas.wetbulbC(data['outTemp'], data['outHumidity'], data['pressure'])
            u = 'degree_C'
        return ValueTuple(val, u, 'group_temperature')

    @staticmethod
    def calc_solar_wetBulb(key, data, db_manager=None):
        if 'solar_outTemp' not in data or 'solar_outHumidity' not in data or 'solar_pressure' not in data:
            raise weewx.CannotCalculate(key)

        if data['usUnits'] == weewx.US:
            val = user.weiherhammerformulas.wetbulbF(data['solar_outTemp'], data['solar_outHumidity'], data['solar_pressure'])
            u = 'degree_F'
        else:
            val = user.weiherhammerformulas.wetbulbC(data['solar_outTemp'], data['solar_outHumidity'], data['solar_pressure'])
            u = 'degree_C'
        return ValueTuple(val, u, 'group_temperature')

    def calc_solar_heatindex(self, key, data, db_manager=None):
        if 'solar_outTemp' not in data or 'solar_outHumidity' not in data:
            raise weewx.CannotCalculate(key)
        if data['usUnits'] == weewx.US:
            val = weewx.wxformulas.heatindexF(data['solar_outTemp'], data['solar_outHumidity'],
                                              algorithm=self.solar_heatindex_algo)
            u = 'degree_F'
        else:
            val = weewx.wxformulas.heatindexC(data['solar_outTemp'], data['solar_outHumidity'],
                                              algorithm=self.solar_heatindex_algo)
            u = 'degree_C'
        return ValueTuple(val, u, 'group_temperature')

    @staticmethod
    def calc_solar_dewpoint(key, data, db_manager=None):
        if 'solar_outTemp' not in data or 'solar_outHumidity' not in data:
            raise weewx.CannotCalculate(key)
        if data['usUnits'] == weewx.US:
            val = weewx.wxformulas.dewpointF(data['solar_outTemp'], data['solar_outHumidity'])
            u = 'degree_F'
        else:
            val = weewx.wxformulas.dewpointC(data['solar_outTemp'], data['solar_outHumidity'])
            u = 'degree_C'
        return ValueTuple(val, u, 'group_temperature')

    @staticmethod
    def calc_asky_dome_dewpoint(key, data, db_manager=None):
        if 'asky_dome_temperature' not in data or 'asky_box_humidity' not in data:
            raise weewx.CannotCalculate(key)
        if data['usUnits'] == weewx.US:
            val = weewx.wxformulas.dewpointF(data['asky_dome_temperature'], data['asky_box_humidity'])
            u = 'degree_F'
        else:
            val = weewx.wxformulas.dewpointC(data['asky_dome_temperature'], data['asky_box_humidity'])
            u = 'degree_C'
        return ValueTuple(val, u, 'group_temperature')

    @staticmethod
    def calc_asky_box_dewpoint(key, data, db_manager=None):
        if 'asky_box_temperature' not in data or 'asky_box_humidity' not in data:
            raise weewx.CannotCalculate(key)
        if data['usUnits'] == weewx.US:
            val = weewx.wxformulas.dewpointF(data['asky_box_temperature'], data['asky_box_humidity'])
            u = 'degree_F'
        else:
            val = weewx.wxformulas.dewpointC(data['asky_box_temperature'], data['asky_box_humidity'])
            u = 'degree_C'
        return ValueTuple(val, u, 'group_temperature')

    @staticmethod
    def calc_solar_windchill(key, data, db_manager=None):
        if 'solar_outTemp' not in data or 'windSpeed' not in data:
            raise weewx.CannotCalculate(key)
        if data['usUnits'] == weewx.US:
            val = weewx.wxformulas.windchillF(data['solar_outTemp'], data['windSpeed'])
            u = 'degree_F'
        elif data['usUnits'] == weewx.METRIC:
            val = weewx.wxformulas.windchillMetric(data['solar_outTemp'], data['windSpeed'])
            u = 'degree_C'
        elif data['usUnits'] == weewx.METRICWX:
            val = weewx.wxformulas.windchillMetricWX(data['solar_outTemp'], data['windSpeed'])
            u = 'degree_C'
        else:
            raise weewx.ViolatedPrecondition("Unknown unit system %s" % data['usUnits'])
        return ValueTuple(val, u, 'group_temperature')

    @staticmethod
    def calc_solar_humidex(key, data, db_manager=None):
        if 'solar_outTemp' not in data or 'solar_outHumidity' not in data:
            raise weewx.CannotCalculate(key)
        if data['usUnits'] == weewx.US:
            val = weewx.wxformulas.humidexF(data['solar_outTemp'], data['solar_outHumidity'])
            u = 'degree_F'
        else:
            val = weewx.wxformulas.humidexC(data['solar_outTemp'], data['solar_outHumidity'])
            u = 'degree_C'
        return ValueTuple(val, u, 'group_temperature')

    @staticmethod
    def calc_solar_appTemp(key, data, db_manager=None):
        if 'solar_outTemp' not in data or 'solar_outHumidity' not in data or 'windSpeed' not in data:
            raise weewx.CannotCalculate(key)
        if data['usUnits'] == weewx.US:
            val = weewx.wxformulas.apptempF(data['solar_outTemp'], data['solar_outHumidity'],
                                            data['windSpeed'])
            u = 'degree_F'
        else:
            # The metric equivalent needs wind speed in mps. Convert.
            windspeed_vt = weewx.units.as_value_tuple(data, 'windSpeed')
            windspeed_mps = weewx.units.convert(windspeed_vt, 'meter_per_second')[0]
            val = weewx.wxformulas.apptempC(data['solar_outTemp'], data['solar_outHumidity'], windspeed_mps)
            u = 'degree_C'
        return ValueTuple(val, u, 'group_temperature')

    @staticmethod
    def calc_thwIndex(key, data, db_manager=None):
        if 'outTemp' not in data or 'outHumidity' not in data or 'windSpeed' not in data:
            raise weewx.CannotCalculate(key)

        if data['usUnits'] == weewx.US:
            val = user.weiherhammerformulas.thwIndexF(data['outTemp'], data['outHumidity'], data['windSpeed'])
            u = 'degree_F'
        else:
            val = user.weiherhammerformulas.thwIndexC(data['outTemp'], data['outHumidity'], data['windSpeed'])
            u = 'degree_C'
        return ValueTuple(val, u, 'group_temperature')

    @staticmethod
    def calc_solar_thwIndex(key, data, db_manager=None):
        if 'solar_outTemp' not in data or 'solar_outHumidity' not in data or 'windSpeed' not in data:
            raise weewx.CannotCalculate(key)

        if data['usUnits'] == weewx.US:
            val = user.weiherhammerformulas.thwIndexF(data['solar_outTemp'], data['solar_outHumidity'], data['windSpeed'])
            u = 'degree_F'
        else:
            val = user.weiherhammerformulas.thwIndexC(data['solar_outTemp'], data['solar_outHumidity'], data['windSpeed'])
            u = 'degree_C'
        return ValueTuple(val, u, 'group_temperature')

    @staticmethod
    def calc_thswIndex(key, data, db_manager=None):
        if 'outTemp' not in data or 'outHumidity' not in data or 'windSpeed' not in data or 'radiation' not in data:
            raise weewx.CannotCalculate(key)

        if data['usUnits'] == weewx.US:
            val = user.weiherhammerformulas.thswIndexF(data['outTemp'], data['outHumidity'], data['windSpeed'], data['radiation'])
            u = 'degree_F'
        else:
            val = user.weiherhammerformulas.thswIndexC(data['outTemp'], data['outHumidity'], data['windSpeed'], data['radiation'])
            u = 'degree_C'
        return ValueTuple(val, u, 'group_temperature')

    @staticmethod
    def calc_solar_thswIndex(key, data, db_manager=None):
        if 'solar_outTemp' not in data or 'outHumidity' not in data or 'windSpeed' not in data or 'radiation' not in data:
            raise weewx.CannotCalculate(key)

        if data['usUnits'] == weewx.US:
            val = user.weiherhammerformulas.thswIndexF(data['solar_outTemp'], data['solar_outHumidity'], data['windSpeed'], data['radiation'])
            u = 'degree_F'
        else:
            val = user.weiherhammerformulas.thswIndexC(data['solar_outTemp'], data['solar_outHumidity'], data['windSpeed'], data['radiation'])
            u = 'degree_C'
        return ValueTuple(val, u, 'group_temperature')

    def calc_sunshineThreshold(self, key, data, db_manager=None):
        # TypeError: argument of type 'NoneType' is not iterable
        if data is None:
            raise weewx.CannotCalculate(key)
        if 'dateTime' not in data:
            raise weewx.CannotCalculate(key)
        monthofyear = to_int(time.strftime("%m",time.gmtime(data['dateTime'])))
        coeff = to_float(self.sunshineThreshold_coeff_dict.get(str(monthofyear)))
        if coeff is None:
            coeff = to_float(defaults_dict.get(str(monthofyear), 1.0))
            logerr("sunshineThreshold, user configured coeff month=%d is not valid! Using default coeff instead." % (monthofyear))
        if self.sunshineThreshold_debug >= 3:
            logdbg("sunshineThreshold, month=%d coeff=%.2f" % (monthofyear, coeff)) 
        threshold = user.weiherhammerformulas.sunshineThreshold(data['dateTime'], self.lat, self.lon, coeff)
        if self.sunshineThreshold_debug >= 2:
            logdbg("sunshineThreshold, threshold=%.2f" % threshold)
        return ValueTuple(threshold, 'watt_per_meter_squared', 'group_radiation')

    def calc_sunshineRadiationMin(self, key, data, db_manager=None):
        return ValueTuple(self.sunshine_radiation_min, 'watt_per_meter_squared', 'group_radiation')

    def calc_sunshineThresholdMin(self, key, data, db_manager=None):
        return ValueTuple(self.sunshine_threshold_min, 'watt_per_meter_squared', 'group_radiation')

    def calc_sunshine(self, key, data, db_manager=None):
        if 'radiation' not in data or 'dateTime' not in data:
            raise weewx.CannotCalculate(key)
        sunshine = threshold = None
        if data['radiation'] is not None:
            sunshine = 0
            monthofyear = to_int(time.strftime("%m",time.gmtime(data['dateTime'])))
            coeff = to_float(self.sunshineThreshold_coeff_dict.get(str(monthofyear)))
            if coeff is None:
                coeff = 1.0
                logerr("sunshine, user configured coeff month=%d is not valid! Using default coeff=1.0 instead." % (monthofyear))
            if self.sunshine_debug >= 3:
                logdbg("sunshine, month=%d coeff=%.2f" % (monthofyear, coeff)) 
            threshold = user.weiherhammerformulas.sunshineThreshold(data['dateTime'], self.lat, self.lon, coeff)

            if self.sunshine_evaluate_min == 'radiation':
                if data['radiation'] >= self.sunshine_radiation_min:
                    if threshold > 0.0 and data['radiation'] > threshold:
                        sunshine = 1
                elif self.sunshine_debug >= 2:
                    logdbg("sunshine, radiation=%.2f lower than radiation_min=%.2f" % (data['radiation'], self.sunshine_radiation_min))
            elif self.sunshine_evaluate_min == 'threshold':
                if threshold >= self.sunshine_threshold_min:
                    if threshold > 0.0 and data['radiation'] > threshold:
                        sunshine = 1
                elif self.sunshine_debug >= 2:
                    logdbg("sunshine, threshold=%.2f lower than threshold_min=%.2f" % (threshold, self.sunshine_threshold_min))

        elif self.sunshine_debug >= 3:
            logdbg("sunshine, radiation is None")
        if self.sunshine_debug >= 2:
            logdbg("sunshine, sunshine=%s radiation=%s threshold=%s" % (
                str(sunshine) if sunshine is not None else 'None',
                str(data['radiation']) if data['radiation'] is not None else 'None',
                str(threshold) if threshold is not None else 'None'))
        return ValueTuple(sunshine, 'count', 'group_count')

    @staticmethod
    def calc_solar_batt_percent(key, data, db_manager=None):
        if 'solar_batt' not in data or data['solar_batt'] is None:
            raise weewx.CannotCalculate(key)
        # 3.8V = 0%, 4.2V = 100%
        val = user.weiherhammerformulas.batt_to_percent(data['solar_batt'], 3.8, 4.2)
        return ValueTuple(val, 'percent', 'group_percent')

    @staticmethod
    def calc_wh31_ch1_batt_percent(key, data, db_manager=None):
        if 'wh31_ch1_batt' not in data or data['wh31_ch1_batt'] is None:
            raise weewx.CannotCalculate(key)
        # 0 = high = 100%, 1 = low = 50%
        val = user.weiherhammerformulas.wh31_batt_to_percent(data['wh31_ch1_batt'])
        return ValueTuple(val, 'percent', 'group_percent')

    @staticmethod
    def calc_wh31_ch2_batt_percent(key, data, db_manager=None):
        if 'wh31_ch2_batt' not in data or data['wh31_ch2_batt'] is None:
            raise weewx.CannotCalculate(key)
        # 0 = high = 100%, 1 = low = 50%
        val = user.weiherhammerformulas.wh31_batt_to_percent(data['wh31_ch2_batt'])
        return ValueTuple(val, 'percent', 'group_percent')

    @staticmethod
    def calc_wh31_ch3_batt_percent(key, data, db_manager=None):
        if 'wh31_ch3_batt' not in data or data['wh31_ch3_batt'] is None:
            raise weewx.CannotCalculate(key)
        # 0 = high = 100%, 1 = low = 50%
        val = user.weiherhammerformulas.wh31_batt_to_percent(data['wh31_ch3_batt'])
        return ValueTuple(val, 'percent', 'group_percent')

    @staticmethod
    def calc_wh51_ch1_batt_percent(key, data, db_manager=None):
        if 'wh51_ch1_batt' not in data or data['wh51_ch1_batt'] is None:
            raise weewx.CannotCalculate(key)
        # 1.0V = 0%, 1.8V = 100%
        val = user.weiherhammerformulas.batt_to_percent(data['wh51_ch1_batt'], 1.0, 1.8)
        return ValueTuple(val, 'percent', 'group_percent')

    @staticmethod
    def calc_wh57_batt_percent(key, data, db_manager=None):
        if 'wh57_batt' not in data or data['wh57_batt'] is None:
            raise weewx.CannotCalculate(key)
        val = user.weiherhammerformulas.batt_to_percent(data['wh57_batt'], 0, 5)
        return ValueTuple(val, 'percent', 'group_percent')

    @staticmethod
    def calc_wh65_batt_percent(key, data, db_manager=None):
        if 'wh65_batt' not in data or data['wh65_batt'] is None:
            raise weewx.CannotCalculate(key)
        # 0 = high = 100%, 1 = low = 50%
        val = user.weiherhammerformulas.wh65_batt_to_percent(data['wh65_batt'])
        return ValueTuple(val, 'percent', 'group_percent')

#
# ######################## Class PressureCooker ##############################
#

class PressureCooker(weewx.xtypes.XType):
    """Pressure related extensions to the WeeWX type system. """

    def __init__(self, altitude_vt,
                 max_delta_12h=1800,
                 altimeter_algorithm='aaASOS'):

        # Algorithms can be abbreviated without the prefix 'aa':
        if not altimeter_algorithm.startswith('aa'):
            altimeter_algorithm = 'aa%s' % altimeter_algorithm

        self.altitude_vt = altitude_vt
        self.max_delta_12h = max_delta_12h
        self.altimeter_algorithm = altimeter_algorithm

        # Timestamp (roughly) 12 hours ago
        self.ts_12h = None
        # AllSky Box Temperature 12 hours ago as a ValueTuple
        self.asky_box_temp_12h_vt = None
        # Solar Station Temperature 12 hours ago as a ValueTuple
        self.solar_temp_12h_vt = None

    def _get_asky_box_temp_12h(self, ts, dbmanager):
        """Get the temperature as a ValueTuple from 12 hours ago.  The value will
         be None if no temperature is available.
         """

        ts_12h = ts - 12 * 3600

        # Look up the temperature 12h ago if this is the first time through,
        # or we don't have a usable temperature, or the old temperature is too stale.
        if self.ts_12h is None \
                or self.asky_box_temp_12h_vt is None \
                or abs(self.ts_12h - ts_12h) < self.max_delta_12h:
            # Hit the database to get a newer temperature.
            record = dbmanager.getRecord(ts_12h, max_delta=self.max_delta_12h)
            if record and 'outTemp' in record:
                # Figure out what unit the record is in ...
                unit = weewx.units.getStandardUnitType(record['usUnits'], 'outTemp')
                # ... then form a ValueTuple.
                self.asky_box_temp_12h_vt = weewx.units.ValueTuple(record['outTemp'], *unit)
            else:
                # Invalidate the temperature ValueTuple from 12h ago
                self.asky_box_temp_12h_vt = None
            # Save the timestamp
            self.ts_12h = ts_12h

        return self.asky_box_temp_12h_vt

    def _get_solar_temp_12h(self, ts, dbmanager):
        """Get the temperature as a ValueTuple from 12 hours ago.  The value will
         be None if no temperature is available.
         """

        ts_12h = ts - 12 * 3600

        # Look up the temperature 12h ago if this is the first time through,
        # or we don't have a usable temperature, or the old temperature is too stale.
        if self.ts_12h is None \
                or self.solar_temp_12h_vt is None \
                or abs(self.ts_12h - ts_12h) < self.max_delta_12h:
            # Hit the database to get a newer temperature.
            record = dbmanager.getRecord(ts_12h, max_delta=self.max_delta_12h)
            if record and 'outTemp' in record:
                # Figure out what unit the record is in ...
                unit = weewx.units.getStandardUnitType(record['usUnits'], 'outTemp')
                # ... then form a ValueTuple.
                self.solar_temp_12h_vt = weewx.units.ValueTuple(record['outTemp'], *unit)
            else:
                # Invalidate the temperature ValueTuple from 12h ago
                self.solar_temp_12h_vt = None
            # Save the timestamp
            self.ts_12h = ts_12h

        return self.solar_temp_12h_vt

    def get_scalar(self, key, record, dbmanager, **option_dict):
        if key == 'asky_box_pressure' or key == 'solar_pressure':
            return self.pressure(record, dbmanager, key)
        elif key == 'asky_box_altimeter' or key == 'solar_altimeter':
            return self.altimeter(record, key)
        elif key == 'asky_box_barometer' or key == 'solar_barometer':
            return self.barometer(record, key)
        else:
            raise weewx.UnknownType(key)

    def pressure(self, record, dbmanager, obs):
        """Calculate the observation type 'xxx_pressure'."""

        # All of the following keys are required:
        if obs == 'asky_box_pressure':
            if any(key not in record for key in ['usUnits', 'asky_box_temperature', 'asky_box_barometer', 'asky_box_humidity']):
                raise weewx.CannotCalculate(obs)
        elif obs == 'solar_pressure':
            if any(key not in record for key in ['usUnits', 'solar_outTemp', 'solar_barometer', 'solar_outHumidity']):
                raise weewx.CannotCalculate(obs)

        # Get the temperature in Fahrenheit from 12 hours ago
        if obs == 'asky_box_pressure':
            temp_12h_vt = self._get_asky_box_temp_12h(record['dateTime'], dbmanager)
            if temp_12h_vt is None \
                    or temp_12h_vt[0] is None \
                    or record['asky_box_temperature'] is None \
                    or record['asky_box_barometer'] is None \
                    or record['asky_box_humidity'] is None:
                pressure = None
            else:
                # The following requires everything to be in US Customary units.
                # Rather than convert the whole record, just convert what we need:
                record_US = weewx.units.to_US({'usUnits': record['usUnits'],
                                               'asky_box_temperature': record['asky_box_temperature'],
                                               'asky_box_barometer': record['asky_box_barometer'],
                                               'asky_box_humidity': record['asky_box_humidity']})
                # Get the altitude in feet
                altitude_ft = weewx.units.convert(self.altitude_vt, "foot")
                # The outside temperature in F.
                temp_12h_F = weewx.units.convert(temp_12h_vt, "degree_F")
                pressure = weewx.uwxutils.uWxUtilsVP.SeaLevelToSensorPressure_12(
                    record_US['asky_box_barometer'],
                    altitude_ft[0],
                    record_US['asky_box_temperature'],
                    temp_12h_F[0],
                    record_US['asky_box_humidity']
                )
        elif obs == 'solar_pressure':
            temp_12h_vt = self._get_solar_temp_12h(record['dateTime'], dbmanager)
            if temp_12h_vt is None \
                    or temp_12h_vt[0] is None \
                    or record['solar_outTemp'] is None \
                    or record['solar_barometer'] is None \
                    or record['solar_outHumidity'] is None:
                pressure = None
            else:
                # The following requires everything to be in US Customary units.
                # Rather than convert the whole record, just convert what we need:
                record_US = weewx.units.to_US({'usUnits': record['usUnits'],
                                               'solar_outTemp': record['solar_outTemp'],
                                               'solar_barometer': record['solar_barometer'],
                                               'solar_outHumidity': record['solar_outHumidity']})
                # Get the altitude in feet
                altitude_ft = weewx.units.convert(self.altitude_vt, "foot")
                # The outside temperature in F.
                temp_12h_F = weewx.units.convert(temp_12h_vt, "degree_F")
                pressure = weewx.uwxutils.uWxUtilsVP.SeaLevelToSensorPressure_12(
                    record_US['solar_barometer'],
                    altitude_ft[0],
                    record_US['solar_outTemp'],
                    temp_12h_F[0],
                    record_US['solar_outHumidity']
                )

        return ValueTuple(pressure, 'inHg', 'group_pressure')

    def altimeter(self, record, obs):
        """Calculate the observation type 'xxx_altimeter'."""
        if obs == 'asky_box_altimeter':
            if 'asky_box_pressure' not in record:
                raise weewx.CannotCalculate(obs)
        elif obs == 'solar_altimeter':
            if 'solar_pressure' not in record:
                raise weewx.CannotCalculate(obs)

        # Convert altitude to same unit system of the incoming record
        altitude = weewx.units.convertStd(self.altitude_vt, record['usUnits'])

        # Figure out which altimeter formula to use, and what unit the results will be in:
        if record['usUnits'] == weewx.US:
            formula = weewx.wxformulas.altimeter_pressure_US
            u = 'inHg'
        else:
            formula = weewx.wxformulas.altimeter_pressure_Metric
            u = 'mbar'
        # Apply the formula
        if obs == 'asky_box_altimeter':
            altimeter = formula(record['asky_box_pressure'], altitude[0], self.altimeter_algorithm)
        elif obs == 'solar_altimeter':
            altimeter = formula(record['solar_pressure'], altitude[0], self.altimeter_algorithm)

        return ValueTuple(altimeter, u, 'group_pressure')

    def barometer(self, record, obs):
        """Calculate the observation type 'xxx_barometer'"""
        if obs == 'asky_box_barometer':
            if 'asky_box_pressure' not in record or 'asky_box_temperature' not in record:
                raise weewx.CannotCalculate(obs)
        elif obs == 'solar_barometer':
            if 'solar_pressure' not in record or 'solar_outTemp' not in record:
                raise weewx.CannotCalculate(obs)

        # Convert altitude to same unit system of the incoming record
        altitude = weewx.units.convertStd(self.altitude_vt, record['usUnits'])

        # Figure out what barometer formula to use:
        if record['usUnits'] == weewx.US:
            formula = weewx.wxformulas.sealevel_pressure_US
            u = 'inHg'
        else:
            formula = weewx.wxformulas.sealevel_pressure_Metric
            u = 'mbar'
        # Apply the formula
        if obs == 'asky_box_barometer':
            barometer = formula(record['asky_box_pressure'], altitude[0], record['asky_box_temperature'])
        elif obs == 'solar_barometer':
            barometer = formula(record['solar_pressure'], altitude[0], record['solar_outTemp'])

        return ValueTuple(barometer, u, 'group_pressure')



class WeiherhammerXTypes(StdService):
    """Instantiate and register the Weiherhammer xtype extension WXXTypes."""

    def __init__(self, engine, config_dict):
        super(WeiherhammerXTypes, self).__init__(engine, config_dict)
        loginf("Service version is %s" % VERSION)

        altitude = engine.stn_info.altitude_vt
        latitude = engine.stn_info.latitude_f
        longitude = engine.stn_info.longitude_f

        # Get any user-defined overrides
        try:
            override_dict = config_dict['WeiherhammerWXCalculate']['WXXTypes']
        except KeyError:
            override_dict = {}
        # Get the default values, then merge the user overrides into it
        option_dict = weeutil.config.deep_copy(defaults_dict['WeiherhammerWXCalculate']['WXXTypes'])
        option_dict.merge(override_dict)

        # solar-heatindex-related options
        solar_heatindex_algo = option_dict['solar_heatindex'].get('algorithm', 'new').lower()

        # sunshine threshold related options
        sunshineThreshold_debug = to_int(option_dict['sunshineThreshold'].get('debug', 0))
        sunshineThreshold_coeff_dict = option_dict['sunshineThreshold'].get('coeff', {})

        # sunshine related options
        sunshine_debug = to_int(option_dict['sunshine'].get('debug', 0))

        sunshine_radiation_min = to_float(option_dict['sunshine'].get('radiation_min', 0.0))
        if sunshine_radiation_min < 0.0:
            logerr("Invalid value radiation_min %.2f, using default 0.0 instead!" % sunshine_radiation_min)
            sunshine_radiation_min = 0.0

        sunshine_threshold_min = to_float(option_dict['sunshine'].get('threshold_min', 0.0))
        if sunshine_threshold_min < 0.0:
            logerr("Invalid value threshold_min %.2f, using default 0.0 instead!" % sunshine_threshold_min)
            sunshine_threshold_min = 0.0

        sunshine_evaluate_min = option_dict['sunshine'].get('evaluate_min', 'radiation').lower()
        if sunshine_evaluate_min != 'radiation' and sunshine_evaluate_min != 'threshold':
            logerr("Invalid value evaluate_min '%s', using default 'radiation' instead!" % sunshine_evaluate_min)
            sunshine_evaluate_min = 'radiation'

        # Instantiate an instance of WXXTypes:
        self.wxxtypes = WXXTypes(altitude, latitude, longitude, 
                                 sunshineThreshold_debug,
                                 sunshineThreshold_coeff_dict,
                                 sunshine_debug,
                                 sunshine_radiation_min,
                                 sunshine_threshold_min,
                                 sunshine_evaluate_min,
                                 solar_heatindex_algo
                                 )
        # Register it:
        weewx.xtypes.xtypes.append(self.wxxtypes)

    def shutDown(self):
        # Remove the registered instance:
        weewx.xtypes.xtypes.remove(self.wxxtypes)



class WeiherhammerPressureCooker(weewx.engine.StdService):
    """Instantiate and register the Weiherhammer XTypes extension PressureCooker"""

    def __init__(self, engine, config_dict):
        """Initialize the PressureCooker. """
        super(WeiherhammerPressureCooker, self).__init__(engine, config_dict)

        try:
            override_dict = config_dict['WeiherhammerWXCalculate']['PressureCooker']
        except KeyError:
            override_dict = {}

        # Get the default values, then merge the user overrides into it
        option_dict = weeutil.config.deep_copy(defaults_dict['WeiherhammerWXCalculate']['PressureCooker'])
        option_dict.merge(override_dict)

        max_delta_12h = to_float(option_dict.get('max_delta_12h', 1800))
        altimeter_algorithm = option_dict['altimeter'].get('algorithm', 'aaASOS')

        self.pressure_cooker = PressureCooker(engine.stn_info.altitude_vt,
                                              max_delta_12h,
                                              altimeter_algorithm)

        # Add pressure_cooker to the XTypes system
        weewx.xtypes.xtypes.append(self.pressure_cooker)

    def shutDown(self):
        """Engine shutting down. """
        weewx.xtypes.xtypes.remove(self.pressure_cooker)

