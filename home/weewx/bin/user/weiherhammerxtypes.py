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
import math
from datetime import datetime
import time
from math import sin,cos,pi,asin
import ast

# WeeWX imports
import weewx
import weewx.units
import weewx.xtypes
import weeutil.config
from weewx.engine import StdService
from weeutil.weeutil import to_int, to_float, to_bool
from weewx.units import ValueTuple, CtoF, FtoC, INHG_PER_MBAR

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

VERSION = '0.3'

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
    [[PressureCooker]]
        max_delta_12h = 1800
        [[[altimeter]]]
            algorithm = aaASOS    # Case-sensitive!
"""
defaults_dict = weeutil.config.config_from_str(DEFAULTS_INI)

def wetbulb_Metric(t_C, RH, PP):
    #  Wet bulb calculations == Kuehlgrenztemperatur, Feuchtekugeltemperatur
    #  t_C = outTemp
    #  RH = outHumidity
    #  PP = pressure

    if t_C is None or RH is None or PP is None:
        return None

    Tdc = ((t_C - (14.55 + 0.114 * t_C) * (1 - (0.01 * RH)) - ((2.5 + 0.007 * t_C) * (1 - (0.01 * RH))) ** 3 - (15.9 + 0.117 * t_C) * (1 - (0.01 * RH)) ** 14))
    E = (6.11 * 10 ** (7.5 * Tdc / (237.7 + Tdc)))
    WBc = (((0.00066 * PP) * t_C) + ((4098 * E) / ((Tdc + 237.7) ** 2) * Tdc)) / ((0.00066 * PP) + (4098 * E) / ((Tdc + 237.7) ** 2))
    return WBc if WBc is not None else None

def wetbulb_US(t_F, RH, p_inHg):
    #  Wet bulb calculations == Kuehlgrenztemperatur, Feuchtekugeltemperatur
    #  t_F = temperatur degree F
    #  RH = outHumidity
    #  p_inHg = pressure in inHg

    if t_F is None or RH is None or p_inHg is None:
        return None

    t_C = FtoC(t_F)
    p_mbar = p_inHg / INHG_PER_MBAR
    wb_C = wetbulb_Metric(t_C, RH, p_mbar)

    return CtoF(wb_C) if wb_C is not None else None

def airDensity_Metric(dp_C, t_C, p_mbar):
    """Calculate the Air density in in kg per m3
    dp_C - dewpoint in degree Celsius
    t_C - temperature in degree Celsius
    p_mbar - pressure in hPa or mbar
    """

    if dp_C is None or t_C is None or p_mbar is None:
        return None

    dp = dp_C
    Tk = (t_C) + 273.15
    p = (0.99999683 + dp * (-0.90826951E-2 + dp * (0.78736169E-4 +
        dp * (-0.61117958E-6 + dp * (0.43884187E-8 +
        dp * (-0.29883885E-10 + dp * (0.21874425E-12 +
        dp * (-0.17892321E-14 + dp * (0.11112018E-16 +
        dp * (-0.30994571E-19))))))))))
    Pv = 100 * 6.1078 / (p**8)
    Pd = p_mbar * 100 - Pv
    density = round((Pd / (287.05 * Tk)) + (Pv / (461.495 * Tk)), 3)

    return density

def airDensity_US(dp_F, t_F, p_inHg):
    """Calculate the Air Density in kg per m3
    dp_F - dewpoint in degree Fahrenheit
    t_F - temperature in degree Fahrenheit
    p_inHg - pressure in inHg
    calculation airdensity_Metric(dp_C, t_C, p_mbar)
    """

    if dp_F is None or t_F is None or p_inHg is None:
        return None

    t_C = FtoC(t_F)
    dp_C = FtoC(dp_F)
    p_mbar = p_inHg / INHG_PER_MBAR
    aden_C = airDensity_Metric(dp_C, t_C, p_mbar)

    return aden_C if aden_C is not None else None

def windPressure_Metric(dp_C, t_C, p_mbar, ws_kph):
    """Calculate the windPressure in N per m2
    dp_C - dewpoint in degree Celsius
    t_C - temperature in degree Celsius
    p_mbar - pressure in hPa or mbar
    vms - windSpeed in km per hour
          must in  m per second
    wd = cp * airdensity / 2 * vms2
    wd - winddruck
    cp - Druckbeiwert (dimensionslos) = 1
    """

    if dp_C is None or t_C is None or p_mbar is None or ws_kph is None:
        return None

    dp = dp_C
    Tk = t_C + 273.15

    if ws_kph < 1:
        vms = 0.2
    elif ws_kph < 6:
        vms = 1.5
    elif ws_kph < 12:
        vms = 3.3
    elif ws_kph < 20:
        vms = 5.4
    elif ws_kph < 29:
        vms = 7.9
    elif ws_kph < 39:
        vms = 10.7
    elif ws_kph < 50:
        vms = 13.8
    elif ws_kph < 62:
        vms = 17.1
    elif ws_kph < 75:
        vms = 20.7
    elif ws_kph < 89:
        vms = 24.7
    elif ws_kph < 103:
        vms = 28.5
    elif ws_kph < 117:
        vms = 32.7
    elif ws_kph >= 117:
        vms = ws_kph * 0.277777778

    p = (0.99999683 + dp * (-0.90826951E-2 + dp * (0.78736169E-4 +
        dp * (-0.61117958E-6 + dp * (0.43884187E-8 +
        dp * (-0.29883885E-10 + dp * (0.21874425E-12 +
        dp * (-0.17892321E-14 + dp * (0.11112018E-16 +
        dp * (-0.30994571E-19))))))))))

    Pv = 100 * 6.1078 / (p**8)
    Pd = p_mbar * 100 - Pv
    densi = round((Pd / (287.05 * Tk)) + (Pv / (461.495 * Tk)), 3)

    wsms2 = vms * vms

    winddruck = densi / 2 * wsms2

    return winddruck

def windPressure_US(dp_F, t_F, p_inHg, ws_mph):
    """Calculate the windPressure in N per m2
    dp_F - dewpoint in degree Fahrenheit
    t_F - temperature in degree Fahrenheit
    p_inHg - pressure in inHg
    ws_mph - windSpeed in mile per hour
    """
    if dp_F is None or t_F is None or p_inHg is None or ws_mph is None:
        return None

    t_C = FtoC(t_F)
    dp_C = FtoC(dp_F)
    p_mbar = p_inHg / INHG_PER_MBAR
    ws_kph = ws_mph * 1.609344

    wdru_C = windPressure_Metric(dp_C, t_C, p_mbar, ws_kph)

    return wdru_C if wdru_C is not None else None

def thwIndex_Metric(t_C, RH, ws_kph):
    """ Uses the air temperature, relative humidity, and wind speed
    (THW = temperature-humidity-wind) to calculate a
    potentially more accurate "felt-air temperature." This is not as accurate, however, as the THSW index, which
    can only be calculated when solar radiation information is available. It uses `calculate_heat_index` and then
    applies additional calculations to it using the wind speed. As such, it returns `None` for input temperatures below
    70 degrees Fahrenheit. The additional calculations come from web forums rumored to contain the proprietary
    Davis Instruments THW index formulas.
    hi is the heat index as calculated by `calculate_heat_index`
    WS is the wind speed in miles per hour
    :param temperature: The temperature in degrees Fahrenheit
    :type temperature: int | long | decimal.Decimal
    :param relative_humidity: The relative humidity as a percentage (88.2 instead of 0.882)
    :type relative_humidity: int | long | decimal.Decimal
    :param wind_speed: The wind speed in miles per hour
    :type wind_speed: int | long | decimal.Decimal
    :return: The THW index temperature in degrees Fahrenheit to one decimal place, or `None` if the temperature is
     less than 70F
    :rtype: decimal.Decimal
    """
    t_F = CtoF(t_C)
    hi_F = weewx.wxformulas.heatindexF(t_F, RH)
    WS = kph_to_mph(ws_kph)

    if not hi_F:
        return None

    hi = hi_F - (1.072 * WS)
    thw_C = FtoC(hi)

    # return round(thw_C, 1) if thw_C is not None else None
    return thw_C if thw_C is not None else None

def thwIndex_US(t_F, RH, ws_mph):

    if t_F is None or ws_mph is None or RH is None:
        return None

    hi_F = weewx.wxformulas.heatindexF(t_F, RH)
    thw_F = hi_F - (1.072 * ws_mph)

    # return round(thw_F, 1) if thw_F is not None else None
    return thw_F if thw_F is not None else None

def thswIndex_Metric(t_C, RH, ws_kph, rahes):
    """ Tc is the temperature in degrees Celsius
        RH is the relative humidity percentage
        QD is the direct thermal radiation in watts absorbed per square meter of surface area
        Qd is the diffuse thermal radiation in watts absorbed per square meter of surface area
        Q1 is the thermal radiation in watts absorbed per square meter of surface area as measured by a pyranometer;
                it represents "global radiation" (QD + Qd)
        Q2 is the direct and diffuse radiation in watts absorbed per square meter of surface on the human body
        Q3 is the ground-reflected radiation in watts absorbed per square meter of surface on the human body
        Q is total thermal radiation that affects apparent temperature
        WS is the wind speed in meters per second
        E is the water vapor pressure
        Thsw is the THSW index temperature 
    https://github.com/beamerblvd/weatherlink-python/blob/master/weatherlink/utils.py
    """

    if t_C is None or ws_kph is None or RH is None or rahes is None:
        return None

    Qd = rahes * 0.25
    Q2 = Qd / 7
    Q3 = rahes / 28
    Q = Q2 + Q3
    WS = ws_kph * 0.277777778
    E = RH / 100 * 6.105 * math.exp(17.27 * t_C / (237.7 + t_C))
    thsw_C = t_C + (0.348 * E) - (0.70 * WS) + ((0.70 * Q) / (WS + 10)) - 4.25

    # return round(thsw_C, 1) if thsw_C is not None else None
    return thsw_C if thsw_C is not None else None

def thswIndex_US(t_F, RH, ws_mph, rahes):

    if t_F is None or ws_mph is None or RH is None or rahes is None:
        return None

    t_C = FtoC(t_F)
    ws_kph = ws_mph * 1.609344
    thsw_C = thswIndex_Metric(t_C, RH, ws_kph, rahes)
    thsw_F = CtoF(thsw_C)

    # return round(thsw_F, 1) if thsw_F is not None else None
    return thsw_F if thsw_F is not None else None

# calculate sunshine threshold for sunshine yes/no
# https://github.com/Jterrettaz/sunduration
def sunshineThreshold(mydatetime, lat, lon, coeff=1.0):
    utcdate = datetime.utcfromtimestamp(mydatetime)
    dayofyear = to_int(time.strftime("%j",time.gmtime(mydatetime)))
    theta = 360 * dayofyear / 365
    equatemps = 0.0172 + 0.4281 * cos((pi / 180) * theta) - 7.3515 * sin(
        (pi / 180) * theta) - 3.3495 * cos(2 * (pi / 180) * theta) - 9.3619 * sin(
        2 * (pi / 180) * theta)
    corrtemps = lon * 4
    declinaison = asin(0.006918 - 0.399912 * cos((pi / 180) * theta) + 0.070257 * sin(
        (pi / 180) * theta) - 0.006758 * cos(2 * (pi / 180) * theta) + 0.000908 * sin(
        2 * (pi / 180) * theta)) * (180 / pi)
    minutesjour = utcdate.hour * 60 + utcdate.minute
    tempsolaire = (minutesjour + corrtemps + equatemps) / 60
    angle_horaire = (tempsolaire - 12) * 15
    hauteur_soleil = asin(sin((pi / 180) * lat) * sin((pi / 180) * declinaison) + cos(
        (pi / 180) * lat) * cos((pi / 180) * declinaison) * cos((pi / 180) * angle_horaire)) * (180 / pi)
    if hauteur_soleil > 3:
        seuil = (0.73 + 0.06 * cos((pi / 180) * 360 * dayofyear / 365)) * 1080 * pow(
            sin((pi / 180) * hauteur_soleil), 1.25) * coeff
    else:
        seuil = 0.0

    return seuil

class WXXTypes(weewx.xtypes.XType):
    """Weiherhammer weather extensions to the WeeWX xtype system"""

    def __init__(self, altitude, latitude, longitude,
                 sunshineThreshold_debug,
                 sunshineThreshold_coeff_dict,
                 sunshine_debug,
                 sunshine_radiation_min,
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

        if self.sunshineThreshold_debug > 0:
            logdbg("sunshineThreshold, monthly coeff is %s" % str(self.sunshineThreshold_coeff_dict))
        if self.sunshine_debug > 0:
            logdbg("sunshine, radiation_min is %.2f" % self.sunshine_radiation_min)

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
            val = wetbulb_US(data['outTemp'], data['outHumidity'], data['pressure'])
            u = 'degree_F'
        else:
            val = wetbulb_Metric(data['outTemp'], data['outHumidity'], data['pressure'])
            u = 'degree_C'
        return ValueTuple(val, u, 'group_temperature')

    @staticmethod
    def calc_solar_wetBulb(key, data, db_manager=None):
        if 'solar_temperature' not in data or 'solar_humidity' not in data or 'solar_pressure' not in data:
            raise weewx.CannotCalculate(key)

        if data['usUnits'] == weewx.US:
            val = wetbulb_US(data['solar_temperature'], data['solar_humidity'], data['solar_pressure'])
            u = 'degree_F'
        else:
            val = wetbulb_Metric(data['solar_temperature'], data['solar_humidity'], data['solar_pressure'])
            u = 'degree_C'
        return ValueTuple(val, u, 'group_temperature')

    def calc_solar_heatindex(self, key, data, db_manager=None):
        if 'solar_temperature' not in data or 'solar_humidity' not in data:
            raise weewx.CannotCalculate(key)
        if data['usUnits'] == weewx.US:
            val = weewx.wxformulas.heatindexF(data['solar_temperature'], data['solar_humidity'],
                                              algorithm=self.solar_heatindex_algo)
            u = 'degree_F'
        else:
            val = weewx.wxformulas.heatindexC(data['solar_temperature'], data['solar_humidity'],
                                              algorithm=self.solar_heatindex_algo)
            u = 'degree_C'
        return ValueTuple(val, u, 'group_temperature')

    @staticmethod
    def calc_solar_dewpoint(key, data, db_manager=None):
        if 'solar_temperature' not in data or 'solar_humidity' not in data:
            raise weewx.CannotCalculate(key)
        if data['usUnits'] == weewx.US:
            val = weewx.wxformulas.dewpointF(data['solar_temperature'], data['solar_humidity'])
            u = 'degree_F'
        else:
            val = weewx.wxformulas.dewpointC(data['solar_temperature'], data['solar_humidity'])
            u = 'degree_C'
        return ValueTuple(val, u, 'group_temperature')

    @staticmethod
    def calc_solar_windchill(key, data, db_manager=None):
        if 'solar_temperature' not in data or 'windSpeed' not in data:
            raise weewx.CannotCalculate(key)
        if data['usUnits'] == weewx.US:
            val = weewx.wxformulas.windchillF(data['solar_temperature'], data['windSpeed'])
            u = 'degree_F'
        elif data['usUnits'] == weewx.METRIC:
            val = weewx.wxformulas.windchillMetric(data['solar_temperature'], data['windSpeed'])
            u = 'degree_C'
        elif data['usUnits'] == weewx.METRICWX:
            val = weewx.wxformulas.windchillMetricWX(data['solar_temperature'], data['windSpeed'])
            u = 'degree_C'
        else:
            raise weewx.ViolatedPrecondition("Unknown unit system %s" % data['usUnits'])
        return ValueTuple(val, u, 'group_temperature')

    @staticmethod
    def calc_solar_humidex(key, data, db_manager=None):
        if 'solar_temperature' not in data or 'solar_humidity' not in data:
            raise weewx.CannotCalculate(key)
        if data['usUnits'] == weewx.US:
            val = weewx.wxformulas.humidexF(data['solar_temperature'], data['solar_humidity'])
            u = 'degree_F'
        else:
            val = weewx.wxformulas.humidexC(data['solar_temperature'], data['solar_humidity'])
            u = 'degree_C'
        return ValueTuple(val, u, 'group_temperature')

    @staticmethod
    def calc_solar_appTemp(key, data, db_manager=None):
        if 'solar_temperature' not in data or 'solar_humidity' not in data or 'windSpeed' not in data:
            raise weewx.CannotCalculate(key)
        if data['usUnits'] == weewx.US:
            val = weewx.wxformulas.apptempF(data['solar_temperature'], data['solar_humidity'],
                                            data['windSpeed'])
            u = 'degree_F'
        else:
            # The metric equivalent needs wind speed in mps. Convert.
            windspeed_vt = weewx.units.as_value_tuple(data, 'windSpeed')
            windspeed_mps = weewx.units.convert(windspeed_vt, 'meter_per_second')[0]
            val = weewx.wxformulas.apptempC(data['solar_temperature'], data['solar_humidity'], windspeed_mps)
            u = 'degree_C'
        return ValueTuple(val, u, 'group_temperature')

    def calc_sunshineThreshold(self, key, data, db_manager=None):
        if 'dateTime' not in data:
            raise weewx.CannotCalculate(key)
        monthofyear = to_int(time.strftime("%m",time.gmtime(data['dateTime'])))
        coeff = to_float(self.sunshineThreshold_coeff_dict.get(str(monthofyear)))
        if coeff is None:
            coeff = to_float(defaults_dict.get(str(monthofyear), 1.0))
            logerr("sunshineThreshold, user configured coeff month=%d is not valid! Using default coeff instead." % (monthofyear))
        if self.sunshineThreshold_debug >= 3:
            logdbg("sunshineThreshold, month=%d coeff=%.2f" % (monthofyear, coeff)) 
        threshold = sunshineThreshold(data['dateTime'], self.lat, self.lon, coeff)
        if self.sunshineThreshold_debug >= 2:
            logdbg("sunshineThreshold, threshold=%.2f" % threshold)
        return ValueTuple(threshold, 'watt_per_meter_squared', 'group_radiation')

    def calc_sunshineRadiationMin(self, key, data, db_manager=None):
        return ValueTuple(self.sunshine_radiation_min, 'watt_per_meter_squared', 'group_radiation')

    def calc_sunshine(self, key, data, db_manager=None):
        if 'radiation' not in data or 'dateTime' not in data:
            raise weewx.CannotCalculate(key)
        sunshine = threshold = None
        if data['radiation'] is not None:
            if data['radiation'] >= self.sunshine_radiation_min:
                sunshine = 0
                monthofyear = to_int(time.strftime("%m",time.gmtime(data['dateTime'])))
                coeff = to_float(self.sunshineThreshold_coeff_dict.get(str(monthofyear)))
                if coeff is None:
                    coeff = 1.0
                    logerr("sunshine, user configured coeff month=%d is not valid! Using default coeff=1.0 instead." % (monthofyear))
                if self.sunshine_debug >= 3:
                    logdbg("sunshine, month=%d coeff=%.2f" % (monthofyear, coeff)) 
                threshold = sunshineThreshold(data['dateTime'], self.lat, self.lon, coeff)
                if threshold > 0.0 and data['radiation'] > threshold:
                    sunshine = 1
            elif self.sunshine_debug >= 2:
                logdbg("sunshine, radiation=%.2f lower than radiation_min=%.2f" % (data['radiation'], self.sunshine_radiation_min))
        elif self.sunshine_debug >= 3:
            logdbg("sunshine, radiation is None")
        if self.sunshine_debug >= 2:
            logdbg("sunshine, sunshine=%s radiation=%s threshold=%s" % (
                str(sunshine) if sunshine is not None else 'None',
                str(data['radiation']) if data['radiation'] is not None else 'None',
                str(threshold) if threshold is not None else 'None'))
        return ValueTuple(sunshine, 'count', 'group_count')

    @staticmethod
    def calc_airDensity(key, data, db_manager=None):
        if 'dewpoint' not in data or 'outTemp' not in data or 'pressure' not in data:
            raise weewx.CannotCalculate(key)

        if data['usUnits'] == weewx.US:
            val = airDensity_US(data['dewpoint'], data['outTemp'], data['pressure'])
            u = 'kg_per_meter_qubic'
        else:
            val = airDensity_Metric(data['dewpoint'], data['outTemp'], data['pressure'])
            u = 'kg_per_meter_qubic'
        return ValueTuple(val, u, 'group_pressure3')

    @staticmethod
    def calc_windPressure(key, data, db_manager=None):
        if 'dewpoint' not in data or 'outTemp' not in data or 'windSpeed' not in data or 'pressure' not in data:
            raise weewx.CannotCalculate(key)

        if data['usUnits'] == weewx.US:
            val = windPressure_US(data['dewpoint'], data['outTemp'], data['pressure'], data['windSpeed'])
            u = 'N_per_meter_squared'
        else:
            val = windPressure_Metric(data['dewpoint'], data['outTemp'], data['pressure'], data['windSpeed'])
            u = 'N_per_meter_squared'
        return ValueTuple(val, u, 'group_pressure2')

    @staticmethod
    def calc_thwIndex(key, data, db_manager=None):
        if 'outTemp' not in data or 'outHumidity' not in data or 'windSpeed' not in data:
            raise weewx.CannotCalculate(key)

        if data['usUnits'] == weewx.US:
            val = thwIndex_US(data['outTemp'], data['outHumidity'], data['windSpeed'])
            u = 'degree_F'
        else:
            val = thwIndex_Metric(data['outTemp'], data['outHumidity'], data['windSpeed'])
            u = 'degree_C'
        return ValueTuple(val, u, 'group_temperature')

    @staticmethod
    def calc_thswIndex(key, data, db_manager=None):
        if 'outTemp' not in data or 'outHumidity' not in data or 'windSpeed' not in data or 'radiation' not in data:
            raise weewx.CannotCalculate(key)

        if data['usUnits'] == weewx.US:
            val = thswIndex_US(data['outTemp'], data['outHumidity'], data['windSpeed'], data['radiation'])
            u = 'degree_F'
        else:
            val = thswIndex_Metric(data['outTemp'], data['outHumidity'], data['windSpeed'], data['radiation'])
            u = 'degree_C'
        return ValueTuple(val, u, 'group_temperature')


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
        if key == 'solar_pressure':
            if any(key not in record for key in ['usUnits', 'solar_temperature', 'solar_barometer', 'solar_humidity']):
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
        if obs == 'solar_pressure':
            temp_12h_vt = self._get_solar_temp_12h(record['dateTime'], dbmanager)
            if temp_12h_vt is None \
                    or temp_12h_vt[0] is None \
                    or record['solar_temperature'] is None \
                    or record['solar_barometer'] is None \
                    or record['solar_humidity'] is None:
                pressure = None
            else:
                # The following requires everything to be in US Customary units.
                # Rather than convert the whole record, just convert what we need:
                record_US = weewx.units.to_US({'usUnits': record['usUnits'],
                                               'solar_temperature': record['solar_temperature'],
                                               'solar_barometer': record['solar_barometer'],
                                               'solar_humidity': record['solar_humidity']})
                # Get the altitude in feet
                altitude_ft = weewx.units.convert(self.altitude_vt, "foot")
                # The outside temperature in F.
                temp_12h_F = weewx.units.convert(temp_12h_vt, "degree_F")
                pressure = weewx.uwxutils.uWxUtilsVP.SeaLevelToSensorPressure_12(
                    record_US['solar_barometer'],
                    altitude_ft[0],
                    record_US['solar_temperature'],
                    temp_12h_F[0],
                    record_US['solar_humidity']
                )

        return ValueTuple(pressure, 'inHg', 'group_pressure')

    def altimeter(self, record, obs):
        """Calculate the observation type 'xxx_altimeter'."""
        if obs == 'asky_box_altimeter':
            if 'asky_box_pressure' not in record:
                raise weewx.CannotCalculate(obs)
        if obs == 'solar_altimeter':
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
        if obs == 'solar_altimeter':
            altimeter = formula(record['solar_pressure'], altitude[0], self.altimeter_algorithm)

        return ValueTuple(altimeter, u, 'group_pressure')

    def barometer(self, record, obs):
        """Calculate the observation type 'xxx_barometer'"""
        if obs == 'asky_box_barometer':
            if 'asky_box_pressure' not in record or 'asky_box_temperature' not in record:
                raise weewx.CannotCalculate(obs)
        if obs == 'solar_barometer':
            if 'solar_pressure' not in record or 'solar_temperature' not in record:
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
        if obs == 'solar_barometer':
            barometer = formula(record['solar_pressure'], altitude[0], record['solar_temperature'])

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

        # Instantiate an instance of WXXTypes:
        self.wxxtypes = WXXTypes(altitude, latitude, longitude, 
                                 sunshineThreshold_debug,
                                 sunshineThreshold_coeff_dict,
                                 sunshine_debug,
                                 sunshine_radiation_min,
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
