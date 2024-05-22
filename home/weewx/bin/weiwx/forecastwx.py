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
      DWD (MOSMIX)
      Open-Meteo (ICON-GLOBAL, ICON-D2, ICON-EU, ICON-SEAMLESS, BEST-MATCH)
      OpenWeather

    The goal is to provide the Weiherhammer Skin (Belchertown Skin Fork) with 
    standardized JSON data in a file and in a MQTT Topic. This way it is possible
    to switch within the skin without much effort between the different providers.
    If new data is loaded, the updated topic can be loaded and displayed updated.
"""

VERSION = "0.1b1"

import sys
import os
import threading
import configobj
import io
import time
import random
import copy
import shutil
import pytz
import math
from statistics import mean
import paho.mqtt.publish as mqtt_publish
import paho.mqtt.subscribe as mqtt_subscribe
import requests
from requests.exceptions import Timeout
import datetime
from datetime import timezone
import json
from json import JSONDecodeError

try:
    # Test for new-style weewx logging by trying to import weeutil.logger
    import weeutil.logger
    import logging
    log = logging.getLogger("weiwx.forecastwx")

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
        syslog.syslog(level, 'weiwx.forecastwx: %s' % msg)

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

SERVICEID='forecastwx'

# provider forecast
# ID               = Provider and model
# aeris            = Vaisala Xweather Forecast
# brightsky        = Bright Sky Forecast
# dwd-mosmix       = DWD MOSMIX
# om-best-match    = Open-Meteo best-match
# om-icon-combined = Open-Meteo DWD ICON
# om-icon-d2       = Open-Meteo DWD ICON D2
# om-icon-eu       = Open-Meteo DWD ICON EU
# om-icon-seamless = Open-Meteo DWD seamless

HTMLTMPL = "<p><a href='%s' target='_blank' rel='tooltip' title=''>%s</a>%s</p>"

PROVIDER = {
    'aeris': ('Vaisala Xweather', 'https://www.vaisala.com', ''),
    'brightsky': ('Bright Sky', 'https://brightsky.dev', ''),
    'dwd-mosmix': ('Deutscher Wetterdienst', 'https://www.dwd.de', ' (MOSMIX)'),
    'om-best-match': ('Open-Meteo', 'https://open-meteo.com', ' (best-match)'),
    'om-icon-combined': ('Open-Meteo', 'https://open-meteo.com', ' (DWD ICON)'),
    'om-icon-d2': ('Open-Meteo', 'https://open-meteo.com', ' (DWD ICON D2)'),
    'om-icon-eu': ('Open-Meteo', 'https://open-meteo.com', ' (DWD ICON EU)'),
    'om-icon-seamless': ('Open-Meteo', 'https://open-meteo.com', ' (DWD ICON SEAMLESS)'),
}

COMPASS = {
    'de':['N','NNO','NO','ONO','O','OSO','SO','SSO','S','SSW','SW','WSW','W','WNW','NW','NNW'],
    'en':['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW']
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
            logerr("thread '%s': Info: %s" % (thread_name, str(addcontent)))


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

    headers={'User-Agent': 'forecastwx'}
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
def minimize_forecast_total_mqtt(thread_name, data, interval, debug=0, log_success=False, log_failure=True):
    """
    Minimize the output of weather providers and generate only the required elements that are 
    absolutely necessary for displaying the forecast weather conditions in the Belchertown skin.
    """
    poPrecip = ['pos', 'pofr', 'por', 'pop', 'posp', 'pod', 'pop_001', 'pop_002', 'pop_003', 'pop_004', 'pop_007', 'pop_010', 'pop_020'
                , 'pop_030', 'pop_050', 'pop_100', 'pop_150', 'pop_250']
    solidPrecip = ['ice', 'snow', 'pos', 'posp']
    if debug > 2:
        logdbg("thread '%s': minimize_forecast_total_mqtt data %s" % (thread_name, json.dumps(data)))
    minimized = dict()
    try:
        minimized['timestamp'] = weeutil.weeutil.to_int(data.get('timestamp'))
        minimized['timestampISO'] = data.get('timestampISO')
        minimized['icon'] = data.get('weathericon')
        minimized['text'] = data.get('weathertext')
        if interval in ('1h','db'):
            minimized['temp'] = round(data.get('outTemp'), 5) if data.get('outTemp') is not None else None
        else:
            minimized['temp_min'] = round(data.get('outTemp_min'), 5) if data.get('outTemp_min') is not None else None
            minimized['temp_max'] = round(data.get('outTemp_max'), 5) if data.get('outTemp_max') is not None else None
        poplist = list()
        for pop in poPrecip:
            val = data.get(pop, 0.0)
            poplist.append(val)
        minimized['pop'] = weeutil.weeutil.to_int(max(poplist))
        solid = 0
        for sp in solidPrecip:
            val = data.get(sp, 0.0)
            if val > 0.0:
                solid = 1
                break
        minimized['dewpoint'] = round(data.get('dewpoint'), 5) if data.get('dewpoint') is not None else None
        minimized['solidPrecip'] = weeutil.weeutil.to_int(solid)
        minimized['outHumidity'] = weeutil.weeutil.to_int(data.get('outHumidity'))
        if interval in ('1h','db'):
            minimized['wind_min'] = round(data.get('windSpeed'), 5) if data.get('windSpeed') is not None else None
            minimized['wind_max'] = round(data.get('windGust'), 5) if data.get('windGust') is not None else None
        else:
            minimized['wind_min'] = round(data.get('windSpeed_min'), 5) if data.get('windSpeed_min') is not None else None
            minimized['wind_max'] = round(data.get('windSpeed_max'), 5) if data.get('windSpeed_max') is not None else None
        minimized['windDir'] = weeutil.weeutil.to_int(data.get('windDir'))
        minimized['compass'] = data.get('compass')
        minimized['barometer'] = round(data.get('barometer'), 5) if data.get('barometer') is not None else None
        if debug > 2:
            logdbg("thread '%s': minimize_forecast_total_mqtt minimized %s" % (thread_name, json.dumps(minimized)))
    except Exception as e:
        exception_output(thread_name, e)
        return data
    return minimized


@staticmethod
def minimize_forecast_total_file(thread_name, data, interval, debug=0, log_success=False, log_failure=True):
    """
    Minimize the output of weather providers and generate only the required elements that are 
    absolutely necessary for displaying the forecast weather conditions in the Belchertown skin.
    """
    poPrecip = ['pos', 'pofr', 'por', 'pop', 'posp', 'pod', 'pop_001', 'pop_002', 'pop_003', 'pop_004', 'pop_007', 'pop_010', 'pop_020'
                , 'pop_030', 'pop_050', 'pop_100', 'pop_150', 'pop_250']
    solidPrecip = ['ice', 'snow', 'pos', 'posp']
    if debug > 2:
        logdbg("thread '%s': minimize_forecast_total_file data %s" % (thread_name, json.dumps(data)))
    minimized = dict()
    try:
        minimized['timestamp'] = weeutil.weeutil.to_int(data.get('timestamp'))
        minimized['timestampISO'] = data.get('timestampISO')
        minimized['icon'] = data.get('weathericon')
        minimized['text'] = data.get('weathertext')
        if interval in ('1h', 'db'):
            minimized['temp'] = round(data.get('outTemp'), 5) if data.get('outTemp') is not None else None
        else:
            minimized['temp_min'] = round(data.get('outTemp_min'), 5) if data.get('outTemp_min') is not None else None
            minimized['temp_max'] = round(data.get('outTemp_max'), 5) if data.get('outTemp_max') is not None else None
        poplist = list()
        for pop in poPrecip:
            val = data.get(pop, 0.0)
            poplist.append(val)
        minimized['pop'] = weeutil.weeutil.to_int(max(poplist))
        solid = 0
        for sp in solidPrecip:
            val = data.get(sp, 0.0)
            if val > 0.0:
                solid = 1
                break
        minimized['dewpoint'] = round(data.get('dewpoint'), 5) if data.get('dewpoint') is not None else None
        minimized['solidPrecip'] = weeutil.weeutil.to_int(solid)
        minimized['outHumidity'] = weeutil.weeutil.to_int(data.get('outHumidity'))
        if interval in ('1h','db'):
            minimized['wind_min'] = round(data.get('windSpeed'), 5) if data.get('windSpeed') is not None else None
            minimized['wind_max'] = round(data.get('windGust'), 5) if data.get('windGust') is not None else None
        else:
            minimized['wind_min'] = round(data.get('windSpeed_min'), 5) if data.get('windSpeed_min') is not None else None
            minimized['wind_max'] = round(data.get('windSpeed_max'), 5) if data.get('windSpeed_max') is not None else None
        minimized['windDir'] = weeutil.weeutil.to_int(data.get('windDir'))
        minimized['compass'] = data.get('compass')
        minimized['barometer'] = round(data.get('barometer'), 5) if data.get('barometer') is not None else None
        if debug > 2:
            logdbg("thread '%s': minimize_forecast_total_file minimized %s" % (thread_name, json.dumps(minimized)))
    except Exception as e:
        exception_output(thread_name, e)
        return data
    return minimized


@staticmethod
def minimize_forecast_result_mqtt(thread_name, data, debug=0, log_success=False, log_failure=True):
    """
    Minimizes the data and provides only the data that should be included in a WeeWX Loop Packet or in a WeeWX Archive Record.
    I don't need text fields in loop or archive data anymore. Icons and texts can be loaded externally by using weathercodeKey.
    """
    strings_to_check = ['sourceUrl', 'sourceId', 'sourceModul', 'sourceProviderLink', 'sourceProviderHTML', 'interval']
    result = data
    if debug > 2:
        logdbg("thread '%s': minimize_forecast_result_mqtt result full %s" % (thread_name, json.dumps(result)))

    keys_to_remove = [key for key in result.keys() if any(string in key for string in strings_to_check)]
    for key in keys_to_remove:
        result.pop(key)

    if debug > 2:
        logdbg("thread '%s': minimize_forecast_result_mqtt result minimized %s" % (thread_name, json.dumps(result)))
    return result


@staticmethod
def minimize_forecast_weewx(thread_name, data, debug=0, log_success=False, log_failure=True):
    """
    Minimizes the data and provides only the data that should be included in a WeeWX Loop Packet or in a WeeWX Archive Record.
    I don't need text fields in loop or archive data anymore. Icons and texts can be loaded externally by using weathercodeKey.
    """
    return data
    # TODO
    forecast = dict()
    if debug > 2:
        logdbg("thread '%s': minimize_forecast_weewx data full %s" % (thread_name, json.dumps(data)))

    for obs, value in data.items():
        if str(value).isnumeric():
            forecast[obs] = data[obs]

    if debug > 2:
        logdbg("thread '%s': minimize_forecast_weewx data minimized %s" % (thread_name, json.dumps(data)))
    return forecast


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
                    exception_output(thread_name, e)
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
def to_packet(thread_name, datain, lang, debug=0, log_success=False, log_failure=True):
    dataout = dict()
    try:
        for obs in datain:
            try:
                if obs == 'weathertext':
                    dataout[obs] = datain[obs][lang][0]
                elif isinstance(datain[obs], (list, tuple, set, dict)):
                    dataout[obs] = datain[obs][0]
                else:
                    dataout[obs] = datain[obs]
            except LookupError:
                dataout[obs] = None
    except Exception as e:
        exception_output(thread_name, e, "datain %s" % (json.dumps(datain)))
        return dataout
    return dataout


@staticmethod
def to_weewx(thread_name, data_vt, dest_unit_system, debug=0, log_success=False, log_failure=True):
    try:
        if type(data_vt) is not tuple:
            return data_vt
        elif data_vt[0] in ('interval', 'usUnits'):
            return data_vt
        elif data_vt[0] is None:
            return data_vt
        elif data_vt[1] in ('count', 'unix_epoch', 'percent', 'degree_compass', 'uv_index'):
            return data_vt
        elif data_vt[2] == None:
            return data_vt
        try:
            val = weewx.units.convertStd(data_vt, dest_unit_system)
            return val
        except (TypeError,ValueError,LookupError,ArithmeticError) as e:
            exception_output(thread_name, e, "to_weewx data_vt %s" % str(data_vt))
            return data_vt
    except Exception as e:
        exception_output(thread_name, e, "to_weewx data_vt %s" % str(data_vt))
        return data_vt


@staticmethod
def to_unit_system(thread_name, datain, dest_unit_system, debug=0, log_success=False, log_failure=True):
    dataout = dict()
    if debug > 2:
        logdbg("thread '%s': to_unit_system dest unit=%s" % (thread_name, str(dest_unit_system)))
        logdbg("thread '%s': to_unit_system datain %s" % (thread_name, json.dumps(datain)))
    try:
        for key, values in datain.items():
            dataout[key] = to_weewx(thread_name, values, dest_unit_system, debug=debug, log_success=log_success, log_failure=log_failure)
    except Exception as e:
        exception_output(thread_name, e, "to_unit_system key %s - values %s" % (key, values))
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

@staticmethod
def compass(x, lang='de'):
    if x is None:
        return ''
    try:
        y = (x+11.25)//22.5
        if y>=16: y -= 16
        return COMPASS[lang][int(y)]
    except Exception:
        return ''


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


    #
    #                     fictitious 
    #                     numerical
    #  weathercodeAeris:  AerisCode   deutsch , english, Belchertown Icon Day, Belchertown Icon Night
    #                         0          1         2               3                     4
    #
    # CODECONVERTER = {
    #      '::NA': (-1, 'nicht gemeldet', 'not reported', 'unknown.png', 'unknown.png'),
    # return: (text_de, text_en, icon)
    def get_icon_and_text(self, aeris_code, night=0, debug=0, log_success=False, log_failure=True, weathertext_en=None):
        if night is None:
            night = 0
        try:
            # using only ':xx:xx' without Aeris intensity codes
            aeriscode_l = str(aeris_code).split(':')
            aeriscode = ':%s:%s' % (aeriscode_l[1], aeriscode_l[2])
            x = CODECONVERTER[aeriscode]
            icon = x[4] if night == 1 else x[3]
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


    def publish_result_mqtt(self):
        """ publish forecast weather data record to MQTT Broker """
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
            mqtt_options['mqtt_topic_json_extension'] = mqttout_dict.get('topic_json_extension', 'loop')
            mqtt_options['timezone'] = self.timezone

            # prepare output
            output = dict()
            if self.name == '%s_total' % SERVICEID:
                for source_id, value_dict in self.data_result.items():
                    data = dict()
                    data.update(self.data_result[source_id])
                    output[source_id] = dict()
                    output[source_id].update(data)
                    if data.get('lang') != lang:
                        output[source_id]['lang'] = lang
                    for interval in ('1h', '3h', '24h', 'db'):
                    #for interval in ('1h', '3h', '24h'):
                        #output[source_id][interval] = dict()
                        output[source_id][interval] = list()
                        for col, values in data[interval].items():
                            if data.get('usUnits') != unitsystem:
                                values = to_unit_system(self.name, values, unitsystem, debug=debug, log_success=log_success, log_failure=log_failure)
                                output[source_id]['usUnits'] = unitsystem
                            values = to_packet(self.name, values, lang, debug=debug, log_success=log_success, log_failure=log_failure)
                            if weeutil.weeutil.to_bool(mqttout_dict.get('minimize', False)):
                                values = minimize_forecast_total_mqtt(self.name, values, interval, debug=debug, log_success=log_success, log_failure=log_failure)
                            #output[source_id][interval][col] = values
                            output[source_id][interval].append(values)
            else:
                output.update(self.data_result)
                if self.data_result.get('lang')[0] != lang:
                    output['lang'] = lang
                for interval in ('1h', '3h', '24h', 'db'):
                #for interval in ('1h', '3h', '24h'):
                    #output[interval] = dict()
                    output[interval] = list()
                    for col, values in self.data_result[interval].items():
                        if self.data_result.get('usUnits') != unitsystem:
                            values = to_unit_system(self.name, values, unitsystem, debug=debug, log_success=log_success, log_failure=log_failure)
                            output['usUnits'] = unitsystem
                        values = to_packet(self.name, values, lang, debug=debug, log_success=log_success, log_failure=log_failure)
                        if weeutil.weeutil.to_bool(mqttout_dict.get('minimize', False)):
                            values = minimize_forecast_total_mqtt(self.name, values, interval, debug=debug, log_success=log_success, log_failure=log_failure)
                        #output[interval][col] = values
                        output[interval].append(values)

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


    def publish_result_file(self):
        """ publish forecast weather data record to a file. Currently only JSON files supported. """

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
                    logerr("thread '%s': publish_result_file required 'basepath' is not valid. Station %s" % (self.name, self.station))
                return False
            if filename is None or filename == '':
                if log_failure or debug > 0:
                    logerr("thread '%s': publish_result_file required 'filename' is not valid. Station %s" % (self.name, self.station))
                return False
            filename = "%s/%s" % (basepath, filename)
            file_options['file_filename'] = filename
            file_options['file_max_attempts'] = weeutil.weeutil.to_int(fileout_dict.get('max_attempts', 1))
            file_options['file_formats'] = weeutil.weeutil.option_as_list(fileout_dict.get('formats', list()))
            file_options['timezone'] = self.timezone

            # prepare output
            output = dict()
            if self.name == '%s_total' % SERVICEID:
                for source_id, value_dict in self.data_result.items():
                    data = dict()
                    data.update(self.data_result[source_id])
                    output[source_id] = dict()
                    output[source_id].update(data)
                    if data.get('lang') != lang:
                        output[source_id]['lang'] = lang
                    for interval in ('1h', '3h', '24h', 'db'):
                    #for interval in ('1h', '3h', '24h'):
                        #output[source_id][interval] = dict()
                        output[source_id][interval] = list()
                        for col, values in data[interval].items():
                            if data.get('usUnits') != unitsystem:
                                values = to_unit_system(self.name, values, unitsystem, debug=debug, log_success=log_success, log_failure=log_failure)
                                output[source_id]['usUnits'] = unitsystem
                            values = to_packet(self.name, values, lang, debug=debug, log_success=log_success, log_failure=log_failure)
                            if weeutil.weeutil.to_bool(fileout_dict.get('minimize', False)):
                                values = minimize_forecast_total_file(self.name, values, interval, debug=debug, log_success=log_success, log_failure=log_failure)
                            #output[source_id][interval][col] = values
                            output[source_id][interval].append(values)
            else:
                output.update(self.data_result)
                if self.data_result.get('lang')[0] != lang:
                    output['lang'] = lang
                for interval in ('1h', '3h', '24h', 'db'):
                #for interval in ('1h', '3h', '24h'):
                    #output[interval] = dict()
                    output[interval] = list()
                    for col, values in self.data_result[interval].items():
                        if self.data_result.get('usUnits') != unitsystem:
                            values = to_unit_system(self.name, values, unitsystem, debug=debug, log_success=log_success, log_failure=log_failure)
                            output['usUnits'] = unitsystem
                        values = to_packet(self.name, values, lang, debug=debug, log_success=log_success, log_failure=log_failure)
                        if weeutil.weeutil.to_bool(fileout_dict.get('minimize', False)):
                            values = minimize_forecast_total_file(self.name, values, interval, debug=debug, log_success=log_success, log_failure=log_failure)
                        #output[interval][col] = values
                        output[interval].append(values)

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


    def new_db_record(self):
        """ insert Forecast Data into DB """

        dbout_dict = self.config.get('db_out', configobj.ConfigObj())
        debug = weeutil.weeutil.to_int(dbout_dict.get('debug', self.debug))
        log_success = weeutil.weeutil.to_bool(dbout_dict.get('log_success', self.log_success))
        log_failure = weeutil.weeutil.to_bool(dbout_dict.get('log_failure', self.log_failure))

        if len(self.data_temp) <= 0:
            if debug > 0:
                logdbg("thread '%s': new_db_record there are no forecast data available yet. Don't execute." % (self.name))
            return False

        if debug > 0:
            logdbg("thread '%s': new_db_record started" % (self.name))
        if debug > 2:
            logdbg("thread '%s': new_db_record config %s" %(self.name, json.dumps(dbout_dict)))

        if not weeutil.weeutil.to_bool(dbout_dict.get('enable', False)):
            if log_success or debug > 0:
                loginf("thread '%s': new_db_record db_out is diabled. Enable it in the [db_out] section of station %s" %(self.name, self.station))
            return False

        data = self.get_data_result()
        if len(data) <= 0:
            if debug > 0:
                logdbg("thread '%s': new_db_record There are no forecast data available yet. Don't execute." % (self.name))
            return False

        # unit system
        unit_system = None
        unitsystem = None
        u_s = dbout_dict.get('unit_system', self.unit_system)
        if u_s is not None:
            u_s = str(u_s).upper()
            if u_s in('US', 'METRIC', 'METRICWX'):
                unit_system = u_s
                if unit_system == 'US': unitsystem = weewx.US
                elif unit_system == 'METRIC': unitsystem = weewx.METRIC
                elif unit_system == 'METRICWX': unitsystem = weewx.METRICWX

        # lang
        lang = dbout_dict.get('lang', self.lang)
        if lang is not None:
            lang = str(lang).lower()
            if lang not in('de', 'en'):
                lang = None

        data_binding_name = dbout_dict.get('data_binding')
        if data_binding_name is None:
            if self.log_failure or self.debug > 0:
                logerr("thread '%s': new_db_record data_binding is not configured!" % (self.name))
            return False

        # open the data store
        try:
            sql = "delete from %s" % (self.dbm.table_name)
            self.dbm.getSql(sql)
        except Exception as e:
            exception_output(self.name, e)
            return False

        if log_success or debug > 0:
            loginf("thread '%s': new_db_record content table '%s' deleted." % (self.name, self.dbm.table_name))

        records = list()
        usUnits = data.get('usUnits', weewx.METRIC)
        for col, ds in data['db'].items():
            record = dict()
            ds = to_packet(self.name, ds, lang, debug=debug, log_success=log_success, log_failure=log_failure)
            record['dateTime'] = ds.get('timestamp')
            record['interval'] = 60
            record['usUnits'] = usUnits
            record['weathercode'] = ds.get('weathercode')
            record['outTemp'] = ds.get('outTemp')
            record['appTemp'] = ds.get('appTemp', ds.get('feelslike'))
            record['dewpoint'] = ds.get('dewpoint')
            record['outHumidity'] = ds.get('outHumidity')
            record['barometer'] = ds.get('barometer')
            record['windDir'] = ds.get('windDir')
            record['windSpeed'] = ds.get('windSpeed')
            record['windGust'] = ds.get('windGust')
            record['cloudcover'] = ds.get('cloudcover')
            record['visibility'] = ds.get('visibility')
            record['uvi'] = ds.get('uvi')
            record['pop'] = ds.get('pop')
            record['precipitation'] = ds.get('precipitation')
            record['rain'] = ds.get('rain')
            record['shower'] = ds.get('shower')
            record['snow'] = ds.get('snow')
            record['snowRain'] = ds.get('snowRain')
            record['rainDur'] = ds.get('rainDur')
            record['sunshineDur'] = ds.get('sunshineDur')
            records.append(record)
            # self.dbm.addRecord(record)
        try:
            self.dbm.addRecord(records)
        except Exception as e:
            exception_output(self.name, e)

        if log_success or debug > 0:
            loginf("thread '%s': new_db_record finished." % (self.name))
        self.last_db_ts = weeutil.weeutil.to_int(time.time())
        return True


    def new_result_from_temp(self, oldData=False):
        if self.debug > 2:
            loginf("thread '%s': new_result_from_temp started." % (self.name))
        if oldData:
            # nothing to do
            if self.log_success or self.debug > 0:
                loginf("thread '%s': new_result_from_temp finished" % (self.name))
            return
        try:
            self.lock.acquire()
            self.data_result = dict()
            self.data_result.update(self.data_temp)
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
                loginf("thread '%s': running" % self.name)
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
                        loginf("thread '%s': get_data_api" % self.name)
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
                    # if api_out:
                        # self.publish_result_api()
                    if file_out:
                        self.publish_result_file()
                    if db_out and not oldData:
                        self.new_db_record()

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
# Class OPENMETEOthread
#
# ============================================================================

class OPENMETEOthread(AbstractThread):

    WEATHERMODELS = {
        # option: (country, weather service, model, API endpoint, exclude list)
        'best_match':('', '', '', 'forecast',['snowfall_height']),
        'dwd-icon':('DE', 'DWD', 'ICON', 'dwd-icon',['precipitation_probability', 'precipitation_probability_max', 'uv_index', 'uv_index_max', 'uv_index_clear_sky', 'uv_index_clear_sky_max', 'visibility']),
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
        'icon_d2':('DE', 'DWD', 'ICON D2', 'forecast',['precipitation_probability', 'precipitation_probability_max', 'snowfall_height', 'uv_index', 'uv_index_clear_sky', 'visibility']), # TODO check excludes
        'icon_eu':('DE', 'DWD', 'ICON EU', 'forecast',['precipitation_probability', 'precipitation_probability_max', 'snowfall_height', 'uv_index', 'uv_index_clear_sky', 'visibility']), # TODO check excludes
        'icon_global':('DE', 'DWD', 'ICON Global', 'forecast',['precipitation_probability_max', 'snowfall_height' 'uv_index', 'uv_index_clear_sky']),
        'icon_seamless':('DE', 'DWD', 'ICON Seamless', 'forecast',['precipitation_probability', 'precipitation_probability_max', 'snowfall_height', 'uv_index', 'uv_index_clear_sky', 'visibility']), # TODO check excludes
        'jma':('JP', 'JMA', 'GSM+MSM', 'jma',['evapotranspiration', 'freezinglevel_height', 'precipitation_probability', 'rain', 'showers', 'snow_depth', 'snowfall_height', 'visibility', 'windgusts_10m']),
        'meteofrance':('FR', 'MeteoFrance', 'Arpege+Arome', 'meteofrance',['evapotranspiration', 'freezinglevel_height', 'precipitation_probability', 'rain', 'showers', 'snow_depth', 'snowfall_height', 'visibility']),
        'metno':('NO', 'MET Norway', 'Nordic', 'metno',['evapotranspiration', 'freezinglevel_height', 'precipitation_probability', 'rain', 'showers', 'snow_depth', 'snowfall_height', 'visibility']),
        'metno_nordic':('NO', 'MET Norway', 'Nordic', 'forecast',['precipitation_probability', 'snowfall_height', 'surface_pressure'])
    }


    # https://open-meteo.com/en/docs
    # Mapping hourly API field -> WeeWX field
    HOURLYOBS = {
        'apparent_temperature': ('appTemp', 'degree_C', 'group_temperature'),
        'cloudcover': ('cloudcover', 'percent', 'group_percent'),
        'dewpoint_2m': ('dewpoint', 'degree_C', 'group_temperature'), # not available in forecast model ecmwf
        'evapotranspiration': ('et', 'mm', 'group_rain'),
        'freezinglevel_height': ('freezinglevelHeight', 'meter', 'group_altitude'),
        'is_day': ('is_day', 'count', 'group_count'),
        'precipitation': ('precipitation', 'mm', 'group_rain'),
        'precipitation_probability': ('pop', 'percent', 'group_percent'),
        'pressure_msl': ('barometer', 'hPa', 'group_pressure'),
        'rain': ('rain', 'mm', 'group_rain'),
        'relativehumidity_2m': ('outHumidity', 'percent', 'group_percent'), # not available in forecast model ecmwf
        'diffuse_radiation_instant': ('solarRad', 'watt_per_meter_squared', 'group_radiation'),
        'shortwave_radiation_instant': ('radiation', 'watt_per_meter_squared', 'group_radiation'),
        'showers': ('shower', 'mm', 'group_rain'),
        'snow_depth': ('snowDepth', 'meter', 'group_rain'),
        'snowfall': ('snow', 'cm', 'group_rain'),
        'snowfall_height': ('snowfallHeight', 'meter', 'group_altitude'), # only available in DWD-ICON
        'surface_pressure': ('pressure', 'hPa', 'group_pressure'),
        'temperature_2m': ('outTemp', 'degree_C', 'group_temperature'),
        #'uv_index': ('uvi', 'uv_index', 'group_uv'), # not available in DWD-ICON
        #'uv_index_clear_sky': ('clearSkyUvi', 'uv_index', 'group_uv'), # not available in DWD-ICON
        'visibility': ('visibility',  'meter', 'group_distance'), # only available by the American weather models.
        'weathercode': ('weathercode', 'count', 'group_count'),
        'winddirection_10m': ('windDir', 'degree_compass', 'group_direction'),
        'windgusts_10m': ('windGust', 'km_per_hour', 'group_speed'), # not available in forecast model ecmwf
        'windspeed_10m': ('windSpeed', 'km_per_hour', 'group_speed'),
    }


    # https://open-meteo.com/en/docs
    # Mapping daily API field -> WeeWX field
    DAILYOBS = {
        'apparent_temperature_max': ('appTemp_max', 'degree_C', 'group_temperature'),
        'apparent_temperature_min': ('appTemp_min', 'degree_C', 'group_temperature'),
        'precipitation_hours': ('precipitation_hours', 'hour', 'group_deltatime'),
        'precipitation_sum': ('precipitation_sum', 'mm', 'group_rain'),
        'rain_sum': ('rain_sum', 'mm', 'group_rain'),
        'shortwave_radiation_sum': ('radiation_sum', 'megajoule_per_meter_squared', 'group_radiation'),
        'showers_sum': ('shower_sum', 'mm', 'group_rain'),
        'snowfall_sum': ('snow_sum', 'cm', 'group_rain'),
        'temperature_2m_max': ('outTemp_max', 'degree_C', 'group_temperature'),
        'temperature_2m_min': ('outTemp_min', 'degree_C', 'group_temperature'),
        'weathercode': ('weathercode', 'count', 'group_count'),
        'winddirection_10m_dominant': ('windDir_avg', 'degree_compass', 'group_direction'),
        'windgusts_10m_max': ('windGust_max', 'km_per_hour', 'group_speed'), # not available in forecast model ecmwf
        'windspeed_10m_max': ('windSpeed_max', 'km_per_hour', 'group_speed'),
        # only /forecast endpoint:
        #'uv_index_max': ('UV_max', 'uv_index', 'group_uv'), # not available in DWD-ICON
        #'uv_index_clear_sky_max': ('clearSkyUV_max', 'uv_index', 'group_uv'), # not available in DWD-ICON
        # only /forecast endpoint model best_match
        'precipitation_probability_max': ('pop', 'percent', 'group_percent'),
    }


    # Mapping API unit -> WeeWX unit
    APITOWEEWXUNITS = {
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
        'uv_index': 'uv_index',
        '': 'count',
        'unixtime': 'unix_epoch',
        'h': 'hour',
        u'MJ/m²': 'megajoule_per_meter_squared'
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

    def get_api_to_weewx_units(self):
        units = OPENMETEOthread.APITOWEEWXUNITS
        return units

    def get_hourly_obs(self):
        hobs = copy.deepcopy(OPENMETEOthread.HOURLYOBS)
        modelparams = OPENMETEOthread.WEATHERMODELS.get(self.model)
        if modelparams is not None:
            # remove exclude list from obs
            for x in modelparams[4]:
                if x in hobs:
                    hobs.pop(x)
        return hobs

    def get_daily_obs(self):
        dobs = copy.deepcopy(OPENMETEOthread.DAILYOBS)
        modelparams = OPENMETEOthread.WEATHERMODELS.get(self.model)
        if modelparams is not None:
            # remove exclude list from obs
            for x in modelparams[4]:
                if x in dobs:
                    dobs.pop(x)
        return dobs

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
        self.source_id = self.config.get('source_id', 'om-' + str(self.model).replace('_', '-'))
        self.interval_get = weeutil.weeutil.to_int(self.config.get('interval_get', 300))
        self.interval_push = weeutil.weeutil.to_int(self.config.get('interval_push', 30))
        self.expired = weeutil.weeutil.to_int(self.config.get('expired', 600))
        self.icon_path_belchertown = self.config.get('icon_path_belchertown', '')
        self.timezone = self.config.get('timezone', 'Europe/Berlin')
        self.hourly_obs = self.get_hourly_obs()
        self.daily_obs = self.get_daily_obs()
        self.api_to_weewx_units = self.get_api_to_weewx_units()
        self.config_dict = thread_dict.get('config_dict')
        self.engine = thread_dict.get('engine')
        self.data_result = dict()
        self.data_temp = dict()
        self.last_get_ts = 0

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

        weewx.units.obs_group_dict.setdefault('dateTime','group_time')
        weewx.units.obs_group_dict.setdefault('generated','group_time')
        weewx.units.obs_group_dict.setdefault('age','group_deltatime')
        weewx.units.obs_group_dict.setdefault('day','group_count')
        weewx.units.obs_group_dict.setdefault('expired','group_count')
        weewx.units.obs_group_dict.setdefault('weathercode','group_count')
        weewx.units.obs_group_dict.setdefault('weathercodeKey','group_count')
        for opsapi, obsweewx in self.hourly_obs.items():
            weewx.units.obs_group_dict.setdefault(obsweewx[0],obsweewx[2])
        for opsapi, obsweewx in self.daily_obs.items():
            weewx.units.obs_group_dict.setdefault(obsweewx[0],obsweewx[2])

        dbout_dict = self.config.get('db_out', configobj.ConfigObj())
        if weeutil.weeutil.to_bool(dbout_dict.get('enable', False)):
            data_binding_name = dbout_dict.get('data_binding')
            if data_binding_name is None:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': init data_binding is not configured!" % (self.name))
                return
            # open the data store
            self.dbm = self.engine.db_binder.get_manager(data_binding=data_binding_name, initialize=True)
            # confirm db schema
            dbcols = self.dbm.connection.columnsOf(self.dbm.table_name)
            dbm_dict = weewx.manager.get_manager_dict_from_config(self.config_dict, data_binding_name)
            memcols = [x[0] for x in dbm_dict['schema']]
            if dbcols != memcols:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': init store schema mismatch: %s != %s" % (self.name, dbcols, memcols))
                return
        elif self.log_success or self.debug > 0:
            loginf("thread '%s': init db_out is diabled. Enable it in the [db_out] section of station %s" %(self.name, self.station))

        if self.log_success or self.debug > 0:
            loginf("thread '%s': init finished" % self.name)


    def getDataInterval(self, data_interval_calc, unitsystem, lat, lon, alt, lang, debug=0, log_success=False, log_failure=True):
        """ preprocess Open-Meteo interval forecast data """

        data_temp = dict()

        # temp using for is_night
        night_dict = dict()
        night_dict['latitude'] = lat
        night_dict['longitude'] = lon
        night_dict['altitude'] = alt

        try:
            for interval, intervaldata in data_interval_calc.items():
                data_temp[interval] = dict()
                col = 0
                for ts, tsdata in intervaldata.items():
                    col += 1
                    data_temp[interval][str(col)] = dict()
                    data_temp[interval][str(col)]['timestamp'] = (ts, 'unix_epoch', 'group_time')
                    data_temp[interval][str(col)]['timestampISO'] = (get_isodate_from_timestamp(ts, self.timezone), None, None)
                    for apiobs, obsdata in tsdata.items():
                        
                        if interval == '24h' and apiobs.startswith("daily_"):
                            data_temp[interval][str(col)][apiobs] = obsdata
                            #logdbg("thread '%s': Daily %s - %s" % (self.name, apiobs, str(obsdata)))
                            continue

                        weewxobs = self.hourly_obs.get(apiobs)
                        #logdbg("thread '%s': getDataInterval apiobs %s" % (self.name, apiobs))
                        #logdbg("thread '%s': getDataInterval weewxobs %s" % (self.name, weewxobs))
                        #logdbg("thread '%s': getDataInterval obsdata %s" % (self.name, str(obsdata)))
                        if weewxobs is None:
                            if log_failure or debug > 0:
                                logerr("thread '%s': getDataInterval unknown api obs '%s'" % (self.name, apiobs))
                            continue
                        if interval in ('1h','db'):
                            vt = obsdata['val']
                            vt = to_weewx(self.name, vt, unitsystem, debug=debug, log_success=log_success, log_failure=log_failure)
                            #logdbg("thread '%s': getDataInterval vt %s" % (self.name, str(vt)))
                        else:
                            vt_min = obsdata['min']
                            vt_min = to_weewx(self.name, vt_min, unitsystem, debug=debug, log_success=log_success, log_failure=log_failure)

                            vt_avg = obsdata['avg']
                            vt_avg = to_weewx(self.name, vt_avg, unitsystem, debug=debug, log_success=log_success, log_failure=log_failure)

                            vt_max = obsdata['max']
                            vt_max = to_weewx(self.name, vt_max, unitsystem, debug=debug, log_success=log_success, log_failure=log_failure)

                            vt_sum = obsdata['sum']
                            vt_sum = to_weewx(self.name, vt_sum, unitsystem, debug=debug, log_success=log_success, log_failure=log_failure)

                            #logdbg("thread '%s': getDataInterval vt_min %s" % (self.name, str(vt_min)))
                            #logdbg("thread '%s': getDataInterval vt_avg %s" % (self.name, str(vt_avg)))
                            #logdbg("thread '%s': getDataInterval vt_max %s" % (self.name, str(vt_max)))
                            #logdbg("thread '%s': getDataInterval vt_sum %s" % (self.name, str(vt_sum)))

                        # TODO Filter?
                        if weewxobs[2] in ('group_temperature', 'group_speed'):
                            if interval in ('1h','db'):
                                data_temp[interval][str(col)][weewxobs[0]] = vt
                            else:
                                data_temp[interval][str(col)][weewxobs[0]+'_min'] = vt_min
                                data_temp[interval][str(col)][weewxobs[0]+'_avg'] = vt_avg
                                data_temp[interval][str(col)][weewxobs[0]+'_max'] = vt_max
                        elif weewxobs[2] in ('group_pressure', 'group_direction'):
                            if interval in ('1h','db'):
                                data_temp[interval][str(col)][weewxobs[0]] = vt
                            else:
                                data_temp[interval][str(col)][weewxobs[0]] = vt_avg
                        elif weewxobs[2] in ('group_count', 'group_percent'):
                            if interval in ('1h','db'):
                                data_temp[interval][str(col)][weewxobs[0]] = vt if vt[0] is not None else (0.0, vt[1], vt[2])
                            else:
                                data_temp[interval][str(col)][weewxobs[0]] = vt_max if vt_max[0] is not None else (0.0, vt_max[1], vt_max[2])
                        elif weewxobs[2] in ('group_distance'):
                            if interval in ('1h','db'):
                                data_temp[interval][str(col)][weewxobs[0]] = vt
                            else:
                                data_temp[interval][str(col)][weewxobs[0]] = vt_min
                        elif weewxobs[2] in ('group_rain'):
                            if interval in ('1h','db'):
                                data_temp[interval][str(col)][weewxobs[0]] = vt if vt[0] is not None else (0.0, vt[1], vt[2])
                            else:
                                data_temp[interval][str(col)][weewxobs[0]] = vt_sum if vt_sum[0] is not None else (0.0, vt_sum[1], vt_sum[2])

                    # compass
                    wdir = data_temp[interval][str(col)].get('windDir')
                    if wdir is not None:
                        data_temp[interval][str(col)]['compass'] = (compass(wdir[0], lang), None, None)
                    else:
                        data_temp[interval][str(col)]['compass'] = ('', None, None)

                    # is night?
                    night_dict['dateTime'] = data_temp[interval][str(col)].get('timestamp')
                    if interval in ('1h','db'):
                        night_dict['outTemp'] = data_temp[interval][str(col)].get('outTemp')
                        night_dict['barometer'] = data_temp[interval][str(col)].get('barometer')
                        night = is_night(self.name, night_dict, debug=debug, log_success=log_success, log_failure=log_failure)
                        if night is None:
                            night = 1 if weeutil.weeutil.to_int(data_temp[interval][str(col)].get('is_Day', 0)) == 1 else 0
                    elif interval == '3h':
                        night_dict['outTemp'] = data_temp[interval][str(col)].get('outTemp_max')
                        night_dict['barometer'] = data_temp[interval][str(col)].get('barometer')
                        night = is_night(self.name, night_dict, debug=debug, log_success=log_success, log_failure=log_failure)
                        if night is None:
                            night = 1 if weeutil.weeutil.to_int(data_temp[interval][str(col)].get('is_Day', 0)) == 1 else 0
                    else:
                        night = 0
                    data_temp[interval][str(col)]['day'] = (0 if night else 1, 'count', 'group_count')

                    # weathertext and weathericon
                    code = data_temp[interval][str(col)].get('weathercode')[0]
                    aeriscode = self.get_aeriscode(code)
                    data_temp[interval][str(col)]['weathercodeAeris'] = (aeriscode, None, None)
                    # return (text_de, text_en, icon, weathercode)
                    wxdata = self.get_icon_and_text(aeriscode, night=night, debug=debug, log_success=log_success, log_failure=log_failure, weathertext_en=None)
                    data_temp[interval][str(col)]['weathercodeKey'] = (weeutil.weeutil.to_int(wxdata[3]), 'count', 'group_count')
                    data_temp[interval][str(col)]['weathericon'] = (wxdata[2], None, None)
                    data_temp[interval][str(col)]['weathertext'] = dict()
                    data_temp[interval][str(col)]['weathertext']['de'] = (wxdata[0], None, None)
                    data_temp[interval][str(col)]['weathertext']['en'] = (wxdata[1], None, None)
        except Exception as e:
            exception_output(self.name, e, json.dumps(data_temp[interval][str(col)]))
            return None
        return data_temp

    def getDataIntervalCalc(self, apidata, debug=0, log_success=False, log_failure=True):
        """ preprocess Open-Meteo api forecast data """

        data_temp = dict()
        timestamps = apidata['hourly'].get('time')
        timestamp_len = len(timestamps)

        # current timestamp
        current_time = datetime.datetime.now(pytz.utc)
        current_time_ts = weeutil.weeutil.to_int(current_time.timestamp())
        current_time_berlin = current_time.astimezone(pytz.timezone('Europe/Berlin'))
        utcoffset = weeutil.weeutil.to_int(current_time_berlin.utcoffset().total_seconds())

        # start with the next full hour timestamp
        next_hour = current_time.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
        next_hour_ts = weeutil.weeutil.to_int(next_hour.timestamp())

        # or start with the current full hour timestamp
        current_hour = current_time.replace(minute=0, second=0, microsecond=0)
        current_hour_ts = weeutil.weeutil.to_int(current_hour.timestamp())

        # next day 00:00 timestamp
        next_day = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
        next_day_ts = weeutil.weeutil.to_int(next_day.timestamp()) - utcoffset

        # max 8 days 
        end_day = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=8)
        end_day_ts = weeutil.weeutil.to_int(end_day.timestamp()) - utcoffset

        # diff hours from start to 24h
        today_remaining_hours = weeutil.weeutil.to_int((next_day_ts + utcoffset - next_hour_ts) / 3600)

        if debug > 2:
            logdbg("thread '%s': current_time_ts %d" % (self.name, current_time_ts))
            logdbg("thread '%s': current_time_ts %s" % (self.name, current_time.isoformat(sep="T", timespec="seconds")))
            logdbg("thread '%s': current_time_ts %s" % (self.name, get_isodate_from_timestamp(current_time_ts)))

            logdbg("thread '%s': current_hour_ts %d" % (self.name, current_hour_ts))
            logdbg("thread '%s': current_hour_ts %s" % (self.name, current_hour.isoformat(sep="T", timespec="seconds")))
            logdbg("thread '%s': current_hour_ts %s" % (self.name, get_isodate_from_timestamp(current_hour_ts)))

            logdbg("thread '%s':    next_hour_ts %d" % (self.name, next_hour_ts))
            logdbg("thread '%s':    next_hour_ts %s" % (self.name, next_hour.isoformat(sep="T", timespec="seconds")))
            logdbg("thread '%s':    next_hour_ts %s" % (self.name, get_isodate_from_timestamp(next_hour_ts)))

            logdbg("thread '%s':     next_day_ts %d" % (self.name, next_day_ts))
            logdbg("thread '%s':     next_day_ts %s" % (self.name, next_day.isoformat(sep="T", timespec="seconds")))
            logdbg("thread '%s':     next_day_ts %s" % (self.name, get_isodate_from_timestamp(next_day_ts)))

            logdbg("thread '%s':      end_day_ts %d" % (self.name, end_day_ts))
            logdbg("thread '%s':      end_day_ts %s" % (self.name, end_day.isoformat(sep="T", timespec="seconds")))
            logdbg("thread '%s':      end_day_ts %s" % (self.name, get_isodate_from_timestamp(end_day_ts)))

            logdbg("thread '%s': today_remaining_hours: %d" % (self.name, today_remaining_hours))
            logdbg("thread '%s':       timezone offset: %d" % (self.name, utcoffset))

        # 24h interval
        data_temp['24h'] = dict()
        interval_start = next_hour_ts
        if interval_start < next_day_ts:
            hours = today_remaining_hours
        else:
            hours = 24
        ii = 0
        try:
            daily = apidata.get('daily') # Test
            daily_timestamps = daily.get('time') # Test
            for i in range(len(timestamps)):
                if timestamps[i] >= interval_start:
                    data_temp['24h'][timestamps[i]] = dict()
                    for obsapi, obsweewx in self.hourly_obs.items():
                        data_temp['24h'][timestamps[i]][obsapi] = dict()
                        obslist = apidata['hourly'].get(obsapi)
                        if obslist is None or len(obslist) != timestamp_len:
                            if log_failure or debug > 0:
                                if obslist is None:
                                    logerr("thread '%s': getDataIntervalCalc None for ts %s obs %s - %s" % (self.name, str(timestamps[i]), obsapi, obsweewx[0]))
                                elif len(obslist) != timestamp_len is None:
                                    logerr("thread '%s': getDataIntervalCalc obs %s number of values not equal to number of timestamps %d != %d" % (self.name, obsapi, len(obslist), timestamp_len))
                            data_temp['24h'][timestamps[i]][obsapi]['min'] = (None, obsweewx[1], obsweewx[2])
                            data_temp['24h'][timestamps[i]][obsapi]['avg'] = (None, obsweewx[1], obsweewx[2])
                            data_temp['24h'][timestamps[i]][obsapi]['max'] = (None, obsweewx[1], obsweewx[2])
                            data_temp['24h'][timestamps[i]][obsapi]['sum'] = (None, obsweewx[1], obsweewx[2])
                            continue
                        interval_values = obslist[i:i+hours]
                        try:
                            data_temp['24h'][timestamps[i]][obsapi]['min'] = (min(x for x in interval_values if x is not None), obsweewx[1], obsweewx[2])
                        except (ValueError, TypeError, ArithmeticError):
                            data_temp['24h'][timestamps[i]][obsapi]['min'] = (None, obsweewx[1], obsweewx[2])
                            pass
                        try:
                            data_temp['24h'][timestamps[i]][obsapi]['avg'] = (mean(x for x in interval_values if x is not None), obsweewx[1], obsweewx[2])
                        except (ValueError, TypeError, ArithmeticError):
                            data_temp['24h'][timestamps[i]][obsapi]['avg'] = (None, obsweewx[1], obsweewx[2])
                            pass
                        try:
                            data_temp['24h'][timestamps[i]][obsapi]['max'] = (max(x for x in interval_values if x is not None), obsweewx[1], obsweewx[2])
                        except (ValueError, TypeError, ArithmeticError):
                            data_temp['24h'][timestamps[i]][obsapi]['max'] = (None, obsweewx[1], obsweewx[2])
                            pass
                        try:
                            data_temp['24h'][timestamps[i]][obsapi]['sum'] = (sum(x for x in interval_values if x is not None), obsweewx[1], obsweewx[2])
                        except (ValueError, TypeError, ArithmeticError):
                            data_temp['24h'][timestamps[i]][obsapi]['sum'] = (None, obsweewx[1], obsweewx[2])
                            pass

                    # Test
                    try:
                        if hours == 24 and daily_timestamps is not None:
                            if interval_start in daily_timestamps:
                                key = daily_timestamps.index(interval_start)
                                for obsapi, obsweewx in self.daily_obs.items():
                                    obslist = daily.get(obsapi)
                                    if obslist is None:
                                        data_temp['24h'][timestamps[i]]['daily_'+obsapi] = (None, obsweewx[1], obsweewx[2])
                                    else:
                                        data_temp['24h'][timestamps[i]]['daily_'+obsapi] = (obslist[key], obsweewx[1], obsweewx[2])
                    except Exception as e:
                        exception_output(self.name, e)
                        pass

                    if hours < 24:
                        interval_start = next_day_ts
                        hours = 24
                    else:
                        interval_start += (hours * 3600)
                    #logdbg("thread '%s': 24h %s" % (self.name, json.dumps(data_temp['24h'][timestamps[i]])))
                    ii += 1
                    if ii >= 8 or interval_start > end_day_ts:
                        break
        except Exception as e:
            exception_output(self.name, e)
            return None

        # 3h interval
        data_temp['3h'] = dict()
        interval_start = next_hour_ts
        ii = 0
        try:
            for i in range(len(timestamps)):
                if timestamps[i] >= interval_start:
                    data_temp['3h'][timestamps[i]] = dict()
                    if timestamps[i] + (3 * 3600) > end_day_ts:
                        hours = weeutil.weeutil.to_int(end_day_ts - timestamps[i] / 3600)
                        if hours < 1:
                            break
                    else:
                        hours = 3
                    for obsapi, obsweewx in self.hourly_obs.items():
                        data_temp['3h'][timestamps[i]][obsapi] = dict()
                        obslist = apidata['hourly'].get(obsapi)
                        if obslist is None or len(obslist) != timestamp_len:
                            if log_failure or debug > 0:
                                if obslist is None:
                                    logerr("thread '%s': getDataIntervalCalc None for ts %s obs %s - %s" % (self.name, str(timestamps[i]), obsapi, obsweewx[0]))
                                elif len(obslist) != timestamp_len is None:
                                    logerr("thread '%s': getDataIntervalCalc number of values not equal to number of timestamps %d != %d" % (self.name, len(obslist), timestamp_len))
                            data_temp['3h'][timestamps[i]][obsapi]['min'] = (None, obsweewx[1], obsweewx[2])
                            data_temp['3h'][timestamps[i]][obsapi]['avg'] = (None, obsweewx[1], obsweewx[2])
                            data_temp['3h'][timestamps[i]][obsapi]['max'] = (None, obsweewx[1], obsweewx[2])
                            data_temp['3h'][timestamps[i]][obsapi]['sum'] = (None, obsweewx[1], obsweewx[2])
                            continue
                        interval_values = obslist[i:i+hours]
                        try:
                            data_temp['3h'][timestamps[i]][obsapi]['min'] = (min(x for x in interval_values if x is not None), obsweewx[1], obsweewx[2])
                        except (ValueError, TypeError, ArithmeticError):
                            data_temp['3h'][timestamps[i]][obsapi]['min'] = (None, obsweewx[1], obsweewx[2])
                            pass
                        try:
                            data_temp['3h'][timestamps[i]][obsapi]['avg'] = (mean(x for x in interval_values if x is not None), obsweewx[1], obsweewx[2])
                        except (ValueError, TypeError, ArithmeticError):
                            data_temp['3h'][timestamps[i]][obsapi]['avg'] = (None, obsweewx[1], obsweewx[2])
                            pass
                        try:
                            data_temp['3h'][timestamps[i]][obsapi]['max'] = (max(x for x in interval_values if x is not None), obsweewx[1], obsweewx[2])
                        except (ValueError, TypeError, ArithmeticError):
                            data_temp['3h'][timestamps[i]][obsapi]['max'] = (None, obsweewx[1], obsweewx[2])
                            pass
                        try:
                            data_temp['3h'][timestamps[i]][obsapi]['sum'] = (sum(x for x in interval_values if x is not None), obsweewx[1], obsweewx[2])
                        except (ValueError, TypeError, ArithmeticError):
                            data_temp['3h'][timestamps[i]][obsapi]['sum'] = (None, obsweewx[1], obsweewx[2])
                            pass
                    interval_start += (3 * 3600)
                    ii += 1
                    #logdbg("thread '%s': 3h hours %s" % (self.name, str(hours)))
                    #logdbg("thread '%s': 3h %s" % (self.name, json.dumps(data_temp['3h'][timestamps[i]])))
                    if ii >= 8 or interval_start > end_day_ts:
                        break
        except Exception as e:
            exception_output(self.name, e)
            return None

        # 1h interval
        data_temp['1h'] = dict()
        interval_start = next_hour_ts
        ii = 0
        try:
            for i in range(len(timestamps)):
                if timestamps[i] > end_day_ts:
                    break
                if timestamps[i] >= interval_start:
                    data_temp['1h'][timestamps[i]] = dict()
                    for obsapi, obsweewx in self.hourly_obs.items():
                        data_temp['1h'][timestamps[i]][obsapi] = dict()
                        obslist = apidata['hourly'].get(obsapi)
                        if obslist is None or len(obslist) != timestamp_len:
                            if log_failure or debug > 0:
                                if obslist is None:
                                    logerr("thread '%s': getDataIntervalCalc None for ts %s obs %s - %s" % (self.name, str(timestamps[i]), obsapi, obsweewx[0]))
                                elif len(obslist) != timestamp_len is None:
                                    logerr("thread '%s': getDataIntervalCalc number of values not equal to number of timestamps %d != %d" % (self.name, len(obslist), timestamp_len))
                            data_temp['1h'][timestamps[i]][obsapi]['val'] = (None, obsweewx[1], obsweewx[2])
                            continue
                        data_temp['1h'][timestamps[i]][obsapi]['val'] = (obslist[i], obsweewx[1], obsweewx[2])
                    #interval_start += 3600
                    ii += 1
                    #logdbg("thread '%s': 1h %s" % (self.name, json.dumps(data_temp['1h'][timestamps[i]])))
                    if ii >= 16 or interval_start > end_day_ts:
                        break
        except Exception as e:
            exception_output(self.name, e)
            return None

        # Database
        data_temp['db'] = dict()
        interval_start = next_hour_ts
        try:
            for i in range(len(timestamps)):
                if timestamps[i] > end_day_ts:
                    break
                if timestamps[i] >= interval_start:
                    data_temp['db'][timestamps[i]] = dict()
                    for obsapi, obsweewx in self.hourly_obs.items():
                        data_temp['db'][timestamps[i]][obsapi] = dict()
                        obslist = apidata['hourly'].get(obsapi)
                        if obslist is None or len(obslist) != timestamp_len:
                            if log_failure or debug > 0:
                                if obslist is None:
                                    logerr("thread '%s': getDataIntervalCalc None for ts %s obs %s - %s" % (self.name, str(timestamps[i]), obsapi, obsweewx[0]))
                                elif len(obslist) != timestamp_len:
                                    logerr("thread '%s': getDataIntervalCalc number of values not equal to number of timestamps %d != %d" % (self.name, len(obslist), timestamp_len))
                            data_temp['db'][timestamps[i]][obsapi]['val'] = (None, obsweewx[1], obsweewx[2])
                            continue
                        data_temp['db'][timestamps[i]][obsapi]['val'] = (obslist[i], obsweewx[1], obsweewx[2])
        except Exception as e:
            exception_output(self.name, e)
            return None
        return data_temp


    def get_data_api(self):
        """ download and process Open-Meteo forecast data """

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

        # forecast
        # https://api.open-meteo.com/v1/forecast?latitude=49.6333&longitude=12.0667&hourly=XXX&daily=XXX&timeformat=unixtime&timezone=GMT&models=best_match&forecast_days=10
        # DWD-ICON
        # https://api.open-meteo.com/v1/dwd-icon?latitude=49.6333&longitude=12.0667&hourly=XXX&daily=XXX&timeformat=unixtime&timezone=GMT&start_date=2023-08-09&end_date=2023-08-16
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
        params += '&timezone=GMT'

        # TODO config param?
        # cell_selection, land | sea | nearest
        # Set a preference how grid-cells are selected. The default land finds a suitable grid-cell on land with similar
        # elevation to the requested coordinates using a 90-meter digital elevation model. sea prefers grid-cells on sea.
        # nearest selects the nearest possible grid-cell.
        #params += '&cell_selection=land'

        # The time interval to get weather data. A day must be specified as an ISO8601 date (e.g. 2022-06-30).
        # if endpoint == 'forecast':
            # params += '&forecast_days=10'
        # else:
        today = datetime.datetime.today().strftime('%Y-%m-%d')
        lastday = datetime.datetime.now() + datetime.timedelta(8)
        lastday = datetime.datetime.strftime(lastday, '%Y-%m-%d')
        params += '&start_date=%s' % today
        params += '&end_date=%s' % lastday

        # units
        # The API request is made in the metric system
        # Temperature in celsius
        params += '&temperature_unit=celsius'
        # Wind in km/h
        params += '&windspeed_unit=kmh'
        # Precipitation in mm
        params += '&precipitation_unit=mm'

        # A list of weather variables which should be returned. Values can be comma separated,
        # or multiple &hourly= parameter in the URL can be used.
        # defined in HOURLYOBS
        params += '&hourly='+','.join([ii for ii in self.hourly_obs])

        # A list of weather variables which should be returned. Values can be comma separated,
        # or multiple &daily= parameter in the URL can be used.
        # defined in DAILYOBS
        params += '&daily='+','.join([ii for ii in self.daily_obs])

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
                                            debug = debug,
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
            apidata = None
            return False

        if debug > 2:
            logdbg("thread '%s': get_data_api api unchecked result %s" % (self.name, json.dumps(apidata)))

        # check results

        try:
            # check unit system
            if unitsystem is None and apidata.get('usUnits') is None:
                if log_failure or debug > 0:
                    logerr("thread '%s': get_data_api api did not send unit system and it's not configured in section [api_in]" % (self.name))
                apidata = None
                return False

            for obs in ('hourly', 'daily'):
                if apidata.get(obs) is None:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api api sent no %s data" % (self.name, obs))
                    apidata = None
                    return False

                # timestamps
                timestamps = apidata[obs].get('time')
                if timestamps is None:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api api sent no %s time periods data" % (self.name, obs))
                    apidata = None
                    return False

                if not isinstance(timestamps, list):
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api api sent %s time periods data not as list" % (self.name, obs))
                    apidata = None
                    return False

                if len(timestamps) == 0:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api api sent %s time periods without data" % (self.name, obs))
                    apidata = None
                    return False

                # check api units again configured units
                api_units = apidata.get(obs+'_units')
                if api_units is None:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api api sent no %s_units data" % (self.name, obs))
                    apidata = None
                    return False
                if obs == 'hourly':
                    for obsapi, obsweewx in self.hourly_obs.items():
                        unitapi = api_units.get(obsapi)
                        if unitapi is None:
                            if log_failure or debug > 0:
                                logerr("thread '%s': get_data_api no unit for obs %s - %s" % (self.name, obsapi, obsweewx[0]))
                        unitweewx = self.api_to_weewx_units.get(unitapi)
                        if unitweewx is None:
                            if log_failure or debug > 0:
                                logerr("thread '%s': get_data_api obs %s could not convert api unit %s to weewx unit" % (self.name, obsapi, str(unitapi)))
                        obsweewx = self.hourly_obs.get(obsapi)
                        if unitweewx != obsweewx[1]:
                            if log_failure or debug > 0:
                                logerr("thread '%s': get_data_api obs %s converted api unit %s != configured weewx unit %s" % (self.name, obsapi, unitweewx, obsweewx[1]))
                    # TODO doing?
                else:
                    for obsapi, obsweewx in self.daily_obs.items():
                        unitapi = api_units.get(obsapi)
                        if unitapi is None:
                            if log_failure or debug > 0:
                                logerr("thread '%s': get_data_api no unit for obs %s - %s" % (self.name, obsapi, obsweewx[0]))
                        unitweewx = self.api_to_weewx_units.get(unitapi)
                        if unitweewx is None:
                            if log_failure or debug > 0:
                                logerr("thread '%s': get_data_api obs %s could not convert api unit %s to weewx unit" % (self.name, obsapi, str(unitapi)))
                        obsweewx = self.daily_obs.get(obsapi)
                        if unitweewx != obsweewx[1]:
                            if log_failure or debug > 0:
                                logerr("thread '%s': get_data_api obs %s converted api unit %s != configured weewx unit %s" % (self.name, obsapi, unitweewx, obsweewx[1]))
                    # TODO doing?

            actts = weeutil.weeutil.to_int(time.time())
            self.data_temp['dateTime'] = weeutil.weeutil.to_int(actts)
            self.data_temp['dateTimeISO'] = get_isodate_from_timestamp(weeutil.weeutil.to_int(actts), self.timezone)
            self.data_temp['generated'] = weeutil.weeutil.to_int(actts)
            self.data_temp['generatedISO'] = get_isodate_from_timestamp(weeutil.weeutil.to_int(actts), self.timezone)
            lat = apidata.get('latitude', self.lat)
            lon = apidata.get('longitude', self.lon)
            alt = apidata.get('elevation', self.alt)
            self.data_temp['latitude'] = lat
            self.data_temp['longitude'] = lon
            self.data_temp['altitude'] = alt
            self.data_temp['sourceProvider'] = PROVIDER[self.source_id][0]
            self.data_temp['sourceUrl'] = obfuscate_secrets(url)
            self.data_temp['sourceProviderLink'] = PROVIDER[self.source_id][1]
            self.data_temp['sourceProviderHTML'] = HTMLTMPL % (PROVIDER[self.source_id][1], PROVIDER[self.source_id][0], PROVIDER[self.source_id][2])
            self.data_temp['sourceModul'] = self.name
            self.data_temp['sourceId'] = self.source_id
            self.data_temp['lang'] = lang
            self.data_temp['usUnits'] = unitsystem
            self.data_temp['1h'] = dict()
            self.data_temp['3h'] = dict()
            self.data_temp['24h'] = dict()
            self.data_temp['db'] = dict()

            data_interval_calc = self.getDataIntervalCalc(apidata, debug=debug, log_success=log_success, log_failure=log_failure)
            if data_interval_calc is None:
                if log_failure or debug > 0:
                    logerr("thread '%s': get_data_api getDataIntervalCalc returned None" % self.name)
                self.data_temp = dict()
                apidata = None
                return False

            lat = (lat, 'degree_compass', 'group_coordinate')
            lon = (lon, 'degree_compass', 'group_coordinate')
            alt = (alt, 'meter', 'group_altitude')
            data_interval = self.getDataInterval(data_interval_calc, unitsystem, lat, lon, alt, lang, debug=debug, log_success=log_success, log_failure=log_failure)
            if data_interval is None:
                if log_failure or debug > 0:
                    logerr("thread '%s': get_data_api getIntervalData returned None" % self.name)
                self.data_temp = dict()
                apidata = None
                return False

            self.data_temp['1h'] = data_interval['1h']
            self.data_temp['3h'] = data_interval['3h']
            self.data_temp['24h'] = data_interval['24h']
            self.data_temp['db'] = data_interval['db']
        except Exception as e:
            exception_output(self.name, e)
            self.data_temp = dict()
            apidata = None
            return False

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
    # response:
    # {
      # "weather": [
        # {
          # "timestamp": "2023-08-10T11:00:00+00:00",
          # "source_id": 3352,
          # "precipitation": 0,
          # "pressure_msl": 1021.3,
          # "sunshine": 50,
          # "temperature": 19.9,
          # "wind_direction": 263,
          # "wind_speed": 9.3,
          # "cloud_cover": 27,
          # "dew_point": 6.7,
          # "relative_humidity": null,
          # "visibility": 59300,
          # "wind_gust_direction": null,
          # "wind_gust_speed": 20.4,
          # "condition": "dry",
          # "precipitation_probability": 1,
          # "precipitation_probability_6h": null,
          # "solar": 0.767,
          # "icon": "partly-cloudy-day"
        # },
        # {
        # ...
        # }
      # ],
      # "sources": [
        # {
          # "id": 3352,
          # "dwd_station_id": "05397",
          # "observation_type": "forecast",
          # "lat": 49.67,
          # "lon": 12.18,
          # "height": 438,
          # "station_name": "WEIDEN",
          # "wmo_station_id": "10688",
          # "first_record": "2023-08-10T08:00:00+00:00",
          # "last_record": "2023-08-20T16:00:00+00:00"
        # }
      # ]
    # }

    # Mapping API observation fields -> WeeWX field, unit, group
    HOURLYOBS = {
        'timestamp': ('timestamp', 'unix_epoch', 'group_time'),
        'source_id': ('bsk_code', 'count', 'group_count'),
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
        'precipitation_probability': ('pop', 'percent', 'group_percent'),
        'precipitation_probability_6h': ('pop6h', 'percent', 'group_percent'),
        'solar': ('radiation', 'kilowatt_hour_per_meter_squared', 'group_radiation_energy'), # TODO check this
        'icon': ('icon', None, None),
        'iconId': ('iconId', 'count', 'group_count'),
        'condition': ('condition', None, None),
        'conditionId': ('conditionId', 'count', 'group_count'),
        'weathercode': ('weathercode', 'count', 'group_count'),
    }

    # Mapping API icon field to internal weathercode
    # https://brightsky.dev/docs/#/operations/getWeather
    # Icon alias suitable for the current weather conditions. Unlike the numerical parameters,
    # this field is not taken as-is from the raw data (because it does not exist), but is calculated
    # from different fields in the raw data as a best effort. Not all values are available for all source types.
    # Allowed values:   clear-day, clear-night, partly-cloudy-day, partly-cloudy-night, cloudy, fog, wind,
    #                   rain, sleet, snow, hail, thunderstorm, null
    ICONS = {
        'unknown': -1,
        'clear-day': 0,
        'clear-night': 0,
        'partly-cloudy-day': 2,
        'partly-cloudy-night': 2,
        'cloudy': 4,
        'wind': 10,
        'snow': 73,
        'fog': 45,
        'rain': 63,
        'hail': 77,
        'sleet': 85,
        'thunderstorm': 95,
    }

    # Mapping API condition field to internal weathercode
    # https://brightsky.dev/docs/#/operations/getWeather
    # Current weather conditions. Unlike the numerical parameters, this field is not taken as-is from
    # the raw data (because it does not exist), but is calculated from different fields in the raw data
    # as a best effort. Not all values are available for all source types.
    # Allowed values: dry, fog, rain, sleet, snow, hail, thunderstorm, null
    CONDITIONS = {
        'unknown': -1,
        'dry': 0,
        'fog': 45,
        'rain': 63,
        'sleet': 85,
        'snow': 73,
        'hail': 77,
        'thunderstorm': 95
    }

    # Mapping internal weathercode to aeris code
    BRIGHTSKY_AERIS = {
         -1: '::NA',
          0: '::CL',
          2: '::SC',
          4: '::OV',
         10: '::WG',
         73: '::S',
         45: '::BR',
         63: '::R',
         77: '::A',
         85: '::RS',
         95: '::T'
    }

    def get_aeriscode(self, code):
        """ get aeris weathercode from weathercode """
        try:
            x = self.BRIGHTSKY_AERIS[code]
        except (LookupError, TypeError):
            x = self.BRIGHTSKY_AERIS[-1]
        return x

    def get_icon_weathercode(self, icon):
        """ get brightsky weathercode from api icon """
        try:
            x = self.ICONS[icon]
        except (LookupError, TypeError):
            x = self.WEATHERCODE['unknown']
        return x

    def get_weathercode_icon(self, weathercode):
        """ get brightsky icon from brightsky weathercode """
        for icon in self.ICONS:
            code = self.get_icon_weathercode(icon)
            if code == weathercode:
                return icon
        return 'unknown'

    def get_condition_weathercode(self, condition):
        """ get brightsky weathercode from api condition """
        try:
            x = self.CONDITIONS[condition]
        except (LookupError, TypeError):
            x = self.CONDITIONS['unknown']
        return x

    def get_weathercode_condition(self, weathercode):
        """ get brightsky condition from brightsky weathercode """
        for condition in self.CONDITIONS:
            code = self.get_condition_weathercode(condition)
            if code == weathercode:
                return condition
        return 'unknown'

    def get_hourly_obs(self):
        return BRIGHTSKYthread.HOURLYOBS


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
        self.provider = self.config.get('provider', 'brightsky')
        self.model = self.config.get('model', 'brightsky')
        self.source_id = self.config.get('source_id', 'brightsky')
        self.interval_get = weeutil.weeutil.to_int(self.config.get('interval_get', 300))
        self.interval_push = weeutil.weeutil.to_int(self.config.get('interval_push', 30))
        self.expired = weeutil.weeutil.to_int(self.config.get('expired', 600))
        self.icon_path_belchertown = self.config.get('icon_path_belchertown', '')
        self.timezone = self.config.get('timezone', 'Europe/Berlin')
        self.hourly_obs = self.get_hourly_obs()
        self.primary_api_query = None
        self.primary_api_query_fallback = None
        self.config_dict = thread_dict.get('config_dict')
        self.engine = thread_dict.get('engine')
        self.data_result = dict()
        self.data_temp = dict()
        self.last_get_ts = 0

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

        weewx.units.obs_group_dict.setdefault('dateTime','group_time')
        weewx.units.obs_group_dict.setdefault('generated','group_time')
        weewx.units.obs_group_dict.setdefault('age','group_deltatime')
        weewx.units.obs_group_dict.setdefault('day','group_count')
        weewx.units.obs_group_dict.setdefault('expired','group_count')
        weewx.units.obs_group_dict.setdefault('weathercode','group_count')
        weewx.units.obs_group_dict.setdefault('weathercodeKey','group_count')

        for opsapi, obsweewx in self.hourly_obs.items():
            weewx.units.obs_group_dict.setdefault(obsweewx[0],obsweewx[2])

        dbout_dict = self.config.get('db_out', configobj.ConfigObj())
        if weeutil.weeutil.to_bool(dbout_dict.get('enable', False)):
            data_binding_name = dbout_dict.get('data_binding')
            if data_binding_name is None:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': init data_binding is not configured!" % (self.name))
                return
            # open the data store
            self.dbm = self.engine.db_binder.get_manager(data_binding=data_binding_name, initialize=True)
            # confirm db schema
            dbcols = self.dbm.connection.columnsOf(self.dbm.table_name)
            dbm_dict = weewx.manager.get_manager_dict_from_config(self.config_dict, data_binding_name)
            memcols = [x[0] for x in dbm_dict['schema']]
            if dbcols != memcols:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': init store schema mismatch: %s != %s" % (self.name, dbcols, memcols))
                return
        elif self.log_success or self.debug > 0:
            loginf("thread '%s': init db_out is diabled. Enable it in the [db_out] section of station %s" %(self.name, self.station))

        if self.log_success or self.debug > 0:
            loginf("thread '%s': init finished" % self.name)


    def getDataInterval(self, data_interval_calc, unitsystem, lat, lon, alt, lang, debug=0, log_success=False, log_failure=True):
        """ preprocess MOSMIX interval forecast data """

        data_temp = dict()

        # temp using for is_night
        night_dict = dict()
        night_dict['latitude'] = lat
        night_dict['longitude'] = lon
        night_dict['altitude'] = alt

        try:
            for interval, intervaldata in data_interval_calc.items():
                data_temp[interval] = dict()
                col = 0
                for ts, tsdata in intervaldata.items():
                    col += 1
                    data_temp[interval][str(col)] = dict()
                    data_temp[interval][str(col)]['timestamp'] = (ts, 'unix_epoch', 'group_time')
                    data_temp[interval][str(col)]['timestampISO'] = (get_isodate_from_timestamp(ts, self.timezone), None, None)
                    for apiobs, obsdata in tsdata.items():
                        weewxobs = self.hourly_obs.get(apiobs)
                        #logdbg("thread '%s': getDataInterval apiobs %s" % (self.name, apiobs))
                        #logdbg("thread '%s': getDataInterval weewxobs %s" % (self.name, weewxobs))
                        #logdbg("thread '%s': getDataInterval obsdata %s" % (self.name, str(obsdata)))
                        if weewxobs is None:
                            if log_failure or debug > 0:
                                logerr("thread '%s': getDataInterval unknown api obs '%s'" % (self.name, apiobs))
                            continue
                        if interval in ('1h','db') or apiobs in ('icon', 'condition'):
                            vt = obsdata['val']
                            vt = to_weewx(self.name, vt, unitsystem, debug=debug, log_success=log_success, log_failure=log_failure)
                            #logdbg("thread '%s': getDataInterval vt %s" % (self.name, str(vt)))
                        elif weewxobs[1] is not None:
                            vt_min = obsdata['min']
                            vt_min = to_weewx(self.name, vt_min, unitsystem, debug=debug, log_success=log_success, log_failure=log_failure)

                            vt_avg = obsdata['avg']
                            vt_avg = to_weewx(self.name, vt_avg, unitsystem, debug=debug, log_success=log_success, log_failure=log_failure)

                            vt_max = obsdata['max']
                            vt_max = to_weewx(self.name, vt_max, unitsystem, debug=debug, log_success=log_success, log_failure=log_failure)

                            vt_sum = obsdata['sum']
                            vt_sum = to_weewx(self.name, vt_sum, unitsystem, debug=debug, log_success=log_success, log_failure=log_failure)

                            #logdbg("thread '%s': getDataInterval vt_min %s" % (self.name, str(vt_min)))
                            #logdbg("thread '%s': getDataInterval vt_avg %s" % (self.name, str(vt_avg)))
                            #logdbg("thread '%s': getDataInterval vt_max %s" % (self.name, str(vt_max)))
                            #logdbg("thread '%s': getDataInterval vt_sum %s" % (self.name, str(vt_sum)))

                        # Filter
                        # 'timestamp': ('timestamp', 'unix_epoch', 'group_time'),
                        # 'source_id': ('bsk_code', 'count', 'group_count'),
                        # 'precipitation': ('precipitation', 'mm', 'group_rain'),
                        # 'pressure_msl': ('barometer', 'hPa', 'group_pressure'),
                        # 'sunshine': ('sunshineDur', 'minute', 'group_deltatime'),
                        # 'temperature': ('outTemp', 'degree_C', 'group_temperature'),
                        # 'wind_direction': ('windDir', 'degree_compass', 'group_direction'),
                        # 'wind_speed': ('windSpeed', 'km_per_hour', 'group_speed'),
                        # 'cloud_cover': ('cloudcover', 'percent', 'group_percent'),
                        # 'dew_point': ('dewpoint', 'degree_C', 'group_temperature'),
                        # 'relative_humidity': ('outHumidity', 'percent', 'group_percent'),
                        # 'visibility': ('visibility', 'meter', 'group_distance'),
                        # 'wind_gust_direction': ('windGustDir', 'degree_compass', 'group_direction'),
                        # 'wind_gust_speed': ('windGust', 'km_per_hour', 'group_speed'),
                        # 'precipitation_probability': ('pop', 'percent', 'group_percent'),
                        # 'precipitation_probability_6h': ('pop6h', 'percent', 'group_percent'),
                        # 'solar': ('radiation', 'kilowatt_hour_per_meter_squared', 'group_radiation_energy'), # TODO check this
                        # 'icon': ('icon', None, None),
                        # 'iconId': ('iconId', 'count', 'group_count'),
                        # 'condition': ('condition', None, None),
                        # 'conditionId': ('conditionId', 'count', 'group_count'),
                        # 'weathercode': ('weathercode', 'count', 'group_count'),
                        if apiobs == 'icon':
                            data_temp[interval][str(col)]['icons'] = vt
                        elif apiobs == 'condition':
                            data_temp[interval][str(col)]['conditions'] = vt
                        elif weewxobs[2] in ('group_temperature', 'group_speed'):
                            if interval in ('1h','db'):
                                data_temp[interval][str(col)][weewxobs[0]] = vt
                            else:
                                data_temp[interval][str(col)][weewxobs[0]+'_min'] = vt_min
                                data_temp[interval][str(col)][weewxobs[0]+'_avg'] = vt_avg
                                data_temp[interval][str(col)][weewxobs[0]+'_max'] = vt_max
                        elif weewxobs[2] in ('group_pressure', 'group_direction'):
                            if interval in ('1h','db'):
                                data_temp[interval][str(col)][weewxobs[0]] = vt
                            else:
                                data_temp[interval][str(col)][weewxobs[0]] = vt_avg
                        elif weewxobs[2] in ('group_count', 'group_percent'):
                            if interval in ('1h','db'):
                                data_temp[interval][str(col)][weewxobs[0]] = vt if vt[0] is not None else (0.0, vt[1], vt[2])
                            else:
                                data_temp[interval][str(col)][weewxobs[0]] = vt_max if vt_max[0] is not None else (0.0, vt_max[1], vt_max[2])
                        elif weewxobs[2] in ('group_distance'):
                            if interval in ('1h','db'):
                                data_temp[interval][str(col)][weewxobs[0]] = vt
                            else:
                                data_temp[interval][str(col)][weewxobs[0]] = vt_min
                        elif weewxobs[2] in ('group_rain'):
                            if interval in ('1h','db'):
                                data_temp[interval][str(col)][weewxobs[0]] = vt if vt[0] is not None else (0.0, vt[1], vt[2])
                            else:
                                data_temp[interval][str(col)][weewxobs[0]] = vt_sum if vt_sum[0] is not None else (0.0, vt_sum[1], vt_sum[2])

                    # outHumidity
                    if data_temp[interval][str(col)].get('outHumidity')[0] < 1.0 or data_temp[interval][str(col)].get('outHumidity')[0] is None:
                        if interval in ('1h','db'):
                            t = data_temp[interval][str(col)].get('outTemp')[0]
                            rd = data_temp[interval][str(col)].get('dewpoint')[0]
                        else:
                            t = data_temp[interval][str(col)].get('outTemp_avg')[0]
                            td = data_temp[interval][str(col)].get('dewpoint_avg')[0]
                        h = get_humidity(self.name, t, td, debug=debug, log_success=log_success, log_failure=log_failure)
                        data_temp[interval][str(col)]['outHumidity'] = (weeutil.weeutil.to_int(h), 'percent', 'group_percent')

                    # compass
                    wdir = data_temp[interval][str(col)].get('windDir')
                    if wdir is not None:
                        data_temp[interval][str(col)]['compass'] = (compass(wdir[0], lang), None, None)
                    else:
                        data_temp[interval][str(col)]['compass'] = ('', None, None)

                    # is night?
                    night_dict['dateTime'] = (ts, 'unix_epoch', 'group_time')
                    if interval in ('1h','db'):
                        night_dict['outTemp'] = data_temp[interval][str(col)].get('outTemp')
                        night_dict['barometer'] = data_temp[interval][str(col)].get('barometer')
                        night = is_night(self.name, night_dict, debug=debug, log_success=log_success, log_failure=log_failure)
                    elif interval == '3h':
                        night_dict['outTemp'] = data_temp[interval][str(col)].get('outTemp_max')
                        night_dict['barometer'] = data_temp[interval][str(col)].get('barometer')
                        night = is_night(self.name, night_dict, debug=debug, log_success=log_success, log_failure=log_failure)
                    else:
                        night = 0
                    data_temp[interval][str(col)]['day'] = (0 if night else 1, 'count', 'group_count')

                    # weathertext and weathericon
                    code = data_temp[interval][str(col)].get('weathercode')[0]
                    aeriscode = self.get_aeriscode(code)
                    data_temp[interval][str(col)]['weathercodeAeris'] = (aeriscode, None, None)
                    # return (text_de, text_en, icon, weathercode)
                    wxdata = self.get_icon_and_text(aeriscode, night=night, debug=debug, log_success=log_success, log_failure=log_failure, weathertext_en=None)
                    data_temp[interval][str(col)]['weathercodeKey'] = (weeutil.weeutil.to_int(wxdata[3]), 'count', 'group_count')
                    data_temp[interval][str(col)]['weathericon'] = (wxdata[2], None, None)
                    data_temp[interval][str(col)]['weathertext'] = dict()
                    data_temp[interval][str(col)]['weathertext']['de'] = (wxdata[0], None, None)
                    data_temp[interval][str(col)]['weathertext']['en'] = (wxdata[1], None, None)
        except Exception as e:
            exception_output(self.name, e)
            return None
        return data_temp

    def getDataIntervalCalc(self, apidata, debug=0, log_success=False, log_failure=True):
        """ preprocess Brightsky api forecast data """

        try:
            data_temp = dict()
            timestamps = apidata['hourly'].get('timestamp')
            timestamp_len = len(timestamps)

            # current timestamp
            current_time = datetime.datetime.now(pytz.utc)
            current_time_ts = weeutil.weeutil.to_int(current_time.timestamp())
            current_time_berlin = current_time.astimezone(pytz.timezone('Europe/Berlin'))
            utcoffset = weeutil.weeutil.to_int(current_time_berlin.utcoffset().total_seconds())

            # start with the next full hour timestamp
            next_hour = current_time.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
            next_hour_ts = weeutil.weeutil.to_int(next_hour.timestamp())

            # or start with the current full hour timestamp
            current_hour = current_time.replace(minute=0, second=0, microsecond=0)
            current_hour_ts = weeutil.weeutil.to_int(current_hour.timestamp())

            # next day 00:00 timestamp
            next_day = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
            next_day_ts = weeutil.weeutil.to_int(next_day.timestamp()) - utcoffset

            # max 8 days 
            end_day = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=8)
            end_day_ts = weeutil.weeutil.to_int(end_day.timestamp()) - utcoffset

            # diff hours from start to 24h
            today_remaining_hours = weeutil.weeutil.to_int((next_day_ts + utcoffset - next_hour_ts) / 3600)

            if debug > 2:
                logdbg("thread '%s': current_time_ts %d" % (self.name, current_time_ts))
                logdbg("thread '%s': current_time_ts %s" % (self.name, current_time.isoformat(sep="T", timespec="seconds")))
                logdbg("thread '%s': current_time_ts %s" % (self.name, get_isodate_from_timestamp(current_time_ts)))

                logdbg("thread '%s': current_hour_ts %d" % (self.name, current_hour_ts))
                logdbg("thread '%s': current_hour_ts %s" % (self.name, current_hour.isoformat(sep="T", timespec="seconds")))
                logdbg("thread '%s': current_hour_ts %s" % (self.name, get_isodate_from_timestamp(current_hour_ts)))

                logdbg("thread '%s':    next_hour_ts %d" % (self.name, next_hour_ts))
                logdbg("thread '%s':    next_hour_ts %s" % (self.name, next_hour.isoformat(sep="T", timespec="seconds")))
                logdbg("thread '%s':    next_hour_ts %s" % (self.name, get_isodate_from_timestamp(next_hour_ts)))

                logdbg("thread '%s':     next_day_ts %d" % (self.name, next_day_ts))
                logdbg("thread '%s':     next_day_ts %s" % (self.name, next_day.isoformat(sep="T", timespec="seconds")))
                logdbg("thread '%s':     next_day_ts %s" % (self.name, get_isodate_from_timestamp(next_day_ts)))

                logdbg("thread '%s':      end_day_ts %d" % (self.name, end_day_ts))
                logdbg("thread '%s':      end_day_ts %s" % (self.name, end_day.isoformat(sep="T", timespec="seconds")))
                logdbg("thread '%s':      end_day_ts %s" % (self.name, get_isodate_from_timestamp(end_day_ts)))

                logdbg("thread '%s': today_remaining_hours: %d" % (self.name, today_remaining_hours))
                logdbg("thread '%s':       timezone offset: %d" % (self.name, utcoffset))

        except Exception as e:
            exception_output(self.name, e)
            return None

        # 24h interval
        data_temp['24h'] = dict()
        interval_start = next_hour_ts
        if interval_start < next_day_ts:
            hours = today_remaining_hours
        else:
            hours = 24
        ii = 0
        try:
            for i in range(len(timestamps)):
                if timestamps[i] >= interval_start:
                    data_temp['24h'][timestamps[i]] = dict()
                    for obsapi, obsweewx in self.hourly_obs.items():
                        data_temp['24h'][timestamps[i]][obsapi] = dict()
                        obslist = apidata['hourly'].get(obsapi)
                        if obslist is None or len(obslist) != timestamp_len:
                            if log_failure or debug > 0:
                                if obslist is None:
                                    logerr("thread '%s': getDataIntervalCalc None for ts %s obs %s - %s" % (self.name, str(timestamps[i]), obsapi, obsweewx[0]))
                                elif len(obslist) != timestamp_len is None:
                                    logerr("thread '%s': getDataIntervalCalc obs %s number of values not equal to number of timestamps %d != %d" % (self.name, obsapi, len(obslist), timestamp_len))
                            data_temp['24h'][timestamps[i]][obsapi]['min'] = (None, obsweewx[1], obsweewx[2])
                            data_temp['24h'][timestamps[i]][obsapi]['avg'] = (None, obsweewx[1], obsweewx[2])
                            data_temp['24h'][timestamps[i]][obsapi]['max'] = (None, obsweewx[1], obsweewx[2])
                            data_temp['24h'][timestamps[i]][obsapi]['sum'] = (None, obsweewx[1], obsweewx[2])
                            data_temp['24h'][timestamps[i]][obsapi]['val'] = (None, obsweewx[1], obsweewx[2])
                            continue
                        interval_values = obslist[i:i+hours]
                        if obsweewx[2] is None:
                            data_temp['24h'][timestamps[i]][obsapi]['val'] = (interval_values, obsweewx[1], obsweewx[2])
                        else:
                            try:
                                data_temp['24h'][timestamps[i]][obsapi]['min'] = (min(x for x in interval_values if x is not None), obsweewx[1], obsweewx[2])
                            except (ValueError, TypeError, ArithmeticError):
                                data_temp['24h'][timestamps[i]][obsapi]['min'] = (None, obsweewx[1], obsweewx[2])
                                pass
                            try:
                                data_temp['24h'][timestamps[i]][obsapi]['avg'] = (mean(x for x in interval_values if x is not None), obsweewx[1], obsweewx[2])
                            except (ValueError, TypeError, ArithmeticError):
                                data_temp['24h'][timestamps[i]][obsapi]['avg'] = (None, obsweewx[1], obsweewx[2])
                                pass
                            try:
                                data_temp['24h'][timestamps[i]][obsapi]['max'] = (max(x for x in interval_values if x is not None), obsweewx[1], obsweewx[2])
                            except (ValueError, TypeError, ArithmeticError):
                                data_temp['24h'][timestamps[i]][obsapi]['max'] = (None, obsweewx[1], obsweewx[2])
                                pass
                            try:
                                data_temp['24h'][timestamps[i]][obsapi]['sum'] = (sum(x for x in interval_values if x is not None), obsweewx[1], obsweewx[2])
                            except (ValueError, TypeError, ArithmeticError):
                                data_temp['24h'][timestamps[i]][obsapi]['sum'] = (None, obsweewx[1], obsweewx[2])
                                pass

                    if hours < 24:
                        interval_start = next_day_ts
                        hours = 24
                    else:
                        interval_start += (hours * 3600)
                    #logdbg("thread '%s': 24h %s" % (self.name, json.dumps(data_temp['24h'][timestamps[i]])))
                    ii += 1
                    if ii >= 8 or interval_start > end_day_ts:
                        break
        except Exception as e:
            exception_output(self.name, e)
            return None

        # 3h interval
        data_temp['3h'] = dict()
        interval_start = next_hour_ts
        ii = 0
        try:
            for i in range(len(timestamps)):
                if timestamps[i] >= interval_start:
                    data_temp['3h'][timestamps[i]] = dict()
                    if timestamps[i] + (3 * 3600) > end_day_ts:
                        hours = weeutil.weeutil.to_int(end_day_ts - timestamps[i] / 3600)
                        if hours < 1:
                            break
                    else:
                        hours = 3
                    for obsapi, obsweewx in self.hourly_obs.items():
                        data_temp['3h'][timestamps[i]][obsapi] = dict()
                        obslist = apidata['hourly'].get(obsapi)
                        if obslist is None or len(obslist) != timestamp_len:
                            if log_failure or debug > 0:
                                if obslist is None:
                                    logerr("thread '%s': getDataIntervalCalc None for ts %s obs %s - %s" % (self.name, str(timestamps[i]), obsapi, obsweewx[0]))
                                elif len(obslist) != timestamp_len is None:
                                    logerr("thread '%s': getDataIntervalCalc number of values not equal to number of timestamps %d != %d" % (self.name, len(obslist), timestamp_len))
                            data_temp['3h'][timestamps[i]][obsapi]['min'] = (None, obsweewx[1], obsweewx[2])
                            data_temp['3h'][timestamps[i]][obsapi]['avg'] = (None, obsweewx[1], obsweewx[2])
                            data_temp['3h'][timestamps[i]][obsapi]['max'] = (None, obsweewx[1], obsweewx[2])
                            data_temp['3h'][timestamps[i]][obsapi]['sum'] = (None, obsweewx[1], obsweewx[2])
                            data_temp['3h'][timestamps[i]][obsapi]['val'] = (None, obsweewx[1], obsweewx[2])
                            continue
                        interval_values = obslist[i:i+hours]
                        # if obsapi == 'TTT':
                            # logdbg("thread '%s': 3h %s -> %s" % (self.name, obsapi, json.dumps(interval_values)))
                        if obsweewx[2] is None:
                            data_temp['3h'][timestamps[i]][obsapi]['val'] = (interval_values, obsweewx[1], obsweewx[2])
                        else:
                            try:
                                data_temp['3h'][timestamps[i]][obsapi]['min'] = (min(x for x in interval_values if x is not None), obsweewx[1], obsweewx[2])
                            except (ValueError, TypeError, ArithmeticError):
                                data_temp['3h'][timestamps[i]][obsapi]['min'] = (None, obsweewx[1], obsweewx[2])
                                pass
                            try:
                                data_temp['3h'][timestamps[i]][obsapi]['avg'] = (mean(x for x in interval_values if x is not None), obsweewx[1], obsweewx[2])
                            except (ValueError, TypeError, ArithmeticError):
                                data_temp['3h'][timestamps[i]][obsapi]['avg'] = (None, obsweewx[1], obsweewx[2])
                                pass
                            try:
                                data_temp['3h'][timestamps[i]][obsapi]['max'] = (max(x for x in interval_values if x is not None), obsweewx[1], obsweewx[2])
                            except (ValueError, TypeError, ArithmeticError):
                                data_temp['3h'][timestamps[i]][obsapi]['max'] = (None, obsweewx[1], obsweewx[2])
                                pass
                            try:
                                data_temp['3h'][timestamps[i]][obsapi]['sum'] = (sum(x for x in interval_values if x is not None), obsweewx[1], obsweewx[2])
                            except (ValueError, TypeError, ArithmeticError):
                                data_temp['3h'][timestamps[i]][obsapi]['sum'] = (None, obsweewx[1], obsweewx[2])
                                pass

                        # if obsapi == 'TTT':
                            # logdbg("thread '%s': 3h min %s -> %s" % (self.name, obsapi, json.dumps(data_temp['3h'][timestamps[i]][obsapi]['min'])))
                            # logdbg("thread '%s': 3h avg %s -> %s" % (self.name, obsapi, json.dumps(data_temp['3h'][timestamps[i]][obsapi]['avg'])))
                            # logdbg("thread '%s': 3h max %s -> %s" % (self.name, obsapi, json.dumps(data_temp['3h'][timestamps[i]][obsapi]['max'])))
                            # logdbg("thread '%s': 3h sum %s -> %s" % (self.name, obsapi, json.dumps(data_temp['3h'][timestamps[i]][obsapi]['sum'])))


                    interval_start += (3 * 3600)
                    ii += 1
                    #logdbg("thread '%s': 3h hours %s" % (self.name, str(hours)))
                    #logdbg("thread '%s': 3h %s" % (self.name, json.dumps(data_temp['3h'][timestamps[i]])))
                    if ii >= 8 or interval_start > end_day_ts:
                        break
        except Exception as e:
            exception_output(self.name, e)
            return None

        # 1h interval
        data_temp['1h'] = dict()
        interval_start = next_hour_ts
        ii = 0
        try:
            for i in range(len(timestamps)):
                if timestamps[i] > end_day_ts:
                    break
                if timestamps[i] >= interval_start:
                    data_temp['1h'][timestamps[i]] = dict()
                    for obsapi, obsweewx in self.hourly_obs.items():
                        data_temp['1h'][timestamps[i]][obsapi] = dict()
                        obslist = apidata['hourly'].get(obsapi)
                        if obslist is None or len(obslist) != timestamp_len:
                            if log_failure or debug > 0:
                                if obslist is None:
                                    logerr("thread '%s': getDataIntervalCalc None for ts %s obs %s - %s" % (self.name, str(timestamps[i]), obsapi, obsweewx[0]))
                                elif len(obslist) != timestamp_len is None:
                                    logerr("thread '%s': getDataIntervalCalc number of values not equal to number of timestamps %d != %d" % (self.name, len(obslist), timestamp_len))
                            data_temp['1h'][timestamps[i]][obsapi]['val'] = (None, obsweewx[1], obsweewx[2])
                            continue
                        data_temp['1h'][timestamps[i]][obsapi]['val'] = (obslist[i], obsweewx[1], obsweewx[2])
                    #interval_start += 3600
                    ii += 1
                    #logdbg("thread '%s': 1h %s" % (self.name, json.dumps(data_temp['1h'][timestamps[i]])))
                    if ii >= 16 or interval_start > end_day_ts:
                        break
        except Exception as e:
            exception_output(self.name, e)
            return None

        # Database
        data_temp['db'] = dict()
        interval_start = next_hour_ts
        try:
            for i in range(len(timestamps)):
                if timestamps[i] > end_day_ts:
                    break
                if timestamps[i] >= interval_start:
                    data_temp['db'][timestamps[i]] = dict()
                    for obsapi, obsweewx in self.hourly_obs.items():
                        data_temp['db'][timestamps[i]][obsapi] = dict()
                        obslist = apidata['hourly'].get(obsapi)
                        if obslist is None or len(obslist) != timestamp_len:
                            if log_failure or debug > 0:
                                if obslist is None:
                                    logerr("thread '%s': getDataIntervalCalc None for ts %s obs %s - %s" % (self.name, str(timestamps[i]), obsapi, obsweewx[0]))
                                elif len(obslist) != timestamp_len is None:
                                    logerr("thread '%s': getDataIntervalCalc number of values not equal to number of timestamps %d != %d" % (self.name, len(obslist), timestamp_len))
                            data_temp['db'][timestamps[i]][obsapi]['val'] = (None, obsweewx[1], obsweewx[2])
                            continue
                        data_temp['db'][timestamps[i]][obsapi]['val'] = (obslist[i], obsweewx[1], obsweewx[2])
        except Exception as e:
            exception_output(self.name, e)
            return None

        return data_temp


    def prepApidata(self, apidata, debug=0, log_success=False, log_failure=True):
        """ preprocess Brightsky api forecast data """

        weather = apidata.get('weather')
        data_temp = dict()
        data_temp['hourly'] = dict()
        try:
            for data in weather:
                for obsapi, obsweewx in self.hourly_obs.items():
                    if obsapi in ('icon', 'iconId','condition', 'conditionId', 'weathercode'):
                        if obsapi == 'icon':
                            if data_temp['hourly'].get(obsapi) is None:
                                data_temp['hourly'][obsapi] = list()
                            if data_temp['hourly'].get('iconId') is None:
                                data_temp['hourly']['iconId'] = list()
                            if data_temp['hourly'].get('weathercode') is None:
                                data_temp['hourly']['weathercode'] = list()
                            val = data.get(obsapi)
                            data_temp['hourly'][obsapi].append(val)
                            data_temp['hourly']['iconId'].append(self.get_icon_weathercode(val))
                            data_temp['hourly']['weathercode'].append(self.get_icon_weathercode(val))
                        elif obsapi == 'condition':
                            if data_temp['hourly'].get(obsapi) is None:
                                data_temp['hourly'][obsapi] = list()
                            if data_temp['hourly'].get('conditionId') is None:
                                data_temp['hourly']['conditionId'] = list()
                            val = data.get(obsapi)
                            data_temp['hourly'][obsapi].append(val)
                            data_temp['hourly']['conditionId'].append(self.get_condition_weathercode(val))
                        continue
                    elif obsapi == 'timestamp':
                        dt_string = data.get(obsapi)
                        dt = datetime.datetime.strptime(dt_string, "%Y-%m-%dT%H:%M:%S%z")
                        val = weeutil.weeutil.to_int(dt.timestamp())
                    else:
                        val = data.get(obsapi)
                    if data_temp['hourly'].get(obsapi) is None:
                        data_temp['hourly'][obsapi] = list()
                    data_temp['hourly'][obsapi].append(val)

        except Exception as e:
            exception_output(self.name, e)
            return None
        return data_temp


    def get_data_api(self):
        """ download and process Brightsky API forecast data """

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

        # current timestamp
        current_time = datetime.datetime.now(pytz.utc)
        current_time_ts = weeutil.weeutil.to_int(current_time.timestamp())
        current_time_berlin = current_time.astimezone(pytz.timezone('Europe/Berlin'))
        utcoffset = weeutil.weeutil.to_int(current_time_berlin.utcoffset().total_seconds())

        # start with the next full hour timestamp
        next_hour = current_time.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
        next_hour_ts = weeutil.weeutil.to_int(next_hour.timestamp())

        # next day 00:00 timestamp
        next_day = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
        next_day_ts = weeutil.weeutil.to_int(next_day.timestamp()) - utcoffset

        # max 8 days 
        end_day = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=8)
        end_day_ts = weeutil.weeutil.to_int(end_day.timestamp()) - utcoffset

        # diff hours from start to 24h
        today_remaining_hours = weeutil.weeutil.to_int((next_day_ts + utcoffset - next_hour_ts) / 3600)

        # https://api.brightsky.dev/weather?wmo_station_id=10688&tz=Etc/UTC&units=dwd&date=2023-08-10T11:00+00:00&last_date=2023-08-17T00:00+00:00
        baseurl = 'https://api.brightsky.dev/weather'

        # primary api query
        params = self.primary_api_query

        # Timezone in which record timestamps will be presented, as tz database name, e.g. Europe/Berlin.
        # Will also be used as timezone when parsing date and last_date, unless these have explicit UTC offsets.
        # If omitted but date has an explicit UTC offset, that offset will be used as timezone.
        # Otherwise will default to UTC.
        #params += '&tz=Europe/Berlin'
        params += '&tz=Etc/UTC'

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

        fromDate = next_hour.isoformat(sep='T', timespec='minutes')
        toDate = end_day.isoformat(sep='T', timespec='minutes')
        params += '&date=%s&last_date=%s' % (fromDate, toDate)

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
            apidata = None
            return False

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
            apidata = None
            return False

        sources = apidata.get('sources')
        if sources is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api did not send 'sources' data" % self.name)
            apidata = None
            return False

        # check unit system
        if unitsystem is None and weather.get('usUnits') is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api did not send unit system and it's not configured in section [api_in]" % (self.name))
            apidata = None
            return False

        try:
            actts = weeutil.weeutil.to_int(time.time())
            self.data_temp['dateTime'] = weeutil.weeutil.to_int(actts)
            self.data_temp['dateTimeISO'] = get_isodate_from_timestamp(weeutil.weeutil.to_int(actts), self.timezone)
            self.data_temp['generated'] = weeutil.weeutil.to_int(actts)
            self.data_temp['generatedISO'] = get_isodate_from_timestamp(weeutil.weeutil.to_int(actts), self.timezone)
            lat = sources[0].get('lat', self.lat)
            lon = sources[0].get('lon', self.lon)
            alt = sources[0].get('height', self.alt)
            self.data_temp['latitude'] = lat
            self.data_temp['longitude'] = lon
            self.data_temp['altitude'] = alt
            for source in sources:
                name = source.get('station_name')[0].upper() + source.get('station_name')[1:].lower()
                self.data_temp[name] = dict()
                self.data_temp[name]['wmo_code'] = source.get('wmo_station_id')
                self.data_temp[name]['dwd_code'] = source.get('dwd_station_id')
                self.data_temp[name]['bsk_code'] = source.get('id')
                self.data_temp[name]['latitude'] = source.get('lat')
                self.data_temp[name]['longitude'] = source.get('lon')
                self.data_temp[name]['altitude'] = source.get('height')
            self.data_temp['sourceProvider'] = PROVIDER[self.source_id][0]
            self.data_temp['sourceUrl'] = obfuscate_secrets(url)
            self.data_temp['sourceProviderLink'] = PROVIDER[self.source_id][1]
            self.data_temp['sourceProviderHTML'] = HTMLTMPL % (PROVIDER[self.source_id][1], PROVIDER[self.source_id][0], PROVIDER[self.source_id][2])
            self.data_temp['sourceModul'] = self.name
            self.data_temp['sourceId'] = self.source_id
            self.data_temp['lang'] = lang
            self.data_temp['usUnits'] = unitsystem
            self.data_temp['1h'] = dict()
            self.data_temp['3h'] = dict()
            self.data_temp['24h'] = dict()
            self.data_temp['db'] = dict()

            prep_apidata = self.prepApidata(apidata, debug=debug, log_success=log_success, log_failure=log_failure)
            if prep_apidata is None:
                if log_failure or debug > 0:
                    logerr("thread '%s': get_data_api prepApidata returned None" % self.name)
                self.data_temp = dict()
                apidata = None
                return False

            data_interval_calc = self.getDataIntervalCalc(prep_apidata, debug=debug, log_success=log_success, log_failure=log_failure)
            if data_interval_calc is None:
                if log_failure or debug > 0:
                    logerr("thread '%s': get_data_api getDataIntervalCalc returned None" % self.name)
                self.data_temp = dict()
                apidata = None
                prep_apidata = None
                return False

            lat = (lat, 'degree_compass', 'group_coordinate')
            lon = (lon, 'degree_compass', 'group_coordinate')
            alt = (alt, 'meter', 'group_altitude')
            data_interval = self.getDataInterval(data_interval_calc, unitsystem, lat, lon, alt, lang, debug=debug, log_success=log_success, log_failure=log_failure)
            if data_interval is None:
                if log_failure or debug > 0:
                    logerr("thread '%s': get_data_api getIntervalData returned None" % self.name)
                self.data_temp = dict()
                apidata = None
                prep_apidata = None
                return False

            self.data_temp['1h'] = data_interval['1h']
            self.data_temp['3h'] = data_interval['3h']
            self.data_temp['24h'] = data_interval['24h']
            self.data_temp['db'] = data_interval['db']
        except Exception as e:
            exception_output(self.name, e)
            self.data_temp = dict()
            apidata = None
            prep_apidata = None
            return False

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
    HOURLYOBS = {
        'ww': ('weathercode', 'count', 'group_count'),
        #'ww3': ('weathercode_3h', 'count', 'group_count'),
        'TTT': ('outTemp', 'degree_C', 'group_temperature'),
        'Td': ('dewpoint', 'degree_C', 'group_temperature'),
        'PPPP': ('barometer', 'hPa', 'group_pressure'),
        'FF': ('windSpeed', 'km_per_hour', 'group_speed'),
        'FX1': ('windGust', 'km_per_hour', 'group_speed'),
        'DD': ('windDir', 'degree_compass', 'group_direction'),
        'VV': ('visibility', 'meter', 'group_distance'),
        'Neff': ('cloudcover', 'percent', 'group_percent'),
        'N': ('cloudcoverTotal', 'percent', 'group_percent'),
        'RR1c': ('precipitation', 'mm', 'group_rain'),
        #'RR3c': ('precip_3h', 'mm', 'group_rain'),
        #'RRdc': ('precip_24h', 'mm', 'group_rain'),
        'RRL1c': ('rain', 'mm', 'group_rain'),
        'RRS1c': ('snowRain', 'mm', 'group_rain'),
        #'RRS3c': ('snowRain_3h', 'mm', 'group_rain'),
        'wwD': ('pos', 'percent', 'group_percent'), # Probability of Snow
        'wwF': ('pofr', 'percent', 'group_percent'), # Probability of Freezing Rain
        'wwL': ('por', 'percent', 'group_percent'), # Probability of Rain
        'wwP': ('pop', 'percent', 'group_percent'), # Probability of Precipitation
        'wwS': ('posp', 'percent', 'group_percent'), # Probability of Solid Precipitation
        #'wwPd': ('pop_24h', 'percent', 'group_percent'), # Probability of Precipitation
        'wwT': ('pot', 'percent', 'group_percent'), # Probability of Thunderstorm
        #'wwTd': ('pot_24h', 'percent', 'group_percent'), # Probability of Thunderstorm
        'wwZ': ('pod', 'percent', 'group_percent'), # Probability of Drizzle
        'R101':  ('pop_001', 'percent', 'group_percent'),  # Probability of Precipitation >0.1 / 1h
        'R102':  ('pop_002', 'percent', 'group_percent'),  # Probability of Precipitation >0.2 / 1h
        'R103':  ('pop_003', 'percent', 'group_percent'),  # Probability of Precipitation >0.3 / 1h
        'R105':  ('pop_004', 'percent', 'group_percent'),  # Probability of Precipitation >0.5 / 1h
        'R107':  ('pop_007', 'percent', 'group_percent'),  # Probability of Precipitation >0.7 / 1h
        'R110':  ('pop_010', 'percent', 'group_percent'),  # Probability of Precipitation >1.0 / 1h
        'R120':  ('pop_020', 'percent', 'group_percent'),  # Probability of Precipitation >2.0 / 1h
        'R130':  ('pop_030', 'percent', 'group_percent'),  # Probability of Precipitation >3.0 / 1h
        'R150':  ('pop_050', 'percent', 'group_percent'),  # Probability of Precipitation >5.0 / 1h
        'RR1o1': ('pop_100', 'percent', 'group_percent'),  # Probability of Precipitation >10.0 / 1h
        'RR1w1': ('pop_150', 'percent', 'group_percent'),  # Probability of Precipitation >15.0 / 1h
        'RR1u1': ('pop_250', 'percent', 'group_percent'),  # Probability of Precipitation >25.0 / 1h
        #'Rd00':  ('pop_000_24h', 'percent', 'group_percent'), # Probability of Precipitation >0.0 / 24h
        #'Rd02':  ('pop_002_24h', 'percent', 'group_percent'), # Probability of Precipitation >0.2 / 24h
        #'Rd10':  ('pop_010_24h', 'percent', 'group_percent'), # Probability of Precipitation >1.0 / 24h
        #'Rd50':  ('pop_050_24h', 'percent', 'group_percent'), # Probability of Precipitation >5.0 / 24h
        'DRR1':  ('rainDur', 'second', 'group_deltatime'),
        'SunD1':  ('sunshineDur', 'second', 'group_deltatime')
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


    def get_hourly_obs(self):
        return MOSMIXthread.HOURLYOBS


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
        self.source_id = self.config.get('source_id', 'dwd-mosmix')
        self.interval_get = weeutil.weeutil.to_int(self.config.get('interval_get', 300))
        self.interval_push = weeutil.weeutil.to_int(self.config.get('interval_push', 30))
        self.expired = weeutil.weeutil.to_int(self.config.get('expired', 600))
        self.timezone = self.config.get('timezone', 'Europe/Berlin')
        self.icon_path_belchertown = self.config.get('icon_path_belchertown', '')
        self.hourly_obs = self.get_hourly_obs()
        self.config_dict = thread_dict.get('config_dict')
        self.engine = thread_dict.get('engine')
        self.lat = weeutil.weeutil.to_float(self.config.get('latitude'))
        self.lon = weeutil.weeutil.to_float(self.config.get('longitude'))
        self.alt = weeutil.weeutil.to_float(self.config.get('altitude'))
        self.data_temp = dict()
        self.data_result = dict()
        self.last_get_ts = 0

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

        weewx.units.obs_group_dict.setdefault('dateTime','group_time')
        weewx.units.obs_group_dict.setdefault('generated','group_time')
        weewx.units.obs_group_dict.setdefault('age','group_deltatime')
        weewx.units.obs_group_dict.setdefault('day','group_count')
        weewx.units.obs_group_dict.setdefault('expired','group_count')
        weewx.units.obs_group_dict.setdefault('weathercode','group_count')
        weewx.units.obs_group_dict.setdefault('weathercodeKey','group_count')
        for opsapi, obsweewx in self.hourly_obs.items():
            weewx.units.obs_group_dict.setdefault(obsweewx[0],obsweewx[2])

        dbout_dict = self.config.get('db_out', configobj.ConfigObj())
        if weeutil.weeutil.to_bool(dbout_dict.get('enable', False)):
            data_binding_name = dbout_dict.get('data_binding')
            if data_binding_name is None:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': init data_binding is not configured!" % (self.name))
                return
            # open the data store
            self.dbm = self.engine.db_binder.get_manager(data_binding=data_binding_name, initialize=True)
            # confirm db schema
            dbcols = self.dbm.connection.columnsOf(self.dbm.table_name)
            dbm_dict = weewx.manager.get_manager_dict_from_config(self.config_dict, data_binding_name)
            memcols = [x[0] for x in dbm_dict['schema']]
            if dbcols != memcols:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': init store schema mismatch: %s != %s" % (self.name, dbcols, memcols))
                return
        elif self.log_success or self.debug > 0:
            loginf("thread '%s': init db_out is diabled. Enable it in the [db_out] section of station %s" %(self.name, self.station))

        if self.log_success or self.debug > 0:
            loginf("thread '%s': init finished" % self.name)


    def getDataInterval(self, data_interval_calc, unitsystem, lat, lon, alt, lang, debug=0, log_success=False, log_failure=True):
        """ preprocess MOSMIX interval forecast data """

        data_temp = dict()

        # temp using for is_night
        night_dict = dict()
        night_dict['latitude'] = lat
        night_dict['longitude'] = lon
        night_dict['altitude'] = alt

        try:
            for interval, intervaldata in data_interval_calc.items():
                data_temp[interval] = dict()
                col = 0
                for ts, tsdata in intervaldata.items():
                    col += 1
                    data_temp[interval][str(col)] = dict()
                    data_temp[interval][str(col)]['timestamp'] = (ts, 'unix_epoch', 'group_time')
                    data_temp[interval][str(col)]['timestampISO'] = (get_isodate_from_timestamp(ts, self.timezone), None, None)
                    for apiobs, obsdata in tsdata.items():
                        weewxobs = self.hourly_obs.get(apiobs)
                        #logdbg("thread '%s': getDataInterval apiobs %s" % (self.name, apiobs))
                        #logdbg("thread '%s': getDataInterval weewxobs %s" % (self.name, weewxobs))
                        #logdbg("thread '%s': getDataInterval obsdata %s" % (self.name, str(obsdata)))
                        if weewxobs is None:
                            if log_failure or debug > 0:
                                logerr("thread '%s': getDataInterval unknown api obs '%s'" % (self.name, apiobs))
                            continue
                        if weewxobs[2] is None:
                            vt = obsdata['val']
                        elif interval in ('1h','db'):
                            vt = obsdata['val']
                            vt = to_weewx(self.name, vt, unitsystem, debug=debug, log_success=log_success, log_failure=log_failure)
                            #logdbg("thread '%s': getDataInterval vt %s" % (self.name, str(vt)))
                        else:
                            vt_min = obsdata['min']
                            vt_min = to_weewx(self.name, vt_min, unitsystem, debug=debug, log_success=log_success, log_failure=log_failure)

                            vt_avg = obsdata['avg']
                            vt_avg = to_weewx(self.name, vt_avg, unitsystem, debug=debug, log_success=log_success, log_failure=log_failure)

                            vt_max = obsdata['max']
                            vt_max = to_weewx(self.name, vt_max, unitsystem, debug=debug, log_success=log_success, log_failure=log_failure)

                            vt_sum = obsdata['sum']
                            vt_sum = to_weewx(self.name, vt_sum, unitsystem, debug=debug, log_success=log_success, log_failure=log_failure)

                            #logdbg("thread '%s': getDataInterval vt_min %s" % (self.name, str(vt_min)))
                            #logdbg("thread '%s': getDataInterval vt_avg %s" % (self.name, str(vt_avg)))
                            #logdbg("thread '%s': getDataInterval vt_max %s" % (self.name, str(vt_max)))
                            #logdbg("thread '%s': getDataInterval vt_sum %s" % (self.name, str(vt_sum)))

                        # Filter
                        # 'ww': ('weathercode', 'count', 'group_count'),
                        # 'ww3': ('weathercode_3h', 'count', 'group_count'),
                        # 'TTT': ('outTemp', 'degree_C', 'group_temperature'),
                        # 'Td': ('dewpoint', 'degree_C', 'group_temperature'),
                        # 'PPPP': ('barometer', 'hPa', 'group_pressure'),
                        # 'FF': ('windSpeed', 'km_per_hour', 'group_speed'),
                        # 'FX1': ('windGust', 'km_per_hour', 'group_speed'),
                        # 'DD': ('windDir', 'degree_compass', 'group_direction'),
                        # 'VV': ('visibility', 'meter', 'group_distance'),
                        # 'Neff': ('cloudcoverEffective', 'percent', 'group_percent'),
                        # 'N': ('cloudcoverTotal', 'percent', 'group_percent'),
                        # 'RR1c': ('precip', 'mm', 'group_rain'),
                        # 'RR3c': ('precip_3h', 'mm', 'group_rain'),
                        # 'RRdc': ('precip_24h', 'mm', 'group_rain'),
                        # 'RRL1c': ('rain', 'mm', 'group_rain'),
                        # 'RRS1c': ('snowRain', 'mm', 'group_rain'),
                        # 'RRS3c': ('snowRain_3h', 'mm', 'group_rain'),
                        # 'wwD': ('pos', 'percent', 'group_percent'), # Probability of Snow
                        # 'wwF': ('pofr', 'percent', 'group_percent'), # Probability of Freezing Rain
                        # 'wwL': ('por', 'percent', 'group_percent'), # Probability of Rain
                        # 'wwP': ('pop', 'percent', 'group_percent'), # Probability of Precipitation
                        # 'wwS': ('posp', 'percent', 'group_percent'), # Probability of Solid Precipitation
                        # 'wwPd': ('pop_24h', 'percent', 'group_percent'), # Probability of Precipitation
                        # 'wwT': ('pot', 'percent', 'group_percent'), # Probability of Thunderstorm
                        # 'wwTd': ('pot_24h', 'percent', 'group_percent'), # Probability of Thunderstorm
                        # 'wwZ': ('pod', 'percent', 'group_percent'), # Probability of Drizzle
                        # 'R101':  ('pop_001', 'percent', 'group_percent'),  # Probability of Precipitation >0.1 / 1h
                        # 'R102':  ('pop_002', 'percent', 'group_percent'),  # Probability of Precipitation >0.2 / 1h
                        # 'R103':  ('pop_003', 'percent', 'group_percent'),  # Probability of Precipitation >0.3 / 1h
                        # 'R105':  ('pop_004', 'percent', 'group_percent'),  # Probability of Precipitation >0.5 / 1h
                        # 'R107':  ('pop_007', 'percent', 'group_percent'),  # Probability of Precipitation >0.7 / 1h
                        # 'R110':  ('pop_010', 'percent', 'group_percent'),  # Probability of Precipitation >1.0 / 1h
                        # 'R120':  ('pop_020', 'percent', 'group_percent'),  # Probability of Precipitation >2.0 / 1h
                        # 'R130':  ('pop_030', 'percent', 'group_percent'),  # Probability of Precipitation >3.0 / 1h
                        # 'R150':  ('pop_050', 'percent', 'group_percent'),  # Probability of Precipitation >5.0 / 1h
                        # 'RR1o1': ('pop_100', 'percent', 'group_percent'),  # Probability of Precipitation >10.0 / 1h
                        # 'RR1w1': ('pop_150', 'percent', 'group_percent'),  # Probability of Precipitation >15.0 / 1h
                        # 'RR1u1': ('pop_250', 'percent', 'group_percent'),  # Probability of Precipitation >25.0 / 1h
                        # 'Rd00':  ('pop_000_24h', 'percent', 'group_percent'), # Probability of Precipitation >0.0 / 24h
                        # 'Rd02':  ('pop_002_24h', 'percent', 'group_percent'), # Probability of Precipitation >0.2 / 24h
                        # 'Rd10':  ('pop_010_24h', 'percent', 'group_percent'), # Probability of Precipitation >1.0 / 24h
                        # 'Rd50':  ('pop_050_24h', 'percent', 'group_percent'), # Probability of Precipitation >5.0 / 24h
                        # 'SunD1':  ('sunshineDur', 'second', 'group_deltatime')



                        # TODO check if x_1h_x exists
                        # TODO check if x_3h_x exists
                        # TODO check if x_24h_x exists



                        if weewxobs[2] in ('group_temperature', 'group_speed'):
                            if interval in ('1h','db'):
                                data_temp[interval][str(col)][weewxobs[0]] = vt
                            else:
                                data_temp[interval][str(col)][weewxobs[0]+'_min'] = vt_min
                                data_temp[interval][str(col)][weewxobs[0]+'_avg'] = vt_avg
                                data_temp[interval][str(col)][weewxobs[0]+'_max'] = vt_max
                        elif weewxobs[2] in ('group_pressure', 'group_direction'):
                            if interval in ('1h','db'):
                                data_temp[interval][str(col)][weewxobs[0]] = vt
                            else:
                                data_temp[interval][str(col)][weewxobs[0]] = vt_avg
                        elif weewxobs[2] in ('group_percent'):
                            if interval in ('1h','db'):
                                data_temp[interval][str(col)][weewxobs[0]] = vt if vt[0] is not None else (0.0, vt[1], vt[2])
                            else:
                                data_temp[interval][str(col)][weewxobs[0]] = vt_max if vt_max[0] is not None else (0.0, vt_max[1], vt_max[2])
                        elif weewxobs[2] in ('group_count'):
                            if interval in ('1h','db'):
                                data_temp[interval][str(col)][weewxobs[0]] = vt
                            else:
                                data_temp[interval][str(col)][weewxobs[0]] = vt_max
                        elif weewxobs[2] in ('group_distance'):
                            if interval in ('1h','db'):
                                data_temp[interval][str(col)][weewxobs[0]] = vt
                            else:
                                data_temp[interval][str(col)][weewxobs[0]] = vt_min
                        elif weewxobs[2] in ('group_rain', 'group_deltatime'):
                            if interval in ('1h','db'):
                                data_temp[interval][str(col)][weewxobs[0]] = vt if vt[0] is not None else (0.0, vt[1], vt[2])
                            else:
                                data_temp[interval][str(col)][weewxobs[0]] = vt_sum if vt_sum[0] is not None else (0.0, vt_sum[1], vt_sum[2])

                    # outHumidity
                    if interval in ('1h','db'):
                        t = data_temp[interval][str(col)].get('outTemp')[0]
                        td = data_temp[interval][str(col)].get('dewpoint')[0]
                    else:
                        t = data_temp[interval][str(col)].get('outTemp_avg')[0]
                        td = data_temp[interval][str(col)].get('dewpoint_avg')[0]
                    h = get_humidity(self.name, t, td, debug=debug, log_success=log_success, log_failure=log_failure)
                    data_temp[interval][str(col)]['outHumidity'] = (weeutil.weeutil.to_int(h), 'percent', 'group_percent')

                    # compass
                    wdir = data_temp[interval][str(col)].get('windDir')
                    if wdir is not None:
                        data_temp[interval][str(col)]['compass'] = (compass(wdir[0], lang), None, None)
                    else:
                        data_temp[interval][str(col)]['compass'] = ('', None, None)

                    # is night?
                    night_dict['dateTime'] = (ts, 'unix_epoch', 'group_time')
                    if interval in ('1h','db'):
                        night_dict['outTemp'] = data_temp[interval][str(col)].get('outTemp')
                        night_dict['barometer'] = data_temp[interval][str(col)].get('barometer')
                        night = is_night(self.name, night_dict, debug=debug, log_success=log_success, log_failure=log_failure)
                    elif interval == '3h':
                        night_dict['outTemp'] = data_temp[interval][str(col)].get('outTemp_max')
                        night_dict['barometer'] = data_temp[interval][str(col)].get('barometer')
                        night = is_night(self.name, night_dict, debug=debug, log_success=log_success, log_failure=log_failure)
                    else:
                        night = 0
                    data_temp[interval][str(col)]['day'] = (0 if night else 1, 'count', 'group_count')

                    # weathertext and weathericon
                    code = data_temp[interval][str(col)].get('weathercode')[0]
                    aeriscode = self.get_aeriscode(code)
                    data_temp[interval][str(col)]['weathercodeAeris'] = (aeriscode, None, None)
                    # return (text_de, text_en, icon, weathercode)
                    wxdata = self.get_icon_and_text(aeriscode, night=night, debug=debug, log_success=log_success, log_failure=log_failure, weathertext_en=None)
                    data_temp[interval][str(col)]['weathercodeKey'] = (weeutil.weeutil.to_int(wxdata[3]), 'count', 'group_count')
                    data_temp[interval][str(col)]['weathericon'] = (wxdata[2], None, None)
                    data_temp[interval][str(col)]['weathertext'] = dict()
                    data_temp[interval][str(col)]['weathertext']['de'] = (wxdata[0], None, None)
                    data_temp[interval][str(col)]['weathertext']['en'] = (wxdata[1], None, None)
        except Exception as e:
            exception_output(self.name, e)
            return None
        return data_temp


    def getDataIntervalCalc(self, apidata, debug=0, log_success=False, log_failure=True):
        """ preprocess MOSMIX api forecast data """

        data_temp = dict()
        timestamps = apidata['hourly'].get('time')
        timestamp_len = len(timestamps)

        # current timestamp
        current_time = datetime.datetime.now(pytz.utc)
        current_time_ts = weeutil.weeutil.to_int(current_time.timestamp())
        current_time_berlin = current_time.astimezone(pytz.timezone('Europe/Berlin'))
        utcoffset = weeutil.weeutil.to_int(current_time_berlin.utcoffset().total_seconds())

        # start with the next full hour timestamp
        next_hour = current_time.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
        next_hour_ts = weeutil.weeutil.to_int(next_hour.timestamp())

        # or start with the current full hour timestamp
        current_hour = current_time.replace(minute=0, second=0, microsecond=0)
        current_hour_ts = weeutil.weeutil.to_int(current_hour.timestamp())

        # next day 00:00 timestamp
        next_day = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
        next_day_ts = weeutil.weeutil.to_int(next_day.timestamp()) - utcoffset

        # max 8 days 
        end_day = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=8)
        end_day_ts = weeutil.weeutil.to_int(end_day.timestamp()) - utcoffset

        # diff hours from start (next hour) to 24h
        today_remaining_hours = weeutil.weeutil.to_int((next_day_ts + utcoffset - next_hour_ts) / 3600)

        if debug > 2:
            logdbg("thread '%s': current_time_ts %d" % (self.name, current_time_ts))
            logdbg("thread '%s': current_time_ts %s" % (self.name, current_time.isoformat(sep="T", timespec="seconds")))
            logdbg("thread '%s': current_time_ts %s" % (self.name, get_isodate_from_timestamp(current_time_ts)))

            logdbg("thread '%s': current_hour_ts %d" % (self.name, current_hour_ts))
            logdbg("thread '%s': current_hour_ts %s" % (self.name, current_hour.isoformat(sep="T", timespec="seconds")))
            logdbg("thread '%s': current_hour_ts %s" % (self.name, get_isodate_from_timestamp(current_hour_ts)))

            logdbg("thread '%s':    next_hour_ts %d" % (self.name, next_hour_ts))
            logdbg("thread '%s':    next_hour_ts %s" % (self.name, next_hour.isoformat(sep="T", timespec="seconds")))
            logdbg("thread '%s':    next_hour_ts %s" % (self.name, get_isodate_from_timestamp(next_hour_ts)))

            logdbg("thread '%s':     next_day_ts %d" % (self.name, next_day_ts))
            logdbg("thread '%s':     next_day_ts %s" % (self.name, next_day.isoformat(sep="T", timespec="seconds")))
            logdbg("thread '%s':     next_day_ts %s" % (self.name, get_isodate_from_timestamp(next_day_ts)))

            logdbg("thread '%s':      end_day_ts %d" % (self.name, end_day_ts))
            logdbg("thread '%s':      end_day_ts %s" % (self.name, end_day.isoformat(sep="T", timespec="seconds")))
            logdbg("thread '%s':      end_day_ts %s" % (self.name, get_isodate_from_timestamp(end_day_ts)))

            logdbg("thread '%s': today_remaining_hours: %d" % (self.name, today_remaining_hours))
            logdbg("thread '%s':       timezone offset: %d" % (self.name, utcoffset))

        # 24h interval
        data_temp['24h'] = dict()
        interval_start = next_hour_ts
        if interval_start < next_day_ts:
            hours = today_remaining_hours
        else:
            hours = 24
        ii = 0
        try:
            for i in range(len(timestamps)):
                if timestamps[i] >= interval_start:
                    data_temp['24h'][timestamps[i]] = dict()
                    for obsapi, obsweewx in self.hourly_obs.items():
                        data_temp['24h'][timestamps[i]][obsapi] = dict()
                        obslist = apidata['hourly'].get(obsapi)
                        if obslist is None or len(obslist) != timestamp_len:
                            if log_failure or debug > 0:
                                if obslist is None:
                                    logerr("thread '%s': getDataIntervalCalc None for ts %s obs %s - %s" % (self.name, str(timestamps[i]), obsapi, obsweewx[0]))
                                elif len(obslist) != timestamp_len:
                                    logerr("thread '%s': getDataIntervalCalc obs %s number of values not equal to number of timestamps %d != %d" % (self.name, obsapi, len(obslist), timestamp_len))
                            data_temp['24h'][timestamps[i]][obsapi]['min'] = (None, obsweewx[1], obsweewx[2])
                            data_temp['24h'][timestamps[i]][obsapi]['avg'] = (None, obsweewx[1], obsweewx[2])
                            data_temp['24h'][timestamps[i]][obsapi]['max'] = (None, obsweewx[1], obsweewx[2])
                            data_temp['24h'][timestamps[i]][obsapi]['sum'] = (None, obsweewx[1], obsweewx[2])
                            data_temp['24h'][timestamps[i]][obsapi]['val'] = (None, obsweewx[1], obsweewx[2])
                            continue
                        interval_values = obslist[i:i+hours]
                        try:
                            data_temp['24h'][timestamps[i]][obsapi]['min'] = (min(x for x in interval_values if x is not None), obsweewx[1], obsweewx[2])
                        except (ValueError, TypeError, ArithmeticError):
                            data_temp['24h'][timestamps[i]][obsapi]['min'] = (None, obsweewx[1], obsweewx[2])
                            pass
                        try:
                            data_temp['24h'][timestamps[i]][obsapi]['avg'] = (mean(x for x in interval_values if x is not None), obsweewx[1], obsweewx[2])
                        except (ValueError, TypeError, ArithmeticError):
                            data_temp['24h'][timestamps[i]][obsapi]['avg'] = (None, obsweewx[1], obsweewx[2])
                            pass
                        try:
                            data_temp['24h'][timestamps[i]][obsapi]['max'] = (max(x for x in interval_values if x is not None), obsweewx[1], obsweewx[2])
                        except (ValueError, TypeError, ArithmeticError):
                            data_temp['24h'][timestamps[i]][obsapi]['max'] = (None, obsweewx[1], obsweewx[2])
                            pass
                        try:
                            data_temp['24h'][timestamps[i]][obsapi]['sum'] = (sum(x for x in interval_values if x is not None), obsweewx[1], obsweewx[2])
                        except (ValueError, TypeError, ArithmeticError):
                            data_temp['24h'][timestamps[i]][obsapi]['sum'] = (None, obsweewx[1], obsweewx[2])
                            pass

                    if hours < 24:
                        interval_start = next_day_ts
                        hours = 24
                    else:
                        interval_start += (hours * 3600)
                    #logdbg("thread '%s': 24h %s" % (self.name, json.dumps(data_temp['24h'][timestamps[i]])))
                    ii += 1
                    if ii >= 8 or interval_start > end_day_ts:
                        break
        except Exception as e:
            exception_output(self.name, e)
            return None

        # 3h interval
        data_temp['3h'] = dict()
        interval_start = next_hour_ts
        ii = 0
        try:
            for i in range(len(timestamps)):
                if timestamps[i] >= interval_start:
                    data_temp['3h'][timestamps[i]] = dict()
                    if timestamps[i] + (3 * 3600) > end_day_ts:
                        hours = weeutil.weeutil.to_int(end_day_ts - timestamps[i] / 3600)
                        if hours < 1:
                            break
                    else:
                        hours = 3
                    for obsapi, obsweewx in self.hourly_obs.items():
                        data_temp['3h'][timestamps[i]][obsapi] = dict()
                        obslist = apidata['hourly'].get(obsapi)
                        if obslist is None or len(obslist) != timestamp_len:
                            if log_failure or debug > 0:
                                if obslist is None:
                                    logerr("thread '%s': getDataIntervalCalc None for ts %s obs %s - %s" % (self.name, str(timestamps[i]), obsapi, obsweewx[0]))
                                elif len(obslist) != timestamp_len:
                                    logerr("thread '%s': getDataIntervalCalc number of values not equal to number of timestamps %d != %d" % (self.name, len(obslist), timestamp_len))
                            data_temp['3h'][timestamps[i]][obsapi]['min'] = (None, obsweewx[1], obsweewx[2])
                            data_temp['3h'][timestamps[i]][obsapi]['avg'] = (None, obsweewx[1], obsweewx[2])
                            data_temp['3h'][timestamps[i]][obsapi]['max'] = (None, obsweewx[1], obsweewx[2])
                            data_temp['3h'][timestamps[i]][obsapi]['sum'] = (None, obsweewx[1], obsweewx[2])
                            data_temp['3h'][timestamps[i]][obsapi]['val'] = (None, obsweewx[1], obsweewx[2])
                            continue
                        interval_values = obslist[i:i+hours]
                        # if obsapi == 'TTT':
                            # logdbg("thread '%s': 3h %s -> %s" % (self.name, obsapi, json.dumps(interval_values)))
                        try:
                            data_temp['3h'][timestamps[i]][obsapi]['min'] = (min(x for x in interval_values if x is not None), obsweewx[1], obsweewx[2])
                        except (ValueError, TypeError, ArithmeticError):
                            data_temp['3h'][timestamps[i]][obsapi]['min'] = (None, obsweewx[1], obsweewx[2])
                            pass
                        try:
                            data_temp['3h'][timestamps[i]][obsapi]['avg'] = (mean(x for x in interval_values if x is not None), obsweewx[1], obsweewx[2])
                        except (ValueError, TypeError, ArithmeticError):
                            data_temp['3h'][timestamps[i]][obsapi]['avg'] = (None, obsweewx[1], obsweewx[2])
                            pass
                        try:
                            data_temp['3h'][timestamps[i]][obsapi]['max'] = (max(x for x in interval_values if x is not None), obsweewx[1], obsweewx[2])
                        except (ValueError, TypeError, ArithmeticError):
                            data_temp['3h'][timestamps[i]][obsapi]['max'] = (None, obsweewx[1], obsweewx[2])
                            pass
                        try:
                            data_temp['3h'][timestamps[i]][obsapi]['sum'] = (sum(x for x in interval_values if x is not None), obsweewx[1], obsweewx[2])
                        except (ValueError, TypeError, ArithmeticError):
                            data_temp['3h'][timestamps[i]][obsapi]['sum'] = (None, obsweewx[1], obsweewx[2])
                            pass

                        # if obsapi == 'TTT':
                            # logdbg("thread '%s': 3h min %s -> %s" % (self.name, obsapi, json.dumps(data_temp['3h'][timestamps[i]][obsapi]['min'])))
                            # logdbg("thread '%s': 3h avg %s -> %s" % (self.name, obsapi, json.dumps(data_temp['3h'][timestamps[i]][obsapi]['avg'])))
                            # logdbg("thread '%s': 3h max %s -> %s" % (self.name, obsapi, json.dumps(data_temp['3h'][timestamps[i]][obsapi]['max'])))
                            # logdbg("thread '%s': 3h sum %s -> %s" % (self.name, obsapi, json.dumps(data_temp['3h'][timestamps[i]][obsapi]['sum'])))


                    interval_start += (3 * 3600)
                    ii += 1
                    #logdbg("thread '%s': 3h hours %s" % (self.name, str(hours)))
                    #logdbg("thread '%s': 3h %s" % (self.name, json.dumps(data_temp['3h'][timestamps[i]])))
                    if ii >= 8 or interval_start > end_day_ts:
                        break
        except Exception as e:
            exception_output(self.name, e)
            return None

        # 1h interval
        data_temp['1h'] = dict()
        interval_start = next_hour_ts
        ii = 0
        try:
            for i in range(len(timestamps)):
                if timestamps[i] > end_day_ts:
                    break
                if timestamps[i] >= interval_start:
                    data_temp['1h'][timestamps[i]] = dict()
                    for obsapi, obsweewx in self.hourly_obs.items():
                        data_temp['1h'][timestamps[i]][obsapi] = dict()
                        obslist = apidata['hourly'].get(obsapi)
                        if obslist is None or len(obslist) != timestamp_len:
                            if log_failure or debug > 0:
                                if obslist is None:
                                    logerr("thread '%s': getDataIntervalCalc None for ts %s obs %s - %s" % (self.name, str(timestamps[i]), obsapi, obsweewx[0]))
                                elif len(obslist) != timestamp_len:
                                    logerr("thread '%s': getDataIntervalCalc number of values not equal to number of timestamps %d != %d" % (self.name, len(obslist), timestamp_len))
                            data_temp['1h'][timestamps[i]][obsapi]['val'] = (None, obsweewx[1], obsweewx[2])
                            continue
                        data_temp['1h'][timestamps[i]][obsapi]['val'] = (obslist[i], obsweewx[1], obsweewx[2])
                    #interval_start += 3600
                    ii += 1
                    #logdbg("thread '%s': 1h %s" % (self.name, json.dumps(data_temp['1h'][timestamps[i]])))
                    if ii >= 16 or interval_start > end_day_ts:
                        break
        except Exception as e:
            exception_output(self.name, e)
            return None

        # Database
        data_temp['db'] = dict()
        interval_start = next_hour_ts
        try:
            for i in range(len(timestamps)):
                if timestamps[i] > end_day_ts:
                    break
                if timestamps[i] >= interval_start:
                    data_temp['db'][timestamps[i]] = dict()
                    for obsapi, obsweewx in self.hourly_obs.items():
                        data_temp['db'][timestamps[i]][obsapi] = dict()
                        obslist = apidata['hourly'].get(obsapi)
                        if obslist is None or len(obslist) != timestamp_len:
                            if log_failure or debug > 0:
                                if obslist is None:
                                    logerr("thread '%s': getDataIntervalCalc None for ts %s obs %s - %s" % (self.name, str(timestamps[i]), obsapi, obsweewx[0]))
                                elif len(obslist) != timestamp_len:
                                    logerr("thread '%s': getDataIntervalCalc number of values not equal to number of timestamps %d != %d" % (self.name, len(obslist), timestamp_len))
                            data_temp['db'][timestamps[i]][obsapi]['val'] = (None, obsweewx[1], obsweewx[2])
                            continue
                        data_temp['db'][timestamps[i]][obsapi]['val'] = (obslist[i], obsweewx[1], obsweewx[2])
                    #interval_start += 3600
        except Exception as e:
            exception_output(self.name, e)
            return None
        return data_temp


    def merge_mosmixl_mosmixs(self, mosl, moss):
        mosmix = dict()
        mosmix['station'] = mosl.get('station', moss.get('station'))
        mosmix['usUnits'] = mosl.get('usUnits', moss.get('usUnits'))
        
        try:
            hourly_l = mosl.get('hourly', dict())
            hourly_s = moss.get('hourly', dict())
            timestamps_l = hourly_l.get('time', list())
            timestamps_s = hourly_s.get('time', list())

            mosmix['hourly'] = dict()
            mosmix['hourly']['time'] = list()

            #TODO: check if s or l dict is none

            idx_s = 0
            for ts_s in timestamps_s:
                mosmix['hourly']['time'].append(ts_s)
                idx_l = 0
                ts_found = None
                for ts_l in timestamps_l:
                    if ts_l == ts_s:
                        ts_found = 1
                        for obsapi, obsweewx in self.hourly_obs.items():
                            obslist_l = hourly_l.get(obsapi)
                            obslist_s = hourly_s.get(obsapi)
                            val = None
                            if obslist_s is not None:
                                if 0 <= idx_s < len(obslist_s):
                                    val = obslist_s[idx_s]
                            if val is None:
                                if obslist_l is not None:
                                    if 0 <= idx_l < len(obslist_l):
                                        val = obslist_l[idx_l]
                            if mosmix['hourly'].get(obsapi) is None:
                                mosmix['hourly'][obsapi] = list()
                            mosmix['hourly'][obsapi].append(val)
                        break
                    idx_l += 1
                if ts_found is None:
                    for obsapi, obsweewx in self.hourly_obs.items():
                        obslist_s = hourly_s.get(obsapi)
                        val = None
                        if obslist_s is not None:
                            if 0 <= idx_s < len(obslist_s):
                                val = obslist_s[idx_s]
                        if mosmix['hourly'].get(obsapi) is None:
                            mosmix['hourly'][obsapi] = list()
                        mosmix['hourly'][obsapi].append(val)
                idx_s += 1
        except Exception as e:
            exception_output(self.name, e)
            return mosl
        return mosmix


    def get_data_api(self):
        """ download and process DWD MOSMIX forecast data """

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

        # Test MOSMIX_S merged over MOSMIX_L

        mosl_dict = dict()
        moss_dict = dict()
        apidata = dict()
        for mosmix in ('l', 's'):
            # Params
            params = '?station=%s&type=%s' % (str(self.station).lower(), mosmix.lower())

            url = baseurl + params

            if debug > 2:
                logdbg("thread '%s': get_data_api url %s" % (self.name, url))

            attempts = 0
            try:
                while attempts <= attempts_max:
                    attempts += 1
                    response, code = request_api(self.name, url,
                                                debug = self.debug,
                                                log_success = log_success,
                                                log_failure = log_failure)
                    if response is not None:
                        if mosmix == 'l':
                            mosl_dict = response
                        else:
                            moss_dict = response
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
                mosl_dict = None
                moss_dict = None
                return False

        if debug > 2:
            logdbg("thread '%s': get_data_api api mosmix_s result %s" % (self.name, json.dumps(moss_dict)))
            logdbg("thread '%s': get_data_api api mosmix_l result %s" % (self.name, json.dumps(mosl_dict)))

        apidata = self.merge_mosmixl_mosmixs(mosl_dict, moss_dict)

        if debug > 2:
            logdbg("thread '%s': get_data_api api merged s/l result %s" % (self.name, json.dumps(apidata)))

        # check results

        # check unit system
        if unitsystem is None and apidata.get('usUnits') is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api did not send unit system and it's not configured in section [api_in]" % (self.name))
            mosl_dict = None
            moss_dict = None
            apidata = None
            return False

        station = apidata.get('station')
        if station is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api no station data" % self.name)
            mosl_dict = None
            moss_dict = None
            apidata = None
            return False

        if apidata.get('hourly') is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api no hourly data" % self.name)
            mosl_dict = None
            moss_dict = None
            apidata = None
            return False

        # hourly timestamps
        timestamps = apidata['hourly'].get('time')
        if timestamps is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api no hourly time periods data" % self.name)
            mosl_dict = None
            moss_dict = None
            apidata = None
            return False

        if not isinstance(timestamps, list):
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api hourly time periods data not as list" % self.name)
            mosl_dict = None
            moss_dict = None
            apidata = None
            return False

        if len(timestamps) == 0:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api hourly time periods without data" % self.name)
            mosl_dict = None
            moss_dict = None
            apidata = None
            return False

        try:
            actts = weeutil.weeutil.to_int(time.time())
            self.data_temp['dateTime'] = weeutil.weeutil.to_int(actts)
            self.data_temp['dateTimeISO'] = get_isodate_from_timestamp(weeutil.weeutil.to_int(actts), self.timezone)
            source = mosl_dict.get('source')
            self.data_temp[source] = dict()
            self.data_temp[source]['generated'] = weeutil.weeutil.to_int(mosl_dict.get('generated'))
            self.data_temp[source]['generatedISO'] = mosl_dict.get('generatedISO')
            self.data_temp[source]['sourceUrl'] = mosl_dict.get('sourceUrl')
            source = moss_dict.get('source')
            self.data_temp[source] = dict()
            self.data_temp[source]['generated'] = weeutil.weeutil.to_int(moss_dict.get('generated'))
            self.data_temp[source]['generatedISO'] = moss_dict.get('generatedISO')
            self.data_temp[source]['sourceUrl'] = moss_dict.get('sourceUrl')
            self.data_temp['generated'] = max(weeutil.weeutil.to_int(mosl_dict.get('generated')), weeutil.weeutil.to_int(moss_dict.get('generated')))
            self.data_temp['generatedISO'] = get_isodate_from_timestamp(self.data_temp['generated'])
            lat = station.get('latitude', self.lat)
            lon = station.get('longitude', self.lon)
            alt = station.get('elevation', self.alt)
            self.data_temp['latitude'] = lat
            self.data_temp['longitude'] = lon
            self.data_temp['altitude'] = alt
            self.data_temp['wmo_code'] = station.get('wmo_code')
            self.data_temp['sourceProvider'] = PROVIDER[self.source_id][0]
            self.data_temp['sourceProviderLink'] = PROVIDER[self.source_id][1]
            self.data_temp['sourceProviderHTML'] = HTMLTMPL % (PROVIDER[self.source_id][1], PROVIDER[self.source_id][0], PROVIDER[self.source_id][2])
            self.data_temp['sourceModul'] = self.name
            self.data_temp['sourceId'] = self.source_id
            self.data_temp['lang'] = lang
            self.data_temp['usUnits'] = unitsystem
            self.data_temp['1h'] = dict()
            self.data_temp['3h'] = dict()
            self.data_temp['24h'] = dict()
            self.data_temp['db'] = dict()

            data_interval_calc = self.getDataIntervalCalc(apidata, debug=debug, log_success=log_success, log_failure=log_failure)
            if data_interval_calc is None:
                if log_failure or debug > 0:
                    logerr("thread '%s': get_data_api getDataIntervalCalc returned None" % self.name)
                self.data_temp = dict()
                mosl_dict = None
                moss_dict = None
                apidata = None
                return False

            lat = (lat, 'degree_compass', 'group_coordinate')
            lon = (lon, 'degree_compass', 'group_coordinate')
            alt = (alt, 'meter', 'group_altitude')
            data_interval = self.getDataInterval(data_interval_calc, unitsystem, lat, lon, alt, lang, debug=debug, log_success=log_success, log_failure=log_failure)
            if data_interval is None:
                if log_failure or debug > 0:
                    logerr("thread '%s': get_data_api getIntervalData returned None" % self.name)
                self.data_temp = dict()
                mosl_dict = None
                moss_dict = None
                apidata = None
                return False

            self.data_temp['1h'] = data_interval['1h']
            self.data_temp['3h'] = data_interval['3h']
            self.data_temp['24h'] = data_interval['24h']
            self.data_temp['db'] = data_interval['db']
        except Exception as e:
            exception_output(self.name, e)
            self.data_temp = dict()
            mosl_dict = None
            moss_dict = None
            apidata = None
            return False

        self.last_get_ts = weeutil.weeutil.to_int(time.time())
        return (len(self.data_temp) > 0)


# ============================================================================
#
# Class AERISthread
#
# ============================================================================

class AERISthread(AbstractThread):

    # API: https://www.aerisweather.com/support/docs/api/reference/endpoints/forecasts/#response
    # Evapotranspiration/UV-Index:
    # Attention, no capital letters for WeeWX fields. Otherwise the WeeWX field "ET"/"UV" will be formed if no prefix is used!
    # Mapping API observation fields -> WeeWX field, unit, group
    OBS = {
        'timestamp': ('timestamp', 'unix_epoch', 'group_time'),
        'dateTimeISO': ('timestampISO', None, None),
        'tempC': ('outTemp', 'degree_C', 'group_temperature'), # The temperature in Celsius at the start of the forecast period. The value will be null when using filter=day, filter=mdnt2mdnt, or filter=daynight.
        'minTempC': ('outTemp_min', 'degree_C', 'group_temperature'),
        'maxTempC': ('outTemp_max', 'degree_C', 'group_temperature'),
        'feelslikeC': ('feelslike', 'degree_C', 'group_temperature'), #The apparent temperature in Celsius. - Not used/valid when using filter=day or filter=daynight
        'minFeelslikeC': ('feelslike_min', 'degree_C', 'group_temperature'),
        'maxFeelslikeC': ('feelslike_max', 'degree_C', 'group_temperature'),
        'dewpointC': ('dewpoint', 'degree_C', 'group_temperature'),
        'minDewpointC': ('dewpoint_min', 'degree_C', 'group_temperature'),
        'maxDewpointC': ('dewpoint_max', 'degree_C', 'group_temperature'),
        'humidity': ('outHumidity', 'percent', 'group_percent'),
        'minHumidity': ('outHumidity_min', 'percent', 'group_percent'),
        'maxHumidity': ('outHumidity_max', 'percent', 'group_percent'),
        'pop': ('pop', 'percent', 'group_percent'),
        'precipMM': ('rain', 'mm', 'group_rain'), # Precipitation expected in millimeters. The total liquid equivalent of all precipitation.
        #'iceaccumMM': ('ice', 'mm', 'group_rain'), # The amount of ice accretion/accumulation in mm. Available for the US only out 48 hours
        'snowCM': ('snow', 'cm', 'group_rain'), # Snowfall amount in centimeters.
        'windDir': ('compass', None, None), # TODO Wind direction in cardinal coordinates. - Not used/valid when using filter=day or filter=daynight
        'windDirMin': ('compass_min', None, None), # Wind direction in cardinal coordinates. - Not used/valid when using filter=day or filter=daynight
        'windDirMax': ('compass_max', None, None), # Wind direction in cardinal coordinates. - Not used/valid when using filter=day or filter=daynight
        'windDirDEG': ('windDir', 'degree_compass', 'group_direction'),
        'windDirMinDEG': ('windDir_min', 'degree_compass', 'group_direction'),
        'windDirMaxDEG': ('windDir_max', 'degree_compass', 'group_direction'),
        'windSpeedKPH': ('windSpeed', 'km_per_hour', 'group_speed'),
        'windSpeedMinKPH': ('windSpeed_min', 'km_per_hour', 'group_speed'),
        'windSpeedMaxKPH': ('windSpeed_max', 'km_per_hour', 'group_speed'),
        'windGustKPH': ('windGust', 'km_per_hour', 'group_speed'),
        'sky': ('cloudcover', 'percent', 'group_percent'),
        'cloudsCoded': ('cloudsCoded', None, None),
        'weather': ('weather', None, None),
        'weatherCoded': ('weatherCoded', None, None),
        'weatherPrimary': ('weatherPrimary', None, None),
        'weatherPrimaryCoded': ('weatherPrimaryCoded', None, None),
        'icon': ('icon', None, None),
        'visibilityKM': ('visibility', 'km', 'group_distance'),
        #'uvi': ('uvi','uv_index','group_uv'), # The ultraviolet index. Integer from 0 - 12, null if unavailable. Available for the first five days of the forecasts
        'solradWM2': ('solarRad','watt_per_meter_squared','group_radiation'), # TODO solarRad or radiation?
        'solradMinWM2': ('solarRad_min','watt_per_meter_squared','group_radiation'),
        'solradMaxWM2': ('solarRad_max','watt_per_meter_squared','group_radiation'),
        'solradClearSkyWM2': ('solarRadClearSky','watt_per_meter_squared','group_radiation'), # TODO solarRad or radiation?
        'spressureMB': ('pressure', 'mbar', 'group_pressure'), # only 1h, 3h
        'pressureMB': ('barometer', 'mbar', 'group_pressure'),
        'altimeterMB': ('altimeter', 'mbar', 'group_pressure'), # only 1h, 3h
        'isDay': ('day', 'count', 'group_count')
    }

    def get_obs(self):
        return AERISthread.OBS



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
        self.model = self.config.get('model', 'aeris')
        self.source_id = self.config.get('source_id', 'aeris')
        self.interval_get = weeutil.weeutil.to_int(self.config.get('interval_get', 300))
        self.interval_push = weeutil.weeutil.to_int(self.config.get('interval_push', 30))
        self.expired = weeutil.weeutil.to_int(self.config.get('expired', 600))
        self.icon_path_belchertown = self.config.get('icon_path_belchertown', '')
        self.timezone = self.config.get('timezone', 'Europe/Berlin')
        self.config_dict = thread_dict.get('config_dict')
        self.engine = thread_dict.get('engine')
        self.hourly_obs = self.get_obs()
        self.lat = weeutil.weeutil.to_float(self.config.get('latitude'))
        self.lon = weeutil.weeutil.to_float(self.config.get('longitude'))
        self.alt = weeutil.weeutil.to_float(self.config.get('altitude'))
        self.data_result = dict()
        self.data_temp = dict()
        self.last_get_ts = 0

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

        weewx.units.obs_group_dict.setdefault('dateTime','group_time')
        weewx.units.obs_group_dict.setdefault('generated','group_time')
        weewx.units.obs_group_dict.setdefault('age','group_deltatime')
        weewx.units.obs_group_dict.setdefault('day','group_count')
        weewx.units.obs_group_dict.setdefault('expired','group_count')
        weewx.units.obs_group_dict.setdefault('weathercode','group_count')
        weewx.units.obs_group_dict.setdefault('weathercodeKey','group_count')
        for opsapi, obsweewx in self.hourly_obs.items():
            weewx.units.obs_group_dict.setdefault(obsweewx[0], obsweewx[2])

        dbout_dict = self.config.get('db_out', configobj.ConfigObj())
        if weeutil.weeutil.to_bool(dbout_dict.get('enable', False)):
            data_binding_name = dbout_dict.get('data_binding')
            if data_binding_name is None:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': init data_binding is not configured!" % (self.name))
                return
            # open the data store
            self.dbm = self.engine.db_binder.get_manager(data_binding=data_binding_name, initialize=True)
            # confirm db schema
            dbcols = self.dbm.connection.columnsOf(self.dbm.table_name)
            dbm_dict = weewx.manager.get_manager_dict_from_config(self.config_dict, data_binding_name)
            memcols = [x[0] for x in dbm_dict['schema']]
            if dbcols != memcols:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': init store schema mismatch: %s != %s" % (self.name, dbcols, memcols))
                return
        elif self.log_success or self.debug > 0:
            loginf("thread '%s': init db_out is diabled. Enable it in the [db_out] section of station %s" %(self.name, self.station))

        if self.log_success or self.debug > 0:
            loginf("thread '%s': init finished" % self.name)


    def get_data_api(self):
        """ download and process Aeris API forecast data """

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

        baseurl = 'https://api.aerisapi.com/forecasts/%s,%s?format=json&client_id=%s&client_secret=%s'
        # Params
        params = '&filter=%s&limit=%s'
        baseurl = baseurl % (str(self.lat), str(self.lon), api_id, api_secret)

        data_temp = dict()
        for interval in ('1h', '3h', '24h', 'db'):
            if interval == '1h':
                limit = '16'
                param = params % (interval, limit)
            elif interval == 'db':
                # current timestamp
                current_time = datetime.datetime.now(pytz.utc)
                current_time_ts = weeutil.weeutil.to_int(current_time.timestamp())
                current_time_berlin = current_time.astimezone(pytz.timezone('Europe/Berlin'))
                utcoffset = weeutil.weeutil.to_int(current_time_berlin.utcoffset().total_seconds())

                # start with the current full hour timestamp
                current_hour = current_time.replace(minute=0, second=0, microsecond=0)
                current_hour_ts = weeutil.weeutil.to_int(current_hour.timestamp())

                # next day 00:00 timestamp
                next_day = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
                next_day_ts = weeutil.weeutil.to_int(next_day.timestamp()) - utcoffset

                # max 8 days 
                end_day = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=8)
                end_day_ts = weeutil.weeutil.to_int(end_day.timestamp()) - utcoffset

                # diff hours from start to 24h
                today_remaining_hours = weeutil.weeutil.to_int((next_day_ts + utcoffset - current_hour_ts) / 3600)

                limit = str((7*24) + today_remaining_hours)
                param = params % ('1h', limit)
            else:
                limit = '8'
                param = params % (interval, limit)
            url = baseurl + param

            if debug > 2:
                logdbg("thread '%s': get_data_api url %s" % (self.name, url))

            attempts = 0
            try:
                while attempts <= attempts_max:
                    attempts += 1
                    response, code = request_api(self.name, url,
                                                debug = self.debug,
                                                log_success = log_success,
                                                log_failure = log_failure)
                    if response is not None:
                        data_temp[interval] = response
                        attempts = attempts_max + 1
                    elif attempts <= attempts_max:
                        if log_failure or debug > 0:
                            logerr("thread '%s': get_data_api request_api sent http status code %d" % (self.name, code))
                            loginf("thread '%s': get_data_api request_api next try (%d/%d) in %d seconds" % (self.name, attempts, attempts_max, attempts_wait))
                        time.sleep(attempts_wait)
                    else:
                        if log_failure or debug > 0:
                            logerr("thread '%s': get_data_api api did not send data" % self.name)
                        data_temp = None
                        return False
            except Exception as e:
                exception_output(self.name, e)
                data_temp = None
                return False


        if debug > 2:
            logdbg("thread '%s': get_data_api api unchecked result %s" % (self.name, json.dumps(data_temp)))

        # check results
        ok = True
        error = ''
        for interval in ('1h', '3h', '24h', 'db'):
            try:
                success = data_temp[interval]['success']
                if not success:
                    error += ', ' + interval + ': ' + data_temp.get(interval, dict()).get('error', '')
                    ok = False
                # test if datas exists
                test = data_temp[interval]['response'][0]['periods']
                test = data_temp[interval]['response'][0]['loc']
                test = data_temp[interval]['response'][0]['loc']['long']
                test = data_temp[interval]['response'][0]['loc']['lat']
                test = data_temp[interval]['response'][0]['place']['name']
                test = data_temp[interval]['response'][0]['place']['state']
                test = data_temp[interval]['response'][0]['place']['country']
                test = data_temp[interval]['response'][0]['profile']
                test = data_temp[interval]['response'][0]['profile']['tz']
                test = data_temp[interval]['response'][0]['profile']['elevM']
                test = None
            except Exception as e:
                exception_output(self.name, e, 'get_data_api interval %s' % interval)
                ok = False
                pass

        if not ok:
            logerr("thread '%s': get_data_api api send error %s" % (self.name, error[2:]))
            data_temp = None
            return False

        try:
            actts = weeutil.weeutil.to_int(time.time())
            self.data_temp['dateTime'] = weeutil.weeutil.to_int(actts)
            self.data_temp['dateTimeISO'] = get_isodate_from_timestamp(weeutil.weeutil.to_int(actts), self.timezone)
            self.data_temp['generated'] = weeutil.weeutil.to_int(actts)
            self.data_temp['generatedISO'] = get_isodate_from_timestamp(weeutil.weeutil.to_int(actts), self.timezone)
            lat = data_temp['24h']['response'][0]['loc']['lat']
            lon = data_temp['24h']['response'][0]['loc']['long']
            alt = data_temp['24h']['response'][0]['profile']['elevM']
            self.data_temp['latitude'] = lat
            self.data_temp['longitude'] = lon
            self.data_temp['altitude'] = alt
            self.data_temp['name'] = data_temp[interval]['response'][0]['place']['name'][0].upper() + data_temp[interval]['response'][0]['place']['name'][1:].lower()
            self.data_temp['state'] = data_temp[interval]['response'][0]['place']['state']
            self.data_temp['country'] = data_temp[interval]['response'][0]['place']['country']
            self.data_temp['sourceProvider'] = PROVIDER[self.source_id][0]
            self.data_temp['sourceUrl'] = obfuscate_secrets(url)
            self.data_temp['sourceProviderLink'] = PROVIDER[self.source_id][1]
            self.data_temp['sourceProviderHTML'] = HTMLTMPL % (PROVIDER[self.source_id][1], PROVIDER[self.source_id][0], PROVIDER[self.source_id][2])
            self.data_temp['sourceModul'] = self.name
            self.data_temp['sourceId'] = self.source_id
            self.data_temp['lang'] = lang
            self.data_temp['usUnits'] = unitsystem
            self.data_temp['1h'] = dict()
            self.data_temp['3h'] = dict()
            self.data_temp['24h'] = dict()
            self.data_temp['db'] = dict()

            # temp using for is_night
            night_dict = dict()
            night_dict['latitude'] = (lat, 'degree_compass', 'group_coordinate')
            night_dict['longitude'] = (lon, 'degree_compass', 'group_coordinate')
            night_dict['altitude'] = (alt, 'meter', 'group_altitude')

            for interval in ('1h', '3h', '24h', 'db'):
                col = 0
                for data in data_temp[interval]['response'][0]['periods']:
                    col += 1
                    self.data_temp[interval][str(col)] = dict()
                    for obsapi, obsweewx in self.hourly_obs.items():
                        obsval = data.get(obsapi)
                        if obsval is None:
                            if log_failure or debug > 0:
                                logerr("thread '%s': get_data_api None for ts %s obs %s - %s" % (self.name, interval, obsapi, obsweewx[0]))
                        if obsweewx[2] is not None:
                            obsval = weeutil.weeutil.to_float(obsval)
                        if obsval is None and obsweewx[2] in ('group_rain', 'group_percent'):
                            obsval = 0.0
                        self.data_temp[interval][str(col)][obsweewx[0]] = (obsval, obsweewx[1], obsweewx[2])

                    # TODO check this
                    # compass
                    # wdir = self.data_temp[interval][str(col)].get('windDir')
                    # if wdir is not None:
                        # self.data_temp[interval][str(col)]['compass'] = (compass(wdir[0], lang), None, None)
                    # else:
                        # self.data_temp[interval][str(col)]['compass'] = ('', None, None)

                    # is night?
                    night_dict['dateTime'] = self.data_temp[interval][str(col)].get('timestamp')
                    if interval in ('1h', 'db'):
                        night_dict['outTemp'] = self.data_temp[interval][str(col)].get('outTemp')
                        night_dict['barometer'] = self.data_temp[interval][str(col)].get('barometer')
                        night = is_night(self.name, night_dict, debug=debug, log_success=log_success, log_failure=log_failure)
                    elif interval == '3h':
                        night_dict['outTemp'] = self.data_temp[interval][str(col)].get('outTemp_max')
                        night_dict['barometer'] = self.data_temp[interval][str(col)].get('barometer')
                        night = is_night(self.name, night_dict, debug=debug, log_success=log_success, log_failure=log_failure)
                    else:
                        night = 0
                    # TODO check this
                    self.data_temp[interval][str(col)]['day'] = (0 if night else 1, 'count', 'group_count')

                    # weathertext and weathericon
                    self.data_temp[interval][str(col)]['weathercodeAeris'] = self.data_temp[interval][str(col)].get('weatherPrimaryCoded')
                    # return (text_de, text_en, icon, weathercode)
                    aeriscode = self.data_temp[interval][str(col)].get('weatherPrimaryCoded')[0]
                    weathertext_en = self.data_temp[interval][str(col)].get('weather')[0]
                    wxdata = self.get_icon_and_text(aeriscode, night=night, debug=debug, log_success=log_success, log_failure=log_failure, weathertext_en=weathertext_en)
                    self.data_temp[interval][str(col)]['weathercode'] = (weeutil.weeutil.to_int(wxdata[3]), 'count', 'group_count')
                    self.data_temp[interval][str(col)]['weathercodeKey'] = (weeutil.weeutil.to_int(wxdata[3]), 'count', 'group_count')
                    self.data_temp[interval][str(col)]['weathericon'] = (wxdata[2], None, None)
                    self.data_temp[interval][str(col)]['weathertext'] = dict()
                    self.data_temp[interval][str(col)]['weathertext']['de'] = (wxdata[0], None, None)
                    self.data_temp[interval][str(col)]['weathertext']['en'] = (wxdata[1], None, None)

        except Exception as e:
            exception_output(self.name, e, 'get_data_api interval %s' % interval)
            self.data_temp = dict()
            data_temp = None
            return False

        if log_success or debug > 0:
            loginf("thread '%s': get_data_api finished. Number of records processed: %d" % (self.name, len(self.data_temp)))
        if debug > 2:
            logdbg("thread '%s': get_data_api unchecked result %s" % (self.name, json.dumps(self.data_temp)))
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
            data = threads[thread_name].get_data_result()
            if len(data) > 0:
                source_id = data.get('sourceId')
                if source_id is not None:
                    if debug > 2:
                        loginf("thread '%s': get_data_results Thread '%s' has valid source_id %s" % (self.name, thread_name, str(source_id)))
                    self.data_temp[source_id] = data
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
# Class ForecastWX
#
# ============================================================================

class ForecastWX(StdService):

    def _create_openmeteo_thread(self, thread_name, station_dict):
        thread_name = "%s_%s" % (SERVICEID, thread_name)
        self.threads[SERVICEID][thread_name] = OPENMETEOthread(thread_name, station_dict,
                    debug=weeutil.weeutil.to_int(station_dict.get('debug', self.debug)),
                    log_success=weeutil.weeutil.to_bool(station_dict.get('log_success',self.log_success)),
                    log_failure=weeutil.weeutil.to_bool(station_dict.get('log_failure',self.log_failure)))
        self.threads[SERVICEID][thread_name].start()



    def _create_brightsky_thread(self, thread_name, station_dict):
        thread_name = "%s_%s" % (SERVICEID, thread_name)
        self.threads[SERVICEID][thread_name] = BRIGHTSKYthread(thread_name, station_dict,
                    debug=weeutil.weeutil.to_int(station_dict.get('debug', self.debug)),
                    log_success=weeutil.weeutil.to_bool(station_dict.get('log_success',self.log_success)),
                    log_failure=weeutil.weeutil.to_bool(station_dict.get('log_failure',self.log_failure)))
        self.threads[SERVICEID][thread_name].start()



    def _create_mosmix_thread(self, thread_name, station_dict):
        thread_name = "%s_%s" % (SERVICEID, thread_name)
        self.threads[SERVICEID][thread_name] = MOSMIXthread(thread_name, station_dict,
                    debug=weeutil.weeutil.to_int(station_dict.get('debug', self.debug)),
                    log_success=weeutil.weeutil.to_bool(station_dict.get('log_success',self.log_success)),
                    log_failure=weeutil.weeutil.to_bool(station_dict.get('log_failure',self.log_failure)))
        self.threads[SERVICEID][thread_name].start()



    def _create_aeris_thread(self, thread_name, station_dict):
        thread_name = "%s_%s" % (SERVICEID, thread_name)
        self.threads[SERVICEID][thread_name] = AERISthread(thread_name, station_dict,
                    debug=weeutil.weeutil.to_int(station_dict.get('debug', self.debug)),
                    log_success=weeutil.weeutil.to_bool(station_dict.get('log_success',self.log_success)),
                    log_failure=weeutil.weeutil.to_bool(station_dict.get('log_failure',self.log_failure)))
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
            logdbg("Service 'ForecastWX': check_section section '%s' started" % (section))

        cancel = False

        # new section configurations apply?
        debug = weeutil.weeutil.to_int(section_dict.get('debug', self.service_dict.get('debug', 0)))
        log_success = weeutil.weeutil.to_bool(section_dict.get('log_success', self.service_dict.get('log_success', False)))
        log_failure = weeutil.weeutil.to_bool(section_dict.get('log_failure', self.service_dict.get('log_success', True)))

        # Check required provider
        provider = section_dict.get('provider')
        if provider: provider = provider.lower()
        if provider not in ('dwd', 'brightsky', 'open-meteo', 'aeris', 'total'):
            if log_failure or debug > 0:
                logerr("Service 'ForecastWX': check_section section '%s' forecast service provider '%s' is not valid. Skip Section" % (section, provider))
            cancel = True
            return cancel, section_dict

        # Check required model
        model = section_dict.get('model')
        if model: model = model.lower()
        if provider == 'dwd':
            if model not in ('mosmix'):
                if log_failure or debug > 0:
                    logerr("Service 'ForecastWX': check_section section '%s' forecast service provider '%s' - model '%s' is not valid. Skip Section" % (section, provider, model))
                cancel = True
                return cancel, section_dict
        elif provider == 'aeris':
            if model not in ('forecast'):
                if log_failure or debug > 0:
                    logerr("Service 'ForecastWX': check_section section '%s' forecast service provider '%s' - model '%s' is not valid. Skip Section" % (section, provider, model))
                cancel = True
                return cancel, section_dict
        elif provider == 'brightsky':
            if model not in ('weather'):
                if log_failure or debug > 0:
                    logerr("Service 'ForecastWX': check_section section '%s' forecast service provider '%s' - model '%s' is not valid. Skip Section" % (section, provider, model))
                cancel = True
                return cancel, section_dict
        elif provider == 'open-meteo':
            if model not in OPENMETEOthread.WEATHERMODELS:
                if log_failure or debug > 0:
                    logerr("Service 'ForecastWX': check_section section '%s' forecast service provider '%s' - model '%s' is not valid. Skip Section" % (section, provider, model))
                cancel = True
                return cancel, section_dict

        # check required station 
        station = section_dict.get('station')
        if provider in ('dwd', 'brightsky') and station is None:
            if log_failure or debug > 0:
                logerr("Service 'ForecastWX': check_section section '%s' forecast service provider '%s' - station '%s' is not valid. Skip Section" % (section, provider, station))
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
                        logerr("Service 'ForecastWX': check_section section '%s' configured unit '%s' for altitude is not valid, altitude will be ignored" % (section, altitude_t[1]))
            else:
                section_dict['altitude'] = None
                if self.log_failure or self.debug > 0:
                    logerr("Service 'ForecastWX': check_section section '%s' configured altitude '%s' is not valid, altitude will be ignored" % (section, altitude))

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
            loginf("Service 'ForecastWX': check_section section '%s' finished" % (section))

        return cancel, section_dict



    def __init__(self, engine, config_dict):
        super(ForecastWX,self).__init__(engine, config_dict)

        self.service_dict = weeutil.config.accumulateLeaves(config_dict.get('forecastwx',configobj.ConfigObj()))
        # service enabled?
        if not weeutil.weeutil.to_bool(self.service_dict.get('enable', False)):
            loginf("Service 'ForecastWX': service is disabled. Enable it in the [forecastwx] section of weewx.conf")
            return
        loginf("Service 'ForecastWX': service is enabled")

        self.threads = dict()
        self.threads[SERVICEID] = dict()
        self.threads['worker'] = dict()

        #general configs
        self.debug = weeutil.weeutil.to_int(self.service_dict.get('debug', 0))
        self.log_success = weeutil.weeutil.to_bool(self.service_dict.get('log_success', True))
        self.log_failure = weeutil.weeutil.to_bool(self.service_dict.get('log_failure', True))
        if self.debug > 0:
            logdbg("Service 'ForecastWX': init started")

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
        forecastwx_dict = config_dict.get('forecastwx', configobj.ConfigObj())
        if self.debug > 2:
            logdbg("Service 'ForecastWX': forecastwx_dict %s" % (str(json.dumps(forecastwx_dict))))

        # section with current weather services only
        current_dict = config_dict.get('forecastwx',configobj.ConfigObj()).get('forecast',configobj.ConfigObj())
        if self.debug > 2:
            logdbg("Service 'ForecastWX': current_dict %s" % (str(json.dumps(current_dict))))

        stations_dict = current_dict.get('stations',configobj.ConfigObj())
        for section in stations_dict.sections:
            if not weeutil.weeutil.to_bool(stations_dict[section].get('enable', False)):
                if self.log_success or self.debug > 0:
                    loginf("Service 'ForecastWX': init current section '%s' is not enabled. Skip section" % section)
                continue

            # build section config
            section_dict = weeutil.config.accumulateLeaves(stations_dict[section])
            provider = str(section_dict.get('provider')).lower()
            model = str(section_dict.get('model')).lower()

            # update general config
            section_dict['result_in'] = weeutil.config.deep_copy(forecastwx_dict.get('result_in'))
            section_dict['api_in'] = weeutil.config.deep_copy(forecastwx_dict.get('api_in'))
            section_dict['api_out'] = weeutil.config.deep_copy(forecastwx_dict.get('api_out'))
            section_dict['mqtt_in'] = weeutil.config.deep_copy(forecastwx_dict.get('mqtt_in'))
            section_dict['mqtt_out'] = weeutil.config.deep_copy(forecastwx_dict.get('mqtt_out'))
            section_dict['file_in'] = weeutil.config.deep_copy(forecastwx_dict.get('file_in'))
            section_dict['file_out'] = weeutil.config.deep_copy(forecastwx_dict.get('file_out'))
            section_dict['db_in'] = weeutil.config.deep_copy(forecastwx_dict.get('db_in'))
            section_dict['db_out'] = weeutil.config.deep_copy(forecastwx_dict.get('db_out'))

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

            # start configured forecast weather threads
            if provider == 'dwd':
                if model == 'mosmix':
                    self._create_mosmix_thread(section, thread_config)
            elif provider == 'open-meteo':
                self._create_openmeteo_thread(section, thread_config)
            elif provider == 'brightsky':
                self._create_brightsky_thread(section, thread_config)
            elif provider == 'aeris':
                self._create_aeris_thread(section, thread_config)
            elif provider == 'total':
                self._create_total_thread(section, thread_config)
            elif self.log_failure or self.debug > 0:
                logerr("Service 'ForecastWX': init section '%s' unknown forecast service provider '%s'" % (section, provider))

        if  __name__!='__main__':
            self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet)
            self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

        if self.log_success or self.debug > 0:
            loginf("Service 'ForecastWX': init finished. Number of current threads started: %d" % (len(self.threads[SERVICEID])))
        if len(self.threads[SERVICEID]) < 1:
            loginf("Service 'ForecastWX': no threads have been started. Service 'ForecastWX' exits now")
            return
