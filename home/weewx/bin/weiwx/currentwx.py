#!/usr/bin/python3
# Copyright (C) 2023 Henry Ott
#
# The service is based on the idea and source code of 
# Johanna Roedenbeck https://github.com/roe-dl
# weatherservices.py https://github.com/roe-dl/weewx-DWD/blob/master/bin/user/weatherservices.py
"""
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

    The service loads data about the current weather from different weather providers.

    Providers:
      Vaisala Xweather (METAR, conditions)
      Brightsky (current, weather)
      DWD (CDC, POI)
      Open-Meteo (ICON-GLOBAL, ICON-D2, ICON-EU, ICON-SEAMLESS, BEST-MATCH)
      OpenWeather
      PWS Weiherhammer

    The goal is to provide the Weiherhammer Skin (Belchertown Skin Fork) with 
    standardized JSON data in a file and in a MQTT Topic. This way it is possible
    to switch within the skin without much effort between the different providers.
    If new data is loaded, the updated topic can be loaded and displayed updated.
"""

VERSION = "0.1b3"

import sys
import os
import threading
import configobj
import csv
import io
import zipfile
import time
import dateutil.parser
import random
import copy
import shutil
import pytz
import math
import paho.mqtt.publish as mqtt_publish
import paho.mqtt.subscribe as mqtt_subscribe
import requests
from requests.exceptions import Timeout
import datetime
from datetime import timezone
import json
from json import JSONDecodeError
from statistics import mean

try:
    # Test for new-style weewx logging by trying to import weeutil.logger
    import weeutil.logger
    import logging
    log = logging.getLogger("weiwx.currentwx")

    def logdbg(msg):
        log.debug(msg)

    def loginf(msg):
        log.info(msg)

    def logerr(msg):
        log.error(msg)

    def logwrn(msg):
        log.warning(msg)

except ImportError:
    # Old-style weewx logging
    import syslog

    def logmsg(level, msg):
        syslog.syslog(level, 'weiwx.currentwx: %s' % msg)

    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)

    def logwrn(msg):
        logmsg(syslog.LOG_WARNING, msg)

import weewx
from weewx.engine import StdService
import weeutil.weeutil
import weewx.accum
import weewx.units
import weewx.wxformulas
import weewx.almanac

for group in weewx.units.std_groups:
    weewx.units.std_groups[group].setdefault('group_coordinate','degree_compass')
weewx.units.obs_group_dict.setdefault('generated','group_time')
weewx.units.obs_group_dict.setdefault('age','group_deltatime')
weewx.units.obs_group_dict.setdefault('day','group_count')
weewx.units.obs_group_dict.setdefault('expired','group_count')
weewx.units.obs_group_dict.setdefault('weathercode','group_count')
weewx.units.obs_group_dict.setdefault('weathercodeKey','group_count')

# rain
weewx.units.MetricUnits['group_rain'] = 'mm'
weewx.units.conversionDict.setdefault('meter',{})
weewx.units.conversionDict.setdefault('cm',{})
weewx.units.conversionDict.setdefault('mm',{})
weewx.units.conversionDict['meter']['cm'] = lambda x : x * 100
weewx.units.conversionDict['meter']['mm'] = lambda x : x * 1000
weewx.units.conversionDict['cm']['mm']    = lambda x : x * 10
weewx.units.conversionDict['cm']['meter'] = lambda x : x * 0.01
weewx.units.conversionDict['mm']['meter'] = lambda x : x * 0.001

SERVICEID='currentwx'

# provider current conditions
# ID               = Provider and model
# aeris-conditions = Vaisala Xweather conditions
# aeris-metar      = Vaisala Xweather METAR ETIC
# bs-current       = Bright Sky current
# bs-weather       = Bright Sky weather
# dwd-cdc          = DWD CDC
# dwd-mosmix       = DWD MOSMIX_L
# dwd-poi          = DWD POI
# om-best-match    = Open-Meteo best-match
# om-icon-combined = Open-Meteo DWD ICON
# om-icon-d2       = Open-Meteo DWD ICON D2
# om-icon-eu       = Open-Meteo DWD ICON EU
# om-icon-seamless = Open-Meteo DWD seamless
# owm              = OpenWeather
# pws              = PWS Weiherhammer

HTMLTMPL = "<p><a href='%s' target='_blank' rel='tooltip' title='%s'>%s</a>%s</p>"

PROVIDER = {
    'aeris-conditions': ('Vaisala Xweather', 'https://www.xweather.com', ' (conditions)'),
    'aeris-metar': ('Vaisala Xweather', 'https://www.xweather.com', ' (METAR ETIC)'),
    'bs-current': ('Bright Sky', 'https://brightsky.dev', ' (current)'),
    'bs-weather': ('Bright Sky', 'https://brightsky.dev', ' (weather)'),
    'dwd-cdc': ('Deutscher Wetterdienst', 'https://www.dwd.de', ' (CDC)'),
    'dwd-mosmix': ('Deutscher Wetterdienst', 'https://www.dwd.de', ' (MOSMIX)'),
    'dwd-poi': ('Deutscher Wetterdienst', 'https://www.dwd.de', ' (POI)'),
    'om-best-match': ('Open-Meteo', 'https://open-meteo.com', ' (best match)'),
    'om-icon-combined': ('Open-Meteo', 'https://open-meteo.com', ' (DWD ICON)'),
    'om-icon-d2': ('Open-Meteo', 'https://open-meteo.com', ' (DWD ICON D2)'),
    'om-icon-eu': ('Open-Meteo', 'https://open-meteo.com', ' (DWD ICON EU)'),
    'om-icon-seamless': ('Open-Meteo', 'https://open-meteo.com', ' (DWD ICON SEAMLESS)'),
    'owm': ('OpenWeather', 'https://openweathermap.org', ''),
    'pws': ('PWS Weiherhammer', 'https://www.weiherhammer-wetter.de', '')
}


# https://www.xweather.com/docs/weather-api/reference/weather-codes
# TODO check this: https://www.woellsdorf-wetter.de/info/symbols.html
#
#              fictitious 
#              numerical
#  AerisCode:  AerisCode   deutsch , english, Belchertown Icon Day, Belchertown Icon Night
#                  0          1         2               3                     4
#
CODECONVERTER = {
            # aeris code
      '::NA': (-1, 'nicht gemeldet', 'not reported', 'unknown.png', 'unknown.png'),
              # TODO: 0..4 ==> use cloudcover if present
      '::CL': (0, 'wolkenlos', 'clear', 'clear-day.png', 'clear-night.png'),
      '::FW': (1, 'heiter', 'mostly clear', 'mostly-clear-day.png', 'mostly-clear-night.png'),
      '::SC': (2, 'wolkig', 'partly cloudy', 'partly-cloudy-day.png', 'partly-cloudy-night.png'),
      '::BK': (3, 'stark bew&ouml;lkt', 'mostly cloudy', 'mostly-cloudy-day.png', 'mostly-cloudy-night.png'),
      '::OV': (4, 'bedeckt', 'overcast', 'cloudy.png', 'cloudy.png'),
       '::A': (5, 'Hagel', 'Hail', 'hail.png', 'hail.png'),
      ':H:A': (6, 'starker Hagel', 'heavy Hail', 'hail.png', 'hail.png'),
      ':L:A': (7, 'leichter Hagel', 'light Hail', 'hail.png', 'hail.png'),
     ':VH:A': (8, 'sehr starker Hagel', 'very heavy Hail', 'hail.png', 'hail.png'),
     ':VL:A': (9, 'sehr leichter Hagel', 'very light Hail', 'hail.png', 'hail.png'),
      '::BD': (10, 'Staubwind', 'Blowing dust', 'blowing-dust.png', 'blowing-dust.png'),
     ':H:BD': (11, 'starker Staubwind', 'heavy Blowing dust', 'blowing-dust.png', 'blowing-dust.png'),
     ':L:BD': (12, 'leichter Staubwind', 'light Blowing dust', 'blowing-dust.png', 'blowing-dust.png'),
    ':VH:BD': (13, 'sehr starker Staubwind', 'very heavy Blowing dust', 'blowing-dust.png', 'blowing-dust.png'),
    ':VL:BD': (14, 'sehr leichter Staubwind', 'very light Blowing dust', 'blowing-dust.png', 'blowing-dust.png'),
      '::BN': (15, 'Sandwind', 'Blowing sand', 'blowing-dust.png', 'blowing-dust.png'),
     ':H:BN': (16, 'starker Sandwind', 'heavy Blowing sand', 'blowing-dust.png', 'blowing-dust.png'),
     ':L:BN': (17, 'leichter Sandwind', 'light Blowing sand', 'blowing-dust.png', 'blowing-dust.png'),
    ':VH:BN': (18, 'sehr starker Sandwind', 'very heavy Blowing sand', 'blowing-dust.png', 'blowing-dust.png'),
    ':VL:BN': (19, 'sehr leichter Sandwind', 'very light Blowing sand', 'blowing-dust.png', 'blowing-dust.png'),
      '::BR': (20, 'Nebel', 'Mist', 'mist.png', 'mist.png'),
     ':H:BR': (21, 'starker Nebel', 'heavy Mist', 'mist.png', 'mist.png'),
     ':L:BR': (22, 'leichter Nebel', 'light Mist', 'mist.png', 'mist.png'),
    ':VH:BR': (23, 'sehr starker Nebel', 'very heavy Mist', 'mist.png', 'mist.png'),
    ':VL:BR': (24, 'sehr leichter Nebel', 'very light Mist', 'mist.png', 'mist.png'),
      '::BS': (25, 'Schneetreiben', 'Blowing snow', 'blowing-snow.png', 'blowing-snow.png'),
     ':H:BS': (26, 'starkes Schneetreiben', 'heavy Blowing snow', 'blowing-snow.png', 'blowing-snow.png'),
     ':L:BS': (27, 'leichtes Schneetreiben', 'light Blowing snow', 'blowing-snow.png', 'blowing-snow.png'),
    ':VH:BS': (28, 'sehr starkes Schneetreiben', 'very heavy Blowing snow', 'blowing-snow.png', 'blowing-snow.png'),
    ':VL:BS': (29, 'sehr leichtes Schneetreiben', 'very light Blowing snow', 'blowing-snow.png', 'blowing-snow.png'),
      '::BY': (30, 'Gischt', 'Blowing spray', 'blowing-spray.png', 'blowing-spray.png'),
     ':H:BY': (31, 'starke Gischt', 'heavy Blowing spray', 'blowing-spray.png', 'blowing-spray.png'),
     ':L:BY': (32, 'leichte Gischt', 'light Blowing spray', 'blowing-spray.png', 'blowing-spray.png'),
    ':VH:BY': (33, 'sehr starke Gischt', 'very heavy Blowing spray', 'blowing-spray.png', 'blowing-spray.png'),
    ':VL:BY': (34, 'sehr leichte Gischt', 'very light Blowing spray', 'blowing-spray.png', 'blowing-spray.png'),
       '::F': (35, 'Nebel', 'Fog', 'fog.png', 'fog.png'),
      ':H:F': (36, 'starker Nebel', 'heavy Fog', 'fog.png', 'fog.png'),
      ':L:F': (37, 'leichter Nebel', 'light Fog', 'fog.png', 'fog.png'),
     ':VH:F': (38, 'sehr starker Nebel', 'very heavy Fog', 'fog.png', 'fog.png'),
     ':VL:F': (39, 'sehr leichter Nebel', 'very light Fog', 'fog.png', 'fog.png'),
      '::FC': (40, 'Trichterwolken', 'Funnel Cloud', 'funnel-cloud.png', 'funnel-cloud.png'),
     ':H:FC': (41, 'starke Trichterwolken', 'heavy Funnel Cloud', 'funnel-cloud.png', 'funnel-cloud.png'),
     ':L:FC': (42, 'leichte Trichterwolken', 'light Funnel Cloud', 'funnel-cloud.png', 'funnel-cloud.png'),
    ':VH:FC': (43, 'sehr starke Trichterwolken', 'very heavy Funnel Cloud', 'funnel-cloud.png', 'funnel-cloud.png'),
    ':VL:FC': (44, 'sehr leichte Trichterwolken', 'very light Funnel Cloud', 'funnel-cloud.png', 'funnel-cloud.png'),
      '::FR': (45, 'Frost', 'Frost', 'frost-day.png', 'frost-night.png'),
     ':H:FR': (46, 'starker Frost', 'heavy Frost', 'frost-day.png', 'frost-night.png'),
     ':L:FR': (47, 'leichter Frost', 'light Frost', 'frost-day.png', 'frost-night.png'),
    ':VH:FR': (48, 'sehr starker Frost', 'very heavy Frost', 'frost-day.png', 'frost-night.png'),
    ':VL:FR': (49, 'sehr leichter Frost', 'very light Frost', 'frost-day.png', 'frost-night.png'),
       '::H': (50, 'Dunst', 'Haze', 'haze.png', 'haze.png'),
      ':H:H': (51, 'starker Dunst', 'heavy Haze', 'haze.png', 'haze.png'),
      ':L:H': (52, 'leichter Dunst', 'light Haze', 'haze.png', 'haze.png'),
     ':VH:H': (53, 'sehr starker Dunst', 'very heavy Haze', 'haze.png', 'haze.png'),
     ':VL:H': (54, 'sehr leichter Dunst', 'very light Haze', 'haze.png', 'haze.png'),
      '::IC': (55, 'Eiskristalle', 'Ice crystals', 'ice-cristals.png', 'ice-cristals.png'),
     ':H:IC': (56, 'starke Eiskristalle', 'heavy Ice crystals', 'ice-cristals.png', 'ice-cristals.png'),
     ':L:IC': (57, 'leichte Eiskristalle', 'light Ice crystals', 'ice-cristals.png', 'ice-cristals.png'),
    ':VH:IC': (58, 'sehr starke Eiskristalle', 'very heavy Ice crystals', 'ice-cristals.png', 'ice-cristals.png'),
    ':VL:IC': (59, 'sehr leichte Eiskristalle', 'very light Ice crystals', 'ice-cristals.png', 'ice-cristals.png'),
      '::IF': (60, 'Eisnebel', 'Ice fog', 'ice-fog.png', 'ice-fog.png'),
     ':H:IF': (61, 'starker Eisnebel', 'heavy Ice fog', 'ice-fog.png', 'ice-fog.png'),
     ':L:IF': (62, 'leichter Eisnebel', 'light Ice fog', 'ice-fog.png', 'ice-fog.png'),
    ':VH:IF': (63, 'sehr starker Eisnebel', 'very heavy Ice fog', 'ice-fog.png', 'ice-fog.png'),
    ':VL:IF': (64, 'sehr leichter Eisnebel', 'very light Ice fog', 'ice-fog.png', 'ice-fog.png'),
      '::IP': (65, 'Graupel', 'Ice pellets / Sleet', 'sleet.png', 'sleet.png'),
     ':H:IP': (66, 'starker Graupel', 'heavy Ice pellets / Sleet', 'sleet.png', 'sleet.png'),
     ':L:IP': (67, 'leichter Graupel', 'light Ice pellets / Sleet', 'sleet.png', 'sleet.png'),
    ':VH:IP': (68, 'sehr starker Graupel', 'very heavy Ice pellets / Sleet', 'sleet.png', 'sleet.png'),
    ':VL:IP': (69, 'sehr leichter Graupel', 'very light Ice pellets / Sleet', 'sleet.png', 'sleet.png'),
       '::K': (70, 'Rauch', 'Smoke', 'smoke.png', 'smoke.png'),
      ':H:K': (71, 'starker Rauch', 'heavy Smoke', 'smoke.png', 'smoke.png'),
      ':L:K': (72, 'leichter Rauch', 'light Smoke', 'smoke.png', 'smoke.png'),
     ':VH:K': (73, 'sehr starker Rauch', 'very heavy Smoke', 'smoke.png', 'smoke.png'),
     ':VL:K': (74, 'sehr leichter Rauch', 'very light Smoke', 'smoke.png', 'smoke.png'),
       '::L': (75, 'Nieselregen', 'Drizzle', 'drizzle.png', 'drizzle.png'),
      ':H:L': (76, 'starker Nieselregen', 'heavy Drizzle', 'drizzle.png', 'drizzle.png'),
      ':L:L': (77, 'leichter Nieselregen', 'light Drizzle', 'drizzle.png', 'drizzle.png'),
     ':VH:L': (78, 'sehr starker Nieselregen', 'very heavy Drizzle', 'drizzle.png', 'drizzle.png'),
     ':VL:L': (79, 'sehr leichter Nieselregen', 'very light Drizzle', 'drizzle.png', 'drizzle.png'),
       '::R': (80, 'Regen', 'Rain', 'rain.png', 'rain.png'),
      ':H:R': (81, 'starker Regen', 'heavy Rain', 'rain.png', 'rain.png'),
      ':L:R': (82, 'leichter Regen', 'light Rain', 'light-rain.png', 'light-rain.png'),
     ':VH:R': (83, 'sehr starker Regen', 'very heavy Rain', 'rain.png', 'rain.png'),
     ':VL:R': (84, 'sehr leichter Regen', 'very light Rain', 'light-rain.png', 'light-rain.png'),
      '::RS': (85, 'Schneeregen', 'Rain/snow mix', 'rain-and-snow.png', 'rain-and-snow.png'),
     ':H:RS': (86, 'starker Schneeregen', 'heavy Rain/snow mix', 'rain-and-snow.png', 'rain-and-snow.png'),
     ':L:RS': (87, 'leichter Schneeregen', 'light Rain/snow mix', 'rain-and-snow.png', 'rain-and-snow.png'),
    ':VH:RS': (88, 'sehr starker Schneeregen', 'very heavy Rain/snow mix', 'rain-and-snow.png', 'rain-and-snow.png'),
    ':VL:RS': (89, 'sehr leichter Schneeregen', 'very light Rain/snow mix', 'rain-and-snow.png', 'rain-and-snow.png'),
      '::RW': (90, 'Regenschauer', 'Rain showers', 'rain-showers-day.png', 'rain-showers-night.png'),
     ':H:RW': (91, 'starke Regenschauer', 'heavy Rain showers', 'rain-showers-day.png', 'rain-showers-night.png'),
     ':L:RW': (92, 'leichte Regenschauer', 'light Rain showers', 'rain-showers-day.png', 'rain-showers-night.png'),
    ':VH:RW': (93, 'sehr starke Regenschauer', 'very heavy Rain showers', 'rain-showers-day.png', 'rain-showers-night.png'),
    ':VL:RW': (94, 'sehr leichte Regenschauer', 'very light Rain showers', 'rain-showers-day.png', 'rain-showers-night.png'),
       '::S': (95, 'Schneefall', 'Snow', 'snow.png', 'snow.png'),
      ':H:S': (96, 'starker Schneefall', 'heavy Snow', 'snow.png', 'snow.png'),
      ':L:S': (97, 'leichter Schneefall', 'light Snow', 'snow.png', 'snow.png'),
     ':VH:S': (98, 'sehr starker Schneefall', 'very heavy Snow', 'snow.png', 'snow.png'),
     ':VL:S': (99, 'sehr leichter Schneefall', 'very light Snow', 'snow.png', 'snow.png'),
      '::SI': (100, 'Schnee-/Graupel-Mix', 'Snow/sleet mix', 'sleet-and-snow.png', 'sleet-and-snow.png'),
     ':H:SI': (101, 'starker Schnee-/Graupel-Mix', 'heavy Snow/sleet mix', 'sleet-and-snow.png', 'sleet-and-snow.png'),
     ':L:SI': (102, 'leichter Schnee-/Graupel-Mix', 'light Snow/sleet mix', 'sleet-and-snow.png', 'sleet-and-snow.png'),
    ':VH:SI': (103, 'sehr starker Schnee-/Graupel-Mix', 'very heavy Snow/sleet mix', 'sleet-and-snow.png', 'sleet-and-snow.png'),
    ':VL:SI': (104, 'sehr leichter Schnee-/Graupel-Mix', 'very light Snow/sleet mix', 'sleet-and-snow.png', 'sleet-and-snow.png'),
            # self made aeris code Start
      '::SR': (105, 'Schneeregenschauer', 'Rain/snow mix showers', 'rain-and-snow-showers-day.png', 'rain-and-snow-showers-night.png'),
     ':H:SR': (106, 'starke Schneeregenschauer', 'heavy Rain/snow mix showers', 'rain-and-snow-showers-day.png', 'rain-and-snow-showers-night.png'),
     ':L:SR': (107, 'leichte Schneeregenschauer', 'light Rain/snow mix showers', 'rain-and-snow-showers-day.png', 'rain-and-snow-showers-night.png'),
      '::SS': (108, 'Graupelschauer', 'Sleet showers', 'sleet-showers-day.png', 'sleet-showers-night.png'),
     ':H:SS': (109, 'starke Graupelschauer', 'heavy Sleet showers', 'sleet-showers-day.png', 'sleet-showers-night.png'),
            # self made aeris code End
      '::SW': (110, 'Schneeschauer', 'Snow showers', 'snow-showers-day.png', 'snow-showers-night.png'),
     ':H:SW': (111, 'starke Schneeschauer', 'heavy Snow showers', 'snow-showers-day.png', 'snow-showers-night.png'),
     ':L:SW': (112, 'leichte Schneeschauer', 'light Snow showers', 'snow-showers-day.png', 'snow-showers-night.png'),
    ':VH:SW': (113, 'sehr starke Schneeschauer', 'very heavy Snow showers', 'snow-showers-day.png', 'snow-showers-night.png'),
    ':VL:SW': (114, 'sehr leichte Schneeschauer', 'very light Snow showers', 'snow-showers-day.png', 'snow-showers-night.png'),
       '::T': (115, 'Gewitter', 'Thunderstorms', 'thunderstorm.png', 'thunderstorm.png'),
      ':H:T': (116, 'starkes Gewitter', 'heavy Thunderstorms', 'thunderstorm.png', 'thunderstorm.png'),
      ':L:T': (117, 'leichtes Gewitter', 'light Thunderstorms', 'thunderstorm.png', 'thunderstorm.png'),
     ':VH:T': (118, 'sehr starkes Gewitter', 'very heavy Thunderstorms', 'thunderstorm.png', 'thunderstorm.png'),
     ':VL:T': (119, 'sehr leichtes Gewitter', 'very light Thunderstorms', 'thunderstorm.png', 'thunderstorm.png'),
            # self made aeris code Start
      '::TH': (120, 'Gewitter mit Hagel', 'Thunderstorm with Hail', 'thunderstorm-and-hail.png', 'thunderstorm-and-hail.png'),
     ':H:TH': (121, 'starkes Gewitter mit Hagel', 'heavy Thunderstorm with Hail', 'thunderstorm-and-hail.png', 'thunderstorm-and-hail.png'),
      '::TL': (122, 'Gewitter mit Nieselregen', 'thunderstorm with drizzle', 'thunderstorm-and-drizzle.png', 'thunderstorm-and-drizzle.png'),
     ':H:TL': (123, 'Gewitter mit starkem Nieselregen', 'thunderstorm with heavy drizzle', 'thunderstorm-and-drizzle.png', 'thunderstorm-and-drizzle.png'),
     ':L:TL': (124, 'Gewitter mit leichtem Nieselregen', 'thunderstorm with light drizzle', 'thunderstorm-and-drizzle.png', 'thunderstorm-and-drizzle.png'),
            # self made aeris code End
      '::TO': (125, 'Tornado', 'Tornado', 'tornado.png', 'tornado.png'),
     ':H:TO': (126, 'starker Tornado', 'heavy Tornado', 'tornado.png', 'tornado.png'),
     ':L:TO': (127, 'leichter Tornado', 'light Tornado', 'tornado.png', 'tornado.png'),
    ':VH:TO': (128, 'sehr starker Tornado', 'very heavy Tornado', 'tornado.png', 'tornado.png'),
    ':VL:TO': (129, 'sehr leichter Tornado', 'very light Tornado', 'tornado.png', 'tornado.png'),
            # self made aeris code Start
      '::TP': (130, 'Gewitter ohne Niederschlag', 'Thunderstorms without Precipitation', 'thunderstorm-without-rain.png', 'thunderstorm-without-rain.png'),
      '::TR': (131, 'Gewitter mit Regen', 'thunderstorm with rain', 'thunderstorm.png', 'thunderstorm.png'),
     ':H:TR': (132, 'Gewitter mit starkem Regen', 'thunderstorm with heavy rain', 'thunderstorm.png', 'thunderstorm.png'),
     ':L:TR': (133, 'Gewitter mit leichtem Regen', 'thunderstorm with light rain', 'thunderstorm-and-drizzle.png', 'thunderstorm-and-drizzle.png'),
      '::UP': (134, 'unbekannter Niederschlag', 'unknown precipitation', 'unknown.png', 'unknown.png'),
     ':H:UP': (135, 'starker unbekannter Niederschlag', 'heavy unknown precipitation', 'unknown.png', 'unknown.png'),
     ':L:UP': (136, 'leichter unbekannter Niederschlag', 'light unknown precipitationMay', 'unknown.png', 'unknown.png'),
    ':VH:UP': (137, 'sehr starker unbekannter Niederschlag', 'very heavy unknown precipitationMay', 'unknown.png', 'unknown.png'),
    ':VL:UP': (138, 'sehr leichter unbekannter Niederschlag', 'very light unknown precipitationMay', 'unknown.png', 'unknown.png'),
            # self made aeris code End
      '::VA': (139, 'Vulkanasche', 'Volcanic ash', 'volcanic-ash.png', 'volcanic-ash.png'),
     ':H:VA': (140, 'starke Vulkanasche', 'heavy Volcanic ash', 'volcanic-ash.png', 'volcanic-ash.png'),
     ':L:VA': (141, 'leichte Vulkanasche', 'light Volcanic ash', 'volcanic-ash.png', 'volcanic-ash.png'),
    ':VH:VA': (142, 'sehr starke Vulkanasche', 'very heavy Volcanic ash', 'volcanic-ash.png', 'volcanic-ash.png'),
    ':VL:VA': (143, 'sehr leichte Vulkanasche', 'very light Volcanic ash', 'volcanic-ash.png', 'volcanic-ash.png'),
            # self made aeris code Start
      '::WG': (144, 'Windböen', 'Wind Gust', 'windgust-day.png', 'windgust-night.png'),
            # self made aeris code End
      '::WM': (145, 'Schnee-/Graupel-/Regen-Mix', 'Wintry Mix', 'wintrymix.png', 'wintrymix.png'),
     ':H:WM': (146, 'starker Schnee-/Graupel-/Regen-Mix', 'heavy Wintry Mix', 'wintrymix.png', 'wintrymix.png'),
     ':L:WM': (147, 'leichter Schnee-/Graupel-/Regen-Mix', 'light Wintry Mix', 'wintrymix.png', 'wintrymix.png'),
    ':VH:WM': (148, 'sehr starker Schnee-/Graupel-/Regen-Mix', 'very heavyWintry Mix', 'wintrymix.png', 'wintrymix.png'),
    ':VL:WM': (149, 'sehr leichter Schnee-/Graupel-/Regen-Mix', 'very light Wintry Mix', 'wintrymix.png', 'wintrymix.png'),
      '::WP': (150, 'Spr&uuml;hregen', 'Waterspouts', 'waterspouts.png', 'waterspouts.png'),
     ':H:WP': (151, 'starker Spr&uuml;hregen', 'heavy Waterspouts', 'waterspouts.png', 'waterspouts.png'),
     ':L:WP': (152, 'leichter Spr&uuml;hregen', 'light Waterspouts', 'waterspouts.png', 'waterspouts.png'),
    ':VH:WP': (153, 'sehr starker Spr&uuml;hregen', 'very heavy Waterspouts', 'waterspouts.png', 'waterspouts.png'),
    ':VL:WP': (154, 'sehr leichter Spr&uuml;hregen', 'very light Waterspouts', 'waterspouts.png', 'waterspouts.png'),
      '::ZF': (155, 'gefrierender Nebel', 'Freezing fog', 'freezing-fog.png', 'freezing-fog.png'),
     ':H:ZF': (156, 'starker gefrierender Nebel', 'heavy Freezing fog', 'freezing-fog.png', 'freezing-fog.png'),
     ':L:ZF': (157, 'leichter gefrierender Nebel', 'light Freezing fog', 'freezing-fog.png', 'freezing-fog.png'),
    ':VH:ZF': (158, 'sehr starker gefrierender Nebel', 'very heavy Freezing fog', 'freezing-fog.png', 'freezing-fog.png'),
    ':VL:ZF': (159, 'sehr leichter gefrierender Nebel', 'very light Freezing fog', 'freezing-fog.png', 'freezing-fog.png'),
      '::ZL': (160, 'gefrierender Nieselregen', 'Freezing drizzle', 'freezing-drizzle.png', 'freezing-drizzle.png'),
     ':H:ZL': (161, 'starker gefrierender Nieselregen', 'heavy Freezing drizzle', 'freezing-drizzle.png', 'freezing-drizzle.png'),
     ':L:ZL': (162, 'leichter gefrierender Nieselregen', 'light Freezing drizzle', 'freezing-drizzle.png', 'freezing-drizzle.png'),
    ':VH:ZL': (163, 'sehr starker gefrierender Nieselregen', 'very heavy Freezing drizzle', 'freezing-drizzle.png', 'freezing-drizzle.png'),
    ':VL:ZL': (164, 'sehr leichter gefrierender Nieselregen', 'very light Freezing drizzle', 'freezing-drizzle.png', 'freezing-drizzle.png'),
      '::ZR': (165, 'gefrierender Regen', 'Freezing rain', 'freezing-rain.png', 'freezing-rain.png'),
     ':H:ZR': (166, 'starker gefrierender Regen', 'heavy Freezing rain', 'freezing-rain.png', 'freezing-rain.png'),
     ':L:ZR': (167, 'leichter gefrierender Regen', 'light Freezing rain', 'freezing-rain.png', 'freezing-rain.png'),
    ':VH:ZR': (168, 'sehr starker gefrierender Regen', 'very heavy Freezing rain', 'freezing-rain.png', 'freezing-rain.png'),
    ':VL:ZR': (169, 'sehr leichter gefrierender Regen', 'very light Freezing rain', 'freezing-rain.png', 'freezing-rain.png'),
      '::ZY': (170, 'gefrierender Spr&uuml;hregen', 'Freezing spray', 'freezing-spray.png', 'freezing-spray.png'),
     ':H:ZY': (171, 'starker gefrierender Spr&uuml;hregen', 'heavy Freezing spray', 'freezing-spray.png', 'freezing-spray.png'),
     ':L:ZY': (172, 'leichter gefrierender Spr&uuml;hregen', 'light Freezing spray', 'freezing-spray.png', 'freezing-spray.png'),
    ':VH:ZY': (173, 'sehr starker gefrierender Spr&uuml;hregen', 'very heavy Freezing spray', 'freezing-spray.png', 'freezing-spray.png'),
    ':VL:ZY': (174, 'sehr leichter gefrierender Spr&uuml;hregen', 'very light Freezing spray', 'freezing-spray.png', 'freezing-spray.png'),
}


@staticmethod
def exception_output(thread_name, e, addcontent=None, debug=1, log_failure=True):
    if log_failure or debug > 0:
        exception_type, exception_object, exception_traceback = sys.exc_info()
        filename = os.path.split(exception_traceback.tb_frame.f_code.co_filename)[1]
        line = exception_traceback.tb_lineno
        logerr("thread '%s': Exception: %s - %s File: %s Line: %s" % (thread_name, e.__class__.__name__, e, str(filename), str(line)))
        if addcontent is not None:
            logerr("thread '%s': Exception: Info: %s" % (thread_name, str(addcontent)))


# @staticmethod
# def get_cloudcover_code(thread_name, cloudcover, weatherprovider='dwd', debug=0, log_success=False, log_failure=True):
    # """ get code for cloud cover percentage """

# # #
# # #                                self-made
# # #  AerisCode: deutsch , english, AerisCode, WMOCode, POICode, DWDCode, Aeris Icon Day, Aeris Icon Night
# # #                0         1         2         3        4        5            6              7
# # #
# # CODECONVERTER = {
      # # '::NA': ('nicht gemeldet','not reported', -1, -1, -1, -1, 'na', 'nan'),
      # # '::CL': ('wolkenlos','clear', 0, 0, 1, 0, 'clear', 'clearn'),
      # # '::FW': ('heiter','mostly clear', 1, 1, 2, 1, 'fair', 'fairn'),
      # # '::SC': ('wolkig','partly cloudy', 2, 2, None, 2, 'pcloudy', 'pcloudyn'),
      # # '::BK': ('bewölkt','mostly cloudy', 3, None, 3, 3, 'pcloudy', 'pcloudyn'),
      # # '::OV': ('bedeckt','overcast', 4, 3, 4, 4, 'cloudy', 'cloudyn'),

    # if debug > 0:
        # logdbg("thread '%s': get_cloudcover weatherprovider '%s' cloudcover '%s %' started" % (thread_name, weatherprovider, str(cloudcover)))

    # if weatherprovider == 'dwd':
        # # https://www.dwd.de/DE/service/lexikon/Functions/glossar.html?lv2=100932&lv3=101016
        # if cloudcover < 12.5:
            # code = '::CL'
        # elif cloudcover <= 37.5:
            # code = '::FW'
        # elif cloudcover <= 75.0:
            # code = '::SC'
        # elif cloudcover <= 87.5:
            # code = '::BK'
        # else:
            # code = '::OV'
    # elif weatherprovider == 'aeris':
        # # https://www.xweather.com/docs/weather-api/reference/weather-codes
        # if cloudcover<=7:
            # code = '::CL'
        # elif cloudcover<=32:
            # code = '::FW'
        # elif cloudcover<=70:
            # code = '::SC'
        # elif cloudcover<=95:
            # code = '::BK'
        # else:
            # code = '::OV'
    # else:
        # code = '::NA'

    # if log_success or debug > 0:
        # logdbg("thread '%s': get_cloudcover finished" % (thread_name))
    # if debug > 2:
        # logdbg("thread '%s': get_cloudcover result %s" % (thread_name, code))
    # return code


