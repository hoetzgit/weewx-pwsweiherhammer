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

    This service loads current AQI data from various providers.

    Providers:
      Vaisala Xweather
      Open-Meteo
      OpenWeather
      Umweltbundesamt
      PWS Weiherhammer
      and and a mix of the data from the PWS with the data from the other services

    The goal is to provide the Weiherhammer Skin (Belchertown Skin Fork) with 
    standardized JSON data in a file and in a MQTT Topic. This way it is possible
    to switch within the skin without much effort between the different providers.
    If new data is loaded, the updated topic can be loaded and displayed updated.
"""

#TODO: develop03 weewx[81006] ERROR weiwx.currentaq: thread 'currentaq_total': Exception: TypeError - 'int' object is not subscriptable File: currentaq.py Line: 1262

VERSION = "0.1b3"

import threading
import configobj
import csv
import io
import time
import random
import os
import shutil
import sys
import paho.mqtt.publish as mqtt_publish
import paho.mqtt.subscribe as mqtt_subscribe
import requests
from requests.exceptions import Timeout
import datetime
from datetime import timezone
import pytz
import json
from json import JSONDecodeError

try:
    # Test for new-style weewx logging by trying to import weeutil.logger
    import weeutil.logger
    import logging
    log = logging.getLogger("weiwx.currentaq")

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
        syslog.syslog(level, 'weiwx.currentaq: %s' % msg)

    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)

    def logwrn(msg):
        logmsg(syslog.LOG_WARNING, msg)

import weewx
import weewx.engine
from weewx.engine import StdService
import weeutil.weeutil
import weewx.accum
import weewx.units
import weewx.wxformulas
import weewx.almanac
import weewx.cheetahgenerator

sys.path.append('/home/weewx/bin/weiwx/aqi')
from calculate import Calculate

SERVICEID='currentaq'

# provider current air quality
# ID        = Provider and model
# aeris     = Vaisala Xweather
# om        = Open-Meteo
# owm       = OpenWeather
# pws-506   = PWS Weiherhammer and Umweltbundesamt DEBY072
# pws-509   = PWS Weiherhammer and Umweltbundesamt DEBY075
# pws-aeris = PWS Weiherhammer and Vaisala Xweather
# pws-om    = PWS Weiherhammer and Open-Meteo
# pws-owm   = PWS Weiherhammer and OpenWeather
# uba-506   = Umweltbundesamt DEBY072
# uba-509   = Umweltbundesamt DEBY075

HTMLTMPL = {
    1: "<p><a href='%s' target='_blank' rel='tooltip' title=''>%s</a></p>",
    2: "<p><a href='%s' target='_blank' rel='tooltip' title=''>%s</a> (<a href='%s' target='_blank' rel='tooltip' title=''>%s</a>)</p>",
    3: "<p><a href='%s' target='_blank' rel='tooltip' title=''>%s</a> - <a href='%s' target='_blank' rel='tooltip' title=''>%s</a></p>"
}
PROVIDER = {
    'aeris': (1, 'Vaisala Xweather', 'https://www.xweather.com'),
    'om': (1, 'Open-Meteo', 'https://open-meteo.com'),
    'owm': (1, 'OpenWeather', 'https://openweathermap.org'),
    'pws': (1, 'PWS Weiherhammer', 'https://www.weiherhammer-wetter.de'),
    'uba-506': (2, 'Umweltbundesamt', 'DEBY072', 'https://www.umweltbundesamt.de', 'https://www.lfu.bayern.de/luft/immissionsmessungen/doc/lueb_dokumentation/aktiv/03_Oberpfalz/04_tiefenbach_altenschneeberg.pdf'),
    'uba-509': (2, 'Umweltbundesamt', 'DEBY075', 'https://www.umweltbundesamt.de', 'https://www.lfu.bayern.de/luft/immissionsmessungen/doc/lueb_dokumentation/aktiv/03_Oberpfalz/05_weiden_idopf_nikolaistrasse.pdf'),
    'pws-506': (3, 'PWS', 'UBA DEBY072', 'https://www.weiherhammer-wetter.de', 'https://www.umweltbundesamt.de'),
    'pws-509': (3, 'PWS', 'UBA DEBY075', 'https://www.weiherhammer-wetter.de', 'https://www.umweltbundesamt.de'),
    'pws-aeris': (3, 'PWS', 'Vaisala Xweather', 'https://www.weiherhammer-wetter.de', 'https://www.xweather.com'),
    'pws-om': (3, 'PWS', 'Open-Meteo', 'https://www.weiherhammer-wetter.de', 'https://open-meteo.com'),
    'pws-owm': (3, 'PWS', 'OpenWeather', 'https://www.weiherhammer-wetter.de', 'https://openweathermap.org')
}

# TODO
# Instant   Grains/m³ Pollen for various plants. Only available in Europe as provided by CAMS European Air Quality forecast.
# alder_pollen
# birch_pollen
# grass_pollen
# mugwort_pollen
# olive_pollen
# ragweed_pollen

AQOBS_EU = {
    'co': ('co', 'microgram_per_meter_cubed', 'group_concentration'),
    'nh3': ('nh3', 'microgram_per_meter_cubed', 'group_concentration'),
    'no': ('no', 'microgram_per_meter_cubed', 'group_concentration'),
    'no2': ('no2', 'microgram_per_meter_cubed', 'group_concentration'),
    'o3': ('o3', 'microgram_per_meter_cubed', 'group_concentration'),
    'pb': ('pb', 'microgram_per_meter_cubed', 'group_concentration'),
    'pm10_0': ('pm10_0', 'microgram_per_meter_cubed', 'group_concentration'),
    'pm2_5': ('pm2_5', 'microgram_per_meter_cubed', 'group_concentration'),
    'so2': ('so2', 'microgram_per_meter_cubed', 'group_concentration')
}

AQOBS_US = {
    'co': ('co', 'ppm', 'group_fraction'),
    'nh3': ('nh3', 'ppm', 'group_fraction'),
    'no': ('no', 'ppm', 'group_fraction'),
    'no2': ('no2', 'ppm', 'group_fraction'),
    'o3': ('o3', 'ppm', 'group_fraction'),
    'pb': ('pb', 'ppm', 'group_fraction'),
    'pm10_0': ('pm10_0', 'microgram_per_meter_cubed', 'group_concentration'),
    'pm2_5': ('pm2_5', 'microgram_per_meter_cubed', 'group_concentration'),
    'so2': ('so2', 'ppm', 'group_fraction')
}

AQIOBS = {
    'aqi_standard': ('eu_aqi_standard', 'count', 'group_count'),
    'aqi_composite': ('eu_aqi_composite', 'count', 'group_count'),
    'aqi_composite_category': ('eu_aqi_composite_category', 'count', 'group_count'),
    'aqi_co': ('eu_aqi_co', 'count', 'group_count'),
    'aqi_co_category': ('eu_aqi_co_category', 'count', 'group_count'),
    'aqi_nh3': ('eu_aqi_nh3', 'count', 'group_count'),
    'aqi_nh3_category': ('eu_aqi_nh3_category', 'count', 'group_count'),
    'aqi_no': ('eu_aqi_no', 'count', 'group_count'),
    'aqi_no_category': ('eu_aqi_no_category', 'count', 'group_count'),
    'aqi_no2': ('eu_aqi_no2', 'count', 'group_count'),
    'aqi_no2_category': ('eu_aqi_no2_category', 'count', 'group_count'),
    'aqi_o3': ('eu_aqi_o3', 'count', 'group_count'),
    'aqi_o3_category': ('eu_aqi_o3_category', 'count', 'group_count'),
    'aqi_pb': ('eu_aqi_pb', 'count', 'group_count'),
    'aqi_pb_category': ('eu_aqi_pb_category', 'count', 'group_count'),
    'aqi_pm10_0': ('eu_aqi_pm10_0', 'count', 'group_count'),
    'aqi_pm10_0_category': ('eu_aqi_pm10_0_category', 'count', 'group_count'),
    'aqi_pm2_5': ('eu_aqi_pm2_5', 'count', 'group_count'),
    'aqi_pm2_5_category': ('eu_aqi_pm2_5_category', 'count', 'group_count'),
    'aqi_so2': ('eu_aqi_so2', 'count', 'group_count'),
    'aqi_so2_category': ('eu_aqi_so2_category', 'count', 'group_count')
}

AQIOBS_EU = {
    'eu_aqi_standard': ('eu_aqi_standard', 'count', 'group_count'),
    'eu_aqi_composite': ('eu_aqi_composite', 'count', 'group_count'),
    'eu_aqi_composite_category': ('eu_aqi_composite_category', 'count', 'group_count'),
    'eu_aqi_co': ('eu_aqi_co', 'count', 'group_count'),
    'eu_aqi_co_category': ('eu_aqi_co_category', 'count', 'group_count'),
    'eu_aqi_nh3': ('eu_aqi_nh3', 'count', 'group_count'),
    'eu_aqi_nh3_category': ('eu_aqi_nh3_category', 'count', 'group_count'),
    'eu_aqi_no': ('eu_aqi_no', 'count', 'group_count'),
    'eu_aqi_no_category': ('eu_aqi_no_category', 'count', 'group_count'),
    'eu_aqi_no2': ('eu_aqi_no2', 'count', 'group_count'),
    'eu_aqi_no2_category': ('eu_aqi_no2_category', 'count', 'group_count'),
    'eu_aqi_o3': ('eu_aqi_o3', 'count', 'group_count'),
    'eu_aqi_o3_category': ('eu_aqi_o3_category', 'count', 'group_count'),
    'eu_aqi_pb': ('eu_aqi_pb', 'count', 'group_count'),
    'eu_aqi_pb_category': ('eu_aqi_pb_category', 'count', 'group_count'),
    'eu_aqi_pm10_0': ('eu_aqi_pm10_0', 'count', 'group_count'),
    'eu_aqi_pm10_0_category': ('eu_aqi_pm10_0_category', 'count', 'group_count'),
    'eu_aqi_pm2_5': ('eu_aqi_pm2_5', 'count', 'group_count'),
    'eu_aqi_pm2_5_category': ('eu_aqi_pm2_5_category', 'count', 'group_count'),
    'eu_aqi_so2': ('eu_aqi_so2', 'count', 'group_count'),
    'eu_aqi_so2_category': ('eu_aqi_so2_category', 'count', 'group_count')
}

AQIOBS_US = {
    'us_aqi_standard': ('eu_aqi_standard', 'count', 'group_count'),
    'us_aqi_composite': ('eu_aqi_composite', 'count', 'group_count'),
    'us_aqi_composite_category': ('eu_aqi_composite_category', 'count', 'group_count'),
    'us_aqi_co': ('us_aqi_co', 'count', 'group_count'),
    'us_aqi_co_category': ('us_aqi_co_category', 'count', 'group_count'),
    'us_aqi_nh3': ('us_aqi_nh3', 'count', 'group_count'),
    'us_aqi_nh3_category': ('us_aqi_nh3_category', 'count', 'group_count'),
    'us_aqi_no': ('us_aqi_no', 'count', 'group_count'),
    'us_aqi_no_category': ('us_aqi_no_category', 'count', 'group_count'),
    'us_aqi_no2': ('us_aqi_no2', 'count', 'group_count'),
    'us_aqi_no2_category': ('us_aqi_no2_category', 'count', 'group_count'),
    'us_aqi_o3': ('us_aqi_o3', 'count', 'group_count'),
    'us_aqi_o3_category': ('us_aqi_o3_category', 'count', 'group_count'),
    'us_aqi_pb': ('us_aqi_pb', 'count', 'group_count'),
    'us_aqi_pb_category': ('us_aqi_pb_category', 'count', 'group_count'),
    'us_aqi_pm10_0': ('us_aqi_pm10_0', 'count', 'group_count'),
    'us_aqi_pm10_0_category': ('us_aqi_pm10_0_category', 'count', 'group_count'),
    'us_aqi_pm2_5': ('us_aqi_pm2_5', 'count', 'group_count'),
    'us_aqi_pm2_5_category': ('us_aqi_pm2_5_category', 'count', 'group_count'),
    'us_aqi_so2': ('us_aqi_so2', 'count', 'group_count'),
    'us_aqi_so2_category': ('us_aqi_so2_category', 'count', 'group_count'),
}

AQIOBS_UBA = {
    'uba_aqi_standard': ('eu_aqi_standard', 'count', 'group_count'),
    'uba_aqi_composite': ('eu_aqi_composite', 'count', 'group_count'),
    'uba_aqi_composite_category': ('eu_aqi_composite_category', 'count', 'group_count'),
    'uba_aqi_co': ('uba_aqi_co', 'count', 'group_count'),
    'uba_aqi_co_category': ('uba_aqi_co_category', 'count', 'group_count'),
    'uba_aqi_nh3': ('uba_aqi_nh3', 'count', 'group_count'),
    'uba_aqi_nh3_category': ('uba_aqi_nh3_category', 'count', 'group_count'),
    'uba_aqi_no': ('uba_aqi_no', 'count', 'group_count'),
    'uba_aqi_no_category': ('uba_aqi_no_category', 'count', 'group_count'),
    'uba_aqi_no2': ('uba_aqi_no2', 'count', 'group_count'),
    'uba_aqi_no2_category': ('uba_aqi_no2_category', 'count', 'group_count'),
    'uba_aqi_o3': ('uba_aqi_o3', 'count', 'group_count'),
    'uba_aqi_o3_category': ('uba_aqi_o3_category', 'count', 'group_count'),
    'uba_aqi_pb': ('uba_aqi_pb', 'count', 'group_count'),
    'uba_aqi_pb_category': ('uba_aqi_pb_category', 'count', 'group_count'),
    'uba_aqi_pm10_0': ('uba_aqi_pm10_0', 'count', 'group_count'),
    'uba_aqi_pm10_0_category': ('uba_aqi_pm10_0_category', 'count', 'group_count'),
    'uba_aqi_pm2_5': ('uba_aqi_pm2_5', 'count', 'group_count'),
    'uba_aqi_pm2_5_category': ('uba_aqi_pm2_5_category', 'count', 'group_count'),
    'uba_aqi_so2': ('uba_aqi_so2', 'count', 'group_count'),
    'uba_aqi_so2_category': ('uba_aqi_so2_category', 'count', 'group_count')
}

for group in weewx.units.std_groups:
    weewx.units.std_groups[group].setdefault('group_coordinate','degree_compass')
for obs, values in AQOBS_EU.items():
    weewx.units.obs_group_dict.setdefault(obs, values[2])
for obs, values in AQIOBS_EU.items():
    weewx.units.obs_group_dict.setdefault(obs, values[2])
for obs, values in AQIOBS_US.items():
    weewx.units.obs_group_dict.setdefault(obs, values[2])
for obs, values in AQIOBS_UBA.items():
    weewx.units.obs_group_dict.setdefault(obs, values[2])

weewx.units.obs_group_dict.setdefault('age','group_deltatime')
weewx.units.obs_group_dict.setdefault('expired','group_count')
weewx.units.obs_group_dict.setdefault('generated','group_time')
weewx.units.obs_group_dict.setdefault('generatedMin','group_time')
weewx.units.obs_group_dict.setdefault('generatedMax','group_time')


@staticmethod
def create_provider_html(thread_name, prov, debug=0, log_success=False, log_failure=True):
    try:
        data = PROVIDER.get(prov)
        typ = data[0]
        tmpl = HTMLTMPL[typ]
        if typ == 1:
            text = data[1]
            link = data[2]
            html = tmpl % (data[2], data[1])
        elif typ == 2:
            text = "%s (%s)" % (data[1], data[2])
            link = data[3]
            html = tmpl % (data[3], data[1], data[4], data[2])
        elif typ == 3:
            text = "%s, %s" % (data[1], data[2])
            link = "%s, %s" % (data[3], data[4])
            html = tmpl % (data[3], data[1], data[4], data[2])
        return text, link, html
    except Exception as e:
        exception_output(thread_name, e, prov)


@staticmethod
def exception_output(thread_name, e, addcontent=None, debug=1, log_failure=True):
    if log_failure or debug > 0:
        exception_type, exception_object, exception_traceback = sys.exc_info()
        filename = os.path.split(exception_traceback.tb_frame.f_code.co_filename)[1]
        line = exception_traceback.tb_lineno
        logerr("thread '%s': Exception: %s - %s File: %s Line: %s" % (thread_name, e.__class__.__name__, e, str(filename), str(line)))
        if addcontent is not None:
            logerr("thread '%s': addcontent: %s" % (thread_name, str(addcontent)))


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

    headers={'User-Agent': 'currentaq'}
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
    current['sourceProvider'] = data['sourceProvider'] if ('sourceProvider' in data and data['sourceProvider'] is not None) else 'unknown'
    current['sourceProviderLink'] = data['sourceProviderLink'] if ('sourceProviderLink' in data and data['sourceProviderLink'] is not None) else 'https://www.weiherhammer-wetter.de'
    current['sourceProviderHTML'] = data['sourceProviderHTML'] if ('sourceProviderHTML' in data and data['sourceProviderHTML'] is not None) else HTMLTMPL[1] % ('https://www.weiherhammer-wetter.de', 'unknown')
    for obs, values in AQOBS_EU.items():
        if obs in data:
            current[obs] = data.get(obs)
    for obs, values in AQIOBS_EU.items():
        if obs in data:
            current[obs] = data.get(obs)
    for obs, values in AQIOBS_UBA.items():
        if obs in data:
            current[obs] = data.get(obs)
    for obs, values in AQIOBS_US.items():
        if obs in data:
            current[obs] = data.get(obs)
    if debug > 2:
        logdbg("thread '%s': minimize_current_total_mqtt current %s" % (thread_name, json.dumps(current)))
    return current


@staticmethod
def minimize_current_total_file(thread_name, data, debug=0, log_success=False, log_failure=True):
    """
    Minimize the output of weather providers and generate only the required elements that are 
    absolutely necessary for displaying the current weather conditions in the Belchertown skin.
    """
    strings_to_remove = ['sourceUrl', 'sourceId', 'sourceModul', 'sourceProviderLink', 'sourceProviderHTML', 'interval']
    if debug > 2:
        logdbg("thread '%s': minimize_current_total_file data %s" % (thread_name, json.dumps(data)))
    current = dict()
    current['dateTime'] = data['dateTime'] if ('dateTime' in data and data['dateTime'] is not None) else 0
    current['dateTimeISO'] = data['dateTimeISO'] if ('dateTimeISO' in data and data['dateTimeISO'] is not None) else 'unknown' # better visual monitoring
    current['generated'] = data['generated'] if ('generated' in data and data['generated'] is not None) else 0
    current['generatedISO'] = data['generatedISO'] if ('generatedISO' in data and data['generatedISO'] is not None) else 'unknown' # better visual monitoring
    current['usUnits'] = data['usUnits'] if ('usUnits' in data and data['usUnits'] is not None) else -1
    current['lang'] = data['lang'] if ('lang' in data and data['lang'] is not None) else 'de'
    current['age'] = data['age'] if ('age' in data and data['age'] is not None) else None
    current['expired'] = data['expired'] if ('expired' in data and data['expired'] is not None) else 1
    current['sourceProvider'] = data['sourceProvider'] if ('sourceProvider' in data and data['sourceProvider'] is not None) else 'unknown'
    current['sourceProviderLink'] = data['sourceProviderLink'] if ('sourceProviderLink' in data and data['sourceProviderLink'] is not None) else 'https://www.weiherhammer-wetter.de'
    current['sourceProviderHTML'] = data['sourceProviderHTML'] if ('sourceProviderHTML' in data and data['sourceProviderHTML'] is not None) else HTMLTMPL[1] % ('https://www.weiherhammer-wetter.de', 'unknown')
    for obs, values in AQOBS_EU.items():
        if obs in data:
            current[obs] = data.get(obs)
    for obs, values in AQIOBS_EU.items():
        if obs in data:
            current[obs] = data.get(obs)
    for obs, values in AQIOBS_UBA.items():
        if obs in data:
            current[obs] = data.get(obs)
    for obs, values in AQIOBS_US.items():
        if obs in data:
            current[obs] = data.get(obs)
    if debug > 2:
        logdbg("thread '%s': minimize_current_total_file current %s" % (thread_name, json.dumps(current)))
    return current


@staticmethod
def minimize_current_result_mqtt(thread_name, data, debug=0, log_success=False, log_failure=True):
    """
    Minimizes the data and provides only the data that should be included in a WeeWX Loop Packet or in a WeeWX Archive Record.
    I don't need text fields in loop or archive data anymore. Icons and texts can be loaded externally by using weathercodeKey.
    """
    strings_to_remove = ['Url', 'sourceId', 'sourceModul', 'sourceProviderLink', 'sourceProviderHTML', 'interval']
    result = data
    if debug > 2:
        logdbg("thread '%s': minimize_current_result_mqtt result full %s" % (thread_name, json.dumps(result)))

    keys_to_remove = [key for key in result.keys() if any(string in key for string in strings_to_remove)]
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
            current[obs] = data.get(obs)

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
                        value = " " # # TODO The publisher does not send NULL or "" values
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
            if type(values) is not tuple:
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

    def __init__(self, name, thread_dict, debug=0, log_success=False, log_failure=True, threads=None):

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
        self.data_aqi = dict()
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


    def get_data_temp(self):
        """ get buffered data """
        try:
            self.lock.acquire()
            data = self.data_temp
        finally:
            self.lock.release()
        return data


    def get_last_aqi_ts(self):
        """ get last AQI saved timestamp """
        try:
            self.lock.acquire()
            last_aqi_ts = self.last_aqi_ts
        finally:
            self.lock.release()
        return last_aqi_ts


    def get_last_prepare_ts(self):
        """ get last prepare saved timestamp """
        try:
            self.lock.acquire()
            last_prepare_ts = self.last_prepare_ts
        finally:
            self.lock.release()
        return last_prepare_ts


    def get_config(self):
        """ get thread config data """
        try:
            self.lock.acquire()
            config = self.config
        finally:
            self.lock.release()
        return config


    def prepare_result(self, data, unitsystem, source_id, lang='de', debug=0, log_success=False, log_failure=True):
        """ prepare current weather data record for publishing  """
        if not len(data) > 0:
            if log_failure or debug > 0:
                logerr("thread '%s': prepare_result in data_temp empty." %(self.name))
            return data
        if not isinstance(data, dict):
            if log_failure or debug > 0:
                logerr("thread '%s': prepare_result in data_temp wrong format." %(self.name))
            if self.debug > 2:
                logdbg("thread '%s': prepare_result in data_temp %s" %(self.name, json.dumps(data)))
            return data
        data_temp = data
        try:
            if self.debug > 2:
                logdbg("thread '%s': prepare_result in data_temp %s" %(self.name, json.dumps(data_temp)))
            if source_id is not None:
                data_temp['sourceId'] = (source_id, None, None)
                text, link, html = create_provider_html(self.name, source_id, debug=debug, log_success=log_success, log_failure=log_failure)
                if data_temp.get('sourceProvider') is None:
                    data_temp['sourceProvider'] = (text, None, None)
                if data_temp.get('sourceProviderLink') is None:
                    data_temp['sourceProviderLink'] = (link, None, None)
                if data_temp.get('sourceProviderHTML') is None:
                    data_temp['sourceProviderHTML'] = (html, None, None)
            if data_temp.get('sourceModul') is None:
                data_temp['sourceModul'] = (self.name, None, None)
            data_temp['lang'] = (lang, None, None)

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
                    data_temp['age'] = (weeutil.weeutil.to_int(dateTime - generated), 'count', 'group_deltatime')

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


    def new_db_aq_record(self, event):
        """ insert API AQ Data into DB """

        dbout_dict = self.config.get('db_out', configobj.ConfigObj())
        debug = weeutil.weeutil.to_int(dbout_dict.get('debug', self.debug))
        log_success = weeutil.weeutil.to_bool(dbout_dict.get('log_success', self.log_success))
        log_failure = weeutil.weeutil.to_bool(dbout_dict.get('log_failure', self.log_failure))

        if len(self.data_temp) <= 0:
            if debug > 0:
                logdbg("thread '%s': new_db_aq_record There are no AQ data available yet. Don't execute." % (self.name))
            return False

        if debug > 0:
            logdbg("thread '%s': new_db_aq_record started" % (self.name))
        if debug > 2:
            logdbg("thread '%s': new_db_aq_record config %s" %(self.name, json.dumps(dbout_dict)))

        if not weeutil.weeutil.to_bool(dbout_dict.get('enable', False)):
            if log_success or debug > 0:
                loginf("thread '%s': new_db_aq_record db_out is diabled. Enable it in the [db_out] section of station %s" %(self.name, self.station))
            return False

        data = self.get_data_result()
        if len(data) <= 0:
            if debug > 0:
                logdbg("thread '%s': new_db_aq_record There are no AQ data available yet. Don't execute." % (self.name))
            return False

        try:
            now = weeutil.weeutil.to_int(time.time())
            data = to_packet(self.name, data, debug=debug, log_success=log_success, log_failure=log_failure, prefix=None)
            record = dict()
            record['dateTime'] = weeutil.weeutil.to_int(event.record['dateTime'])
            record['interval'] = weeutil.weeutil.to_int(event.record['interval'])
            record['usUnits'] = data.get('usUnits') if ('usUnits' in data and data.get('usUnits') is not None) else weewx.METRIC
            for obs, values in AQOBS_EU.items():
                if obs in data:
                    record[obs] = data.get(obs)
            self.dbm_aq.addRecord(record)
            if log_success or debug > 0:
                loginf("thread '%s': new_db_aq_record new record inserted." % (self.name))
        except Exception as e:
            exception_output(self.name, e)

        # delete records with dateTime older than ts
        max_age = weeutil.weeutil.to_int(dbout_dict.get('max_age', 8640000)) # default 100 Days
        if max_age is not None:
            ts = weeutil.weeutil.to_int(now - max_age)
            sql = "delete from %s where dateTime < %d" % (self.dbm_aq.table_name, ts)
            self.dbm_aq.getSql(sql)
            try:
                # sqlite databases need some help to stay small
                self.dbm_aq.getSql('vacuum')
            except Exception as e:
                pass
            if log_success or debug > 0:
                loginf("thread '%s': new_db_aq_record table '%s' pruned." % (self.name, self.dbm_aq.table_name))

        if log_success or debug > 0:
            loginf("thread '%s': new_db_aq_record finished." % (self.name))
        self.last_aq_ts = weeutil.weeutil.to_int(time.time())

        return True


    def new_db_aqi_record(self, event):
        """ calculate AQI and insert AQI Data to data_result and into DB """

        aqi_dict = self.config.get('aqi', configobj.ConfigObj())
        debug = weeutil.weeutil.to_int(aqi_dict.get('debug', self.debug))
        log_success = weeutil.weeutil.to_bool(aqi_dict.get('log_success', self.log_success))
        log_failure = weeutil.weeutil.to_bool(aqi_dict.get('log_failure', self.log_failure))

        if debug > 0:
            logdbg("thread '%s': new_db_aqi_record started" % (self.name))
        if debug > 2:
            logdbg("thread '%s': new_db_aqi_record config %s" %(self.name, json.dumps(aqi_dict)))

        if not weeutil.weeutil.to_bool(aqi_dict.get('enable', False)):
            if log_success or debug > 0:
                loginf("thread '%s': new_db_aqi_record aqi is diabled. Enable it in the [aqi] section of station %s" % (self.name, self.station))
            return False

        # get aqi config
        standards = weeutil.weeutil.option_as_list(aqi_dict.get('standards', list()))
        if len(standards) < 1:
            if log_failure or debug > 0:
                logerr("thread '%s': new_db_aqi_record [aqi] no standards defined. Define 'standards' in [aqi] section of station %s" % (self.name, self.station))
            if debug > 2:
                loginf("thread '%s': new_db_aqi_record standards %s" %(self.name, json.dumps(standards)))
            return False
        aq_dict = aqi_dict.get('aq', configobj.ConfigObj())
        if len(aq_dict) < 1:
            if log_failure or debug > 0:
                logerr("thread '%s': new_db_aqi_record [aq] not defined. Define [aq] in [aqi] section of station %s" % (self.name, self.station))
            if debug > 2:
                loginf("thread '%s': new_db_aqi_record aq_dict %s" %(self.name, json.dumps(aq_dict)))
            return False
        weather_dict = aqi_dict.get('weather', configobj.ConfigObj())
        if len(weather_dict) < 1:
            if log_failure or debug > 0:
                logerr("thread '%s': new_db_aqi_record [weather] not defined. Define [weather] in [aqi] section of station %s" % (self.name, self.station))
            if debug > 2:
                loginf("thread '%s': new_db_aqi_record weather_dict %s" % (self.name, json.dumps(weather_dict)))
            return False
        archive_dict = self.config_dict.get('StdArchive', configobj.ConfigObj())
        if len(archive_dict) < 1:
            if log_failure or debug > 0:
                logerr("thread '%s': new_db_aqi_record [StdArchive] not defined. Station %s" % (self.name, self.station))
            return False
        bindings_dict = self.config_dict.get('DataBindings', configobj.ConfigObj())
        if len(bindings_dict) < 1:
            if log_failure or debug > 0:
                logerr("thread '%s': new_db_aqi_record [DataBindings] not defined. Station %s" % (self.name, self.station))
            return False
        databases_dict = self.config_dict.get('Databases', configobj.ConfigObj())
        if len(databases_dict) < 1:
            if log_failure or debug > 0:
                logerr("thread '%s': new_db_aqi_record [Databases] not defined. Station %s" % (self.name, self.station))
            return False
        convert_dict = self.config_dict.get('StdConvert', configobj.ConfigObj())
        if len(convert_dict) < 1:
            if log_failure or debug > 0:
                logerr("thread '%s': new_db_aqi_record [StdConvert] not defined. Station %s" % (self.name, self.station))
            return False

        try:
            data_temp = dict()
            record = dict()
            record['dateTime'] = weeutil.weeutil.to_int(event.record['dateTime'])
            record['interval'] = weeutil.weeutil.to_int(event.record['interval'])
            record['usUnits'] = weewx.METRIC # TODO
            # calculation for each standard
            for standard in standards:
                aqi_config_dict = configobj.ConfigObj()
                aqi_config_dict['StdArchive'] = archive_dict
                aqi_config_dict['DataBindings'] = bindings_dict
                aqi_config_dict['Databases'] = databases_dict
                aqi_config_dict['StdConvert'] = convert_dict
                aqi_config_dict['standard'] = configobj.ConfigObj()
                aqi_config_dict['standard']['standard'] = aqi_dict.get(standard).get('standard')
                aqi_config_dict['aq'] = aq_dict
                aqi_config_dict['weather'] = weather_dict
                if debug > 2:
                    loginf("thread '%s': new_db_aqi_record calculate AQI standard %s" % (self.name, standard))
                aqi_calculator = Calculate("%s AQI %s" % (self.name, standard), self.engine, aqi_config_dict, event, debug=debug, log_success=log_success, log_failure=log_failure)
                aqi_calculator.new_archive_record()
                data_aqi = aqi_calculator.get_data_result()
                if debug > 2:
                    loginf("thread '%s': new_db_aqi_record calculate finished." % (self.name))

                for obs, values in AQIOBS.items():
                    if obs in data_aqi:
                        record[standard + '_' + obs] = data_aqi.get(obs)
                        data_temp[standard + '_' + obs] = (data_aqi.get(obs), values[1], values[2])

            aqi_calculator = None
            # save record to db
            self.dbm_aqi.addRecord(record)
            if log_success or debug > 0:
                loginf("thread '%s': new_db_aqi_record new record inserted." % (self.name))

            # delete records with dateTime older than ts
            max_age = weeutil.weeutil.to_int(aqi_dict.get('max_age', 8640000)) # default 100 Days
            if max_age is not None:
                ts = weeutil.weeutil.to_int(time.time() - max_age)
                sql = "delete from %s where dateTime < %d" % (self.dbm_aqi.table_name, ts)
                self.dbm_aqi.getSql(sql)
                try:
                    # sqlite databases need some help to stay small
                    self.dbm_aqi.getSql('vacuum')
                except Exception as e:
                    pass
                if log_success or debug > 0:
                    loginf("thread '%s': new_db_aqi_record table '%s' pruned." % (self.name, self.dbm_aq.table_name))

        except Exception as e:
            exception_output(self.name, e)
            return False

        try:
            self.lock.acquire()
            if self.debug > 2:
                logdbg("thread '%s': new_db_aqi_record data_temp %s" % (self.name, json.dumps(data_temp)))
            self.data_aqi = data_temp
            self.last_aqi_ts = weeutil.weeutil.to_int(time.time())
        finally:
            self.lock.release()

        if log_success or debug > 0:
            loginf("thread '%s': new_db_aqi_record finished." % (self.name))

        return True


    def new_result_from_temp(self, oldData):
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
        self.data_api = dict()
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
            aqi_enabled = weeutil.weeutil.to_bool(self.config.get('aqi', configobj.ConfigObj()).get('enable', False))

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
# Class OPENMETEOthread
#
# ============================================================================

class OPENMETEOthread(AbstractThread):

    # https://open-meteo.com/en/docs/air-quality-api
    # Mapping API field -> WeeWX field
    HOURLYOBS = {
        'ammonia': ('nh3', 'microgram_per_meter_cubed', 'group_concentration'),
        'carbon_monoxide': ('co', 'microgram_per_meter_cubed', 'group_concentration'),
        'nitrogen_dioxide': ('no2', 'microgram_per_meter_cubed', 'group_concentration'),
        'ozone': ('o3', 'microgram_per_meter_cubed', 'group_concentration'),
        'pm10': ('pm10_0', 'microgram_per_meter_cubed', 'group_concentration'),
        'pm2_5': ('pm2_5', 'microgram_per_meter_cubed', 'group_concentration'),
        'sulphur_dioxide': ('so2', 'microgram_per_meter_cubed', 'group_concentration'),
        'aerosol_optical_depth': ('aerosol_optical_depth', 'count', 'group_count'),
        'dust': ('dust', 'microgram_per_meter_cubed', 'group_concentration'),
        'uv_index': ('uvi', 'count', 'group_count'),
        'uv_index_clear_sky': ('uvi_clear_sky', 'count', 'group_count'),
        'alder_pollen': ('alder_pollen', 'grains_per_meter_cubed', 'group_concentration'),
        'birch_pollen': ('birch_pollen', 'grains_per_meter_cubed', 'group_concentration'),
        'grass_pollen': ('grass_pollen', 'grains_per_meter_cubed', 'group_concentration'),
        'mugwort_pollen': ('mugwort_pollen', 'grains_per_meter_cubed', 'group_concentration'),
        'olive_pollen': ('olive_pollen', 'grains_per_meter_cubed', 'group_concentration'),
        'ragweed_pollen': ('ragweed_pollen', 'grains_per_meter_cubed', 'group_concentration')
    }

    # API result contain no units for current_weather
    # Mapping API current_weather unit -> WeeWX unit
    HOURLYUNIT = {
        'time': 'unixtime',
        'pm10': u'μg/m³',
        'pm2_5': u'μg/m³',
        'carbon_monoxide': u'μg/m³',
        'nitrogen_dioxide': u'μg/m³',
        'sulphur_dioxide': u'μg/m³',
        'ozone': u'μg/m³',
        'aerosol_optical_depth': 'count',
        'dust': 'μg/m³',
        'uv_index': '',
        'uv_index_clear_sky': '',
        'ammonia': u'μg/m³',
        'alder_pollen': u'grains/m³',
        'birch_pollen': u'grains/m³',
        'grass_pollen': u'grains/m³',
        'mugwort_pollen': u'grains/m³',
        'olive_pollen': u'grains/m³',
        'european_aqi': 'EAQI',
        'european_aqi_pm2_5': 'EAQI',
        'european_aqi_pm10': 'EAQI',
        'european_aqi_no2': 'EAQI',
        'european_aqi_o3': 'EAQI',
        'european_aqi_so2': 'EAQI'
    }

    def get_hourly_obs(self):
        return OPENMETEOthread.HOURLYOBS

    def get_hourly_units(self):
        return OPENMETEOthread.HOURLYUNITS

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
        self.prefix = self.config.get('prefix', 'current_om_')
        self.source_id = self.config.get('source_id', 'om')
        self.interval_get = weeutil.weeutil.to_int(self.config.get('interval_get', 300))
        self.interval_push = weeutil.weeutil.to_int(self.config.get('interval_push', 30))
        self.expired = weeutil.weeutil.to_int(self.config.get('expired', 600))
        self.timezone = self.config.get('timezone', 'Europe/Berlin')
        self.hourly_obs = self.get_hourly_obs()
        self.config_dict = thread_dict.get('config_dict')
        self.engine = thread_dict.get('engine')

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
                    #raise weewx.ViolatedPrecondition("thread '%s': Could not get geodata for station '%s'" % (self.name, station))
                    return
            else:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': init configured station is not valid" % self.name)
                #raise weewx.ViolatedPrecondition("thread '%s': Configured station is not valid" % self.name)
                return

        self.data_result = dict()
        self.data_temp = dict()
        self.data_aqi = dict()
        self.last_get_ts = 0
        self.last_prepare_ts = 0
        self.last_aq_ts = 0
        self.last_aqi_ts = 0

        weewx.units.obs_group_dict.setdefault(self.prefix+'dateTime','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'generated','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'age','group_deltatime')
        weewx.units.obs_group_dict.setdefault(self.prefix+'expired','group_count')
        for opsapi, obsweewx in self.hourly_obs.items():
            obs = obsweewx[0]
            group = obsweewx[2]
            if group is not None:
                weewx.units.obs_group_dict.setdefault(self.prefix + obs, group)

        dbout_dict = self.config.get('db_out', configobj.ConfigObj())
        if weeutil.weeutil.to_bool(dbout_dict.get('enable', False)):
            aq_data_binding_name = dbout_dict.get('data_binding')
            if aq_data_binding_name is None:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': init aq data_binding is not configured!" % (self.name))
                return
            # open the aq data store
            self.dbm_aq = self.engine.db_binder.get_manager(data_binding=aq_data_binding_name, initialize=True)
            # confirm aqi schema
            dbcols = self.dbm_aq.connection.columnsOf(self.dbm_aq.table_name)
            dbm_dict = weewx.manager.get_manager_dict_from_config(self.config_dict, aq_data_binding_name)
            memcols = [x[0] for x in dbm_dict['schema']]
            if dbcols != memcols:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': aq store schema mismatch: %s != %s" % (self.name, dbcols, memcols))
                return
        elif self.log_success or self.debug > 0:
            loginf("thread '%s': init db_out is diabled. Enable it in the [db_out] section of station %s" %(self.name, self.station))

        aqi_dict = self.config.get('aqi', configobj.ConfigObj())
        if weeutil.weeutil.to_bool(aqi_dict.get('enable', False)):
            aqi_data_binding_name = aqi_dict.get('data_binding')
            if aq_data_binding_name is None:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': init aqi data_binding is not configured!" % (self.name))
                return
            # open the aq data store
            self.dbm_aqi = self.engine.db_binder.get_manager(data_binding=aqi_data_binding_name, initialize=True)
            # confirm aqi schema
            dbcols = self.dbm_aqi.connection.columnsOf(self.dbm_aqi.table_name)
            dbm_dict = weewx.manager.get_manager_dict_from_config(self.config_dict, aqi_data_binding_name)
            memcols = [x[0] for x in dbm_dict['schema']]
            if dbcols != memcols:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': aq store schema mismatch: %s != %s" % (self.name, dbcols, memcols))
                return
        elif self.log_success or self.debug > 0:
            loginf("thread '%s': init aqi is diabled. Enable it in the [aqi] section of station %s" %(self.name, self.station))

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


        baseurl = 'https://air-quality-api.open-meteo.com/v1/air-quality'

        # Geographical WGS84 coordinate of the location
        params = '?latitude=%s' % self.lat
        params += '&longitude=%s' % self.lon

        # timeformat iso8601 | unixtime. Default: iso8601
        params += '&timeformat=unixtime'

        # timezone
        # If format unixtime is selected, all time values are returned in UNIX epoch time in seconds. Please note
        # that all timestamp are in GMT+0! For daily values with unix timestamps, please apply utc_offset_seconds
        # again to get the correct date. Default: GMT
        #params += '&timezone=GMT'

        # Set a preference how grid-cells are selected. The default land finds a suitable grid-cell on land with
        # similar elevation to the requested coordinates using a 90-meter digital elevation model. sea prefers
        # grid-cells on sea. nearest selects the nearest possible grid-cell. Default: nearest
        #params += '&cell_selection=nearest'

        # Automatically combine both domains auto or specifically select the European cams_europe or global domain cams_global.
        params += '&domains=cams_europe'

        # The time interval to get aq data. A day must be specified as an ISO8601 date (e.g. 2022-06-30).
        today = datetime.datetime.today().strftime('%Y-%m-%d')
        params += '&start_date=%s' % today
        params += '&end_date=%s' % today

        # A list of weather variables which should be returned. Values can be comma separated,
        # or multiple &hourly= parameter in the URL can be used.
        # defined in HOURLYOBS
        params += '&hourly='+','.join([ii for ii in self.hourly_obs])

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
            logdbg("thread '%s': get_data_api api result %s" % (self.name, json.dumps(apidata)))

        # check results

        # check unit system
        if unitsystem is None and apidata.get('usUnits') is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api did not send unit system and it's not configured in section [api_in]" % (self.name))
            return False

        hourly_units = apidata.get('hourly_units')
        if hourly_units is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api sent no hourly_units data" % self.name)
            return False

        if apidata.get('hourly') is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api sent no hourly data" % self.name)
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

        # get the last hourly observation timestamp before the current time
        actts = weeutil.weeutil.to_int(time.time())
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

        if debug > 2:
            logdbg("thread '%s': get_data_api    ts now %s" % (self.name, str(actts)))
            logdbg("thread '%s': get_data_api    ts now %s" % (self.name, str( datetime.datetime.fromtimestamp(actts).strftime('%Y-%m-%d %H:%M:%S'))))
            logdbg("thread '%s': get_data_api ts hourly %s" % (self.name, str(obshts)))
            logdbg("thread '%s': get_data_api ts hourly %s" % (self.name, str( datetime.datetime.fromtimestamp(obshts).strftime('%Y-%m-%d %H:%M:%S'))))
            logdbg("thread '%s': get_data_api lat %s lon %s" % (self.name,latitude,longitude))

        # final timestamp
        self.data_temp['generated'] = (obshts, 'unix_epoch', 'group_time')

        # TODO: check this
        apiunitsystem = apidata.get('usUnits')
        if apiunitsystem is None:
            self.data_temp['usUnits'] = (unitsystem, None, None)
        else:
            self.data_temp['usUnits'] = (weeutil.weeutil.to_int(apiunitsystem), None, None)

        try:
            # get hourly aq data
            for obsapi, obsweewx in self.hourly_obs.items():
                obsname = self.prefix + str(obsweewx[0])
                if debug > 2:
                    logdbg("thread '%s': get_data_api hourly: weewx %s api %s obs %s" % (self.name, str(obsweewx[0]), str(obsapi), str(obsname)))
                obslist = apidata['hourly'].get(obsapi)
                if obslist is None:
                    if log_failure or debug > 0:
                        logerr("thread '%s': get_data_api hourly: No value for observation '%s' - '%s'" % (self.name, str(obsapi), str(obsname)))
                    self.data_temp[obsweewx[0]] = (None, obsweewx[1], obsweewx[2])
                    continue
                # Build a dictionary with timestamps as key and the corresponding values
                obsvals = dict(zip(htimelist, obslist))
                obsval = obsvals.get(obshts)
                if obsval is None:
                    if log_failure or debug > 0:
                        logwrn("thread '%s': get_data_api hourly: 'None' for observation %s - %s on timestamp %s" % (self.name, str(obsapi), str(obsname), str(obshts)))
                # WeeWX value with group?
                if obsweewx[2] is not None:
                    obsval = weeutil.weeutil.to_float(obsval)
                self.data_temp[obsweewx[0]] = (obsval, obsweewx[1], obsweewx[2])

                if debug > 2:
                    logdbg("thread '%s': API hourly: weewx=%s result=%s" % (self.name, str(obsweewx[0]), str(self.data_temp[obsweewx[0]])))

            if self.debug > 3:
                logdbg("thread '%s': get_data_api hourly: result %s" % (self.name, json.dumps(self.data_temp)))

            self.data_temp['altitude'] = (self.alt,'meter','group_altitude')
            self.data_temp['latitude'] = (latitude,'degree_compass','group_coordinate')
            self.data_temp['longitude'] = (longitude,'degree_compass','group_coordinate')
            self.data_temp['sourceUrl'] = (obfuscate_secrets(url), None, None)
            self.data_temp['generated'] = (weeutil.weeutil.to_int(time.time()), 'unix_epoch', 'group_time')

            if len(self.data_aqi) > 0 and time.time() - self.last_aqi_ts < 1300:
                self.data_temp.update(self.data_aqi)

            if log_success or debug > 0:
                loginf("thread '%s': get_data_api finished. Number of records processed: %d" % (self.name, len(self.data_temp)))
            if debug > 2:
                logdbg("thread '%s': get_data_api result %s" % (self.name, json.dumps(self.data_temp)))

            

        except Exception as e:
            exception_output(self.name, e)
        self.last_get_ts = weeutil.weeutil.to_int(time.time())
        return (len(self.data_temp) > 0)


# ============================================================================
#
# Class UBAthread
#
# stations: https://www.umweltbundesamt.de/api/air_data/v2/meta/json?lang=de&date_from=2023-07-24&date_to=2023-07-25&use=measure
# components: https://www.umweltbundesamt.de/api/air_data/v2/components/json?lang=de
# scopes: https://www.umweltbundesamt.de/api/air_data/v2/scopes/json?lang=de
# networks: https://www.umweltbundesamt.de/api/air_data/v2/networks/json
# settings: https://www.umweltbundesamt.de/api/air_data/v2/stationsettings/json?lang=de
# measurements: https://www.umweltbundesamt.de/api/air_data/v2/airquality/json?lang=de&station=506&date_from=2023-07-31&date_to=2023-08-31
# measurements: https://www.umweltbundesamt.de/api/air_data/v2/measures/json?date_from=2023-07-31&date_to=2023-08-01&ang=de&station=506&component=XX&scope=YY
#
# Homepage: https://www.umweltbundesamt.de/daten/luft/luftdaten/luftqualitaet/eJzrWJSSuMrIwMhY18BC18BwUUnmQrNFeakLFhWXLDY1MFuc4lYElTbXNTJdnBKSj6w6t4pjUW5y0-KcxJLTDh63GNNiHjsvzslLP-2gVviBgYGBEQBuNyJi
# API Docu: https://www.umweltbundesamt.de/daten/luft/luftdaten/doc
#
# ============================================================================

class UBAthread(AbstractThread):

    OBS = {
        '1': ('pm10_0', 'microgram_per_meter_cubed', 'group_concentration'),
        '2': ('co', 'microgram_per_meter_cubed', 'group_concentration'),
        '3': ('o3', 'microgram_per_meter_cubed', 'group_concentration'),
        '4': ('so2', 'microgram_per_meter_cubed', 'group_concentration'),
        '5': ('no2', 'microgram_per_meter_cubed', 'group_concentration'),
        '6': ('pm10_0_pb', 'microgram_per_meter_cubed', 'group_concentration'),
        '7': ('pm10_0_bap', 'nanogram_per_meter_cubed', 'group_concentration'),
        '8': ('c6h6', 'microgram_per_meter_cubed', 'group_concentration'),
        '9': ('pm2_5', 'microgram_per_meter_cubed', 'group_concentration'),
       '10': ('pm10_0_as', 'nanogram_per_meter_cubed', 'group_concentration'),
       '11': ('pm10_0_cd', 'nanogram_per_meter_cubed', 'group_concentration'),
       '12': ('pm10_0_ni', 'nanogram_per_meter_cubed', 'group_concentration')
    }

    def get_current_obs(self):
        return UBAthread.OBS

    def __init__(self, name, thread_dict, debug=0, log_success=False, log_failure=True):

        super(UBAthread, self).__init__(name=name, thread_dict=thread_dict, debug=debug, log_success=log_success, log_failure=log_failure)

        self.config = thread_dict.get('config')
        self.debug = weeutil.weeutil.to_int(self.config.get('debug', 0))
        self.log_success = weeutil.weeutil.to_bool(self.config.get('log_success', log_success))
        self.log_failure = weeutil.weeutil.to_bool(self.config.get('log_failure', log_failure))

        if self.debug > 0:
            logdbg("thread '%s': init started" % self.name)
        if self.debug > 2:
            logdbg("thread '%s': init config %s" % (self.name, json.dumps(self.config)))

        self.station = self.config.get('station', '506')
        self.provider = self.config.get('provider', 'uba')
        self.prefix = self.config.get('prefix', 'current_uba-'+self.station)
        self.source_id = self.config.get('source_id', 'uba-'+self.station)
        self.interval_get = weeutil.weeutil.to_int(self.config.get('interval_get', 300))
        self.interval_push = weeutil.weeutil.to_int(self.config.get('interval_push', 30))
        self.expired = weeutil.weeutil.to_int(self.config.get('expired', 600))
        self.timezone = self.config.get('timezone', 'Europe/Berlin')
        self.current_obs = self.get_current_obs()
        self.config_dict = thread_dict.get('config_dict')
        self.engine = thread_dict.get('engine')

        self.lat = weeutil.weeutil.to_float(self.config.get('latitude'))
        self.lon = weeutil.weeutil.to_float(self.config.get('longitude'))
        self.alt = weeutil.weeutil.to_float(self.config.get('altitude'))

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

        self.data_result = dict()
        self.data_temp = dict()
        self.data_aqi = dict()
        self.last_get_ts = 0
        self.last_prepare_ts = 0
        self.last_aq_ts = 0
        self.last_aqi_ts = 0

        self.station_dict = dict()
        self.network_dict = dict()
        self.types_dict = dict()
        self.settings_dict = dict()
        self.scopes_dict = dict()
        self.components_dict = dict()
        self.last_station_ts = 0

        weewx.units.obs_group_dict.setdefault(self.prefix+'dateTime','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'generated','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'age','group_deltatime')
        weewx.units.obs_group_dict.setdefault(self.prefix+'day','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'expired','group_count')
        for opsapi, obsweewx in self.current_obs.items():
            obs = obsweewx[0]
            group = obsweewx[2]
            if group is not None:
                weewx.units.obs_group_dict.setdefault(self.prefix + obs, group)

        dbout_dict = self.config.get('db_out', configobj.ConfigObj())
        if weeutil.weeutil.to_bool(dbout_dict.get('enable', False)):
            aq_data_binding_name = dbout_dict.get('data_binding')
            if aq_data_binding_name is None:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': init aq data_binding is not configured!" % (self.name))
                return
            # open the aq data store
            self.dbm_aq = self.engine.db_binder.get_manager(data_binding=aq_data_binding_name, initialize=True)
            # confirm aqi schema
            dbcols = self.dbm_aq.connection.columnsOf(self.dbm_aq.table_name)
            dbm_dict = weewx.manager.get_manager_dict_from_config(self.config_dict, aq_data_binding_name)
            memcols = [x[0] for x in dbm_dict['schema']]
            if dbcols != memcols:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': aq store schema mismatch: %s != %s" % (self.name, dbcols, memcols))
                return
        elif self.log_success or self.debug > 0:
            loginf("thread '%s': init db_out is diabled. Enable it in the [db_out] section of station %s" %(self.name, self.station))

        aqi_dict = self.config.get('aqi', configobj.ConfigObj())
        if weeutil.weeutil.to_bool(aqi_dict.get('enable', False)):
            aqi_data_binding_name = aqi_dict.get('data_binding')
            if aq_data_binding_name is None:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': init aqi data_binding is not configured!" % (self.name))
                return
            # open the aq data store
            self.dbm_aqi = self.engine.db_binder.get_manager(data_binding=aqi_data_binding_name, initialize=True)
            # confirm aqi schema
            dbcols = self.dbm_aqi.connection.columnsOf(self.dbm_aqi.table_name)
            dbm_dict = weewx.manager.get_manager_dict_from_config(self.config_dict, aqi_data_binding_name)
            memcols = [x[0] for x in dbm_dict['schema']]
            if dbcols != memcols:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': aq store schema mismatch: %s != %s" % (self.name, dbcols, memcols))
                return
        elif self.log_success or self.debug > 0:
            loginf("thread '%s': init aqi is diabled. Enable it in the [aqi] section of station %s" %(self.name, self.station))

        if self.log_success or self.debug > 0:
            loginf("thread '%s': init finished" % self.name)


    def getUbaData(self, debug=0, log_success=False, log_failure=True):
        """ download and pre-process UBA API Air Quality data """

        # Result Example:
        # result_dict {
            # "station": {
                # "id": "506",
                # "code": "DEBY072",
                # "name": "Tiefenbach/Altenschneeberg",
                # "city": "Tiefenbach, Gde.teil Altenschneeberg",
                # "synonym": "",
                # "activefrom": "1983-10-01",
                # "activeto": null,
                # "longitude": "12.5489",
                # "latitude": "49.4385",
                # "networkid": "2",
                # "settingid": "5",
                # "typeid": "1",
                # "networkcode": "BY",
                # "networkname": "Bayern",
                # "settingname": "l\u00e4ndlich regional",
                # "settingshortname": "l\u00e4ndlich",
                # "typename": "Hintergrund",
                # "street": "Flurst\u00fcck-Nr. 14",
                # "streetnr": "",
                # "zipcode": "93464",
                # "url": "https://www.umweltbundesamt.de/api/air_data/v2/meta/json?use=measure&lang=de&date_from=2023-07-30&date_to=2023-08-01"
            # },
            # "network": {
                # "id": "2",
                # "code": "BY",
                # "name": "Bayern"
            # },
            # "type": {
                # "id": "1",
                # "name": "Hintergrund",
                # "url": "https://www.umweltbundesamt.de/api/air_data/v2/stationtypes/json?lang=de"
            # },
            # "settings": {
                # "id": "5",
                # "name": "l\u00e4ndlich regional",
                # "shortname": "l\u00e4ndlich",
                # "url": "https://www.umweltbundesamt.de/api/air_data/v2/stationsettings/json?lang=de"
            # },
            # "data": {
                # "generatedMin": 1690887600,
                # "generatedMinISO": "2023-08-01T13:00:00+02:00",
                # "generatedMax": 1690887600,
                # "generatedMaxISO": "2023-08-01T13:00:00+02:00",
                # "components": {
                    # "1": {
                        # "value": 21,
                        # "started": 1690884000,
                        # "startedISO": "2023-08-01T12:00:00+02:00",
                        # "generated": 1690887600,
                        # "generatedISO": "2023-08-01T13:00:00+02:00",
                        # "component": {
                            # "id": "1",
                            # "code": "PM10",
                            # "symbol": "PM\u2081\u2080",
                            # "unit": "\u00b5g/m\u00b3",
                            # "name": "Feinstaub"
                        # },
                        # "scope": {
                            # "id": "6",
                            # "code": "1TMWGL",
                            # "timebase": "hour",
                            # "timescope": "3600",
                            # "timeismax": "0",
                            # "name": "Tagesmittel (st\u00fcndlich gleitend)"
                        # },
                        # "url": "https://www.umweltbundesamt.de/api/air_data/v2/measures/json?date_from=2023-07-30&date_to=2023-08-01&station=506&scope=6&component=1"
                    # },
                    # "3": {
                        # "value": 63,
                        # "started": 1690884000,
                        # "startedISO": "2023-08-01T12:00:00+02:00",
                        # "generated": 1690887600,
                        # "generatedISO": "2023-08-01T13:00:00+02:00",
                        # "component": {
                            # "id": "3",
                            # "code": "O3",
                            # "symbol": "O\u2083",
                            # "unit": "\u00b5g/m\u00b3",
                            # "name": "Ozon"
                        # },
                        # "scope": {
                            # "id": "2",
                            # "code": "1SMW",
                            # "timebase": "hour",
                            # "timescope": "3600",
                            # "timeismax": "0",
                            # "name": "Ein-Stunden-Mittelwert"
                        # },
                        # "url": "https://www.umweltbundesamt.de/api/air_data/v2/measures/json?date_from=2023-07-30&date_to=2023-08-01&station=506&scope=2&component=3"
                    # },
                    # "5": {
                        # "value": 4,
                        # "started": 1690884000,
                        # "startedISO": "2023-08-01T12:00:00+02:00",
                        # "generated": 1690887600,
                        # "generatedISO": "2023-08-01T13:00:00+02:00",
                        # "component": {
                            # "id": "5",
                            # "code": "NO2",
                            # "symbol": "NO\u2082",
                            # "unit": "\u00b5g/m\u00b3",
                            # "name": "Stickstoffdioxid"
                        # },
                        # "scope": {
                            # "id": "2",
                            # "code": "1SMW",
                            # "timebase": "hour",
                            # "timescope": "3600",
                            # "timeismax": "0",
                            # "name": "Ein-Stunden-Mittelwert"
                        # },
                        # "url": "https://www.umweltbundesamt.de/api/air_data/v2/measures/json?date_from=2023-07-30&date_to=2023-08-01&station=506&scope=2&component=5"
                    # },
                    # "9": {
                        # "value": 4,
                        # "started": 1690884000,
                        # "startedISO": "2023-08-01T12:00:00+02:00",
                        # "generated": 1690887600,
                        # "generatedISO": "2023-08-01T13:00:00+02:00",
                        # "component": {
                            # "id": "9",
                            # "code": "PM2",
                            # "symbol": "PM\u2082,\u2085",
                            # "unit": "\u00b5g/m\u00b3",
                            # "name": "Feinstaub"
                        # },
                        # "scope": {
                            # "id": "6",
                            # "code": "1TMWGL",
                            # "timebase": "hour",
                            # "timescope": "3600",
                            # "timeismax": "0",
                            # "name": "Tagesmittel (st\u00fcndlich gleitend)"
                        # },
                        # "url": "https://www.umweltbundesamt.de/api/air_data/v2/measures/json?date_from=2023-07-30&date_to=2023-08-01&station=506&scope=6&component=9"
                    # }
                # }
            # }
        # }

        if debug > 0:
            logdbg("thread '%s': getUbaData started" % (self.name))

        # Dates
        today_date = time.time()
        #yesterday_date = today_date-86400 # 1 day
        yesterday_date = today_date - 172800 #2 days, Period increased because sometimes no measurements were available.
        today_date = time.localtime(today_date)
        today_date = time.strftime('%Y-%m-%d', today_date)
        yesterday_date = time.localtime(yesterday_date)
        yesterday_date = time.strftime('%Y-%m-%d', yesterday_date)

        if time.time() - self.last_station_ts > 14400:
            # get Meta data
            baseurl = "https://www.umweltbundesamt.de/api/air_data/v2/meta/json?use=measure&time_from=1&time_to=24"
            params = '&lang=%s&date_from=%s&date_to=%s' % (self.lang, yesterday_date, today_date)
            url = baseurl + params

            if debug > 2:
                logdbg("thread '%s': getUbaData meta url %s" % (self.name, url))

            apidata = dict()
            try:
                response, code = request_api(self.name, url, debug=debug, log_success=log_success, log_failure=log_failure, text=False)
                if response is not None:
                    apidata = response
                else:
                    if log_failure or debug > 0:
                        logerr("thread '%s': getUbaData api did not send data" % self.name)
                    return None
            except Exception as e:
                exception_output(self.name, e)
                return None

            # "stations": [
              # "0: string - station id",
              # "1: string - station code",
              # "2: string - station name",
              # "3: string - station city",
              # "4: string - station synonym",
              # "5: string - station active from",
              # "6: string|null - station active to",
              # "7: string - station longitude",
              # "8: string - station latitude",
              # "9: string - network id",
              # "10: string - station setting id",
              # "11: string - station type id",
              # "12: string - network code",
              # "13: string - network name",
              # "14: string - station setting name",
              # "15: string - station setting short name",
              # "16: string - station type name",
              # "17: string - station street",
              # "18: string - station street nr",
              # "19: string - station zip code"
            # ],
            try:
                stations = apidata.get('stations')
                station = stations.get(self.station)
                #if debug > 2:
                logdbg("thread '%s': getUbaData station %s" % (self.name, json.dumps(station)))
                station_dict = dict()
                station_dict['id'] = station[0]
                station_dict['code'] = station[1]
                station_dict['name'] = station[2]
                station_dict['city'] = station[3]
                station_dict['synonym'] = station[4]
                station_dict['activefrom'] = station[5]
                station_dict['activeto'] = station[6]
                station_dict['longitude'] = station[7]
                station_dict['latitude'] = station[8]
                station_dict['networkid'] = station[9]
                station_dict['settingid'] = station[10]
                station_dict['typeid'] = station[11]
                station_dict['networkcode'] = station[12]
                station_dict['networkname'] = station[13]
                station_dict['settingname'] = station[14]
                station_dict['settingshortname'] = station[15]
                station_dict['typename'] = station[16]
                station_dict['street'] = station[17]
                station_dict['streetnr'] = station[18]
                station_dict['zipcode'] = station[19]
                station_dict['url'] = url
                if debug > 2:
                    logdbg("thread '%s': getUbaData station_dict %s" % (self.name, json.dumps(station_dict)))
                networkId = station[9]
                settingsId = station[10]
                typeId = station[11]
            except Exception as e:
                exception_output(self.name, e)
                return None

            # "components": [
              # "0: string - component id",
              # "1: string - component code",
              # "2: string - component symbol",
              # "3: string - component unit",
              # "4: string - component name"
            # ],
            try:
                components = apidata.get('components')
                components_dict = dict()
                for id, component in components.items():
                    components_dict[id] = dict()
                    components_dict[id]['id'] = component[0]
                    components_dict[id]['code'] = component[1]
                    components_dict[id]['symbol'] = component[2]
                    components_dict[id]['unit'] = component[3]
                    components_dict[id]['name'] = component[4]
                if debug > 5:
                    logdbg("thread '%s': getUbaData components %s" % (self.name, json.dumps(components_dict)))
            except Exception as e:
                exception_output(self.name, e)
                return None

            # "networks": [
              # "0: string - network id",
              # "1: string - network code",
              # "2: string - network name"
            # ],
            try:
                networks = apidata.get('networks')
                network = networks.get(networkId)
                network_dict = dict()
                network_dict['id'] = network[0]
                network_dict['code'] = network[1]
                network_dict['name'] = network[2]
                if debug > 2:
                    logdbg("thread '%s': getUbaData network %s" % (self.name, json.dumps(network_dict)))
            except Exception as e:
                exception_output(self.name, e)
                return None

            # "scopes": [
              # "0: string - scope id",
              # "1: string - scope code",
              # "2: string - scope time base",
              # "3: string - scope time scope",
              # "4: string - scope time is max",
              # "5: string - scope name"
            # ],
            try:
                scopes = apidata.get('scopes')
                scopes_dict = dict()
                for id, scope in scopes.items():
                    scopes_dict[id] = dict()
                    scopes_dict[id]['id'] = scope[0]
                    scopes_dict[id]['code'] = scope[1]
                    scopes_dict[id]['timebase'] = scope[2]
                    scopes_dict[id]['timescope'] = scope[3]
                    scopes_dict[id]['timeismax'] = scope[4]
                    scopes_dict[id]['name'] = scope[5]
                if debug > 2:
                    logdbg("thread '%s': getUbaData scopes %s" % (self.name, json.dumps(scopes_dict)))
            except Exception as e:
                exception_output(self.name, e)
                return None

            # "limits": {
              # "use = airquality|measure": [
                # "0: string - Id of scope",
                # "1: string - Id of component",
                # "2: string - Id of station",
                # "3: string - Minimum datetime of start (CET)",
                # "4: string - Maximum datetime of start (CET)"
            # ],
            # try:
                # limits = apidata.get('limits')
                # limits_dict = dict()
                # for limit, values in limits.items():
                    # if len(values) > 2 and values[2] == '506':
                        # limits_dict[limit] = dict()
                        # scopeId = values[0]
                        # componentId = values[1]
                        # limits_dict[limit]['scopes'] = dict()
                        # limits_dict[limit]['scopes'][scopeId] = scopes_dict.get(scopeId)
                        # limits_dict[limit]['components'] = dict()
                        # limits_dict[limit]['components'][componentId] = components_dict.get(componentId)
                        # limits_dict[limit]['minStart'] = values[3]
                        # limits_dict[limit]['maxStart'] = values[4]
                # if debug > 2:
                    # logdbg("thread '%s': getUbaData limits %s" % (self.name, json.dumps(limits_dict)))
            # except Exception as e:
                # exception_output(self.name, e)
                # return None

            # "xref": [
              # "0: string - Id of component",
              # "1: string - Id of scope",
              # "2: string - Flag if this combination of component and scope has a map",
              # "3: string - Flag if this combination of component and scope has an alternative map",
              # "4: string - Flag if this combination of component and scope is an hourly value"
            # ],
            # try:
                # xref = apidata.get('xref')
            # except Exception as e:
                # exception_output(self.name, e)
                # return None

            baseurl = "https://www.umweltbundesamt.de/api/air_data/v2/stationsettings/json"
            params = '?lang=%s' % (self.lang)
            url = baseurl + params

            if debug > 2:
                logdbg("thread '%s': getUbaData settings url %s" % (self.name, url))

            apidata = dict()
            try:
                response, code = request_api(self.name, url, debug=debug, log_success=log_success, log_failure=log_failure, text=False)
                if response is not None:
                    apidata = response
                else:
                    if log_failure or debug > 0:
                        logerr("thread '%s': getUbaData api did not send data" % self.name)
                    return False
            except Exception as e:
                exception_output(self.name, e)
                return False

            try:
                settings = apidata.get(settingsId)
                settings_dict = dict()
                settings_dict['id'] = settings[0]
                settings_dict['name'] = settings[1]
                settings_dict['shortname'] = settings[2]
                settings_dict['url'] = url
                if debug > 2:
                    logdbg("thread '%s': getUbaData settings %s" % (self.name, json.dumps(settings_dict)))
            except Exception as e:
                exception_output(self.name, e)
                return None

            baseurl = "https://www.umweltbundesamt.de/api/air_data/v2/stationtypes/json"
            params = '?lang=%s' % (self.lang)
            url = baseurl + params

            if debug > 2:
                logdbg("thread '%s': getUbaData types url %s" % (self.name, url))

            apidata = dict()
            try:
                response, code = request_api(self.name, url, debug=debug, log_success=log_success, log_failure=log_failure, text=False)
                if response is not None:
                    apidata = response
                else:
                    if log_failure or debug > 0:
                        logerr("thread '%s': getUbaData api did not send data" % self.name)
                    return None
            except Exception as e:
                exception_output(self.name, e)
                return None

            try:
                types = apidata.get(typeId)
                types_dict = dict()
                types_dict['id'] = types[0]
                types_dict['name'] = types[1]
                types_dict['url'] = url
                if debug > 2:
                    logdbg("thread '%s': getUbaData types %s" % (self.name, json.dumps(types_dict)))
            except Exception as e:
                exception_output(self.name, e)
                return None

            # All metadata loaded
            self.station_dict = dict()
            self.network_dict = dict()
            self.types_dict = dict()
            self.settings_dict = dict()
            self.scopes_dict = dict()
            self.components_dict = dict()

            self.components_dict = components_dict
            self.scopes_dict = scopes_dict
            self.station_dict[self.station] = station_dict
            self.network_dict[self.station] = network_dict
            if self.settings_dict.get(self.station) is None:
                self.settings_dict[self.station] = settings_dict
            if self.types_dict.get(self.station) is None:
                self.types_dict[self.station] = types_dict
            self.last_station_ts = weeutil.weeutil.to_int(time.time())

        # ----------------------------------------------
        # now load the data
        # ----------------------------------------------

        # Station 506/509 get components 1, 3, 5
        # baseurl = "https://www.umweltbundesamt.de/api/air_data/v2/airquality/json?time_from=1&time_to=24"
        # params = '&lang=%s&date_from=%s&date_to=%s&station=%s' % (self.lang, yesterday_date, today_date, self.station)

        # Station 506/509 get only component 9 or all component valid for the station
        # https://www.umweltbundesamt.de/api/air_data/v2/measures/json?date_from=2023-07-31&date_to=2023-08-01&ang=de&station=506&component=9
        baseurl = "https://www.umweltbundesamt.de/api/air_data/v2/measures/json?time_from=1&time_to=24"
        params = '&date_from=%s&date_to=%s&station=%s' % (yesterday_date, today_date, self.station)
        paracomp = '&scope=%s&component=%s'
        baseurl = baseurl + params

        # comp:scope
        # 1:6 (pm10)
        # 9:6 (pm2.5)
        # 3:2 (o3)
        # 5:2 (no2)

        data_dict = dict()
        generatedMax = 0
        generatedMin = weeutil.weeutil.to_int(time.time())
        for comp, values in self.components_dict.items():
            if comp in ('1', '9'):
                scope = '6'
            else:
                scope = '2'
            url = baseurl + (paracomp % (scope, comp))
            compcode = values.get('code', 'N/A')
            if debug > 2:
                logdbg("thread '%s': getUbaData trying to load values for '%s'" % (self.name, compcode))
            apidata = dict()
            try:
                response, code = request_api(self.name, url, debug=debug, log_success=log_success, log_failure=log_failure, text=False)
                if response is not None:
                    apidata = response
                else:
                    if log_failure or debug > 0:
                        logerr("thread '%s': getUbaData api did not send data" % self.name)
                    return None
            except Exception as e:
                exception_output(self.name, e)
                return None

            apidata = apidata.get('data')
            if apidata is None or len(apidata) < 1:
                if log_failure or debug > 0:
                    loginf("thread '%s': getUbaData api did not send data for '%s'" % (self.name, compcode))
                continue
            apidata = apidata.get(self.station)
            if apidata is None or len(apidata) < 1:
                if log_failure or debug > 0:
                    loginf("thread '%s': getUbaData api did not send station for '%s'" % (self.name, compcode))
                continue

            try:
                results = list(apidata.items())[-1]
                # "2023-08-01 08:00:00",
                # [
                    # 9,
                    # 6,
                    # 4,
                    # "2023-08-01 09:00:00",
                    # "1"
                # ]
                # "date start": [
                  # "component id",
                  # "scope id",
                  # "value",
                  # "date end",
                  # "index"
                # ]
                data_dict[comp] = dict()
                # start date
                # Datetime-Object from UBA date start (CET) = +01:00
                cet_date = datetime.datetime.strptime(results[0], '%Y-%m-%d %H:%M:%S')
                # UTC timestamp
                utc_started_ts = weeutil.weeutil.to_int(cet_date.timestamp()) + 3600 # +01:00 => +00:00

                # end date
                results = results[1]
                # Datetime-Object from UBA date end (CET) = +01:00
                cet_date = datetime.datetime.strptime(results[3], '%Y-%m-%d %H:%M:%S')
                # UTC timestamp
                utc_generated_ts = weeutil.weeutil.to_int(cet_date.timestamp()) + 3600 # +01:00 => +00:00
                generatedMax = max(utc_generated_ts, generatedMax)
                generatedMin = min(utc_generated_ts, generatedMin)

                # values
                data_dict[comp]['value'] = results[2]
                data_dict[comp]['started'] = utc_started_ts
                data_dict[comp]['startedISO'] = get_isodate_from_timestamp(utc_started_ts, 'Europe/Berlin')
                data_dict[comp]['generated'] = utc_generated_ts
                data_dict[comp]['generatedISO'] = get_isodate_from_timestamp(utc_generated_ts, 'Europe/Berlin')
                data_dict[comp]['component'] = self.components_dict.get(comp)
                data_dict[comp]['scope'] = self.scopes_dict.get(scope)
                data_dict[comp]['url'] = url
                if debug > 2:
                    logdbg("thread '%s': getUbaData comp '%s - %s' results %s " % (self.name, comp, compcode, json.dumps(data_dict[comp])))
            except Exception as e:
                exception_output(self.name, e)
                return None

        # ----------------------------------------------
        # now preprocessing data
        # ----------------------------------------------

        # Result Data
        result_dict = dict()
        try:
            result_dict['station'] = self.station_dict.get(self.station)
            result_dict['network'] = self.network_dict.get(self.station)
            result_dict['type'] = self.types_dict.get(self.station)
            result_dict['settings'] = self.settings_dict.get(self.station)
            result_dict['data'] = dict()
            result_dict['data']['generatedMin'] = generatedMin
            result_dict['data']['generatedMinISO'] = get_isodate_from_timestamp(generatedMin, 'Europe/Berlin')
            result_dict['data']['generatedMax'] = generatedMax
            result_dict['data']['generatedMaxISO'] = get_isodate_from_timestamp(generatedMax, 'Europe/Berlin')
            result_dict['data']['components'] = data_dict
            if debug > 2:
                logdbg("thread '%s': getUbaData result_dict %s " % (self.name, json.dumps(result_dict)))
        except Exception as e:
            exception_output(self.name, e)
            return None
        return result_dict

    def get_data_api(self):
        """ process UBA API Air Quality data """

        self.data_temp = dict()
        apiin_dict = self.config.get('api_in', configobj.ConfigObj())
        debug = weeutil.weeutil.to_int(apiin_dict.get('debug', self.debug))
        log_success = weeutil.weeutil.to_bool(apiin_dict.get('log_success', self.log_success))
        log_failure = weeutil.weeutil.to_bool(apiin_dict.get('log_failure', self.log_failure))
        attempts_max = weeutil.weeutil.to_int(apiin_dict.get('attempts_max', 1))
        attempts_wait = weeutil.weeutil.to_int(apiin_dict.get('attempts_wait', 10))

        if not weeutil.weeutil.to_bool(apiin_dict.get('enable', False)):
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api is diabled. Enable it in the [api_in] section of station %s" % (self.name, self.station))
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

        apidata = dict()
        attempts = 0
        try:
            while attempts <= attempts_max:
                attempts += 1
                response = self.getUbaData(debug = debug,
                                           log_success = log_success,
                                           log_failure = log_failure)
                if response is not None:
                    apidata = response
                    attempts = attempts_max + 1
                elif attempts <= attempts_max:
                    if log_failure or debug > 0:
                        loginf("thread '%s': get_data_api getUbaData with error next try (%d/%d) in %d seconds" % (self.name, attempts, attempts_max, attempts_wait))
                    time.sleep(attempts_wait)
                elif log_failure or debug > 0:
                    logerr("thread '%s': get_data_api getUbaData did not send data" % self.name)
                    return False
        except Exception as e:
            exception_output(self.name, e)
            return False

        if debug > 2:
            logdbg("thread '%s': get_data_api getUbaData result %s" % (self.name, json.dumps(apidata)))

        # check results
        data_station = apidata.get('station')
        if data_station is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api getUbaData did not send 'station' data" % self.name)
            return False
        data_result = apidata.get('data')
        if data_result is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api getUbaData did not send 'data' data" % (self.name))
            return False
        components_result = data_result.get('components')
        if data_result is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api getUbaData did not send 'components' data" % (self.name))
            return False

        # check unit system
        if unitsystem is None and data_result.get('usUnits') is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api getUbaData did not send unit system and it's not configured in section [api_in]" % (self.name))
            return False

        self.data_temp['dateTime'] = (weeutil.weeutil.to_int(time.time()), 'unix_epoch', 'group_time')
        self.data_temp['generated'] = (weeutil.weeutil.to_int(data_result.get('generatedMax', time.time())), 'unix_epoch', 'group_time')

        try:
            for obs, values in self.current_obs.items():
                if components_result.get(obs) is not None:
                    val = components_result[obs].get('value')
                    if values[2] is not None: #group
                        val = weeutil.weeutil.to_float(val)
                    self.data_temp[values[0]] = (val, values[1], values[2])
                    url = components_result[obs].get('url')
                    self.data_temp['dataUrl_'+values[0]] = (obfuscate_secrets(url), None, None)
        except Exception as e:
            exception_output(self.name, e)
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api getUbaData sent data in an unknown format. Station %s" % (self.name, str(self.station)))
            self.data_temp = dict()
            return False

        # TODO: check this
        apiunitsystem = apidata.get('usUnits')
        if apiunitsystem is None:
            self.data_temp['usUnits'] = (unitsystem, None, None)
        else:
            self.data_temp['usUnits'] = (weeutil.weeutil.to_int(apiunitsystem), None, None)

        try:
            self.data_temp['altitude'] = (data_station.get('altitude', self.alt), 'meter','group_altitude')
            self.data_temp['latitude'] = (data_station.get('latitude', self.lat), 'degree_compass','group_coordinate')
            self.data_temp['longitude'] = (data_station.get('longitude', self.lon), 'degree_compass','group_coordinate')
            self.data_temp['metaUrl'] = (obfuscate_secrets(data_station.get('url', '')), None, None)
            self.data_temp['settingsUrl'] = (obfuscate_secrets(apidata.get('settings', dict()).get('url', 'N/A')), None, None)
            self.data_temp['typesUrl'] = (obfuscate_secrets(apidata.get('type', dict()).get('url', 'N/A')), None, None)
        except Exception as e:
            exception_output(self.name, e)
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api getUbaData sent data in an unknown format. Station %s" % (self.name, str(self.station)))
            self.data_temp = dict()
            return False

        if len(self.data_aqi) > 0 and time.time() - self.last_aqi_ts < 1300:
            self.data_temp.update(self.data_aqi)

        if log_success or debug > 0:
            loginf("thread '%s': get_data_api finished. Number of records processed: %d" % (self.name, len(self.data_temp)))
        if debug > 2:
            logdbg("thread '%s': get_data_api result %s" % (self.name, json.dumps(self.data_temp)))
        self.last_get_ts = weeutil.weeutil.to_int(time.time())
        return (len(self.data_temp) > 0)


# ============================================================================
#
# Class PWSthread
#
# ============================================================================

class PWSthread(AbstractThread):

    OBS = {
        'dateTime': ('generated', 'unix_epoch', 'group_time'),
        'airrohr_pm2_5': ('pm2_5', 'microgram_per_meter_cubed', 'group_concentration'),
        'airrohr_pm10_0': ('pm10_0', 'microgram_per_meter_cubed', 'group_concentration'),
        'airrohr_dht22_outTemp': ('dht22_outTemp', 'degree_C', 'group_temperature'),
        'airrohr_dht22_outHumidity': ('dht22_outHumidity', 'percent', 'group_percent'),
        'airrohr_bme280_outTemp': ('bme280_outTemp', 'degree_C', 'group_temperature'),
        'airrohr_bme280_outHumidity': ('bme280_outHumidity', 'percent', 'group_percent'),
        'airrohr_pressure': ('pressure', 'hPa', 'group_pressure'),
        'airrohr_signal_level': ('signal_level', 'count', 'group_count'),
        'airrohr_signal_percent': ('sig_percent', 'percent', 'group_percent'),
        'airrohr_signal_ecowitt': ('sig', 'count', 'group_count')
    }

    ADDOBS = {
        'pws' : 'pws',
        'pws-aeris' : 'aeris',
        'pws-om' : 'om',
        'pws-owm' : 'owm',
        'pws-506' : 'uba-506',
        'pws-509' : 'uba-509',
    }

    def get_current_obs(self):
        return PWSthread.OBS

    def get_add_obs(self):
        return PWSthread.ADDOBS

    def __init__(self, name, thread_dict, debug=0, log_success=False, log_failure=True, threads=None):

        super(PWSthread, self).__init__(name=name, thread_dict=thread_dict, debug=debug, log_success=log_success, log_failure=log_failure, threads=threads)

        self.config = thread_dict.get('config')
        self.debug = weeutil.weeutil.to_int(self.config.get('debug', 0))
        self.log_success = weeutil.weeutil.to_bool(self.config.get('log_success', log_success))
        self.log_failure = weeutil.weeutil.to_bool(self.config.get('log_failure', log_failure))

        if self.debug > 0:
            logdbg("thread '%s': init started" % self.name)
        if self.debug > 2:
            logdbg("thread '%s': init config %s" % (self.name, json.dumps(self.config)))

        self.station = self.config.get('station', 'here')
        self.provider = self.config.get('provider', 'pws')
        self.prefix = self.config.get('prefix', 'current_pws_')
        self.source_id = self.config.get('source_id', 'pws')
        self.interval_get = weeutil.weeutil.to_int(self.config.get('interval_get', 300))
        self.interval_push = weeutil.weeutil.to_int(self.config.get('interval_push', 30))
        self.expired = weeutil.weeutil.to_int(self.config.get('expired', 600))
        self.timezone = self.config.get('timezone', 'Europe/Berlin')
        self.current_obs = self.get_current_obs()
        self.add_obs = self.get_add_obs()
        self.threads = threads
        self.config_dict = thread_dict.get('config_dict')
        self.engine = thread_dict.get('engine')

        self.lat = weeutil.weeutil.to_float(self.config.get('latitude'))
        self.lon = weeutil.weeutil.to_float(self.config.get('longitude'))
        self.alt = weeutil.weeutil.to_float(self.config.get('altitude'))

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

        self.data_result = dict()
        self.data_temp = dict()
        self.data_aqi = dict()
        self.last_get_ts = 0
        self.last_prepare_ts = 0
        self.last_aq_ts = 0
        self.last_aqi_ts = 0

        weewx.units.obs_group_dict.setdefault(self.prefix+'dateTime','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'generated','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'age','group_deltatime')
        weewx.units.obs_group_dict.setdefault(self.prefix+'day','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'expired','group_count')
        for opsapi, obsweewx in self.current_obs.items():
            obs = obsweewx[0]
            group = obsweewx[2]
            if group is not None:
                weewx.units.obs_group_dict.setdefault(self.prefix + obs, group)

        dbout_dict = self.config.get('db_out', configobj.ConfigObj())
        if weeutil.weeutil.to_bool(dbout_dict.get('enable', False)):
            aq_data_binding_name = dbout_dict.get('data_binding')
            if aq_data_binding_name is None:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': init aq data_binding is not configured!" % (self.name))
                return
            # open the aq data store
            self.dbm_aq = self.engine.db_binder.get_manager(data_binding=aq_data_binding_name, initialize=True)
            # confirm aqi schema
            dbcols = self.dbm_aq.connection.columnsOf(self.dbm_aq.table_name)
            dbm_dict = weewx.manager.get_manager_dict_from_config(self.config_dict, aq_data_binding_name)
            memcols = [x[0] for x in dbm_dict['schema']]
            if dbcols != memcols:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': aq store schema mismatch: %s != %s" % (self.name, dbcols, memcols))
                return
        elif self.log_success or self.debug > 0:
            loginf("thread '%s': init db_out is diabled. Enable it in the [db_out] section of station %s" %(self.name, self.station))

        aqi_dict = self.config.get('aqi', configobj.ConfigObj())
        if weeutil.weeutil.to_bool(aqi_dict.get('enable', False)):
            aqi_data_binding_name = aqi_dict.get('data_binding')
            if aq_data_binding_name is None:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': init aqi data_binding is not configured!" % (self.name))
                return
            # open the aq data store
            self.dbm_aqi = self.engine.db_binder.get_manager(data_binding=aqi_data_binding_name, initialize=True)
            # confirm aqi schema
            dbcols = self.dbm_aqi.connection.columnsOf(self.dbm_aqi.table_name)
            dbm_dict = weewx.manager.get_manager_dict_from_config(self.config_dict, aqi_data_binding_name)
            memcols = [x[0] for x in dbm_dict['schema']]
            if dbcols != memcols:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': aq store schema mismatch: %s != %s" % (self.name, dbcols, memcols))
                return
        elif self.log_success or self.debug > 0:
            loginf("thread '%s': init aqi is diabled. Enable it in the [aqi] section of station %s" %(self.name, self.station))

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

        baseurl = 'https://api.weiherhammer-wetter.de/v1/airrohr/'

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
            logdbg("thread '%s': get_data_api api result %s" % (self.name, json.dumps(apidata)))

        try:
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

            # Should data from other providers be added?
            other_source_id = self.add_obs.get(self.source_id)
            if other_source_id != self.source_id:
                threads = self.threads
                for thread_name in threads:
                    # get thread config. if total is False continue with next thread
                    tconfig = threads[thread_name].get_config()
                    if tconfig.get('source_id') == other_source_id:
                        # get collected data
                        data = None
                        if threads[thread_name].get_last_aqi_ts() > 0:
                            data = threads[thread_name].get_data_result()
                        elif threads[thread_name].get_last_prepare_ts() > 0:
                            data = threads[thread_name].get_data_temp()
                        else:
                            # Thread has not yet generated any usable data.
                            continue
                        if len(data) > 0:
                            for obs, values in AQOBS_EU.items():
                                if obs == 'pm2_5' or obs =='pm10_0':
                                    continue # measured by PWS
                                if obs in data:
                                    self.data_temp[obs] = data.get(obs)
                        elif log_failure or debug > 0:
                            logerr("thread '%s': get_data_api Thread '%s' has no valid result data" % (self.name, thread_name))
                            if debug > 2:
                                logerr("thread '%s': get_data_api Thread '%s' result_data %s" % (self.name, thread_name, json.dumps(data)))
                        break

            self.data_temp['dateTime'] = (weeutil.weeutil.to_int(time.time()), 'unix_epoch', 'group_time')
            self.data_temp['altitude'] = (self.alt,'meter','group_altitude')
            self.data_temp['latitude'] = (self.lat,'degree_compass','group_coordinate')
            self.data_temp['longitude'] = (self.lon,'degree_compass','group_coordinate')
            self.data_temp['sourceUrl'] = (obfuscate_secrets(url), None, None)

            if len(self.data_aqi) > 0 and time.time() - self.last_aqi_ts < 1300:
                self.data_temp.update(self.data_aqi)

        except Exception as e:
            exception_output(self.name, e)
            return False

        if log_success or debug > 0:
            loginf("thread '%s': get_data_api finished. Number of records processed: %d" % (self.name, len(self.data_temp)))
        if debug > 2:
            logdbg("thread '%s': get_data_api result %s" % (self.name, json.dumps(self.data_temp)))
        self.last_get_ts = weeutil.weeutil.to_int(time.time())
        return (len(self.data_temp) > 0)


# ============================================================================
#
# Class AERISthread
#
# ============================================================================

class AERISthread(AbstractThread):

    OBS = {
        'o3': ('o3', 'microgram_per_meter_cubed', 'group_concentration'),
        'pm2.5': ('pm2_5', 'microgram_per_meter_cubed', 'group_concentration'),
        'pm10': ('pm10_0', 'microgram_per_meter_cubed', 'group_concentration'),
        'co': ('co', 'microgram_per_meter_cubed', 'group_concentration'),
        'no2': ('no2', 'microgram_per_meter_cubed', 'group_concentration'),
        'so2': ('so2', 'microgram_per_meter_cubed', 'group_concentration')
    }

    def get_current_obs(self):
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
        self.prefix = self.config.get('prefix', 'current_aeris_')
        self.source_id = self.config.get('source_id', 'aeris')
        self.interval_get = weeutil.weeutil.to_int(self.config.get('interval_get', 300))
        self.interval_push = weeutil.weeutil.to_int(self.config.get('interval_push', 30))
        self.expired = weeutil.weeutil.to_int(self.config.get('expired', 600))
        self.timezone = self.config.get('timezone', 'Europe/Berlin')
        self.current_obs = self.get_current_obs()
        self.config_dict = thread_dict.get('config_dict')
        self.engine = thread_dict.get('engine')

        self.lat = weeutil.weeutil.to_float(self.config.get('latitude'))
        self.lon = weeutil.weeutil.to_float(self.config.get('longitude'))
        self.alt = weeutil.weeutil.to_float(self.config.get('altitude'))

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

        self.data_result = dict()
        self.data_temp = dict()
        self.data_aqi = dict()
        self.last_get_ts = 0
        self.last_prepare_ts = 0
        self.last_aq_ts = 0
        self.last_aqi_ts = 0

        weewx.units.obs_group_dict.setdefault(self.prefix+'dateTime','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'generated','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'age','group_deltatime')
        weewx.units.obs_group_dict.setdefault(self.prefix+'day','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'expired','group_count')
        for opsapi, obsweewx in self.current_obs.items():
            obs = obsweewx[0]
            group = obsweewx[2]
            if group is not None:
                weewx.units.obs_group_dict.setdefault(self.prefix + obs, group)

        dbout_dict = self.config.get('db_out', configobj.ConfigObj())
        if weeutil.weeutil.to_bool(dbout_dict.get('enable', False)):
            aq_data_binding_name = dbout_dict.get('data_binding')
            if aq_data_binding_name is None:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': init aq data_binding is not configured!" % (self.name))
                return
            # open the aq data store
            self.dbm_aq = self.engine.db_binder.get_manager(data_binding=aq_data_binding_name, initialize=True)
            # confirm aqi schema
            dbcols = self.dbm_aq.connection.columnsOf(self.dbm_aq.table_name)
            dbm_dict = weewx.manager.get_manager_dict_from_config(self.config_dict, aq_data_binding_name)
            memcols = [x[0] for x in dbm_dict['schema']]
            if dbcols != memcols:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': aq store schema mismatch: %s != %s" % (self.name, dbcols, memcols))
                return
        elif self.log_success or self.debug > 0:
            loginf("thread '%s': init db_out is diabled. Enable it in the [db_out] section of station %s" %(self.name, self.station))

        aqi_dict = self.config.get('aqi', configobj.ConfigObj())
        if weeutil.weeutil.to_bool(aqi_dict.get('enable', False)):
            aqi_data_binding_name = aqi_dict.get('data_binding')
            if aq_data_binding_name is None:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': init aqi data_binding is not configured!" % (self.name))
                return
            # open the aq data store
            self.dbm_aqi = self.engine.db_binder.get_manager(data_binding=aqi_data_binding_name, initialize=True)
            # confirm aqi schema
            dbcols = self.dbm_aqi.connection.columnsOf(self.dbm_aqi.table_name)
            dbm_dict = weewx.manager.get_manager_dict_from_config(self.config_dict, aqi_data_binding_name)
            memcols = [x[0] for x in dbm_dict['schema']]
            if dbcols != memcols:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': aq store schema mismatch: %s != %s" % (self.name, dbcols, memcols))
                return
        elif self.log_success or self.debug > 0:
            loginf("thread '%s': init aqi is diabled. Enable it in the [aqi] section of station %s" %(self.name, self.station))

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

        baseurl = 'https://api.aerisapi.com/airquality/%s,%s?format=json&client_id=%s&client_secret=%s' % (str(self.lat), str(self.lon), api_id, api_secret)
        params = '&fields=periods.timestamp,periods.pollutants.type,periods.pollutants.valueUGM3'
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
            logdbg("thread '%s': get_data_api api result %s" % (self.name, json.dumps(apidata)))

        try:
            apidata = apidata['response'][0]['periods'][0]
        except (KeyError, IndexError):
            exception_output(self.name, e)
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api sent values in an unknown format" % (self.name))
        except Exception as e:
            exception_output(self.name, e)
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api sent values in an unknown format" % (self.name))
            return False

        # check unit system
        if unitsystem is None and apidata.get('usUnits') is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api did not send unit system and it's not configured in section [api_in]" % (self.name))
            return False

        # TODO: check this
        apiunitsystem = apidata.get('usUnits')
        if apiunitsystem is None:
            self.data_temp['usUnits'] = (unitsystem, None, None)
        else:
            self.data_temp['usUnits'] = (weeutil.weeutil.to_int(apiunitsystem), None, None)

        # get current data
        try:
            self.data_temp['generated'] = (weeutil.weeutil.to_int(apidata.get('timestamp')), 'unix_epoch', 'group_time')
        except (KeyError, IndexError):
            exception_output(self.name, e)
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api sent values in an unknown format" % (self.name))
            return False
        except Exception as e:
            exception_output(self.name, e)
            return False

        try:
            apidata = apidata.get('pollutants')
            for pollutant in apidata:
                apiobs = pollutant.get('type')
                obs = self.current_obs[apiobs][0]
                unit = self.current_obs[apiobs][1]
                group = self.current_obs[apiobs][2]
                val = weeutil.weeutil.to_float(pollutant.get('valueUGM3'))
                self.data_temp[obs] = (val, unit, group)
        except (KeyError, IndexError):
            exception_output(self.name, e)
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api sent values in an unknown format" % (self.name))
            return False
        except Exception as e:
            exception_output(self.name, e)
            return False

        self.data_temp['dateTime'] = (weeutil.weeutil.to_int(time.time()), 'unix_epoch', 'group_time')
        self.data_temp['altitude'] = (self.alt,'meter','group_altitude')
        self.data_temp['latitude'] = (self.lat,'degree_compass','group_coordinate')
        self.data_temp['longitude'] = (self.lon,'degree_compass','group_coordinate')
        self.data_temp['sourceUrl'] = (obfuscate_secrets(url), None, None)

        if len(self.data_aqi) > 0 and time.time() - self.last_aqi_ts < 1300:
            self.data_temp.update(self.data_aqi)

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

    OBS = {
        'co': ('co', 'microgram_per_meter_cubed', 'group_concentration'),
        'no': ('no', 'microgram_per_meter_cubed', 'group_concentration'),
        'no2': ('no2', 'microgram_per_meter_cubed', 'group_concentration'),
        'o3': ('o3', 'microgram_per_meter_cubed', 'group_concentration'),
        'so2': ('so2', 'microgram_per_meter_cubed', 'group_concentration'),
        'pm2_5': ('pm2_5', 'microgram_per_meter_cubed', 'group_concentration'),
        'pm10': ('pm10_0', 'microgram_per_meter_cubed', 'group_concentration'),
        'nh3': ('nh3', 'microgram_per_meter_cubed', 'group_concentration'),
    }


    def get_current_obs(self):
        return OPENWEATHERthread.OBS


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
        self.prefix = self.config.get('prefix', 'current_owm_')
        self.source_id = self.config.get('source_id', 'owm')
        self.interval_get = weeutil.weeutil.to_int(self.config.get('interval_get', 300))
        self.interval_push = weeutil.weeutil.to_int(self.config.get('interval_push', 30))
        self.expired = weeutil.weeutil.to_int(self.config.get('expired', 600))
        self.timezone = self.config.get('timezone', 'Europe/Berlin')
        self.current_obs = self.get_current_obs()
        self.config_dict = thread_dict.get('config_dict')
        self.engine = thread_dict.get('engine')

        self.lat = weeutil.weeutil.to_float(self.config.get('latitude'))
        self.lon = weeutil.weeutil.to_float(self.config.get('longitude'))
        self.alt = weeutil.weeutil.to_float(self.config.get('altitude'))

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

        self.data_result = dict()
        self.data_temp = dict()
        self.data_aqi = dict()
        self.last_get_ts = 0
        self.last_prepare_ts = 0
        self.last_aq_ts = 0
        self.last_aqi_ts = 0

        weewx.units.obs_group_dict.setdefault(self.prefix+'dateTime','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'generated','group_time')
        weewx.units.obs_group_dict.setdefault(self.prefix+'age','group_deltatime')
        weewx.units.obs_group_dict.setdefault(self.prefix+'day','group_count')
        weewx.units.obs_group_dict.setdefault(self.prefix+'expired','group_count')
        for opsapi, obsweewx in self.current_obs.items():
            obs = obsweewx[0]
            group = obsweewx[2]
            if group is not None:
                weewx.units.obs_group_dict.setdefault(self.prefix + obs, group)

        dbout_dict = self.config.get('db_out', configobj.ConfigObj())
        if weeutil.weeutil.to_bool(dbout_dict.get('enable', False)):
            aq_data_binding_name = dbout_dict.get('data_binding')
            if aq_data_binding_name is None:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': init aq data_binding is not configured!" % (self.name))
                return
            # open the aq data store
            self.dbm_aq = self.engine.db_binder.get_manager(data_binding=aq_data_binding_name, initialize=True)
            # confirm aqi schema
            dbcols = self.dbm_aq.connection.columnsOf(self.dbm_aq.table_name)
            dbm_dict = weewx.manager.get_manager_dict_from_config(self.config_dict, aq_data_binding_name)
            memcols = [x[0] for x in dbm_dict['schema']]
            if dbcols != memcols:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': aq store schema mismatch: %s != %s" % (self.name, dbcols, memcols))
                return
        elif self.log_success or self.debug > 0:
            loginf("thread '%s': init db_out is diabled. Enable it in the [db_out] section of station %s" %(self.name, self.station))

        aqi_dict = self.config.get('aqi', configobj.ConfigObj())
        if weeutil.weeutil.to_bool(aqi_dict.get('enable', False)):
            aqi_data_binding_name = aqi_dict.get('data_binding')
            if aq_data_binding_name is None:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': init aqi data_binding is not configured!" % (self.name))
                return
            # open the aq data store
            self.dbm_aqi = self.engine.db_binder.get_manager(data_binding=aqi_data_binding_name, initialize=True)
            # confirm aqi schema
            dbcols = self.dbm_aqi.connection.columnsOf(self.dbm_aqi.table_name)
            dbm_dict = weewx.manager.get_manager_dict_from_config(self.config_dict, aqi_data_binding_name)
            memcols = [x[0] for x in dbm_dict['schema']]
            if dbcols != memcols:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': aq store schema mismatch: %s != %s" % (self.name, dbcols, memcols))
                return
        elif self.log_success or self.debug > 0:
            loginf("thread '%s': init aqi is diabled. Enable it in the [aqi] section of station %s" %(self.name, self.station))

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

        baseurl = 'https://api.openweathermap.org/data/2.5/air_pollution?lat=%s&lon=%s&units=metric&lang=%s&appid=%s' % (str(self.lat), str(self.lon), self.lang, api_id)

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
        data = apidata.get('coord')
        if data is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api did not send 'coord' data" % self.name)
            return False
        self.data_temp['latitude'] = (data.get('lat', self.lat),'degree_compass','group_coordinate')
        self.data_temp['longitude'] = (data.get('lon', self.lon),'degree_compass','group_coordinate')

        try:
            data = apidata['list'][0]
        except (KeyError, IndexError):
            exception_output(self.name, e)
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api sent values in an unknown format" % (self.name))
        except Exception as e:
            exception_output(self.name, e)
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api sent values in an unknown format" % (self.name))
            return False

        generated = data.get('dt')
        if generated is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api did not send 'dt' data" % self.name)
            return False

        components = data.get('components')
        if components is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api did not send 'components' data" % self.name)
            return False

        # check unit system
        if unitsystem is None and components.get('usUnits') is None:
            if log_failure or debug > 0:
                logerr("thread '%s': get_data_api api did not send unit system and it's not configured in section [api_in]" % (self.name))
            return False

        # TODO: check this
        apiunitsystem = components.get('usUnits')
        if apiunitsystem is None:
            self.data_temp['usUnits'] = (unitsystem, None, None)
        else:
            self.data_temp['usUnits'] = (weeutil.weeutil.to_int(apiunitsystem), None, None)

        # get current data
        self.data_temp['dateTime'] = (weeutil.weeutil.to_int(time.time()), 'unix_epoch', 'group_time')
        self.data_temp['generated'] = (weeutil.weeutil.to_int(generated), 'unix_epoch', 'group_time')

        for obsapi, obsweewx in self.current_obs.items():
            obsname = self.prefix + str(obsweewx[0])
            obsval = components.get(obsapi)
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
        self.data_temp['sourceUrl'] = (obfuscate_secrets(url), None, None)

        if len(self.data_aqi) > 0 and time.time() - self.last_aqi_ts < 1300:
            self.data_temp.update(self.data_aqi)

        if log_success or debug > 0:
            loginf("thread '%s': get_data_api finished. Number of records processed: %d" % (self.name, len(self.data_temp)))
        if debug > 2:
            logdbg("thread '%s': get_data_api result %s" % (self.name, json.dumps(self.data_temp)))
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

        self.station = self.config.get('station', 'here')
        self.provider = self.config.get('provider', 'total')
        self.model = self.config.get('model', 'total')
        self.interval_get = weeutil.weeutil.to_int(self.config.get('interval_get', 300))
        self.interval_push = weeutil.weeutil.to_int(self.config.get('interval_push', 30))
        self.expired = weeutil.weeutil.to_int(self.config.get('expired', 600))
        self.source_id = None #self.config.get('source_id', 'total')
        self.first_delay = weeutil.weeutil.to_int(self.config.get('first_delay', 300))
        self.icon_path_belchertown = self.config.get('icon_path_belchertown', '')
        self.timezone = self.config.get('timezone', 'Europe/Berlin')
        self.threads = threads
        self.config_dict = thread_dict.get('config_dict')
        self.engine = thread_dict.get('engine')

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

        self.data_result = dict()
        self.data_temp = dict()
        self.data_aqi = dict()
        self.last_get_ts = 0
        self.last_prepare_ts = 0
        self.last_aq_ts = 0
        self.last_aqi_ts = 0

        if self.first_delay > 0:
            if self.debug > 0:
                logdbg("thread '%s': init waiting (%d s) for the first threads data completions.." % (self.name, self.first_delay))
            time.sleep(self.first_delay)

        dbout_dict = self.config.get('db_out', configobj.ConfigObj())
        if weeutil.weeutil.to_bool(dbout_dict.get('enable', False)):
            aq_data_binding_name = dbout_dict.get('data_binding')
            if aq_data_binding_name is None:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': init aq data_binding is not configured!" % (self.name))
                return
            # open the aq data store
            self.dbm_aq = self.engine.db_binder.get_manager(data_binding=aq_data_binding_name, initialize=True)
            # confirm aqi schema
            dbcols = self.dbm_aq.connection.columnsOf(self.dbm_aq.table_name)
            dbm_dict = weewx.manager.get_manager_dict_from_config(self.config_dict, aq_data_binding_name)
            memcols = [x[0] for x in dbm_dict['schema']]
            if dbcols != memcols:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': aq store schema mismatch: %s != %s" % (self.name, dbcols, memcols))
                return
        elif self.log_success or self.debug > 0:
            loginf("thread '%s': init db_out is diabled. Enable it in the [db_out] section of station %s" %(self.name, self.station))

        aqi_dict = self.config.get('aqi', configobj.ConfigObj())
        if weeutil.weeutil.to_bool(aqi_dict.get('enable', False)):
            aqi_data_binding_name = aqi_dict.get('data_binding')
            if aq_data_binding_name is None:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': init aqi data_binding is not configured!" % (self.name))
                return
            # open the aq data store
            self.dbm_aqi = self.engine.db_binder.get_manager(data_binding=aqi_data_binding_name, initialize=True)
            # confirm aqi schema
            dbcols = self.dbm_aqi.connection.columnsOf(self.dbm_aqi.table_name)
            dbm_dict = weewx.manager.get_manager_dict_from_config(self.config_dict, aqi_data_binding_name)
            memcols = [x[0] for x in dbm_dict['schema']]
            if dbcols != memcols:
                if self.log_failure or self.debug > 0:
                    logerr("thread '%s': aq store schema mismatch: %s != %s" % (self.name, dbcols, memcols))
                return
        elif self.log_success or self.debug > 0:
            loginf("thread '%s': init aqi is diabled. Enable it in the [aqi] section of station %s" %(self.name, self.station))

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
            if log_success or debug > 0:
                loginf("thread '%s': get_data_results check results thread '%s'" % (self.name, thread_name))
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
            if threads[thread_name].get_last_aqi_ts() > 0:
                data = threads[thread_name].get_data_result()
            elif threads[thread_name].get_last_prepare_ts() > 0:
                data = threads[thread_name].get_data_temp()
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
# Class CurrentAQ
#
# ============================================================================

class CurrentAQ(StdService):

    def _create_openmeteo_thread(self, thread_name, station_dict):
        thread_name = "%s_%s" % (SERVICEID, thread_name)
        self.threads[SERVICEID][thread_name] = OPENMETEOthread(thread_name, station_dict,
                    debug=weeutil.weeutil.to_int(station_dict.get('debug', self.debug)),
                    log_success=weeutil.weeutil.to_bool(station_dict.get('log_success',self.log_success)),
                    log_failure=weeutil.weeutil.to_bool(station_dict.get('log_failure',self.log_failure)))
        self.threads[SERVICEID][thread_name].start()


    def _create_uba_thread(self, thread_name, station_dict):
        thread_name = "%s_%s" % (SERVICEID, thread_name)
        self.threads[SERVICEID][thread_name] = UBAthread(thread_name, station_dict,
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


    def _create_owm_thread(self, thread_name, station_dict):
        thread_name = "%s_%s" % (SERVICEID, thread_name)
        self.threads[SERVICEID][thread_name] = OPENWEATHERthread(thread_name, station_dict,
                    debug=weeutil.weeutil.to_int(station_dict.get('debug', self.debug)),
                    log_success=weeutil.weeutil.to_bool(station_dict.get('log_success',self.log_success)),
                    log_failure=weeutil.weeutil.to_bool(station_dict.get('log_failure',self.log_failure)))
        self.threads[SERVICEID][thread_name].start()


    def _create_pws_thread(self, thread_name, station_dict):
        thread_name = "%s_%s" % (SERVICEID, thread_name)
        self.threads[SERVICEID][thread_name] = PWSthread(thread_name, station_dict,
                    debug=weeutil.weeutil.to_int(station_dict.get('debug', self.debug)),
                    log_success=weeutil.weeutil.to_bool(station_dict.get('log_success',self.log_success)),
                    log_failure=weeutil.weeutil.to_bool(station_dict.get('log_failure',self.log_failure)),
                    threads=self.threads[SERVICEID])
        self.threads[SERVICEID][thread_name].start()


    def _create_total_thread(self, thread_name, station_dict):
        thread_name = "%s_%s" % (SERVICEID, thread_name)
        self.threads['worker'][thread_name] = TOTALthread(thread_name, station_dict,
                    debug=weeutil.weeutil.to_int(station_dict.get('debug', self.debug)),
                    log_success=weeutil.weeutil.to_bool(station_dict.get('log_success',self.log_success)),
                    log_failure=weeutil.weeutil.to_bool(station_dict.get('log_failure',self.log_failure)),
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
            self.threads[SERVICEID][thread_name].new_db_aq_record(event)
            self.threads[SERVICEID][thread_name].new_db_aqi_record(event)


    def check_section(self, engine, section_dict, section):

        if self.debug > 0:
            logdbg("Service 'CurrentAQ': check_section section '%s' started" % (section))

        cancel = False

        # new section configurations apply?
        debug = weeutil.weeutil.to_int(section_dict.get('debug', self.service_dict.get('debug', 0)))
        log_success = weeutil.weeutil.to_bool(section_dict.get('log_success', self.service_dict.get('log_success', False)))
        log_failure = weeutil.weeutil.to_bool(section_dict.get('log_failure', self.service_dict.get('log_success', True)))

        # Check required provider
        provider = section_dict.get('provider')
        if provider: provider = provider.lower()
        if provider not in ('uba', 'open-meteo', 'aeris', 'owm', 'pws', 'pws-aeris', 'pws-om', 'pws-owm', 'pws-506', 'pws-509', 'total'):
            if log_failure or debug > 0:
                logerr("Service 'CurrentAQ': check_section section '%s' aq service provider '%s' is not valid. Skip Section" % (section, provider))
            cancel = True
            return cancel, section_dict


        # check required station 
        station = section_dict.get('station')
        if provider in ('uba') and station is None:
            if log_failure or debug > 0:
                logerr("Service 'CurrentAQ': check_section section '%s' aq service provider '%s' - station '%s' is not valid. Skip Section" % (section, provider, station))
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
                        logerr("Service 'CurrentAQ': check_section section '%s' configured unit '%s' for altitude is not valid, altitude will be ignored" % (section, altitude_t[1]))
            else:
                section_dict['altitude'] = None
                if self.log_failure or self.debug > 0:
                    logerr("Service 'CurrentAQ': check_section section '%s' configured altitude '%s' is not valid, altitude will be ignored" % (section, altitude))

        # set default station if not selected and lat or lon is None
        if station is None and (section_dict.get('latitude') is None or section_dict.get('longitude') is None):
            section_dict['station'] = 'thisstation'

        if station is None and (section_dict.get('latitude') is None or section_dict.get('longitude') is None):
            section_dict['station'] = 'thisstation'

        # using lat/lon/alt from weewx.conf
        if section_dict['station'].lower() in ('thisstation', 'here'):
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
            loginf("Service 'CurrentAQ': check_section section '%s' finished" % (section))

        return cancel, section_dict



    def __init__(self, engine, config_dict):

        super(CurrentAQ,self).__init__(engine, config_dict)

        self.service_dict = weeutil.config.accumulateLeaves(config_dict.get('currentaq',configobj.ConfigObj()))
        # service enabled?
        if not weeutil.weeutil.to_bool(self.service_dict.get('enable', False)):
            loginf("Service 'CurrentAQ': service is disabled. Enable it in the [currentaq] section of weewx.conf")
            return
        loginf("Service 'CurrentAQ': service is enabled")

        self.threads = dict()
        self.threads[SERVICEID] = dict()
        self.threads['worker'] = dict()

        #general configs
        self.debug = weeutil.weeutil.to_int(self.service_dict.get('debug', 0))
        self.log_success = weeutil.weeutil.to_bool(self.service_dict.get('log_success', True))
        self.log_failure = weeutil.weeutil.to_bool(self.service_dict.get('log_failure', True))
        if self.debug > 0:
            logdbg("Service 'CurrentAQ': init started")
        if self.debug > 2:
            logdbg("Service 'CurrentAQ': service_dict %s" % (str(json.dumps(self.service_dict))))

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
        currentaq_dict = config_dict.get('currentaq', configobj.ConfigObj())
        if self.debug > 2:
            logdbg("Service 'CurrentAQ': currentaq_dict %s" % (str(json.dumps(currentaq_dict))))

        # section with current weather services only
        current_dict = config_dict.get('currentaq',configobj.ConfigObj()).get('current',configobj.ConfigObj())
        if self.debug > 2:
            logdbg("Service 'CurrentAQ': current_dict %s" % (str(json.dumps(current_dict))))

        stations_dict = current_dict.get('stations',configobj.ConfigObj())
        if self.debug > 2:
            logdbg("Service 'CurrentAQ': stations_dict %s" % (str(json.dumps(stations_dict))))
        for section in stations_dict.sections:
            if not weeutil.weeutil.to_bool(stations_dict[section].get('enable', False)):
                if self.log_success or self.debug > 0:
                    loginf("Service 'CurrentAQ': init current section '%s' is not enabled. Skip section" % section)
                continue

            # build section config
            section_dict = configobj.ConfigObj()
            section_dict = weeutil.config.accumulateLeaves(stations_dict[section])
            provider = str(section_dict.get('provider')).lower()

            # update general config
            section_dict['result_in'] = weeutil.config.deep_copy(currentaq_dict.get('result_in'))
            section_dict['api_in'] = weeutil.config.deep_copy(currentaq_dict.get('api_in'))
            section_dict['api_out'] = weeutil.config.deep_copy(currentaq_dict.get('api_out'))
            section_dict['mqtt_in'] = weeutil.config.deep_copy(currentaq_dict.get('mqtt_in'))
            section_dict['mqtt_out'] = weeutil.config.deep_copy(currentaq_dict.get('mqtt_out'))
            section_dict['file_in'] = weeutil.config.deep_copy(currentaq_dict.get('file_in'))
            section_dict['file_out'] = weeutil.config.deep_copy(currentaq_dict.get('file_out'))
            section_dict['db_in'] = weeutil.config.deep_copy(currentaq_dict.get('db_in'))
            section_dict['db_out'] = weeutil.config.deep_copy(currentaq_dict.get('db_out'))
            section_dict['aqi'] = weeutil.config.deep_copy(currentaq_dict.get('aqi'))
            #logdbg("Service 'CurrentAQ': DEBUG provider %s default section_dict['aqi'] %s" % (provider, json.dumps(section_dict['aqi'])))

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
            section_dict['aqi'].merge(current_dict.get('aqi', configobj.ConfigObj()))
            #logdbg("Service 'CurrentAQ': DEBUG provider %s current section_dict['aqi'] %s" % (provider, json.dumps(section_dict['aqi'])))

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
            section_dict['aqi'].merge(stations_dict.get('aqi', configobj.ConfigObj()))
            #logdbg("Service 'CurrentAQ': DEBUG provider %s station section_dict['aqi'] %s" % (provider, json.dumps(section_dict['aqi'])))

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
            section_dict['aqi'].merge(stations_dict[section].get('aqi', configobj.ConfigObj()))
            #logdbg("Service 'CurrentAQ': DEBUG provider %s provider section_dict['aqi'] %s" % (provider, json.dumps(section_dict['aqi'])))

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
            if provider == 'open-meteo':
                self._create_openmeteo_thread(section, thread_config)
            elif provider == 'uba':
                self._create_uba_thread(section, thread_config)
            elif provider == 'aeris':
                self._create_aeris_thread(section, thread_config)
            elif provider == 'owm':
                self._create_owm_thread(section, thread_config)
            elif provider == 'pws':
                self._create_pws_thread(section, thread_config)
            elif provider == 'pws-aeris':
                self._create_pws_thread(section, thread_config)
            elif provider == 'pws-om':
                self._create_pws_thread(section, thread_config)
            elif provider == 'pws-owm':
                self._create_pws_thread(section, thread_config)
            elif provider == 'pws-506':
                self._create_pws_thread(section, thread_config)
            elif provider == 'pws-509':
                self._create_pws_thread(section, thread_config)
            elif provider == 'total':
                self._create_total_thread(section, thread_config)
            elif self.log_failure or self.debug > 0:
                logerr("Service 'CurrentAQ': init section '%s' unknown weather service provider '%s'" % (section, provider))
            section_dict = None

        if  __name__!='__main__':
            self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet)
            self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

        if self.log_success or self.debug > 0:
            loginf("Service 'CurrentAQ': init finished. Number of current threads started: %d" % (len(self.threads[SERVICEID])))
        if len(self.threads[SERVICEID]) < 1:
            loginf("Service 'CurrentAQ': no threads have been started. Service 'CurrentAQ' exits now")
            return
