"""
    Copyright (C) 2022 Henry Ott

    Various weather related formulas and utilities.

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
from __future__ import absolute_import
from __future__ import print_function

# python imports
import logging
import cmath
import math
from math import sin,cos,pi,asin
from datetime import datetime
import time

# WeeWX imports
from weeutil.weeutil import to_int, to_float, to_bool
import weewx.uwxutils
import weewx.units
from weewx.units import ValueTuple, CtoK, CtoF, FtoC, mph_to_knot, kph_to_knot, mps_to_knot
from weewx.units import INHG_PER_MBAR, METER_PER_FOOT, METER_PER_MILE, MM_PER_INCH

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

VERSION = '0.1'

# PWS Weiherhammer own weathercodes
pws_weathercode_clear_sky = 0
pws_weathercode_mostly_clear = 1
pws_weathercode_partly_cloudy = 2
pws_weathercode_mostly_cloudy = 3
pws_weathercode_overcast = 4
pws_weathercode_slight_rain = 61
pws_weathercode_moderate_rain = 63
pws_weathercode_heavy_rain = 65
pws_weathercode_very_heavy_rain = 66
pws_weathercode_thunderstorm_rain = 95
pws_weathercode_thunderstorm = 96
pws_weathercode_unknown = -1

def wetbulbC(t_C, RH, PP):
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

def wetbulbF(t_F, RH, p_inHg):
    #  Wet bulb calculations == Kuehlgrenztemperatur, Feuchtekugeltemperatur
    #  t_F = temperatur degree F
    #  RH = outHumidity
    #  p_inHg = pressure in inHg

    if t_F is None or RH is None or p_inHg is None:
        return None

    t_C = FtoC(t_F)
    p_mbar = p_inHg / INHG_PER_MBAR
    wb_C = wetbulbC(t_C, RH, p_mbar)

    return CtoF(wb_C) if wb_C is not None else None

def thwIndexC(t_C, RH, ws_kph):
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

def thwIndexF(t_F, RH, ws_mph):

    if t_F is None or ws_mph is None or RH is None:
        return None

    hi_F = weewx.wxformulas.heatindexF(t_F, RH)
    thw_F = hi_F - (1.072 * ws_mph)

    # return round(thw_F, 1) if thw_F is not None else None
    return thw_F if thw_F is not None else None

def thswIndexC(t_C, RH, ws_kph, rahes):
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

def thswIndexF(t_F, RH, ws_mph, rahes):

    if t_F is None or ws_mph is None or RH is None or rahes is None:
        return None

    t_C = FtoC(t_F)
    ws_kph = ws_mph * 1.609344
    thsw_C = thswIndexC(t_C, RH, ws_kph, rahes)
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

# calculate battery values in percent
def batt_to_percent(isBatt, minBatt, maxBatt):
    isBatt = round(isBatt, 1)
    minBatt = round(minBatt, 1)
    maxBatt = round(maxBatt, 1)
    if isBatt > maxBatt:
        isBatt = maxBatt
    if isBatt < minBatt:
        isBatt = minBatt
    isBatt -= minBatt
    maxBatt -= minBatt
    percentBatt = 0.0
    if isBatt > 0.0:
        percentBatt = isBatt * 100 / maxBatt
    return percentBatt

# "calculate" Ecowitt WH31 battery status in percent
# Battery values 0 (high) => 100% and 1 (low) => 50%
def wh31_batt_to_percent(isBatt):
    if isBatt < 1.0:
        percentBatt = 100.0
    else:
        percentBatt = 50.0
    return percentBatt

# "calculate" Ecowitt WH65 battery status in percent
# Battery values 0 (high) => 100% and 1 (low) => 50%
def wh65_batt_to_percent(isBatt):
    if isBatt < 1.0:
        percentBatt = 100.0
    else:
        percentBatt = 50.0
    return percentBatt

# Cloudy sky is warmer that clear sky. Thus sky temperature meassure by IR sensor
# is a good indicator to estimate cloud cover. However IR really meassure the
# temperatura of all the air column above increassing with ambient temperature.
# So it is important include some correction factor:
# From AAG Cloudwatcher formula. Need to improve futher.
# http://www.aagware.eu/aag/cloudwatcher700/WebHelp/index.htm#page=Operational%20Aspects/23-TemperatureFactor-.htm
# Sky temp correction factor. Tsky=Tsky_meassure – Tcorrection
# Formula Tcorrection = (K1 / 100) * (Thr – K2 / 10) + (K3 / 100) * pow((exp (K4 / 1000* Thr)) , (K5 / 100));
# "calculate" cloud cover with skyTemp from a MLX90614 Sensor and outTemp from Weatherstation
# see also: allsky_cloud.py
# https://indiduino.wordpress.com/2013/02/02/meteostation/
# https://lunaticoastro.com/aagcw/TechInfo/SkyTemperatureModel.pdf

# cloud cover helper function
def getsign(d):
    if d < 0:
        return -1.0
    if d == 0:
        return 0.0
    return 1.0

# https://sourceforge.net/projects/mysqmproesp32/
# https://github.com/AllskyTeam/allsky-modules/blob/master/allsky_cloud/allsky_cloud.py
# Readings are only valid at night when dark and sensor is pointed to sky
# During the day readings are meaningless
# clear   : skyTemp <= -8°C
# cloudy  : skyTemp -5°C to 0°C
# overcast: skyTemp > 0°C
def skyTempCorr(outTemp, skyTemp, cloudwatcher_dict):
    K1 = to_int(cloudwatcher_dict.get('k1', 33))
    K2 = to_int(cloudwatcher_dict.get('k2', 0))
    K3 = to_int(cloudwatcher_dict.get('k3', 4))
    K4 = to_int(cloudwatcher_dict.get('k4', 100))
    K5 = to_int(cloudwatcher_dict.get('k5', 100))
    K6 = to_int(cloudwatcher_dict.get('k6', 0))
    K7 = to_int(cloudwatcher_dict.get('k7', 0))

    if abs((K2 / 10 - outTemp)) < 1:
        T67 = getsign(K6) * getsign(outTemp - K2 / 10) * abs((K2 / 10 - outTemp))
    else:
        T67 = K6 / 10 * getsign(outTemp - K2 / 10) * (math.log(abs((K2 / 10 - outTemp))) / math.log(10) + K7 / 100)
    Td = (K1 / 100) * (outTemp - K2 / 10) + (K3 / 100) * pow((math.exp(K4 / 1000 * outTemp)), (K5 / 100)) + T67
    Tsky = skyTemp - Td

    return Tsky

def pws_cloudpercent(outTemp, skyTemp, cloudwatcher_dict):
    CLOUD_TEMP_CLEAR = to_int(cloudwatcher_dict.get('temp_clear', -8))
    CLOUD_TEMP_OVERCAST = to_int(cloudwatcher_dict.get('temp_overcast', 0))

    Tsky = skyTempCorr(outTemp, skyTemp, cloudwatcher_dict)

    if Tsky < CLOUD_TEMP_CLEAR:
        Tsky = CLOUD_TEMP_CLEAR
    elif Tsky > CLOUD_TEMP_OVERCAST:
        Tsky = CLOUD_TEMP_OVERCAST
    cloudcoverPercentage = ((Tsky - CLOUD_TEMP_CLEAR) * 100.0) / (CLOUD_TEMP_OVERCAST - CLOUD_TEMP_CLEAR)
    if cloudcoverPercentage > 100.0:
        cloudcoverPercentage = 100.0

    return to_int(cloudcoverPercentage)

# https://www.dwd.de/DE/service/lexikon/Functions/glossar.html?nn=103346&lv2=101812&lv3=101906
def weathercode_rain(rain10):
    code = pws_weathercode_unknown
    if rain10 is None or to_float(rain10) <= 0.0:
        return code

    rain10 = to_float(rain10)
    if rain10 < 0.5:
        code = pws_weathercode_slight_rain
    elif rain10 < 1.7:
        code = pws_weathercode_moderate_rain
    elif rain10 < 8.3:
        code = pws_weathercode_heavy_rain
    elif rain10 >= 8.3:
        code = pws_weathercode_very_heavy_rain

    return code

def weathercode_thunderstorm(thunderstorm10, rain10):
    code = pws_weathercode_unknown
    if thunderstorm10 is None or to_int(thunderstorm10) <= 0:
        return code

    if rain10 is not None and to_float(rain10) > 0.0:
        code = pws_weathercode_thunderstorm_rain
    else:
        code = pws_weathercode_thunderstorm

    return code

def weathercode_clouds(cloud_percent):
    code = pws_weathercode_unknown

    if cloud_percent is None:
        return code

    cloud_percent = to_float(cloud_percent)
    if cloud_percent < 12.5:
        code = pws_weathercode_clear_sky
    elif cloud_percent <= 37.5:
        code = pws_weathercode_mostly_clear
    elif cloud_percent <= 75.0:
        code = pws_weathercode_partly_cloudy
    elif cloud_percent <= 87.5:
        code = pws_weathercode_mostly_cloudy
    elif cloud_percent <= 100.0:
        code = pws_weathercode_overcast

    return code

# "calculate" own weathercode
def pws_weathercode(cloud_percent, rain10, thunderstorm10):
    weathercode = pws_weathercode_unknown

    # Thunderstorm?
    weathercode = weathercode_thunderstorm(thunderstorm10, rain10)
    if weathercode != pws_weathercode_unknown:
        return weathercode

    # Rain?
    weathercode = weathercode_rain(rain10)
    if weathercode != pws_weathercode_unknown:
        return weathercode

    # Clouds?
    weathercode = weathercode_clouds(cloud_percent)

    return weathercode

# Attempt to calculate whether the precipitation could be snow
def possibly_snow(outTemp, outHumidity, windSpeed, barometer, cloudpercent=None):
    if cloudpercent is not None and cloudpercent < 80.0:
        return 0
    if outTemp is not None and outHumidity is not None and windSpeed is not None and barometer is not None:
        if (outTemp < 0.0 and outHumidity > 70.0) or (outTemp > 0.0 and outHumidity > 70.0 and windSpeed < 10.0 and barometer < 1000.0):
            return 1
        else:
            return 0
    else:
        return 0
