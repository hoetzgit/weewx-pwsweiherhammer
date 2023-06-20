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

# cloud cover helper function
def getsign(d):
    if d < 0:
        return -1.0
    if d == 0:
        return 0.0
    return 1.0

# "calculate" cloud cover with skyTemp from a MLX90614 Sensor and outTemp from Weatherstation
# see also: allsky_cloud.py
# https://indiduino.wordpress.com/2013/02/02/meteostation/ and https://lunaticoastro.com/aagcw/TechInfo/SkyTemperatureModel.pdf
def weewx_cloud_percent(skyambient, skyobject):
    k1 = 33
    k2 = 0
    k3 = 4
    k4 = 100
    k5 = 100
    k6 = 0
    k7 = 0
    clearbelow = -10
    cloudyabove = 5
    
    if abs((k2 / 10.0 - skyambient)) < 1:
        t67 = getsign(k6) * getsign(skyambient - k2 / 10.) * abs((k2 / 10. - skyambient))
    else:
        t67 = k6 / 10. * getsign(skyambient - k2 / 10.) * (math.log(abs((k2 / 10. - skyambient))) / math.log(10) + k7 / 100)

    td = (k1 / 100.) * (skyambient - k2 / 10.) + (k3 / 100.) * pow((math.exp(k4 / 1000. * skyambient)), (k5 / 100.)) + t67

    tsky = skyobject - td
    if tsky < clearbelow:
        tsky = clearbelow
    elif tsky > cloudyabove:
        tsky = cloudyabove
    cloudcoverPercentage = ((tsky - clearbelow) * 100.) / (cloudyabove - clearbelow)
    return cloudcoverPercentage

# "calculate" cloud cover icon with weewx_cloud_percent
def weewx_cloud_icon(cloud_percent):
    if cloud_percent<12.5:
        icon = 0
    elif cloud_percent<=37.5:
        icon = 1
    elif cloud_percent<=75.0:
        icon = 2
    elif cloud_percent<=87.5:
        icon = 3
    else:
        icon = 4
    return icon






