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

    he service downloads weather warnings from various providers.

    Providers:
      Brightsky (DWD)
      AerisWeather

    The goal is to provide the Weiherhammer Skin (Belchertown Skin Fork) with 
    standardized JSON data in a file and in a MQTT Topic. This way it is possible
    to switch within the skin without much effort between the different providers.
    If new data is loaded, the updated topic can be loaded and displayed updated.
"""

VERSION = "0.1a1"

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
from tzlocal import get_localzone
from dateutil import parser

try:
    # Test for new-style weewx logging by trying to import weeutil.logger
    import weeutil.logger
    import logging
    log = logging.getLogger("weiwx.warnwx")

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
        syslog.syslog(level, 'weiwx.warnwx: %s' % msg)

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

SERVICEID='warnwx'

# provider warnings
# ID         = Provider and model
# brightsky  = Bright Sky DWD Warnings
# aeris      = Vaisala Xweather Warnings

HTMLTMPL = "<p><a href='%s' target='_blank' rel='tooltip' title=''>%s</a>%s</p>"

PROVIDER = {
    'brightsky': ('Bright Sky', 'https://brightsky.dev', ''),
    'aeris': ('Vaisala Xweather', 'https://www.vaisala.com', '')
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

    headers={'User-Agent': 'warnwx'}
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
        exception_output(thread_name, e, addcontent=json.dumps(data))
        return None
    return not (sunrise_ts < data['dateTime'][0] < sunset_ts)


@staticmethod
def minimize_warnings_total_mqtt(thread_name, data, debug=0, log_success=False, log_failure=True):
    """
    Minimize the output of weather providers and generate only the required elements that are 
    absolutely necessary for displaying the warnings weather conditions in the Belchertown skin.
    """
    if debug > 2:
        logdbg("thread '%s': minimize_warnings_total_mqtt data %s" % (thread_name, json.dumps(data)))
    minimized = list()
    try:
        data = data.get('alerts')
        logdbg("thread '%s': minimize_warnings_total_mqtt alerts %s" % (thread_name, json.dumps(data)))
        for cell, alerts in data.items():
            if debug > 2:
                logdbg("thread '%s': minimize_warnings_total_mqtt cell %s alerts %s" % (thread_name, cell, json.dumps(alerts)))
            for alert in alerts:
                if debug > 2:
                    logdbg("thread '%s': minimize_warnings_total_mqtt alert %s" % (thread_name, json.dumps(alert)))
                minalert = dict()
                minalert['title'] = alert.get('headline_de')
                minalert['title_short'] = alert.get('event_de')
                minalert['description'] = alert.get('description_de')
                minalert['instruction'] = alert.get('instruction_de')
                minalert['begins'] = alert.get('onset')
                if minalert['begins'] is not None:
                    dt = datetime.datetime.fromisoformat(minalert['begins'])
                    tz = pytz.timezone(minalert['begins'][-6:])
                    dtz = tz.localize(dt)
                    minalert['begins'] = weeutil.weeutil.to_int(dtz.timestamp())
                minalert['expires'] = alert.get('expires')
                if minalert['expires'] is not None:
                    dt = datetime.datetime.fromisoformat(minalert['expires'])
                    tz = pytz.timezone(minalert['expires'][-6:])
                    dtz = tz.localize(dt)
                    minalert['expires'] = weeutil.weeutil.to_int(dtz.timestamp())
                minimized.append(minalert)
        if debug > 2:
            logdbg("thread '%s': minimize_warnings_total_mqtt minimized %s" % (thread_name, json.dumps(minimized)))
    except Exception as e:
        exception_output(thread_name, e)
    return minimized


@staticmethod
def minimize_warnings_total_file(thread_name, data, debug=0, log_success=False, log_failure=True):
    """
    Minimize the output of weather providers and generate only the required elements that are 
    absolutely necessary for displaying the warnings weather conditions in the Belchertown skin.
    """
    if debug > 2:
        logdbg("thread '%s': minimize_warnings_total_file data %s" % (thread_name, json.dumps(data)))
    minimized = list()
    try:
        data = data.get('alerts')
        logdbg("thread '%s': minimize_warnings_total_file alerts %s" % (thread_name, json.dumps(data)))
        for cell, alerts in data.items():
            if debug > 2:
                logdbg("thread '%s': minimize_warnings_total_file cell %s alerts %s" % (thread_name, cell, json.dumps(alerts)))
            for alert in alerts:
                if debug > 2:
                    logdbg("thread '%s': minimize_warnings_total_file alert %s" % (thread_name, json.dumps(alert)))
                minalert = dict()
                minalert['title'] = alert.get('headline_de')
                minalert['title_short'] = alert.get('event_de')
                minalert['description'] = alert.get('description_de')
                minalert['instruction'] = alert.get('instruction_de')
                minalert['begins'] = alert.get('onset')
                # https://chat.openai.com/c/5870e17e-d964-4d68-bd5f-1038211fc456
                if minalert['begins'] is not None:
                    # Konvertiere das gegebene Datum von einem String zu einem datetime-Objekt
                    begins_dt = parser.parse(minalert['begins'])
                    # Extrahiere die Zeitzone als UTC-Verschiebung in Minuten
                    utc_offset_minutes = begins_dt.utcoffset().total_seconds() // 60
                    # Erstelle ein pytz.FixedOffset-Objekt mit der UTC-Verschiebung
                    begins_tz = pytz.FixedOffset(int(utc_offset_minutes))
                    # Wandle das gegebene Datum in ein "naives" datetime-Objekt um
                    naive_td = begins_dt.replace(tzinfo=None)
                    # Wandle das "naive" Datum in die entsprechende Zeitzone um
                    localized_dt = begins_tz.localize(naive_td)
                    # Verwende die lokale Zeitzone
                    local_tz = get_localzone()
                    local_dt = localized_dt.astimezone(local_tz)
                    minalert['begins'] = weeutil.weeutil.to_int(local_dt.timestamp())
                minalert['expires'] = alert.get('expires')
                if minalert['expires'] is not None:
                    # Konvertiere das gegebene Datum von einem String zu einem datetime-Objekt
                    expires_dt = parser.parse(minalert['expires'])
                    # Extrahiere die Zeitzone als UTC-Verschiebung in Minuten
                    utc_offset_minutes = expires_dt.utcoffset().total_seconds() // 60
                    # Erstelle ein pytz.FixedOffset-Objekt mit der UTC-Verschiebung
                    expires_tz = pytz.FixedOffset(int(utc_offset_minutes))
                    # Wandle das gegebene Datum in ein "naives" datetime-Objekt um
                    naive_td = expires_dt.replace(tzinfo=None)
                    # Wandle das "naive" Datum in die entsprechende Zeitzone um
                    localized_dt = begins_tz.localize(naive_td)
                    # Verwende die lokale Zeitzone
                    local_tz = get_localzone()
                    local_dt = localized_dt.astimezone(local_tz)
                    minalert['expires'] = weeutil.weeutil.to_int(local_dt.timestamp())
                minimized.append(minalert)
        if debug > 2:
            logdbg("thread '%s': minimize_warnings_total_file minimized %s" % (thread_name, json.dumps(minimized)))
    except Exception as e:
        exception_output(thread_name, e)
    return minimized


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
    try:
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
                    exception_output(thread_name, e, addcontent='topic=%s payload=%s' % (topic, value))
                    return False
            if format == 'keyvalue':
                if debug > 2:
                    logdbg("thread '%s': publish_broker keyvalue '%s:%s' topic '%s'" % (thread_name, mqtt_options['mqtt_broker'], str(mqtt_options['mqtt_port']), mqtt_options['mqtt_topic']))
                for key, value in packet.items():
                    try:
                        if value is None:
                            value = " " # TODO: The publisher does not send NULL or "" values
                        if isinstance(value, dict) or isinstance(value, list):
                            value = json.dumps(value)
                        topic = mqtt_options['mqtt_topic'] + '/' + str(key)
                        if debug > 2:
                            logdbg("thread '%s': publish_broker keyvalue %s=%s" % (thread_name, topic, str(value)))
                        mqtt_publish.single(topic, value, hostname=mqtt_options['mqtt_broker'], port=mqtt_options['mqtt_port'],
                            auth={'username': mqtt_options['mqtt_username'], 'password': mqtt_options['mqtt_password']}, keepalive=mqtt_options['mqtt_keepalive'],
                            qos=mqtt_options['mqtt_qos'], retain=mqtt_options['mqtt_retain'], client_id=mqtt_options['mqtt_clientid'])
                    except Exception as e:
                        exception_output(thread_name, e, addcontent='topic=%s payload=%s' % (topic, value))
                        return False
    except Exception as e:
        exception_output(thread_name, e)

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


    def publish_result_mqtt(self):
        """ publish warnings weather data record to MQTT Broker """
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
                loginf("thread '%s': publish_result_mqtt is diabled. Enable it in the [mqtt_out] section of station %s" % (self.name, self.station))
            return False

        if len(self.data_result) < 1:
            if log_failure or debug > 0:
                logwrn("thread '%s': publish_result_mqtt there are no result data available. Abort." % (self.name))
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
                logerr("thread '%s': publish_result_mqtt required 'unit_system' is not configured. Configure 'unit_system = US/METRIC/METRICWX' in the [mqtt_out] section of station %s" % (self.name, self.station))
            return False
        if lang is None:
            if log_failure or debug > 0:
                logerr("thread '%s': publish_result_mqtt required 'lang' is not configured. Configure 'lang = de/en' in the [mqtt_out] section of station %s" % (self.name, self.station))
            return False

        try:
            # MQTT options
            mqtt_options = dict()
            basetopic = mqttout_dict.get('basetopic', self.name)
            topic = mqttout_dict.get('topic', self.name)
            if basetopic is None or basetopic == '':
                if log_failure or debug > 0:
                    logerr("thread '%s': publish_result_mqtt required 'basetopic' is not valid. Station %s" % (self.name, self.station))
                return False
            if topic is None or topic == '':
                if log_failure or debug > 0:
                    logerr("thread '%s': publish_result_mqtt required 'topic' is not valid. Station %s" % (self.name, self.station))
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
                    output[source_id] = minimize_warnings_total_file(self.name, data, debug=debug, log_success=log_success, log_failure=log_failure)
            else:
                output.update(self.data_result)

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
        """ publish warnings weather data record to a file. Currently only JSON files supported. """

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
                loginf("thread '%s': publish_result_file is diabled. Enable it in the [file_out] section of station %s" % (self.name, self.station))
            return False

        if len(self.data_result) < 1:
            if log_failure or debug > 0:
                logwrn("thread '%s': publish_result_file there are no result data available. Abort." % (self.name))
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
                logerr("thread '%s': publish_result_file required 'unit_system' is not configured. Configure 'unit_system = US/METRIC/METRICWX' in the [mqtt_out] section of station %s" % (self.name, self.station))
            return False
        if lang is None:
            if log_failure or debug > 0:
                logerr("thread '%s': publish_result_file required 'lang' is not configured. Configure 'lang = de/en' in the [mqtt_out] section of station %s" % (self.name, self.station))
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
                    output[source_id] = minimize_warnings_total_file(self.name, data, debug=debug, log_success=log_success, log_failure=log_failure)
            else:
                output.update(self.data_result)

            if not publish_file(self.name, file_options, output, debug=debug, log_success=log_success, log_failure=log_failure):
                if log_failure or debug > 0:
                    logerr("thread '%s': publish_result_file generated an error" % (self.name))
                return False
        except Exception as e:
            exception_output(self.name, e)
            return False

        if log_success or debug > 0:
            loginf("thread '%s': publish_result_file finished" % (self.name))
        # TODO: error handling?
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
                if self.interval_get == 300: # TODO: flex
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
# Class BRIGHTSKYthread
#
# ============================================================================

class BRIGHTSKYthread(AbstractThread):

    # Warn Cell Id's:
    # 109374000 = Kreis Neustadt a.d. Waldnaab
    # 109363000 = Stadt Weiden i.d. OPf.
    #
    # 809374166 = Mitgliedsgemeinde in Verwaltungsgemeinschaft Weiherhammer
    # 809374452 = gemeindefreies Gebiet Manteler Forst
    # 809374131 = Mitgliedsgemeinde in Verwaltungsgemeinschaft Kohlberg
    # 809374132 = Mitgliedsgemeinde in Verwaltungsgemeinschaft Leuchtenberg
    # 809371127 = Stadt Hirschau
    # 809371150 = Stadt Schnaittenbach
    # 809374133 = Gemeinde Luhe-Wildenau
    # 809374134 = Gemeinde Mantel
    # 809371121 = Gemeinde Freihung
    # 809374124 = Stadt Grafenwöhr

    # https://brightsky.dev/demo/alerts/
    # https://brightsky.dev/docs/#/operations/getAlerts

    # https://api.brightsky.dev/alerts?lat=49.632270&lon=12.056186
    # or
    # https://api.brightsky.dev/alerts?warn_cell_id=809374166
    #
    # response:

    # {
      # "alerts": [
        # {
          # "id": 402638,
          # "alert_id": "2.49.0.0.276.0.DWD.PVW.1693046460000.3e4c31d9-f407-42f8-bff6-83e020f584c3",
          # "effective": "2023-08-26T10:41:00+00:00",
          # "onset": "2023-08-26T22:00:00+00:00",
          # "expires": "2023-08-29T16:00:00+00:00",
          # "category": "met",
          # "response_type": "prepare",
          # "urgency": "immediate",
          # "severity": "moderate",
          # "certainty": "likely",
          # "event_code": 63,
          # "event_en": "persistent rain",
          # "event_de": "DAUERREGEN",
          # "headline_en": "Official WARNING of PERSISTANT RAIN",
          # "headline_de": "Amtliche WARNUNG vor DAUERREGEN",
          # "description_en": "There is a risk of persistent rain (Level 2 of 4).\nPrecipitation amounts: ~ 60 l/m²",
          # "description_de": "Es tritt Dauerregen wechselnder Intensität auf. Dabei werden Niederschlagsmengen um 60 l/m² erwartet.",
          # "instruction_en": null,
          # "instruction_de": null
        # }
      # ],
      # "location": {
        # "warn_cell_id": 809374166,
        # "name": "Mitgliedsgemeinde in Verwaltungsgemeinschaft Weiherhammer",
        # "name_short": "Weiherhammer",
        # "district": "Neustadt a.d. Waldnaab",
        # "state": "Bayern",
        # "state_short": "BY"
      # }
    # }

    # {
      # "alerts": [
        # {
          # "id": 347754,
          # "alert_id": "2.49.0.0.276.0.DWD.PVW.1692689700000.a2003648-2a6c-45fc-be7d-275f295146fc",
          # "effective": "2023-08-22T07:35:00+00:00",
          # "onset": "2023-08-22T09:00:00+00:00",
          # "expires": "2023-08-22T17:00:00+00:00",
          # "category": "health",
          # "response_type": "prepare",
          # "urgency": "immediate",
          # "severity": "minor",
          # "certainty": "likely",
          # "event_code": 247,
          # "event_en": "strong heat",
          # "event_de": "STARKE HITZE",
          # "headline_en": "Official WARNING of STRONG HEAT",
          # "headline_de": "Amtliche WARNUNG vor HITZE",
          # "description_en": "The expected weather will bring a situation of strong heat stress. (Level 1 of 3)\nHeight range: < 800 m",
          # "description_de": "Am Dienstag wird eine starke Wärmebelastung erwartet. ",
          # "instruction_en": "NOTE: be aware that this is an automatically generated product. The manually created original text warning is only available in German.It is issued by the DWD - Centre for Human Biometeorological Research (ZMMF) in Freiburg.",
          # "instruction_de": "Hitzebelastung kann für den menschlichen Körper gefährlich werden und zu einer Vielzahl von gesundheitlichen Problemen führen. Vermeiden Sie nach Möglichkeit die Hitze, trinken Sie ausreichend Wasser und halten Sie die Innenräume kühl."
        # }
      # ],
      # "location": {
        # "warn_cell_id": 809374166,
        # "name": "Mitgliedsgemeinde in Verwaltungsgemeinschaft Weiherhammer",
        # "name_short": "Weiherhammer",
        # "district": "Neustadt a.d. Waldnaab",
        # "state": "Bayern",
        # "state_short": "BY"
      # }
    # }

    # {
      # "alerts": [],
      # "location": {
        # "warn_cell_id": 809374166,
        # "name": "Mitgliedsgemeinde in Verwaltungsgemeinschaft Weiherhammer",
        # "name_short": "Weiherhammer",
        # "district": "Neustadt a.d. Waldnaab",
        # "state": "Bayern",
        # "state_short": "BY"
      # }
    # }

    # Belchertown old:

    # "alerts": [
        # {
            # "success": true,
            # "error": null,
            # "response": [
                # {
                    # "id": "2.49.0.0.276.0.DWD.PVW.1693046460000.8497c05a-6d46-4f49-b2ed-fbfadc913f19.DEU",
                    # "loc": {},
                    # "dataSource": "PVW",
                    # "details": {
                        # "type": "AW.RA.MD",
                        # "name": "DAUERREGEN",
                        # "loc": "",
                        # "emergency": null,
                        # "priority": null,
                        # "color": null,
                        # "cat": "RAIN",
                        # "body": "Es tritt Dauerregen wechselnder Intensität auf. Dabei werden Niederschlagsmengen um 60 l/m² erwartet.",
                        # "bodyFull": "Es tritt Dauerregen wechselnder Intensität auf. Dabei werden Niederschlagsmengen um 60 l/m² erwartet."
                    # },
                    # "timestamps": {
                        # "issued": 1693046460,
                        # "begins": 1693087200,
                        # "expires": 1693324800,
                        # "updated": 1693046460,
                        # "added": 1693046460,
                        # "created": 1693046460
                    # },
                    # "poly": "",
                    # "geoPoly": null,
                    # "includes": {},
                    # "place": {},
                    # "profile": {},
                    # "active": true
                # }
            # ]
        # }
    # ],



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

        self.station = self.config.get('station', 'thisstation')
        self.provider = self.config.get('provider', 'brightsky')
        self.warncells = weeutil.weeutil.option_as_list(self.config.get('warncells', list()))
        self.source_id = self.config.get('source_id', 'brightsky')
        self.interval_get = weeutil.weeutil.to_int(self.config.get('interval_get', 300))
        self.interval_push = weeutil.weeutil.to_int(self.config.get('interval_push', 30))
        self.expired = weeutil.weeutil.to_int(self.config.get('expired', 600))
        self.icon_path_belchertown = self.config.get('icon_path_belchertown', 'images')
        self.timezone = self.config.get('timezone', 'Europe/Berlin')
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

        weewx.units.obs_group_dict.setdefault('dateTime','group_time')
        weewx.units.obs_group_dict.setdefault('generated','group_time')
        weewx.units.obs_group_dict.setdefault('age','group_deltatime')
        weewx.units.obs_group_dict.setdefault('day','group_count')
        weewx.units.obs_group_dict.setdefault('expired','group_count')

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
            loginf("thread '%s': init db_out is diabled. Enable it in the [db_out] section of station %s" % (self.name, self.station))

        if self.log_success or self.debug > 0:
            loginf("thread '%s': init finished" % self.name)

    def prepare_api_data(self, apidata, lang, unitsystem, debug=0, log_success=False, log_failure=True):
        """ preprocess Brightsky api warnings data """

        data_temp = dict()
        actts = weeutil.weeutil.to_int(time.time())
        data_temp['dateTime'] = weeutil.weeutil.to_int(actts)
        data_temp['dateTimeISO'] = get_isodate_from_timestamp(weeutil.weeutil.to_int(actts), self.timezone)
        data_temp['generated'] = weeutil.weeutil.to_int(actts)
        data_temp['generatedISO'] = get_isodate_from_timestamp(weeutil.weeutil.to_int(actts), self.timezone)
        data_temp['sourceProvider'] = PROVIDER[self.source_id][0]
        data_temp['sourceProviderLink'] = PROVIDER[self.source_id][1]
        data_temp['sourceProviderHTML'] = HTMLTMPL % (PROVIDER[self.source_id][1], PROVIDER[self.source_id][0], PROVIDER[self.source_id][2])
        data_temp['sourceModul'] = self.name
        data_temp['sourceId'] = self.source_id
        data_temp['lang'] = lang
        data_temp['usUnits'] = unitsystem
        data_temp['alerts'] = dict()
        data_temp['locations'] = dict()
        data_temp['sourceUrl'] = dict()
        data_temp[self.source_id] = dict()

        station = apidata.get(self.station)
        if station is None:
            # API query with warncells
            for cell in apidata:
                alerts = apidata[cell].get('alerts')
                data_temp['alerts'][cell] = dict()
                data_temp['alerts'][cell] = alerts
                data_temp['locations'][cell] = dict()
                data_temp['locations'][cell] = apidata[cell].get('location')
                data_temp['sourceUrl'][cell] = dict()
                data_temp['sourceUrl'][cell] = apidata[cell].get('sourceUrl')
                data_temp[self.source_id][cell] = dict()
                data_temp[self.source_id][cell]['success'] = True
                data_temp[self.source_id][cell]['code'] = ''
                data_temp[self.source_id][cell]['description'] = ''
                if len(alerts) <= 0:
                    data_temp[self.source_id][cell]['code'] = 'warn_no_data'
                    data_temp[self.source_id][cell]['description'] = 'Valid request. No results available based on your query parameters.'
        else:
            # API query with lat and lon
            alerts = apidata[station].get('alerts')
            alertsCount += len(alerts)
            location = apidata[station].get('location', dict())
            cell = location.get('warn_cell_id')
            if cell is not None:
                data_temp['alerts'][cell] = dict()
                data_temp['alerts'][cell] = alerts
                data_temp['locations'][cell] = dict()
                data_temp['locations'][cell] = apidata[station].get('location')
                data_temp['sourceUrl'][cell] = dict()
                data_temp['sourceUrl'][cell] = apidata[cell].get('sourceUrl')
                data_temp[self.source_id][cell] = dict()
                data_temp[self.source_id][cell]['sucess'] = True
                data_temp[self.source_id][cell]['code'] = ''
                data_temp[self.source_id][cell]['description'] = ''
                if len(alerts) <= 0:
                    data_temp[self.source_id][cell]['code'] = 'warn_no_data'
                    data_temp[self.source_id][cell]['description'] = 'Valid request. No results available based on your query parameters.'
            else:
                cell = self.station
                if log_failure or debug > 0:
                    logerr("thread '%s': prepare_api_data could not get 'warn_cell_id'" % (self.name))
                if debug > 2:
                    logerr("thread '%s': prepare_api_data api_data %s" % (self.name, json.dumps(apidata)))
                data_temp['alerts'][cell] = list()
                data_temp['locations'][cell] = dict()
                data_temp['sourceUrl'][cell] = dict()
                data_temp['sourceUrl'][cell] = apidata[cell].get('sourceUrl')
                data_temp[self.source_id][cell] = dict()
                data_temp[self.source_id][cell]['sucess'] = False
                data_temp[self.source_id][cell]['code'] = 'error_no_warn_cell_id'
                data_temp[self.source_id][cell]['description'] = 'Valid request. No results and warn_cell_id available based on your query parameters.'

        if debug > 2:
            logdbg("thread '%s': prepare_api_data data_temp %s" % (self.name, json.dumps(data_temp)))

        return data_temp


    def get_data_api(self):
        """ download and process Brightsky API warnings data """

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

        # https://api.brightsky.dev/alerts?warn_cell_id=809374166
        baseurl = 'https://api.brightsky.dev/alerts'

        # Timezone in which record timestamps will be presented, as tz database name, e.g. Europe/Berlin.
        # Will also be used as timezone when parsing date and last_date, unless these have explicit UTC offsets.
        # If omitted but date has an explicit UTC offset, that offset will be used as timezone.
        # Otherwise will default to UTC.
        #params += '&tz=Europe/Berlin'
        baseparams = '?tz=Etc/UTC'

        # TODO: one function
        apidata = dict()
        if len(self.warncells) > 0:
            for warncell in self.warncells:
                params = '&warn_cell_id=%d' % weeutil.weeutil.to_int(warncell)
                url = baseurl + baseparams + params
                apidata[warncell] = dict()
                apidata[warncell]['sourceUrl'] = obfuscate_secrets(url)
                if debug > 0:
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
                            apidata[warncell] = response
                            apidata[warncell]['sourceUrl'] = obfuscate_secrets(url)
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
        else:
            params = '&lat=%s&lon=%s' % (self.lat, self.lon)
            url = baseurl + baseparams + params
            apidata[self.station] = dict()
            apidata[self.station]['sourceUrl'] = url
            if debug > 0:
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
                        apidata[self.station] = response
                        apidata[self.station]['sourceUrl'] = url
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
            logdbg("thread '%s': get_data_api api result %s" % (self.name, json.dumps(apidata)))

        # prepare data
        self.data_temp = self.prepare_api_data(apidata, lang, unitsystem,
                                               debug=debug, log_success=log_success, log_failure=log_failure)

        self.last_get_ts = weeutil.weeutil.to_int(time.time())
        return (len(self.data_temp) > 0)



# ============================================================================
#
# Class AERISthread
#
# ============================================================================

class AERISthread(AbstractThread):

    # API: https://api.aerisapi.com/alerts/49.632270,12.056186?format=json&limit=10&lang=de&client_id=[ID]&client_secret=[SECRET]

    # response:

    # {
        # "success": true,
        # "error": {
            # "code": "warn_no_data",
            # "description": "Valid request. No results available based on your query parameters."
        # },
        # "response": []
    # }

    # or

    # {
        # "success": true,
        # "error": null,
        # "response": [{
            # "id": "7751ec729930c9b5c6787ab6c532482c",
            # "loc": {
                # "long": -103.223027968,
                # "lat": 44.0006520001
            # },
            # "details": {
                # "type": "FF.A",
                # "name": "FLASH FLOOD WATCH",
                # "loc": "SDZ026",
                # "emergency": false,
                # "color": "32CD32",
                # "cat": "flood",
                # "body": "...LOCALLY HEAVY RAINFALL POSSIBLE THROUGH EVENING...\n\n.Scattered showers and thunderstorms will continue through this \nevening. Some of the storms could produce locally heavy rainfall \non already saturated ground, resulting in flash flooding.\n\n\n...FLASH FLOOD WATCH REMAINS IN EFFECT UNTIL MIDNIGHT MDT\nTONIGHT...\n\nThe Flash Flood Watch continues for\n\n* Portions of South Dakota and the Black Hills of Wyoming, \nincluding the following areas, in South Dakota, the Central \nBlack Hills, the Hermosa Foot Hills, the Northern Black Hills, \nthe Northern Foot Hills, the Rapid City area, the Southern \nBlack Hills, the Southern Foot Hills, and the Sturgis\/Piedmont \nFoot Hills. In the Black Hills of Wyoming, the Wyoming Black \nHills. \n\n* Until midnight MDT tonight\n\n* Scattered showers and thunderstorms will continue through this\nevening. Locally heavy rain is possible, especially through \nearly this evening. \n\n* Local rainfall amounts of more than an inch are possible in a \nshort period of time, which combined with the already \nsaturated ground, may result in flash flooding. \n\nA flash flood watch means that conditions are favorable for heavy\nrain over the watch area, which may cause flash flooding along\nstreams, creeks, canyons, and draws. If you are in the watch\narea, monitor noaa weather radio and local media for updated\nforecasts. Be ready to quickly move to higher ground, if heavy\nrain occurs, rising water levels are observed, or a warning is\nissued.",
                # "bodyFull": "WGUS63 KUNR 291958\nFFAUNR\n\nFlood Watch\nNational Weather Service Rapid City SD\n158 PM MDT Tue May 29 2018\n\n...LOCALLY HEAVY RAINFALL POSSIBLE THROUGH EVENING...\n\n.Scattered showers and thunderstorms will continue through this \nevening. Some of the storms could produce locally heavy rainfall \non already saturated ground, resulting in flash flooding.\n\nSDZ024>029-072-074-WYZ057-300600-\n\/O.CON.KUNR.FF.A.0003.000000T0000Z-180530T0600Z\/\n\/00000.0.ER.000000T0000Z.000000T0000Z.000000T0000Z.OO\/\nNorthern Black Hills-Northern Foot Hills-Rapid City-\nSouthern Foot Hills-Central Black Hills-Southern Black Hills-\nSturgis\/Piedmont Foot Hills-Hermosa Foot Hills-\nWyoming Black Hills-\nIncluding the cities of Lead, Deadwood, Spearfish, Rapid City, \nEdgemont, Hot Springs, Hill City, Mt Rushmore, Custer, Sturgis, \nHermosa, Four Corners, and Sundance\n158 PM MDT Tue May 29 2018\n\n\n\n...FLASH FLOOD WATCH REMAINS IN EFFECT UNTIL MIDNIGHT MDT\nTONIGHT...\n\nThe Flash Flood Watch continues for\n\n* Portions of South Dakota and the Black Hills of Wyoming, \nincluding the following areas, in South Dakota, the Central \nBlack Hills, the Hermosa Foot Hills, the Northern Black Hills, \nthe Northern Foot Hills, the Rapid City area, the Southern \nBlack Hills, the Southern Foot Hills, and the Sturgis\/Piedmont \nFoot Hills. In the Black Hills of Wyoming, the Wyoming Black \nHills. \n\n* Until midnight MDT tonight\n\n* Scattered showers and thunderstorms will continue through this\nevening. Locally heavy rain is possible, especially through \nearly this evening. \n\n* Local rainfall amounts of more than an inch are possible in a \nshort period of time, which combined with the already \nsaturated ground, may result in flash flooding. \n\nPRECAUTIONARY\/PREPAREDNESS ACTIONS...\n\nA flash flood watch means that conditions are favorable for heavy\nrain over the watch area, which may cause flash flooding along\nstreams, creeks, canyons, and draws. If you are in the watch\narea, monitor noaa weather radio and local media for updated\nforecasts. Be ready to quickly move to higher ground, if heavy\nrain occurs, rising water levels are observed, or a warning is\nissued.\n\n&&"
            # },
            # "timestamps": {
                # "issued": 1527623880,
                # "issuedISO": "2018-05-29T13:58:00-06:00",
                # "begins": 1527623880,
                # "beginsISO": "2018-05-29T13:58:00-06:00",
                # "expires": 1527660000,
                # "expiresISO": "2018-05-30T00:00:00-06:00",
                # "added": 1527623935,
                # "addedISO": "2018-05-29T13:58:55-06:00"
            # },
            # "poly": "",
            # "geoPoly": null,
            # "includes": {
                # "counties": [],
                # "fips": ["46033", "46047", "46081", "46093", "46103", "56011", "56045"],
                # "wxzones": ["SDZ024", "SDZ025", "SDZ026", "SDZ027", "SDZ028", "SDZ029", "SDZ072", "SDZ074", "WYZ057"],
                # "zipcodes": [57626, 57701, 57702, 57703, 57706, 57709, 57718, 57719, 57722, 57725, 57730, 57732, 57735, 57737, 57738, 57741, 57744, 57745, 57747, 57748, 57751, 57754, 57758, 57759, 57761, 57763, 57766, 57767, 57769, 57773, 57775, 57779, 57780, 57782, 57783, 57785, 57787, 57790, 57791, 57792, 57793, 57799, 82701, 82710, 82711, 82712, 82714, 82715, 82720, 82721, 82723, 82729, 82730]
            # },
            # "place": {
                # "name": "rapid city",
                # "state": "sd",
                # "country": "us"
            # },
            # "profile": {
                # "tz": "America\/Denver"
            # },
            # "active": true
        # }]
    # }


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
        self.source_id = self.config.get('source_id', 'aeris')
        self.interval_get = weeutil.weeutil.to_int(self.config.get('interval_get', 300))
        self.interval_push = weeutil.weeutil.to_int(self.config.get('interval_push', 30))
        self.expired = weeutil.weeutil.to_int(self.config.get('expired', 600))
        self.icon_path_belchertown = self.config.get('icon_path_belchertown', 'images')
        self.timezone = self.config.get('timezone', 'Europe/Berlin')
        self.config_dict = thread_dict.get('config_dict')
        self.engine = thread_dict.get('engine')
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
            loginf("thread '%s': init db_out is diabled. Enable it in the [db_out] section of station %s" % (self.name, self.station))

        if self.log_success or self.debug > 0:
            loginf("thread '%s': init finished" % self.name)


    def prepare_api_data(self, apidata, lang, unitsystem, url, debug=0, log_success=False, log_failure=True):
        """ preprocess AerisWeather api warnings data """

        data_temp = dict()
        actts = weeutil.weeutil.to_int(time.time())
        data_temp['dateTime'] = weeutil.weeutil.to_int(actts)
        data_temp['dateTimeISO'] = get_isodate_from_timestamp(weeutil.weeutil.to_int(actts), self.timezone)
        data_temp['generated'] = weeutil.weeutil.to_int(actts)
        data_temp['generatedISO'] = get_isodate_from_timestamp(weeutil.weeutil.to_int(actts), self.timezone)
        data_temp['sourceProvider'] = PROVIDER[self.source_id][0]
        data_temp['sourceUrl'] = obfuscate_secrets(url)
        data_temp['sourceProviderLink'] = PROVIDER[self.source_id][1]
        data_temp['sourceProviderHTML'] = HTMLTMPL % (PROVIDER[self.source_id][1], PROVIDER[self.source_id][0], PROVIDER[self.source_id][2])
        data_temp['sourceModul'] = self.name
        data_temp['sourceId'] = self.source_id
        data_temp['lang'] = lang
        data_temp['usUnits'] = unitsystem
        data_temp['alerts'] = dict()
        data_temp['locations'] = dict()
        data_temp[self.source_id] = dict()
        cell = self.station

        try:
            success = weeutil.weeutil.to_bool(apidata.get('success', False))
            if not success:
                error = apidata.get('error', dict())
                code = error.get('code', '???')
                description = error.get('description', '???')
                if log_failure or debug > 0:
                    logerr("thread '%s': prepare_api_data api send Error." % (self.name))
                    logerr("thread '%s': code: %s, description: %s" % (self.name, code, description))
                data_temp['alerts'][cell] = list()
                data_temp['locations'][cell] = dict()
                data_temp[self.source_id][cell] = dict()
                data_temp[self.source_id][cell]['success'] = success
                data_temp[self.source_id][cell]['code'] = code
                data_temp[self.source_id][cell]['description'] = description
                if debug > 2:
                    logdbg("thread '%s': prepare_api_data data_temp %s" % (self.name, json.dumps(data_temp)))
                return data_temp
        except Exception as e:
            exception_output(self.name, e)
            data_temp['alerts'][cell] = list()
            data_temp['locations'][cell] = dict()
            data_temp[self.source_id][cell] = dict()
            data_temp[self.source_id][cell]['success'] = False
            data_temp[self.source_id][cell]['code'] = e.__class__.__name__
            data_temp[self.source_id][cell]['description'] = e
            if debug > 2:
                logdbg("thread '%s': prepare_api_data data_temp %s" % (self.name, json.dumps(data_temp)))
            return data_temp

        response = apidata.get('response', list())
        if len(response) <= 0:
            error = apidata.get('error', dict())
            code = error.get('code', '???')
            description = error.get('description', '???')
            if log_success or debug > 0:
                loginf("thread '%s': prepare_api_data api send no warnings." % (self.name))
                loginf("thread '%s': code: %s, description: %s" % (self.name, code, description))
            data_temp['alerts'][cell] = list()
            data_temp['locations'][cell] = dict()
            data_temp[self.source_id][cell] = dict()
            data_temp[self.source_id][cell]['success'] = True
            data_temp[self.source_id][cell]['code'] = code
            data_temp[self.source_id][cell]['description'] = description
            if debug > 2:
                logdbg("thread '%s': prepare_api_data data_temp %s" % (self.name, json.dumps(data_temp)))
            return data_temp

        # Brightsky Schema
        # https://brightsky.dev/docs/#/operations/getAlerts
        try:
            for alert, values in enumerate(response):
                loc = response[alert].get('loc')
                details = response[alert].get('details')
                timestamps = response[alert].get('timestamps')
                includes = response[alert].get('includes') #TODO: wxzones?
                place = response[alert].get('place')
                profile = response[alert].get('profile')
                cell = details.get('loc')
                if data_temp['alerts'].get(cell) is None:
                    data_temp['alerts'][cell] = list()
                alert_tmp = dict()
                alert_tmp['id'] = details.get('type')
                alert_tmp['alert_id'] = response[alert].get('id')
                alert_tmp['effective'] = timestamps.get('issuedISO')
                alert_tmp['onset'] = timestamps.get('beginsISO')
                alert_tmp['expires'] = timestamps.get('expiresISO')
                alert_tmp['category'] = details.get('cat')
                alert_tmp['response_type'] = "prepare"
                alert_tmp['urgency'] = "immediate"
                if weeutil.weeutil.to_bool(details.get('emergency', False)):
                    alert_tmp['severity'] = "extreme"
                else:
                    alert_tmp['severity'] = "moderate"
                alert_tmp['certainty'] = "likely"
                alert_tmp['event_code'] = details.get('priority')
                alert_tmp['event_en'] = details.get('cat')
                alert_tmp['event_de'] = details.get('cat')
                alert_tmp['headline_en'] = details.get('name')
                alert_tmp['headline_de'] = details.get('name')
                alert_tmp['description_en'] = details.get('bodyFull')
                alert_tmp['description_de'] = details.get('bodyFull')
                alert_tmp['instruction_en'] = None
                alert_tmp['instruction_de'] = None
                data_temp['alerts'][cell].append(alert_tmp)

                if data_temp['locations'].get(cell) is None:
                    data_temp['locations'][cell] = dict()
                    data_temp['locations'][cell]['warn_cell_id'] = cell
                    data_temp['locations'][cell]['name'] = place.get('name')
                    data_temp['locations'][cell]['name_short'] = place.get('name')
                    data_temp['locations'][cell]['district'] = place.get('name')
                    data_temp['locations'][cell]['state'] = place.get('state')
                    data_temp['locations'][cell]['state_short'] = place.get('state')
                
                if data_temp[self.source_id].get(cell) is not None:
                    cell = "%s_%s" % (details.get('loc'), str(alert))
                data_temp[self.source_id][cell] = dict()
                data_temp[self.source_id][cell]['success'] = True
                data_temp[self.source_id][cell]['code'] = details.get('type')
                data_temp[self.source_id][cell]['description'] = details.get('name')
                data_temp[self.source_id][cell]['cat'] = details.get('cat')
                data_temp[self.source_id][cell]['body'] = details.get('body')
                data_temp[self.source_id][cell]['bodyFull'] = details.get('bodyFull')
                data_temp[self.source_id][cell]['active'] = weeutil.weeutil.to_bool(response[alert].get('active'))
                data_temp[self.source_id][cell]['emergency'] = details.get('emergency')
                data_temp[self.source_id][cell]['issued'] = timestamps.get('issued')
                data_temp[self.source_id][cell]['begins'] = timestamps.get('begins')
                data_temp[self.source_id][cell]['expires'] = timestamps.get('expires')
                data_temp[self.source_id][cell]['added'] = timestamps.get('added')
                data_temp[self.source_id][cell]['dataSource'] = response[alert].get('dataSource')
                data_temp[self.source_id][cell]['priority'] = details.get('priority')
                data_temp[self.source_id][cell]['color'] = details.get('color')
                data_temp[self.source_id][cell]['county'] = place.get('county')
                data_temp[self.source_id][cell]['country'] = place.get('country')
                data_temp[self.source_id][cell]['lat'] = loc.get('lat')
                data_temp[self.source_id][cell]['lon'] = loc.get('long')
                data_temp[self.source_id][cell]['tz'] = profile.get('tz')
        except Exception as e:
            exception_output(self.name, e)
            cell = self.station
            data_temp['alerts'][cell] = list()
            data_temp['locations'][cell] = dict()
            data_temp[self.source_id][cell] = dict()
            data_temp[self.source_id][cell]['success'] = False
            data_temp[self.source_id][cell]['code'] = e.__class__.__name__
            data_temp[self.source_id][cell]['description'] = e

        if debug > 2:
            logdbg("thread '%s': prepare_api_data data_temp %s" % (self.name, json.dumps(data_temp)))

        return data_temp


    def get_data_api(self):
        """ download and process Aeris API warnings data """

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

        api_id = apiin_dict.get('api_id')
        api_secret = apiin_dict.get('api_secret')

        if api_id is None:
            if log_failure or debug > 0:
                loginf("thread '%s': get_data_api required 'api_id' in the [api_in] section of station %s is not valid" % (self.name, self.station))
            return False
        if api_secret is None:
            if log_failure or debug > 0:
                loginf("thread '%s': get_data_api required 'api_secret' in the [api_in] section of station %s is not valid" % (self.name, self.station))
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

        baseurl = 'https://api.aerisapi.com/alerts/%s,%s?format=json&client_id=%s&client_secret=%s'
        baseurl = baseurl % (str(self.lat), str(self.lon), api_id, api_secret)

        # Params
        params = '&lang=de'

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
                    self.data_temp = None
                    return False
        except Exception as e:
            exception_output(self.name, e)
            self.data_temp = None
            return False

        if debug > 2:
            logdbg("thread '%s': get_data_api api result %s" % (self.name, json.dumps(apidata)))

        # prepare data
        self.data_temp = self.prepare_api_data(apidata, lang, unitsystem, url,
                                               debug=debug, log_success=log_success, log_failure=log_failure)

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

        self.icon_path_belchertown = self.config.get('icon_path_belchertown', 'images')
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
                loginf("thread '%s': get_data_results is diabled. Enable it in the [result_in] section of station %s" % (self.name, self.station))
            return False

        if debug > 0:
            logdbg("thread '%s': get_data_results started" % (self.name))
        if debug > 2:
            logdbg("thread '%s': get_data_results config %s" % (self.name, json.dumps(resultin_dict)))

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
# Class WarnWX
#
# ============================================================================

class WarnWX(StdService):

    def _create_brightsky_thread(self, thread_name, stations_dict):
        thread_name = "%s_%s" % (SERVICEID, thread_name)
        self.threads[SERVICEID][thread_name] = BRIGHTSKYthread(thread_name, stations_dict,
                    debug=weeutil.weeutil.to_int(stations_dict.get('debug', self.debug)),
                    log_success=weeutil.weeutil.to_bool(stations_dict.get('log_success',self.log_success)),
                    log_failure=weeutil.weeutil.to_bool(stations_dict.get('log_failure',self.log_failure)))
        self.threads[SERVICEID][thread_name].start()


    def _create_aeris_thread(self, thread_name, stations_dict):
        thread_name = "%s_%s" % (SERVICEID, thread_name)
        self.threads[SERVICEID][thread_name] = AERISthread(thread_name, stations_dict,
                    debug=weeutil.weeutil.to_int(stations_dict.get('debug', self.debug)),
                    log_success=weeutil.weeutil.to_bool(stations_dict.get('log_success',self.log_success)),
                    log_failure=weeutil.weeutil.to_bool(stations_dict.get('log_failure',self.log_failure)))
        self.threads[SERVICEID][thread_name].start()


    def _create_total_thread(self, thread_name, stations_dict):
        thread_name = "%s_%s" % (SERVICEID, thread_name)
        self.threads['worker'][thread_name] = TOTALthread(thread_name, stations_dict,
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
            logdbg("Service 'WarnWX': check_section section '%s' started" % (section))

        cancel = False

        # new section configurations apply?
        debug = weeutil.weeutil.to_int(section_dict.get('debug', self.service_dict.get('debug', 0)))
        log_success = weeutil.weeutil.to_bool(section_dict.get('log_success', self.service_dict.get('log_success', False)))
        log_failure = weeutil.weeutil.to_bool(section_dict.get('log_failure', self.service_dict.get('log_success', True)))

        # Check required provider
        provider = section_dict.get('provider')
        if provider: provider = provider.lower()
        if provider not in ('brightsky', 'aeris', 'total'):
            if log_failure or debug > 0:
                logerr("Service 'WarnWX': check_section section '%s' warnings service provider '%s' is not valid. Skip Section" % (section, provider))
            cancel = True
            return cancel, section_dict

        # check required station 
        station = section_dict.get('station')
        # if provider in ('brightsky', 'aeris', 'total') and station is None:
            # if log_failure or debug > 0:
                # logerr("Service 'ForecastWX': check_section section '%s' forecast service provider '%s' - station '%s' is not valid. Skip Section" % (section, provider, station))
            # cancel = True
            # return cancel, section_dict

        # set default station if not selected and lat or lon is None
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
            loginf("Service 'WarnWX': check_section section '%s' finished" % (section))

        return cancel, section_dict



    def __init__(self, engine, config_dict):
        super(WarnWX,self).__init__(engine, config_dict)

        self.service_dict = weeutil.config.accumulateLeaves(config_dict.get('warnwx',configobj.ConfigObj()))
        # service enabled?
        if not weeutil.weeutil.to_bool(self.service_dict.get('enable', False)):
            loginf("Service 'WarnWX': service is disabled. Enable it in the [warnwx] section of weewx.conf")
            return
        loginf("Service 'WarnWX': service is enabled")

        self.threads = dict()
        self.threads[SERVICEID] = dict()
        self.threads['worker'] = dict()

        #general configs
        self.debug = weeutil.weeutil.to_int(self.service_dict.get('debug', 0))
        self.log_success = weeutil.weeutil.to_bool(self.service_dict.get('log_success', True))
        self.log_failure = weeutil.weeutil.to_bool(self.service_dict.get('log_failure', True))
        if self.debug > 0:
            logdbg("Service 'WarnWX': init started")

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
        warnwx_dict = config_dict.get('warnwx', configobj.ConfigObj())
        if self.debug > 2:
            logdbg("Service 'WarnWX': warnwx_dict %s" % (str(json.dumps(warnwx_dict))))

        # section with current weather services only
        current_dict = config_dict.get('warnwx',configobj.ConfigObj()).get('warnings',configobj.ConfigObj())
        if self.debug > 2:
            logdbg("Service 'WarnWX': current_dict %s" % (str(json.dumps(current_dict))))

        stations_dict = current_dict.get('stations',configobj.ConfigObj())
        for section in stations_dict.sections:
            if not weeutil.weeutil.to_bool(stations_dict[section].get('enable', False)):
                if self.log_success or self.debug > 0:
                    loginf("Service 'WarnWX': init current section '%s' is not enabled. Skip section" % section)
                continue

            # build section config
            section_dict = weeutil.config.accumulateLeaves(stations_dict[section])
            provider = str(section_dict.get('provider')).lower()

            # update general config
            section_dict['result_in'] = weeutil.config.deep_copy(warnwx_dict.get('result_in'))
            section_dict['api_in'] = weeutil.config.deep_copy(warnwx_dict.get('api_in'))
            section_dict['api_out'] = weeutil.config.deep_copy(warnwx_dict.get('api_out'))
            section_dict['mqtt_in'] = weeutil.config.deep_copy(warnwx_dict.get('mqtt_in'))
            section_dict['mqtt_out'] = weeutil.config.deep_copy(warnwx_dict.get('mqtt_out'))
            section_dict['file_in'] = weeutil.config.deep_copy(warnwx_dict.get('file_in'))
            section_dict['file_out'] = weeutil.config.deep_copy(warnwx_dict.get('file_out'))
            section_dict['db_in'] = weeutil.config.deep_copy(warnwx_dict.get('db_in'))
            section_dict['db_out'] = weeutil.config.deep_copy(warnwx_dict.get('db_out'))

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

            # start configured warnings weather threads
            if provider == 'brightsky':
                self._create_brightsky_thread(section, thread_config)
            elif provider == 'aeris':
                self._create_aeris_thread(section, thread_config)
            elif provider == 'total':
                self._create_total_thread(section, thread_config)
            elif self.log_failure or self.debug > 0:
                logerr("Service 'WarnWX': init section '%s' unknown warnings service provider '%s'" % (section, provider))

        if  __name__!='__main__':
            self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet)
            self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

        if self.log_success or self.debug > 0:
            loginf("Service 'WarnWX': init finished. Number of current threads started: %d" % (len(self.threads[SERVICEID])))
        if len(self.threads[SERVICEID]) < 1:
            loginf("Service 'WarnWX': no threads have been started. Service 'WarnWX' exits now")
            return