#https://www.dwd.de/DE/leistungen/met_verfahren_mosmix/faq/relative_feuchte.html
@staticmethod
def get_humidity(thread_name, temperature, dewpoint, debug=0, log_success=False, log_failure=True):
    try:
        RH = 100*math.exp((17.5043*dewpoint/(241.2+dewpoint))-(17.5043*temperature/(241.2+temperature)))
        return RH
    except Exception as e:
        exception_output(thread_name, e, "TEMP=%f, DEWPT=%f" % (temperature,dewpoint))
        return None


@staticmethod
def get_geocoding(thread_name, station, lang='de', debug=0, log_success=False, log_failure=True):
    """
    Get geocoding data with Open-Meteo Geocoding API

    Inputs:
       station: String to search for. An empty string or only 1 character will return an empty result.
                2 characters will only match exact matching locations. 3 and more characters will perform
                fuzzy matching. The search string can be a location name or a postal code.
    Outputs:
       geocoding result as dict from the first API result or None if errors occurred
    """
    geodata = dict()

    baseurl = 'https://geocoding-api.open-meteo.com/v1/search'
    # String to search for.
    params = '?name=%s' % station
    # The number of search results to return. Up to 100 results can be retrieved.
    # here default 1
    params += '&count=1'
    # By default, results are returned as JSON.
    params += '&format=json'
    # Return translated results, if available, otherwise return english or the native location name. Lower-cased.
    params += '&language=%s' % lang

    url = baseurl + params

    if debug > 0:
        logdbg("thread '%s': get_geocoding station '%s' url '%s' started" % (thread_name, station, url))

    try:
        response, code = request_api(thread_name, url,
                                    debug = debug,
                                    log_success = log_success,
                                    log_failure = log_failure,
                                    text=False)
        if response is not None:
            geodata = json.loads(response)
            if debug > 2:
                logdbg("thread '%s': get_geocoding raw result %s" % (thread_name, station, url, json.dumps(geodata)))
            geodata = geodata['results'][0]
        else:
            if log_failure or debug > 0:
                logerr("thread '%s': Geocoding data raw station '%s' result 'None'" % (thread_name, station))
            return None
    except (Exception, LookupError) as e:
        exception_output(thread_name, e)
        return None

    if log_success or debug > 0:
        logdbg("thread '%s': get_geocoding finished" % (thread_name))
    if debug > 2:
        logdbg("thread '%s': get_geocoding result %s" % (thread_name, json.dumps(geodata)))
    return geodata

@staticmethod
def request_api(thread_name, url, debug=0, log_success=False, log_failure=True, text=False):
    """ download  """

    if debug > 0:
        logdbg("thread '%s': request_api url '%s' started" % (thread_name, url))

    headers={'User-Agent': 'currentwx'}
    response = requests.get(url, headers=headers, timeout=10)
    content_type = response.headers.get("Content-Type")
    if debug > 5:
        logdbg("thread '%s': request_api response content_type '%s'" % (thread_name, str(content_type)))
    if response.status_code >=200 and response.status_code <= 206:
        if log_success or debug > 0:
            loginf("thread '%s': request_api finished with success, http status code %s" % (thread_name, str(response.status_code)))
        if content_type:
            if "application/json" in content_type:
                try:
                    resp = response.json()
                    return resp, response.status_code
                except JSONDecodeError:
                    if log_failure or debug > 0:
                        logerr("thread '%s': request_api finished with error, response could not be serialized" % (thread_name))
                        logerr("thread '%s': request_api url %s" % (thread_name, url))
                    return None, 500 # Internal Server Error
            elif "application/zip" in content_type:
                return response.content, response.status_code
            elif "application/octet-stream" in content_type:
                return response.content, response.status_code
            elif "text/plain" in content_type or "text/html" in content_type:
                return response.text, response.status_code
            else:
                return response.content.decode('utf-8'), response.status_code
        else:
            return response.content.decode('utf-8'), response.status_code
    elif response.status_code == 400:
        logerr("thread '%s': request_api finished with error, http status code %s" % (thread_name, str(response.status_code)))
        logerr("thread '%s': request_api url %s" % (thread_name, url))
        if log_failure or debug > 0:
            if content_type:
                if "application/json" in content_type:
                    reason = response.reason
                    # Open-Meteo returned a JSON error object with a reason
                    if 'reason' in response.json():
                        reason = str(response.json()['reason'])
                    # Brightsky returned a JSON error object with a error description
                    elif 'description' in response.json():
                        reason = str(response.json()['description'])
                    # other services may return a JSON error object with an error message
                    elif 'error' in response.json():
                        reason = str(response.json()['error'])
                    logerr("thread '%s': request_api finished with error '%s - %s'" % (thread_name, str(response.status_code), reason))
                    logerr("thread '%s': request_api url %s" % (thread_name, url))
                    return None, response.status_code
            logerr("thread '%s': request_api finished with error '%s - %s'" % (thread_name, str(response.status_code), response.reason))
            logerr("thread '%s': request_api url %s" % (thread_name, url))
            return None, response.status_code
    else:
        if log_failure or debug > 0:
            logerr("thread '%s': request_api finished with error '%s - %s'" % (thread_name, str(response.status_code), response.reason))
            logerr("thread '%s': request_api url %s" % (thread_name, url))
        return None, response.status_code


@staticmethod
def is_night(thread_name, data, debug=0, log_success=False, log_failure=True):
    """
    Portions based on the dashboard service Copyright 2021 Gary Roderick gjroderick<at>gmail.com
    and distributed under the terms of the GNU Public License (GPLv3).

    To get the correct icon (ww Code 0..4) calculates sun rise and sun set
    and determines whether the dateTime field in the record concerned falls
    outside of the period sun rise to sun set.

    Input:
        data: Result from get_data_api()
    Returns:
        False if the dateTime field is during the daytime otherwise True.
    """
    if debug > 2:
        logdbg("thread '%s': is_night in data %s" % (thread_name, json.dumps(data)))
    try:
        if 'dateTime' in data and data.get('dateTime') is not None:
            dateTime = data['dateTime'][0]
            if dateTime is None:
                if log_failure or debug > 0:
                    logerr("thread '%s': is_night dateTime is invalid!" % (thread_name))
                    logerr("thread '%s': Info %s" % (thread_name, json.dumps(data)))
                return None
        else:
            if log_failure or debug > 0:
                logerr("thread '%s': is_night dateTime is invalid!" % (thread_name))
                logerr("thread '%s': Info %s" % (thread_name, json.dumps(data)))
            return None
        if 'latitude' in data and data.get('latitude') is not None:
            latitude = data['latitude'][0]
            if latitude is None:
                if log_failure or debug > 0:
                    logerr("thread '%s': is_night latitude is invalid!" % (thread_name))
                    logerr("thread '%s': Info %s" % (thread_name, json.dumps(data)))
                return None
        else:
            if log_failure or debug > 0:
                logerr("thread '%s': is_night latitude is invalid!" % (thread_name))
                logerr("thread '%s': Info %s" % (thread_name, json.dumps(data)))
            return None
        if 'longitude' in data and data.get('longitude') is not None:
            longitude = data['longitude'][0]
            if longitude is None:
                if log_failure or debug > 0:
                    logerr("thread '%s': is_night longitude is invalid!" % (thread_name))
                    logerr("thread '%s': Info %s" % (thread_name, json.dumps(data)))
                return None
        else:
            if log_failure or debug > 0:
                logerr("thread '%s': is_night longitude is invalid!" % (thread_name))
                logerr("thread '%s': Info %s" % (thread_name, json.dumps(data)))
            return None

        # Almanac object gives more accurate results if current temp and
        # pressure are provided. Initialise some defaults.
        default_temperature_c = 15.0
        default_barometer_mbar = 1010.0
        default_altitude_m = 0.0 # Default is 0 (sea level)
        # data:
        # 'dateTime': (1676905200, 'unix_epoch', 'group_time')
        # 'outTemp': (10.2, 'degree_C', 'group_temperature')
        # 'barometer': (1021.0, 'hPa', 'group_pressure')

        temperature_c = None
        if 'outTemp' in data and data.get('outTemp') is not None:
            outTemp = data.get('outTemp')[0]
            if outTemp is not None:
                temperature_c = weewx.units.convert(data['outTemp'], 'degree_C')[0]
                if temperature_c is None:
                    if log_failure or debug > 0:
                        logerr("thread '%s': is_night outTemp is invalid! Using defaults." % (thread_name))
                        logerr("thread '%s': Info %s" % (thread_name, json.dumps(data)))
                    temperature_c = default_temperature_c
            else:
                temperature_c = default_temperature_c
        else:
            temperature_c = default_temperature_c

        barometer_mbar = None
        if 'barometer' in data and data.get('barometer') is not None:
            barometer = data.get('barometer')[0]
            if barometer is not None:
                barometer_mbar = weewx.units.convert(data['barometer'], 'mbar')[0]
                if barometer_mbar is None:
                    if log_failure or debug > 0:
                        logerr("thread '%s': is_night barometer is invalid! Using defaults." % (thread_name))
                        logerr("thread '%s': Info %s" % (thread_name, json.dumps(data)))
                    barometer_mbar = default_barometer_mbar
            else:
                barometer_mbar = default_barometer_mbar
        else:
            barometer_mbar = default_barometer_mbar

        altitude_m = None
        if 'altitude' in data and data.get('altitude') is not None:
            altitude = data.get('altitude')[0]
            if altitude is not None:
                altitude_m = weewx.units.convert(data['altitude'], 'meter')[0]
                if altitude_m is None:
                    if log_failure or debug > 0:
                        logerr("thread '%s': is_night altitude is invalid! Using defaults." % (thread_name))
                        logerr("thread '%s': Info %s" % (thread_name, json.dumps(data)))
                    altitude_m = default_altitude_m
            else:
                altitude_m = default_altitude_m
        else:
            altitude_m = default_altitude_m

        # get our almanac object
        almanac = weewx.almanac.Almanac(dateTime,
                                        latitude,
                                        longitude,
                                        altitude_m,
                                        temperature_c,
                                        barometer_mbar)
        # work out sunrise and sunset timestamp so we can determine if it is
        # night or day
        sunrise_ts = almanac.sun.rise.raw
        sunset_ts = almanac.sun.set.raw
        # if we are not between sunrise and sunset it must be night
    except Exception as e:
        exception_output(thread_name, e, json.dumps(data))
        return None
    return not (sunrise_ts < data['dateTime'][0] < sunset_ts)


@staticmethod
def minimize_current_total_mqtt(thread_name, data, debug=0, log_success=False, log_failure=True):
    """
    Minimize the output of weather providers and generate only the required elements that are 
    absolutely necessary for displaying the current weather conditions in the Belchertown skin.
    """
    if debug > 2:
        logdbg("thread '%s': minimize_current_total_mqtt data %s" % (thread_name, json.dumps(data)))
    current = dict()
    current['dateTime'] = data['dateTime'] if ('dateTime' in data and data['dateTime'] is not None) else 0
    current['dateTimeISO'] = data['dateTimeISO'] if ('dateTimeISO' in data and data['dateTimeISO'] is not None) else 'unknown' # better visual monitoring
    current['generated'] = data['generated'] if ('generated' in data and data['generated'] is not None) else 0
    current['generatedISO'] = data['generatedISO'] if ('generatedISO' in data and data['generatedISO'] is not None) else 'unknown' # better visual monitoring
    current['usUnits'] = data['usUnits'] if ('usUnits' in data and data['usUnits'] is not None) else -1
    current['lang'] = data['lang'] if ('lang' in data and data['lang'] is not None) else 'de'
    current['age'] = data['age'] if ('age' in data and data['age'] is not None) else None
    current['expired'] = data['expired'] if ('expired' in data and data['expired'] is not None) else 1
    current['weathericon'] = data['weathericon'] if ('weathericon' in data and data['weathericon'] is not None) else 'unknown.png'
    current['weathertext'] = data['weathertext'] if ('weathertext' in data and data['weathertext'] is not None) else 'N/A'
    current['cloudcover'] = data['cloudcover'] if ('cloudcover' in data and data['cloudcover'] is not None) else None
    current['visibility'] = data['visibility'] if ('visibility' in data and data['visibility'] is not None) else None
    current['weathercode'] = data['weathercode'] if ('weathercode' in data and data['weathercode'] is not None) else -1
    current['weathercodeKey'] = data['weathercodeKey'] if ('weathercodeKey' in data and data['weathercodeKey'] is not None) else 1
    current['weathercodeAeris'] = data['weathercodeAeris'] if ('weathercodeAeris' in data and data['weathercodeAeris'] is not None) else '::NA'
    current['sourceProvider'] = data['sourceProvider'] if ('sourceProvider' in data and data['sourceProvider'] is not None) else 'unknown'
    current['sourceProviderLink'] = data['sourceProviderLink'] if ('sourceProviderLink' in data and data['sourceProviderLink'] is not None) else 'https://www.weiherhammer-wetter.de'
    current['sourceProviderHTML'] = data['sourceProviderHTML'] if ('sourceProviderHTML' in data and data['sourceProviderHTML'] is not None) else HTMLTMPL % ('https://www.weiherhammer-wetter.de', current['sourceProvider'], current['sourceProvider'], '')
    if debug > 2:
        logdbg("thread '%s': minimize_current_total_mqtt current %s" % (thread_name, json.dumps(current)))
    return current


@staticmethod
def minimize_current_total_file(thread_name, data, debug=0, log_success=False, log_failure=True):
    """
    Minimize the output of weather providers and generate only the required elements that are 
    absolutely necessary for displaying the current weather conditions in the Belchertown skin.
    """
    if debug > 2:
        logdbg("thread '%s': minimize_current_total_file data %s" % (thread_name, json.dumps(data)))
    current = dict()
    current['dateTime'] = data['dateTime'] if ('dateTime' in data and data['dateTime'] is not None) else 0
    current['dateTimeISO'] = data['dateTimeISO'] if ('dateTimeISO' in data and data['dateTimeISO'] is not None) else 'unknown' # better visual monitoring
    current['generated'] = data['generated'] if ('generated' in data and data['generated'] is not None) else 0
    current['generatedISO'] = data['generatedISO'] if ('generatedISO' in data and data['generatedISO'] is not None) else 'unknown' # better visual monitoring
    current['lang'] = data['lang'] if ('lang' in data and data['lang'] is not None) else 'de'
    current['age'] = data['age'] if ('age' in data and data['age'] is not None) else None
    current['expired'] = data['expired'] if ('expired' in data and data['expired'] is not None) else 1
    current['weathericon'] = data['weathericon'] if ('weathericon' in data and data['weathericon'] is not None) else 'unknown.png'
    current['weathertext'] = data['weathertext'] if ('weathertext' in data and data['weathertext'] is not None) else 'N/A'
    current['cloudcover'] = data['cloudcover'] if ('cloudcover' in data and data['cloudcover'] is not None) else None
    current['visibility'] = data['visibility'] if ('visibility' in data and data['visibility'] is not None) else None
    current['weathercode'] = data['weathercode'] if ('weathercode' in data and data['weathercode'] is not None) else -1
    current['weathercodeKey'] = data['weathercodeKey'] if ('weathercodeKey' in data and data['weathercodeKey'] is not None) else -1
    current['weathercodeAeris'] = data['weathercodeAeris'] if ('weathercodeAeris' in data and data['weathercodeAeris'] is not None) else '::NA'
    current['sourceProvider'] = data['sourceProvider'] if ('sourceProvider' in data and data['sourceProvider'] is not None) else 'unknown'
    current['sourceProviderLink'] = data['sourceProviderLink'] if ('sourceProviderLink' in data and data['sourceProviderLink'] is not None) else 'https://www.weiherhammer-wetter.de'
    current['sourceProviderHTML'] = data['sourceProviderHTML'] if ('sourceProviderHTML' in data and data['sourceProviderHTML'] is not None) else HTMLTMPL % ('https://www.weiherhammer-wetter.de', 'unknown', '')
    if debug > 2:
        logdbg("thread '%s': minimize_current_total_file current %s" % (thread_name, json.dumps(current)))
    return current


@staticmethod
def minimize_current_result_mqtt(thread_name, data, debug=0, log_success=False, log_failure=True):
    """
    Minimizes the data and provides only the data that should be included in a WeeWX Loop Packet or in a WeeWX Archive Record.
    I don't need text fields in loop or archive data anymore. Icons and texts can be loaded externally by using weathercodeKey.
    """
    strings_to_check = ['sourceUrl', 'sourceId', 'sourceModul', 'sourceProviderLink', 'sourceProviderHTML', 'interval']
    result = data
    if debug > 2:
        logdbg("thread '%s': minimize_current_result_mqtt result full %s" % (thread_name, json.dumps(result)))

    keys_to_remove = [key for key in result.keys() if any(string in key for string in strings_to_check)]
    for key in keys_to_remove:
        result.pop(key)

    if debug > 2:
        logdbg("thread '%s': minimize_current_result_mqtt result minimized %s" % (thread_name, json.dumps(result)))
    return result


@staticmethod
def minimize_current_weewx(thread_name, data, debug=0, log_success=False, log_failure=True):
    """
    Minimizes the data and provides only the data that should be included in a WeeWX Loop Packet or in a WeeWX Archive Record.
    I don't need text fields in loop or archive data anymore. Icons and texts can be loaded externally by using weathercodeKey.
    """
    return data
    # TODO
    current = dict()
    if debug > 2:
        logdbg("thread '%s': minimize_current_weewx data full %s" % (thread_name, json.dumps(data)))

    for obs, value in data.items():
        if str(value).isnumeric():
            current[obs] = data[obs]

    if debug > 2:
        logdbg("thread '%s': minimize_current_weewx data minimized %s" % (thread_name, json.dumps(data)))
    return current


# @staticmethod
# def subscribe_broker(thread_name, mqtt_options, debug=0, log_success=False, log_failure=True):
    # data = None
    # if debug > 0:
        # logdbg("thread '%s': subscribe_broker broker '%s:%s' topic '%s'" % (thread_name, mqtt_options['mqtt_broker'], str(mqtt_options['mqtt_port']), mqtt_options['mqtt_topic']))
    # if debug > 2:
        # logdbg("thread '%s': subscribe_broker mqtt_options %s" % (thread_name, json.dumps(mqtt_options)))

    # try:
        # message = mqtt_subscribe.simple(mqtt_options['mqtt_topic'], hostname=mqtt_options['mqtt_broker'], port=mqtt_options['mqtt_port'],
            # auth={'username': mqtt_options['mqtt_username'], 'password': mqtt_options['mqtt_password']}, keepalive=mqtt_options['mqtt_keepalive'],
            # qos=mqtt_options['mqtt_qos'], retained=mqtt_options['mqtt_retained'], client_id=mqtt_options['mqtt_clientid'])
        # data = message.payload
    # except Exception as e:
        # exception_output(thread_name, e)
        # return False

    # if log_success or debug > 0:
        # loginf("thread '%s': subscribe_broker message received" % (thread_name))
    # if debug > 2:
        # logdbg("thread '%s': subscribe_broker result %s" % (thread_name, json.dumps(data)))
    # return data


@staticmethod
def publish_broker(thread_name, mqtt_options, packet, debug=0, log_success=False, log_failure=True):

    if debug > 0:
        logdbg("thread '%s': publish_broker broker '%s:%s' started" % (thread_name, mqtt_options['mqtt_broker'], str(mqtt_options['mqtt_port'])))
    if debug > 2:
        logdbg("thread '%s': publish_broker mqtt_options %s" % (thread_name, json.dumps(mqtt_options)))
        logdbg("thread '%s': publish_broker raw packet %s" % (thread_name, json.dumps(packet)))

    if weeutil.weeutil.to_bool(mqtt_options.get('mqtt_minimize', False)):
        if thread_name == '%s_total' % SERVICEID:
            data = dict()
            for source_id, value_dict in packet.items():
                data[source_id] = minimize_current_total_mqtt(thread_name, packet[source_id], debug=debug, log_success=log_success, log_failure=log_failure)
        else:
            data = minimize_current_total_mqtt(thread_name, packet, debug=debug, log_success=log_success, log_failure=log_failure)
        packet = data
        if debug > 2:
            logdbg("thread '%s': publish_broker minimized packet %s" % (thread_name, str(packet)))

    for format in mqtt_options['mqtt_formats']:
        if format == 'json':
            ts = weeutil.weeutil.to_int(time.time())
            packet['published'] = ts
            packet['publishedISO'] = get_isodate_from_timestamp(ts, mqtt_options['timezone'])
            value = json.dumps(packet)
            topic = mqtt_options['mqtt_topic']
            extension = mqtt_options.get('topic_json_extension', 'loop')
            if extension != '':
                topic += '/' + extension
            if debug > 2:
                logdbg("thread '%s': publish_broker json '%s:%s' topic '%s'" % (thread_name, mqtt_options['mqtt_broker'], str(mqtt_options['mqtt_port']), topic))
                logdbg("thread '%s': publish_broker json value '%s'" % (thread_name, json.dumps(value)))
            try:
                mqtt_publish.single(topic, value, hostname=mqtt_options['mqtt_broker'], port=mqtt_options['mqtt_port'],
                    auth={'username': mqtt_options['mqtt_username'], 'password': mqtt_options['mqtt_password']}, keepalive=mqtt_options['mqtt_keepalive'],
                    qos=mqtt_options['mqtt_qos'], retain=mqtt_options['mqtt_retain'], client_id=mqtt_options['mqtt_clientid'])
            except Exception as e:
                exception_output(thread_name, e)
                return False
        if format == 'keyvalue':
            if debug > 2:
                logdbg("thread '%s': publish_broker keyvalue '%s:%s' topic '%s'" % (thread_name, mqtt_options['mqtt_broker'], str(mqtt_options['mqtt_port']), mqtt_options['mqtt_topic']))
            for key, value in packet.items():
                try:
                    if value is None:
                        value = " " # TODO The publisher does not send NULL or "" values
                    topic = mqtt_options['mqtt_topic'] + '/' + str(key)
                    if debug > 2:
                        logdbg("thread '%s': publish_broker keyvalue %s=%s" % (thread_name, topic, str(value)))
                    mqtt_publish.single(topic, value, hostname=mqtt_options['mqtt_broker'], port=mqtt_options['mqtt_port'],
                        auth={'username': mqtt_options['mqtt_username'], 'password': mqtt_options['mqtt_password']}, keepalive=mqtt_options['mqtt_keepalive'],
                        qos=mqtt_options['mqtt_qos'], retain=mqtt_options['mqtt_retain'], client_id=mqtt_options['mqtt_clientid'])
                except Exception as e:
                    exception_output(thread_name, e, 'payload %s' % json.dumps(value))
                    return False

    if log_success or debug > 0:
        loginf("thread '%s': publish_broker message published" % (thread_name))
    return True


@staticmethod
def publish_file(thread_name, file_options, packet, debug=0, log_success=False, log_failure=True):

    if debug > 0:
        logdbg("thread '%s': publish_file file '%s'" % (thread_name, file_options['file_filename']))

    if debug > 2:
        logdbg("thread '%s': publish_file file_options %s" % (thread_name, json.dumps(file_options)))
        logdbg("thread '%s': publish_file raw packet %s" % (thread_name, json.dumps(packet)))

    if file_options.get('file_minimize', False):
        if thread_name == '%s_total' % SERVICEID:
            data = dict()
            for source_id, value_dict in packet.items():
                data[source_id] = minimize_current_total_file(thread_name, packet[source_id], debug=debug, log_success=log_success, log_failure=log_failure)
        else:
            data = minimize_current_total_file(thread_name, packet, debug=debug, log_success=log_success, log_failure=log_failure)
        packet = data
        if debug > 2:
            logdbg("thread '%s': publish_file minimized packet %s" % (thread_name, str(packet)))

    for format in file_options['file_formats']:
        if format == 'json':
            ts = weeutil.weeutil.to_int(time.time())
            packet['published'] = ts
            packet['publishedISO'] = get_isodate_from_timestamp(ts, file_options['timezone'])
            tmpname = file_options['file_filename'] + '.tmp'
            try:
                directory = os.path.dirname(tmpname)
                if not os.path.exists(directory):
                    os.makedirs(directory)
                with open(tmpname, "w") as f:
                    # raw
                    #f.write(json.dumps(packet))
                    # formatted
                    f.write(json.dumps(packet, indent=4))
                    f.flush()
                    os.fsync(f.fileno())
                if debug > 1:
                    loginf("thread '%s': publish_file wrote packet to file: '%s'" % (thread_name, tmpname))
                # move it to filename
                shutil.move(tmpname, file_options['file_filename'])
                if debug > 1:
                    loginf("thread '%s': publish_file moved '%s' to '%s'" % (thread_name, tmpname, file_options['file_filename']))
            except OSError as e:
                exception_output(thread_name, e)
                return False
            except Exception as e:
                exception_output(thread_name, e)
                return False
        if format == 'keyvalue':
            logerr("thread '%s': publish_file format 'kv' Not yet implemented" % (thread_name))
            return False

    if log_success or debug > 0:
        loginf("thread '%s': publish_file finished" % (thread_name))
    return True


@staticmethod
def to_packet(thread_name, datain, debug=0, log_success=False, log_failure=True, prefix=None):
    dataout = dict()
    try:
        for key in datain:
            try:
                obs = key if prefix is None else prefix + key
                if not isinstance(datain[key], (list, tuple, set, dict)):
                    dataout[obs] = datain[key]
                else:
                    dataout[obs] = datain[key][0]
            except LookupError:
                dataout[obs] = None
    except Exception as e:
        exception_output(thread_name, e, "datain %s" % (json.dumps(datain)))
        return dataout
    return dataout


@staticmethod
def to_unit_system(thread_name, datain, dest_unit_system, debug=0, log_success=False, log_failure=True):
    dataout = dict()
    if debug > 2:
        logdbg("thread '%s': to_unit_system dest unit=%s" % (thread_name, str(dest_unit_system)))
        logdbg("thread '%s': to_unit_system datain %s" % (thread_name, json.dumps(datain)))
    try:
        for key, values in datain.items():
            if key in ('interval', 'usUnits'):
                dataout[key] = datain[key]
                continue
            elif not isinstance(datain[key], (list, tuple, set, dict)):
                dataout[key] = datain[key]
                continue
            elif values[2] == None: # without group
                dataout[key] = datain[key]
                continue
            elif values[0] is None:
                dataout[key] = datain[key]
                continue
            elif values[1] in ('count', 'unix_epoch', 'percent', 'degree_compass'):
                dataout[key] = datain[key]
                continue
            try:
                val = datain[key]
                if debug > 2:
                    logdbg("thread '%s': to_unit_system key=%s val=%s" % (thread_name, str(key), str(val)))
                val = weewx.units.convertStd(val, dest_unit_system)
                if debug > 2:
                    logdbg("thread '%s': to_unit_system key=%s val=%s" % (thread_name, str(key), str(val)))
            except (TypeError,ValueError,LookupError,ArithmeticError) as e:
                try:
                    val = datain[key]
                except LookupError:
                    val = (None, None, None)
            dataout[key] = val
        dataout['usUnits'] = (dest_unit_system, None, None)
    except Exception as e:
        exception_output(thread_name, e, "%s - %s" % (key, values))
        return datain
    return dataout


@staticmethod
def has_sections(test_dict):
    """ Checks if one of the values in a dictionary is another dictionary """
    for value in test_dict.values():
        if isinstance(value, dict):
            return True
    return False


@staticmethod
def obfuscate_secrets(input_string):
    sensitive_keywords = ["client_id=", "client_secret=", 'app_id=', 'appid=']
    for keyword in sensitive_keywords:
        start_index = input_string.find(keyword)
        if start_index != -1:
            end_index = input_string.find("&", start_index)
            if end_index == -1:
                end_index = len(input_string)
            length = end_index - start_index - len(keyword)
            masked_data = "X" * length
            input_string = input_string[:start_index + len(keyword)] + masked_data + input_string[end_index:]
    return input_string


@staticmethod
def get_isodate_from_timestamp(timestamp, target='Europe/Berlin', source='UTC'):
    dt = datetime.datetime.fromtimestamp(timestamp, pytz.timezone(source)).astimezone(pytz.timezone(target))
    return dt.isoformat(sep="T", timespec="seconds")

