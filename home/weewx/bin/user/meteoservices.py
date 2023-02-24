# $Id: Meteoservices.py 1201 07-07-2021 3.2$
# Copyright 2020 Dipl. Met. Frank Bandle 
# based on Scripts written by M.Wall
# Thanks Luc Heijst for testing and correction
"""
Upload data to Meteoservices.net
  https://channel2.meteo-services.com/stations/

[StdRESTful]
    [[Meteoservices]]
        stationid = INSERT_STATIONID_HERE
        password  = INSERT_PASSWORD_HERE
"""

import sys
import time
import syslog

import weewx
import weewx.restx
import weewx.units
import weewx.manager
from weeutil.weeutil import to_bool, accumulateLeaves


VERSION = "3.2"

if weewx.__version__ < "3":
    raise weewx.UnsupportedFeature("weewx 3 is required, found %s" %
                                   weewx.__version__)

if weewx.__version__ >= '4':
    import logging
    logger = logging.getLogger(__name__)
    severityMap = {syslog.LOG_DEBUG: logging.DEBUG,
                   syslog.LOG_INFO:  logging.INFO,
                   syslog.LOG_ERR:   logging.ERROR}

try:
    # try Python 3 modules first
    import queue
    from urllib.parse import urlencode
    from urllib.request import urlopen, Request
except ImportError:
    # assume Python 2
    import Queue as queue
    from urllib import urlencode
    from urllib2 import urlopen, Request


def logmsg(level, msg):
    text = 'restx: Meteoservices: %s' % msg
    if weewx.__version__ < '4':
        syslog.syslog(level, text)
    else:
        logger.log(severityMap[level], text)


def logdbg(msg):
    logmsg(syslog.LOG_DEBUG, msg)


def loginf(msg):
    logmsg(syslog.LOG_INFO, msg)


def logerr(msg):
    logmsg(syslog.LOG_ERR, msg)


class Meteoservices(weewx.restx.StdRESTbase):
    def __init__(self, engine, config_dict):
        """This service recognizes standard restful options plus the following:

        stationid = INSERT_STATIONID_HERE
        password  = INSERT_PASSWORD_HERE
        enable    = true/false

        latitude: Station latitude in decimal degrees
        Default is station latitude

        longitude: Station longitude in decimal degrees
        Default is station longitude

        Enable: Enable uploads woth this service
        Default is true
        """
        super(Meteoservices, self).__init__(engine, config_dict)
        loginf("service version is %s" % VERSION)
        try:
            site_dict = config_dict['StdRESTful']['Meteoservices']
            site_dict = accumulateLeaves(site_dict, max_level=1)
        except KeyError as e:
            logerr("Data will not be posted: Missing option %s" % e)
            return
        self.enable_driver = to_bool(site_dict.get('enable', True))
        if not self.enable_driver:
            loginf('Driver disabled, skipping uploads')
            return
        # Get rid of the no longer needed key 'enable':
        site_dict.pop('enable', None)
        site_dict.setdefault('latitude', engine.stn_info.latitude_f)
        site_dict.setdefault('longitude', engine.stn_info.longitude_f)
        site_dict.setdefault('altitude', engine.stn_info.altitude_vt[0])
        site_dict['manager_dict'] = weewx.manager.get_manager_dict(
            config_dict['DataBindings'], config_dict['Databases'], 'wx_binding')

        self.archive_queue = queue.Queue()
        self.archive_thread = MeteoservicesThread(self.archive_queue, **site_dict)
        self.archive_thread.start()
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)
        loginf("Data will be uploaded for station id %s" % site_dict['stationid'])

    def new_archive_record(self, event):
        if not self.enable_driver:
            return
        self.archive_queue.put(event.record)


