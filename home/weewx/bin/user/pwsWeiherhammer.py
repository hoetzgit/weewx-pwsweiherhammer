#
#    Copyright (c) 2022 Henry Ott <hoetz@gmx.net>
#
"""

REQUIRES WeeWX V4.2 OR LATER!

To use:
    1. Stop weewxd
    2. Put this file in your user subdirectory.
    3. In weewx.conf, subsection [Engine][[Services]], add pwsWeiherhammerService to the list
    "xtype_services". For example, this means changing this

        [Engine]
            [[Services]]
                xtype_services = weewx.wxxtypes.StdWXXTypes, weewx.wxxtypes.StdPressureCooker, weewx.wxxtypes.StdRainRater

    to this:

        [Engine]
            [[Services]]
                xtype_services = weewx.wxxtypes.StdWXXTypes, weewx.wxxtypes.StdPressureCooker, weewx.wxxtypes.StdRainRater, user.pwsWeiherhammer.pwsWeiherhammerService

    4. Optionally, add the following section to weewx.conf:
        [pwsWeiherhammer]
            [[WXXTypes]]
                [[[solar_heatindex]]]
                    algorithm = new

    5. Restart weewxd

"""

VERSION = "0.0.2"

import math
from datetime import datetime
import time
from math import sin,cos,pi,asin

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
        syslog.syslog(level, 'pwsWeiherhammer: %s' % msg)

    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)