# ============================================================================
#
# Class AbstractThread
#
# ============================================================================
class AbstractThread(threading.Thread):

    def __init__(self, name, thread_dict=None, debug=0, log_success=False, log_failure=True, threads=None):

        super(AbstractThread,self).__init__(name=name)

        self.running = False
        self.lock = threading.Lock()
        self.threading_event = threading.Event()
        self.threading_event.clear()
        self.debug = debug
        self.log_success = log_success
        self.log_failure = log_failure
        self.data_temp = dict()
        self.data_result = dict()
        self.interval_get = 300
        self.interval_push = 30

    def get_data_result(self):
        """ get buffered data """
        try:
            self.lock.acquire()
            data = self.data_result
        finally:
            self.lock.release()
        return data


    def get_config(self):
        """ get thread config data """
        try:
            self.lock.acquire()
            config = self.config
        finally:
            self.lock.release()
        return config


    def get_last_prepare_ts(self):
        """ get last prepare saved timestamp """
        try:
            self.lock.acquire()
            last_prepare_ts = self.last_prepare_ts
        finally:
            self.lock.release()
        return last_prepare_ts


    #
    #                     fictitious 
    #                     numerical
    #  weathercodeAeris:  AerisCode   deutsch , english, Belchertown Icon Day, Belchertown Icon Night
    #                         0          1         2               3                     4
    #
    # CODECONVERTER = {
    #      '::NA': (-1, 'nicht gemeldet', 'not reported', 'unknown.png', 'unknown.png'),
    # return: (text_de, text_en, icon)
    def get_icon_and_text(self, data, night=0, debug=0, log_success=False, log_failure=True, weathertext_en=None):
        if night is None:
            night = 0
        try:
            # using only ':xx:xx' without Aeris intensity codes
            aeriscode_l = str(data['weathercodeAeris'][0]).split(':')
            aeriscode = ':%s:%s' % (aeriscode_l[1], aeriscode_l[2])
            x = CODECONVERTER[aeriscode]
            icon = x[4] if night else x[3]
            icon = os.path.join(self.icon_path_belchertown, icon)
            text_de = x[1]
            text_en = x[2] if weathertext_en is None else weathertext_en # if original Aeris use weather
            weathercode = x[0] # only for Aeris 
        except (LookupError,TypeError) as e:
            exception_output(self.name, e)
            #logerr("thread '%s': get_icon_and_text data %s" % (self.name, json.dumps(data)))
            #logerr("thread '%s': get_icon_and_text weathercode %s" % (self.name, str(data.get('weathercodeAeris', 'N/A'))))
            icon = 'unknown.png'
            icon = os.path.join(self.icon_path_belchertown, icon)
            text_de = 'Text nicht verfügbar'
            text_en = 'Text not available'
            weathercode = -1 # only for Aeris 
        return (text_de, text_en, icon, weathercode)


    def prepare_result(self, data, unitsystem, source_id, lang='de', debug=0, log_success=False, log_failure=True):
        """ prepare current weather data record for publishing  """

        if not len(data) > 0:
            return data
        data_temp = data
        try:
            if self.debug > 2:
                logdbg("thread '%s': prepare_result in data_temp %s" %(self.name, json.dumps(data_temp)))
            if data_temp.get('sourceProvider') is None:
                data_temp['sourceProvider'] = (PROVIDER[source_id][0], None, None)
            if data_temp.get('sourceProviderLink') is None:
                data_temp['sourceProviderLink'] = (PROVIDER[source_id][1], None, None)
            if data_temp.get('sourceProviderHTML') is None:
                data_temp['sourceProviderHTML'] = (HTMLTMPL % (PROVIDER[source_id][1], PROVIDER[source_id][0], PROVIDER[source_id][0], PROVIDER[source_id][2]), None, None)
            if data_temp.get('sourceModul') is None:
                data_temp['sourceModul'] = (self.name, None, None)
            if source_id is not None:
                data_temp['sourceId'] = (source_id, None, None)
            data_temp['lang'] = (lang, None, None)
            night = is_night(self.name, data_temp, debug=debug, log_success=log_success, log_failure=log_failure)
            data_temp['day'] = (0 if night else 1, 'count', 'group_count')

            # return (text_de, text_en, icon, weathercode)
            wxdata = ['Text nicht verfügbar', 'Text not available', 'unknown.png']
            if self.provider == 'aeris':
                weathertext_en = data.get('weather')
                if weathertext_en is not None:
                    weathertext_en = weathertext_en[0]
                wxdata = self.get_icon_and_text(data_temp, night=night, debug=debug, log_success=log_success, log_failure=log_failure, weathertext_en=weathertext_en)
                data_temp['weathercode'] = (weeutil.weeutil.to_int(wxdata[3]), 'count', 'group_count')
            else:
                wxdata = self.get_icon_and_text(data_temp, night=night, debug=debug, log_success=log_success, log_failure=log_failure, weathertext_en=None)

            data_temp['weathercodeKey'] = (weeutil.weeutil.to_int(wxdata[3]), 'count', 'group_count')
            data_temp['weathericon'] = (wxdata[2], None, None)
            if lang == "en":
                data_temp['weathertext'] = (wxdata[1], None, None)
            else:
                data_temp['weathertext'] = (wxdata[0], None, None)

            dateTime = None
            generated = None
            if 'dateTime' in data_temp:
                dateTime = data_temp.get('dateTime')
            if 'generated' in data_temp:
                generated = data_temp.get('generated')

            if generated is not None:
                generated = weeutil.weeutil.to_int(generated[0])
                if generated is not None:
                    data_temp['generated'] = (generated, 'unix_epoch', 'group_time') # convert all generated to int
                    data_temp['expired'] = (1 if ((weeutil.weeutil.to_int(time.time() - generated > self.expired) or self.expired is None)) else 0, 'count', 'group_count')
                    if not 'generatedISO' in data_temp:
                        data_temp['generatedISO'] = (get_isodate_from_timestamp(generated, self.timezone), None, None)

            if dateTime is not None:
                dateTime = weeutil.weeutil.to_int(dateTime[0])
                if dateTime is not None:
                    data_temp['dateTime'] = (dateTime, 'unix_epoch', 'group_time') # convert all dateTime to int
                    if not 'dateTimeISO' in data_temp:
                        data_temp['dateTimeISO'] = (get_isodate_from_timestamp(dateTime, self.timezone), None, None)
                if generated is not None:
                    data_temp['age'] = (weeutil.weeutil.to_int(dateTime - generated), 'second', 'group_deltatime')

            data_temp = to_unit_system(self.name, data_temp, unitsystem, debug=debug, log_success=log_success, log_failure=log_failure)

            if self.debug > 2:
                logdbg("thread '%s': prepare_result out data_temp %s" %(self.name, json.dumps(data_temp)))
        except Exception as e:
            exception_output(self.name, e)
        self.last_prepare_ts = weeutil.weeutil.to_int(time.time())
        return data_temp


    def publish_result_mqtt(self):
        """ publish current weather data record to MQTT Broker """
        mqttout_dict = self.config.get('mqtt_out', configobj.ConfigObj())
        debug = weeutil.weeutil.to_int(mqttout_dict.get('debug', self.debug))
        log_success = weeutil.weeutil.to_bool(mqttout_dict.get('log_success', self.log_success))
        log_failure = weeutil.weeutil.to_bool(mqttout_dict.get('log_failure', self.log_failure))

        if debug > 1:
            logdbg("thread '%s': publish_result_mqtt started" % (self.name))
        if debug > 2:
            logdbg("thread '%s': publish_result_mqtt config %s" % (self.name, json.dumps(mqttout_dict)))

        if not weeutil.weeutil.to_bool(mqttout_dict.get('enable', False)):
            if log_success or debug > 0:
                loginf("thread '%s': publish_result_mqtt is diabled. Enable it in the [mqtt_out] section of station %s" %(self.name, self.station))
            return False

        if len(self.data_result) < 1:
            if log_failure or debug > 0:
                logwrn("thread '%s': publish_result_mqtt there are no result data available. Abort." %(self.name))
            return False

        # unit system
        unit_system = None
        unitsystem = None
        u_s = mqttout_dict.get('unit_system', self.unit_system)
        if u_s is not None:
            u_s = str(u_s).upper()
            if u_s in('US', 'METRIC', 'METRICWX'):
                unit_system = u_s
                if unit_system == 'US': unitsystem = weewx.US
                elif unit_system == 'METRIC': unitsystem = weewx.METRIC
                elif unit_system == 'METRICWX': unitsystem = weewx.METRICWX

        # lang
        lang = mqttout_dict.get('lang', self.lang)
        if lang is not None:
            lang = str(lang).lower()
            if lang not in('de', 'en'):
                lang = None

        # check required parameter
        if unitsystem is None or unit_system is None:
            if log_failure or debug > 0:
                logerr("thread '%s': publish_result_mqtt required 'unit_system' is not configured. Configure 'unit_system = US/METRIC/METRICWX' in the [mqtt_out] section of station %s" %(self.name, self.station))
            return False
        if lang is None:
            if log_failure or debug > 0:
                logerr("thread '%s': publish_result_mqtt required 'lang' is not configured. Configure 'lang = de/en' in the [mqtt_out] section of station %s" %(self.name, self.station))
            return False

        try:
            # MQTT options
            mqtt_options = dict()
            basetopic = mqttout_dict.get('basetopic', self.name)
            topic = mqttout_dict.get('topic', self.name)
            if basetopic is None or basetopic == '':
                if log_failure or debug > 0:
                    logerr("thread '%s': publish_result_mqtt required 'basetopic' is not valid. Station %s" %(self.name, self.station))
                return False
            if topic is None or topic == '':
                if log_failure or debug > 0:
                    logerr("thread '%s': publish_result_mqtt required 'topic' is not valid. Station %s" %(self.name, self.station))
                return False
            topic = "%s/%s" % (basetopic, topic)
            mqtt_options['mqtt_topic'] = topic
            mqtt_options['mqtt_broker'] = mqttout_dict.get('broker', 'localhost')
            mqtt_options['mqtt_port'] = weeutil.weeutil.to_int(mqttout_dict.get('port', 1883))
            mqtt_options['mqtt_username'] = mqttout_dict.get('username', 'weewx')
            mqtt_options['mqtt_password'] = mqttout_dict.get('password', 'weewx')
            mqtt_options['mqtt_keepalive'] = weeutil.weeutil.to_int(mqttout_dict.get('keepalive', 60))
            mqtt_options['mqtt_qos'] = weeutil.weeutil.to_int(mqttout_dict.get('qos', 0))
            mqtt_options['mqtt_clientid'] = mqttout_dict.get('clientid')
            if mqtt_options['mqtt_clientid'] is None or mqtt_options['mqtt_clientid'] == '':
                mqtt_options['mqtt_clientid'] = "%s-%s" % (self.name, str(random.randint))
            mqtt_options['mqtt_retain'] = weeutil.weeutil.to_bool(mqttout_dict.get('retain', False))
            mqtt_options['mqtt_max_attempts'] = weeutil.weeutil.to_int(mqttout_dict.get('max_attempts', 1))
            mqtt_options['mqtt_formats'] = weeutil.weeutil.option_as_list(mqttout_dict.get('formats', list()))
            mqtt_options['mqtt_minimize'] = weeutil.weeutil.to_bool(mqttout_dict.get('minimize', False))
            mqtt_options['mqtt_topic_json_extension'] = mqttout_dict.get('topic_json_extension', 'loop')
            mqtt_options['timezone'] = self.timezone

            # prepare output
            output = dict()
            data = dict()
            if self.name == '%s_total' % SERVICEID:
                for source_id, value_dict in self.data_result.items():
                    data[source_id] = self.data_result[source_id]
                    output[source_id] = to_packet(self.name, data[source_id], debug=debug, log_success=log_success, log_failure=log_failure)
            else:
                data = self.prepare_result(self.data_result, unitsystem, mqttout_dict.get('source_id', self.source_id), lang=lang, debug=debug, log_success=log_success, log_failure=log_failure)
                output = to_packet(self.name, data, debug=debug, log_success=log_success, log_failure=log_failure)

            if debug > 2:
                logdbg("thread '%s': publish_result_mqtt mqtt_options %s" % (self.name, json.dumps(mqtt_options)))
                logdbg("thread '%s': publish_result_mqtt raw data_result %s" % (self.name, json.dumps(self.data_result)))
                logdbg("thread '%s': publish_result_mqtt converted data %s" % (self.name, json.dumps(data)))
                logdbg("thread '%s': publish_result_mqtt output %s" % (self.name, json.dumps(output)))

            if not publish_broker(self.name, mqtt_options, output, debug=debug, log_success=log_success, log_failure=log_failure):
                if log_failure or debug > 0:
                    logerr("thread '%s': publish_result_mqtt generated an error" % (self.name))
                return False
        except Exception as e:
            exception_output(self.name, e)
            return False

        if log_success or debug > 0:
            loginf("thread '%s': publish_result_mqtt finished" % (self.name))
        return True


    def publish_result_mqtt_prefix(self):
        """ All thread result data is published to the MQTT broker in the form of a loop packet and as key/value values. Here with prefix """

        if self.name != '%s_total' % SERVICEID: return True

        mqttout_dict = self.config.get('mqtt_out', configobj.ConfigObj())
        debug = weeutil.weeutil.to_int(mqttout_dict.get('debug', self.debug))
        log_success = weeutil.weeutil.to_bool(mqttout_dict.get('log_success', self.log_success))
        log_failure = weeutil.weeutil.to_bool(mqttout_dict.get('log_failure', self.log_failure))

        if debug > 1:
            logdbg("thread '%s': publish_result_mqtt_prefix started" % (self.name))
        if debug > 2:
            logdbg("thread '%s': publish_result_mqtt_prefix config %s" % (self.name, json.dumps(mqttout_dict)))

        if not weeutil.weeutil.to_bool(mqttout_dict.get('enable', False)):
            if log_success or debug > 0:
                loginf("thread '%s': publish_result_mqtt_prefix is diabled. Enable it in the [mqtt_out] section [total]" %(self.name))
            return False

        if len(self.data_result) < 1:
            if log_failure or debug > 0:
                logwrn("thread '%s': publish_result_mqtt_prefix there are no result data available. Abort." %(self.name))
            return False

        # unit system
        unit_system = None
        unitsystem = None
        u_s = mqttout_dict.get('unit_system', self.unit_system)
        if u_s is not None:
            u_s = str(u_s).upper()
            if u_s in('US', 'METRIC', 'METRICWX'):
                unit_system = u_s
                if unit_system == 'US': unitsystem = weewx.US
                elif unit_system == 'METRIC': unitsystem = weewx.METRIC
                elif unit_system == 'METRICWX': unitsystem = weewx.METRICWX

        if unit_system is None or unitsystem is None:
            if log_failure or debug > 0:
                logerr("thread '%s': publish_result_mqtt_prefix required unit system is not configured in section [mqtt_out]" % (self.name))
            return False

        generated_max = 0
        output = dict()
        dateTime = weeutil.weeutil.to_int(time.time())
        generated_min = dateTime
        threads = self.threads
        try:
            for thread_name in threads:
                tconfig = threads[thread_name].get_config()
                prefix = tconfig.get('prefix')
                mqttout_dict = tconfig.get('mqtt_out', configobj.ConfigObj())
                if not weeutil.weeutil.to_bool(mqttout_dict.get('enable', False)):
                    if log_success or debug > 0:
                        loginf("thread '%s': publish_result_mqtt_prefix Thread '%s' mqtt_out is diabled. Enable it in the [mqtt_out] section of station %s" %(self.name, thread_name, self.station))
                    continue
                # get collected data
                data_temp = threads[thread_name].get_data_result()
                #logdbg("thread '%s': get_data_resultsPrefix thread '%s' data %s" % (self.name, thread_name, json.dumps(data_temp)))
                if len(data_temp) > 0:
                    source_id = data_temp.get('sourceId')
                    if source_id is not None:
                        data_temp = to_packet(self.name, data_temp, debug=self.debug, log_success=self.log_success, log_failure=self.log_failure, prefix=prefix)
                        us = weeutil.weeutil.to_int(data_temp.get(prefix+'usUnits'))
                        if us != unitsystem:
                            if log_failure or debug > 0:
                                logerr("thread '%s': publish_result_mqtt_prefix Thread '%s' data unit system '%s' differs to configured unit system '%s'" %(self.name, thread_name, str(us), str(unitsystem)))
                            if debug > 2:
                                logerr("thread '%s': publish_result_mqtt_prefix Thread '%s' data %s" %(self.name, thread_name, json.dumps(data_temp)))
                            continue
                        generated = data_temp.get(prefix+'generated')
                        if generated is not None:
                            generated = weeutil.weeutil.to_int(generated)
                            generated_max = max(generated_max, generated)
                            generated_min = min(generated_min, generated)
                            data_temp[prefix+'age'] = weeutil.weeutil.to_int(dateTime - generated)
                        data_temp = minimize_current_result_mqtt(self.name, data_temp, debug=self.debug, log_success=self.log_success, log_failure=self.log_failure)
                        output.update(data_temp)
                    elif log_failure or debug > 0:
                        logerr("thread '%s': publish_result_mqtt_prefix Thread '%s' data has no valid 'source_id'" % (self.name, thread_name))
                elif log_failure or debug > 0:
                    logerr("thread '%s': publish_result_mqtt_prefix Thread '%s' has no valid result data" % (self.name, thread_name))

            data_temp['dateTime'] = dateTime
            # data_temp['dateTimeISO'] = (get_isodate_from_timestamp(dateTime, self.timezone), None, None)
            # data_temp['generatedMax'] = (generated_max, 'unix_epoch', 'group_time')
            # data_temp['generatedMaxISO'] = (get_isodate_from_timestamp(generated_max, self.timezone), None, None)
            # data_temp['generatedMin'] = (generated_min, 'unix_epoch', 'group_time')
            # data_temp['generatedMinISO'] = (get_isodate_from_timestamp(generated_min, self.timezone), None, None)
            data_temp['dateTimeISO'] = get_isodate_from_timestamp(dateTime, self.timezone)
            data_temp['generatedMax'] = generated_max
            data_temp['generatedMaxISO'] = get_isodate_from_timestamp(generated_max, self.timezone)
            data_temp['generatedMin'] = generated_min
            data_temp['generatedMinISO'] = get_isodate_from_timestamp(generated_min, self.timezone)
            data_temp['usUnits'] = unitsystem
            output.update(data_temp)
        except Exception as e:
            exception_output(self.name, e)

        if log_success or debug > 0:
            loginf("thread '%s': publish_result_mqtt_prefix number of records processed: %d" % (self.name, len(output)))
        if debug > 2:
            logdbg("thread '%s': publish_result_mqtt_prefix result %s" % (self.name, json.dumps(output)))

        # MQTT options
        mqtt_options = dict()
        basetopic = mqttout_dict.get('basetopic', self.name)
        topic = 'result' # static
        if basetopic is None or basetopic == '':
            if log_failure or debug > 0:
                logerr("thread '%s': publish_result_mqtt_prefix required 'basetopic' is not valid. Station %s" %(self.name, self.station))
            return False
        if topic is None or topic == '':
            if log_failure or debug > 0:
                logerr("thread '%s': publish_result_mqtt_prefix required 'topic' is not valid. Station %s" %(self.name, self.station))
            return False
        topic = "%s/%s" % (basetopic, topic)
        mqtt_options['mqtt_topic'] = topic
        mqtt_options['mqtt_broker'] = mqttout_dict.get('broker', 'localhost')
        mqtt_options['mqtt_port'] = weeutil.weeutil.to_int(mqttout_dict.get('port', 1883))
        mqtt_options['mqtt_username'] = mqttout_dict.get('username', 'weewx')
        mqtt_options['mqtt_password'] = mqttout_dict.get('password', 'weewx')
        mqtt_options['mqtt_keepalive'] = weeutil.weeutil.to_int(mqttout_dict.get('keepalive', 60))
        mqtt_options['mqtt_qos'] = weeutil.weeutil.to_int(mqttout_dict.get('qos', 0))
        mqtt_options['mqtt_clientid'] = mqttout_dict.get('clientid')
        if mqtt_options['mqtt_clientid'] is None or mqtt_options['mqtt_clientid'] == '':
            mqtt_options['mqtt_clientid'] = "%s-%s" % (self.name, str(random.randint))
        mqtt_options['mqtt_retain'] = weeutil.weeutil.to_bool(mqttout_dict.get('retain', False))
        mqtt_options['mqtt_max_attempts'] = weeutil.weeutil.to_int(mqttout_dict.get('max_attempts', 1))
        mqtt_options['mqtt_formats'] = ('json','keyvalue') # static
        mqtt_options['mqtt_minimize'] = False # static
        mqtt_options['mqtt_topic_json_extension'] = 'loop' # static
        mqtt_options['timezone'] = self.timezone

        if debug > 2:
            logdbg("thread '%s': publish_result_mqtt_prefix mqtt_options %s" % (self.name, json.dumps(mqtt_options)))
            logdbg("thread '%s': publish_result_mqtt_prefix output %s" % (self.name, json.dumps(output)))

        if not publish_broker(self.name, mqtt_options, output, debug=debug, log_success=log_success, log_failure=log_failure):
            if log_failure or debug > 0:
                logerr("thread '%s': publish_result_mqtt_prefix generated an error" % (self.name))
            return False

        if log_success or debug > 0:
            loginf("thread '%s': publish_result_mqtt_prefix finished" % (self.name))
        return True


    def publish_result_file(self):
        """ publish current weather data record to a file. Currently only JSON files supported. """

        fileout_dict = self.config.get('file_out', configobj.ConfigObj())
        debug = weeutil.weeutil.to_int(fileout_dict.get('debug', self.debug))
        log_success = weeutil.weeutil.to_bool(fileout_dict.get('log_success', self.log_success))
        log_failure = weeutil.weeutil.to_bool(fileout_dict.get('log_failure', self.log_failure))

        if debug > 1:
            logdbg("thread '%s': publish_result_file started" % (self.name))
        if debug > 2:
            logdbg("thread '%s': publish_result_file config %s" % (self.name, json.dumps(fileout_dict)))

        if not weeutil.weeutil.to_bool(fileout_dict.get('enable', False)):
            if log_success or debug > 0:
                loginf("thread '%s': publish_result_file is diabled. Enable it in the [file_out] section of station %s" %(self.name, self.station))
            return False

        if len(self.data_result) < 1:
            if log_failure or debug > 0:
                logwrn("thread '%s': publish_result_file there are no result data available. Abort." %(self.name))
            return False

        # unit system
        unit_system = None
        unitsystem = None
        u_s = fileout_dict.get('unit_system', self.unit_system)
        if u_s is not None:
            u_s = str(u_s).upper()
            if u_s in('US', 'METRIC', 'METRICWX'):
                unit_system = u_s
                if unit_system == 'US': unitsystem = weewx.US
                elif unit_system == 'METRIC': unitsystem = weewx.METRIC
                elif unit_system == 'METRICWX': unitsystem = weewx.METRICWX

        # lang
        lang = fileout_dict.get('lang', self.lang)
        if lang is not None:
            lang = str(lang).lower()
            if lang not in('de', 'en'):
                lang = None

        # check required parameter
        if unitsystem is None or unit_system is None:
            if log_failure or debug > 0:
                logerr("thread '%s': publish_result_file required 'unit_system' is not configured. Configure 'unit_system = US/METRIC/METRICWX' in the [mqtt_out] section of station %s" %(self.name, self.station))
            return False
        if lang is None:
            if log_failure or debug > 0:
                logerr("thread '%s': publish_result_file required 'lang' is not configured. Configure 'lang = de/en' in the [mqtt_out] section of station %s" %(self.name, self.station))
            return False

        try:
            # FILE options
            file_options = dict()
            basepath = fileout_dict.get('basepath')
            filename = fileout_dict.get('filename')
            # TODO: check filesystem
            if basepath is None or basepath == '':
                if log_failure or debug > 0:
                    logerr("thread '%s': publish_result_file required 'basepath' is not valid. Station %s" %(self.name, self.station))
                return False
            if filename is None or filename == '':
                if log_failure or debug > 0:
                    logerr("thread '%s': publish_result_file required 'filename' is not valid. Station %s" %(self.name, self.station))
                return False
            filename = "%s/%s" % (basepath, filename)
            file_options['file_filename'] = filename
            file_options['file_max_attempts'] = weeutil.weeutil.to_int(fileout_dict.get('max_attempts', 1))
            file_options['file_formats'] = weeutil.weeutil.option_as_list(fileout_dict.get('formats', list()))
            file_options['file_minimize'] = weeutil.weeutil.to_bool(fileout_dict.get('minimize', False))
            file_options['timezone'] = self.timezone

            # prepare output
            output = dict()
            data = dict()
            if self.name == '%s_total' % SERVICEID:
                for source_id, value_dict in self.data_result.items():
                    data[source_id] = self.data_result[source_id]
                    output[source_id] = to_packet(self.name, data[source_id], debug=debug, log_success=log_success, log_failure=log_failure)
            else:
                data = self.prepare_result(self.data_result, unitsystem, fileout_dict.get('source_id', self.source_id), lang=lang, debug=debug, log_success=log_success, log_failure=log_failure)
                output = to_packet(self.name, data, debug=debug, log_success=log_success, log_failure=log_failure)

            if debug > 2:
                logdbg("thread '%s': publish_result_file file_options %s" % (self.name, json.dumps(file_options)))
                logdbg("thread '%s': publish_result_file raw data_result %s" % (self.name, json.dumps(self.data_result)))
                logdbg("thread '%s': publish_result_file converted data %s" % (self.name, json.dumps(data)))
                logdbg("thread '%s': publish_result_file output %s" % (self.name, json.dumps(output)))

            if not publish_file(self.name, file_options, output, debug=debug, log_success=log_success, log_failure=log_failure):
                if log_failure or debug > 0:
                    logerr("thread '%s': publish_result_file generated an error" % (self.name))
                return False
        except Exception as e:
            exception_output(self.name, e)
            return False

        if log_success or debug > 0:
            loginf("thread '%s': publish_result_file finished" % (self.name))
        #TODO: error handling?
        return True


    def new_result_from_temp(self, oldData=False):
        # prepare data
        if self.debug > 2:
            loginf("thread '%s': new_result_from_temp started." % (self.name))
        try:
            self.lock.acquire()
            if oldData:
                # update dateTime only
                now = weeutil.weeutil.to_int(time.time())
                if self.name == '%s_total' % SERVICEID:
                    for source_id, value_dict in self.data_temp.items():
                        self.data_temp[source_id]['dateTime'] = (now, 'unix_epoch', 'group_time')
                        self.data_temp[source_id]['dateTimeISO'] = (get_isodate_from_timestamp(now, self.timezone), None, None)
                else:
                    self.data_temp['dateTime'] = (now, 'unix_epoch', 'group_time')
                    self.data_temp['dateTimeISO'] = (get_isodate_from_timestamp(now, self.timezone), None, None)
            else:
                if self.name != '%s_total' % SERVICEID:
                    self.data_temp = self.prepare_result(self.data_temp, self.unitsystem, self.source_id, lang=self.lang, debug=self.debug, log_success=self.log_success, log_failure=self.log_failure)
            if self.debug > 2:
                logdbg("thread '%s': new_result_from_temp data_temp %s" % (self.name, json.dumps(self.data_temp)))
            # The external data are prepared and can now be attached to loop or archive data sets.
            self.data_result.update(self.data_temp)
            if self.debug > 2:
                loginf("thread '%s': new_result_from_temp data_result %s" % (self.name, json.dumps(self.data_result)))
        finally:
            self.lock.release()
        if self.log_success or self.debug > 0:
            loginf("thread '%s': new_result_from_temp finished" % (self.name))


    def publish_result_api(self):
        raise NotImplementedError


    def get_data_mqtt(self):
        raise NotImplementedError


    def get_data_file(self):
        raise NotImplementedError


    def get_data_api(self):
        return True


    def get_data_results(self):
        return True


    def run(self):
        """ thread loop """
        self.running = True
        self.data_temp = dict()
        self.data_result = dict()
        self.wait = 0

        if self.log_success or self.debug > 0:
            loginf("thread '%s': starting" % self.name)
        try:
            result_in = weeutil.weeutil.to_bool(self.config.get('result_in', configobj.ConfigObj()).get('enable', False))
            mqtt_in = weeutil.weeutil.to_bool(self.config.get('mqtt_in', configobj.ConfigObj()).get('enable', False))
            mqtt_out = weeutil.weeutil.to_bool(self.config.get('mqtt_out', configobj.ConfigObj()).get('enable', False))
            api_in = weeutil.weeutil.to_bool(self.config.get('api_in', configobj.ConfigObj()).get('enable', False))
            api_out = weeutil.weeutil.to_bool(self.config.get('api_out', configobj.ConfigObj()).get('enable', False))
            file_in = weeutil.weeutil.to_bool(self.config.get('file_in', configobj.ConfigObj()).get('enable', False))
            file_out = weeutil.weeutil.to_bool(self.config.get('file_out', configobj.ConfigObj()).get('enable', False))
            db_in = weeutil.weeutil.to_bool(self.config.get('db_in', configobj.ConfigObj()).get('enable', False))
            db_out = weeutil.weeutil.to_bool(self.config.get('db_out', configobj.ConfigObj()).get('enable', False))

            while self.running:
                # check for stop
                if self.threading_event.is_set():
                    self.data_result = dict()
                    break
                oldData = True
                if time.time() - self.last_get_ts > self.wait:
                    oldData = False
                    self.data_temp = dict()
                    # download data
                    # if mqtt_in:
                        # if not self.get_data_mqtt():
                            # self.data_temp = dict()
                            # self.data_result = dict()
                    if api_in:
                        if not self.get_data_api():
                            self.data_temp = dict()
                            self.data_result = dict()
                    # if file_in:
                        # if not self.get_data_file():
                            # self.data_temp = dict()
                            # self.data_result = dict()
                    if result_in:
                        if not self.get_data_results():
                            self.data_temp = dict()
                            self.data_result = dict()

                if len(self.data_temp) > 0:
                    # The data are now ready
                    self.new_result_from_temp(oldData)

                    # The external data has been prepared and is now distributed according to its configuration.
                    if mqtt_out:
                        self.publish_result_mqtt()
                        if self.name == '%s_total' % SERVICEID:
                            self.publish_result_mqtt_prefix()
                    # if api_out:
                        # self.publish_result_api()
                    if file_out:
                        self.publish_result_file()

                # time to the next interval
                if self.interval_get == 300: # TODO
                    smin = 0.6
                    smax = 1.0
                    p = random.uniform(smin, smax)
                    self.wait = self.interval_get * p
                else:
                    self.wait = self.interval_get

                # wait
                waiting = self.interval_push
                if self.log_success or self.debug > 0:
                    loginf("thread '%s': wait %s s" % (self.name,waiting))
                self.threading_event.wait(waiting)
                self.threading_event.clear()
        except Exception as e:
            self.data_temp = dict()
            self.data_result = dict()
            exception_output(self.name, e)
        finally:
            if self.log_success or self.debug > 0:
                loginf("thread '%s': stopped" % self.name)


    def shutDown(self):
        """ request thread shutdown """
        if self.log_success or self.debug > 0:
            loginf("thread '%s': SHUTDOWN - thread initiated" % self.name)
        self.running = False
        self.threading_event.set()
        self.join(20.0)
        if self.is_alive():
            if self.log_failure or self.debug > 0:
                logerr("thread '%s': Unable to shut down thread" % self.name)
                self = None