class MeteoservicesThread(weewx.restx.RESTThread):
    def format_url(self, _):
        pass

    _SERVER_URL = 'https://channel1.meteo-services.com/stations/index.php'
    _DATA_MAP = {'winddir':       ('windDir',         '%.0f', 1.0),   # degrees
                 'windspeed':     ('windSpeed',       '%.1f', 0.2777777777),  # m/s
                 'windgust':      ('windGust',        '%.1f', 0.2777777777),  # m/s
                 't2m':           ('outTemp',         '%.1f', 1.0),   # C
                 'relhum':        ('outHumidity',     '%.0f', 1.0),   # percent
                 'press':         ('barometer',       '%.3f', 1.0),   # hpa?
                 'rainh':         ('hourRain',        '%.2f', 10.0),  # mm
                 'raind':         ('dayRain',         '%.2f', 10.0),  # mm
                 'rainrate':      ('rainRate',        '%.2f', 10.0),  # mm/hr
                 'uvi':           ('UV',              '%.1f', 1.0),   # index * 1
                 'radi':          ('radiation',       '%.1f', 1.0),   # W/m^2 * 1
                 'et':            ('ET',              '%.5f', 10.0),  # mm * 1
                 'wchill':        ('windchill',       '%.1f', 1.0),   # C * 1
                 'heat':          ('heatindex',       '%.1f', 1.0),   # C * 1
                 'dew2m':         ('dewpoint',        '%.1f', 1.0),   # C * 1
                 'rxsignal':      ('rxCheckPercent',  '%.0f', 1.0),   # percent / dB
                 'cloudbase':     ('cloudbase',       '%.1f', 1.0),   # m
                 'windrun':       ('windrun',         '%.1f', 1.0),   # m
                 'humidex':       ('humidex',         '%.1f', 1.0),   #
                 'appTemp':       ('appTemp',         '%.1f', 1.0),   # C
                 'soiltemp':      ('soilTemp1',       '%.1f', 1.0),   # C
                 'soiltemp2':     ('soilTemp2',       '%.1f', 1.0),   # C
                 'soiltemp3':     ('soilTemp3',       '%.1f', 1.0),   # C
                 'soiltemp4':     ('soilTemp4',       '%.1f', 1.0),   # C
                 'soilmoisture':  ('soilMoist1',      '%.1f', 1.0),   # %
                 'soilmoisture2': ('soilMoist2',      '%.1f', 1.0),   # %
                 'soilmoisture3': ('soilMoist3',      '%.1f', 1.0),   # %
                 'soilmoisture4': ('soilMoist4',      '%.1f', 1.0),   # %
                 'leafwetness':   ('leafWet1',        '%.1f', 1.0),   # %
                 'leafwetness2':  ('leafWet2',        '%.1f', 1.0),   # %
                 #'t005m':         ('extraTemp1',      '%.1f', 1.0),   # C # PWS Weiherhammer N/A, unused extraTemp6 as dummy
                 't005m':         ('extraTemp6',      '%.1f', 1.0),   # C
                 #'temp3':         ('extraTemp2',      '%.1f', 1.0),   # C # PWS Weiherhammer N/A, unused extraTemp7 as dummy
                 'temp3':         ('extraTemp7',      '%.1f', 1.0),   # C
                 #'temp4':         ('extraTemp3',      '%.1f', 1.0),   # C # PWS Weiherhammer N/A, unused extraTemp8 as dummy
                 'temp4':         ('extraTemp8',      '%.1f', 1.0),   # C
                 #'humidity2':     ('extraHumid1',     '%.0f', 1.0),   # % # PWS Weiherhammer N/A, unused extraHumid7 as dummy
                 'humidity2':     ('extraHumid7',     '%.0f', 1.0),   # %
                 #'humidity3':     ('extraHumid2',     '%.0f', 1.0),   # % # PWS Weiherhammer N/A, unused extraHumid8 as dummy
                 'humidity3':     ('extraHumid8',     '%.0f', 1.0),   # %
                 'txbattery':     ('txBatteryStatus', '%.0f', 1.0),   # %
                 }

    def __init__(self, archive_queue,
                 stationid, latitude, longitude, altitude,
                 manager_dict,
                 server_url=_SERVER_URL, skip_upload=False,
                 post_interval=None, max_backlog=sys.maxsize, stale=None,
                 log_success=True, log_failure=True,
                 timeout=60, max_tries=3, retry_wait=5, password=None):
        super(MeteoservicesThread, self).__init__(archive_queue,
                                               protocol_name='Meteoservices',
                                               manager_dict=manager_dict,
                                               post_interval=post_interval,
                                               max_backlog=max_backlog,
                                               stale=stale,
                                               log_success=log_success,
                                               log_failure=log_failure,
                                               max_tries=max_tries,
                                               timeout=timeout,
                                               retry_wait=retry_wait)
        self.latitude = float(latitude)
        self.longitude = float(longitude)
        self.altitude = float(altitude)
        self.stationid = stationid
        self.server_url = server_url
        self.skip_upload = to_bool(skip_upload)
        self.password = password

    def process_record(self, record, dbm):
        r = self.get_record(record, dbm)
        data = self.get_data(r)
        url = urlencode(data).encode()
        if self.skip_upload:
            loginf("skipping upload")
            return
        req = Request(self.server_url, url)
        logdbg("Data uploaded to %s is: (%s)" % (self.server_url, url))
        req.get_method = lambda: 'POST'
        req.add_header("User-Agent", "weewx/%s" % weewx.__version__)
        self.post_with_retries(req)

    def check_response(self, response):
        txt = response.read().decode()
        if txt.find('invalid-login-data') >= 0:
            raise weewx.restx.BadLogin(txt)
        elif not txt.startswith('INSERT'):
            raise weewx.restx.FailedPost("Server returned '%s'" % txt)

    def get_data(self, in_record):
        # put everything into the right units
        record = weewx.units.to_METRIC(in_record)

        # put data into expected scaling, structure, and format
        values = {
            'lat': str(self.latitude),
            'long': str(self.longitude),
            'alt': str(self.altitude),
            'stationid': self.stationid,
            'prec_time': 60,
            'datum': time.strftime('%Y%m%d%H%M', time.localtime(record['dateTime'])),
            'utcstamp': int(record['dateTime'])
        }
        for key in self._DATA_MAP:
            rkey = self._DATA_MAP[key][0]
            if rkey in record and record[rkey] is not None:
                v = record[rkey] * self._DATA_MAP[key][2]
                values[key] = self._DATA_MAP[key][1] % v

        return values