DEFAULTS_INI = """
[StdWXCalculate]
  [[WXXTypes]]
    [[[windDir]]]
       force_null = True
    [[[maxSolarRad]]]
      algorithm = rs
      atc = 0.8
      nfac = 2
    [[[ET]]]
      wind_height = 2.0
      et_period = 3600
    [[[heatindex]]]
      algorithm = new
  [[PressureCooker]]
    max_delta_12h = 1800
    [[[altimeter]]]
      algorithm = aaASOS    # Case-sensitive!
  [[RainRater]]
    rain_period = 900
    retain_period = 930
  [[Delta]]
    [[[rain]]]
      input = totalRain
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

class pwsWeiherhammer(weewx.xtypes.XType):

    def __init__(self, altitude, latitude, longitude,
                 solar_heat_index_algo='new',
                 sunshine_coeff=0.79,
                 sunshine_min=20.0,
                 sunshine_debug=False
                 ):
        self.alt = altitude
        self.lat = latitude
        self.lon = longitude
        self.solar_heat_index_algo = solar_heat_index_algo.lower()
        self.sunshine_coeff = sunshine_coeff
        self.sunshine_min = sunshine_min
        self.sunshine_debug = sunshine_debug

        loginf("Version %s" % VERSION)

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
                                              algorithm=self.solar_heat_index_algo)
            u = 'degree_F'
        else:
            val = weewx.wxformulas.heatindexC(data['solar_temperature'], data['solar_humidity'],
                                              algorithm=self.solar_heat_index_algo)
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

    # calculate sunshine threshold for sunshining yes/no
    def calc_sunshineThreshold(self, key, data, db_manager=None):
        utcdate = datetime.utcfromtimestamp(int(data['dateTime']))
        dayofyear = int(time.strftime("%j",time.gmtime(int(data['dateTime']))))
        theta = 360 * dayofyear / 365
        equatemps = 0.0172 + 0.4281 * cos((pi / 180) * theta) - 7.3515 * sin(
            (pi / 180) * theta) - 3.3495 * cos(2 * (pi / 180) * theta) - 9.3619 * sin(
            2 * (pi / 180) * theta)
        corrtemps = self.lon * 4
        declinaison = asin(0.006918 - 0.399912 * cos((pi / 180) * theta) + 0.070257 * sin(
            (pi / 180) * theta) - 0.006758 * cos(2 * (pi / 180) * theta) + 0.000908 * sin(
            2 * (pi / 180) * theta)) * (180 / pi)
        minutesjour = utcdate.hour * 60 + utcdate.minute
        tempsolaire = (minutesjour + corrtemps + equatemps) / 60
        angle_horaire = (tempsolaire - 12) * 15
        hauteur_soleil = asin(sin((pi / 180) * self.lat) * sin((pi / 180) * declinaison) + cos(
            (pi / 180) * self.lat) * cos((pi / 180) * declinaison) * cos((pi / 180) * angle_horaire)) * (180 / pi)
        if hauteur_soleil > 3:
            seuil = (0.73 + 0.06 * cos((pi / 180) * 360 * dayofyear / 365)) * 1080 * pow(
                (sin(pi / 180) * hauteur_soleil), 1.25) * self.sunshine_coeff
        else:
            seuil = 0.0
        return ValueTuple(seuil, 'watt_per_meter_squared', 'group_radiation')

    # calculate sunshine threshold for sunshining yes/no
    def calc_sunshineThresholdOriginal(self, key, data, db_manager=None):
        utcdate = datetime.utcfromtimestamp(int(data['dateTime']))
        dayofyear = int(time.strftime("%j",time.gmtime(int(data['dateTime']))))
        theta = 360 * dayofyear / 365
        equatemps = 0.0172 + 0.4281 * cos((pi / 180) * theta) - 7.3515 * sin(
            (pi / 180) * theta) - 3.3495 * cos(2 * (pi / 180) * theta) - 9.3619 * sin(
            2 * (pi / 180) * theta)
        corrtemps = self.lon * 4
        declinaison = asin(0.006918 - 0.399912 * cos((pi / 180) * theta) + 0.070257 * sin(
            (pi / 180) * theta) - 0.006758 * cos(2 * (pi / 180) * theta) + 0.000908 * sin(
            2 * (pi / 180) * theta)) * (180 / pi)
        minutesjour = utcdate.hour * 60 + utcdate.minute
        tempsolaire = (minutesjour + corrtemps + equatemps) / 60
        angle_horaire = (tempsolaire - 12) * 15
        hauteur_soleil = asin(sin((pi / 180) * self.lat) * sin((pi / 180) * declinaison) + cos(
            (pi / 180) * self.lat) * cos((pi / 180) * declinaison) * cos((pi / 180) * angle_horaire)) * (180 / pi)
        if hauteur_soleil > 0:
            seuil = (0.7 + 0.085 * cos((pi / 180) * 360 * dayofyear / 365)) * 1080 * pow(
                (sin(pi / 180) * hauteur_soleil), 1.25) 
        else:
            seuil = 0.0
        return ValueTuple(seuil, 'watt_per_meter_squared', 'group_radiation')

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


class pwsWeiherhammerService(StdService):
    """ WeeWX service whose job is to register the XTypes extension pwsWeiherhammer with the
    XType system.
    """

    def __init__(self, engine, config_dict):
        super(pwsWeiherhammerService, self).__init__(engine, config_dict)

        altitude = engine.stn_info.altitude_vt
        latitude = engine.stn_info.latitude_f
        longitude = engine.stn_info.longitude_f

        # Get any user-defined overrides
        try:
            override_dict = config_dict['pwsWeiherhammer']['WXXTypes']
        except KeyError:
            override_dict = {}
        # Get the default values, then merge the user overrides into it
        option_dict = weeutil.config.deep_copy(defaults_dict['StdWXCalculate']['WXXTypes'])
        option_dict.merge(override_dict)

        # solar-heatindex-related options
        solar_heatindex_algo = option_dict['solar_heatindex'].get('algorithm', 'new').lower()

        # sunshine threshold related options
        sunshine_coeff = float(option_dict['sunshineThreshold'].get('coeff', 0.79))
        sunshine_min = float(option_dict['sunshineThreshold'].get('sunshine_min', 20.0))
        sunshine_debug = to_bool(option_dict['sunshineThreshold'].get('debug', False))

        # Instantiate an instance of pwsWeiherhammer:
        self.pwsW = pwsWeiherhammer(altitude, latitude, longitude, 
                                    solar_heatindex_algo,
                                    sunshine_coeff,
                                    sunshine_min,
                                    sunshine_debug
                                   )
        # Register it:
        weewx.xtypes.xtypes.append(self.pwsW)

    def shutDown(self):
        # Remove the registered instance:
        weewx.xtypes.xtypes.remove(self.pwsW)