# ============================================================================
#
# Class POIthread
#
# ============================================================================
# check: https://www.dwd.de/DE/leistungen/beobachtung/beobachtung.html
class POIthread(AbstractThread):

    OBS = {
        'cloud_cover_total':'cloudcover',
        'dew_point_temperature_at_2_meter_above_ground':'dewpoint',
        'diffuse_solar_radiation_last_hour':'solarRad',
        'dry_bulb_temperature_at_2_meter_above_ground':'outTemp',
        'global_radiation_last_hour':'radiation',
        'height_of_base_of_lowest_cloud_above_station':'cloudbase',
        'horizontal_visibility':'visibility',
        'mean_wind_direction_during_last_10 min_at_10_meters_above_ground':'windDir',
        'mean_wind_speed_during last_10_min_at_10_meters_above_ground':'windSpeed',
        'precipitation_amount_last_hour':'rain',
        'present_weather':'weathercode',
        'pressure_reduced_to_mean_sea_level':'barometer',
        'relative_humidity':'outHumidity',
        'temperature_at_5_cm_above_ground':'extraTemp1',
        'total_snow_depth':'snowDepth',
        'depth_of_new_snow':'snowDepthNew',
        'total_time_of_sunshine_during_last_hour':'sunshineDur',
        'maximum_wind_speed_last_hour':'windGust'
    }


    UNIT = {
        'Grad C': 'degree_C',
        'Grad': 'degree_compass',
        'W/m2': 'watt_per_meter_squared',
        'km/h': 'km_per_hour',
        'h': 'hour',
        'min': 'minute',
        '%': 'percent',
        'km': 'km',
        'm': 'meter',
        'cm': 'cm',
        'mm': 'mm',
        'hPa': 'hPa',
        'CODE_TABLE': 'count'
    }


    # Mapping API presentWeather field to aeris code
    POI_AERIS = {
        -1: '::NA',
         1: '::CL',
         2: '::FW',
         3: '::BK',
         4: '::OV',
         5: '::F',
         6: '::ZF',
         7: ':L:R',
         8: '::R',
         9: ':H:R',
        10: '::ZR',
        11: ':H:ZR',
        12: '::RS',
        13: ':H:RS',
        14: ':L:S',
        15: '::S',
        16: ':H:S',
        17: '::A',
        18: '::RW',
        19: ':H:RW',
        20: '::SR',
        21: ':H:SR',
        22: '::SW',
        23: ':H:SW',
        24: '::SS',
        25: ':H:SS',
        26: '::TP',
        27: '::T',
        28: ':H:T',
        29: '::TH',
        30: ':H:TH',
        31: '::WG'
    }


    def get_aeriscode(self, code):
        """ get aeris weather code from api code """
        try:
            x = self.POI_AERIS[code]
        except (LookupError, TypeError):
            x = self.POI_AERIS[-1]
        return x


    def get_current_obs(self):
        return POIthread.OBS


    def __init__(self, name, thread_dict, debug=0, log_success=False, log_failure=True):

        super(POIthread,self).__init__(name=name, thread_dict=thread_dict, debug=debug, log_success=log_success, log_failure=log_failure)

        self.config = thread_dict.get('config')
        self.debug = weeutil.weeutil.to_int(self.config.get('debug', 0))
        self.log_success = weeutil.weeutil.to_bool(self.config.get('log_success', log_success))
        self.log_failure = weeutil.weeutil.to_bool(self.config.get('log_failure', log_failure))

        if self.debug > 0:
            logdbg("thread '%s': init started" % self.name)
        if self.debug > 2:
            logdbg("thread '%s': init config %s" % (self.name, json.dumps(self.config)))

        self.station = self.config.get('station', 'here')
        self.provider = self.config.get('provider', 'dwd')
        self.model = self.config.get('model', 'poi')
        self.prefix = self.config.get('prefix', 'current_dwd_'+ str(self.model).replace('-', '_') + '_')
        self.source_id = self.config.get('source_id', 'dwd-' + str(self.model).replace('_', '-'))
        self.interval_get = weeutil.weeutil.to_int(self.config.get('interval_get', 300))
        self.interval_push = weeutil.weeutil.to_int(self.config.get('interval_push', 30))
        self.expired = weeutil.weeutil.to_int(self.config.get('expired', 600))
        self.icon_path_belchertown = self.config.get('icon_path_belchertown', '')
        self.timezone = self.config.get('timezone', 'Europe/Berlin')
        self.current_obs = self.get_current_obs()
        self.config_dict = thread_dict.get('config_dict')
        self.engine = thread_dict.get('engine')
        self.lat = weeutil.weeutil.to_float(self.config.get('latitude'))
        self.lon = weeutil.weeutil.to_float(self.config.get('longitude'))
        self.alt = weeutil.weeutil.to_float(self.config.get('altitude'))
        self.data_result = dict()
        self.data_temp = dict()
        self.last_get_ts = 0
        self.last_prepare_ts = 0

        # unit system
        self.unit_system = None
        self.unitsystem = None
        unit_system = self.config.get('unit_system')
        if unit_system is not None:
            unit_system = str(unit_system).upper()
            if unit_system in('US', 'METRIC', 'METRICWX'):
                self.unit_system = unit_system
                if self.unit_system == 'US': self.unitsystem = weewx.US
                elif self.unit_system == 'METRIC': self.unitsystem = weewx.METRIC
                elif self.unit_system == 'METRICWX': self.unitsystem = weewx.METRICWX

        # lang
        self.lang = self.config.get('lang')
        if self.lang is not None:
            self.lang = str(self.lang).lower()
            if self.lang not in('de', 'en'):
                self.lang = None

        weewx.units.obs_group_dict.setdefault(self.prefix+'dateTime','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'generated','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'age','group_deltatime')
        weewx.units.obs_group_dict.setdefault(self.prefix+'day','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'expired','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'weathercode','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'weathercodeKey','group_count')
        for key in POIthread.OBS:
            obstype = POIthread.OBS[key]
            if obstype=='visibility':
                obsgroup = 'group_distance'
            elif obstype=='solarRad':
                obsgroup = 'group_radiation'
            elif obstype=='snowDepthNew':
                obsgroup = 'group_rain'
            elif obstype=='weathercode':
                obsgroup = 'group_count'
            else:
                obsgroup = weewx.units.obs_group_dict.get(obstype)
            if obsgroup:
                weewx.units.obs_group_dict.setdefault(self.prefix+obstype,obsgroup)
        if self.log_success or self.debug > 0:
            loginf("thread '%s': init finished" % self.name)


    @staticmethod
    def to_float(x):
        """ convert value out of the CSV file to float """
        try:
            #if x[0:1]=='--': raise ValueError('no number')
            if x[0:1]=='--': return None
            if ',' in x:
                return float(x.replace(',','.'))
            if '.' in x:
                return float(x)
            return int(x)
        except Exception:
            pass
        return None


    def get_data_api(self):
        """ download and process POI weather data """

        self.data_temp = list()
        apiin_dict = self.config.get('api_in', configobj.ConfigObj())
        debug = weeutil.weeutil.to_int(apiin_dict.get('debug', self.debug))
        log_success = weeutil.weeutil.to_bool(apiin_dict.get('log_success', self.log_success))
        log_failure = weeutil.weeutil.to_bool(apiin_dict.get('log_failure', self.log_failure))
        attempts_max = weeutil.weeutil.to_int(apiin_dict.get('attempts_max', 1))
        attempts_wait = weeutil.weeutil.to_int(apiin_dict.get('attempts_wait', 10))

        if not weeutil.weeutil.to_bool(apiin_dict.get('enable', False)):
            if log_success or debug > 0:
                loginf("thread '%s': get_data_api is diabled. Enable it in the [api_in] section of station %s" %(self.name, self.station))
            return False

        if debug > 0:
            logdbg("thread '%s': get_data_api started" % (self.name))
        if debug > 2:
            logdbg("thread '%s': get_data_api config %s" %(self.name, json.dumps(apiin_dict)))

        # unit system
        unit_system = None
        unitsystem = None
        u_s = apiin_dict.get('unit_system', self.unit_system)
        if u_s is not None:
            u_s = str(u_s).upper()
            if u_s in('US', 'METRIC', 'METRICWX'):
                unit_system = u_s
                if unit_system == 'US': unitsystem = weewx.US
                elif unit_system == 'METRIC': unitsystem = weewx.METRIC
                elif unit_system == 'METRICWX': unitsystem = weewx.METRICWX

        # lang
        lang = apiin_dict.get('lang', self.lang)
        if lang is not None:
            lang = str(lang).lower()
            if lang not in('de', 'en'):
                lang = None

        url = 'https://opendata.dwd.de/weather/weather_reports/poi/'+self.station+'-BEOB.csv'

        attempts = 0
        try:
            while attempts <= attempts_max:
                attempts += 1
                response, code = request_api(self.name, url,
                                            debug = self.debug,
                                            log_success = log_success,
                                            log_failure = log_failure,
                                            text=True)
                if response is not None:
                    attempts = attempts_max + 1
                    response = response.decode('utf-8')
                elif attempts <= attempts_max:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api request_api sent http status code %d" % (self.name, code))
                        loginf("thread '%s': get_data_api request_api next try (%d/%d) in %d seconds" % (self.name, attempts, attempts_max, attempts_wait))
                    time.sleep(attempts_wait)
                else:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api api did not send data" % self.name)
                    return False
        except Exception as e:
            exception_output(self.name, e)
            return False

        self.data_temp = dict()
        ii = 0;
        for ln in csv.reader(response.splitlines(),delimiter=';'):
            if ii==0:
                # column names
                names = ln
            elif ii==1:
                # units
                units = ln
            elif ii==2:
                # german column names
                gnames = ln
            else:
                # data lines
                self.data_temp['dateTime'] = (weeutil.weeutil.to_int(time.time()), 'unix_epoch', 'group_time')
                dt = ln[0].split('.')
                ti = ln[1].split(':')
                d = datetime.datetime(weeutil.weeutil.to_int(dt[2])+2000,weeutil.weeutil.to_int(dt[1]),weeutil.weeutil.to_int(dt[0]),weeutil.weeutil.to_int(ti[0]),weeutil.weeutil.to_int(ti[1]),0,tzinfo=datetime.timezone(datetime.timedelta(),'UTC'))
                self.data_temp['generated'] = (weeutil.weeutil.to_int(d.timestamp()), 'unix_epoch', 'group_time')
                self.data_temp['usUnits'] = (unitsystem, None, None)
                for idx,val in enumerate(ln):
                    if idx==0:
                        self.data_temp['date'] = (val,None,None)
                    elif idx==1:
                        self.data_temp['time'] = (val,None,None)
                        #self.data_temp['tz'] = ('UTC', None, None)
                    else:
                        col = POIthread.OBS.get(names[idx])
                        if debug > 2:
                            logdbg("thread '%s': get_data_api read poi=%s col=%s" % (self.name, names[idx], col))
                        if col is None:
                            continue
                        unit = POIthread.UNIT.get(units[idx],units[idx])
                        if unit=='degree_C':
                            grp = 'group_temperature'
                        elif unit=='percent':
                            grp = 'group_percent'
                        else:
                            grp = weewx.units.obs_group_dict.get(self.prefix+col)
                        if debug > 2:
                            logdbg("thread '%s': get_data_api read poi=%s col=%s val=%s unit=%s group=%s" % (self.name, names[idx], col, str(val), str(unit), str(grp)))
                        if col and val is not None:
                            self.data_temp[col] = (POIthread.to_float(val),
                                      unit,
                                      grp)

                if self.alt is not None:
                    self.data_temp['altitude'] = (self.alt,'meter','group_altitude')

                if self.lat is not None and self.lon is not None:
                    self.data_temp['latitude'] = (self.lat,'degree_compass','group_coordinate')
                    self.data_temp['longitude'] = (self.lon,'degree_compass','group_coordinate')
                    night = is_night(self.name, self.data_temp,
                                        debug=self.debug,
                                        log_success=self.log_success,
                                        log_failure=self.log_failure)
                else:
                    night = None

                if night is not None:
                    self.data_temp['day'] = (0 if night else 1,'count','group_count')
                
                self.data_temp['model'] = (self.model, None, None)
                self.data_temp['sourceUrl'] = (obfuscate_secrets(url), None, None)
                weathercode = self.data_temp.get('weathercode', (-1, 'count', 'group_count'))[0]
                self.data_temp['weathercodeAeris'] = (self.get_aeriscode(weathercode), None, None)
                break
            ii += 1

        if log_success or debug > 0:
            loginf("thread '%s': get_data_api finished. Number of records processed: %d" % (self.name, len(self.data_temp)))
        if debug > 2:
            logdbg("thread '%s': get_data_api unchecked result %s" % (self.name, json.dumps(self.data_temp)))

        # last check
        weathercode = self.data_temp.get('weathercode')
        if weathercode is None or weathercode[0] is None:
            self.data_temp['weathercode'] = (-1, 'count', 'group_count')
            self.data_temp['weathercodeAeris'] = (self.get_aeriscode(-1), None, None)
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api finished. No valid data could be loaded" % (self.name))
        if debug > 2:
            logdbg("thread '%s': get_data_api checked result %s" % (self.name, json.dumps(self.data_temp)))
        self.last_get_ts = weeutil.weeutil.to_int(time.time())
        return (len(self.data_temp) > 0)



# ============================================================================
#
# Class CDCthread
#
# ============================================================================
# check: https://www.dwd.de/DE/leistungen/beobachtung/beobachtung.html
class CDCthread(AbstractThread):


    # Mapping API presentWeather field to aeris code
    CDC_AERIS = {
        -1: '::NA',
         1: '::CL',
         2: '::FW',
         3: '::BK',
         4: '::OV',
         5: '::F',
         6: '::ZF',
         7: ':L:R',
         8: '::R',
         9: ':H:R',
        10: '::ZR',
        11: ':H:ZR',
        12: '::RS',
        13: ':H:RS',
        14: ':L:S',
        15: '::S',
        16: ':H:S',
        17: '::A',
        18: '::RW',
        19: ':H:RW',
        20: '::SR',
        21: ':H:SR',
        22: '::SW',
        23: ':H:SW',
        24: '::SS',
        25: ':H:SS',
        26: '::TP',
        27: '::T',
        28: ':H:T',
        29: '::TH',
        30: ':H:TH',
        31: '::WG'
    }

    BASE_URL = 'https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate'

    OBS = dict()
    
    # https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/wind/now/BESCHREIBUNG_obsgermany_climate_10min_wind_now_de.pdf
    OBS['wind'] = {
        'MESS_DATUM':('wind_generated', 'unix_epoch', 'group_time'),
           'QN':('wind_qualityLevel','count','group_count'),
        'FF_10':('windSpeed','meter_per_second','group_speed'),
        'DD_10':('windDir','degree_compass','group_direction')
    }

    # https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/extreme_wind/now/BESCHREIBUNG_obsgermany_climate_10min_fx_now_de.pdf
    OBS['gust'] = {
        'MESS_DATUM':('gust_generated', 'unix_epoch', 'group_time'),
            'QN':('gust_qualityLevel','count','group_count'),
         'FX_10':('windGust','meter_per_second','group_speed'),
         'DX_10':('windGustDir','degree_compass','group_direction'),
        'FNX_10':('windSpeedMin','meter_per_second','group_speed'),
        'FMX_10':('windSpeedMax','meter_per_second','group_speed')
    }

    # https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/air_temperature/now/BESCHREIBUNG_obsgermany_climate_10min_tu_now_de.pdf
    OBS['air'] = {
        'MESS_DATUM':('air_generated', 'unix_epoch', 'group_time'),
            'QN':('air_qualityLevel','count','group_count'),
         'PP_10':('pressure','hPa','group_pressure'),
         'TT_10':('outTemp','degree_C','group_temperature'),
        'TM5_10':('extraTemp1','degree_C','group_temperature'),
         'RF_10':('outHumidity','percent','group_percent'),
         'TD_10':('dewpoint','degree_C','group_temperature')
    }

    # https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/precipitation/now/BESCHREIBUNG_obsgermany_climate_10min_precipitation_now_de.pdf
    OBS['precipitation'] = {
        'MESS_DATUM':('precipitation_generated', 'unix_epoch', 'group_time'),
                'QN':('precipitation_qualityLevel','count','group_count'),
        'RWS_DAU_10':('rainDur','minute','group_deltatime'),
            'RWS_10':('rain','mm','group_rain'),
        'RWS_IND_10':('rainIndex','count','group_count')
    }

    # https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/solar/now/BESCHREIBUNG_obsgermany_climate_10min_solar_now_de.pdf
    OBS['solar'] = {
        'MESS_DATUM':('solar_generated', 'unix_epoch', 'group_time'),
           'QN':('solar_qualityLevel','count','group_count'),
        'DS_10':('solarRad','joule_per_cm_squared','group_radiation_energy'),
        'GS_10':('radiation','joule_per_cm_squared','group_radiation_energy'),
        'SD_10':('sunshineDur','hour','group_deltatime'),
        'LS_10':('atmosRad','joule_per_cm_squared','group_radiation_energy')
    }

    DIRS = {
        'air':('air_temperature','10minutenwerte_TU_','_now.zip','Meta_Daten_zehn_min_tu_'),
        'wind':('wind','10minutenwerte_wind_','_now.zip','Meta_Daten_zehn_min_ff_'),
        'gust':('extreme_wind','10minutenwerte_extrema_wind_','_now.zip','Meta_Daten_zehn_min_fx_'),
        'precipitation':('precipitation','10minutenwerte_nieder_','_now.zip','Meta_Daten_zehn_min_rr_'),
        'solar':('solar','10minutenwerte_SOLAR_','_now.zip','Meta_Daten_zehn_min_sd_')
    }

    # TODO ?
    def get_aeriscode(self, code):
        """ get aeris weather code from api code """
        try:
            x = self.CDC_AERIS[code]
        except (LookupError, TypeError):
            x = self.CDC_AERIS[-1]
        return x


    def __init__(self, name, thread_dict, debug=0, log_success=False, log_failure=True):

        super(CDCthread,self).__init__(name=name, thread_dict=thread_dict, debug=debug, log_success=log_success, log_failure=log_failure)

        self.config = thread_dict.get('config')
        self.debug = weeutil.weeutil.to_int(self.config.get('debug', 0))
        self.log_success = weeutil.weeutil.to_bool(self.config.get('log_success', log_success))
        self.log_failure = weeutil.weeutil.to_bool(self.config.get('log_failure', log_failure))

        if self.debug > 0:
            logdbg("thread '%s': init started" % self.name)
        if self.debug > 2:
            logdbg("thread '%s': init config %s" % (self.name, json.dumps(self.config)))

        self.station = self.config.get('station', '05397')
        self.provider = self.config.get('provider', 'dwd')
        self.model = self.config.get('model', 'cdc')
        self.prefix = self.config.get('prefix', 'current_dwd_'+ str(self.model).replace('-', '_') + '_')
        self.source_id = self.config.get('source_id', 'dwd-' + str(self.model).replace('_', '-'))
        self.interval_get = weeutil.weeutil.to_int(self.config.get('interval_get', 300))
        self.interval_push = weeutil.weeutil.to_int(self.config.get('interval_push', 30))
        self.expired = weeutil.weeutil.to_int(self.config.get('expired', 600))
        self.icon_path_belchertown = self.config.get('icon_path_belchertown', '')
        self.timezone = self.config.get('timezone', 'Europe/Berlin')
        self.config_dict = thread_dict.get('config_dict')
        self.engine = thread_dict.get('engine')
        self.lat_fallback = weeutil.weeutil.to_float(self.config.get('latitude'))
        self.lon_fallback = weeutil.weeutil.to_float(self.config.get('longitude'))
        self.alt_fallback = weeutil.weeutil.to_float(self.config.get('altitude'))
        self.lat = None
        self.lon = None
        self.alt = None
        self.dateTime = 0
        self.data_result = dict()
        self.data_temp = dict()
        self.last_get_ts = 0
        self.last_prepare_ts = 0

        # unit system
        self.unit_system = None
        self.unitsystem = None
        unit_system = self.config.get('unit_system')
        if unit_system is not None:
            unit_system = str(unit_system).upper()
            if unit_system in('US', 'METRIC', 'METRICWX'):
                self.unit_system = unit_system
                if self.unit_system == 'US': self.unitsystem = weewx.US
                elif self.unit_system == 'METRIC': self.unitsystem = weewx.METRIC
                elif self.unit_system == 'METRICWX': self.unitsystem = weewx.METRICWX

        # lang
        self.lang = self.config.get('lang')
        if self.lang is not None:
            self.lang = str(self.lang).lower()
            if self.lang not in('de', 'en'):
                self.lang = None

        # observations
        observations = self.config.get('observations')
        if observations:
            self.observations = weeutil.weeutil.option_as_list(observations)
        else:
            self.observations = ('air','wind','gust','precipitation','solar')
        self.requested = list()

        weewx.units.obs_group_dict.setdefault(self.prefix+'dateTime','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'generated','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'age','group_deltatime')
        weewx.units.obs_group_dict.setdefault(self.prefix+'day','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'expired','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'weathercode','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'weathercodeKey','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'barometer','group_pressure')
        weewx.units.obs_group_dict.setdefault(self.prefix+'altimeter','group_pressure')
        weewx.units.obs_group_dict.setdefault(self.prefix+'dateTime','group_time')
        for obsgrp in self.observations:
            grpobs = CDCthread.OBS.get(obsgrp)
            if grpobs is not None:
                for opsapi, obsweewx in grpobs.items():
                    obs = obsweewx[0]
                    group = obsweewx[2]
                    if group is not None:
                        weewx.units.obs_group_dict.setdefault(self.prefix + obs, group)

        if self.log_success or self.debug > 0:
            loginf("thread '%s': init finished" % self.name)


    def decodezip(self, zipdata):
        zz = zipfile.ZipFile(io.BytesIO(zipdata),'r')
        for ii in zz.namelist():
            return zz.read(ii).decode(encoding='utf-8')
        return None


    def get_meta_data(self, url):
        if self.lat is not None and self.lon is not None and self.alt is not None:
            return

        if url not in self.requested:
            self.requested.append(url)

        apiin_dict = self.config.get('api_in', configobj.ConfigObj())
        debug = weeutil.weeutil.to_int(apiin_dict.get('debug', self.debug))
        log_success = weeutil.weeutil.to_bool(apiin_dict.get('log_success', self.log_success))
        log_failure = weeutil.weeutil.to_bool(apiin_dict.get('log_failure', self.log_failure))
        attempts_max = weeutil.weeutil.to_int(apiin_dict.get('attempts_max', 1))
        attempts_wait = weeutil.weeutil.to_int(apiin_dict.get('attempts_wait', 10))

        attempts = 0
        try:
            while attempts <= attempts_max:
                attempts += 1
                response, code = request_api(self.name, url,
                                            debug = self.debug,
                                            log_success = log_success,
                                            log_failure = log_failure)
                if response is not None:
                    attempts = attempts_max + 1
                    zz = zipfile.ZipFile(io.BytesIO(response),'r')
                    for ii in zz.namelist():
                        if ii[0:20]=='Metadaten_Geographie':
                            txt = zz.read(ii).decode(encoding='utf-8')
                            x = list()
                            for ln in csv.reader(txt.splitlines(),delimiter=';'):
                                x.append(ln)
                            if x:
                                self.alt = float(x[-1][1])
                                self.lat = float(x[-1][2])
                                self.lon = float(x[-1][3])
                                if log_success or debug > 0:
                                    loginf("thread '%s': get_meta_data - id %s, name '%s', lat %.4f°, lon %.4f°, alt %.1f m" % (self.name, x[-1][0],x[-1][6], self.lat,self.lon,self.alt))
                elif attempts <= attempts_max:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api request_api sent http status code %d" % (self.name, code))
                        loginf("thread '%s': get_data_api request_api next try (%d/%d) in %d seconds" % (self.name, attempts, attempts_max, attempts_wait))
                    time.sleep(attempts_wait)
                else:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api api did not send data" % self.name)
                    return False
        except Exception as e:
            exception_output(self.name, e)
            return False


    def decodecsv(self, csvdata, obsgroup):
        # the first row are the column headers
        # The last row contains the most recent measurements
        csvdata = csvdata.strip()
        if not csvdata:
            return None

        try:
            first_row = None
            last_row = None
            rows = csv.reader(csvdata.splitlines(),delimiter=';')
            first_row = next(rows, None)
            if first_row is None or 'STATIONS_ID' not in first_row:
                return None
            for row in rows:
                if 'eor' in row:
                    last_row = row
            if last_row is None:
                return None
        except Exception as e:
            exception_output(self.name, e)
            return None

        obs_dict = CDCthread.OBS.get(obsgroup)
        group_data = dict()
        obscsv = first_row
        for idx, val in enumerate(last_row):
            if idx==0: continue # station id
            if val == 'eor': continue # end of data
            # if not val.isnumeric(): continue # data error
            obs = obscsv[idx].strip()
            if obs not in obs_dict:
                #logdbg("thread '%s': decodecsv nehme nicht aus gruppe %s das feld %s" % (self.name, obsgroup, obs))
                continue # not required
            #logdbg("thread '%s': decodecsv nehme aus gruppe %s das feld %s" % (self.name, obsgroup, obs))
            if idx == 1:
                # date and time (UTC)
                d = datetime.datetime.strptime(val, "%Y%m%d%H%M")
                ts = weeutil.weeutil.to_int(d.timestamp())
                if ts > self.dateTime:
                    self.dateTime = ts
                col = obs_dict.get(obs,(obs, None, None))
                group_data[col[0]] = (ts, col[1], col[2])
                continue
            # data columns
            elif obs=='QN':
                val = int(val)
            else:
                try:
                    val = weeutil.weeutil.to_float(val)
                    if val == -999.0: val = None
                except (ValueError, TypeError, ArithmeticError):
                    pass
            col = obs_dict.get(obs,(obs, None, None))
            group_data[col[0]] = (val, col[1], col[2])

        if group_data is None:
            return None

        if 'windDir' in group_data:
            group_data['windDir10'] = group_data['windDir']
        if 'windSpeed' in group_data:
            group_data['windSpeed10'] = group_data['windSpeed']
        if 'pressure' in group_data and 'altimeter' not in group_data and self.alt is not None:
            try:
                group_data['altimeter'] = (weewx.wxformulas.altimeter_pressure_Metric(group_data['pressure'][0],self.alt),'hPa','group_pressure')
            except Exception as e:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': weewx.wxformulas.altimeter_pressure_Metric (altimeter) altimeter %s, group_data %s" % (self.alt, json.dumps(group_data)))
                exception_output(self.name, e)
        if 'pressure' in group_data and 'outTemp' in group_data and 'barometer' not in group_data and self.alt is not None:
            try:
                group_data['barometer'] = (weewx.wxformulas.sealevel_pressure_Metric(group_data['pressure'][0],self.alt,group_data['outTemp'][0]),'hPa','group_pressure')
            except Exception as e:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': weewx.wxformulas.sealevel_pressure_Metric (barometer) altimeter %s, group_data %s" % (self.alt, json.dumps(group_data)))
                exception_output(self.name, e)
        return group_data



    def get_data_api(self):
        """ download and process CDC weather data """

        self.data_temp = dict()
        apiin_dict = self.config.get('api_in', configobj.ConfigObj())
        debug = weeutil.weeutil.to_int(apiin_dict.get('debug', self.debug))
        log_success = weeutil.weeutil.to_bool(apiin_dict.get('log_success', self.log_success))
        log_failure = weeutil.weeutil.to_bool(apiin_dict.get('log_failure', self.log_failure))
        attempts_max = weeutil.weeutil.to_int(apiin_dict.get('attempts_max', 1))
        attempts_wait = weeutil.weeutil.to_int(apiin_dict.get('attempts_wait', 10))

        if not weeutil.weeutil.to_bool(apiin_dict.get('enable', False)):
            if log_success or debug > 0:
                loginf("thread '%s': get_data_api is diabled. Enable it in the [api_in] section of station %s" %(self.name, self.station))
            return False

        if debug > 0:
            logdbg("thread '%s': get_data_api started" % (self.name))
        if debug > 2:
            logdbg("thread '%s': get_data_api config %s" %(self.name, json.dumps(apiin_dict)))

        # unit system
        unit_system = None
        unitsystem = None
        u_s = apiin_dict.get('unit_system', self.unit_system)
        if u_s is not None:
            u_s = str(u_s).upper()
            if u_s in('US', 'METRIC', 'METRICWX'):
                unit_system = u_s
                if unit_system == 'US': unitsystem = weewx.US
                elif unit_system == 'METRIC': unitsystem = weewx.METRIC
                elif unit_system == 'METRICWX': unitsystem = weewx.METRICWX

        # lang
        lang = apiin_dict.get('lang', self.lang)
        if lang is not None:
            lang = str(lang).lower()
            if lang not in('de', 'en'):
                lang = None

        url = CDCthread.BASE_URL+'/10_minutes/'
        urls = dict()
        # get metadata and obsevation urls
        for obsgroup in self.observations:
            jj = CDCthread.DIRS.get(obsgroup)
            if jj:
                self.get_meta_data(url+jj[0]+'/meta_data/'+jj[3]+self.station+'.zip')
                urls[obsgroup] = url+jj[0]+'/now/'+jj[1]+self.station+jj[2]
            elif self.log_failure or self.debug > 0:
                logerr("thread '%s': init unknown observation group %s" % (self.name, obsgroup))

        for obsgroup, url in urls.items():
            attempts = 0

            if url not in self.requested:
                self.requested.append(url)

            try:
                while attempts <= attempts_max:
                    attempts += 1
                    # download data in ZIP format from DWD's server
                    response, code = request_api(self.name, url,
                                                debug = self.debug,
                                                log_success = log_success,
                                                log_failure = log_failure)
                    if response is not None:
                        # extract data file out of the downloaded ZIP file
                        txt = self.decodezip(response)
                        if not txt: raise FileNotFoundError("thread '%s': no file inside ZIP" % (self.name))
                        # convert CSV data to Python array
                        data_temp = self.decodecsv(txt, obsgroup)
                        if data_temp is not None:
                            self.data_temp.update(data_temp)
                            attempts = attempts_max + 1
                    elif attempts <= attempts_max:
                        if log_failure or debug > 0:
                            logerr("thread '%s': get_data_api request_api sent http status code %d" % (self.name, code))
                            loginf("thread '%s': get_data_api request_api next try (%d/%d) in %d seconds" % (self.name, attempts, attempts_max, attempts_wait))
                        time.sleep(attempts_wait)
                    else:
                        if log_failure or debug > 0:
                            logerr("thread '%s': get_data_api api did not send data" % self.name)
                        return False
            except Exception as e:
                exception_output(self.name, e)
                return False

        if self.data_temp is not None:
            self.data_temp['dateTime'] = (weeutil.weeutil.to_int(time.time()), 'unix_epoch', 'group_time')
            self.data_temp['generated'] = (self.dateTime if self.dateTime > 0 else weeutil.weeutil.to_int(time.time()), 'unix_epoch', 'group_time')
            apiunitsystem = self.data_temp.get('usUnits')
            if apiunitsystem is None:
                self.data_temp['usUnits'] = (unitsystem, None, None)
            else:
                self.data_temp['usUnits'] = (weeutil.weeutil.to_int(apiunitsystem), None, None)

            if self.lat is not None and self.lon is not None and self.alt is not None:
                self.data_temp['latitude'] = (self.lat, 'degree_compass', 'group_coordinate')
                self.data_temp['longitude'] = (self.lon, 'degree_compass', 'group_coordinate')
                self.data_temp['altitude'] = (self.alt, 'meter', 'group_altitude')
            else:
                self.data_temp['latitude'] = (self.lat_fallback, 'degree_compass', 'group_coordinate')
                self.data_temp['longitude'] = (self.lon_fallback, 'degree_compass', 'group_coordinate')
                self.data_temp['altitude'] = (self.alt_fallback, 'meter', 'group_altitude')

            if self.data_temp.get('latitude') is not None and self.data_temp.get('longitude') is not None:
                night = is_night(self.name, self.data_temp,
                                 debug=self.debug,
                                 log_success=self.log_success,
                                 log_failure=self.log_failure)
            else:
                night = None
            self.data_temp['day'] = (1 if not night else 1, 'count', 'group_count')
            self.data_temp['model'] = (self.model, None, None)
            ii = 1
            for url in self.requested:
                lfd = '{:02d}'.format(ii)
                self.data_temp['sourceUrl' + lfd] = (obfuscate_secrets(url), None, None)
                ii += 1
            weathercode = self.data_temp.get('weathercode', (-1, 'count', 'group_count'))[0]
            self.data_temp['weathercodeAeris'] = (self.get_aeriscode(weathercode), None, None)
            # as String
            self.data_temp['station_id'] = (str(self.station), None, None)

        if log_success or debug > 0:
            loginf("thread '%s': get_data_api finished. Number of records processed: %d" % (self.name, len(self.data_temp)))
        if debug > 2:
            logdbg("thread '%s': get_data_api unchecked result %s" % (self.name, json.dumps(self.data_temp)))

        # last check, but it's ok, we have no weather code or other values for these data that we could use for a pictorial or text representation
        weathercode = self.data_temp.get('weathercode')
        if weathercode is None or weathercode[0] is None:
            self.data_temp['weathercode'] = (-1, 'count', 'group_count')
            self.data_temp['weathercodeAeris'] = (self.get_aeriscode(-1), None, None)
            if log_success or debug > 0:
                loginf("thread '%s': get_data_api finished. No valid data could be loaded, but it is ok!" % (self.name))
        if debug > 2:
            logdbg("thread '%s': get_data_api checked result %s" % (self.name, json.dumps(self.data_temp)))
        self.last_get_ts = weeutil.weeutil.to_int(time.time())
        return (len(self.data_temp) > 0)



# ============================================================================
#
# Class OPENMETEOthread
#
# ============================================================================

class OPENMETEOthread(AbstractThread):

    WEATHERMODELS = {
        # option: (country, weather service, model, API endpoint, exclude list)
        'best_match':('', '', '', 'forecast',['snowfall_height']),
        'dwd-icon':('DE', 'DWD', 'ICON', 'dwd-icon',['precipitation_probability', 'visibility']),
        'ecmwf':('EU', 'ECMWF', 'open IFS', 'ecmwf',['apparent_temperature', 'dewpoint_2m', 'diffuse_radiation_instant', 'evapotranspiration', 'freezinglevel_height', 'precipitation_probability', 'rain', 'relativehumidity_2m', 'shortwave_radiation_instant', 'showers', 'snow_depth', 'snowfall_height', 'surface_pressure', 'visibility', 'windgusts_10m']),
        'ecmwf_ifs04':('EU', 'ECMWF', 'IFS', 'forecast',['snowfall_height']),
        'gem':('CA', 'MSC-CMC', 'GEM+HRDPS', 'gem',['evapotranspiration', 'freezinglevel_height', 'precipitation_probability', 'snow_depth', 'snowfall_height', 'visibility']),
        'gem_global':('CA', 'MSC-CMC', 'GEM', 'forecast',['snowfall_height']),
        'gem_hrdps_continental':('CA', 'MSC-CMC', 'GEM-HRDPS', 'forecast',['precipitation_probability', 'snowfall_height', 'surface_pressure']),
        'gem_regional':('CA', 'MSC-CMC', 'GEM', 'forecast',['snowfall_height', 'surface_pressure']),
        'gem_seamless':('CA', 'MSC-CMC', 'GEM', 'forecast',['snowfall_height']),
        'gfs':('US', 'NOAA', 'GFS', 'gfs',['snowfall_height']),
        'gfs_global':('US', 'NOAA', 'GFS Global', 'forecast',['snowfall_height']),
        'gfs_hrrr':('US', 'NOAA', 'GFS HRRR', 'forecast',['precipitation_probability', 'snowfall_height', 'surface_pressure']),
        'gfs_seamless':('US', 'NOAA', 'GFS Seamless', 'forecast',['snowfall_height']),
        'icon_d2':('DE', 'DWD', 'ICON D2', 'forecast',['precipitation_probability', 'snowfall_height', 'visibility']), # TODO check excludes
        'icon_eu':('DE', 'DWD', 'ICON EU', 'forecast',['precipitation_probability', 'snowfall_height', 'visibility']), # TODO check excludes
        'icon_global':('DE', 'DWD', 'ICON Global', 'forecast',['snowfall_height']),
        'icon_seamless':('DE', 'DWD', 'ICON Seamless', 'forecast',['precipitation_probability', 'snowfall_height', 'visibility']), # TODO check excludes
        'jma':('JP', 'JMA', 'GSM+MSM', 'jma',['evapotranspiration', 'freezinglevel_height', 'precipitation_probability', 'rain', 'showers', 'snow_depth', 'snowfall_height', 'visibility', 'windgusts_10m']),
        'meteofrance':('FR', 'MeteoFrance', 'Arpege+Arome', 'meteofrance',['evapotranspiration', 'freezinglevel_height', 'precipitation_probability', 'rain', 'showers', 'snow_depth', 'snowfall_height', 'visibility']),
        'metno':('NO', 'MET Norway', 'Nordic', 'metno',['evapotranspiration', 'freezinglevel_height', 'precipitation_probability', 'rain', 'showers', 'snow_depth', 'snowfall_height', 'visibility']),
        'metno_nordic':('NO', 'MET Norway', 'Nordic', 'forecast',['precipitation_probability', 'snowfall_height', 'surface_pressure']),
        # TODO remove 'test' in stable release?
        'test':('', '', '', '',[])
    }


    # Mapping API field -> WeeWX field
    CURRENTOBS = {
        'temperature': 'outTemp',
        'windspeed': 'windSpeed',
        'winddirection': 'windDir',
        'weathercode': 'weathercode',
        'is_day': 'isDay'
    }


    # Mapping 15 Minutes API field -> WeeWX field
    MIN15OBS = {
        'precipitation': 'precipitation',
        'rain': 'rain',
        'snowfall':'snow',
        'freezinglevel_height':'freezinglevelHeight',
        'shortwave_radiation_instant':'radiation',
        'diffuse_radiation_instant':'solarRad'
    }


    # https://open-meteo.com/en/docs
    # Evapotranspiration/UV-Index: 
    # Attention, no capital letters for WeeWX fields. Otherwise the WeeWX field "ET"/"UV" will be formed if no prefix is used!
    # Attention, not all fields available in each model
    # Mapping API field forecast and dwd-icon endpoint -> WeeWX field
    HOURLYOBS = {
        'temperature_2m': 'outTemp',
        'apparent_temperature': 'appTemp',
        'dewpoint_2m': 'dewpoint', # not available in forecast model ecmwf
        'pressure_msl': 'barometer',
        'surface_pressure': 'pressure',
        'relativehumidity_2m': 'outHumidity', # not available in forecast model ecmwf
        'winddirection_10m': 'windDir',
        'windspeed_10m': 'windSpeed',
        'windgusts_10m': 'windGust', # not available in forecast model ecmwf
        'cloudcover': 'cloudcover',
        'evapotranspiration': 'et',
        'precipitation': 'precipitation',
        'precipitation_probability': 'precipitationProbability',
        'rain': 'rain',
        'showers': 'shower',
        'snowfall':'snow',
        'freezinglevel_height':'freezinglevelHeight',
        'weathercode':'weathercode',
        'snow_depth':'snowDepth',
        'shortwave_radiation_instant':'radiation',
        'diffuse_radiation_instant':'solarRad',
        'visibility':'visibility', # only available by the American weather models.
        'snowfall_height':'snowfallHeight' # Europe only
    }


    # API result contain no units for current_weather
    # Mapping API current_weather unit -> WeeWX unit
    CURRENTUNIT = {
        'temperature': u'°C',
        'windspeed': 'km/h',
        'winddirection': u'°',
        'weathercode': 'wmo code',
        'time': 'unixtime',
        'is_day': ''
    }


    # Mapping API hourly unit -> WeeWX unit
    UNIT = {
        u'°': 'degree_compass',
        u'°C': 'degree_C',
        'mm': 'mm',
        'cm': 'cm',
        'm': 'meter',
        'hPa': 'hPa',
        'kPa': 'kPa',
        u'W/m²': 'watt_per_meter_squared',
        'km/h': 'km_per_hour',
        '%': 'percent',
        'wmo code': 'count',
        '': 'count',
        'unixtime': 'unix_epoch'
    }


    # https://open-meteo.com/en/docs/dwd-api
    # WMO Weather interpretation codes (WW)
    # Code        Description
    # 0           Clear sky
    # 1, 2, 3     Mainly clear, partly cloudy, and overcast
    # 45, 48      Fog and depositing rime fog
    # 51, 53, 55  Drizzle: Light, moderate, and dense intensity
    # 56, 57      Freezing Drizzle: Light and dense intensity
    # 61, 63, 65  Rain: Slight, moderate and heavy intensity
    # 66, 67      Freezing Rain: Light and heavy intensity
    # 71, 73, 75  Snow fall: Slight, moderate, and heavy intensity
    # 77          Snow grains
    # 80, 81, 82  Rain showers: Slight, moderate, and violent
    # 85, 86      Snow showers slight and heavy
    # 95 *        Thunderstorm: Slight or moderate
    # 96, 99 *    Thunderstorm with slight and heavy hail
    # (*) Thunderstorm forecast with hail is only available in Central Europe

    # Mapping API WMO code field to aeris code
    OM_AERIS = {
        -1: '::NA',
         0: '::CL',
         1: '::FW',
         2: '::SC',
         3: '::OV',
        45: '::F',
        48: '::ZF',
        51: ':L:L',
        53: '::L',
        55: ':H:L',
        56: ':L:ZL',
        57: '::ZL',
        61: ':L:R',
        63: '::R',
        65: ':H:R',
        66: ':L:ZR',
        67: '::ZR',
        71: ':L:S',
        73: '::S',
        75: ':H:S',
        77: '::IP',
        80: ':L:RW',
        81: '::RW',
        82: ':H:RW',
        85: ':L:SW',
        86: '::SW',
        95: '::T',
        96: '::TH',
        99: ':H:TH'
    }


    def get_aeriscode(self, code):
        """ get aeris weather code from api code """
        try:
            x = self.OM_AERIS[code]
        except (LookupError, TypeError):
            x = self.OM_AERIS[-1]
        return x


    def get_current_obs(self):
        return OPENMETEOthread.CURRENTOBS


    def get_hourly_obs(self):
        hobs = copy.deepcopy(OPENMETEOthread.HOURLYOBS)
        modelparams = OPENMETEOthread.WEATHERMODELS.get(self.model)
        if modelparams is not None:
            # remove exclude list from obs
            for x in modelparams[4]:
                if x in hobs:
                    hobs.pop(x)
        return hobs


    def get_min15_obs(self):
        min15obs = copy.deepcopy(OPENMETEOthread.MIN15OBS)
        modelparams = OPENMETEOthread.WEATHERMODELS.get(self.model)
        if modelparams is not None:
            # remove exclude list from obs
            for x in modelparams[4]:
                if x in min15obs:
                    min15obs.pop(x)
        return min15obs


    def __init__(self, name, thread_dict, debug=0, log_success=False, log_failure=True):
    
        super(OPENMETEOthread,self).__init__(name=name, thread_dict=thread_dict, debug=debug, log_success=log_success, log_failure=log_failure)

        self.config = thread_dict.get('config')
        self.debug = weeutil.weeutil.to_int(self.config.get('debug', 0))
        self.log_success = weeutil.weeutil.to_bool(self.config.get('log_success', log_success))
        self.log_failure = weeutil.weeutil.to_bool(self.config.get('log_failure', log_failure))

        if self.debug > 0:
            logdbg("thread '%s': init started" % self.name)
        if self.debug > 2:
            logdbg("thread '%s': init config %s" % (self.name, json.dumps(self.config)))

        self.station = self.config.get('station', 'thisstation')
        self.provider = self.config.get('provider', 'open-meteo')
        self.model = self.config.get('model', 'dwd-icon')
        self.prefix = self.config.get('prefix', 'current_om_'+ str(self.model).replace('-', '_') + '_')
        self.source_id = self.config.get('source_id', 'om-' + str(self.model).replace('_', '-'))
        self.interval_get = weeutil.weeutil.to_int(self.config.get('interval_get', 300))
        self.interval_push = weeutil.weeutil.to_int(self.config.get('interval_push', 30))
        self.expired = weeutil.weeutil.to_int(self.config.get('expired', 600))
        self.icon_path_belchertown = self.config.get('icon_path_belchertown', '')
        self.timezone = self.config.get('timezone', 'Europe/Berlin')
        self.current_obs = self.get_current_obs()
        self.min15_obs = self.get_min15_obs()
        self.hourly_obs = self.get_hourly_obs()
        self.config_dict = thread_dict.get('config_dict')
        self.engine = thread_dict.get('engine')
        self.data_result = dict()
        self.data_temp = dict()
        self.last_get_ts = 0
        self.last_prepare_ts = 0

        # unit system
        self.unit_system = None
        self.unitsystem = None
        unit_system = self.config.get('unit_system')
        if unit_system is not None:
            unit_system = str(unit_system).upper()
            if unit_system in('US', 'METRIC', 'METRICWX'):
                self.unit_system = unit_system
                if self.unit_system == 'US': self.unitsystem = weewx.US
                elif self.unit_system == 'METRIC': self.unitsystem = weewx.METRIC
                elif self.unit_system == 'METRICWX': self.unitsystem = weewx.METRICWX

        # lang
        self.lang = self.config.get('lang')
        if self.lang is not None:
            self.lang = str(self.lang).lower()
            if self.lang not in('de', 'en'):
                self.lang = None

        self.lat = weeutil.weeutil.to_float(self.config.get('latitude'))
        self.lon = weeutil.weeutil.to_float(self.config.get('longitude'))
        self.alt = weeutil.weeutil.to_float(self.config.get('altitude'))
        if self.lat is None or self.lon is None or self.alt is None:
            if self.station.lower() not in ('thisstation', 'here'):
                # station is a city name or postal code
                geo = get_geocoding(self.name, self.station, self.lang, debug=self.debug, log_success=self.log_success, log_failure=self.log_failure)
                if geo is not None:
                    if self.lat is None:
                        self.lat = weeutil.weeutil.to_float(geo.get('latitude'))
                    if self.lon is None:
                        self.lon = weeutil.weeutil.to_float(geo.get('longitude'))
                    if self.alt is None:
                        self.alt = weeutil.weeutil.to_float(geo.get('elevation'))
                else:
                    if self.log_failure or self.debug > 0:
                        logerr("thread '%s': Could not get geodata for station '%s'" % (self.name, self.station))
                    #raise weewx.ViolatedPrecondition("thread '%s': Could not get geodata for station '%s'" % (self.name, station))
                    return
            else:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': Configured station is not valid" % self.name)
                #raise weewx.ViolatedPrecondition("thread '%s': Configured station is not valid" % self.name)
                return

        for opsapi, obsweewx in self.current_obs.items():
            obsgroup = None
            if obsweewx=='weathercode':
                obsgroup = 'group_count'
            else:
                obsgroup = weewx.units.obs_group_dict.get(obsweewx)
            if obsgroup is not None:
                weewx.units.obs_group_dict.setdefault(self.prefix+obsweewx,obsgroup)

        weewx.units.obs_group_dict.setdefault(self.prefix+'dateTime','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'generated','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'age','group_deltatime')
        weewx.units.obs_group_dict.setdefault(self.prefix+'day','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'expired','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'weathercode','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'weathercodeKey','group_count')
        for opsapi, obsweewx in self.hourly_obs.items():
            if obsweewx=='weathercode':
                # filled with CURRENTOBS
                continue
            obsgroup = None
            if obsweewx=='precipitation':
                obsgroup = 'group_rain'
            elif obsweewx=='precipitationProbability':
                obsgroup = 'group_percent'
            elif obsweewx=='shower':
                obsgroup = 'group_rain'
            elif obsweewx=='freezinglevelHeight':
                obsgroup = 'group_altitude'
            elif obsweewx=='snowfallHeight':
                obsgroup = 'group_altitude'
            elif obsweewx=='visibility':
                obsgroup = 'group_distance'
            elif obsweewx=='solarRad':
                obsgroup = 'group_radiation'
            else:
                obsgroup = weewx.units.obs_group_dict.get(obsweewx)
            if obsgroup is not None:
                weewx.units.obs_group_dict.setdefault(self.prefix+obsweewx,obsgroup)
        if self.log_success or self.debug > 0:
            loginf("thread '%s': init finished" % self.name)


    def get_data_api(self):
        """ download and process Open-Meteo weather data """

        self.data_temp = dict()
        apiin_dict = self.config.get('api_in', configobj.ConfigObj())
        debug = weeutil.weeutil.to_int(apiin_dict.get('debug', self.debug))
        log_success = weeutil.weeutil.to_bool(apiin_dict.get('log_success', self.log_success))
        log_failure = weeutil.weeutil.to_bool(apiin_dict.get('log_failure', self.log_failure))
        attempts_max = weeutil.weeutil.to_int(apiin_dict.get('attempts_max', 1))
        attempts_wait = weeutil.weeutil.to_int(apiin_dict.get('attempts_wait', 10))

        if not weeutil.weeutil.to_bool(apiin_dict.get('enable', False)):
            if log_success or debug > 0:
                loginf("thread '%s': get_data_api is diabled. Enable it in the [api_in] section of station %s" % (self.name, self.station))
            return False

        if debug > 0:
            logdbg("thread '%s': get_data_api started" % (self.name))
        if debug > 2:
            logdbg("thread '%s': get_data_api config %s" % (self.name, json.dumps(apiin_dict)))

        # unit system
        unit_system = None
        unitsystem = None
        u_s = apiin_dict.get('unit_system', self.unit_system)
        if u_s is not None:
            u_s = str(u_s).upper()
            if u_s in('US', 'METRIC', 'METRICWX'):
                unit_system = u_s
                if unit_system == 'US': unitsystem = weewx.US
                elif unit_system == 'METRIC': unitsystem = weewx.METRIC
                elif unit_system == 'METRICWX': unitsystem = weewx.METRICWX

        # lang
        lang = apiin_dict.get('lang', self.lang)
        if lang is not None:
            lang = str(lang).lower()
            if lang not in('de', 'en'):
                lang = None

        endpoint = OPENMETEOthread.WEATHERMODELS.get(self.model)[3]
        if endpoint == 'forecast':
            modelparams = '&models=%s' % self.model
        else:
            modelparams = ''

        baseurl = 'https://api.open-meteo.com/v1/%s' % endpoint

        # Geographical WGS84 coordinate of the location
        params = '?latitude=%s' % self.lat
        params += '&longitude=%s' % self.lon

        # The elevation used for statistical downscaling. Per default, a 90 meter digital elevation model is used.
        # You can manually set the elevation to correctly match mountain peaks. If &elevation=nan is specified,
        # downscaling will be disabled and the API uses the average grid-cell height.
        # If a valid height exists, it will be used
        if self.alt is not None:
            params += '&elevation=%s' % self.alt

        # timeformat iso8601 | unixtime
        params += '&timeformat=unixtime'

        # timezone
        # If timezone is set, all timestamps are returned as local-time and data is returned starting at 00:00 local-time.
        # Any time zone name from the time zone database is supported. If auto is set as a time zone, the coordinates will
        # be automatically resolved to the local time zone.
        # using API default
        #params += '&timezone=Europe%2FBerlin'

        # TODO config param?
        # cell_selection, land | sea | nearest
        # Set a preference how grid-cells are selected. The default land finds a suitable grid-cell on land with similar
        # elevation to the requested coordinates using a 90-meter digital elevation model. sea prefers grid-cells on sea.
        # nearest selects the nearest possible grid-cell.
        #params += '&cell_selection=land'

        # TODO use "past_days=1" instead of yesterday?
        # The time interval to get weather data. A day must be specified as an ISO8601 date (e.g. 2022-06-30).
        yesterday = datetime.datetime.now() - datetime.timedelta(1)
        yesterday = datetime.datetime.strftime(yesterday, '%Y-%m-%d')
        today = datetime.datetime.today().strftime('%Y-%m-%d')
        params += '&start_date=%s' % yesterday
        params += '&end_date=%s' % today

        # units
        # The API request is made in the metric system
        # Temperature in celsius
        params += '&temperature_unit=celsius'
        # Wind in km/h
        params += '&windspeed_unit=kmh'
        # Precipitation in mm
        params += '&precipitation_unit=mm'

        # Include current weather conditions in the JSON output.
        # currently contained values (28.01.2023): temperature, windspeed, winddirection, weathercode, time
        params += '&current_weather=true'

        # A list of weather variables which should be returned. Values can be comma separated,
        # or multiple &hourly= parameter in the URL can be used.
        # defined in HOURLYOBS
        params += '&hourly='+','.join([ii for ii in self.hourly_obs])

        # 15-Minutely Parameter Definition
        # The parameter &minutely_15= can be used to get 15-minutely data. This data is based on the ICON-D2 model 
        # which is only available in Central Europe. If 15-minutely data is requested for locations outside Central Europe,
        # data is interpolated from 1-hourly to 15-minutely.
        if endpoint == 'dwd-icon':
            params += '&minutely_15='+','.join([ii for ii in self.min15_obs])

        # Model
        params += modelparams

        url = baseurl + params

        if debug > 0:
            logdbg("thread '%s': get_data_api url %s" % (self.name, url))

        apidata = dict()
        attempts = 0
        try:
            while attempts <= attempts_max:
                attempts += 1
                response, code = request_api(self.name, url,
                                            debug = self.debug,
                                            log_success = log_success,
                                            log_failure = log_failure)
                if response is not None:
                    apidata = response
                    attempts = attempts_max + 1
                elif attempts <= attempts_max:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api request_api sent http status code %d" % (self.name, code))
                        loginf("thread '%s': get_data_api request_api next try (%d/%d) in %d seconds" % (self.name, attempts, attempts_max, attempts_wait))
                    time.sleep(attempts_wait)
                else:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api api did not send data" % self.name)
                    return False
        except Exception as e:
            exception_output(self.name, e)
            return False

        if debug > 2:
            logdbg("thread '%s': get_data_api api unchecked result %s" % (self.name, json.dumps(apidata)))

        # check results

        # check unit system
        if unitsystem is None and apidata.get('usUnits') is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api did not send unit system and it's not configured in section [api_in]" % (self.name))
            return False

        if endpoint == 'dwd-icon':
            if apidata.get('minutely_15') is None:
                if log_failure or debug > 0:
                    logerr("thread '%s': get_data_api api sent no 15-minutely data" % self.name)
                return False

            min15_units = apidata.get('minutely_15_units')
            if min15_units is None:
                if log_failure or debug > 0:
                    logerr("thread '%s': get_data_api api sent no minutely_15_units data" % self.name)
                return False

        if apidata.get('hourly') is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api sent no hourly data" % self.name)
            return False

        hourly_units = apidata.get('hourly_units')
        if hourly_units is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api sent no hourly_units data" % self.name)
            return False

        current_weather = apidata.get('current_weather')
        if current_weather is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api sent no current_weather data" % self.name)
            return False

        # 15-minutely timestamps
        if endpoint == 'dwd-icon':
            min15timelist = apidata['minutely_15'].get('time')
            if min15timelist is None:
                if log_failure or debug > 0:
                    logerr("thread '%s': get_data_api api sent no 15-minutely time periods data" % self.name)
                return False

            if not isinstance(min15timelist, list):
                if log_failure or debug > 0:
                    logerr("thread '%s': get_data_api api sent 15-minutely time periods data not as list" % self.name)
                return False

            if len(min15timelist) == 0:
                if log_failure or debug > 0:
                    logerr("thread '%s': get_data_api api sent 15-minutely time periods without data" % self.name)
                return False

        # hourly timestamps
        htimelist = apidata['hourly'].get('time')
        if htimelist is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api sent no hourly time periods data" % self.name)
            return False

        if not isinstance(htimelist, list):
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api sent hourly time periods data not as list" % self.name)
            return False

        if len(htimelist) == 0:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api sent hourly time periods without data" % self.name)
            return False

        # current timestamp
        actts = weeutil.weeutil.to_int(time.time())

        # get the last 15-minutely observation timestamp before the current time
        if endpoint == 'dwd-icon':
            obsmin15ts = None
            for ts in min15timelist:
                if ts > actts:
                    break
                obsmin15ts = weeutil.weeutil.to_int(ts)
            if obsmin15ts is None:
                if log_failure or debug > 0:
                    logerr("thread '%s': get_data_api api sent 15-minutely timestamps only in the future" % self.name)
                return False
        else:
            obsmin15ts = 0

        # get the last hourly observation timestamp before the current time
        obshts = None
        for ts in htimelist:
            if ts > actts:
                break
            obshts = weeutil.weeutil.to_int(ts)
        if obshts is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api sent hourly timestamps only in the future" % self.name)
            return False

        latitude = apidata.get('latitude')
        longitude = apidata.get('longitude')
        altitude = apidata.get('elevation')

        if debug > 2:
            logdbg("thread '%s': get_data_api    ts now %s" % (self.name, str(actts)))
            logdbg("thread '%s': get_data_api    ts now %s" % (self.name, str( datetime.datetime.fromtimestamp(actts).strftime('%Y-%m-%d %H:%M:%S'))))
            if endpoint == 'dwd-icon':
                logdbg("thread '%s': get_data_api  ts 15min %s" % (self.name, str(obsmin15ts)))
                logdbg("thread '%s': get_data_api  ts 15min %s" % (self.name, str( datetime.datetime.fromtimestamp(obsmin15ts).strftime('%Y-%m-%d %H:%M:%S'))))
            logdbg("thread '%s': get_data_api ts hourly %s" % (self.name, str(obshts)))
            logdbg("thread '%s': get_data_api ts hourly %s" % (self.name, str( datetime.datetime.fromtimestamp(obshts).strftime('%Y-%m-%d %H:%M:%S'))))
            logdbg("thread '%s': get_data_api lat %s lon %s alt %s" % (self.name,latitude,longitude,altitude))
            logdbg("thread '%s': get_data_api model %s" % (self.name,self.model))

        # timestamp current_weather
        obscts = int(current_weather.get('time', 0))

        # final timestamp
        obsts = weeutil.weeutil.to_int(max(obscts, obsmin15ts, obshts))
        self.data_temp['dateTime'] = (weeutil.weeutil.to_int(actts), 'unix_epoch', 'group_time')
        self.data_temp['generated'] = (weeutil.weeutil.to_int(actts), 'unix_epoch', 'group_time')
        self.data_temp['obsts'] = (obsts, 'unix_epoch', 'group_time')
        self.data_temp['obstsISO'] = (get_isodate_from_timestamp(obsts, self.timezone), None, None)

        # TODO: check this
        apiunitsystem = apidata.get('usUnits')
        if apiunitsystem is None:
            self.data_temp['usUnits'] = (unitsystem, None, None)
        else:
            self.data_temp['usUnits'] = (weeutil.weeutil.to_int(apiunitsystem), None, None)

        try:
            #get current weather data
            for obsapi, obsweewx in self.current_obs.items():
                obsname = self.prefix + str(obsweewx)
                if debug > 2:
                    logdbg("thread '%s': get_data_api current: weewx %s api %s obs %s" % (self.name, str(obsweewx), str(obsapi), str(obsname)))
                # API json response contain no unit data for current_weather observations
                unitapi = OPENMETEOthread.CURRENTUNIT.get(obsapi)
                if unitapi is None:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api current: No valid unit for observation %s - %s" % (self.name, str(obsapi), str(obsname)))
                    self.data_temp[obsweewx] = (None, None, None)
                    continue
                unitweewx = OPENMETEOthread.UNIT.get(unitapi)
                if unitweewx is None:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api current: Could not convert api unit '%s' to weewx unit" % (self.name, str(unitapi)))
                    self.data_temp[obsweewx] = (None, None, None)
                    continue
                obsval = current_weather.get(obsapi)
                if obsval is None:
                    if log_failure or debug > 0:
                        logwrn("thread '%s': get_data_api current: 'None' for observation %s - %s on timestamp %s" % (self.name, str(obsapi), str(obsname), str(obscts)))
                groupweewx = weewx.units.obs_group_dict.get(obsname)
                self.data_temp[obsweewx] = (weeutil.weeutil.to_float(obsval), unitweewx, groupweewx)
                if debug > 2:
                    logdbg("thread '%s': get_data_api current: weewx %s result %s" % (self.name, str(obsweewx), str(self.data_temp[obsweewx])))
  
            if self.debug > 2:
                logdbg("thread '%s': API current: result %s" % (self.name, json.dumps(self.data_temp)))

            # get 15-minutely weather data
            if endpoint == 'dwd-icon':
                for obsapi, obsweewx in self.min15_obs.items():
                    obsname = self.prefix + str(obsweewx)
                    if self.data_temp.get(obsweewx) is not None:
                        # filled with current_weather data
                        continue
                    if debug > 2:
                        logdbg("thread '%s': get_data_api minutely_15: weewx %s api %s obs %s" % (self.name, str(obsweewx), str(obsapi), str(obsname)))
                    obslist = apidata['minutely_15'].get(obsapi)
                    if obslist is None:
                        if log_failure or debug > 0:
                            logdbg("thread '%s': get_data_api minutely_15: No value for observation '%s' - '%s'" % (self.name, str(obsapi), str(obsname)))
                        self.data_temp[obsweewx] = (None, None, None)
                        continue
                    # Build a dictionary with timestamps as key and the corresponding values
                    obsvals = dict(zip(min15timelist, obslist))
                    obsval = obsvals.get(obsmin15ts)
                    unitapi = min15_units.get(obsapi)
                    if unitapi is None:
                        if log_failure or debug > 0:
                            logerr("thread '%s': get_data_api minutely_15: No unit for observation %s - %s" % (self.name, str(obsapi), str(obsname)))
                        self.data_temp[obsweewx] = (None, None, None)
                        continue
                    unitweewx = OPENMETEOthread.UNIT.get(unitapi)
                    if unitweewx is None:
                        if log_failure or debug > 0:
                            logerr("thread '%s': get_data_api minutely_15: Could not convert api unit '%s' to weewx unit" % (self.name, str(unitapi)))
                        self.data_temp[obsweewx] = (None, None, None)
                        continue
                    if obsval is None:
                        if log_failure or debug > 0:
                            logwrn("thread '%s': get_data_api minutely_15: 'None' for observation %s - %s on timestamp %s" % (self.name, str(obsapi), str(obsname), str(obshts)))
                    groupweewx = weewx.units.obs_group_dict.get(obsname)
                    # snowDepth from meter to mm, weewx snowDepth is weewx group_rain
                    # group_rain has no conversation from meter to mm
                    if obsweewx == 'snowDepth':
                        obsval = (weeutil.weeutil.to_float(obsval) * 1000)
                        unitweewx = 'mm'
                    self.data_temp[obsweewx] = (weeutil.weeutil.to_float(obsval), unitweewx, groupweewx)
                    if debug > 2:
                        logdbg("thread '%s': get_data_api minutely_15: weewx %s result %s" % (self.name, str(obsweewx), str(self.data_temp[obsweewx])))

            if debug > 2:
                logdbg("thread '%s': get_data_api minutely_15: result %s" % (self.name, json.dumps(self.data_temp)))

            # get hourly weather data
            for obsapi, obsweewx in self.hourly_obs.items():
                obsname = self.prefix + str(obsweewx)
                if self.data_temp.get(obsweewx) is not None:
                    # filled with current_weather or minutely_15 data
                    continue
                if debug > 2:
                    logdbg("thread '%s': get_data_api hourly: weewx %s api %s obs %s" % (self.name, str(obsweewx), str(obsapi), str(obsname)))
                obslist = apidata['hourly'].get(obsapi)
                if obslist is None:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api hourly: No value for observation '%s' - '%s'" % (self.name, str(obsapi), str(obsname)))
                    self.data_temp[obsweewx] = (None, None, None)
                    continue
                # Build a dictionary with timestamps as key and the corresponding values
                obsvals = dict(zip(htimelist, obslist))
                obsval = obsvals.get(obshts)
                unitapi = hourly_units.get(obsapi)
                if unitapi is None:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api hourly: No unit for observation %s - %s" % (self.name, str(obsapi), str(obsname)))
                    self.data_temp[obsweewx] = (None, None, None)
                    continue
                unitweewx = OPENMETEOthread.UNIT.get(unitapi)
                if unitweewx is None:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api hourly: Could not convert api unit '%s' to weewx unit" % (self.name, str(unitapi)))
                        self.data_temp[obsweewx] = (None, None, None)
                    continue
                if obsval is None:
                    if log_failure or debug > 0:
                        logwrn("thread '%s': get_data_api hourly: 'None' for observation %s - %s on timestamp %s" % (self.name, str(obsapi), str(obsname), str(obshts)))
                groupweewx = weewx.units.obs_group_dict.get(obsname)
                # snowDepth from meter to mm, weewx snowDepth is weewx group_rain
                # group_rain has no conversation from meter to mm
                if obsweewx == 'snowDepth':
                    obsval = (weeutil.weeutil.to_float(obsval) * 1000)
                    unitweewx = 'mm'
                self.data_temp[obsweewx] = (weeutil.weeutil.to_float(obsval), unitweewx, groupweewx)
                if debug > 2:
                    logdbg("thread '%s': API hourly: weewx=%s result=%s" % (self.name, str(obsweewx), str(self.data_temp[obsweewx])))

            if self.debug > 3:
                logdbg("thread '%s': get_data_api hourly: result %s" % (self.name, json.dumps(self.data_temp)))

            self.data_temp['altitude'] = (altitude,'meter','group_altitude')
            self.data_temp['latitude'] = (latitude,'degree_compass','group_coordinate')
            self.data_temp['longitude'] = (longitude,'degree_compass','group_coordinate')

            night = is_night(self.name, self.data_temp,
                             debug=self.debug,
                             log_success=self.log_success,
                             log_failure=self.log_failure)
            self.data_temp['day'] = (0 if night else 1,'count','group_count')

            self.data_temp['model'] = (self.model,None,None)
            self.data_temp['sourceUrl'] = (obfuscate_secrets(url), None, None)
            weathercode = self.data_temp.get('weathercode', (-1, 'count', 'group_count'))[0]
            self.data_temp['weathercodeAeris'] = (self.get_aeriscode(weathercode), None, None)

            if log_success or debug > 0:
                loginf("thread '%s': get_data_api finished. Number of records processed: %d" % (self.name, len(self.data_temp)))
            if debug > 2:
                logdbg("thread '%s': get_data_api unchecked result %s" % (self.name, json.dumps(self.data_temp)))

            # last check
            weathercode = self.data_temp.get('weathercode')
            if weathercode is None or weathercode[0] is None:
                self.data_temp['weathercode'] = (-1, 'count', 'group_count')
                self.data_temp['weathercodeAeris'] = (self.get_aeriscode(-1), None, None)
                if log_failure or debug > 0:
                    logerr("thread '%s': get_data_api finished. No valid data could be loaded" % (self.name))
            if debug > 2:
                logdbg("thread '%s': get_data_api checked result %s" % (self.name, json.dumps(self.data_temp)))
        except Exception as e:
            exception_output(self.name, e)
        self.last_get_ts = weeutil.weeutil.to_int(time.time())
        return (len(self.data_temp) > 0)

# ============================================================================
#
# Class BRIGHTSKYthread
#
# ============================================================================

class BRIGHTSKYthread(AbstractThread):

    # https://brightsky.dev/docs/#overview--on-stations-and-sources
    # Icons nach https://github.com/jdemaeyer/brightsky/issues/111
    # Icons nach https://github.com/jdemaeyer/brightsky/blob/master/brightsky/web.py#L146-L174
    # condition - dry┃fog┃rain┃sleet┃snow┃hail┃thunderstorm┃
    # icon - clear-day┃clear-night┃partly-cloudy-day┃partly-cloudy-night┃cloudy┃fog┃wind┃rain┃sleet┃snow┃hail┃thunderstorm┃

    # Evapotranspiration/UV-Index:
    # Attention, no capital letters for WeeWX fields. Otherwise the WeeWX field "ET"/"UV" will be formed if no prefix is used!
    # Mapping API observation fields -> WeeWX field, unit, group
    OBSCURRENT = {
        'source_id': ('stationIdBrightsky', 'count', 'group_count'),
        'timestamp': ('generated', 'unix_epoch', 'group_time'),
        'cloud_cover': ('cloudcover', 'percent', 'group_percent'),
        'condition': ('condition', None, None),
        'dew_point': ('dewpoint', 'degree_C', 'group_temperature'),
        'solar_10': ('solar10', 'kilowatt_hour_per_meter_squared', 'group_radiation_energy'),
        'solar_30': ('solar30', 'kilowatt_hour_per_meter_squared', 'group_radiation_energy'),
        'solar_60': ('solar60', 'kilowatt_hour_per_meter_squared', 'group_radiation_energy'),
        'precipitation_10': ('precipitation10', 'mm', 'group_rain'),
        'precipitation_30': ('precipitation30', 'mm', 'group_rain'),
        'precipitation_60': ('precipitation60', 'mm', 'group_rain'),
        'pressure_msl': ('barometer', 'hPa', 'group_pressure'),
        'relative_humidity': ('outHumidity', 'percent', 'group_percent'),
        'visibility': ('visibility', 'meter', 'group_distance'),
        'wind_direction_10': ('windDir10', 'degree_compass', 'group_direction'),
        'wind_direction_30': ('windDir30', 'degree_compass', 'group_direction'),
        'wind_direction_60': ('windDir60', 'degree_compass', 'group_direction'),
        'wind_speed_10': ('windSpeed10', 'km_per_hour', 'group_speed'),
        'wind_speed_30': ('windSpeed30', 'km_per_hour', 'group_speed'),
        'wind_speed_60': ('windSpeed60', 'km_per_hour', 'group_speed'),
        'wind_gust_direction_10': ('windGustDir10', 'degree_compass', 'group_direction'),
        'wind_gust_direction_30': ('windGustDir30', 'degree_compass', 'group_direction'),
        'wind_gust_direction_60': ('windGustDir60', 'degree_compass', 'group_direction'),
        'wind_gust_speed_10': ('windGust10', 'km_per_hour', 'group_speed'),
        'wind_gust_speed_30': ('windGust30', 'km_per_hour', 'group_speed'),
        'wind_gust_speed_60': ('windGust60', 'km_per_hour', 'group_speed'),
        'sunshine_30': ('sunshineDur30', 'minute', 'group_deltatime'),
        'sunshine_60': ('sunshineDur60', 'minute', 'group_deltatime'),
        'temperature': ('outTemp', 'degree_C', 'group_temperature'),
        'icon': ('icon', None, None)
    }

    OBSWEATHER = {
        'timestamp': ('generated', 'unix_epoch', 'group_time'),
        'source_id': ('stationIdBrightsky', 'count', 'group_count'),
        'precipitation': ('precipitation', 'mm', 'group_rain'),
        'pressure_msl': ('barometer', 'hPa', 'group_pressure'),
        'sunshine': ('sunshineDur', 'minute', 'group_deltatime'),
        'temperature': ('outTemp', 'degree_C', 'group_temperature'),
        'wind_direction': ('windDir', 'degree_compass', 'group_direction'),
        'wind_speed': ('windSpeed', 'km_per_hour', 'group_speed'),
        'cloud_cover': ('cloudcover', 'percent', 'group_percent'),
        'dew_point': ('dewpoint', 'degree_C', 'group_temperature'),
        'relative_humidity': ('outHumidity', 'percent', 'group_percent'),
        'visibility': ('visibility', 'meter', 'group_distance'),
        'wind_gust_direction': ('windGustDir', 'degree_compass', 'group_direction'),
        'wind_gust_speed': ('windGust', 'km_per_hour', 'group_speed'),
        'condition': ('condition', None, None),
        'precipitation_probability': ('precipitation_probability', 'percent', 'group_percent'),
        'precipitation_probability_6h': ('precipitation_probability_6h', 'percent', 'group_percent'),
        'solar': ('solar', 'kilowatt_hour_per_meter_squared', 'group_radiation_energy'),
        'icon': ('icon', None, None)
    }

    # Mapping API primary source fields -> WeeWX field, unit, group
    SOURCESCURRENT = {
        'id': ('stationIdBrightsky', None, None),
        'dwd_station_id': ('stationIdDWD', None, None),
        'wmo_station_id': ('stationIdWMO', None, None),
        'observation_type': ('observationType', None, None),
        'lat': ('latitude', 'degree_compass', 'group_coordinate'),
        'lon': ('longitude', 'degree_compass', 'group_coordinate'),
        'height': ('altitude', 'meter', 'group_altitude'),
        'station_name': ('stationName', None, None),
        'distance': ('distance', 'meter', 'group_distance')
    }

    SOURCESWEATHER = {
        'id': ('stationIdBrightsky', None, None),
        'dwd_station_id': ('stationIdDWD', None, None),
        'observation_type': ('observationType', None, None),
        'lat': ('latitude', 'degree_compass', 'group_coordinate'),
        'lon': ('longitude', 'degree_compass', 'group_coordinate'),
        'height': ('altitude', 'meter', 'group_altitude'),
        'station_name': ('stationName', None, None),
        'wmo_station_id': ('stationIdWMO', None, None)
    }

    # Mapping API icon field to internal weathercode
    WEATHERCODE = {
        'unknown': -1,
        'clear-day': 0,
        'clear-night': 0,
        'partly-cloudy-day': 2,
        'partly-cloudy-night': 2,
        'cloudy': 4,
        'snow': 73,
        'fog': 45,
        'rain': 63,
        'hail': 77,
        'sleet': 85,
        'thunderstorm': 95,
        'wind': 100
    }

    # Mapping internal weathercode to aeris code
    BRIGHTSKY_AERIS = {
         -1: '::NA',
          0: '::CL',
          2: '::SC',
          4: '::OV',
         73: '::S',
         45: '::BR',
         63: '::R',
         77: '::A',
         85: '::RS',
         95: '::T',
        100: '::WG'
    }



    def get_aeriscode(self, code):
        """ get aeris weathercode from weathercode """
        try:
            x = self.BRIGHTSKY_AERIS[code]
        except (LookupError, TypeError):
            x = self.BRIGHTSKY_AERIS[-1]
        return x

    def get_weathercode(self, icon):
        """ get brightsky weathercode from api icon """
        try:
            x = self.WEATHERCODE[icon]
        except (LookupError, TypeError):
            x = self.WEATHERCODE['unknown']
        return x


    def get_obscurrent(self):
        return BRIGHTSKYthread.OBSCURRENT


    def get_obsweather(self):
        return BRIGHTSKYthread.OBSWEATHER


    def get_sourcescurrent(self):
        return BRIGHTSKYthread.SOURCESCURRENT


    def get_sourcesweather(self):
        return BRIGHTSKYthread.SOURCESWEATHER


    def __init__(self, name, thread_dict, debug=0, log_success=False, log_failure=True):

        super(BRIGHTSKYthread, self).__init__(name=name, thread_dict=thread_dict, debug=debug, log_success=log_success, log_failure=log_failure)

        self.config = thread_dict.get('config')
        self.debug = weeutil.weeutil.to_int(self.config.get('debug', 0))
        self.log_success = weeutil.weeutil.to_bool(self.config.get('log_success', log_success))
        self.log_failure = weeutil.weeutil.to_bool(self.config.get('log_failure', log_failure))

        if self.debug > 0:
            logdbg("thread '%s': init started" % self.name)
        if self.debug > 2:
            logdbg("thread '%s': init config %s" % (self.name, json.dumps(self.config)))

        self.station = self.config.get('station', 'wmo_10688')
        self.station_fallback = self.config.get('station_fallback', 'here')
        self.provider = self.config.get('provider', 'brightsky')
        self.model = self.config.get('model', 'weather')
        self.prefix = self.config.get('prefix', 'current_bs_'+ str(self.model).replace('-', '_') + '_')
        self.source_id = self.config.get('source_id', 'bs-' + str(self.model).replace('_', '-'))
        self.interval_get = weeutil.weeutil.to_int(self.config.get('interval_get', 300))
        self.interval_push = weeutil.weeutil.to_int(self.config.get('interval_push', 30))
        self.expired = weeutil.weeutil.to_int(self.config.get('expired', 600))
        self.icon_path_belchertown = self.config.get('icon_path_belchertown', '')
        self.timezone = self.config.get('timezone', 'Europe/Berlin')
        self.primary_api_query = None
        self.primary_api_query_fallback = None
        self.config_dict = thread_dict.get('config_dict')
        self.engine = thread_dict.get('engine')
        self.data_result = dict()
        self.data_temp = dict()
        self.last_get_ts = 0
        self.last_prepare_ts = 0

        if self.model == 'weather':
            self.current_obs = self.get_obsweather()
            self.sources_obs = self.get_sourcesweather()
        else:
            self.current_obs = self.get_obscurrent()
            self.sources_obs = self.get_sourcescurrent()

        # unit system
        self.unit_system = None
        self.unitsystem = None
        unit_system = self.config.get('unit_system')
        if unit_system is not None:
            unit_system = str(unit_system).upper()
            if unit_system in('US', 'METRIC', 'METRICWX'):
                self.unit_system = unit_system
                if self.unit_system == 'US': self.unitsystem = weewx.US
                elif self.unit_system == 'METRIC': self.unitsystem = weewx.METRIC
                elif self.unit_system == 'METRICWX': self.unitsystem = weewx.METRICWX

        # lang
        self.lang = self.config.get('lang')
        if self.lang is not None:
            self.lang = str(self.lang).lower()
            if self.lang not in('de', 'en'):
                self.lang = None

        self.lat = weeutil.weeutil.to_float(self.config.get('latitude'))
        self.lon = weeutil.weeutil.to_float(self.config.get('longitude'))
        self.alt = weeutil.weeutil.to_float(self.config.get('altitude'))
        if self.station.lower() not in ('thisstation', 'here'):
            spl = str(self.station).lower().split('_')
            if len(spl) >= 2:
                # station id is selected?
                if spl[0] == 'api':
                    self.primary_api_query = '?source_id=%s' % spl[1]
                    self.primary_api_query_fallback = '?lat=%s&lon=%s' % (str(self.lat), str(self.lon))
                elif spl[0] == 'dwd':
                    self.primary_api_query = '?dwd_station_id=%s' % str(spl[1])
                    self.primary_api_query_fallback = '?lat=%s&lon=%s' % (str(self.lat), str(self.lon))
                elif spl[0] == 'wmo':
                    self.primary_api_query = '?wmo_station_id=%s' % str(spl[1])
                    self.primary_api_query_fallback = '?lat=%s&lon=%s' % (str(self.lat), str(self.lon))

            if self.primary_api_query is None:
                # station is a city name or postal code?
                geo = get_geocoding(self.name, self.station, self.lang, debug=self.debug, log_success=self.log_success, log_failure=self.log_failure)
                if geo is not None:
                    self.primary_api_query = self.primary_api_query_fallback = '?lat=%s&lon=%s' % (geo.get('latitude'), geo.get('longitude'))
        else:
            self.primary_api_query = self.primary_api_query_fallback = '?lat=%s&lon=%s' % (str(self.lat), str(self.lon))

        if self.primary_api_query is None:
            raise weewx.ViolatedPrecondition("thread '%s': Configured station or latitude/longitude not valid" % self.name)

        for opsapi, obsweewx in self.current_obs.items():
            obs = obsweewx[0]
            group = obsweewx[2]
            if group is not None:
                weewx.units.obs_group_dict.setdefault(self.prefix + obs, group)

        weewx.units.obs_group_dict.setdefault(self.prefix+'dateTime','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'generated','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'age','group_deltatime')
        weewx.units.obs_group_dict.setdefault(self.prefix+'day','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'expired','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'weathercode','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'weathercodeKey','group_count')
        for opsapi, obsweewx in self.sources_obs.items():
            obs = obsweewx[0]
            group = obsweewx[2]
            if group is not None:
                weewx.units.obs_group_dict.setdefault(self.prefix + obs, group)
        if self.log_success or self.debug > 0:
            loginf("thread '%s': init finished" % self.name)



    def get_data_api(self):
        """ download and process Brightsky API weather data """

        self.data_temp = dict()
        apiin_dict = self.config.get('api_in', configobj.ConfigObj())
        debug = weeutil.weeutil.to_int(apiin_dict.get('debug', self.debug))
        log_success = weeutil.weeutil.to_bool(apiin_dict.get('log_success', self.log_success))
        log_failure = weeutil.weeutil.to_bool(apiin_dict.get('log_failure', self.log_failure))
        attempts_max = weeutil.weeutil.to_int(apiin_dict.get('attempts_max', 1))
        attempts_wait = weeutil.weeutil.to_int(apiin_dict.get('attempts_wait', 10))

        if not weeutil.weeutil.to_bool(apiin_dict.get('enable', False)):
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api is diabled. Enable it in the [api_in] section of station %s" %(self.name, self.station))
            return False

        if debug > 0:
            logdbg("thread '%s': get_data_api started" % (self.name))
        if debug > 2:
            logdbg("thread '%s': get_data_api config %s" %(self.name, json.dumps(apiin_dict)))

        # unit system
        unit_system = None
        unitsystem = None
        u_s = apiin_dict.get('unit_system', self.unit_system)
        if u_s is not None:
            u_s = str(u_s).upper()
            if u_s in('US', 'METRIC', 'METRICWX'):
                unit_system = u_s
                if unit_system == 'US': unitsystem = weewx.US
                elif unit_system == 'METRIC': unitsystem = weewx.METRIC
                elif unit_system == 'METRICWX': unitsystem = weewx.METRICWX

        # lang
        lang = apiin_dict.get('lang', self.lang)
        if lang is not None:
            lang = str(lang).lower()
            if lang not in('de', 'en'):
                lang = None

        if self.model == 'weather':
            # https://api.brightsky.dev/weather?wmo_station_id=10688&tz=Europe/Berlin&units=dwd&date=2023-07-12T10:00+02:00&last_date=2023-07-12T10:00+02:00
            # fallback:
            # https://api.brightsky.dev/weather?lat=49.632270&lon=12.056186&tz=Europe/Berlin&units=dwd&date=2023-07-12T12:00+02:00&last_date=2023-07-12T12:00+02:00
            baseurl = 'https://api.brightsky.dev/weather'
        else:
            # https://api.brightsky.dev/current_weather?wmo_station_id=10688&tz=Europe/Berlin&units=dwd
            # fallback:
            # https://api.brightsky.dev/current_weather?lat=49.632270&lon=12.056186&tz=Europe/Berlin&units=dwd
            baseurl = 'https://api.brightsky.dev/current_weather'

        # primary api query
        params = self.primary_api_query

        # Timezone in which record timestamps will be presented, as tz database name, e.g. Europe/Berlin.
        # Will also be used as timezone when parsing date and last_date, unless these have explicit UTC offsets.
        # If omitted but date has an explicit UTC offset, that offset will be used as timezone.
        # Otherwise will default to UTC.
        params += '&tz=Europe/Berlin'

        # Physical units in which meteorological parameters will be returned. Set to si to use SI units.
        # The default dwd option uses a set of units that is more common in meteorological applications and civil use:
        #                       DWD     SI
        # Cloud cover           %       %
        # Dew point             °C      K
        # Precipitation         mm      kg/m²
        # Pressure              hPa     Pa
        # Relative humidity     %       %
        # Sunshine              min     s
        # Temperature           °C      K
        # Visibility            m       m
        # Wind direction        °       °
        # Wind speed            km/h    m/s
        # Wind gust direction   °       °
        # Wind gust speed       km/h    m/s
        # solar                 kWh/m²  J/m²
        params += '&units=dwd'

        if self.model == 'weather':
            # 2023-07-12T12:34+02:00
            iso_str = datetime.datetime.now().astimezone().isoformat('T', 'minutes')
            # '2023-07-12T12:' + '00' + '+02:00'
            fromdate = iso_str[:14] + '00' + iso_str[16:]
            # '2023-07-12T12:00+02:00'
            todate = fromdate
            # &date=2023-07-12T12:00+02:00&last_date=2023-07-12T12:00+02:00
            params += '&date=%s&last_date=%s' % (fromdate, todate)

        url = baseurl + params

        if debug > 0:
            logdbg("thread '%s': get_data_api url %s" % (self.name, url))

        apidata = dict()
        attempts = 0
        try:
            while attempts <= attempts_max:
                attempts += 1
                response, code = request_api(self.name, url,
                                            debug = self.debug,
                                            log_success = log_success,
                                            log_failure = log_failure)
                
                # logdbg("thread '%s': get_data_api request_api response %s code %d" % (self.name, json.dumps(response), code))
                # logdbg("thread '%s': get_data_api request_api primary_api_query %s" % (self.name, self.primary_api_query))
                # logdbg("thread '%s': get_data_api request_api primary_api_query_fallback %s" % (self.name, self.primary_api_query_fallback))
                # logdbg("thread '%s': get_data_api request_api attempts %d attempts_max %d" % (self.name, attempts, attempts_max))
                # logdbg("thread '%s': get_data_api request_api response type %s" % (self.name, type(response)))
                # logdbg("thread '%s': get_data_api request_api response %s" % (self.name, str(response)))
                if response is not None:
                    apidata = response
                    attempts = attempts_max + 1
                elif code == 404 and attempts <= attempts_max:
                    if self.primary_api_query in url:
                        url = url.replace(self.primary_api_query, self.primary_api_query_fallback)
                    elif self.primary_api_query_fallback in url:
                        url = url.replace(self.primary_api_query_fallback, self.primary_api_query)
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api request_api sent http status code %d" % (self.name, code))
                    if debug > 2:
                        logdbg("thread '%s': get_data_api request_api next try (%d/%d) in %d seconds with fallback url %s" % (self.name, attempts, attempts_max, attempts_wait, url))
                    elif debug > 0:
                        loginf("thread '%s': get_data_api request_api next try (%d/%d) in %d seconds" % (self.name, attempts, attempts_max, attempts_wait))
                    time.sleep(attempts_wait)
                elif attempts <= attempts_max:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api request_api sent http status code %d" % (self.name, code))
                        loginf("thread '%s': get_data_api request_api next try (%d/%d) in %d seconds" % (self.name, attempts, attempts_max, attempts_wait))
                    time.sleep(attempts_wait)
                else:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api api did not send data" % self.name)
                    return False
        except Exception as e:
            exception_output(self.name, e)
            return False

        # logdbg("thread '%s': get_data_api apidata type %s" % (self.name, type(apidata)))
        # logdbg("thread '%s': get_data_api apidata %s" % (self.name, str(apidata)))

        if debug > 2:
            logdbg("thread '%s': get_data_api api unchecked result %s" % (self.name, json.dumps(apidata)))

        # check results
        weather = apidata.get('weather')
        if isinstance(weather, list) and len(weather) > 0:
            # is endpoint weather
            weather = weather[0]
        if weather is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api did not send 'weather' data" % self.name)
            return False

        sources = apidata.get('sources')
        if sources is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api did not send 'sources' data" % self.name)
            return False

        # check unit system
        if unitsystem is None and weather.get('usUnits') is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api did not send unit system and it's not configured in section [api_in]" % (self.name))
            return False

        # logdbg("thread '%s': get_data_api weather type %s" % (self.name, type(weather)))
        # logdbg("thread '%s': get_data_api weather %s" % (self.name, str(weather)))
        # logdbg("thread '%s': get_data_api sources type %s" % (self.name, type(sources)))
        # logdbg("thread '%s': get_data_api sources %s" % (self.name, str(sources)))


        self.data_temp['dateTime'] = (weeutil.weeutil.to_int(time.time()), 'unix_epoch', 'group_time')

        # TODO: check this
        apiunitsystem = weather.get('usUnits')
        if apiunitsystem is None:
            self.data_temp['usUnits'] = (unitsystem, None, None)
        else:
            self.data_temp['usUnits'] = (weeutil.weeutil.to_int(apiunitsystem), None, None)

        # get current weather data
        for obsapi, obsweewx in self.current_obs.items():
            obsname = self.prefix + str(obsweewx[0])
            obsval = weather.get(obsapi)
            if obsval is None:
                if log_failure or debug > 0:
                    logwrn("thread '%s': get_data_api value is 'None' for observation '%s' - '%s'" % (self.name, str(obsapi), str(obsweewx[0])))
            if debug > 2:
                logdbg("thread '%s': get_data_api weewx %s api %s obs %s val %s" % (self.name, str(obsweewx[0]), str(obsapi), str(obsname), str(obsval)))
            if obsapi == 'timestamp':
                # get a datetime object from observation timestamp ISO 8601 Format
                dt = dateutil.parser.isoparse(obsval)
                # convert dt timestamp to unix timestamp
                obsval = weeutil.weeutil.to_int(dt.timestamp())
            # WeeWX value with group?
            elif obsweewx[2] is not None:
                obsval = weeutil.weeutil.to_float(obsval)
            self.data_temp[obsweewx[0]] = (obsval, obsweewx[1], obsweewx[2])

        # get primary source data
        source_id = weather.get('source_id')
        if source_id is not None:
            for source in sources:
                if source.get('id') == source_id:
                    for obsapi, obsweewx in self.sources_obs.items():
                        obsname = self.prefix + str(obsweewx[0])
                        obsval = source.get(obsapi)
                        if obsval is None:
                            if log_failure or debug > 0:
                                logwrn("thread '%s': get_data_api value is 'None' for observation '%s' - '%s'" % (self.name, str(obsapi), str(obsweewx[0])))
                        if debug > 2:
                            logdbg("thread '%s': get_data_api sources weewx=%s api=%s obs=%s val=%s" % (self.name, str(obsweewx[0]), str(obsapi), str(obsname), str(obsval)))
                        # WeeWX value with group?
                        if obsweewx[2] is not None:
                            obsval = weeutil.weeutil.to_float(obsval)
                        self.data_temp[obsweewx[0]] = (obsval, obsweewx[1], obsweewx[2])
                    break

        # convert Brightsky icon to get the weathercode
        brightskyicon = weather.get('icon')
        if brightskyicon is None:
            brightskyicon = 'unknown'

        self.data_temp['weathercode'] = (self.get_weathercode(brightskyicon), 'count', 'group_count')

        night = is_night(self.name, self.data_temp,
                         debug=self.debug,
                         log_success=self.log_success,
                         log_failure=self.log_failure)
        self.data_temp['day'] = (0 if night else 1, 'count', 'group_count')

        self.data_temp['model'] = (self.model,None,None)
        self.data_temp['sourceUrl'] = (obfuscate_secrets(url), None, None)
        weathercode = self.data_temp.get('weathercode', (-1, 'count', 'group_count'))[0]
        self.data_temp['weathercodeAeris'] = (self.get_aeriscode(weathercode), None, None)

        if log_success or debug > 0:
            loginf("thread '%s': get_data_api finished. Number of records processed: %d" % (self.name, len(self.data_temp)))
        if debug > 2:
            logdbg("thread '%s': get_data_api unchecked result %s" % (self.name, json.dumps(self.data_temp)))

        # last check
        weathercode = self.data_temp.get('weathercode')
        if weathercode is None or weathercode[0] is None:
            self.data_temp['weathercode'] = (-1, 'count', 'group_count')
            self.data_temp['weathercodeAeris'] = (self.get_aeriscode(-1), None, None)
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api finished. No valid data could be loaded" % (self.name))
        if debug > 2:
            logdbg("thread '%s': get_data_api checked result %s" % (self.name, json.dumps(self.data_temp)))
        self.last_get_ts = weeutil.weeutil.to_int(time.time())
        return (len(self.data_temp) > 0)



# ============================================================================
#
# Class PWSthread
#
# ============================================================================

class PWSthread(AbstractThread):

    # Evapotranspiration/UV-Index:
    # Attention, no capital letters for WeeWX fields. Otherwise the WeeWX field "ET"/"UV" will be formed if no prefix is used!
    # Mapping API observation fields -> WeeWX field, unit, group
    OBS = {
        'dateTime': ('generated', 'unix_epoch', 'group_time'),
        'outTemp': ('outTemp', 'degree_C', 'group_temperature'),
        'barometer': ('barometer', 'hPa', 'group_pressure'),
        'cloudwatcher_weathercode': ('weathercode', 'count', 'group_count'),
        'cloudwatcher_cloudpercent': ('cloudcover', 'percent', 'group_percent')
    }

    # Mapping API PWS code field to aeris code
    PWS_AERIS = {
        -1: '::NA',
         0: '::CL',
         1: '::FW',
         2: '::SC',
         3: '::BK',
         4: '::OV',
        45: '::F',
        49: '::ZF',
        51: ':L:WP',
        53: '::WP',
        55: ':H:WP',
        56: ':L:ZY',
        57: '::ZY',
        61: ':L:R',
        63: '::R',
        65: ':H:R',
        66: ':L:ZR',
        67: '::ZR',
        68: ':L:RS',
        69: '::RS',
        71: ':L:S',
        73: '::S',
        75: ':H:S',
        80: ':L:RW',
        81: '::RW',
        82: ':H:RW',
        83: ':L:SR',
        84: '::SR',
        85: ':L:SW',
        86: '::SW',
        95: '::T'
    }


    def get_aeriscode(self, code):
        """ get aeris weather code from api code """
        try:
            x = self.PWS_AERIS[code]
        except (LookupError, TypeError):
            x = self.PWS_AERIS[-1]
        return x

    def get_current_obs(self):
        return PWSthread.OBS


    def __init__(self, name, thread_dict, debug=0, log_success=False, log_failure=True):

        super(PWSthread, self).__init__(name=name, thread_dict=thread_dict, debug=debug, log_success=log_success, log_failure=log_failure)

        self.config = thread_dict.get('config')
        self.debug = weeutil.weeutil.to_int(self.config.get('debug', 0))
        self.log_success = weeutil.weeutil.to_bool(self.config.get('log_success', log_success))
        self.log_failure = weeutil.weeutil.to_bool(self.config.get('log_failure', log_failure))

        if self.debug > 0:
            logdbg("thread '%s': init started" % self.name)
        if self.debug > 2:
            logdbg("thread '%s': init config %s" % (self.name, json.dumps(self.config)))

        self.station = self.config.get('station', 'thisstation')
        self.provider = self.config.get('provider', 'pws')
        self.model = self.config.get('model', 'pws')
        self.prefix = self.config.get('prefix', 'pws_')
        self.source_id = self.config.get('source_id', 'pws')
        self.interval_get = weeutil.weeutil.to_int(self.config.get('interval_get', 300))
        self.interval_push = weeutil.weeutil.to_int(self.config.get('interval_push', 30))
        self.expired = weeutil.weeutil.to_int(self.config.get('expired', 600))
        self.icon_path_belchertown = self.config.get('icon_path_belchertown', '')
        self.timezone = self.config.get('timezone', 'Europe/Berlin')
        self.current_obs = self.get_current_obs()
        self.config_dict = thread_dict.get('config_dict')
        self.engine = thread_dict.get('engine')
        self.data_temp = dict()
        self.data_result = dict()
        self.last_get_ts = 0
        self.last_prepare_ts = 0

        # unit system
        self.unit_system = None
        self.unitsystem = None
        unit_system = self.config.get('unit_system')
        if unit_system is not None:
            unit_system = str(unit_system).upper()
            if unit_system in('US', 'METRIC', 'METRICWX'):
                self.unit_system = unit_system
                if self.unit_system == 'US': self.unitsystem = weewx.US
                elif self.unit_system == 'METRIC': self.unitsystem = weewx.METRIC
                elif self.unit_system == 'METRICWX': self.unitsystem = weewx.METRICWX

        # lang
        self.lang = self.config.get('lang')
        if self.lang is not None:
            self.lang = str(self.lang).lower()
            if self.lang not in('de', 'en'):
                self.lang = None

        self.lat = weeutil.weeutil.to_float(self.config.get('latitude'))
        self.lon = weeutil.weeutil.to_float(self.config.get('longitude'))
        self.alt = weeutil.weeutil.to_float(self.config.get('altitude'))
        if self.lat is None or self.lon is None or self.alt is None:
            if self.station.lower() not in ('thisstation', 'here'):
                # station is a city name or postal code
                geo = get_geocoding(self.name, self.station, self.lang, debug=self.debug, log_success=self.log_success, log_failure=self.log_failure)
                if geo is not None:
                    if self.lat is None:
                        self.lat = weeutil.weeutil.to_float(geo.get('latitude'))
                    if self.lon is None:
                        self.lon = weeutil.weeutil.to_float(geo.get('longitude'))
                    if self.alt is None:
                        self.alt = weeutil.weeutil.to_float(geo.get('elevation'))
                else:
                    if self.log_failure or self.debug > 0:
                        logerr("thread '%s': init could not get geodata for station '%s'" % (self.name, self.station))
                    return
            else:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': init configured station is not valid" % self.name)
                return

        weewx.units.obs_group_dict.setdefault(self.prefix+'dateTime','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'generated','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'age','group_deltatime')
        weewx.units.obs_group_dict.setdefault(self.prefix+'day','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'expired','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'weathercode','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'weathercodeKey','group_count')
        for opsapi, obsweewx in self.current_obs.items():
            obs = obsweewx[0]
            group = obsweewx[2]
            if group is not None:
                weewx.units.obs_group_dict.setdefault(self.prefix + obs, group)
        if self.log_success or self.debug > 0:
            loginf("thread '%s': init finished" % self.name)


    def get_data_api(self):
        """ download and process PWS API weather data """

        self.data_temp = dict()
        apiin_dict = self.config.get('api_in', configobj.ConfigObj())
        debug = weeutil.weeutil.to_int(apiin_dict.get('debug', self.debug))
        log_success = weeutil.weeutil.to_bool(apiin_dict.get('log_success', self.log_success))
        log_failure = weeutil.weeutil.to_bool(apiin_dict.get('log_failure', self.log_failure))
        attempts_max = weeutil.weeutil.to_int(apiin_dict.get('attempts_max', 1))
        attempts_wait = weeutil.weeutil.to_int(apiin_dict.get('attempts_wait', 10))

        if not weeutil.weeutil.to_bool(apiin_dict.get('enable', False)):
            if log_success or debug > 0:
                loginf("thread '%s': get_data_api is diabled. Enable it in the [api_in] section of station %s" %(self.name, self.station))
            return False

        if debug > 0:
            logdbg("thread '%s': get_data_api started" % (self.name))
        if debug > 2:
            logdbg("thread '%s': get_data_api config %s" %(self.name, json.dumps(apiin_dict)))

        # unit system
        unit_system = None
        unitsystem = None
        u_s = apiin_dict.get('unit_system', self.unit_system)
        if u_s is not None:
            u_s = str(u_s).upper()
            if u_s in('US', 'METRIC', 'METRICWX'):
                unit_system = u_s
                if unit_system == 'US': unitsystem = weewx.US
                elif unit_system == 'METRIC': unitsystem = weewx.METRIC
                elif unit_system == 'METRICWX': unitsystem = weewx.METRICWX

        # lang
        lang = apiin_dict.get('lang', self.lang)
        if lang is not None:
            lang = str(lang).lower()
            if lang not in('de', 'en'):
                lang = None

        baseurl = 'https://api.weiherhammer-wetter.de/v1/weewx/'

        # Params
        params = ''

        url = baseurl + params

        if debug > 2:
            logdbg("thread '%s': get_data_api url %s" % (self.name, url))

        apidata = dict()
        attempts = 0
        try:
            while attempts <= attempts_max:
                attempts += 1
                response, code = request_api(self.name, url,
                                            debug = self.debug,
                                            log_success = log_success,
                                            log_failure = log_failure)
                ok = True
                if response is None:
                    ok = False
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api request_api sent http status code %d" % (self.name, code))
                else:
                    # check results
                    apidata_temp = response
                    for field, val in self.current_obs.items():
                        if field not in apidata_temp or apidata_temp.get(field) is None:
                            ok = False
                            if attempts <= attempts_max:
                                if log_failure or debug > 0:
                                    logwrn("thread '%s': get_data_api no value for field '%s'" % (self.name, field))
                                    logwrn("thread '%s': get_data_api apidata '%s'" % (self.name, json.dumps(apidata_temp)))
                            else:
                                if log_failure or debug > 0:
                                    logerr("thread '%s': get_data_api no value for field '%s'" % (self.name, field))
                                    logerr("thread '%s': get_data_api apidata '%s'" % (self.name, json.dumps(apidata_temp)))
                            break
                if ok:
                    apidata = response
                    attempts = attempts_max + 1
                elif attempts <= attempts_max:
                    if log_failure or debug > 0:
                        loginf("thread '%s': get_data_api request_api next try (%d/%d) in %d seconds" % (self.name, attempts, attempts_max, attempts_wait))
                    time.sleep(attempts_wait)
                else:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api api did not send data" % self.name)
                    return False
        except Exception as e:
            exception_output(self.name, e)
            return False

        if debug > 2:
            logdbg("thread '%s': get_data_api api unchecked result %s" % (self.name, json.dumps(apidata)))

        # check results
        for field, val in self.current_obs.items():
            if field not in apidata or apidata.get(field) is None:
                if log_failure or debug > 0:
                    logerr("thread '%s': get_data_api no value for field '%s'" % (self.name, field))
                return False

        # check unit system
        if unitsystem is None and apidata.get('usUnits') is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api did not send unit system and it's not configured in section [api_in]" % (self.name))
            return False

        self.data_temp['dateTime'] = (weeutil.weeutil.to_int(time.time()), 'unix_epoch', 'group_time')

        # TODO: check this
        apiunitsystem = apidata.get('usUnits')
        if apiunitsystem is None:
            self.data_temp['usUnits'] = (unitsystem, None, None)
        else:
            self.data_temp['usUnits'] = (weeutil.weeutil.to_int(apiunitsystem), None, None)

        # get current data
        for obsapi, obsweewx in self.current_obs.items():
            obsname = self.prefix + str(obsweewx[0])
            obsval = apidata.get(obsapi)
            if obsval is None:
                if log_failure or debug > 0:
                    logwrn("thread '%s': get_data_api value is 'None' for observation '%s' - '%s'" % (self.name, str(obsapi), str(obsweewx[0])))
            if debug > 2:
                logdbg("thread '%s': get_data_api weewx %s api %s obs %s val %s" % (self.name, str(obsweewx[0]), str(obsapi), str(obsname), str(obsval)))
            # WeeWX value with group?
            if obsweewx[2] is not None:
                obsval = weeutil.weeutil.to_float(obsval)
            self.data_temp[obsweewx[0]] = (obsval, obsweewx[1], obsweewx[2])

        self.data_temp['altitude'] = (self.alt,'meter','group_altitude')
        self.data_temp['latitude'] = (self.lat,'degree_compass','group_coordinate')
        self.data_temp['longitude'] = (self.lon,'degree_compass','group_coordinate')

        night = is_night(self.name, self.data_temp,
                         debug=debug,
                         log_success=log_success,
                         log_failure=log_failure)
        self.data_temp['day'] = (0 if night else 1,'count','group_count')

        self.data_temp['model'] = (self.model,None,None)
        self.data_temp['sourceUrl'] = (obfuscate_secrets(url), None, None)
        weathercode = self.data_temp.get('weathercode', (-1, 'count', 'group_count'))[0]
        self.data_temp['weathercodeAeris'] = (self.get_aeriscode(weathercode), None, None)

        if log_success or debug > 0:
            loginf("thread '%s': get_data_api finished. Number of records processed: %d" % (self.name, len(self.data_temp)))
        if debug > 2:
            logdbg("thread '%s': get_data_api unchecked result %s" % (self.name, json.dumps(self.data_temp)))

        # last check
        weathercode = self.data_temp.get('weathercode')
        if weathercode is None or weathercode[0] is None:
            self.data_temp['weathercode'] = (-1, 'count', 'group_count')
            self.data_temp['weathercodeAeris'] = (self.get_aeriscode(-1), None, None)
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api finished. No valid data could be loaded" % (self.name))
        if debug > 2:
            logdbg("thread '%s': get_data_api checked result %s" % (self.name, json.dumps(self.data_temp)))
        self.last_get_ts = weeutil.weeutil.to_int(time.time())
        return (len(self.data_temp) > 0)

# ============================================================================
#
# Class MOSMIXthread
#
# ============================================================================

class MOSMIXthread(AbstractThread):

    # Evapotranspiration/UV-Index:
    # Attention, no capital letters for WeeWX fields. Otherwise the WeeWX field "ET"/"UV" will be formed if no prefix is used!
    # Mapping API observation fields -> WeeWX field, unit, group
    OBS = {
        'TTT': ('outTemp', 'degree_C', 'group_temperature'),
        'Td': ('dewpoint', 'degree_C', 'group_temperature'),
        'PPPP': ('barometer', 'hPa', 'group_pressure'),
        'FF': ('windSpeed', 'km_per_hour', 'group_speed'),
        'FX1': ('windGust', 'km_per_hour', 'group_speed'),
        'DD': ('windDir', 'degree_compass', 'group_direction'),
        'VV': ('visibility', 'meter', 'group_distance'),
        'RR1c': ('rain', 'mm', 'group_rain'), #TODO is precipitation, not rain!
        'Neff': ('cloudcover', 'percent', 'group_percent'), #TODO check N - total cloud cover vs Neff - effective cloud cover
        'ww': ('weathercode', 'count', 'group_count')
    }

    # Mapping API DWD code field to aeris code
    DWD_AERIS = {
        -1: '::NA',
         0: '::CL',
         1: '::FW',
         2: '::SC',
         3: '::BK',
         4: '::OV',
        45: '::F',
        49: '::ZF',
        51: ':L:WP',
        53: '::WP',
        55: ':H:WP',
        56: ':L:ZY',
        57: '::ZY',
        61: ':L:R',
        63: '::R',
        65: ':H:R',
        66: ':L:ZR',
        67: '::ZR',
        68: ':L:RS',
        69: '::RS',
        71: ':L:S',
        73: '::S',
        75: ':H:S',
        80: ':L:RW',
        81: '::RW',
        82: ':H:RW',
        83: ':L:SR',
        84: '::SR',
        85: ':L:SW',
        86: '::SW',
        95: '::T'
    }


    def get_aeriscode(self, code):
        """ get aeris weather code from api code """
        try:
            x = self.DWD_AERIS[code]
        except (LookupError, TypeError):
            x = self.DWD_AERIS[-1]
        return x


    def get_current_obs(self):
        return MOSMIXthread.OBS


    def __init__(self, name, thread_dict, debug=0, log_success=False, log_failure=True):

        super(MOSMIXthread, self).__init__(name=name, thread_dict=thread_dict, debug=debug, log_success=log_success, log_failure=log_failure)

        self.config = thread_dict.get('config')
        self.debug = weeutil.weeutil.to_int(self.config.get('debug', 0))
        self.log_success = weeutil.weeutil.to_bool(self.config.get('log_success', log_success))
        self.log_failure = weeutil.weeutil.to_bool(self.config.get('log_failure', log_failure))

        if self.debug > 0:
            logdbg("thread '%s': init started" % self.name)
        if self.debug > 2:
            logdbg("thread '%s': init config %s" % (self.name, json.dumps(self.config)))

        self.station = self.config.get('station', 'thisstation')
        self.provider = self.config.get('provider', 'dwd')
        self.model = self.config.get('model', 'mosmix')
        self.prefix = self.config.get('prefix', 'dwd_mosmix_')
        self.source_id = self.config.get('source_id', 'dwd-mosmix')
        self.interval_get = weeutil.weeutil.to_int(self.config.get('interval_get', 300))
        self.interval_push = weeutil.weeutil.to_int(self.config.get('interval_push', 30))
        self.expired = weeutil.weeutil.to_int(self.config.get('expired', 600))
        self.timezone = self.config.get('timezone', 'Europe/Berlin')
        self.icon_path_belchertown = self.config.get('icon_path_belchertown', '')
        self.file_version = self.config.get('file_version', 's') # TODO add to config
        self.current_obs = self.get_current_obs()
        self.config_dict = thread_dict.get('config_dict')
        self.engine = thread_dict.get('engine')
        self.lat = weeutil.weeutil.to_float(self.config.get('latitude'))
        self.lon = weeutil.weeutil.to_float(self.config.get('longitude'))
        self.alt = weeutil.weeutil.to_float(self.config.get('altitude'))
        self.data_temp = dict()
        self.data_result = dict()
        self.last_get_ts = 0
        self.last_prepare_ts = 0

        # unit system
        self.unit_system = None
        self.unitsystem = None
        unit_system = self.config.get('unit_system')
        if unit_system is not None:
            unit_system = str(unit_system).upper()
            if unit_system in('US', 'METRIC', 'METRICWX'):
                self.unit_system = unit_system
                if self.unit_system == 'US': self.unitsystem = weewx.US
                elif self.unit_system == 'METRIC': self.unitsystem = weewx.METRIC
                elif self.unit_system == 'METRICWX': self.unitsystem = weewx.METRICWX

        # lang
        self.lang = self.config.get('lang')
        if self.lang is not None:
            self.lang = str(self.lang).lower()
            if self.lang not in('de', 'en'):
                self.lang = None

        weewx.units.obs_group_dict.setdefault(self.prefix+'dateTime','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'generated','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'age','group_deltatime')
        weewx.units.obs_group_dict.setdefault(self.prefix+'day','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'expired','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'weathercode','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'weathercodeKey','group_count')
        for opsapi, obsweewx in self.current_obs.items():
            obs = obsweewx[0]
            group = obsweewx[2]
            if group is not None:
                weewx.units.obs_group_dict.setdefault(self.prefix + obs, group)
        if self.log_success or self.debug > 0:
            loginf("thread '%s': init finished" % self.name)


    def get_data_api(self):
        """ download and process PWS API weather data """

        self.data_temp = dict()
        apiin_dict = self.config.get('api_in', configobj.ConfigObj())
        debug = weeutil.weeutil.to_int(apiin_dict.get('debug', self.debug))
        log_success = weeutil.weeutil.to_bool(apiin_dict.get('log_success', self.log_success))
        log_failure = weeutil.weeutil.to_bool(apiin_dict.get('log_failure', self.log_failure))
        attempts_max = weeutil.weeutil.to_int(apiin_dict.get('attempts_max', 1))
        attempts_wait = weeutil.weeutil.to_int(apiin_dict.get('attempts_wait', 10))

        if not weeutil.weeutil.to_bool(apiin_dict.get('enable', False)):
            if log_success or debug > 0:
                loginf("thread '%s': get_data_api is diabled. Enable it in the [api_in] section of station %s" %(self.name, self.station))
            return False

        if debug > 0:
            logdbg("thread '%s': get_data_api started" % (self.name))
        if debug > 2:
            logdbg("thread '%s': get_data_api config %s" %(self.name, json.dumps(apiin_dict)))

        # unit system
        unit_system = None
        unitsystem = None
        u_s = apiin_dict.get('unit_system', self.unit_system)
        if u_s is not None:
            u_s = str(u_s).upper()
            if u_s in('US', 'METRIC', 'METRICWX'):
                unit_system = u_s
                if unit_system == 'US': unitsystem = weewx.US
                elif unit_system == 'METRIC': unitsystem = weewx.METRIC
                elif unit_system == 'METRICWX': unitsystem = weewx.METRICWX

        # lang
        lang = apiin_dict.get('lang', self.lang)
        if lang is not None:
            lang = str(lang).lower()
            if lang not in('de', 'en'):
                lang = None

        baseurl = 'https://api.weiherhammer-wetter.de/v1/mosmix/'

        # Params
        params = '?station=%s&type=%s' % (str(self.station).lower(), str(self.file_version).lower())

        url = baseurl + params

        if debug > 2:
            logdbg("thread '%s': get_data_api url %s" % (self.name, url))

        apidata = dict()
        attempts = 0
        try:
            while attempts <= attempts_max:
                attempts += 1
                response, code = request_api(self.name, url,
                                            debug = self.debug,
                                            log_success = log_success,
                                            log_failure = log_failure)
                if response is not None:
                    apidata = response
                    attempts = attempts_max + 1
                elif attempts <= attempts_max:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api request_api sent http status code %d" % (self.name, code))
                        loginf("thread '%s': get_data_api request_api next try (%d/%d) in %d seconds" % (self.name, attempts, attempts_max, attempts_wait))
                    time.sleep(attempts_wait)
                else:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api api did not send data" % self.name)
                    return False
        except Exception as e:
            exception_output(self.name, e)
            return False

        if debug > 2:
            logdbg("thread '%s': get_data_api api unchecked result %s" % (self.name, json.dumps(apidata)))

        # check results

        # check unit system
        if unitsystem is None and apidata.get('usUnits') is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api did not send unit system and it's not configured in section [api_in]" % (self.name))
            return False

        if apidata.get('station') is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api sent no station data" % self.name)
            return False

        if apidata.get('hourly') is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api sent no hourly data" % self.name)
            return False

        # hourly timestamps
        timestamps = apidata['hourly'].get('time')
        if timestamps is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api sent no hourly time periods data" % self.name)
            return False

        if not isinstance(timestamps, list):
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api sent hourly time periods data not as list" % self.name)
            return False

        if len(timestamps) == 0:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api sent hourly time periods without data" % self.name)
            return False

        # current timestamp
        current_time = datetime.datetime.now(pytz.utc)
        current_time_ts = weeutil.weeutil.to_int(current_time.timestamp())

        # start with the next full hour timestamp
        next_hour = current_time.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
        next_hour_ts = weeutil.weeutil.to_int(next_hour.timestamp())

        self.data_temp['dateTime'] = (weeutil.weeutil.to_int(time.time()), 'unix_epoch', 'group_time')
        self.data_temp['generated'] = (weeutil.weeutil.to_int(apidata.get('generated')), 'unix_epoch', 'group_time')
        self.data_temp['generatedISO'] = (apidata.get('generatedISO'), None, None)
        self.data_temp['obsts'] = (next_hour_ts, 'unix_epoch', 'group_time')
        self.data_temp['obstsISO'] = (get_isodate_from_timestamp(next_hour_ts, self.timezone), None, None)

        # TODO: check this
        apiunitsystem = apidata.get('usUnits')
        if apiunitsystem is None:
            self.data_temp['usUnits'] = (unitsystem, None, None)
        else:
            self.data_temp['usUnits'] = (weeutil.weeutil.to_int(apiunitsystem), None, None)

        try:
            # get hourly weather data
            for obsapi, obsweewx in self.current_obs.items():
                obsname = self.prefix + str(obsweewx[0])
                obslist = apidata['hourly'].get(obsapi)
                if obslist is None:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api hourly: No value for observation '%s' - '%s'" % (self.name, str(obsapi), str(obsname)))
                    self.data_temp[obsweewx[0]] = (None, obsweewx[1], obsweewx[2])
                    continue
                # Build a dictionary with timestamps as key and the corresponding values
                obsvals = dict(zip(timestamps, obslist))
                obsval = obsvals.get(next_hour_ts)
                if obsval is None:
                    if log_failure or debug > 0:
                        logwrn("thread '%s': get_data_api hourly: 'None' for observation %s - %s on timestamp %s" % (self.name, str(obsapi), str(obsname), str(next_hour_ts)))
                self.data_temp[obsweewx[0]] = (weeutil.weeutil.to_float(obsval), obsweewx[1], obsweewx[2])
                if debug > 2:
                    logdbg("thread '%s': API hourly: weewx=%s result=%s" % (self.name, str(obsweewx[0]), str(self.data_temp[obsweewx[0]])))

            if 'outTemp' in self.data_temp and self.data_temp.get('outTemp') is not None:
                if 'dewpoint' in self.data_temp and self.data_temp.get('dewpoint') is not None:
                    outTemp = weeutil.weeutil.to_float(self.data_temp.get('outTemp')[0])
                    dewpoint = weeutil.weeutil.to_float(self.data_temp.get('dewpoint')[0])
                    outHumidity = get_humidity(self.name, outTemp, dewpoint, debug=debug, log_success=log_success, log_failure=log_failure)
                    if outHumidity is not None:
                        self.data_temp['outHumidity'] = (weeutil.weeutil.to_float(outHumidity), 'percent', 'group_percent')

            if self.debug > 3:
                logdbg("thread '%s': get_data_api hourly: result %s" % (self.name, json.dumps(self.data_temp)))

            # station data
            station = apidata.get('station', dict())
            self.data_temp['altitude'] = (station.get('elevation', self.alt), 'meter', 'group_altitude')
            self.data_temp['latitude'] = (station.get('latitude', self.lat), 'degree_compass', 'group_coordinate')
            self.data_temp['longitude'] = (station.get('longitude', self.lon), 'degree_compass', 'group_coordinate')
            self.data_temp['wmo_code'] = (station.get('wmo_code'), None, None)

            night = is_night(self.name, self.data_temp,
                             debug=self.debug,
                             log_success=self.log_success,
                             log_failure=self.log_failure)
            self.data_temp['day'] = (0 if night else 1, 'count', 'group_count')

            self.data_temp['model'] = (self.model,None,None)
            self.data_temp['source'] = (apidata.get('source'), None, None)
            self.data_temp['sourceUrl'] = (obfuscate_secrets(url), None, None)
            weathercode = self.data_temp.get('weathercode', (-1, 'count', 'group_count'))[0]
            self.data_temp['weathercodeAeris'] = (self.get_aeriscode(weathercode), None, None)

            if log_success or debug > 0:
                loginf("thread '%s': get_data_api finished. Number of records processed: %d" % (self.name, len(self.data_temp)))
            if debug > 2:
                logdbg("thread '%s': get_data_api unchecked result %s" % (self.name, json.dumps(self.data_temp)))

            # last check
            weathercode = self.data_temp.get('weathercode')
            if weathercode is None or weathercode[0] is None:
                self.data_temp['weathercode'] = (-1, 'count', 'group_count')
                self.data_temp['weathercodeAeris'] = (self.get_aeriscode(-1), None, None)
                if log_failure or debug > 0:
                    logerr("thread '%s': get_data_api finished. No valid data could be loaded" % (self.name))
            if debug > 2:
                logdbg("thread '%s': get_data_api checked result %s" % (self.name, json.dumps(self.data_temp)))
        except Exception as e:
            exception_output(self.name, e)
        self.last_get_ts = weeutil.weeutil.to_int(time.time())
        return (len(self.data_temp) > 0)



# ============================================================================
#
# Class AERISthread
#
# ============================================================================

class AERISthread(AbstractThread):

    # Evapotranspiration/UV-Index:
    # Attention, no capital letters for WeeWX fields. Otherwise the WeeWX field "ET"/"UV" will be formed if no prefix is used!
    # Mapping API observation fields -> WeeWX field, unit, group
    OBSMETAR = {
        'timestamp': ('generated', 'unix_epoch', 'group_time'),
        'dateTimeISO': ('generatedISO', None, None),
        'tempC': ('outTemp', 'degree_C', 'group_temperature'),
        'dewpointC': ('dewpoint', 'degree_C', 'group_temperature'),
        'heatindexC': ('heatindex', 'degree_C', 'group_temperature'),
        'windchillC': ('windchill', 'degree_C', 'group_temperature'),
        'feelslikeC': ('feelslike', 'degree_C', 'group_temperature'),
        'humidity': ('outHumidity', 'percent', 'group_percent'),
        'spressureMB': ('pressure', 'mbar', 'group_pressure'),
        'pressureMB': ('barometer', 'mbar', 'group_pressure'),
        'altimeterMB': ('altimeter', 'mbar', 'group_pressure'),
        'windKPH': ('wind', 'km_per_hour', 'group_speed'),
        'windSpeedKPH': ('windSpeed', 'km_per_hour', 'group_speed'),
        'windDirDEG': ('windDir', 'degree_compass', 'group_direction'),
        'windDir': ('windDirCompass', None, None),
        'windGustKPH': ('windGust', 'km_per_hour', 'group_speed'),
        'visibilityKM': ('visibility', 'km', 'group_distance'),
        'weather': ('weather', None, None),
        'weatherCoded': ('weatherCoded', None, None),
        'weatherPrimary': ('weatherPrimary', None, None),
        'weatherPrimaryCoded': ('weatherPrimaryCoded', None, None),
        'cloudsCoded': ('cloudsCoded', None, None),
        'icon': ('icon', None, None),
        'isDay': ('isDay', 'count', 'group_count'),
        'snowDepth': ('snowDepth', 'cm', 'group_rain'),
        'precipMM': ('rain', 'mm', 'group_rain'), # TODO only rain?
        'solradWM2': ('solarRad','watt_per_meter_squared','group_radiation'),
        'light': ('light','percent','group_percent'),
        'uvi': ('uvi','uv_index','group_uv'),
        'sky': ('cloudcover', 'percent', 'group_percent')
    }

    OBSCONDITIONS = {
        'timestamp': ('generated', 'unix_epoch', 'group_time'),
        'dateTimeISO': ('generatedISO', None, None),
        'tempC': ('outTemp', 'degree_C', 'group_temperature'),
        'feelslikeC': ('feelslike', 'degree_C', 'group_temperature'),
        'dewpointC': ('dewpoint', 'degree_C', 'group_temperature'),
        'humidity': ('humidity', 'percent', 'group_percent'),
        'pressureMB': ('barometer', 'mbar', 'group_pressure'),
        'windDir': ('windDirCompass', None, None),
        'windDirDEG': ('windDir', 'degree_compass', 'group_direction'),
        'windSpeedKPH': ('windSpeed', 'km_per_hour', 'group_speed'),
        'windGustKPH': ('windGust', 'km_per_hour', 'group_speed'),
        'precipMM': ('rain', 'mm', 'group_rain'),
        'precipRateMM': ('rainRate', 'mm', 'group_rain'),
        'snowCM': ('snow', 'cm', 'group_rain'),
        'snowRateCM': ('snowRate', 'cm', 'group_rain'),
        'pop': ('precipitation_probability', 'percent', 'group_percent'),
        'visibilityKM': ('visibility', 'km', 'group_distance'),
        'sky': ('cloudcover', 'percent', 'group_percent'),
        'cloudsCoded': ('cloudsCoded', None, None),
        'weather': ('weather', None, None),
        'weatherCoded': ('weatherCoded', None, None),
        'weatherPrimary': ('weatherPrimary', None, None),
        'weatherPrimaryCoded': ('weatherPrimaryCoded', None, None),
        'icon': ('icon', None, None),
        'solradWM2': ('solarRad','watt_per_meter_squared','group_radiation'),
        'uvi': ('uvi','uv_index','group_uv'),
        'isDay': ('isDay', 'count', 'group_count'),
        'spressureMB': ('pressure', 'mbar', 'group_pressure'),
        'altimeterMB': ('altimeter', 'mbar', 'group_pressure')
    }


    def get_obsmetar(self):
        return AERISthread.OBSMETAR


    def get_obsconditions(self):
        return AERISthread.OBSCONDITIONS


    def __init__(self, name, thread_dict, debug=0, log_success=False, log_failure=True):

        super(AERISthread, self).__init__(name=name, thread_dict=thread_dict, debug=debug, log_success=log_success, log_failure=log_failure)

        self.config = thread_dict.get('config')
        self.debug = weeutil.weeutil.to_int(self.config.get('debug', 0))
        self.log_success = weeutil.weeutil.to_bool(self.config.get('log_success', log_success))
        self.log_failure = weeutil.weeutil.to_bool(self.config.get('log_failure', log_failure))

        if self.debug > 0:
            logdbg("thread '%s': init started" % self.name)
        if self.debug > 2:
            logdbg("thread '%s': init config %s" % (self.name, json.dumps(self.config)))

        self.station = self.config.get('station', 'here')
        self.provider = self.config.get('provider', 'aeris')
        self.model = self.config.get('model', 'metar')
        self.prefix = self.config.get('prefix', 'current_aeris_'+ str(self.model).replace('-', '_') + '_')
        self.source_id = self.config.get('source_id', 'aeris-' + str(self.model).replace('_', '-'))
        self.interval_get = weeutil.weeutil.to_int(self.config.get('interval_get', 300))
        self.interval_push = weeutil.weeutil.to_int(self.config.get('interval_push', 30))
        self.expired = weeutil.weeutil.to_int(self.config.get('expired', 600))
        self.icon_path_belchertown = self.config.get('icon_path_belchertown', '')
        self.timezone = self.config.get('timezone', 'Europe/Berlin')
        self.config_dict = thread_dict.get('config_dict')
        self.engine = thread_dict.get('engine')
        self.lat = weeutil.weeutil.to_float(self.config.get('latitude'))
        self.lon = weeutil.weeutil.to_float(self.config.get('longitude'))
        self.alt = weeutil.weeutil.to_float(self.config.get('altitude'))
        self.data_result = dict()
        self.data_temp = dict()
        self.last_get_ts = 0
        self.last_prepare_ts = 0

        if self.model == 'metar':
            self.current_obs = self.get_obsmetar()
        else:
            self.current_obs = self.get_obsconditions()

        # unit system
        self.unit_system = None
        self.unitsystem = None
        unit_system = self.config.get('unit_system')
        if unit_system is not None:
            unit_system = str(unit_system).upper()
            if unit_system in('US', 'METRIC', 'METRICWX'):
                self.unit_system = unit_system
                if self.unit_system == 'US': self.unitsystem = weewx.US
                elif self.unit_system == 'METRIC': self.unitsystem = weewx.METRIC
                elif self.unit_system == 'METRICWX': self.unitsystem = weewx.METRICWX

        # lang
        self.lang = self.config.get('lang')
        if self.lang is not None:
            self.lang = str(self.lang).lower()
            if self.lang not in('de', 'en'):
                self.lang = None

        weewx.units.obs_group_dict.setdefault(self.prefix+'dateTime','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'generated','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'age','group_deltatime')
        weewx.units.obs_group_dict.setdefault(self.prefix+'day','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'expired','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'weathercode','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'weathercodeKey','group_count')
        for opsapi, obsweewx in self.current_obs.items():
            obs = obsweewx[0]
            group = obsweewx[2]
            if group is not None:
                weewx.units.obs_group_dict.setdefault(self.prefix + obs, group)
        if self.log_success or self.debug > 0:
            loginf("thread '%s': init finished" % self.name)



    def get_data_api(self):
        """ download and process PWS API weather data """

        self.data_temp = dict()
        apiin_dict = self.config.get('api_in', configobj.ConfigObj())
        debug = weeutil.weeutil.to_int(apiin_dict.get('debug', self.debug))
        log_success = weeutil.weeutil.to_bool(apiin_dict.get('log_success', self.log_success))
        log_failure = weeutil.weeutil.to_bool(apiin_dict.get('log_failure', self.log_failure))
        attempts_max = weeutil.weeutil.to_int(apiin_dict.get('attempts_max', 1))
        attempts_wait = weeutil.weeutil.to_int(apiin_dict.get('attempts_wait', 10))

        if not weeutil.weeutil.to_bool(apiin_dict.get('enable', False)):
            if log_success or debug > 0:
                loginf("thread '%s': get_data_api is diabled. Enable it in the [api_in] section of station %s" %(self.name, self.station))
            return False

        if debug > 0:
            logdbg("thread '%s': get_data_api started" % (self.name))
        if debug > 2:
            logdbg("thread '%s': get_data_api config %s" %(self.name, json.dumps(apiin_dict)))

        api_id = apiin_dict.get('api_id')
        api_secret = apiin_dict.get('api_secret')

        if api_id is None:
            if log_failure or debug > 0:
                loginf("thread '%s': get_data_api required 'api_id' in the [api_in] section of station %s is not valid" %(self.name, self.station))
            return False
        if api_secret is None:
            if log_failure or debug > 0:
                loginf("thread '%s': get_data_api required 'api_secret' in the [api_in] section of station %s is not valid" %(self.name, self.station))
            return False

        # unit system
        unit_system = None
        unitsystem = None
        u_s = apiin_dict.get('unit_system', self.unit_system)
        if u_s is not None:
            u_s = str(u_s).upper()
            if u_s in('US', 'METRIC', 'METRICWX'):
                unit_system = u_s
                if unit_system == 'US': unitsystem = weewx.US
                elif unit_system == 'METRIC': unitsystem = weewx.METRIC
                elif unit_system == 'METRICWX': unitsystem = weewx.METRICWX

        # lang
        lang = apiin_dict.get('lang', self.lang)
        if lang is not None:
            lang = str(lang).lower()
            if lang not in('de', 'en'):
                lang = None

        #baseurl = 'https://api.aerisapi.com/observations/closest'
        # Params
        #params = '?p=%s,%s&format=json&filter=metar&datasource=NOAA_METAR&limit=1&client_id=%s&client_secret=%s' % (str(self.lat), str(self.lon), api_id, api_secret)

        if self.model == 'metar':
            # https://api.aerisapi.com/observations/49.632270,12.056186?format=json&filter=metar&limit=1&client_id=XXX&client_secret=XXX
            baseurl = 'https://api.aerisapi.com/observations/%s,%s?format=json&filter=metar&limit=1&client_id=%s&client_secret=%s'
        
        else:
            # https://api.aerisapi.com/conditions/49.632270,12.056186?format=json&plimit=1&filter=1min&client_id=XXX&client_secret=XXX
            baseurl = 'https://api.aerisapi.com/conditions/%s,%s?format=json&plimit=1&filter=1min&client_id=%s&client_secret=%s'

        baseurl = baseurl % (str(self.lat), str(self.lon), api_id, api_secret)

        params = ''

        # Filter TODO: get it from OBS
        # filter = '&fields=id,dataSource,place,ob.dateTimeISO'
        # filter += ',ob.tempC,ob.dewpointC,ob.heatindexC,ob.feelslikeC,ob.windchillC'
        # filter += ',ob.humidity,ob.uvi,ob.snowDepthCM,ob.precipMM'
        # filter += ',ob.spressureMB,ob.pressureMB,ob.altimeterMB'
        # filter += ',ob.windKPH,ob.windSpeedKPH,ob.windDir,ob.windGustKPH'
        # filter += ',ob.visibilityKM,ob.sky,ob.isDay,ob.weather,ob.weatherPrimaryCoded,ob.icon'

        #url = baseurl + params + filter
        url = baseurl + params

        if debug > 2:
            logdbg("thread '%s': get_data_api url %s" % (self.name, url))

        apidata_temp = dict()
        attempts = 0
        try:
            while attempts <= attempts_max:
                attempts += 1
                response, code = request_api(self.name, url,
                                            debug = self.debug,
                                            log_success = log_success,
                                            log_failure = log_failure)
                if response is not None:
                    apidata_temp = response
                    attempts = attempts_max + 1
                elif attempts <= attempts_max:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api request_api sent http status code %d" % (self.name, code))
                        loginf("thread '%s': get_data_api request_api next try (%d/%d) in %d seconds" % (self.name, attempts, attempts_max, attempts_wait))
                    time.sleep(attempts_wait)
                else:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api api did not send data" % self.name)
                    return False
        except Exception as e:
            exception_output(self.name, e)
            return False

        if debug > 2:
            logdbg("thread '%s': get_data_api api unchecked result %s" % (self.name, json.dumps(apidata_temp)))

        # check results
        # for field, val in self.current_obs.items():
            # if field not in apidata or apidata.get(field) is None:
                # if log_failure or debug > 0:
                    # logerr("thread '%s': get_data_api no value for field '%s'" % (self.name, field))
                # return False

        apidata = dict()
        try:
            if self.model == 'metar':
                apidata = apidata_temp['response']['ob']
            else:
                apidata = apidata_temp['response'][0]['periods'][0]
        except Exception as e:
            exception_output(self.name, e)
            return False

        if debug > 2:
            logdbg("thread '%s': get_data_api api result %s" % (self.name, json.dumps(apidata)))

        # check unit system
        if unitsystem is None and apidata.get('usUnits') is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api did not send unit system and it's not configured in section [api_in]" % (self.name))
            return False

        self.data_temp['dateTime'] = (weeutil.weeutil.to_int(time.time()), 'unix_epoch', 'group_time')

        # TODO: check this
        apiunitsystem = apidata.get('usUnits')
        if apiunitsystem is None:
            self.data_temp['usUnits'] = (unitsystem, None, None)
        else:
            self.data_temp['usUnits'] = (weeutil.weeutil.to_int(apiunitsystem), None, None)

        # get current data
        for obsapi, obsweewx in self.current_obs.items():
            obsname = self.prefix + str(obsweewx[0])
            obsval = apidata.get(obsapi)
            if obsval is None:
                if log_failure or debug > 0:
                    logwrn("thread '%s': get_data_api value is 'None' for observation '%s' - '%s'" % (self.name, str(obsapi), str(obsweewx[0])))
            if debug > 2:
                logdbg("thread '%s': get_data_api weewx=%s api=%s obs=%s val=%s" % (self.name, str(obsweewx[0]), str(obsapi), str(obsname), str(obsval)))
            # WeeWX value with group?
            if obsweewx[2] is not None:
                obsval = weeutil.weeutil.to_float(obsval)
            self.data_temp[obsweewx[0]] = (obsval, obsweewx[1], obsweewx[2])

        self.data_temp['altitude'] = (self.alt,'meter','group_altitude')
        self.data_temp['latitude'] = (self.lat,'degree_compass','group_coordinate')
        self.data_temp['longitude'] = (self.lon,'degree_compass','group_coordinate')

        night = is_night(self.name, self.data_temp,
                         debug=debug,
                         log_success=log_success,
                         log_failure=log_failure)
        self.data_temp['day'] = (0 if night else 1,'count','group_count')

        self.data_temp['model'] = (self.model,None,None)
        self.data_temp['sourceUrl'] = (obfuscate_secrets(url), None, None)
        self.data_temp['weathercodeAeris'] = (self.data_temp.get('weatherPrimaryCoded', ('::NA', None, None))[0], None, None)

        if log_success or debug > 0:
            loginf("thread '%s': get_data_api finished. Number of records processed: %d" % (self.name, len(self.data_temp)))
        if debug > 2:
            logdbg("thread '%s': get_data_api unchecked result %s" % (self.name, json.dumps(self.data_temp)))
        self.last_get_ts = weeutil.weeutil.to_int(time.time())
        return (len(self.data_temp) > 0)



# ============================================================================
#
# Class OPENWEATHERthread
#
# ============================================================================

class OPENWEATHERthread(AbstractThread):

    # https://openweathermap.org/weather-conditions
    # mapping API code to aeris code
    OWM_AERIS = {
         -1: '::NA',
        800: '::CL',
        801: '::FW',
        802: '::SC',
        803: '::BK',
        804: '::OV',
        200: ':L:TR',
        201: '::TR',
        202: ':H:TR',
        210: ':L:T',
        211: '::T',
        212: ':H:T',
        221: '::T',
        230: ':L:TL',
        231: '::TL',
        232: ':H:TL',
        300: ':L:L',
        301: '::L',
        302: ':H:L',
        310: ':L:L',
        311: '::L',
        312: ':H:L',
        500: ':L:R',
        501: '::R',
        502: ':H:R',
        503: ':VH:R',
        504: ':VH:R',
        511: '::ZR',
        520: ':L:RW',
        521: '::RW',
        522: ':H:RW',
        531: '::RW',
        600: ':L:S',
        601: '::S',
        602: ':H:S',
        611: '::RS',
        612: ':L:RS',
        613: '::RS',
        615: ':L:WM',
        616: '::WM',
        620: ':L:SW',
        621: '::SW',
        622: ':H:SW',
        701: '::BR',
        711: '::K',
        721: '::H',
        731: '::BN',
        741: '::F',
        751: '::BN',
        761: '::BD',
        762: '::VA',
        771: '::WG',
        781: '::TO',
    }

    # Evapotranspiration/UV-Index:
    # Attention, no capital letters for WeeWX fields. Otherwise the WeeWX field "ET"/"UV" will be formed if no prefix is used!
    # Mapping API observation fields -> WeeWX field, unit, group
    OBS = {
        'dt': ('generated', 'unix_epoch', 'group_time'),
        'visibility': ('visibility', 'meter', 'group_distance'),
        'timezone': ('tz', 'count', 'group_count'),
        'name': ('name', None, None)
    }

    OBSWEATHER = {
        'id': ('weathercode', None, None),
        'main': ('weather', None, None),
        'description': ('description', None, None)
    }

    OBSMAIN = {
        'temp': ('outTemp', 'degree_C', 'group_temperature'),
        'feels_like': ('feelslike', 'degree_C', 'group_temperature'),
        'temp_min': ('outTemp_min', 'degree_C', 'group_temperature'),
        'temp_max': ('outTemp_max', 'degree_C', 'group_temperature'),
        'pressure': ('barometer', 'hPa', 'group_pressure'),
        'humidity': ('humidity', 'percent', 'group_percent')
    }

    OBSWIND = {
        'deg': ('windDir', 'degree_compass', 'group_direction'),
        'speed': ('windSpeed', 'meter_per_second', 'group_speed')
    }

    OBSCLOUDS = {
        'all': ('cloudcover', 'percent', 'group_percent')
    }


    def get_aeriscode(self, code):
        """ get aeris weather code from api code """
        try:
            x = self.OWM_AERIS[code]
        except (LookupError, TypeError):
            x = self.OWM_AERIS[-1]
        return x


    def get_current_obs(self):
        return OPENWEATHERthread.OBS


    def get_current_obsweather(self):
        return OPENWEATHERthread.OBSWEATHER


    def get_current_obsmain(self):
        return OPENWEATHERthread.OBSMAIN


    def get_current_obswind(self):
        return OPENWEATHERthread.OBSWIND


    def get_current_obsclouds(self):
        return OPENWEATHERthread.OBSCLOUDS


    def __init__(self, name, thread_dict, debug=0, log_success=False, log_failure=True):

        super(OPENWEATHERthread, self).__init__(name=name, thread_dict=thread_dict, debug=debug, log_success=log_success, log_failure=log_failure)

        self.config = thread_dict.get('config')
        self.debug = weeutil.weeutil.to_int(self.config.get('debug', 0))
        self.log_success = weeutil.weeutil.to_bool(self.config.get('log_success', log_success))
        self.log_failure = weeutil.weeutil.to_bool(self.config.get('log_failure', log_failure))

        if self.debug > 0:
            logdbg("thread '%s': init started" % self.name)
        if self.debug > 2:
            logdbg("thread '%s': init config %s" % (self.name, json.dumps(self.config)))

        self.station = self.config.get('station', 'here')
        self.provider = self.config.get('provider', 'owm')
        self.model = self.config.get('model', 'owm')
        self.prefix = self.config.get('prefix', 'current_owm_'+ str(self.model).replace('-', '_') + '_')
        self.source_id = self.config.get('source_id', 'owm-' + str(self.model).replace('_', '-'))
        self.interval_get = weeutil.weeutil.to_int(self.config.get('interval_get', 300))
        self.interval_push = weeutil.weeutil.to_int(self.config.get('interval_push', 30))
        self.expired = weeutil.weeutil.to_int(self.config.get('expired', 600))
        self.icon_path_belchertown = self.config.get('icon_path_belchertown', '')
        self.timezone = self.config.get('timezone', 'Europe/Berlin')
        self.config_dict = thread_dict.get('config_dict')
        self.engine = thread_dict.get('engine')

        self.current_obs = self.get_current_obs()
        self.current_obsweather = self.get_current_obsweather()
        self.current_obsmain = self.get_current_obsmain()
        self.current_obswind = self.get_current_obswind()
        self.current_obsclouds = self.get_current_obsclouds()
        self.lat = weeutil.weeutil.to_float(self.config.get('latitude'))
        self.lon = weeutil.weeutil.to_float(self.config.get('longitude'))
        self.alt = weeutil.weeutil.to_float(self.config.get('altitude'))
        self.data_result = dict()
        self.data_temp = dict()
        self.last_get_ts = 0
        self.last_prepare_ts = 0

        # unit system
        self.unit_system = None
        self.unitsystem = None
        unit_system = self.config.get('unit_system')
        if unit_system is not None:
            unit_system = str(unit_system).upper()
            if unit_system in('US', 'METRIC', 'METRICWX'):
                self.unit_system = unit_system
                if self.unit_system == 'US': self.unitsystem = weewx.US
                elif self.unit_system == 'METRIC': self.unitsystem = weewx.METRIC
                elif self.unit_system == 'METRICWX': self.unitsystem = weewx.METRICWX

        # lang
        self.lang = self.config.get('lang')
        if self.lang is not None:
            self.lang = str(self.lang).lower()
            if self.lang not in('de', 'en'):
                self.lang = None

        weewx.units.obs_group_dict.setdefault(self.prefix+'dateTime','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'generated','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'age','group_deltatime')
        weewx.units.obs_group_dict.setdefault(self.prefix+'day','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'expired','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'weathercode','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'weathercodeKey','group_count')
        for opsapi, obsweewx in self.current_obs.items():
            obs = obsweewx[0]
            group = obsweewx[2]
            if group is not None:
                weewx.units.obs_group_dict.setdefault(self.prefix + obs, group)
        for opsapi, obsweewx in self.current_obsweather.items():
            obs = obsweewx[0]
            group = obsweewx[2]
            if group is not None:
                weewx.units.obs_group_dict.setdefault(self.prefix + obs, group)
        for opsapi, obsweewx in self.current_obsmain.items():
            obs = obsweewx[0]
            group = obsweewx[2]
            if group is not None:
                weewx.units.obs_group_dict.setdefault(self.prefix + obs, group)
        for opsapi, obsweewx in self.current_obswind.items():
            obs = obsweewx[0]
            group = obsweewx[2]
            if group is not None:
                weewx.units.obs_group_dict.setdefault(self.prefix + obs, group)
        for opsapi, obsweewx in self.current_obsclouds.items():
            obs = obsweewx[0]
            group = obsweewx[2]
            if group is not None:
                weewx.units.obs_group_dict.setdefault(self.prefix + obs, group)
        if self.log_success or self.debug > 0:
            loginf("thread '%s': init finished" % self.name)



    def get_data_api(self):
        """ download and process PWS API weather data """

        self.data_temp = dict()
        apiin_dict = self.config.get('api_in', configobj.ConfigObj())
        debug = weeutil.weeutil.to_int(apiin_dict.get('debug', self.debug))
        log_success = weeutil.weeutil.to_bool(apiin_dict.get('log_success', self.log_success))
        log_failure = weeutil.weeutil.to_bool(apiin_dict.get('log_failure', self.log_failure))
        attempts_max = weeutil.weeutil.to_int(apiin_dict.get('attempts_max', 1))
        attempts_wait = weeutil.weeutil.to_int(apiin_dict.get('attempts_wait', 10))

        if not weeutil.weeutil.to_bool(apiin_dict.get('enable', False)):
            if log_success or debug > 0:
                loginf("thread '%s': get_data_api is diabled. Enable it in the [api_in] section of station %s" %(self.name, self.station))
            return False

        if debug > 0:
            logdbg("thread '%s': get_data_api started" % (self.name))
        if debug > 2:
            logdbg("thread '%s': get_data_api config %s" %(self.name, json.dumps(apiin_dict)))

        api_id = apiin_dict.get('api_id')

        if api_id is None:
            if log_failure or debug > 0:
                loginf("thread '%s': get_data_api required 'api_id' in the [api_in] section of station %s is not valid" %(self.name, self.station))
            return False

        # unit system
        unit_system = None
        unitsystem = None
        u_s = apiin_dict.get('unit_system', self.unit_system)
        if u_s is not None:
            u_s = str(u_s).upper()
            if u_s in('US', 'METRIC', 'METRICWX'):
                unit_system = u_s
                if unit_system == 'US': unitsystem = weewx.US
                elif unit_system == 'METRIC': unitsystem = weewx.METRIC
                elif unit_system == 'METRICWX': unitsystem = weewx.METRICWX

        # lang
        lang = apiin_dict.get('lang', self.lang)
        if lang is not None:
            lang = str(lang).lower()
            if lang not in('de', 'en'):
                lang = None

        baseurl = 'https://api.openweathermap.org/data/2.5/weather?lat=%s&lon=%s&units=metric&lang=%s&appid=%s' % (str(self.lat), str(self.lon), self.lang, api_id)

        # Params
        params = ''

        url = baseurl + params

        if debug > 2:
            logdbg("thread '%s': get_data_api url %s" % (self.name, url))

        apidata = dict()
        attempts = 0
        try:
            while attempts <= attempts_max:
                attempts += 1
                response, code = request_api(self.name, url,
                                            debug = self.debug,
                                            log_success = log_success,
                                            log_failure = log_failure)
                if response is not None:
                    apidata = response
                    attempts = attempts_max + 1
                elif attempts <= attempts_max:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api request_api sent http status code %d" % (self.name, code))
                        loginf("thread '%s': get_data_api request_api next try (%d/%d) in %d seconds" % (self.name, attempts, attempts_max, attempts_wait))
                    time.sleep(attempts_wait)
                else:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api api did not send data" % self.name)
                    return False
        except Exception as e:
            exception_output(self.name, e)
            return False

        if debug > 2:
            logdbg("thread '%s': get_data_api api unchecked result %s" % (self.name, json.dumps(apidata)))

        # check results
        for field, val in self.current_obs.items():
            if field not in apidata or apidata.get(field) is None:
                if log_failure or debug > 0:
                    logerr("thread '%s': get_data_api no value for field '%s'" % (self.name, field))
                return False

        weather = apidata.get('weather')
        if isinstance(weather, list) and len(weather) > 0:
            # TODO: check this
            weather = weather[0]
        if weather is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api did not send 'weather' data" % self.name)
            return False
        for field, val in self.current_obsweather.items():
            if field not in weather or weather.get(field) is None:
                if log_failure or debug > 0:
                    logerr("thread '%s': get_data_api no value for field '%s'" % (self.name, field))
                return False
        main = apidata.get('main')
        if main is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api did not send 'main' data" % self.name)
            return False
        for field, val in self.current_obsmain.items():
            if field not in main or main.get(field) is None:
                if log_failure or debug > 0:
                    logerr("thread '%s': get_data_api no value for field '%s'" % (self.name, field))
                return False
        wind = apidata.get('wind')
        if wind is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api did not send 'wind' data" % self.name)
            return False
        for field, val in self.current_obswind.items():
            if field not in wind or wind.get(field) is None:
                if log_failure or debug > 0:
                    logerr("thread '%s': get_data_api no value for field '%s'" % (self.name, field))
                return False
        clouds = apidata.get('clouds')
        if clouds is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api did not send 'clouds' data" % self.name)
            return False
        for field, val in self.current_obsclouds.items():
            if field not in clouds or clouds.get(field) is None:
                if log_failure or debug > 0:
                    logerr("thread '%s': get_data_api no value for field '%s'" % (self.name, field))
                return False

        # check unit system
        if unitsystem is None and apidata.get('usUnits') is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api did not send unit system and it's not configured in section [api_in]" % (self.name))
            return False

        self.data_temp['dateTime'] = (weeutil.weeutil.to_int(time.time()), 'unix_epoch', 'group_time')

        # TODO: check this
        apiunitsystem = apidata.get('usUnits')
        if apiunitsystem is None:
            self.data_temp['usUnits'] = (unitsystem, None, None)
        else:
            self.data_temp['usUnits'] = (weeutil.weeutil.to_int(apiunitsystem), None, None)

        # get current data
        for obsapi, obsweewx in self.current_obs.items():
            obsname = self.prefix + str(obsweewx[0])
            obsval = apidata.get(obsapi)
            if obsval is None:
                if log_failure or debug > 0:
                    logwrn("thread '%s': get_data_api value is 'None' for observation '%s' - '%s'" % (self.name, str(obsapi), str(obsweewx[0])))
            if debug > 2:
                logdbg("thread '%s': get_data_api weewx=%s api=%s obs=%s val=%s" % (self.name, str(obsweewx[0]), str(obsapi), str(obsname), str(obsval)))
            # WeeWX value with group?
            if obsweewx[2] is not None:
                obsval = weeutil.weeutil.to_float(obsval)
            self.data_temp[obsweewx[0]] = (obsval, obsweewx[1], obsweewx[2])

        for obsapi, obsweewx in self.current_obsweather.items():
            obsname = self.prefix + str(obsweewx[0])
            obsval = weather.get(obsapi)
            if obsval is None:
                if log_failure or debug > 0:
                    logwrn("thread '%s': get_data_api value is 'None' for observation '%s' - '%s'" % (self.name, str(obsapi), str(obsweewx[0])))
            if debug > 2:
                logdbg("thread '%s': get_data_api weewx=%s api=%s obs=%s val=%s" % (self.name, str(obsweewx[0]), str(obsapi), str(obsname), str(obsval)))
            # WeeWX value with group?
            if obsweewx[2] is not None:
                obsval = weeutil.weeutil.to_float(obsval)
            self.data_temp[obsweewx[0]] = (obsval, obsweewx[1], obsweewx[2])

        for obsapi, obsweewx in self.current_obsmain.items():
            obsname = self.prefix + str(obsweewx[0])
            obsval = main.get(obsapi)
            if obsval is None:
                if log_failure or debug > 0:
                    logwrn("thread '%s': get_data_api value is 'None' for observation '%s' - '%s'" % (self.name, str(obsapi), str(obsweewx[0])))
            if debug > 2:
                logdbg("thread '%s': get_data_api weewx=%s api=%s obs=%s val=%s" % (self.name, str(obsweewx[0]), str(obsapi), str(obsname), str(obsval)))
            # WeeWX value with group?
            if obsweewx[2] is not None:
                obsval = weeutil.weeutil.to_float(obsval)
            self.data_temp[obsweewx[0]] = (obsval, obsweewx[1], obsweewx[2])

        for obsapi, obsweewx in self.current_obswind.items():
            obsname = self.prefix + str(obsweewx[0])
            obsval = wind.get(obsapi)
            if obsval is None:
                if log_failure or debug > 0:
                    logwrn("thread '%s': get_data_api value is 'None' for observation '%s' - '%s'" % (self.name, str(obsapi), str(obsweewx[0])))
            if debug > 2:
                logdbg("thread '%s': get_data_api weewx=%s api=%s obs=%s val=%s" % (self.name, str(obsweewx[0]), str(obsapi), str(obsname), str(obsval)))
            # WeeWX value with group?
            if obsweewx[2] is not None:
                obsval = weeutil.weeutil.to_float(obsval)
            self.data_temp[obsweewx[0]] = (obsval, obsweewx[1], obsweewx[2])

        for obsapi, obsweewx in self.current_obsclouds.items():
            obsname = self.prefix + str(obsweewx[0])
            obsval = clouds.get(obsapi)
            if obsval is None:
                if log_failure or debug > 0:
                    logwrn("thread '%s': get_data_api value is 'None' for observation '%s' - '%s'" % (self.name, str(obsapi), str(obsweewx[0])))
            if debug > 2:
                logdbg("thread '%s': get_data_api weewx=%s api=%s obs=%s val=%s" % (self.name, str(obsweewx[0]), str(obsapi), str(obsname), str(obsval)))
            # WeeWX value with group?
            if obsweewx[2] is not None:
                obsval = weeutil.weeutil.to_float(obsval)
            self.data_temp[obsweewx[0]] = (obsval, obsweewx[1], obsweewx[2])

        self.data_temp['altitude'] = (self.alt,'meter','group_altitude')
        self.data_temp['latitude'] = (self.lat,'degree_compass','group_coordinate')
        self.data_temp['longitude'] = (self.lon,'degree_compass','group_coordinate')

        night = is_night(self.name, self.data_temp,
                         debug=debug,
                         log_success=log_success,
                         log_failure=log_failure)
        self.data_temp['day'] = (0 if night else 1,'count','group_count')

        self.data_temp['model'] = (self.model,None,None)
        self.data_temp['sourceUrl'] = (obfuscate_secrets(url), None, None)
        weathercode = self.data_temp.get('weathercode', (-1, 'count', 'group_count'))[0]
        self.data_temp['weathercodeAeris'] = (self.get_aeriscode(weathercode), None, None)

        if log_success or debug > 0:
            loginf("thread '%s': get_data_api finished. Number of records processed: %d" % (self.name, len(self.data_temp)))
        if debug > 2:
            logdbg("thread '%s': get_data_api unchecked result %s" % (self.name, json.dumps(self.data_temp)))

        # last check
        weathercode = self.data_temp.get('weathercode')
        if weathercode is None or weathercode[0] is None:
            self.data_temp['weathercode'] = (-1, 'count', 'group_count')
            self.data_temp['weathercodeAeris'] = (self.get_aeriscode(-1), None, None)
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api finished. No valid data could be loaded" % (self.name))
        if debug > 2:
            logdbg("thread '%s': get_data_api checked result %s" % (self.name, json.dumps(self.data_temp)))
        self.last_get_ts = weeutil.weeutil.to_int(time.time())
        return (len(self.data_temp) > 0)



# ============================================================================
#
# Class TOTALthread
#
# Summary of all thread data to one topic and one file
#
# ============================================================================

class TOTALthread(AbstractThread):

    def __init__(self, name, thread_dict, debug=0, log_success=False, log_failure=True, threads=None):

        super(TOTALthread, self).__init__(name=name, thread_dict=thread_dict, debug=debug, log_success=log_success, log_failure=log_failure, threads=threads)

        self.config = thread_dict.get('config')
        self.debug = weeutil.weeutil.to_int(self.config.get('debug', 0))
        self.log_success = weeutil.weeutil.to_bool(self.config.get('log_success', log_success))
        self.log_failure = weeutil.weeutil.to_bool(self.config.get('log_failure', log_failure))

        if self.debug > 0:
            logdbg("thread '%s': init started" % self.name)
        if self.debug > 2:
            logdbg("thread '%s': init config %s" % (self.name, json.dumps(self.config)))

        self.station = self.config.get('station', 'thisstation')
        self.provider = self.config.get('provider', 'total')
        self.prefix = self.config.get('prefix', 'total_')
        self.source_id = self.config.get('source_id', 'total')
        self.interval_get = weeutil.weeutil.to_int(self.config.get('interval_get', 300))
        self.interval_push = weeutil.weeutil.to_int(self.config.get('interval_push', 30))
        self.expired = weeutil.weeutil.to_int(self.config.get('expired', 600))
        self.timezone = self.config.get('timezone', 'Europe/Berlin')
        self.config_dict = thread_dict.get('config_dict')
        self.engine = thread_dict.get('engine')
        self.data_temp = dict()
        self.data_result = dict()
        self.last_get_ts = 0
        self.last_prepare_ts = 0

        # unit system
        self.unit_system = None
        self.unitsystem = None
        unit_system = self.config.get('unit_system')
        if unit_system is not None:
            unit_system = str(unit_system).upper()
            if unit_system in('US', 'METRIC', 'METRICWX'):
                self.unit_system = unit_system
                if self.unit_system == 'US': self.unitsystem = weewx.US
                elif self.unit_system == 'METRIC': self.unitsystem = weewx.METRIC
                elif self.unit_system == 'METRICWX': self.unitsystem = weewx.METRICWX

        # lang
        self.lang = self.config.get('lang')
        if self.lang is not None:
            self.lang = str(self.lang).lower()
            if self.lang not in('de', 'en'):
                self.lang = None

        self.lat = weeutil.weeutil.to_float(self.config.get('latitude'))
        self.lon = weeutil.weeutil.to_float(self.config.get('longitude'))
        self.alt = weeutil.weeutil.to_float(self.config.get('altitude'))
        if self.lat is None or self.lon is None or self.alt is None:
            if self.station.lower() not in ('thisstation', 'here'):
                # station is a city name or postal code
                geo = get_geocoding(self.name, self.station, self.lang, debug=self.debug, log_success=self.log_success, log_failure=self.log_failure)
                if geo is not None:
                    if self.lat is None:
                        self.lat = weeutil.weeutil.to_float(geo.get('latitude'))
                    if self.lon is None:
                        self.lon = weeutil.weeutil.to_float(geo.get('longitude'))
                    if self.alt is None:
                        self.alt = weeutil.weeutil.to_float(geo.get('elevation'))
                else:
                    if self.log_failure or self.debug > 0:
                        logerr("thread '%s': init could not get geodata for station '%s'" % (self.name, self.station))
                    return
            else:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': init configured station is not valid" % self.name)
                return

        self.model = self.config.get('model', 'pws')
        self.icon_path_belchertown = self.config.get('icon_path_belchertown', '')
        self.threads = threads

        first_delay = weeutil.weeutil.to_int(self.config.get('first_delay', 0))
        if first_delay > 0:
            if self.debug > 0:
                logdbg("thread '%s': init waiting (%d s) for the first threads data completions..." % (self.name, first_delay))
            time.sleep(first_delay)
        if self.log_success or self.debug > 0:
            loginf("thread '%s': init finished" % self.name)


    def get_data_results(self):
        """ download and process current results weather data """

        self.data_temp = dict()
        resultin_dict = self.config.get('result_in', configobj.ConfigObj())
        debug = weeutil.weeutil.to_int(resultin_dict.get('debug', self.debug))
        log_success = weeutil.weeutil.to_bool(resultin_dict.get('log_success', self.log_success))
        log_failure = weeutil.weeutil.to_bool(resultin_dict.get('log_failure', self.log_failure))

        if not weeutil.weeutil.to_bool(resultin_dict.get('enable', False)):
            if log_success or debug > 0:
                loginf("thread '%s': get_data_results is diabled. Enable it in the [result_in] section of station %s" %(self.name, self.station))
            return False

        if debug > 0:
            logdbg("thread '%s': get_data_results started" % (self.name))
        if debug > 2:
            logdbg("thread '%s': get_data_results config %s" %(self.name, json.dumps(resultin_dict)))

        # unit system
        unit_system = None
        unitsystem = None
        u_s = resultin_dict.get('unit_system', self.unit_system)
        if u_s is not None:
            u_s = str(u_s).upper()
            if u_s in('US', 'METRIC', 'METRICWX'):
                unit_system = u_s
                if unit_system == 'US': unitsystem = weewx.US
                elif unit_system == 'METRIC': unitsystem = weewx.METRIC
                elif unit_system == 'METRICWX': unitsystem = weewx.METRICWX

        # lang
        lang = resultin_dict.get('lang', self.lang)
        if lang is not None:
            lang = str(lang).lower()
            if lang not in('de', 'en'):
                lang = None

        threads = self.threads
        for thread_name in threads:
            # get thread config. if total is False continue with next thread
            tconfig = threads[thread_name].get_config()
            #logdbg("thread '%s': get_data_results thread '%s' config %s" % (self.name, thread_name, json.dumps(tconfig)))
            to_total = weeutil.weeutil.to_bool(tconfig.get('to_total', False))
            if not to_total:
                if log_success or debug > 0:
                    loginf("thread '%s': get_data_results total for thread '%s' is disabled" % (self.name, thread_name))
                continue
            # get collected data
            data = None
            if threads[thread_name].get_last_prepare_ts() > 0:
                data = threads[thread_name].get_data_result()
            else:
                # Thread has not yet generated any usable data.
                continue
            if len(data) > 0:
                source_id = data.get('sourceId')
                if source_id is not None:
                    if debug > 2:
                        loginf("thread '%s': get_data_results Thread '%s' has valid source_id %s" % (self.name, thread_name, str(source_id)))
                    self.data_temp[source_id[0]] = data
                elif log_failure or debug > 0:
                    logerr("thread '%s': get_data_results Thread '%s' data has no valid 'source_id'" % (self.name, thread_name))
            elif log_failure or debug > 0:
                logerr("thread '%s': get_data_results Thread '%s' has no valid result data" % (self.name, thread_name))

        if log_success or debug > 0:
            loginf("thread '%s': get_data_results finished. Number of records processed: %d" % (self.name, len(self.data_temp)))
        if debug > 2:
            logdbg("thread '%s': get_data_results result %s" % (self.name, json.dumps(self.data_temp)))

        self.last_get_ts = weeutil.weeutil.to_int(time.time())
        return (len(self.data_temp) > 0)




# ============================================================================
#
# Class CurrentWX
#
# ============================================================================

class CurrentWX(StdService):

    def _create_poi_thread(self, thread_name, station_dict):
        thread_name = "%s_%s" % (SERVICEID, thread_name)
        self.threads[SERVICEID][thread_name] = POIthread(thread_name, station_dict,
                    debug=weeutil.weeutil.to_int(station_dict.get('debug', self.debug)),
                    log_success=weeutil.weeutil.to_bool(station_dict.get('log_success', self.log_success)),
                    log_failure=weeutil.weeutil.to_bool(station_dict.get('log_failure', self.log_failure)))
        self.threads[SERVICEID][thread_name].start()



    def _create_cdc_thread(self, thread_name, station_dict):
        thread_name = "%s_%s" % (SERVICEID, thread_name)
        self.threads[SERVICEID][thread_name] = CDCthread(thread_name, station_dict,
                    debug=weeutil.weeutil.to_int(station_dict.get('debug', self.debug)),
                    log_success=weeutil.weeutil.to_bool(station_dict.get('log_success', self.log_success)),
                    log_failure=weeutil.weeutil.to_bool(station_dict.get('log_failure', self.log_failure)))
        self.threads[SERVICEID][thread_name].start()



    def _create_openmeteo_thread(self, thread_name, station_dict):
        thread_name = "%s_%s" % (SERVICEID, thread_name)
        self.threads[SERVICEID][thread_name] = OPENMETEOthread(thread_name, station_dict,
                    debug=weeutil.weeutil.to_int(station_dict.get('debug', self.debug)),
                    log_success=weeutil.weeutil.to_bool(station_dict.get('log_success', self.log_success)),
                    log_failure=weeutil.weeutil.to_bool(station_dict.get('log_failure', self.log_failure)))
        self.threads[SERVICEID][thread_name].start()



    def _create_brightsky_thread(self, thread_name, station_dict):
        thread_name = "%s_%s" % (SERVICEID, thread_name)
        self.threads[SERVICEID][thread_name] = BRIGHTSKYthread(thread_name, station_dict,
                    debug=weeutil.weeutil.to_int(station_dict.get('debug', self.debug)),
                    log_success=weeutil.weeutil.to_bool(station_dict.get('log_success', self.log_success)),
                    log_failure=weeutil.weeutil.to_bool(station_dict.get('log_failure', self.log_failure)))
        self.threads[SERVICEID][thread_name].start()



    def _create_pws_thread(self, thread_name, station_dict):
        thread_name = "%s_%s" % (SERVICEID, thread_name)
        self.threads[SERVICEID][thread_name] = PWSthread(thread_name, station_dict,
                    debug=weeutil.weeutil.to_int(station_dict.get('debug', self.debug)),
                    log_success=weeutil.weeutil.to_bool(station_dict.get('log_success', self.log_success)),
                    log_failure=weeutil.weeutil.to_bool(station_dict.get('log_failure', self.log_failure)))
        self.threads[SERVICEID][thread_name].start()



    def _create_mosmix_thread(self, thread_name, station_dict):
        thread_name = "%s_%s" % (SERVICEID, thread_name)
        self.threads[SERVICEID][thread_name] = MOSMIXthread(thread_name, station_dict,
                    debug=weeutil.weeutil.to_int(station_dict.get('debug', self.debug)),
                    log_success=weeutil.weeutil.to_bool(station_dict.get('log_success', self.log_success)),
                    log_failure=weeutil.weeutil.to_bool(station_dict.get('log_failure', self.log_failure)))
        self.threads[SERVICEID][thread_name].start()



    def _create_aeris_thread(self, thread_name, station_dict):
        thread_name = "%s_%s" % (SERVICEID, thread_name)
        self.threads[SERVICEID][thread_name] = AERISthread(thread_name, station_dict,
                    debug=weeutil.weeutil.to_int(station_dict.get('debug', self.debug)),
                    log_success=weeutil.weeutil.to_bool(station_dict.get('log_success', self.log_success)),
                    log_failure=weeutil.weeutil.to_bool(station_dict.get('log_failure', self.log_failure)))
        self.threads[SERVICEID][thread_name].start()



    def _create_owm_thread(self, thread_name, station_dict):
        thread_name = "%s_%s" % (SERVICEID, thread_name)
        self.threads[SERVICEID][thread_name] = OPENWEATHERthread(thread_name, station_dict,
                    debug=weeutil.weeutil.to_int(station_dict.get('debug', self.debug)),
                    log_success=weeutil.weeutil.to_bool(station_dict.get('log_success', self.log_success)),
                    log_failure=weeutil.weeutil.to_bool(station_dict.get('log_failure', self.log_failure)))
        self.threads[SERVICEID][thread_name].start()



    def _create_total_thread(self, thread_name, station_dict):
        thread_name = "%s_%s" % (SERVICEID, thread_name)
        self.threads['worker'][thread_name] = TOTALthread(thread_name, station_dict,
                    debug=self.debug,
                    log_success=self.log_success,
                    log_failure=self.log_failure,
                    threads=self.threads[SERVICEID])
        self.threads['worker'][thread_name].start()



    def shutDown(self):
        """ shutdown threads """
        for ii in self.threads[SERVICEID]:
            try:
                self.threads[SERVICEID][ii].shutDown()
            except Exception:
                pass
        for ii in self.threads['worker']:
            try:
                self.threads['worker'][ii].shutDown()
            except Exception:
                pass



    def new_loop_packet(self, event):
        for thread_name in self.threads[SERVICEID]:
            tconfig = self.threads[SERVICEID][thread_name].get_config()
            binding = tconfig.get('binding')
            if not 'loop' in binding:
                continue



    def new_archive_record(self, event):
        for thread_name in self.threads[SERVICEID]:
            tconfig = self.threads[SERVICEID][thread_name].get_config()
            binding = tconfig.get('binding')
            if not 'archive' in binding:
                continue



    def check_section(self, engine, section_dict, section):

        if self.debug > 0:
            logdbg("Service 'CurrentWX': check_section section '%s' started" % (section))

        cancel = False

        # new section configurations apply?
        debug = weeutil.weeutil.to_int(section_dict.get('debug', self.service_dict.get('debug', 0)))
        log_success = weeutil.weeutil.to_bool(section_dict.get('log_success', self.service_dict.get('log_success', False)))
        log_failure = weeutil.weeutil.to_bool(section_dict.get('log_failure', self.service_dict.get('log_success', True)))

        # Check required provider
        provider = section_dict.get('provider')
        if provider: provider = provider.lower()
        if provider not in ('dwd', 'brightsky', 'open-meteo', 'pws', 'aeris', 'owm', 'total'):
            if log_failure or debug > 0:
                logerr("Service 'CurrentWX': check_section section '%s' weather service provider '%s' is not valid. Skip Section" % (section, provider))
            cancel = True
            return cancel, section_dict

        # Check required model
        model = section_dict.get('model')
        if model: model = model.lower()
        if provider == 'dwd':
            if model not in ('poi', 'cdc', 'mosmix'):
                if log_failure or debug > 0:
                    logerr("Service 'CurrentWX': check_section section '%s' weather service provider '%s' - model '%s' is not valid. Skip Section" % (section, provider, model))
                cancel = True
                return cancel, section_dict
        elif provider == 'aeris':
            if model not in ('metar', 'conditions'):
                if log_failure or debug > 0:
                    logerr("Service 'CurrentWX': check_section section '%s' weather service provider '%s' - model '%s' is not valid. Skip Section" % (section, provider, model))
                cancel = True
                return cancel, section_dict
        elif provider == 'brightsky':
            if model not in ('current', 'weather'):
                if log_failure or debug > 0:
                    logerr("Service 'CurrentWX': check_section section '%s' weather service provider '%s' - model '%s' is not valid. Skip Section" % (section, provider, model))
                cancel = True
                return cancel, section_dict
        elif provider == 'open-meteo':
            if model not in OPENMETEOthread.WEATHERMODELS:
                if log_failure or debug > 0:
                    logerr("Service 'CurrentWX': check_section section '%s' weather service provider '%s' - model '%s' is not valid. Skip Section" % (section, provider, model))
                cancel = True
                return cancel, section_dict

        # check required station 
        station = section_dict.get('station')
        if provider in ('dwd', 'brightsky') and station is None:
            if log_failure or debug > 0:
                logerr("Service 'CurrentWX': check_section section '%s' weather service provider '%s' - station '%s' is not valid. Skip Section" % (section, provider, station))
            cancel = True
            return cancel, section_dict

        # possible station altitude
        altitude = section_dict.get('altitude')
        if altitude is not None:
            altitude_t = weeutil.weeutil.option_as_list(altitude)
            if len(altitude_t) >= 2:
                altitude_t[1] = altitude_t[1].lower()
                if altitude_t[1] in ('meter', 'foot'):
                    altitude_vt = weewx.units.ValueTuple(weeutil.weeutil.to_float(altitude_t[0]), altitude_t[1], "group_altitude")
                    section_dict['altitude'] = weewx.units.convert(altitude_vt, 'meter')[0]
                else:
                    section_dict['altitude'] = None
                    if log_failure or debug > 0:
                        logerr("Service 'CurrentWX': check_section section '%s' configured unit '%s' for altitude is not valid, altitude will be ignored" % (section, altitude_t[1]))
            else:
                section_dict['altitude'] = None
                if self.log_failure or self.debug > 0:
                    logerr("Service 'CurrentWX': check_section section '%s' configured altitude '%s' is not valid, altitude will be ignored" % (section, altitude))

        # set default station if not selected and lat or lon is None
        if station is None and (section_dict.get('latitude') is None or section_dict.get('longitude') is None):
            section_dict['station'] = 'thisstation'

        # set default station if not selected and lat or lon is None
        station_fallback = section_dict.get('station_fallback')
        if provider in ('brightsky'):
            if station_fallback is None and (section_dict.get('latitude') is None or section_dict.get('longitude') is None):
                section_dict['station_fallback'] = 'thisstation'

        if station is None and (section_dict.get('latitude') is None or section_dict.get('longitude') is None):
            section_dict['station'] = 'thisstation'

        # using lat/lon/alt from weewx.conf
        if section_dict['station'].lower() in ('thisstation', 'here') or section_dict.get('station_fallback') in ('thisstation', 'here'):
            if section_dict.get('latitude') is None or section_dict.get('longitude') is None:
                section_dict['latitude'] = section_dict.get('latitude', engine.stn_info.latitude_f)
                section_dict['longitude'] = section_dict.get('longitude', engine.stn_info.longitude_f)
            if section_dict.get('altitude') is None:
                section_dict['altitude'] = weewx.units.convert(engine.stn_info.altitude_vt, 'meter')[0]

        # unit system
        unit_system = section_dict.get('unit_system', self.unit_system)
        if unit_system is not None:
            unit_system = str(unit_system).upper()
            if unit_system in('US', 'METRIC', 'METRICWX'):
                section_dict['unit_system'] = unit_system
                if section_dict['unit_system'] == 'US': section_dict['unitsystem'] = weewx.US
                elif section_dict['unit_system'] == 'METRIC': section_dict['unitsystem'] = weewx.METRIC
                elif section_dict['unit_system'] == 'METRICWX': section_dict['unitsystem'] = weewx.METRICWX
            else:
                section_dict['unit_system'] = None

        # lang
        lang = section_dict.get('lang', self.lang)
        if lang is not None:
            lang = str(lang).lower()
            if lang in('de', 'en'):
                section_dict['lang'] = lang
            else:
                section_dict['lang'] = None

        if self.log_success or self.debug > 0:
            loginf("Service 'CurrentWX': check_section section '%s' finished" % (section))

        return cancel, section_dict



    def __init__(self, engine, config_dict):
        super(CurrentWX,self).__init__(engine, config_dict)

        self.service_dict = weeutil.config.accumulateLeaves(config_dict.get('currentwx',configobj.ConfigObj()))
        # service enabled?
        if not weeutil.weeutil.to_bool(self.service_dict.get('enable', False)):
            loginf("Service 'CurrentWX': service is disabled. Enable it in the [currentwx] section of weewx.conf")
            return
        loginf("Service 'CurrentWX': service is enabled")

        self.threads = dict()
        self.threads[SERVICEID] = dict()
        self.threads['worker'] = dict()

        #general configs
        self.debug = weeutil.weeutil.to_int(self.service_dict.get('debug', 0))
        self.log_success = weeutil.weeutil.to_bool(self.service_dict.get('log_success', True))
        self.log_failure = weeutil.weeutil.to_bool(self.service_dict.get('log_failure', True))
        if self.debug > 0:
            logdbg("Service 'CurrentWX': init started")

        # unit system
        self.unit_system = None
        self.unitsystem = None
        unit_system = config_dict.get('unit_system')
        if unit_system is not None:
            unit_system = str(unit_system).upper()
            if unit_system in('US', 'METRIC', 'METRICWX'):
                self.unit_system = unit_system
                if self.unit_system == 'US': self.unitsystem = weewx.US
                elif self.unit_system == 'METRIC': self.unitsystem = weewx.METRIC
                elif self.unit_system == 'METRICWX': self.unitsystem = weewx.METRICWX

        # lang
        self.lang = config_dict.get('lang')
        if self.lang is not None:
            self.lang = str(self.lang).lower()
            if self.lang not in('de', 'en'):
                self.lang = None

        # default configs
        currentwx_dict = config_dict.get('currentwx', configobj.ConfigObj())
        if self.debug > 2:
            logdbg("Service 'CurrentWX': currentwx_dict %s" % (str(json.dumps(currentwx_dict))))

        # section with current weather services only
        current_dict = config_dict.get('currentwx',configobj.ConfigObj()).get('current',configobj.ConfigObj())
        if self.debug > 2:
            logdbg("Service 'CurrentWX': current_dict %s" % (str(json.dumps(current_dict))))

        stations_dict = current_dict.get('stations',configobj.ConfigObj())
        for section in stations_dict.sections:
            if not weeutil.weeutil.to_bool(stations_dict[section].get('enable', False)):
                if self.log_success or self.debug > 0:
                    loginf("Service 'CurrentWX': init current section '%s' is not enabled. Skip section" % section)
                continue

            # build section config
            section_dict = weeutil.config.accumulateLeaves(stations_dict[section])
            provider = str(section_dict.get('provider')).lower()
            model = str(section_dict.get('model')).lower()

            # update general config
            section_dict['result_in'] = weeutil.config.deep_copy(currentwx_dict.get('result_in'))
            section_dict['api_in'] = weeutil.config.deep_copy(currentwx_dict.get('api_in'))
            section_dict['api_out'] = weeutil.config.deep_copy(currentwx_dict.get('api_out'))
            section_dict['mqtt_in'] = weeutil.config.deep_copy(currentwx_dict.get('mqtt_in'))
            section_dict['mqtt_out'] = weeutil.config.deep_copy(currentwx_dict.get('mqtt_out'))
            section_dict['file_in'] = weeutil.config.deep_copy(currentwx_dict.get('file_in'))
            section_dict['file_out'] = weeutil.config.deep_copy(currentwx_dict.get('file_out'))
            section_dict['db_in'] = weeutil.config.deep_copy(currentwx_dict.get('db_in'))
            section_dict['db_out'] = weeutil.config.deep_copy(currentwx_dict.get('db_out'))

            # update current config
            section_dict['result_in'].merge(current_dict.get('result_in', configobj.ConfigObj()))
            section_dict['api_in'].merge(current_dict.get('api_in', configobj.ConfigObj()))
            section_dict['api_out'].merge(current_dict.get('api_out', configobj.ConfigObj()))
            section_dict['mqtt_in'].merge(current_dict.get('mqtt_in', configobj.ConfigObj()))
            section_dict['mqtt_out'].merge(current_dict.get('mqtt_out', configobj.ConfigObj()))
            section_dict['file_in'].merge(current_dict.get('file_in', configobj.ConfigObj()))
            section_dict['file_out'].merge(current_dict.get('file_out', configobj.ConfigObj()))
            section_dict['db_in'].merge(current_dict.get('db_in', configobj.ConfigObj()))
            section_dict['db_out'].merge(current_dict.get('db_out', configobj.ConfigObj()))

            # merge stations config
            section_dict['result_in'].merge(stations_dict.get('result_in', configobj.ConfigObj()))
            section_dict['api_in'].merge(stations_dict.get('api_in', configobj.ConfigObj()))
            section_dict['api_out'].merge(stations_dict.get('api_out', configobj.ConfigObj()))
            section_dict['mqtt_in'].merge(stations_dict.get('mqtt_in', configobj.ConfigObj()))
            section_dict['mqtt_out'].merge(stations_dict.get('mqtt_out', configobj.ConfigObj()))
            section_dict['file_in'].merge(stations_dict.get('file_in', configobj.ConfigObj()))
            section_dict['file_out'].merge(stations_dict.get('file_out', configobj.ConfigObj()))
            section_dict['db_in'].merge(stations_dict.get('db_in', configobj.ConfigObj()))
            section_dict['db_out'].merge(stations_dict.get('db_out', configobj.ConfigObj()))

            # merge own station config
            section_dict['result_in'].merge(stations_dict[section].get('result_in', configobj.ConfigObj()))
            section_dict['api_in'].merge(stations_dict[section].get('api_in', configobj.ConfigObj()))
            section_dict['api_out'].merge(stations_dict[section].get('api_out', configobj.ConfigObj()))
            section_dict['mqtt_in'].merge(stations_dict[section].get('mqtt_in', configobj.ConfigObj()))
            section_dict['mqtt_out'].merge(stations_dict[section].get('mqtt_out', configobj.ConfigObj()))
            section_dict['file_in'].merge(stations_dict[section].get('file_in', configobj.ConfigObj()))
            section_dict['file_out'].merge(stations_dict[section].get('file_out', configobj.ConfigObj()))
            section_dict['db_in'].merge(stations_dict[section].get('db_in', configobj.ConfigObj()))
            section_dict['db_out'].merge(stations_dict[section].get('db_out', configobj.ConfigObj()))

            # check section config
            cancel, section_dict = self.check_section(engine, section_dict, section)
            if cancel:
                section_dict = None
                continue

            # thread_config
            thread_config = configobj.ConfigObj()
            thread_config['engine'] = self.engine
            thread_config['config_dict'] = config_dict
            thread_config['config'] = section_dict
            section_dict = None

            # start configured current weather threads
            if provider == 'dwd':
                if model == 'poi':
                    self._create_poi_thread(section, thread_config)
                elif model == 'cdc':
                    self._create_cdc_thread(section, thread_config)
                elif model == 'mosmix':
                    self._create_mosmix_thread(section, thread_config)
            elif provider == 'open-meteo':
                self._create_openmeteo_thread(section, thread_config)
            elif provider == 'brightsky':
                self._create_brightsky_thread(section, thread_config)
            elif provider == 'pws':
                self._create_pws_thread(section, thread_config)
            elif provider == 'aeris':
                self._create_aeris_thread(section, thread_config)
            elif provider == 'owm':
                self._create_owm_thread(section, thread_config)
            elif provider == 'total':
                self._create_total_thread(section, thread_config)
            elif self.log_failure or self.debug > 0:
                logerr("Service 'CurrentWX': init section '%s' unknown weather service provider '%s'" % (section, provider))

        if  __name__!='__main__':
            self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet)
            self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

        if self.log_success or self.debug > 0:
            loginf("Service 'CurrentWX': init finished. Number of current threads started: %d" % (len(self.threads[SERVICEID])))
        if len(self.threads[SERVICEID]) < 1:
            loginf("Service 'CurrentWX': no threads have been started. Service 'CurrentWX' exits now")
            return
