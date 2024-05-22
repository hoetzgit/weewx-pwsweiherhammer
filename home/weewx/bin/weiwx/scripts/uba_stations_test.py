#!/usr/bin/python3
# Copyright (C) 2023 Henry Ott

import threading
import configobj
import csv
import io
import zipfile
import time
import dateutil.parser
import random
import copy
import os
import shutil
import paho.mqtt.publish as mqtt_publish
import paho.mqtt.subscribe as mqtt_subscribe
import requests
from requests.exceptions import Timeout
import datetime
from datetime import timezone
import pytz
import json
from json import JSONDecodeError

if __name__ == '__main__':

    import sys
    sys.path.append('/home/weewx')
    sys.path.append('/home/weewx/bin')
    sys.path.append('/home/weewx/bin/weiwx')
    sys.path.append('/home/weewx/bin/weiwx/aqi')

    def logdbg(x):
        print('DEBUG',x)
    def loginf(x):
        print('INFO',x)
    def logerr(x):
        print('ERROR',x)
    def logwrn(x):
        print('WARNING',x)

else:

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

from calculate import Calculate

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
def get_dateISOfromTimstamp(timestamp, tz):
    timezone = pytz.timezone(tz)
    datetz = datetime.datetime.fromtimestamp(timestamp, timezone)
    return datetz.isoformat()

@staticmethod
def extrequest(thread_name, url, debug=0, log_success=False, log_failure=True, text=False):
    """ download  """

    if debug > 0:
        logdbg("thread '%s': extrequest url '%s' started" % (thread_name, url))

    headers={'User-Agent': 'currentaq'}
    response = requests.get(url, headers=headers, timeout=10)
    content_type = response.headers.get("Content-Type")
    if debug > 5:
        logdbg("thread '%s': extrequest response content_type '%s'" % (thread_name, str(content_type)))
    if response.status_code >=200 and response.status_code <= 206:
        if log_success or debug > 0:
            loginf("thread '%s': extrequest finished with success, http status code %s" % (thread_name, str(response.status_code)))
        if content_type:
            if "application/json" in content_type:
                try:
                    resp = response.json()
                    return resp, response.status_code
                except JSONDecodeError:
                    if log_failure or debug > 0:
                        logerr("thread '%s': extrequest finished with error, response could not be serialized" % (thread_name))
                        logerr("thread '%s': extrequest url %s" % (thread_name, url))
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
        logerr("thread '%s': extrequest finished with error, http status code %s" % (thread_name, str(response.status_code)))
        logerr("thread '%s': extrequest url %s" % (thread_name, url))
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
                    logerr("thread '%s': extrequest finished with error '%s - %s'" % (thread_name, str(response.status_code), reason))
                    logerr("thread '%s': extrequest url %s" % (thread_name, url))
                    return None, response.status_code
            logerr("thread '%s': extrequest finished with error '%s - %s'" % (thread_name, str(response.status_code), response.reason))
            logerr("thread '%s': extrequest url %s" % (thread_name, url))
            return None, response.status_code
    else:
        if log_failure or debug > 0:
            logerr("thread '%s': extrequest finished with error '%s - %s'" % (thread_name, str(response.status_code), response.reason))
            logerr("thread '%s': extrequest url %s" % (thread_name, url))
        return None, response.status_code

class Stations(object):
    def __init__(self, station, debug=0, log_success=False, log_failure=True, text=False):
        self.debug = debug
        self.log_success = log_success
        self.log_failure = log_failure
        self.name = 'Stations'
        self.lang = 'de'
        self.station = station

    def getMetaData(self):
        if self.debug > 0:
            logdbg("'%s': getApiRecord started" % (self.name))

        # Dates
        today_date = time.time()
        #yesterday_date = today_date-86400 # 1 day
        yesterday_date = today_date - 172800 #2 days, Period increased because sometimes no measurements were available.
        today_date = time.localtime(today_date)
        today_date = time.strftime('%Y-%m-%d', today_date)
        yesterday_date = time.localtime(yesterday_date)
        yesterday_date = time.strftime('%Y-%m-%d', yesterday_date)

        # get Meta data
        baseurl = "https://www.umweltbundesamt.de/api/air_data/v2/meta/json?use=measure"
        params = '&lang=%s&date_from=%s&date_to=%s' % (self.lang, yesterday_date, today_date)
        url = baseurl + params

        if self.debug > 0:
            logdbg("'%s': getApiRecord url %s" % (self.name, url))

        apidata = dict()
        try:
            response, code = extrequest(self.name, url, debug=self.debug, log_success=self.log_success, log_failure=self.log_failure, text=False)
            if response is not None:
                apidata = response
            elif self.log_failure or self.debug > 0:
                logerr("'%s': getApiRecord api did not send data" % self.name)
                return False
        except Exception as e:
            exception_output(self.name, e)
            return False

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
        stations = apidata.get('stations')
        station = stations.get(self.station)
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
        # if self.debug > 0:
            # logdbg("'%s': getApiRecord station_dict %s" % (self.name, json.dumps(station_dict, indent=4)))
        networkId = station[9]
        settingsId = station[10]
        typeId = station[11]

        # "components": [
          # "0: string - component id",
          # "1: string - component code",
          # "2: string - component symbol",
          # "3: string - component unit",
          # "4: string - component name"
        # ],
        components = apidata.get('components')
        components_dict = dict()
        for id, component in components.items():
            components_dict[id] = dict()
            components_dict[id]['id'] = component[0]
            components_dict[id]['code'] = component[1]
            components_dict[id]['symbol'] = component[2]
            components_dict[id]['unit'] = component[3]
            components_dict[id]['name'] = component[4]
        # if self.debug > 0:
            # logdbg("'%s': getApiRecord components %s" % (self.name, json.dumps(components_dict, indent=4)))

        # "networks": [
          # "0: string - network id",
          # "1: string - network code",
          # "2: string - network name"
        # ],
        networks = apidata.get('networks')
        network = networks.get(networkId)
        network_dict = dict()
        network_dict['id'] = network[0]
        network_dict['code'] = network[1]
        network_dict['name'] = network[2]
        # if self.debug > 0:
            # logdbg("'%s': getApiRecord network %s" % (self.name, json.dumps(network_dict, indent=4)))

        # "scopes": [
          # "0: string - scope id",
          # "1: string - scope code",
          # "2: string - scope time base",
          # "3: string - scope time scope",
          # "4: string - scope time is max",
          # "5: string - scope name"
        # ],
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
        # if self.debug > 0:
            # logdbg("'%s': getApiRecord scopes %s" % (self.name, json.dumps(scopes_dict, indent=4)))

        # "limits": {
          # "use = airquality|measure": [
            # "0: string - Id of scope",
            # "1: string - Id of component",
            # "2: string - Id of station",
            # "3: string - Minimum datetime of start (CET)",
            # "4: string - Maximum datetime of start (CET)"
        # ],
        # limits = apidata.get('limits')
        # limit_data = dict()
        # for limit, values in limits.items():
            # if len(values) > 2 and values[2] == '506':
                # limit_data[limit] = dict()
                # scopeId = values[0]
                # componentId = values[1]
                # limit_data[limit]['scopes'] = dict()
                # limit_data[limit]['scopes'][scopeId] = scopes_dict.get(scopeId)
                # limit_data[limit]['components'] = dict()
                # limit_data[limit]['components'][componentId] = components_dict.get(componentId)
                # limit_data[limit]['minStart'] = values[3]
                # limit_data[limit]['maxStart'] = values[4]
                # if self.debug > 0:
                    # # logdbg("'%s': getApiRecord limit %s" % (self.name, json.dumps(limit_data, indent=4)))

        # "xref": [
          # "0: string - Id of component",
          # "1: string - Id of scope",
          # "2: string - Flag if this combination of component and scope has a map",
          # "3: string - Flag if this combination of component and scope has an alternative map",
          # "4: string - Flag if this combination of component and scope is an hourly value"
        # ],
        xref = apidata.get('xref')

        baseurl = "https://www.umweltbundesamt.de/api/air_data/v2/stationsettings/json"
        params = '?lang=%s' % (self.lang)
        url = baseurl + params
        apidata = dict()
        try:
            response, code = extrequest(self.name, url, debug=self.debug, log_success=self.log_success, log_failure=self.log_failure, text=False)
            if response is not None:
                apidata = response
            elif self.log_failure or self.debug > 0:
                logerr("'%s': getApiRecord api did not send data" % self.name)
                return False
        except Exception as e:
            exception_output(self.name, e)
            return False

        settings = apidata.get(settingsId)
        settings_dict = dict()
        settings_dict['id'] = settings[0]
        settings_dict['name'] = settings[1]
        settings_dict['shortname'] = settings[2]
        settings_dict['url'] = url
        # if self.debug > 0:
            # logdbg("'%s': getApiRecord settings %s" % (self.name, json.dumps(settings_dict, indent=4)))

        baseurl = "https://www.umweltbundesamt.de/api/air_data/v2/stationtypes/json"
        params = '?lang=%s' % (self.lang)
        url = baseurl + params
        apidata = dict()
        try:
            response, code = extrequest(self.name, url, debug=self.debug, log_success=self.log_success, log_failure=self.log_failure, text=False)
            if response is not None:
                apidata = response
            elif self.log_failure or self.debug > 0:
                logerr("'%s': getApiRecord api did not send data" % self.name)
                return False
        except Exception as e:
            exception_output(self.name, e)
            return False

        types = apidata.get(typeId)
        types_dict = dict()
        types_dict['id'] = types[0]
        types_dict['name'] = types[1]
        types_dict['url'] = url
        # if self.debug > 0:
            # logdbg("'%s': getApiRecord types %s" % (self.name, json.dumps(types_dict, indent=4)))

        # Station 506/509 get components 1, 3, 5
        # baseurl = "https://www.umweltbundesamt.de/api/air_data/v2/airquality/json"
        # params = '?lang=%s&date_from=%s&date_to=%s&station=%s' % (self.lang, yesterday_date, today_date, self.station)

        # Station 506/509 get component 9 or all component valid for the station
        # https://www.umweltbundesamt.de/api/air_data/v2/measures/json?date_from=2023-07-31&date_to=2023-08-01&ang=de&station=506&component=9
        baseurl = "https://www.umweltbundesamt.de/api/air_data/v2/measures/json"
        params = '?date_from=%s&date_to=%s&station=%s' % (yesterday_date, today_date, self.station)
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
        for comp, values in components.items():
            if comp in ('1', '9'):
                scope = '6'
            else:
                scope = '2'
            url = baseurl + (paracomp % (scope, comp))

            apidata = dict()
            try:
                response, code = extrequest(self.name, url, debug=self.debug, log_success=self.log_success, log_failure=self.log_failure, text=False)
                if response is not None:
                    apidata = response
                elif self.log_failure or self.debug > 0:
                    logerr("'%s': getApiRecord api did not send data" % self.name)
                    return False
            except Exception as e:
                exception_output(self.name, e)
                return False

            apidata = apidata.get('data')
            if apidata is None:
                continue
            apidata = apidata.get(self.station)
            if apidata is None:
                continue
            measures = list(apidata.items())[-1]
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
            cet_date = datetime.datetime.strptime(measures[0], '%Y-%m-%d %H:%M:%S')
            # UTC timestamp
            utc_started_ts = weeutil.weeutil.to_int(cet_date.timestamp()) + 3600 # +01:00 => +00:00

            # end date
            measures = measures[1]
            # Datetime-Object from UBA date end (CET) = +01:00
            cet_date = datetime.datetime.strptime(measures[3], '%Y-%m-%d %H:%M:%S')
            # UTC timestamp
            utc_generated_ts = weeutil.weeutil.to_int(cet_date.timestamp()) + 3600 # +01:00 => +00:00
            if utc_generated_ts > generatedMax:
                generatedMax = utc_generated_ts
            if utc_generated_ts < generatedMin:
                generatedMin = utc_generated_ts

            # values
            data_dict[comp]['value'] = measures[2]
            data_dict[comp]['started'] = utc_started_ts
            data_dict[comp]['startedISO'] = get_dateISOfromTimstamp(utc_started_ts, 'Europe/Berlin')
            data_dict[comp]['generated'] = utc_generated_ts
            data_dict[comp]['generatedISO'] = get_dateISOfromTimstamp(utc_generated_ts, 'Europe/Berlin')
            data_dict[comp]['component'] = components_dict.get(comp)
            data_dict[comp]['scope'] = scopes_dict.get(scope)
            data_dict[comp]['url'] = url
            #logdbg("'%s': getApiRecord comp %s measures %s " % (self.name, comp, json.dumps(data_dict, indent=4)))

        # Result Data
        result_dict = dict()
        result_dict['station'] = station_dict
        result_dict['network'] = network_dict
        result_dict['type'] = types_dict
        result_dict['settings'] = settings_dict
        result_dict['data'] = dict()
        result_dict['data']['generatedMin'] = generatedMin
        result_dict['data']['generatedMinISO'] = get_dateISOfromTimstamp(generatedMin, 'Europe/Berlin')
        result_dict['data']['generatedMax'] = generatedMax
        result_dict['data']['generatedMaxISO'] = get_dateISOfromTimstamp(generatedMax, 'Europe/Berlin')
        result_dict['data']['components'] = data_dict
        logdbg("'%s': getApiRecord result_dict %s " % (self.name, json.dumps(result_dict, indent=4)))


# ============================================================================
#
# __main__
#
# ============================================================================

if __name__ == '__main__':

    stations = Stations(station='506', debug=1, log_success=True, log_failure=True, text=False)
    stations.getMetaData()
    stations = Stations(station='509', debug=1, log_success=True, log_failure=True, text=False)
    stations.getMetaData()
