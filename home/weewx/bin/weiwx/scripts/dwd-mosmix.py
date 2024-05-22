#!/usr/bin/python3
# Wettervorhersage
# Copyright (C) 2022, 2023 Johanna Roedenbeck
# licensed under the terms of the General Public License (GPL) v3

from __future__ import absolute_import
from __future__ import print_function
from __future__ import with_statement

"""
    This script is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This script is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
"""

"""
   station list see:
   https://www.dwd.de/DE/leistungen/met_verfahren_mosmix/mosmix_stationskatalog.cfg?view=nasPublication&nn=16102
   
"""

"""
   Fuer die Reihenfolge bei den Tagesvorsagen ist mindestens Python 3.6
   erforderlich. 
"""

import json
import time
import datetime
import configobj
import os.path
import shutil
import requests
import csv
import io
import math
import urllib.parse
from email.utils import formatdate
import html.parser
import zipfile
from dateutil import tz

# pyephem is used to determine night and day time for choosing the
# appropriate weather icon
try:
    import ephem
    has_pyephem = True
except ImportError:
    has_pyephem = False

# geopy is used to get state and country from latitude/longitude
try:
    from geopy.geocoders import Nominatim
    from geopy import distance
    has_geopy = True
except ImportError:
    has_geopy = False

# sqlite3
try:
    import sqlite3
    has_sqlite = True
except ImportError:
    has_sqlite = False

    
if __name__ == "__main__":
    import optparse
    import sys
    def loginf(x):
        print("INFO", x, file=sys.stderr)
    def logerr(x):
        print("ERROR", x, file=sys.stderr)


DEFAULT_LOCAL_FORECAST_URL = "https://opendata.dwd.de/weather/local_forecasts"

LOCATION_DICT = {
  'Döbeln':'P0291',
  'Wurzen':'P0292',
  'Delitzsch':'EW005',
  'Leipzig':'10471',
  'Oschatz':'10480',
  'Dresden':'10487',
  'Chemnitz':'10577',
  'Görlitz':'10499',
  'Fichtelberg':'10578',
  'Weiden':'10688'}

MOSMIX_DICT = {
  'l':'MOSMIX_L',
  's':'MOSMIX_S'}

OBS_DICT = {
  'FF': lambda x: x*3.6,     # m/s --> km/h  wind speed
  'FX1': lambda x: x*3.6,    # m/s --> km/h  wind gust within last hour
  'FX3': lambda x: x*3.6,    # m/s --> km/h  wind gust within last 3 hours
  'FXh': lambda x: x*3.6,    # m/s --> km/h  wind gust within last 12 hours
  'PPPP':lambda x: x*0.01,   # Pa  --> hPa   surface pressure, reduced
  'T5cm':lambda x: x-273.15, # K   --> °C    temperature 5cm above surface
  'Td':lambda x: x-273.15,   # K   --> °C    dewpoint 2m above surface
  'TG':lambda x: x-273.15,   # K   --> °C    min surface temp 5cm 12 hours
  'TM':lambda x: x-273.15,   # K   --> °C    mean temp last 24 hours
  'TN':lambda x: x-273.15,   # K   --> °C    min temp last 12 hours
  'TTT':lambda x: x-273.15,  # K   --> °C    temperature 2m above surface
  'TX':lambda x: x-273.15,   # K   --> °C    max temp last 12 hours
  'Rad1h':lambda x: x/3.6}   # kJ  --> Wh    Global Irradiance
  
def get_mos_url(location, mosmix):
    if location:
        location = LOCATION_DICT.get(location,location)
        location = "single_stations/%s/kml/MOSMIX_L_LATEST_%s.kmz" % (location,location)
    else:
        location = "all_stations/kml/MOSMIX_L_LATEST.kmz"
    return DEFAULT_LOCAL_FORECAST_URL+'/'+"mos"+"/"+MOSMIX_DICT.get(mosmix.lower(),mosmix)+"/"+location

# https://www.dwd.de/DE/leistungen/opendata/help/schluessel_datenformate/kml/mosmix_element_weather_xls.xlsx?__blob=publicationFile&v=6
# ww, german description, English description, severity, Belchertown icon, DWD icon, Aeris icon, Aeris coded weather
WW_LIST = [
    (95,'leichtes oder mäßiges Gewitter mit Regen oder Schnee','slight or moderate thunderstorm with rain or snow',1,'thunderstorm.png','27.png','tstorm','::T'),
    (57,'mäßiger oder starker gefrierender Sprühregen','Drizzle, freezing, moderate or heavy (dence)',2,'sleet.png','67.png','freezingrain',':H:ZL'),
    (56,'leichter gefrierender Sprühregen','Drizzle, freezing, slight',3,'sleet.png','66.png','freezingrain',':L:ZL'),
    (67,'mäßiger bis starker gefrierender Regen','Rain, freezing, moderate or heavy (dence)',4,'sleet.png','67.png','freezingrain',':H:ZR'),
    (66,'leichter gefrierender Regen','Rain, freezing, slight',5,'sleet.png','66.png','freezingrain',':L:ZR'),
    (86,'mäßiger bis starker Schneeschauer','Snow shower(s), moderate or heavy',6,'snow.png','86.png','snowshowers',':H:SW'),
    (85,'leichter Schneeschauer','Snow shower(s), slight',7,'snow.png','85.png','snowshowers',':L:SW'),
    (84,'mäßiger oder starker Schneeregenschauer','Shower(s) of rain and snow mixed, moderate or heavy',8,'sleet.png','84.png','wintrymix',':H:RS'),
    (83,'leichter Schneeregenschauer','Shower(s) of rain and snow mixed, slight',9,'sleet.png','83.png','wintrymix',':L:RS'),
    (82,'äußerst heftiger Regenschauer','extremely heavy rain shower',10,'rain.png','82.png','showers',':VH:RW'),
    (81,'mäßiger oder starker Regenschauer','moderate or heavy rain showers',11,'rain.png','82.png','showers',':H:RW'),
    (80,'leichter Regenschauer','slight rain shower',12,'rain.png','80.png','showers',':L:RW'),
    (75,'durchgehend starker Schneefall','heavy snowfall, continuous',13,'snow.png','16.png','snow',':H:S'),
    (73,'durchgehend mäßiger Schneefall','moderate snowfall, continuous',14,'snow.png','15.png','snow','::S'),
    (71,'durchgehend leichter Schneefall','slight snowfall, continuous',15,'snow.png','14.png','snow',':L:S'),
    (69,'mäßger oder starker Schneeregen','moderate or heavy rain and snow',16,'sleet.png','13.png','sleet',':H:RS'),
    (68,'leichter Schneeregen','slight rain and snow',17,'sleet.png','12.png','sleet',':L:RS'),
    (55,'durchgehend starker Sprühregen','heavy drizzle, not freezing, continuous',18,'drizzle.png','9.png','drizzle',':H:L'),
    (53,'durchgehend mäßiger Sprühregen','moderate drizzle, not freezing, continuous',19,'drizzle.png','8.png','drizzle','::L'),
    (51,'durchgehend leichter Sprühregen','slight drizzle, not freezing, continuous',20,'drizzle.png','7.png','drizzle',':L:L'),
    (65,'durchgehend starker Regen','heavy rain, not freezing, continuous',21,'rain.png','9.png','rain',':H:R'),
    (63,'durchgehend mäßiger Regen','moderate rain, not freezing, continuous',22,'rain.png','8.png','rain','::R'),
    (61,'durchgehend leichter Regen','slight rain, not freezing, continuous',23,'rain.png','7.png','rain',':L:R'),
    (49,'Nebel mit Reifansatz, Himmel nicht erkennbar, unverändert','Ice Fog, sky not recognizable',24,'fog.png','48.png','fog','::IF'),
    (45,'Nebel, Himmel nicht erkennbar','Fog, sky not recognizable',25,'fog.png','40.png','fog','::F'),
    (4,'bedeckt','Overcast clouds',26,None,None,None,None),
    (3,'bewölkt','Broken clouds',27,None,None,None,None),
    (2,'wolkig','scattered clouds',28,None,None,None,None),
    (1,'heiter','Few clouds',29,None,None,None,None),
    (0,'wolkenlos','clear sky',30,None,None,None,None)]

N_ICON_LIST = [
    ('clear-day.png','clear-night.png','0-8.png','CL','clear'),
    ('mostly-clear-day.png','mostly-clear-night.png','2-8.png','FW','fair'),
    ('partly-cloudy-day.png','partly-cloudy-night.png','5-8.png','SC','pcloudy'),
    ('mostly-cloudy-day.png','mostly-cloudy-night.png','5-8.png','BK','mcloudy'),
    ('cloudy.png','cloudy.png','8-8.png','OV','cloudy')]
    
def get_ww(ww,n,night):
    """ get icon and description for the current weather """
    # If weather code ww is within the list of WW_LIST (which means
    # it is important over cloud coverage), get the data from that
    # list.
    for ii in WW_LIST:
        if ii[0] in ww:
            wwcode = ii
            break
    else:
        wwcode = (0,'','',30,'unknown.png','unknown.png','unknown.png','')
    # Otherwise use cloud coverage
    # see aerisweather for percentage values
    # https://www.aerisweather.com/support/docs/api/reference/weather-codes/
    if wwcode[0]<=3:
        night = 1 if night else 0
        cover = get_cloudcover(n)
        if cover is not None:
            # Belchertown icons
            icon = cover[night]
            # Aeris icons
            aeicon = cover[4]
            aecode = '::'+cover[3]
            # DWD icons
            if n<12.5:
                dwd = N_ICON_LIST[0][2]
            elif n<50:
                dwd = N_ICON_LIST[1][2]
            elif n<87.5:
                dwd = N_ICON_LIST[2][2]
            else:
                dwd = N_ICON_LIST[4][2]
            try:
                n_str = '%.0f%%' % float(n)
            except Exception:
                n_str = str(n)
            wwcode = (wwcode[0],wwcode[1]+' '+n_str,wwcode[2]+' '+str(n),wwcode[3],icon,dwd,aeicon,aecode)
    return wwcode

# def get_cloudcover(n):
    # if n is None: return None
    # if n<7:
        # icon = N_ICON_LIST[0]
    # elif n<32:
        # icon = N_ICON_LIST[1]
    # elif n<70:
        # icon = N_ICON_LIST[2]
    # elif n<95:
        # icon = N_ICON_LIST[3]
    # else:
        # icon = N_ICON_LIST[4]
    # return icon

def get_cloudcover(cloudcover, weatherprovider='dwd'):
    if weatherprovider == 'dwd':
    # https://www.dwd.de/DE/service/lexikon/Functions/glossar.html?lv2=100932&lv3=101016
        if cloudcover<12.5:
            ccdata = N_ICON_LIST[0]
        elif cloudcover<=37.5:
            ccdata = N_ICON_LIST[1]
        elif cloudcover<=75.0:
            ccdata = N_ICON_LIST[2]
        elif cloudcover<=87.5:
            ccdata = N_ICON_LIST[3]
        else:
            ccdata = N_ICON_LIST[4]

    # see aerisweather for percentage values
    # https://www.aerisweather.com/support/docs/api/reference/weather-codes/
    else:
        if cloudcover<=7:
            ccdata = N_ICON_LIST[0]
        elif cloudcover<=32:
            ccdata = N_ICON_LIST[1]
        elif cloudcover<=70:
            ccdata = N_ICON_LIST[2]
        elif cloudcover<=95:
            ccdata = N_ICON_LIST[3]
        else:
            ccdata = N_ICON_LIST[4]
    #print("Provider: <%s> Cover: <%s> Code: <%s>" % (weatherprovider,str(cloudcover),ccdata[3]))
    return ccdata

# week day names
WEEKDAY = {
    'de':['Mo','Di','Mi','Do','Fr','Sa','So'],
    'en':['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],
    'fr':['lu','ma','me','je','ve','sa','di'],
    'it':['lun.','mar.','mer.','gio.','ven.','sab.','dom.'],
    'cz':['Po','Út','St','Čt','Pá','So','Ne'],
    'pl':['pon.','wt.','śr.','czw.','pt.','sob.','niedz.']
}

# compass directions
COMPASS = {
    'de':['N','NNO','NO','ONO','O','OSO','SO','SSO','S','SSW','SW','WSW','W','WNW','NW','NNW'],
    'en':['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW'],
    'fr':['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSO','SO','OSO','O','ONO','NO','NNO'],
    'it':['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSO','SO','OSO','O','ONO','NO','NNO'],
    'cz':['S','SSV','SV','VSV','V','VJV','JV','JJV','J','JJZ','JZ','ZJZ','Z','ZSZ','SZ','SSZ'],
    'es':['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSO','SO','OSO','O','ONO','NO','NNO'],
    'nl':['N','NNO','NO','ONO','O','OZO','ZO','ZZO','Z','ZZW','ZW','WZW','W','WNW','NW','NNW'],
    'no':['N','NNØ','NØ','ØNØ','Ø','ØSØ','SØ','SSØ','S','SSV','SV','VSV','V','VNV','NV','NNV'],
    'gr':['B','BBA','BA','ABA','A','ANA','NA','NNA','N','NNΔ','ΝΔ','ΔΝΔ','Δ','ΔΒΔ','ΒΔ','ΒΒΔ']
}
    
def compass(x, lang='de', withDEG=True):
    try:
        y = (x+11.25)//22.5
        if y>=16: y -= 16
        return COMPASS[lang][int(y)]+((' %.0f°' % x) if withDEG else '')
    except Exception:
        return ''

UBA = {
    'de':['sehr gut','gut','mäßig','schlecht','sehr schlecht'],
    'en':['good','fair','moderate','poor','very poor'],
    'color':['00E400','FFFF00','FF7E00','FF0000','99004C']}

def uba_category(index,lang='de'):
    try:
        return UBA[lang][index]
    except LookupError:
        return ''

EPAAQI = {
    'AQI':[50,100,150,200,300,400,500],
    'PM10':[54,154,254,354,424,504,604],
    'PM2':[12,35.4,55.4,150.4,250.4,350.4,500.4],
    'O3':[108,140,170,210,400],
    'NO2':[101.35,191.23,688.428,1241.08,2388.46,3153.38,3918.3]}

def epaaqi(pollutant, value):
    try:
        c0 = 0
        for idx,c1 in enumerate(EPAAQI[pollutant.upper()]):
            if value<=c1:
                i1 = EPAAQI['AQI'][idx]
                i0 = EPAAQI['AQI'][idx-1] if idx>0 else 0
                return nround((i1-i0)/(c1-c0)*(value-c0)+i0)
            c0 = c1
        return 500
    except Exception:
        return None

#https://www.dwd.de/DE/leistungen/met_verfahren_mosmix/faq/relative_feuchte.html
def humidity(temperature,dewpoint):
    try:
        RH = 100*math.exp((17.5043*dewpoint/(241.2+dewpoint))-(17.5043*temperature/(241.2+temperature)))
        return RH
    except Exception as e:
        print("Error humidity calculation, TEMP=%f, DEWPT=%f Error: %s %s" % (temperature,dewpoint,e.__class__.__name__,e))
        return None

# Database

schema = [('dateTime','INTEGER NOT NULL PRIMARY KEY'),
          ('usUnits','INTEGER NOT NULL'),
          ('interval','INTEGER NOT NULL'),
          ('hour','INTEGER'),
          ('outTemp','REAL'),
          ('dewpoint','REAL'),
          ('humidity','REAL'),
          ('windDir','REAL'),
          ('windSpeed','REAL'),
          ('windGust','REAL'),
          ('pop','REAL'),
          ('cloudcover','REAL'),
          ('barometer','REAL'),
          ('rain','REAL'),
          ('rainDur','REAL'),
          ('sunshineDur','REAL'),
          ('visibility','REAL'),
          ('ww','INTEGER')]

dwd_schema_dict = {
    'DD':'windDir',
    'FF':'windSpeed',
    'FX1':'windGust',
    'N':None,
    'Neff':'cloudcover',
    'PPPP':'barometer',
    'Td':'dewpoint',
    'TTT':'outTemp',
    'R101':'pop',
    'RR1c':'rain',
    'DRR1':'rainDur',
    'SunD1':'sunshineDur',
    'VV':'visibility',
    'ww':'ww'}

POP = ['R101','R102','R103','R105','R107','R110','R120','R130','R150','R600','R602','R610','R650','Rh00','Rh02','Rh10','Rh50','Rd00','Rd02','Rd10','Rd50']
def dwd_obs_to_weewx_obs(x):
    if x is None: return None
    x = x.split('_')
    x[0] = dwd_schema_dict.get(x[0],x[0])
    if x[0] is None: return None
    return '_'.join(x)
    
    
def nround(x,n=None):
    if x is None: return None
    return round(x,n)

def tobool(x):
    """ convert text to boolean
        Copyright (C) Tom Keffer
    """
    try:
        if x.lower() in ['true', 'yes', 'y']:
            return True
        elif x.lower() in ['false', 'no', 'n']:
            return False
    except AttributeError:
        pass
    try:
        return bool(int(x))
    except (ValueError, TypeError):
        pass
    raise ValueError("Unknown boolean specifier: '%s'." % x)

def fahrenheit(tempC):
    if tempC is None: return None
    return tempC*9.0/5.0+32.0

def inchHG(pressureMB):
    if pressureMB is None: return None
    return pressureMB*0.02952998330101
    
def mm_to_inch(mm):
    if mm is None: return None
    return mm/25.4

def mph(kmh):
    if kmh is None: return None
    return kmh/1.609344

def knoten(kmh):
    if kmh is None: return None
    return kmh/1.852
    
    
##############################################################################
#    Parser for the DWD KML weather forecast file                            #
##############################################################################
    
class KmlParser(html.parser.HTMLParser):

    def __init__(self, log_tags=False):
        super(KmlParser,self).__init__()
        self.log_tags = log_tags
        self.lvl = 0
        self.tags = []
        self.mos = dict()
        self.ar = [self.mos]
        self.placemark = None
        self.forecastelement = None
        
    @staticmethod
    def _mktime(timestring):
        """ convert CAP timestamp string to epoch time """
        #xxx = timestring
        if timestring[-1]=='Z':
            timestring = timestring.replace('Z','+0000')
        idx = timestring.find('.')
        if idx>=0:
            idx2 = timestring.find('+')
            if idx2==-1: idx2 = timestring.find('-')
            timestring = timestring[:idx]+timestring[idx2:]
        ti = datetime.datetime.strptime(timestring,'%Y-%m-%dT%H:%M:%S%z')
        #print('_mktime',xxx,ti,ti.timestamp(),time.strftime('%H:%M',time.localtime(ti.timestamp())))
        return int(ti.timestamp()*1000)

    def handle_starttag(self, tag, attrs):
        if self.log_tags:
            print(self.lvl,self.tags,'start',tag,attrs)
        self.tags.append(tag)
        self.lvl+=1
        if tag=='dwd:model' and self.tags[-2]=='dwd:referencedmodel':
            self.mos['ReferenceModel'] = dict()
            for ii in attrs:
                if ii[0]=='dwd:name':
                    self.mos['ReferenceModel']['name'] = ii[1]
                elif ii[0]=='dwd:referencetime':
                    self.mos['ReferenceModel']['ReferenceTime'] = KmlParser._mktime(ii[1])
                    self.mos['ReferenceModel']['ReferenceTimeISO'] = ii[1]
        if tag=='kml:placemark':
            if 'Placemark' not in self.mos:
                self.mos['Placemark'] = []
            if self.placemark:
                self.mos['Placemark'].append(self.placemark)
            self.placemark = dict()
        if tag=='dwd:forecast':
            for ii in attrs:
                if ii[0]=='dwd:elementname':
                    self.forecastelement = ii[1]
        
    def handle_endtag(self, tag):
        del self.tags[-1]
        self.lvl-=1
        if tag=='kml:placemark' and self.placemark:
            if 'Placemark' not in self.mos:
                self.mos['Placemark'] = []
            self.mos['Placemark'].append(self.placemark)
            self.placemark = None
        self.forecastelement = None
        if self.log_tags:
            print(self.lvl,self.tags,'end',tag)
       
    def handle_data(self, data):
        if len(self.tags)>0:
            tag = self.tags[-1]
            if self.placemark is not None:
                # inside a kml:Placemark section
                if tag=='kml:name':
                    self.placemark['id'] = data
                elif tag=='kml:description':
                    self.placemark['description'] = data
                elif tag=='kml:coordinates':
                    el = data.split(',')
                    for idx,val in enumerate(el):
                        try:
                            el[idx] = float(val)
                        except ValueError:
                            pass
                    self.placemark['coordinates'] = el
                elif tag=='dwd:value' and self.forecastelement:
                    if 'Forecast' not in self.placemark:
                        self.placemark['Forecast'] = dict()
                    el = data.split()
                    for idx,val in enumerate(el):
                        if val==self.mos.get('DefaultUndefSign',''):
                            el[idx] = None
                        else:
                            try:
                                vv = float(val)
                                if self.forecastelement in OBS_DICT:
                                    vv = OBS_DICT[self.forecastelement](vv)
                                el[idx] = vv
                            except ValueError:
                                pass
                    self.placemark['Forecast'][self.forecastelement] = el
            elif tag=='dwd:issuer':
                self.mos['Issuer'] = data
            elif tag=='dwd:productid':
                self.mos['ProductID'] = data
            elif tag=='dwd:generatingprocess':
                self.mos['GeneratingProcess'] = data
            elif tag=='dwd:issuetime':
                self.mos['IssueTime'] = KmlParser._mktime(data)
                self.mos['IssueTimeISO'] = data
            elif tag=='dwd:defaultundefsign':
                self.mos['DefaultUndefSign'] = data
            elif tag=='dwd:timestep' and self.tags[-2]=='dwd:forecasttimesteps':
                if 'ForecastTimeSteps' not in self.mos:
                    self.mos['ForecastTimeSteps'] = []
                self.mos['ForecastTimeSteps'].append(KmlParser._mktime(data))
                if 'ForecastTimeStepsISO' not in self.mos:
                    self.mos['ForecastTimeStepsISO'] = []
                self.mos['ForecastTimeStepsISO'].append(data)
        if self.log_tags:
            print(self.lvl,self.tags,'data',data)

###############################################################################
#    process MOSMIX data                                                      #
###############################################################################
        
class DwdMosmix(object):

    def __init__(self, config_dict, verbose=False):
        # target path
        try:
            self.target_path = config_dict['WeatherServices']['path']
        except LookupError:
            self.target_path = config_dict['DeutscherWetterdienst']['path']
        # forecast config data
        try:
            forecast_dict = config_dict['WeatherServices']['forecast']
            ws = True
        except LookupError:
            ws = False
            forecast_dict = config_dict['DeutscherWetterdienst']['forecast']
        # weather icons
        self.icon_pth = forecast_dict['icons']
        # station-specific configuration
        if ws:
            self.stations_dict = forecast_dict
        else:
            self.stations_dict = forecast_dict.get('stations',configobj.ConfigObj())
        # HTML config
        self.show_obs_symbols = tobool(forecast_dict.get('show_obs_symbols',True))
        self.show_obs_description = tobool(forecast_dict.get('show_obs_description',False))
        self.show_obs_units = tobool(forecast_dict.get('show_obs_units',False))
        self.show_placemark = tobool(forecast_dict.get('show_placemark',False))
        self.forecast_max_days = int(forecast_dict.get('max_days', 8))
        # orientation of the HTML table
        orientation = forecast_dict.get('orientation','h,v')
        if not isinstance(orientation,list):
            if orientation.lower()=='both': orientation = 'h,v'
            orientation = orientation.split(',')
        orientation = [ii[0].lower() for ii in orientation]
        self.horizontal_table = 'h' in orientation
        self.vertical_table = 'v' in orientation
        # classes to include in <table> and surroundng <div> tag
        self.horizontal_table_classes = 'dwdforecasttable'
        self.horizontal_div_classes = None
        self.vertical_table_classes = 'dwdforecasttable'
        self.vertical_div_classes = None
        # visibility according to viewport size
        class_hidden = 'hidden-xs'
        class_visible = 'visible-xs-block'
        if self.horizontal_table and self.vertical_table:
            # both tables are included, so we need to set visibility
            self.horizontal_div_classes = ((self.horizontal_div_classes+' ') if self.horizontal_div_classes else '')+class_hidden
            self.vertical_div_classes = ((self.vertical_div_classes+' ') if self.vertical_div_classes else '')+class_visible
        # iconset
        self.iconset = 4
        if forecast_dict.get('icon_set','').lower()=='dwd': self.iconset = 5
        if forecast_dict.get('icon_set','').lower()=='aeris': self.iconset = 6
        # logging
        self.verbose = verbose
        self.log_success = tobool(forecast_dict.get('log_success',config_dict.get('DeutscherWetterdienst',dict()).get('log_success',config_dict.get('log_success',False))))
        self.log_failure = tobool(forecast_dict.get('log_failure',config_dict.get('DeutscherWetterdienst',dict()).get('log_failure',config_dict.get('log_failure',False))))
        if (int(config_dict.get('debug',0))>0) or verbose:
            self.log_success = True
            self.log_failure = True
            self.verbose = True
        # almanac
        stn = config_dict.get('Station',dict())
        self.latitude = float(stn.get('latitude'))
        self.longitude = float(stn.get('longitude'))
        alt = stn.get('altitude',(None,None))
        if alt[1] and alt[1]=='meter':
            alt = float(alt[0])
        elif alt[1] and alt[1]=='foot':
            alt = float(alt[0])*0.3048
        else:
            alt = None
        self.altitude = alt
        if has_pyephem:
            self.sun = ephem.Sun()
        # Belchertown
        try:
            belchertown_dict = config_dict['WeatherServices'].get('Belchertown',configobj.ConfigObj())
            belchertown_section = config_dict['StdReport'][belchertown_dict['section']]
            if 'HTML_ROOT' in belchertown_section:
                self.belchertown_html_root = os.path.join(
                    config_dict['WEEWX_ROOT'],
                    belchertown_section['HTML_ROOT'])
            else:
                self.belchertown_html_root = os.path.join(
                    config_dict['WEEWX_ROOT'],
                    config_dict['StdReport']['HTML_ROOT'])
            self.belchertown_forecast = belchertown_dict.get('forecast', 10688)
            self.belchertown_warning = belchertown_dict.get('warnings', None)
            self.belchertown_include_advance_warning = int(belchertown_dict.get('include_advance_warnings',0))
            self.belchertown_aqi_source = str(belchertown_dict.get('aqi_source', None))
            if self.belchertown_aqi_source: self.belchertown_aqi_source = self.belchertown_aqi_source.lower()
            self.belchertown_compasslang = str(belchertown_dict.get('compass_lang','en')).lower()
            self.belchertown_forecast_filename = belchertown_dict.get('filename', 'forecast.json')
            try:
                ew = belchertown_section['Extras']
            except (LookupError,TypeError):
                ew = dict()
            try:
                skin_dict = configobj.ConfigObj(
                            os.path.join(config_dict['WEEWX_ROOT'],
                                         config_dict['StdReport']['SKIN_ROOT'],
                                         belchertown_section['skin'],
                                         'skin.conf'))
                es = skin_dict['Extras']
            except Exception:
                es = dict()
            self.forecast_api_id = ew.get('forecast_api_id',es.get('forecast_api_id'))
            self.forecast_api_secret = ew.get('forecast_api_secret',es.get('forecast_api_secret'))
        except LookupError as e:
            if 'Belchertown' in config_dict['WeatherServices']:
                logerr("Belchertown config %s %s" % (e.__class__.__name__,e))
            belchertown_section = configobj.ConfigObj()
            self.belchertown_html_root = None
            self.belchertown_warning = None
            self.belchertown_forecast = None
            self.forecast_api_id = None
            self.forecast_api_secret = None
            self.belchertown_aqi_source = None
            self.belchertown_compasslang = 'en'
        # Database
        try:
            self.SQLITE_ROOT = config_dict['DatabaseTypes']['SQLite']['SQLITE_ROOT']
        except LookupError:
            self.SQLITE_ROOT = None
        self.connection = None
        # Log config
        if __name__ == "__main__" and verbose:
            print('-- configuration data ----------------------------------')
            print('log success:     ',self.log_success)
            print('log failure:     ',self.log_failure)
            print('target path:     ',self.target_path)
            print('horiz. tab:      ',self.horizontal_table)
            print('vertical tab:    ',self.vertical_table)
            print('icon set:        ',self.iconset)
            print('station location:','lat',self.latitude,'lon',self.longitude,'alt',self.altitude)
            print('aeris api id:    ',self.forecast_api_id)
            print('aeris api secret:',self.forecast_api_secret)
            print('SQLITE_ROOT:     ',self.SQLITE_ROOT)
            print('Forecast max_days',self.forecast_max_days)
            print('--------------------------------------------------------')

    @staticmethod
    def geo(latitude, longitude):
        """ determine state and country from latitude/longitude """
        if has_geopy:
            try:
                locator = Nominatim(user_agent="dwd-mosmix")
                location = locator.reverse('%s, %s' % (latitude,longitude))
                if location is not None:
                    addr_dict = location.raw.get('address',dict())
                    town = addr_dict.get('town')
                    county = addr_dict.get('county')
                    state = addr_dict.get('state')
                    country = addr_dict.get('contry')
                    iso = addr_dict.get('country_code')
                    data = {
                        'addr':location.address,
                        'lat':location.latitude,
                        'lon':location.longitude,
                        'alt':location.altitude,
                        'raw':location.raw,
                        'town':town,
                        'county':county,
                        'state':state,
                        'country':country,
                        'country_code':iso
                    }
                    return data
            except Exception as e:
                logerr('getting geo data failed: %s' % e)
        return None

    @staticmethod
    def isoformat(ts, tzoffset=None, geo=None):
        """ convert time to string in ISO format """
        try:
            if tzoffset is not None:
                ti = time.gmtime(ts+tzoffset)
            elif geo is not None:
                # TODO
                ti = time.localtime(ts)
            else:
                ti = time.localtime(ts)
            tzstr = time.strftime('%z',ti)
            return time.strftime('%Y-%m-%dT%H:%M:%S',ti)+tzstr[0:3]+':'+tzstr[3:]
        except Exception:
            return '----------T--:--:--+--:--'
        
    @staticmethod
    def timestamp(datum):
        """ convert string to timestamp """
        try:
            #print("datum",datum)
            ti = time.strptime(datum,"%Y-%m-%d %H:%M:%S")
            #print("ti",ti)
            ts = time.mktime(ti)
            #print("ti",ts,time.strftime("%d.%m.%Y %H:%M:%S %z",time.localtime(ts)))
            return int(ts)
        except Exception:
            return None
        
    def download_kml(self, location, mosmix):
        """ download MOSMIX KML file from DWD server """

        url = get_mos_url(location,mosmix)
        
        headers={'User-Agent':'weewx-DWD'}
        try:
            reply = requests.get(url,headers=headers)
        except ConnectionError as e:
            if self.log_failure:
                logerr(e)
            return None
        
        if reply.status_code==200:
            if self.log_success or self.verbose:
                loginf('successfully downloaded %s' % reply.url)
            zz = zipfile.ZipFile(io.BytesIO(reply.content),'r')
            for ii in zz.namelist():
                if self.verbose:
                    loginf('-- %s --' % ii)
                return zz.read(ii).decode(encoding='utf-8')
            return None
        else:
            if self.log_failure or self.verbose:
                logerr('error downloading %s: %s %s' % (reply.url,reply.status_code,reply.reason))
            return None
            
    def process_kml(self, text, log_tags=False):
        """ convert KML file to dict """
        if self.verbose:
            loginf('processing KML file')
        parser = KmlParser(log_tags)
        parser.feed(text)
        parser.close()
        if self.verbose:
            loginf('KML file processed, %s placemarks found' % len(parser.mos.get('Placemark',[])))
        #print(json.dumps(parser.mos,indent=4,ensure_ascii=False))
        #print(parser.mos['Placemark'][0]['Forecast']['TTT'])
        return parser.mos

    @staticmethod
    def timestamp_to_djd(time_ts):
        """ convert unix timestamp to dublin julian day 
            Copyright (C) Tom Keffer
        """
        return 25567.5 + time_ts/86400.0
        
    def is_night(self, location, ts):
        """ check if timestamp ts is nighttime for location location """
        if has_pyephem:
            try:
                # time of the forecast
                djd = DwdMosmix.timestamp_to_djd(ts)
                location.date = djd
                location.epoch = djd
                if self.verbose: loginf(location)
                # calculate next rising and setting of the sun
                rising = location.next_rising(self.sun)
                setting = location.next_setting(self.sun)
                # If the next setting is after the next rising
                # in respect to the given timestamp, it is
                # actually night time. Otherwise it's day time.
                night = setting>rising
            except Exception as e:
                logerr('error calculation sunrise, sunset: %s' % e)
                # If there is an error in calculation we consider
                # the time before 06:00 and after 18:00 to be
                # night time.
                night = not (6 <= time.localtime(ts).tm_hour < 18)
        else:
            # If pyephem is not installed we cannot calculate the
            # real sunrise and sunset. So we consider to be the
            # time betwenn 06:00 and 18:00 to be day time,
            # otherwise night time.
            night = not (6 <= time.localtime(ts).tm_hour < 18)
        return night
        
    def calculate_daynight(self, placemark, timesteps):
        """ calculate array of daylight values """
        geo = placemark['coordinates']
        if has_pyephem:
            try:
                location = ephem.Observer()
                location.lat = geo[1]*0.017453292519943
                location.lon = geo[0]*0.017453292519943
                if geo[2] is not None:
                    location.elevation = geo[2]
            except Exception as e:
                logerr('Observer: %s %s' % (e.__class__.__name__,e))
        else:
            location = None
        daynights = []
        for ts in timesteps:
            daynights.append(self.is_night(location,ts*0.001))
        if len(daynights)!=len(timesteps):
            logerr('calculate_daynight: different array sizes')
        return daynights
        
    @staticmethod
    def _temp_color(temp):
        """ temperature colors 
            Copyright (C) Tom O'Brien
        """
        if temp<=-17.78: return "#1278c8"
        if temp<=-3.8:   return "#30bfef"
        if temp<=0:      return "#1fafdd"
        if temp<=4.4:    return "rgba(0,172,223,1)"
        if temp<=10:     return "#71bc3c"
        if temp<=12.7:   return "rgba(90,179,41,0.8)"
        if temp<=18.3:   return "rgba(131,173,45,1)"
        if temp<=21.1:   return "rgba(206,184,98,1)"
        if temp<=23.8:   return "rgba(255,174,0,0.9)"
        if temp<=26.6:   return "rgba(255,153,0,0.9)"
        if temp<=29.4:   return "rgba(255,127,0,1)"
        if temp<=32.2:   return "rgba(255,79,0,0.9)"
        if temp<=35:     return "rgba(255,69,69,1)"
        if temp<=43.3:   return "rgba(255,104,104,1)"
        return "rgba(218,113,113,1)"
    
    OBS_LABEL = {
        'ww':('','',''),
        'TTT':('<i class="wi wi-thermometer"></i>','Temperatur 2m','&deg;C'),
        'TTTmax':('<i class="wi wi-thermometer"></i>','Maximaltemperatur','&deg;C'),
        'TTTmin':('<i class="wi wi-thermometer"></i>','Minimaltemperatur','&deg;C'),
        'TTTavg':('<i class="wi wi-thermometer"></i>','Durchschnittstemperatur','&deg;C'),
        'T5cm':('<i class="wi wi-thermometer"></i>','Temperatur 5cm','&deg;C'),
        'Td':('<i class="wi wi-thermometer"></i>','Taupunkt 2m','&deg;C'),
        'TG':('<i class="wi wi-thermometer"></i>','Minimaltemperatur 5cm','&deg;C'),
        'TM':('<i class="wi wi-thermometer"></i>','Durchschnittstemperatur','&deg;C'),
        'TN':('<i class="wi wi-thermometer"></i>','Minimaltemperatur','&deg;C'),
        'TX':('<i class="wi wi-thermometer"></i>','Maximaltemperatur','&deg;C'),
        'FF':('<i class="wi wi-strong-wind"></i>','Wind','km/h'),
        'DD':('<i class="wi wi-strong-wind"></i>','Windrichtung','&deg;'),
        'FFavg':('<i class="wi wi-strong-wind"></i>','Wind','km/h'),
        'DDavg':('<i class="wi wi-strong-wind"></i>','Windrichtung','&deg;'),
        'FX1max':('<i class="wi wi-strong-wind"></i>','max. Windb&ouml;en','km/h'),
        'PPPP':('<i class="wi wi-barometer"></i>','Luftdruck','mbar'),
        'PPPPavg':('<i class="wi wi-barometer"></i>','Luftdruck','mbar'),
        'Navg':('<i class="wi wi-cloud"></i>','Bew&ouml;lkung','%'),
        'Neffavg':('<i class="wi wi-cloud"></i>','Bew&ouml;lkung','%'),
        'SunD1':('<i class="wi wi-day-sunny"></i>','SunD1','h'),
        'RSunD':('<i class="wi wi-day-sunny"></i>','Sonnenscheindauer','%'),
        'Rad1h':('<i class="wi wi-hot"></i>','Globalstrahlung','Wh/m&sup2;'),
        'Rad1hsum':('<i class="wi wi-hot"></i>','Globalstrahlung','kWh/m&sup2;'),
        'RR1c':('<i class="wi wi-umbrella"></i>','Niederschlag','mm'),
        'Rd10':('<i class="wi wi-umbrella"></i>','Wahrscheinlichkeit','%'),
        'R101':('<i class="wi wi-umbrella"></i>','Wahrscheinlichkeit','%'),
        'VV':('VV','Sichtweite','m')}

    def write_html(self, placemark, timesteps, daynights, obstypes, dryrun, range=None, lang='de'):
        """ create HTML hourly """
        #timesteps = mos['ForecastTimeSteps']
        try:
            start_day = range[0]
            end_day = range[1]
            count = 9999
        except TypeError:
            start_day = 0
            end_day = 9999
            count = range if range else 9999
        now = time.time()*1000
        # config
        symbols = self.show_obs_symbols and obstypes
        desc = self.show_obs_description or not obstypes
        #for placemark in mos.get('Placemark'):
        if True:
            """
            if has_pyephem:
                try:
                    location = ephem.Observer()
                    # location of the forecast
                    geo = placemark['coordinates']
                    location.lat = geo[1]*0.017453292519943
                    location.lon = geo[0]*0.017453292519943
                    location.elevation = geo[2]
                except Exception as e:
                    logerr('Observer: %s' % e)
            """
            s = ""
            if self.horizontal_table:
                if self.horizontal_div_classes:
                    s += '<div class="%s">\n' % self.horizontal_div_classes
                s += '<table class="%s">' % self.horizontal_table_classes
                start_ct = 0
                old_wd = None
                # timestamp
                s += '<tr><td></td>'
                if symbols: s += '<td></td>'
                if desc: s += '<td></td>'
                old_day_ct = -1
                for idx,ii in enumerate(timesteps):
                    # day of week
                    try:
                        wd = WEEKDAY[lang][time.localtime(ii*0.001).tm_wday]
                    except Exception:
                        wd = ''
                    # count days
                    if old_wd:
                        if old_wd!=wd: day_ct += 1
                    else:
                        day_ct = 0
                    old_wd = wd
                    #
                    if ii<now or day_ct<start_day:
                        start_ct += 1 
                        continue
                    if idx>=count+start_ct: break
                    if day_ct>=end_day: 
                        count = idx-start_ct
                        break
                    #
                    ti = time.localtime(ii*0.001)
                    s += '<td>'
                    if old_day_ct!=day_ct:
                        s += '<strong>%s</strong><br />%s' % (wd,time.strftime('%d.%m.',ti))
                    else:
                        s += '<br />'
                    s += '<br />%s' % time.strftime('%H:%M',ti)
                    s += '</td>'
                    old_day_ct = day_ct
                s += '</tr>\n'
                # weather icon
                s += '<tr class="icons"><td></td>'
                if symbols: s += '<td></td>'
                if desc: s += '<td></td>'
                for idx,ii in enumerate(timesteps):
                    if idx<start_ct: continue
                    if idx>=count+start_ct: break
                    #night = self.is_night(location,ii*0.001)
                    night = daynights[idx]
                    wwcode = get_ww([placemark['Forecast']['ww'][idx]],placemark['Forecast']['Neff'][idx],night)
                    if self.verbose: loginf('night=%s ww=%s' % (night,wwcode))
                    if lang=='en':
                        icontitle = wwcode[2]
                    else:
                        icontitle = wwcode[1].replace('ö','&ouml;').replace('ü','&uuml;')
                    icon = wwcode[self.iconset]
                    if self.iconset==6: icon += ('n' if night else '')+'.png'
                    s += '<td title="%s"><img src="%s/%s" width="50px" alt="%s" /></td>' % (icontitle,self.icon_pth,icon,icontitle)
                s += '</tr>\n'
                # other observation types
                obs = obstypes if obstypes else placemark['Forecast']
                for ii in obs:
                    prec_color = ' #7cb5ec' if ii in ['RR1c','RRL1c','RRS1c','R101'] else None
                    if ii in ['Rad1h']: prec_color = '#ffc83f'
                    color = ';color:%s' % prec_color if prec_color else ''
                    # new table row
                    if obstypes and ii in ['FF','RR1c','PPPP','Neff']:
                        s += '<tr class="topdist">'
                    else:
                        s += '<tr>'
                    # observation type symbol column
                    if symbols:
                        s += '<td style="text-align:left%s" title="%s">%s</td>' % (color,self.OBS_LABEL.get(ii,('',ii,''))[1],self.OBS_LABEL.get(ii,(ii,'',''))[0])
                    # observation type description column
                    if desc:
                        if obstypes:
                            s += '<td>%s</td>' % self.OBS_LABEL.get(ii,('',ii,''))[1]
                        else:
                            s += '<td>%s</td>' % ii
                    # measuring unit column
                    color = ' style="color:%s"' % prec_color if prec_color else ''
                    s += '<td%s>%s</td>' % (color,self.OBS_LABEL.get(ii,(ii,'',''))[2])
                    # values columns
                    for idx,jj in enumerate(placemark['Forecast'].get(ii,[])):
                        if idx<start_ct: continue
                        if idx>=count+start_ct: break
                        try:
                            color = ' style="color:%s"' % prec_color if prec_color else ''
                            if ii=='TTT': color = ' style="color:%s"' % DwdMosmix._temp_color(jj)
                            dp = 1 if ii[0]=='T' or (ii in ['RR1c','RRL1c','RRS1c','RR3c','RR6c']) else 0
                            if ii=='DD':
                                s += '<td><i class="wi wi-direction-down" style="transform:rotate(%sdeg);font-size:150%%" title="%s"></i></td>' % (jj,compass(jj,lang))
                                #s += '<td><i class="wi wi-wind-direction" style="transform:rotate(%sdeg);font-size:150%%"></i></td>' % ((jj+180)%360)
                            else:
                                s += '<td%s>%.*f</td>' % (color,dp,jj)
                        except Exception:
                            s += '<td>%s</td>' % jj
                    s += '</tr>\n'
                fn = placemark['id'].replace(',','_').replace(' ','_')
                s += '</table>\n'
                if self.horizontal_div_classes:
                    s += '</div>\n'
            # HTML for phones
            if self.vertical_table:
                if self.vertical_div_classes:
                    s += '<div class="%s">\n' % self.vertical_div_classes
                s += '<table class="%s">' % self.vertical_table_classes
                s += '<tr><th></th><th>ww</th>'
                for ii in ['TTT','FF','RR1c','PPPP']:
                    color = ' style="color:#7cb5ec"' if ii=='RR1c' else ''
                    s += '<th%s>%s</th>' % (color,self.OBS_LABEL[ii][0])
                s += '</tr>'
                old_day_ct = -1
                for idx,ii in enumerate(timesteps):
                    # day of week
                    try:
                        wd = WEEKDAY[lang][time.localtime(ii*0.001).tm_wday]
                    except Exception:
                        wd = ''
                    # count days
                    if old_wd:
                        if old_wd!=wd: day_ct += 1
                    else:
                        day_ct = 0
                    old_wd = wd
                    #
                    if ii<now or day_ct<start_day:
                        start_ct += 1 
                        continue
                    if idx>=count+start_ct: break
                    if day_ct>=end_day: 
                        count = idx-start_ct
                        break
                    # time stamp column
                    #night = self.is_night(location,ii*0.001)
                    night = daynights[idx]
                    ti = time.localtime(ii*0.001)
                    if old_day_ct!=day_ct:
                        s += '<tr><td colspan="6" style="text-align:left"><strong>%s</strong> %s</td></tr>\n' % (wd,time.strftime('%d.%m.',ti))
                    s += '<tr>'
                    s += '<td rowspan="2">%s</td>' % time.strftime('%H:%M',ti)
                    old_day_ct = day_ct
                    # weather icon column
                    wwcode = get_ww([placemark['Forecast']['ww'][idx]],placemark['Forecast']['Neff'][idx],night)
                    if lang=='en':
                        icontitle = wwcode[2]
                    else:
                        icontitle = wwcode[1].replace('ö','&ouml;').replace('ü','&uuml;')
                    icon = wwcode[self.iconset]
                    if self.iconset==6: icon += ('n' if night else '')+'.png'
                    s += '<td rowspan="2" title="%s"><img src="%s/%s" width="50px" alt="%s" /></td>' % (icontitle,self.icon_pth,icon,icontitle)
                    try:
                        # temperature column
                        temp = placemark['Forecast']['TTT'][idx]
                        temp_s = ('%.1f' % temp).replace('.',',')
                        s += '<td style="color:%s">%s<span style="font-size:50%%"> °C</span></td>' % (DwdMosmix._temp_color(temp),temp_s)
                    except (ValueError,TypeError,LookupError):
                        s += '<td>?</td>'
                    try:
                        # wind column
                        wind_s = ('%.0f' % placemark['Forecast']['FF'][idx]).replace('.',',')
                        s += '<td>%s<span style="font-size:50%%"> km/h</span></td>' % wind_s
                    except (ValueError,TypeError,LookupError):
                        s += '<td>?</td>'
                    try:
                        # rain
                        rain = ('%.1f' % placemark['Forecast']['RR1c'][idx]).replace('.',',')
                        s += '<td style="color:#7cb5ec">%s<span style="font-size:50%%"> mm</span></td>' % rain
                    except (ValueError,TypeError,LookupError):
                        s += '<td>?</td>'
                    try:
                        # barometer
                        s += '<td rowspan="2">%.0f<span style="font-size:50%%"> mbar</span></td>' % placemark['Forecast']['PPPP'][idx]
                    except (ValueError,TypeError,LookupError):
                        s += '<td rowspan="2">?</td>'
                    # end of row
                    s += '</tr>\n'
                    # 2nd row
                    s += '<tr>'
                    # temp
                    s += '<td></td>'
                    try:
                        # wind direction
                        s += '<td%s><i class="wi wi-direction-down" style="transform:rotate(%sdeg);font-size:150%%" title="%s"></i></td>' % ('',placemark['Forecast']['DD'][idx],compass(placemark['Forecast']['DD'][idx],lang))
                    except (ValueError,TypeError,LookupError):
                        s += '<td>%s</td>' % placemark['Forecast'].get('DD',[])[idx]
                    try:
                        # rain propability
                        s += '<td style="color:#7cb5ec">%.0f<span style="font-size:50%%"> %%</span></td>' % placemark['Forecast']['R101'][idx]
                    except (ValueError,TypeError,LookupError):
                        s += '<td>?</td>'
                    s += '</tr>\n'
                s += '</table>\n'
                if self.vertical_div_classes:
                    s += '</div>\n'
            if dryrun:
                print(s)
            else:
                suffix = 'hourly' if obstypes else 'all'
                if end_day<30: suffix += '-'+str(start_day)
                with open("%s/forecast-%s-%s.inc" % (self.target_path,fn,suffix),"w") as file:
                    file.write(s)
        
    def write_html_daily(self, placemark, days, timesteps, issue, obstypes, dryrun, lang='de'):
        """ make daily values out of hourly ones and create HTML and JSON """
        # config
        symbols = self.show_obs_symbols
        desc = self.show_obs_description
        units = self.show_obs_units
        # create HTML and JSON file for each placemark in KML file
        #for placemark in mos.get('Placemark'):
        if True:
            try:
                station_dict = self.stations_dict[placemark['id']]
            except Exception:
                 station_dict = configobj.ConfigObj()
            # HTML 
            s = ""
            if self.show_placemark:
                s += '<p itemscope itemtype="https://schema.org/Place"><strong itemprop="name">%s</strong></p>\n' % placemark['description']
            # HTML for PCs
            if self.horizontal_table:
                if self.horizontal_div_classes:
                    s += '<div class="%s">\n' % self.horizontal_div_classes
                s += '<table class="%s">' % self.horizontal_table_classes
                s += '<tr><td></td>'
                if symbols: s += '<td></td>'
                if desc: s += '<td></td>'
                for day in days:
                    htmlclass = ' class="weekend"' if days[day]['weekday']>=5 else ''
                    s += '<td%s><strong>%s</strong><br />%s</td>' % (htmlclass,WEEKDAY[lang][days[day]['weekday']],day)
                s += '</tr>\n'
                if obstypes:
                    obs = obstypes 
                elif 'observations_daily' in station_dict:
                    obs = station_dict['observations_daily']
                else:
                    obs = ['ww','TTTmax','TTTmin','FFavg','DDavg','RR1c','Rd10','PPPPavg','Neffavg','RSunD','Rad1hsum']
                for ii in obs:
                    if ii=='ww':
                        s += '<tr class="icons">'
                    elif ii in ['FFavg','PPPPavg','RR1c','Neffavg']:
                        s += '<tr class="topdist">'
                    else:
                        s += '<tr>'
                    color = ''
                    prec_color = '#7cb5ec' if ii in ['RR1c','Rd00','Rd01','Rd05','Rd10'] else None
                    if ii in ['Rad1hsum','SunD1','RSunD']: prec_color = '#ffc83f'
                    if prec_color: color = ';color:%s' % prec_color
                    if symbols:
                        s += '<td style="text-align:left%s" title="%s">%s' % (color,self.OBS_LABEL.get(ii,('',ii,''))[1],self.OBS_LABEL.get(ii,('',ii,''))[0])
                        if not desc and ii=='TTTmax': s+='&nbsp;max'
                        if not desc and ii=='TTTmin': s+='&nbsp;min'
                        s += '</td>'
                    if desc:
                        s += '<td style="text-align:left%s">%s</td>' % (color,self.OBS_LABEL.get(ii,('',ii,''))[1])
                    if prec_color: color = ' style="color:%s"' % prec_color
                    s += '<td'+color+'>'+self.OBS_LABEL.get(ii,('',ii,''))[2]+'</td>'
                    dp = 1 if ii in ['TTTmin','TTTmax','TTTavg','SunD1','Rad1hsum'] else 0
                    for day in days:
                        htmlclass = ' class="weekend"' if days[day]['weekday']>=5 else ''
                        try:
                            if ii=='ww':
                                icontitle = days[day]['icontitle'].replace('ö','&ouml;').replace('ü','&uuml;')
                                s += '<td%s title="%s"><img src="%s" width="50px" alt="%s" /></td>' % (htmlclass,icontitle,days[day]['icon'],icontitle)
                            elif ii in ('DD','DDavg'):
                                #s += '<td%s><i class="fa fa-arrow-down" style="transform:rotate(%sdeg)"></i></td>' % (htmlclass,days[day][ii])
                                s += '<td%s><i class="wi wi-direction-down" style="transform:rotate(%sdeg);font-size:150%%" title="%s"></i></td>' % (htmlclass,days[day][ii],compass(days[day][ii],lang))
                            else:
                                color = ''
                                if ii[0:3]=='TTT': color = ' style="color:%s"' % DwdMosmix._temp_color(days[day][ii])
                                if prec_color: color = ' style="color:%s"' % prec_color
                                val = ('%.*f' % (dp,days[day].get(ii,float("NaN")))).replace('.',',')
                                s += '<td%s%s>%s</td>' % (htmlclass,color,val)
                        except (ValueError,TypeError):
                            s += '<td>%s</td>' % days[day].get(ii,'')
                    s += '</tr>\n'
                # PV energy if configured
                if 'pv_factor' in station_dict:
                    pv_factor = float(station_dict['pv_factor'])
                    s += '<tr>\n'
                    if symbols: s += '<td style="text-align:left">PV</td>'
                    if desc: s += '<td>PV-Anlage</td>'
                    s += '<td>kWh</td>'
                    first = True
                    for day in days:
                        htmlclass = ' class="weekend"' if days[day]['weekday']>=5 else ''
                        try:
                            if first:
                                # for today no real value
                                ertrag = ''
                            else:
                                # from tomorrow on
                                ertrag = ('%.1f' % (days[day]['Rad1hsum']*pv_factor)).replace('.',',')
                            s += '<td%s>%s</td>' % (htmlclass,ertrag)
                        except (ValueError,TypeError):
                            s += '<td%s>NaN</td>' % htmlclass
                        first = False
                    s += '</tr>\n'
                s += '</table>\n'
                if self.horizontal_div_classes:
                    s += '</div>\n'
            # HTML for phones
            if self.vertical_table:
                if self.vertical_div_classes:
                    s += '<div class="%s">\n' % self.vertical_div_classes
                s += '<table class="%s">' % self.vertical_table_classes
                # header line
                s += '<tr>'
                s += '<th></th><th>ww</th>'
                for ii in ['TTTmin','FFavg','RR1c','PPPPavg']:
                    color = ' style="color:#7cb5ec"' if ii=='RR1c' else ''
                    s += '<th%s>%s</th>' % (color,self.OBS_LABEL[ii][0])
                s += '</tr>\n'
                for day in days:
                    htmlclass = ' class="weekend"' if days[day]['weekday']>=5 else ''
                    s += '<tr>'
                    # weekday and date
                    s += '<td%s rowspan="2"><strong>%s</strong><br />%s</td>' % (htmlclass,WEEKDAY[lang][days[day]['weekday']],day)
                    try:
                        # weather icon
                        icontitle = days[day]['icontitle'].replace('ö','&ouml;').replace('ü','&uuml;')
                        s += '<td%s title="%s" rowspan="2"><img src="%s" width="50px" alt="%s" /></td>' % (htmlclass,icontitle,days[day]['icon'],icontitle)
                    except (ValueError,TypeError):
                        s += '<td>%s</td>' % days[day].get('','')
                    try:
                        # max temp
                        color = ' style="color:%s"' % DwdMosmix._temp_color(days[day]['TTTmax'])
                        temp_s = ('%.1f' % days[day].get('TTTmax',float("NaN"))).replace('.',',')
                        s += '<td%s%s>%s<span style="font-size:50%%"> °C</span></td>' % (htmlclass,color,temp_s)
                    except (ValueError,TypeError):
                        s += '<td>%s</td>' % days[day].get('TTTmax','')
                    try:
                        # wind
                        color = ''
                        s += ('<td%s%s>%.*f<span style="font-size:50%%"> km/h</span></td>' % (htmlclass,color,0,days[day].get('FFavg',float("NaN")))).replace('.',',')
                    except (ValueError,TypeError):
                        s += '<td>%s</td>' % days[day].get('FFavg','')
                    try:
                        # precipitation
                        color = ' style="color:#7cb5ec"' 
                        s += ('<td%s%s>%.*f<span style="font-size:50%%"> mm</span></td>' % (htmlclass,color,0,days[day].get('RR1c',float("NaN")))).replace('.',',')
                    except (ValueError,TypeError):
                        s += '<td>%s</td>' % days[day].get('RR1c','')
                    try:
                        # pressure
                        color = ''
                        s += ('<td%s%s rowspan="2">%.*f<span style="font-size:50%%"> mbar</span></td>' % (htmlclass,color,0,days[day].get('PPPPavg',float("NaN")))).replace('.',',')
                    except (ValueError,TypeError):
                        s += '<td>%s</td>' % days[day].get('PPPPavg','')
                    # next line
                    s += '</tr>\n<tr>'
                    try:
                        # min temp
                        color = ' style="color:%s"' % DwdMosmix._temp_color(days[day]['TTTmin'])
                        temp_s = ('%.1f' % days[day].get('TTTmin',float("NaN"))).replace('.',',')
                        s += '<td%s%s>%s<span style="font-size:50%%"> °C</span></td>' % (htmlclass,color,temp_s)
                    except (ValueError,TypeError):
                        s += '<td>%s</td>' % days[day].get('TTTmin','')
                    try:
                        # wind direction
                        s += '<td%s><i class="wi wi-direction-down" style="transform:rotate(%sdeg);font-size:150%%" title="%s"></i></td>' % (htmlclass,days[day]['DDavg'],compass(days[day]['DDavg'],lang))
                    except (ValueError,TypeError):
                        s += '<td>%s</td>' % days[day].get('DDavg','')
                    try:
                        # rain propability
                        color = ' style="color:#7cb5ec"' 
                        s += ('<td%s%s>%.*f<span style="font-size:50%%"> %%</span></td>' % (htmlclass,color,0,days[day].get('Rd10',float("NaN")))).replace('.',',')
                    except (ValueError,TypeError):
                        s += '<td>%s</td>' % days[day].get('Rd10','')
                    s += '</tr>\n'
                s += '</table>\n'
                if self.vertical_div_classes:
                    s += '</div>\n'
            # Copyright notice
            s += '<p style="font-size:65%">'
            if issue.get('Issuer','')=='Open-Meteo':
                s += 'bereitgestellt von <a href="https://open-meteo.com/" target="_blank">Open-Meteo</a>'
            else:
                s += 'herausgegeben vom <a href="https://www.dwd.de" target="_blank">DWD</a>'
            s += ' am %s' % time.strftime('%d.%m.%Y %H:%M',time.localtime(issue['IssueTime']/1000.0))
            s += ' | Vorhersage erstellt am %s' % time.strftime('%d.%m.%Y %H:%M')
            s += '</p>\n'
            fn = os.path.join(self.target_path,'forecast-'+placemark['id'].replace(',','_').replace(' ','_')+'.inc')
            if dryrun:
                print(s)
            else:
                with open(fn,"w") as file:
                    file.write(s)
    
    def dump(self, placemark, days, recs6hr, recs3hr, timesteps, daynights, issue, dryrun, lang='de'):
        fn = os.path.join(self.target_path,'forecast-'+placemark['id'].replace(',','_').replace(' ','_')+'.json')
        with open(fn,"w") as file:
            hours = []
            for idx,val in enumerate(timesteps):
                hour = {'timestamp':int(val*0.001),'night':daynights[idx]}
                for ii in placemark['Forecast']:
                    hour[ii] = placemark['Forecast'][ii][idx]

                wwcode = get_ww([placemark['Forecast']['ww'][idx]],placemark['Forecast']['Neff'][idx],daynights[idx])
                icon = self.icon_pth + '/' + wwcode[self.iconset]
                if self.iconset == 6: icon += ('n' if night else '') + '.png'

                hour['icon'] = icon
                hour['icontitle'] = wwcode[2] if lang == 'en' else wwcode[1]

                hours.append(hour)
            x = {
                'Issuer':issue.get('Issuer'),
                'ProductID':issue.get('ProductID'),
                'GeneratingProcess':issue.get('GeneratingProcess'),
                'IssueTime':issue.get('IssueTime'),
                'IssueTimeISO':issue.get('IssueTimeISO'),
                'ReferenceModel':issue.get('ReferenceModel'),
                'id':placemark.get('id'),
                'name':placemark.get('description'),
                'coordinates':placemark.get('coordinates'),
                'ForecastDaily':[days[day] for day in days],
                'Forecast6hr':recs6hr,
                'Forecast3hr':recs3hr,
                'ForecastHourly':hours}
            json.dump(x,file,indent=4,ensure_ascii=False)
            
    def belchertown(self, placemark, days, recs6h, recs3h, timesteps, daynights, issue, dryrun):
        geo = placemark['coordinates']
        """
        if has_pyephem:
            try:
                location = ephem.Observer()
                location.lat = geo[1]*0.017453292519943
                location.lon = geo[0]*0.017453292519943
                location.elevation = geo[2]
            except Exception as e:
                logerr('Observer: %s' % e)
        else:
            location = None
        """
        fn = os.path.join(self.target_path,'geo-%s.json' % placemark['id'])
        try:
            with open(fn,"r") as file:
                geodata = json.load(file)
            if self.verbose:
                loginf("geo file '%s' succuessfully loaded" % fn)
        except Exception:
            geodata = None
        if has_geopy and not geodata:
            geodata = DwdMosmix.geo(geo[1],geo[0])
            if self.verbose:
                loginf("%s  geo data" % ("successfully retrieved" if geodata else "failed to retrieve"))
            if geodata and not dryrun:
                try:
                    with open(fn,"w") as file:
                        json.dump(geodata,file,indent=4,ensure_ascii=False)
                except Exception as e:
                    logerr('error writing %s: %s' % (fn,e))
        #print(geodata)
        if has_geopy and geodata:
            try:
                rel_dist = distance.distance((geodata['lat'],geodata['lon']),(self.latitude,self.longitude))
                rel_dist_km = rel_dist.km
                rel_dist_mi = rel_dist.miles
            except Exception:
                rel_dist = None
                rel_dist_km = None
                rel_dist_mi = None
        else:
            rel_dist = None
            rel_dist_km = None
            rel_dist_mi = None
        now = time.time()
        # creation time
        forecast = {'timestamp':int(now)}
        for idx,ii in enumerate(timesteps):
            if now<=ii*0.001:
                if self.verbose:
                    loginf("now %s timestep %s" % (time.strftime('%H:%M:%S',time.localtime(now)),time.strftime('%H:%M:%S',time.localtime(timesteps[idx]*0.001))))
                break
        #night = self.is_night(location,timesteps[idx]*0.001)
        night = daynights[idx]
        wwcode = get_ww([placemark['Forecast']['ww'][idx]],placemark['Forecast']['Neff'][idx],night)
        forecast['current'] = [{
            'success':True,
            'error':None,
            'source':'MOSMIX',
            'response':{
                'id':placemark['id'],
                'dataSource':issue['ReferenceModel']['name'],
                'loc':{
                    'long':geo[0],
                    'lat':geo[1]},
                'place':{
                    'name':placemark['description'],
                    'city':placemark['description'],
                    'state':geodata['state'] if geodata else '',
                    'country':geodata['country_code'] if geodata else ''},
                'profile':{
                    'tz':'Europe/Berlin',
                    'tzname':'CET',
                    'tzoffset':3600,
                    'isDST':False,
                    'elevM':geo[2]},
                'obTimestamp':int(issue['IssueTime']*0.001),
                'obDateTime':issue['IssueTimeISO'],
                'ob':{
                    'timestamp':int(timesteps[idx]*0.001),
                    'dateTimeISO':DwdMosmix.isoformat(timesteps[idx]*0.001),
                    'tempC':nround(placemark['Forecast']['TTT'][idx],1),
                    'tempF':nround(fahrenheit(placemark['Forecast']['TTT'][idx]),1),
                    'dewpointC':nround(placemark['Forecast']['Td'][idx],1) if 'Td' in placemark['Forecast'] else None,
                    'dewpointF':nround(fahrenheit(placemark['Forecast']['Td'][idx]),1) if 'Td' in placemark['Forecast'] else None,
                    'humidity':nround(humidity(placemark['Forecast']['TTT'][idx],placemark['Forecast']['Td'][idx]),0),
                    'pressureMB':nround(placemark['Forecast']['PPPP'][idx]),
                    'pressureIN':nround(inchHG(placemark['Forecast']['PPPP'][idx]),2),
                    'windKTS':nround(knoten(placemark['Forecast']['FF'][idx])),
                    'windKPH':nround(placemark['Forecast']['FF'][idx]),
                    'windMPH':nround(mph(placemark['Forecast']['FF'][idx])),
                    'windSpeedKTS':nround(knoten(placemark['Forecast']['FF'][idx])),
                    'windSpeedKPH':nround(placemark['Forecast']['FF'][idx]),
                    'windSpeedMPH':nround(mph(placemark['Forecast']['FF'][idx])),
                    'windDir':compass(nround(placemark['Forecast']['DD'][idx]),self.belchertown_compasslang,False),
                    'windDirDEG':nround(placemark['Forecast']['DD'][idx]),
                    'visibilityKM':placemark['Forecast']['VV'][idx]*0.001 if 'VV' in placemark['Forecast'] else None,
                    'weather':wwcode[1],
                    'weatherCoded':wwcode[7],
                    'weatherPrimary':wwcode[1],
                    'weatherPrimaryCoded':wwcode[7],
                    'cloudsCoded':get_cloudcover(placemark['Forecast']['N'][idx])[3],
                    'icon':wwcode[6]+('n' if night else '')+'.png',
                    'solradWM2':placemark['Forecast']['Rad1h'][idx] if 'Rad1h' in placemark['Forecast'] else None,
                    'isDay':not night,
                    'sky':int(placemark['Forecast']['N'][idx]),
                    'weathercode':wwcode[0]
                },
                'raw':'',
                'relativeTo':{
                    'lat':self.latitude,
                    'long':self.longitude,
                    'distanceKM':nround(rel_dist_km,1),
                    'distanceMI':nround(rel_dist_mi,1)
                }
            }}]
        belchertown_days = []
        for day in days:
            wwcode = get_ww(days[day]['ww'],days[day]['Neffavg'],False)
            belchertown_days.append({
                'timestamp':days[day]['timestamp'],
                'validTime':DwdMosmix.isoformat(days[day]['timestamp']),
                'dateTimeISO':DwdMosmix.isoformat(days[day]['timestamp']),
                'maxTempC':nround(days[day]['TTTmax'],1),
                'maxTempF':nround(fahrenheit(days[day]['TTTmax']),1),
                'minTempC':nround(days[day]['TTTmin'],1),
                'minTempF':nround(fahrenheit(days[day]['TTTmin']),1),
                'avgTempC':nround(days[day]['TTTavg'],1),
                'avgTempF':nround(fahrenheit(days[day]['TTTavg']),1),
                'tempC':None,
                'tempF':None,
                'maxDewpointC':nround(days[day]['Tdmax'],1),
                'maxDewpointF':nround(fahrenheit(days[day]['Tdmax']),1),
                'minDewpointC':nround(days[day]['Tdmin'],1),
                'minDewpointF':nround(fahrenheit(days[day]['Tdmin']),1),
                'avgDewpointC':nround(days[day]['Tdavg'],1),
                'avgDewpointF':nround(fahrenheit(days[day]['Tdavg']),1),
                'dewpointC':None,
                'dewpointF':None,
                'humidity':nround(humidity(days[day]['TTTavg'],days[day]['Tdavg']),0),
                'pop':days[day].get('Rd10'),
                #'pop':days[day].get('Rd10',days[day].get('Rh10',days[day].get('R610',days[day].get('R101',None)))),
                'precipMM':nround(days[day].get('RR1c'),1),
                'precipIN':nround(mm_to_inch(days[day].get('RR1c')),1),
                'pressureMB':nround(days[day]['PPPPavg']),
                'pressureIN':nround(inchHG(days[day]['PPPPavg']),2),
                'windDir':compass(days[day]['DDavg'],self.belchertown_compasslang,False),
                'windDirDEG':nround(days[day]['DDavg']),
                'windSpeedKTS':nround(knoten(days[day]['FFavg'])),
                'windSpeedKPH':nround(days[day]['FFavg']),
                'windSpeedMPH':nround(mph(days[day]['FFavg'])),
                'windGustKTS':nround(knoten(days[day]['FX1max'])),
                'windGustKPH':nround(days[day]['FX1max']),
                'windGustMPH':nround(mph(days[day]['FX1max'])),
                'sky':nround(days[day]['Neffavg']),
                'cloudsCoded':get_cloudcover(days[day]['Neffavg'])[3],
                'weather':wwcode[1],
                'weatherCoded':wwcode[7],
                'weatherPrimary':wwcode[1],
                'weatherPrimaryCoded':wwcode[7],
                'icon':wwcode[6]+'.png',
                'isDay':True,
                'weathercode':wwcode[0]})
            if len(belchertown_days)>=self.forecast_max_days: break
        forecast['forecast_24hr'] = [{
            'success':True,
            'error':None,
            'response':[{
                'loc':{
                    'long':geo[0],
                    'lat':geo[1]},
                'interval':'day',
                'periods':belchertown_days,
                'profile':{
                    'tz':'Europe/Berlin',
                    'elevM':geo[2]}}]}]
        belchertown_hours = []
        for rec in recs3h:
            if rec['timestamp']>now:
                wwcode = get_ww([rec['ww3']],rec['Neffavg'],rec['night'])
                hour = {
                    'timestamp':rec['timestamp'],
                    'validTime':DwdMosmix.isoformat(rec['timestamp']),
                    'dateTimeISO':DwdMosmix.isoformat(rec['timestamp']),
                    'maxTempC':rec['TTTmax'],
                    'maxTempF':fahrenheit(rec['TTTmax']),
                    'minTempC':rec['TTTmin'],
                    'minTempF':fahrenheit(rec['TTTmin']),
                    'avgTempC':rec['TTTavg'],
                    'avgTempF':fahrenheit(rec['TTTavg']),
                    'tempC':rec['TTT'],
                    'tempF':fahrenheit(rec['TTT']),
                    'maxDewpointC':rec.get('Tdmax'),
                    'maxDewpointF':fahrenheit(rec.get('Tdmax')),
                    'minDewpointC':rec.get('Tdmin'),
                    'minDewpointF':fahrenheit(rec.get('Tdmin')),
                    'avgDewpointC':rec.get('Tdavg'),
                    'avgDewpointF':fahrenheit(rec.get('Tdavg')),
                    'dewpointC':rec.get('Td'),
                    'dewpointF':fahrenheit(rec.get('Td')),
                    'humidity':nround(humidity(rec['TTT'],rec['Td']),0),
                    'pop':rec.get('R101max'),
                    'pressureMB':rec['PPPPavg'],
                    'pressureIN':nround(inchHG(rec['PPPPavg']),2),
                    'windDir':compass(rec['DDavg'],self.belchertown_compasslang,False),
                    'windDirDEG':rec['DDavg'],
                    'windSpeedKTS':nround(knoten(rec['FFavg'])),
                    'windSpeedKPH':rec['FFavg'],
                    'windSpeedMPH':nround(mph(rec['FFavg'])),
                    'windSpeedMaxKTS':nround(knoten(rec['FFmax'])),
                    'windSpeedMaxKPH':rec['FFmax'],
                    'windSpeedMaxMPH':nround(mph(rec['FFmax'])),
                    'windSpeedMinKTS':nround(knoten(rec['FFmin'])),
                    'windSpeedMinKPH':rec['FFmin'],
                    'windSpeedMinMPH':nround(mph(rec['FFmin'])),
                    'windGustKTS':nround(knoten(rec.get('FX3'))),
                    'windGustKPH':rec.get('FX3'),
                    'windGustMPH':nround(mph(rec.get('FX3'))),
                    'sky':int(rec['Neffavg']),
                    'cloudsCoded':get_cloudcover(rec['Neffavg'])[3],
                    'weather':wwcode[1],
                    'weatherCoded':[],
                    'weatherPrimary':wwcode[1],
                    'weatherPrimaryCoded':wwcode[7],
                    'icon':wwcode[6]+('n' if night else '')+'.png',
                    'visibilityKM':rec['VVmin']/1000.0 if rec.get('VVmin') is not None else None,
                    'isDay':not rec['night'],
                    'maxCoverage':'',
                    'weathercode':wwcode[0]
                    }
                belchertown_hours.append(hour)
            if len(belchertown_hours)>=8: break
        forecast['forecast_3hr'] = [{
            'success':len(belchertown_hours)>0,
            'error':'',
            'response':[{
                'loc':{
                    'long':geo[0],
                    'lat':geo[1]},
                'interval':'3hr',
                'periods':belchertown_hours,
                'profile':{
                    'tz':'Europe/Berlin',
                    'elevM':geo[2]}}]}]
        belchertown_hours = []
        for rec in recs6h:
            if rec['timestamp']>now:
                wwcode = get_ww([rec['ww3']],rec['Neffavg'],rec['night'])
                hour = {
                    'timestamp':rec['timestamp'],
                    'validTime':DwdMosmix.isoformat(rec['timestamp']),
                    'dateTimeISO':DwdMosmix.isoformat(rec['timestamp']),
                    'maxTempC':rec['TTTmax'],
                    'maxTempF':fahrenheit(rec['TTTmax']),
                    'minTempC':rec['TTTmin'],
                    'minTempF':fahrenheit(rec['TTTmin']),
                    'avgTempC':rec['TTTavg'],
                    'avgTempF':fahrenheit(rec['TTTavg']),
                    'tempC':rec['TTT'],
                    'tempF':fahrenheit(rec['TTT']),
                    'maxDewpointC':rec.get('Tdmax'),
                    'maxDewpointF':fahrenheit(rec.get('Tdmax')),
                    'minDewpointC':rec.get('Tdmin'),
                    'minDewpointF':fahrenheit(rec.get('Tdmin')),
                    'avgDewpointC':rec.get('Tdavg'),
                    'avgDewpointF':fahrenheit(rec.get('Tdavg')),
                    'dewpointC':rec.get('Td'),
                    'dewpointF':fahrenheit(rec.get('Td')),
                    'humidity':nround(humidity(rec['TTT'],rec['Td']),0),
                    'pop':rec.get('R101max'),
                    'pressureMB':rec['PPPPavg'],
                    'pressureIN':nround(inchHG(rec['PPPPavg']),2),
                    'windDir':compass(rec['DDavg'],self.belchertown_compasslang,False),
                    'windDirDEG':rec['DDavg'],
                    'windSpeedKTS':nround(knoten(rec['FFavg'])),
                    'windSpeedKPH':rec['FFavg'],
                    'windSpeedMPH':nround(mph(rec['FFavg'])),
                    'windSpeedMaxKTS':nround(knoten(rec['FFmax'])),
                    'windSpeedMaxKPH':rec['FFmax'],
                    'windSpeedMaxMPH':nround(mph(rec['FFmax'])),
                    'windSpeedMinKTS':nround(knoten(rec['FFmin'])),
                    'windSpeedMinKPH':rec['FFmin'],
                    'windSpeedMinMPH':nround(mph(rec['FFmin'])),
                    'windGustKTS':nround(knoten(rec.get('FX3'))),
                    'windGustKPH':rec.get('FX3'),
                    'windGustMPH':nround(mph(rec.get('FX3'))),
                    'sky':int(rec['Neffavg']),
                    'cloudsCoded':get_cloudcover(rec['Neffavg'])[3],
                    'weather':wwcode[1],
                    'weatherCoded':[],
                    'weatherPrimary':wwcode[1],
                    'weatherPrimaryCoded':wwcode[7],
                    'icon':wwcode[6]+('n' if night else '')+'.png',
                    'visibilityKM':rec['VVmin']/1000.0 if rec.get('VVmin') is not None else None,
                    'isDay':not rec['night'],
                    'maxCoverage':'',
                    'weathercode':wwcode[0]
                    }
                belchertown_hours.append(hour)
            if len(belchertown_hours)>=8: break
        forecast['forecast_6hr'] = [{
            'success':len(belchertown_hours)>0,
            'error':'',
            'response':[{
                'loc':{
                    'long':geo[0],
                    'lat':geo[1]},
                'interval':'3hr',
                'periods':belchertown_hours,
                'profile':{
                    'tz':'Europe/Berlin',
                    'elevM':geo[2]}}]}]
        belchertown_hours = []
        for idx,ii in enumerate(timesteps):
            if (ii*0.001)<now: continue
            #night = self.is_night(location,ii*0.001)
            night = daynights[idx]
            wwcode = get_ww([placemark['Forecast']['ww'][idx]],placemark['Forecast']['Neff'][idx],night)
            hour = {
                'timestamp':int(ii*0.001),
                'validTime':DwdMosmix.isoformat(ii*0.001),
                'dateTimeISO':DwdMosmix.isoformat(ii*0.001),
                'maxTempC':placemark['Forecast']['TTT'][idx],
                'maxTempF':fahrenheit(placemark['Forecast']['TTT'][idx]),
                'minTempC':placemark['Forecast']['TTT'][idx],
                'minTempF':fahrenheit(placemark['Forecast']['TTT'][idx]),
                'avgTempC':placemark['Forecast']['TTT'][idx],
                'avgTempF':fahrenheit(placemark['Forecast']['TTT'][idx]),
                'tempC':placemark['Forecast']['TTT'][idx],
                'tempF':fahrenheit(placemark['Forecast']['TTT'][idx]),
                'maxDewpointC':placemark['Forecast']['Td'][idx] if 'Td' in placemark['Forecast'] else None,
                'maxDewpointF':fahrenheit(placemark['Forecast']['Td'][idx]) if 'Td' in placemark['Forecast'] else None,
                'minDewpointC':placemark['Forecast']['Td'][idx] if 'Td' in placemark['Forecast'] else None,
                'minDewpointF':fahrenheit(placemark['Forecast']['Td'][idx]) if 'Td' in placemark['Forecast'] else None,
                'avgDewpointC':placemark['Forecast']['Td'][idx] if 'Td' in placemark['Forecast'] else None,
                'avgDewpointF':fahrenheit(placemark['Forecast']['Td'][idx]) if 'Td' in placemark['Forecast'] else None,
                'dewpointC':placemark['Forecast']['Td'][idx] if 'Td' in placemark['Forecast'] else None,
                'dewpointF':fahrenheit(placemark['Forecast']['Td'][idx]) if 'Td' in placemark['Forecast'] else None,
                'humidity':nround(humidity(placemark['Forecast']['TTT'][idx],placemark['Forecast']['Td'][idx]),0),
                'pop':placemark['Forecast']['R101'][idx] if 'R101' in placemark['Forecast'] else None,
                'precipMM':placemark['Forecast']['RR1c'][idx] if 'RR1c' in placemark['Forecast'] else None,
                'precipIN':mm_to_inch(placemark['Forecast']['RR1c'][idx]) if 'RR1c' in placemark['Forecast'] else None,
                'pressureMB':placemark['Forecast']['PPPP'][idx],
                'pressureIN':nround(inchHG(placemark['Forecast']['PPPP'][idx]),2),
                'windDir':compass(placemark['Forecast']['DD'][idx],self.belchertown_compasslang,False),
                'windDirDEG':placemark['Forecast']['DD'][idx],
                'windSpeedKTS':nround(knoten(placemark['Forecast']['FF'][idx])),
                'windSpeedKPH':placemark['Forecast']['FF'][idx],
                'windSpeedMPH':nround(mph(placemark['Forecast']['FF'][idx])),
                'windGustKTS':nround(knoten(placemark['Forecast']['FX1'][idx])) if 'FX1' in placemark['Forecast'] else None,
                'windGustKPH':placemark['Forecast']['FX1'][idx] if 'FX1' in placemark['Forecast'] else None,
                'windGustMPH':nround(mph(placemark['Forecast']['FX1'][idx])) if 'FX1' in placemark['Forecast'] else None,
                'sky':int(placemark['Forecast']['Neff'][idx]),
                'cloudsCoded':get_cloudcover(placemark['Forecast']['Neff'][idx])[3],
                'weather':wwcode[1],
                'weatherCoded':wwcode[7],
                'weatherPrimary':wwcode[1],
                'weatherPrimaryCoded':wwcode[7],
                'icon':wwcode[6]+('n' if night else '')+'.png',
                'visibilityKM':placemark['Forecast']['VV'][idx]*0.001 if 'VV' in placemark['Forecast'] else None,
                'solradWM2':placemark['Forecast']['Rad1h'][idx] if 'Rad1h' in placemark['Forecast'] else None,
                'solradMinWM2':placemark['Forecast']['Rad1hmin'][idx] if 'Rad1hmin' in placemark['Forecast'] else None,
                'solradMaxWM2':placemark['Forecast']['Rad1hmax'][idx] if 'Rad1hmax' in placemark['Forecast'] else None,
                'isDay':not night,
                'weathercode':[placemark['Forecast']['ww'][idx]]
                }
            belchertown_hours.append(hour)
            if len(belchertown_hours)>=16: break
        forecast['forecast_1hr'] = [{
            'success':True,
            'error':None,
            'response':[{
                'loc':{
                    'long':geo[0],
                    'lat':geo[1]},
                'interval':'1hr',
                'periods':belchertown_hours,
                'profile':{
                    'tz':'Europe/Berlin',
                    'elevM':geo[2]}}]}]
        # weather alerts
        belchertown_alerts = []
        try:
            with open(os.path.join(self.target_path,'warn-'+self.belchertown_warning+'.json'),'r') as file:
                alerts = json.load(file)
            for alert in alerts:
                al = {
                    'id':alert.get('identifier'),
                    'loc':{},
                    'dataSource':alert.get('source'),
                    'details':{
                        'type':'AW.'+
                               ['TS','WI','RA','SI','FG','LT','SI','SI','HT','HT',''][alert.get('type',10)]+
                               '.'+
                               ['','','MN','MD','SV','EX'][alert.get('level',0)],
                        'name':alert.get('event'),
                        'loc':'',
                        'emergency':None,
                        'priority':None,
                        'color':None,
                        'cat':alert.get('eventCode-GROUP'),
                        'body':alert.get('description'),
                        'bodyFull':alert.get('description','')+alert.get('instruction','')
                    },
                    'timestamps':{
                        'issued':int(alert.get('sent',0.0)*0.001),
                        'begins':int(alert.get('start',0.0)*0.001),
                        'expires':int(alert.get('end',0.0)*0.001),
                        'updated':int(alert.get('sent',0.0)*0.001),
                        'added':int(alert.get('released',0.0)*0.001),
                        'created':int(alert.get('released',0.0)*0.001)
                    },
                    'poly':"",
                    'geoPoly':None,
                    'includes':{},
                    'place':{},
                    'profile':{},
                    'active':alert.get('status','')=='Actual'
                }
                if al['timestamps']['begins']<(now+self.belchertown_include_advance_warning) and al['timestamps']['expires']>now:
                    belchertown_alerts.append(al)
            success = True
            err = ''
        except Exception as e:
            if self.log_failure or self.verbose:
                logerr(e)
            success = False
            err = str(e)
            alerts = []
        forecast['alerts'] = [{
            'success':success,
            'error':None if success else {'code':str(err),'description':str(err)},
            'response':belchertown_alerts }]
        # AQI
        if self.belchertown_aqi_source is not None:
            if self.belchertown_aqi_source=='aeris':
                try:
                    if self.forecast_api_id and self.forecast_api_secret:
                        forecast['aqi'] = self.download_aeris('aqi')
                    else:
                        raise Exception
                except Exception as e:
                    if self.log_failure or self.verbose:
                        logerr(e)
                    forecast['aqi'] = [{
                        'success':False,
                        'error':{'code':e.__name__,
                                'description':str(e)},
                        'response':[] }]
            elif self.belchertown_aqi_source[0:3]=='uba':
                try:
                    forecast['aqi'] = self.download_uba('aqi',self.belchertown_aqi_source[3:])
                except Exception as e:
                    if self.log_failure or self.verbose:
                        logerr(e)
                    forecast['aqi'] = [{
                        'success':False,
                        'error':{'code':e.__name__,
                                'description':str(e)},
                        'response':[] }]
            
            else:
                forecast['aqi'] = [{
                    'success':False,
                    'error':{'code':'not_configured',
                            'description':'no AQI source configured'},
                    'response':[] }]
        else:
            forecast['aqi'] = [{
                'success':False,
                'error':{'code':'not_configured',
                        'description':'no AQI source configured'},
                'response':[] }]

        if self.belchertown_forecast_filename and self.belchertown_forecast:
            fn = os.path.join(self.target_path,self.belchertown_forecast_filename)
            fnt = os.path.join(self.target_path,self.belchertown_forecast_filename+'.tmp')
        elif self.belchertown_html_root and self.belchertown_forecast and self.belchertown_forecast==placemark['id'] and not self.belchertown_forecast_filename:
            fn = os.path.join(self.belchertown_html_root,'json','forecast-%s-belchertown.json' % placemark['id'])
            fnt = os.path.join(self.belchertown_html_root,'json','forecast-%s-belchertown.json.tmp' % placemark['id'])
        else:
            fn = os.path.join(self.target_path,'forecast-%s-belchertown.json' % placemark['id'])
            fnt = os.path.join(self.target_path,'forecast-%s-belchertown.json.tmp' % placemark['id'])
        if dryrun:
            s = json.dumps(forecast,indent=4,ensure_ascii=False)
            print(s)
        else:
            if self.verbose:
                loginf("write Belchertown JSON file to %s" % fnt)
            try:
                with open(fnt,"w") as file:
                    json.dump(forecast,file,indent=4,ensure_ascii=False)
                    if self.verbose:
                        loginf("move Belchertown JSON file to %s" % fn)
                    shutil.move(fnt, fn)
            except Exception as e:
                logerr("error writing to '%s': %s" % (fn,e))

    
    def download_aeris(self, what):
        if what=='aqi':
            url = (
                "https://api.aerisapi.com/airquality/closest?p=%s,%s&format=json&radius=50mi&limit=1&client_id=%s&client_secret=%s"
                % (self.latitude, self.longitude, self.forecast_api_id, self.forecast_api_secret)
                )
        else:
            return []

        headers={'User-Agent':'weewx-DWD'}
        try:
            reply = requests.get(url,headers=headers)
        except ConnectionError as e:
            if self.log_failure:
                logerr(e)
            return []
        
        if reply.status_code==200:
            if self.log_success or self.verbose:
                loginf('successfully downloaded %s' % reply.url)
            try:
                return [json.loads(reply.content)]
            except Exception as e:
                return [{'success':False,'error':{'code':e.__name__,'description':str(e)},'response':[]}]
        else:
            if self.log_failure or self.verbose:
                logerr('error downloading %s: %s %s' % (reply.url,reply.status_code,reply.reason))
            return [{
                'success':False,
                'error':{'code':reply.status_code,'description':reply.reason},
                'response':[] }]

    def download_uba(self, what, station, lang='de'):
        """ Download air quality data from Umweltbundesamt """
        # get data from yesterday
        ts0 = time.time()-86400
        ti0 = time.localtime(ts0)
        dt0 = time.strftime('%Y-%m-%d',ti0)
        # to today
        ts = time.time()
        ti = time.localtime(ts)
        dt = time.strftime('%Y-%m-%d',ti)
        # 'meta' has a second parameter
        try:
            what,use = what.split(',')
        except ValueError:
            use = 'airquality'
        # compose url
        if what in ['aqi','airquality']:
            url = 'airquality/json?date_from=%s&date_to=%s&lang=%s' % (dt0,dt,lang)
            if station: url += '&station=%s' % station
            fn = os.path.join(self.target_path,'uba_components.json')
            try:
                with open(fn,'r') as file:
                    components = json.load(file)
            except Exception:
                components = self.download_uba('components',None,lang)
                with open(fn,'w') as file:
                    json.dump(components,file,indent=4,ensure_ascii=False)
        elif what in ['components','networks','scopes']:
            url = '%s/json?lang=%s&index=id' % (what,lang)
        elif what in ['stationsettings','stationtypes','transgessiontypes']:
            url = '%s/json?lang=%s' % (what,lang)
        elif what=='meta':
            url = 'meta/json?use=%s&date_from=%s&date_to=%s&lang=%s' % (use,dt0,dt,lang)
        else:
            if self.log_failure or self.verbose:
                logerr('%s not configured' % what)
            return [{'success':False,'error':{'code':'not configured','description':'%s not configured' % what,'response':[]}}]
        url = 'https://www.umweltbundesamt.de/api/air_data/v2/' + url

        # download data
        headers={'User-Agent':'weewx-DWD'}
        try:
            reply = requests.get(url,headers=headers)
        except ConnectionError as e:
            if self.log_failure or self.verbose:
                logerr(e)
            return [{'success':False,'error':{'code':e.__name__,'description':str(e)},'response':[]}]
        
        if reply.status_code==200:
            if self.log_success or self.verbose:
                loginf('successfully downloaded %s' % reply.url)
            try:
                rtn = json.loads(reply.content)
            except Exception as e:
                if self.log_failure or self.verbose:
                    logerr(e)
                return [{'success':False,'error':{'code':e.__name__,'description':str(e)},'response':[]}]
            if what in ['aqi','airquality']:
                res = dict()
                comp = dict()
                for ii in rtn:
                    if ii=='data':
                        res[ii] = dict()
                        for jj in rtn[ii]:
                            res[ii][jj] = []
                            for kk in rtn[ii][jj]:
                                point = dict()
                                point['date start'] = kk
                                for ix,vv in enumerate(rtn[ii][jj][kk]):
                                    if ix==0:
                                        point['date end'] = vv
                                    elif ix==1:
                                        point['total index'] = vv
                                    elif ix==2:
                                        point['data incomplete'] = vv
                                    else:
                                        point[vv[0]] = {
                                            'component id':vv[0],
                                            'value':vv[1],
                                            'index':vv[2],
                                            'y-value':vv[3],
                                        }
                                        comp[vv[0]] = components[str(vv[0])]
                                res[ii][jj].append(point)
                            res[ii][jj].sort(key=lambda x:x['date start'])
                    else:
                        res[ii] = rtn[ii]
                res['components'] = comp
                # command 'aqi' converts to Belchertown format
                if what=='aqi':
                    aqi = {
                        'success':True,
                        'error':None,
                        'response':[]
                    }
                    for ii in res['data']:
                        vals = res['data'][ii][-1]
                        pols = [{'type':comp[vals[x]['component id']]['component code'],
                                 'name':comp[vals[x]['component id']]['component name'],
                                 'valuePPB':None,
                                 'valueUGM3':vals[x]['value'],
                                 'uba_index':vals[x]['index'],
                                 'aqi':epaaqi(comp[vals[x]['component id']]['component code'],vals[x]['value']),
                                 'category':uba_category(vals[x]['index'],lang),
                                 'color':uba_category(vals[x]['index'],'color'),
                                 'unit':comp[vals[x]['component id']]['component unit']
                                 } for x in vals if isinstance(vals[x],dict)]
                        #aidx = max([vals[x]['index'] for x in vals if isinstance(vals[x],dict)])
                        uidx = max([x['uba_index'] for x in pols])
                        aidx = max([x['aqi'] for x in pols])
                        tse = DwdMosmix.timestamp(vals['date end'])
                        te = DwdMosmix.isoformat(tse) if tse is not None else vals['date end']
                        aqi['response'].append({
                            'id':ii,
                            'loc':{'long':None,'lat':None},
                            'place':{'name':'Weiden','state':'de','country':'by'},
                            'periods':[{
                                'dateTimeISO':te,
                                'timestamp':tse,
                                'uba_index':uidx,
                                'aqi':aidx,
                                'category':uba_category(uidx,lang),
                                'color':uba_category(uidx,'color'),
                                'method':'airnow',
                                'dominant':None,
                                'pollutants':pols
                            }],
                            'profile':{'tz':None,'sources':[],'stations':[]},
                            'relativeTo':{
                                'lat': self.latitude,
                                'long': self.longitude,
                                'bearing':None,
                                'bearingENG':None,
                                'distanceKM':None,
                                'distanceMI':None,
                            }
                        })
                    res = aqi
                else:
                    res['components'] = comp
            elif 'indices' in rtn:
                res = dict()
                for ii in rtn:
                    if ii not in ['indices','count','request']:
                        res[ii] = dict()
                        for idx,val in enumerate(rtn[ii]):
                            try:
                                res[ii][rtn['indices'][idx]] = val
                            except LookupError:
                                pass
            else:
                res = rtn
            if what=='aqi':
                return [res]
            else:
                return res
        else:
            if self.log_failure or self.verbose:
                logerr('error downloading %s: %s %s' % (reply.url,reply.status_code,reply.reason))
            return [{
                'success':False,
                'error':{'code':reply.status_code,'description':reply.reason},
                'response':[] }]

    
    def calculate_3hr_forecast(self, placemark, timesteps, daynights, lang='de'):
        """ """
        """
        if has_pyephem:
            try:
                location = ephem.Observer()
                # location of the forecast
                geo = placemark['coordinates']
                location.lat = geo[1]*0.017453292519943
                location.lon = geo[0]*0.017453292519943
                location.elevation = geo[2]
            except Exception as e:
                logerr('Observer: %s' % e)
        """
        recs = []
        for idx,val in enumerate(timesteps):
            if 'ww3' in placemark['Forecast']:
                ok = placemark['Forecast']['ww3'][idx] is not None
            else:
                ok = (val%10800000)==0
            if ok:
                vals = {ii:placemark['Forecast'][ii][idx] for ii in placemark['Forecast'] if placemark['Forecast'][ii][idx] is not None}
                vals['timestamp'] = int(val*0.001)
                try:
                    ww = []
                    if idx>=2: ww.append(int(placemark['Forecast']['ww'][idx-2]))
                    if idx>=1: ww.append(int(placemark['Forecast']['ww'][idx-1]))
                    ww.append(int(placemark['Forecast']['ww'][idx]))
                    vals['ww'] = ww
                except Exception:
                    vals['ww'] = []
                try:
                    vals['ww3'] = int(placemark['Forecast']['ww3'][idx])
                except Exception:
                    vals['ww3'] = get_ww(vals['ww'],0,None)
                # which observations are available?
                observations = []
                for ii in ['PPPP','TTT','Td','T5cm','DD','FF','N','Neff','VV','R101']:
                    if ii in placemark['Forecast']:
                        observations.append(ii)
                if self.verbose:
                    loginf("3hr-forecast available observations %s" % observations)
                # calculate min, max, and avg for hourly observerations
                for ii in observations:
                    try:
                        # collect the last 3 observations
                        p = []
                        if idx>=2: 
                            val = placemark['Forecast'][ii][idx-2]
                            if val is not None: p.append(val)
                        if idx>=1: 
                            val = placemark['Forecast'][ii][idx-1]
                            if val is not None: p.append(val)
                        val = placemark['Forecast'][ii][idx]
                        if val is not None: p.append(val)
                        # min value
                        try:
                            vals[ii+'min'] = min(p)
                        except Exception:
                            vals[ii+'min'] = None
                        # max value
                        try:
                            vals[ii+'max'] = max(p)
                        except Exception:
                            vals[ii+'max'] = None
                        # avg value
                        try:
                            vals[ii+'avg'] = sum(p)/len(p)
                        except Exception:
                            vals[ii+'avg'] = None
                    except Exception as e:
                        logerr("3hr-forecast %s %s %s" % (ii,e.__class__.__name__,e))
                # Is the timestamp night or day?
                try:
                    #night = self.is_night(location,val*0.001)
                    night = daynights[idx]
                except Exception:
                    night = None
                # weather symbol
                try:
                    wwcode = get_ww([vals['ww3']],vals['Neffavg'],night)
                    icon = self.icon_pth+'/'+wwcode[self.iconset]
                    if self.iconset==6: icon += ('n' if night else '')+'.png'
                    vals['night'] = night
                    vals['icon'] = icon
                    vals['icontitle'] = wwcode[2] if lang=='en' else wwcode[1]
                except Exception as e:
                    logerr("3hr-forecast %s %s" % (e.__class__.__name__,e))
                # append new record to the list
                recs.append(vals)
        return recs

    
    def calculate_6hr_forecast(self, placemark, timesteps, daynights, lang='de'):
        """ """
        """
        if has_pyephem:
            try:
                location = ephem.Observer()
                # location of the forecast
                geo = placemark['coordinates']
                location.lat = geo[1]*0.017453292519943
                location.lon = geo[0]*0.017453292519943
                location.elevation = geo[2]
            except Exception as e:
                logerr('Observer: %s' % e)
        """
        recs = []
        for idx,val in enumerate(timesteps):
            if 'ww3' in placemark['Forecast']:
                ok = placemark['Forecast']['ww3'][idx] is not None
            else:
                ok = (val%21600000)==0
            if ok:
                vals = {ii:placemark['Forecast'][ii][idx] for ii in placemark['Forecast'] if placemark['Forecast'][ii][idx] is not None}
                vals['timestamp'] = int(val*0.001)
                try:
                    ww = []
                    if idx>=2: ww.append(int(placemark['Forecast']['ww'][idx-2]))
                    if idx>=1: ww.append(int(placemark['Forecast']['ww'][idx-1]))
                    ww.append(int(placemark['Forecast']['ww'][idx]))
                    vals['ww'] = ww
                except Exception:
                    vals['ww'] = []
                try:
                    vals['ww3'] = int(placemark['Forecast']['ww3'][idx])
                except Exception:
                    vals['ww3'] = get_ww(vals['ww'],0,None)
                # which observations are available?
                observations = []
                for ii in ['PPPP','TTT','Td','T5cm','DD','FF','N','Neff','VV','R101']:
                    if ii in placemark['Forecast']:
                        observations.append(ii)
                if self.verbose:
                    loginf("6hr-forecast available observations %s" % observations)
                # calculate min, max, and avg for hourly observerations
                for ii in observations:
                    try:
                        # collect the last 3 observations
                        p = []
                        if idx>=2: 
                            val = placemark['Forecast'][ii][idx-2]
                            if val is not None: p.append(val)
                        if idx>=1: 
                            val = placemark['Forecast'][ii][idx-1]
                            if val is not None: p.append(val)
                        val = placemark['Forecast'][ii][idx]
                        if val is not None: p.append(val)
                        # min value
                        try:
                            vals[ii+'min'] = min(p)
                        except Exception:
                            vals[ii+'min'] = None
                        # max value
                        try:
                            vals[ii+'max'] = max(p)
                        except Exception:
                            vals[ii+'max'] = None
                        # avg value
                        try:
                            vals[ii+'avg'] = sum(p)/len(p)
                        except Exception:
                            vals[ii+'avg'] = None
                    except Exception as e:
                        logerr("6hr-forecast %s %s %s" % (ii,e.__class__.__name__,e))
                # Is the timestamp night or day?
                try:
                    #night = self.is_night(location,val*0.001)
                    night = daynights[idx]
                except Exception:
                    night = None
                # weather symbol
                try:
                    wwcode = get_ww([vals['ww3']],vals['Neffavg'],night)
                    icon = self.icon_pth+'/'+wwcode[self.iconset]
                    if self.iconset==6: icon += ('n' if night else '')+'.png'
                    vals['night'] = night
                    vals['icon'] = icon
                    vals['icontitle'] = wwcode[2] if lang=='en' else wwcode[1]
                except Exception as e:
                    logerr("6hr-forecast %s %s" % (e.__class__.__name__,e))
                # append new record to the list
                recs.append(vals)
        return recs
                
    
    def calculate_daily_forecast(self, placemark, timesteps, daynights, lang='de'):
        # observation types to calculate average for
        AVGS = ['TTT','Td','FF','DD','PPPP','N','Neff','VV']
        days = dict()
        # loop over all timestamps
        #ho Test, xx Tage analog Belchertown, keine weiteren Checks, ob option belchertown ...
        if self.forecast_max_days is not None:
            actDate = datetime.datetime.now()
            endDate = actDate + datetime.timedelta(days=self.forecast_max_days)
            actDate = int(actDate.strftime('%Y%m%d%H00'))
            endDate = int(endDate.strftime('%Y%m%d0000'))
        for idx,val in enumerate(timesteps):
            # the day of the actual timestep
            # The timestep marks the end of the interval. That's why
            # the timestep at the day border belongs to the ending
            # day (24:00 rather than 00:00). To get that the day is
            # calculated out of a timestamp 1 second before the actual
            # timestep.
            #ho Test, xx Tage analog Belchertown, keine weiteren Checks, ob option belchertown ...
            #original: day = time.strftime('%d.%m.',time.localtime(val*0.001-1))
            day = time.strftime('%d.%m.',time.localtime(val*0.001))
            if self.forecast_max_days is not None:
                checkDate = int(time.strftime('%Y%m%d%H%M',time.localtime(val*0.001-1)))
                if (checkDate < actDate) or (checkDate > endDate):
                    if self.verbose:
                        print('calculate_daily_forecast: >>> skip forecast %s' % time.strftime('%d.%m.%Y %H:%M',time.localtime(val*0.001)))
                    continue
                if self.verbose:
                    print('calculate_daily_forecast: insert forecast %s' % time.strftime('%d.%m.%Y %H:%M',time.localtime(val*0.001)))
            # get the values for the actual timestep
            vals = {ii:placemark['Forecast'][ii][idx] for ii in placemark['Forecast']}
            # check if first timestamp of a new day
            if day not in days: 
                _wday = time.localtime(val*0.001-1).tm_wday
                days[day] = { 
                    'timestamp':int(val*0.001),
                    'day':day,
                    'weekday':_wday,
                    'weekdayshortname':WEEKDAY[lang][_wday],
                    'TTTmin':1000.0,
                    'TTTmax':-273.15,
                    'Tdmin':1000.0,
                    'Tdmax':-273.15,
                    'count':0,
                    'SunD1':0.0,
                    'RR1c':0.0,
                    'ww':[],
                    'FX1max':0.0,
                    'VVmin':100000000000.0,
                    'Rad1hsum':0.0}
                for ii in AVGS:
                    days[day][ii+'sum'] = 0.0
                    days[day][ii+'ct'] = 0
            days[day]['count'] += 1
            # min and max temperature
            ttt = vals.get('TTT')
            if ttt and ttt>days[day]['TTTmax']: days[day]['TTTmax'] = ttt
            if ttt and ttt<days[day]['TTTmin']: days[day]['TTTmin'] = ttt
            # min and max dewpoint
            td = vals.get('Td')
            if td and td>days[day]['Tdmax']: days[day]['Tdmax'] = td
            if td and td<days[day]['Tdmin']: days[day]['Tdmin'] = td
            # max wind gust
            try:
                    fx1 = vals['FX1']
                    if fx1 and fx1>days[day]['FX1max']: 
                        days[day]['FX1max'] = fx1
            except (TypeError,LookupError):
                    pass
            # minimum visibility
            try:
                vv = vals.get('VV')
                if vv and vv<days[day]['VVmin']: days[day]['VVmin'] = vv
            except (TypeError,LookupError):
                pass
            # sum values to get the average
            for ii in AVGS:
                try:
                    days[day][ii+'sum'] += vals[ii]
                    days[day][ii+'ct'] += 1
                except (TypeError,LookupError) as e:
                    if vals.get(ii) is not None:
                        logerr("%s: %s" % (ii,e))
            # sunshine duration
            try:
                days[day]['SunD1'] += vals['SunD1']/3600
            except (ValueError,TypeError,LookupError):
                # If the error is during night time, it is ignored.
                # If the error is during day time, SunD1 ist set invalid.
                if not daynights[idx]:
                    days[day]['SunD1'] = None
            if vals.get('RSunD') is not None: days[day]['RSunD'] = vals['RSunD']
            if vals.get('Rad1h'): days[day]['Rad1hsum'] += vals['Rad1h']/1000.0
            # rain
            #for ii in ['Rd00','Rd02','Rd10','Rd50']:
            #ho test
            # probability of precipitation during 1h, 6h, 12h, 24h
            for ii in POP:
                if vals.get(ii): days[day][ii] = vals[ii]
                #try:
                #    xx = placemark['Forecast'][ii][idx+1]
                #    if xx: days[day][ii] = xx
                #    #if xx: print(idx,ii,xx)
                #except (ValueError,IndexError):
                #    pass
            if vals.get('RR1c'): days[day]['RR1c'] += vals['RR1c']
            # collect weather codes of the day
            #ho test:
            #if vals['ww'] and vals['ww'] not in days[day]['ww']: days[day]['ww'].append(vals['ww'])
            #ho test:
            if (int(vals['ww']) >= 0) and vals['ww'] not in days[day]['ww']:days[day]['ww'].append(vals['ww'])
        # calculate averages and weather symbol for the days
        for day in days:
            # calculate averages
            for ii in AVGS:
                try:
                    days[day][ii+'avg'] = days[day][ii+'sum']/days[day][ii+'ct']
                except (TypeError,ArithmeticError,LookupError,ValueError):
                    days[day][ii+'avg'] = None
                try:
                    del days[day][ii+'sum']
                    del days[day][ii+'ct']
                except (LookupError,NameError):
                    pass
            # weather symbol
            wwcode = get_ww(days[day]['ww'],days[day]['Neffavg'],False)
            if wwcode[self.iconset] is None:
                days[day]['icon'] = 'unknown.png'
            else:
                days[day]['icon'] = self.icon_pth+'/'+wwcode[self.iconset]+('.png' if self.iconset==6 else '')
            days[day]['icontitle'] = wwcode[2] if lang=='en' else wwcode[1]
        return days


    def write_database(self, placemark, timesteps, issue):
        #print(placemark)
        #print(timesteps)
        if has_sqlite and self.SQLITE_ROOT:
            if issue.get('Issuer','')=='Open-Meteo':
                columns = [dwd_obs_to_weewx_obs(jj) for jj in placemark['Forecast']]
            else:
                columns = None
            self.dbm_open(placemark['id'],columns)
            cursor = self.dbm_cursor()
            self.dbm_truncate(cursor)
            #ho Test, xx Tage analog Belchertown, keine weiteren Checks, ob option belchertown ...
            if self.forecast_max_days is not None:
                actDate = datetime.datetime.now()
                endDate = actDate + datetime.timedelta(days=self.forecast_max_days)
                actDate = int(actDate.strftime('%Y%m%d%H00'))
                endDate = int(endDate.strftime('%Y%m%d0000'))
            for idx,ii in enumerate(timesteps):
                #ho Test, xx Tage analog Belchertown, keine weiteren Checks, ob option belchertown ...
                if self.forecast_max_days is not None:
                    checkDate = int(time.strftime('%Y%m%d%H%M',time.localtime(ii*0.001-1)))
                    if (checkDate < actDate) or (checkDate > endDate):
                        if self.verbose:
                            print('write_database: >>> skip forecast %s' % time.strftime('%d.%m.%Y %H:%M',time.localtime(ii*0.001)))
                        continue
                    if self.verbose:
                        print('write_database: insert forecast %s' % time.strftime('%d.%m.%Y %H:%M',time.localtime(ii*0.001)))
                values = {'dateTime':int(ii*0.001),
                          'usUnits':0x10,  # METRIC (rain in cm)
                          'interval':60,
                          'hour':time.localtime(ii*0.001).tm_hour,  # min.
                          'outTemp':None,
                          'dewpoint':None,
                          'humidity':None
                         }
                for jj in placemark['Forecast']:
                    key = dwd_obs_to_weewx_obs(jj)
                    if key and key in self.dbm_columns():
                        values[key] = placemark['Forecast'][jj][idx]
                        if key=='rain': values[key] *= 0.1
                try:
                    if values.get('outTemp') is not None and values.get('dewpoint') is not None:
                        values['humidity'] = humidity(values['outTemp'],values['dewpoint'])
                    self.dbm_insert(cursor,values)
                except sqlite3.Error as e:
                    logerr('dbm_insert: %s' % e)
            self.dbm_commit()
            self.dbm_close()


    def forecast_placemark(self, placemark, timesteps, issue, output, dryrun, lang='de'):
        """ create forecast for placemark placemark """
        if self.verbose:
            loginf('process placemark id "%s" name "%s"' % (placemark.get('id'),placemark.get('description')))
        
        daynights = self.calculate_daynight(placemark,timesteps)

        if ('daily' in output) or ('json' in output) or ('belchertown' in output):
            if self.verbose:
                loginf('calculate daily forecast')
            days = self.calculate_daily_forecast(placemark,timesteps,daynights,lang=lang)
            
        if ('json' in output) or ('belchertown' in output):
            if self.verbose:
                loginf('calculate 3hr forecast')
            recs3hr = self.calculate_3hr_forecast(placemark,timesteps,daynights,lang=lang)
            if self.verbose:
                loginf('calculate 6hr forecast')
            recs6hr = self.calculate_6hr_forecast(placemark,timesteps,daynights,lang=lang)
        
        if 'html' in output:
        
            if 'all' in output:
                if self.verbose:
                    loginf('output all data')
                self.write_html(placemark,timesteps,daynights,None,dryrun,lang=lang)

            if 'daily' in output:
                if self.verbose:
                    loginf('output daily forecast')
                self.write_html_daily(placemark,days,timesteps,issue,None,dryrun,lang=lang)

            if 'hourly' in output:
                if self.verbose:
                    loginf('output hourly forecast')
                self.write_html(placemark,timesteps,daynights,['TTT','FF','DD','RR1c','R101','PPPP','Rad1h'],dryrun,range=11,lang=lang)
        
        if 'json' in output:
            if self.verbose:
                loginf('json')
            self.dump(placemark,days,recs6hr,recs3hr,timesteps,daynights,issue,dryrun,lang=lang)
            
        if 'belchertown' in output:
            if self.verbose:
                loginf('belchertown')
            self.belchertown(placemark,days,recs6hr,recs3hr,timesteps,daynights,issue,dryrun)
            
        if 'database' in output:
            if self.verbose:
                loginf('database')
            self.write_database(placemark,timesteps,issue)
            
        if self.verbose:
            loginf('placemark id "%s" processed' % placemark.get('id'))


    def forecast_all(self, mos, output, dryrun, lang='de'):
        """ create forecast for all placemarks found """
        if self.verbose:
            loginf('what to output: %s' % output)
            loginf('start loop over placemarks')
        issue = {
            'Issuer':mos.get('Issuer'),
            'ProductID':mos.get('ProductID'),
            'GeneratingProcess':mos.get('GeneratingProcess'),
            'IssueTime':mos.get('IssueTime'),
            'IssueTimeISO':mos.get('IssueTimeISO'),
            'ReferenceModel':mos.get('ReferenceModel')}
        for placemark in mos.get('Placemark'):
            self.forecast_placemark(placemark, mos['ForecastTimeSteps'], issue, output, dryrun, lang)
        if self.verbose:
            loginf('end loop over placemarks')
    
    @staticmethod
    def print_icons_ww(iconset='dwd'):
        if not iconset or iconset.lower()=='belchertown':
            icons = dict()
            for ii in WW_LIST:
                if ii[4] not in icons: icons[ii[4]] = []
                icons[ii[4]].append(ii[0])
            print('Belchertown icons')
            print('=================')
            for ii in icons:
                print('%-16s: %s' % (ii,icons[ii]))
            if not iconset:
                print('')
        if not iconset or iconset.lower()=='dwd':
            icons = dict()
            for ii in WW_LIST:
                if ii[5] not in icons: icons[ii[5]] = []
                icons[ii[5]].append(ii[0])
            print('DWD icons')
            print('=================')
            for ii in icons:
                print('%-16s: %s' % (ii,icons[ii]))
                
    def dbm_open(self, id, columns=None):
        if has_sqlite and self.SQLITE_ROOT:
            fn = os.path.join(self.SQLITE_ROOT,'dwd-forecast-%s.sdb' % id)
            new = not os.path.exists(fn)
            self.connection = sqlite3.connect(fn)
            if columns:
                sch = [('dateTime','INTEGER NOT NULL PRIMARY KEY'),
                     ('usUnits','INTEGER NOT NULL'),
                     ('interval','INTEGER NOT NULL'),
                     ('hour','INTEGER'),
                     ('outTemp','REAL'),
                     ('dewpoint','REAL'),
                     ('humidity','REAL')]
                for x in columns:
                    if x is not None:
                        sch.append((x,'INTEGER' if x=='ww' else 'REAL'))
            else:
                sch = schema
            if new:
                s = ','.join([x[0]+' '+x[1] for x in sch])
                s = 'CREATE TABLE forecast ('+s+')'
                if self.verbose:
                    print('dbm_open',s)
                cur = self.dbm_cursor()
                if cur:
                    cur.execute(s)
                    self.dbm_commit()
            self.columns = [x[0] for x in sch]
            return True
        return False
        
    def dbm_close(self):
        if has_sqlite and self.SQLITE_ROOT:
            if self.connection:
                self.connection.close()
                self.connection = None
    
    def dbm_cursor(self):
        if self.connection:
            return self.connection.cursor()
        return None
        
    def dbm_commit(self):
        if self.connection:
            self.connection.commit()
        
    def dbm_truncate(self, cursor):
        if has_sqlite and self.SQLITE_ROOT:
            cursor.execute("DELETE from forecast")
            
    def dbm_insert(self, cursor, values):
        cols = []
        vals = []
        for ii in values:
            if ii in self.columns and values[ii] is not None:
                cols.append('`'+ii+'`')
                vals.append(str(values[ii]))
        cursor.execute('INSERT INTO forecast (%s) VALUES (%s)' % (','.join(cols),','.join(vals)))
        
    def dbm_columns(self):
        return self.columns
        
    OPENMETEO_OBS = {
        # Open-Meteo name: DWD-MOSMIX name
        'temperature_2m':'TTT',
        'relativehumidity_2m':'RHEL',
        'dewpoint_2m':'Td',
        'pressure_msl':'PPPP',
        'cloudcover':'N',
        'cloudcover_low':'Nl',
        'cloudcover_mid':'Nm',
        'cloudcover_high':'Nh',
        'windspeed_10m':'FF',
        'winddirection_10m':'DD',
        'windgusts_10m':'FX1',
        'weathercode':'ww',
        'visibility':'VV',
        'precipitation':'RR1c'
    }
    
    OPENMETEO_WEATHERMODELS = {
        # option: (country, weather service, model, URL directory)
        'dwd-icon':('DE','DWD','ICON','dwd-icon'), # without visibility
        'gfs':('US','NOAA','GFS','gfs'),
        'meteofrance':('FR','MeteoFrance','Arpege+Arome','meteofrance'),
        'ecmwf':('EU','ECMWF','open IFS','ecmwf'),
        'jma':('JP','JMA','GSM+MSM','jma'),
        'metno':('NO','MET Norway','Nordic','metno'),
        'gem':('CA','MSC-CMC','GEM+HRDPS','gem'),
        'ecmwf_ifs04':('EU','ECMWF','IFS','forecast'),
        'metno_nordic':('NO','MET Norway','Nordic','forecast'),
        'icon_seamless':('DE','DWD','ICON Seamless','forecast'),
        'icon_global':('DE','DWD','ICON Global','forecast'),
        'icon_eu':('DE','DWD','ICON EU','forecast'),
        'icon_d2':('DE','DWD','ICON D2','forecast'),
        'gfs_seamless':('US','NOAA','GFS Seamless','forecast'),
        'gfs_global':('US','NOAA','GFS Global','forecast'),
        'gfs_hrrr':('US','NOAA','GFS HRRR','forecast'),
        'gem_seamless':('CA','MSC-CMC','GEM','forecast'),
        'gem_global':('CA','MSC-CMC','GEM','forecast'),
        'gem_regional':('CA','MSC-CMC','GEM','forecast'),
        'gem_hrdps_continental':('CA','MSC-CMC','GEM-HRDPS','forecast')
    }

    def download_openmeteo(self, lat, lon, model):
        if isinstance(model,list):
            models = model
            dir = 'forecast'
            modelsopt = '&models='+','.join(models)
        else:
            models = [model]
            dir = DwdMosmix.OPENMETEO_WEATHERMODELS[model][3]
            if dir=='forecast':
                modelsopt = '&models='+model
            else:
                modelsopt = ''
        #models = ['icon_eu'] # icon_eu,icon_d2
        #vars = 'temperature_2m,relativehumidity_2m,dewpoint_2m'
        if 'ecmwf' in models:
            excludes = ('relativehumidity_2m','dewpoint_2m','windgusts_10m','visibility')
        elif dir=='forecast':
            excludes = list()
        else:
            excludes = ('visibility',)
        vars = ','.join([x for x in DwdMosmix.OPENMETEO_OBS if x not in excludes])
        url = 'https://api.open-meteo.com/v1/%s?latitude=%s&longitude=%s&hourly=%s%s&timeformat=unixtime' % (dir,lat,lon,vars,modelsopt)

        headers={'User-Agent':'weewx-DWD'}
        try:
            reply = requests.get(url,headers=headers)
        except ConnectionError as e:
            if self.log_failure:
                logerr(e)
            return None
        
        if reply.status_code==200:
            if self.log_success or self.verbose:
                loginf('successfully downloaded %s' % reply.url)
            content = json.loads(reply.text)
        else:
            if self.log_failure or self.verbose:
                logerr('error downloading %s: %s %s' % (reply.url,reply.status_code,reply.reason))
            return None
        
        # TODO: use file time from HTTP header
        issuetime = time.time()
        issuetimeISO = time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(issuetime))
        
        geodata = self.geo(lat,lon)
        if not geodata: geodata = dict()
        town = geodata.get('town')
        if not town: town = '%s %s' % (lat,lon)
        
        modelname = []
        for x in models:
            y = DwdMosmix.OPENMETEO_WEATHERMODELS.get(x)
            if y:
                modelname.append(y[1]+' '+y[2])
            else:
                modelname.append(x)
        
        mmos = {
            'Issuer':'Open-Meteo',
            'ProductID':'Open-Meteo',
            'GeneratingProcess':'',
            'IssueTime': issuetime*1000,
            'IssueTimeISO': issuetimeISO,
            'ReferenceModel': {
                'name':','.join(modelname),
                'ReferenceTime': issuetime*1000,
                'ReferenceTimeISO': issuetimeISO,
            },
            'ForecastTimeSteps': [ts*1000 for ts in content['hourly']['time']],
            'ForecastTimeStepsISO': [time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(ts)) for ts in content['hourly']['time']],
            'DefaultUndefSign':'-',
            'Placemark': [
                {
                    'id':'openmeteo-%s-%s-%s' % (lat,lon,','.join(models)),
                    'description': town,
                    'Forecast': dict(),
                    'coordinates': [
                        content.get('longitude'),
                        content.get('latitude'),
                        content.get('elevation')
                    ]
                }
            ]
        }
        
        for obs,val in content['hourly'].items():
            #val = content['hourly'][obs]
            if obs!='time':
                # TODO: convert 
                for model in DwdMosmix.OPENMETEO_WEATHERMODELS:
                    if obs.endswith(model):
                        obs = obs[0:-len(model)-1]
                        break;
                else:
                    model = None
                mobs = DwdMosmix.OPENMETEO_OBS.get(obs,obs)
                if model:
                    mobs += '_'+model
                mmos['Placemark'][0]['Forecast'][mobs] = val
        
        # TODO: klären, was N und Neff ist
        if 'N' in mmos['Placemark'][0]['Forecast']:
            mmos['Placemark'][0]['Forecast']['Neff'] = mmos['Placemark'][0]['Forecast']['N']
                
        return mmos
    
    
    @staticmethod
    def list_openmeteo_models():
        s = ('option          | country | weather service          | model name    \n'+
             '----------------|---------|--------------------------|---------------\n')
        for i in DwdMosmix.OPENMETEO_WEATHERMODELS:
            model =  DwdMosmix.OPENMETEO_WEATHERMODELS[i]
            s += '%-15s | %-7s | %-24s | %s\n' % (
                i,
                model[0],
                model[1],
                model[2])
        return s
    

if __name__ == "__main__":

    usage = None

    epilog = """Station list:
https://www.dwd.de/DE/leistungen/met_verfahren_mosmix/mosmix_stationskatalog.cfg?view=nasPublication&nn=16102
"""
    
    # Create a command line parser:
    parser = optparse.OptionParser(usage=usage, epilog=epilog)

    # options
    parser.add_option("--config", dest="config_path", type=str,
                      metavar="CONFIG_FILE",
                      default=None,
                      help="Use configuration file CONFIG_FILE.")
    parser.add_option("--weewx", action="store_true",
                      help="Read config from weewx.conf.")
    parser.add_option("--orientation", type=str, metavar="H,V",
                      help="HTML table orientation horizontal, vertial, or both")
    parser.add_option("--icon-set", dest="iconset", type=str, metavar="SET",
                      help="icon set to use, default is 'belchertown', possible values are 'dwd', 'belchertown', and 'aeris'")
    parser.add_option("--lang", dest="lang", type=str,
                      metavar="ISO639",
                      default='de',
                      help="Forecast language. Default 'de'")
    parser.add_option("--aqi-source", dest="aqisource", type=str, metavar="PROVIDER",
                      default=None,
                      help="Provider for Belchertown AQI section")
    parser.add_option("--hide-placemark", dest="hideplacemark",
                      action="store_true",
                      default=None,
                      help="no placemark caption over forecast table")
    parser.add_option("--open-meteo", dest="openmeteo",
                      metavar="MODEL",
                      default=None,
                      help="get forecast from Open-Meteo")

    group = optparse.OptionGroup(parser,"Output and logging options")
    group.add_option("--dry-run", action="store_true",
                      help="Print what would happen but do not do it. Default is False.")
    group.add_option("--log-tags", action="store_true",
                      help="Log tags while parsing the KML file.")
    group.add_option("-v","--verbose", action="store_true",
                      help="Verbose output")
    parser.add_option_group(group)

    # commands
    group = optparse.OptionGroup(parser,"Commands")
    group.add_option("--print-icons-ww", action="store_true", dest="iconsww",
                     help="Print which icons are connected to which ww weather code")
    group.add_option("--html", action="store_true", dest="html",
                     help="Write HTML .inc file")
    group.add_option("--json", action="store_true", dest="json",
                     help="Write JSON file")
    group.add_option("--belchertown", action="store_true",
                     help="Write Belchertown style forecast file")
    group.add_option("--database", action="store_true",
                     help="Write database file")
    group.add_option("--print-uba", dest="uba", type=str,
                     metavar="CMD",
                     default=None,
                     help="download data from UBA")
    parser.add_option_group(group)
    
    # intervals
    group = optparse.OptionGroup(parser,"Intervals")
    group.add_option("--all", action="store_true",
                     help="Output all details in HTML")
    group.add_option("--hourly", action="store_true",
                     help="output hourly forecast")
    group.add_option("--daily", action="store_true",
                     help="output daily forecast (the default)")
    parser.add_option_group(group)

    (options, args) = parser.parse_args()

    if options.verbose is None:
       options.verbose = False

    if options.iconsww:
        DwdMosmix.print_icons_ww(options.iconset)
        sys.exit(0)
        
    if options.weewx:
        config_path = "/etc/weewx/weewx.conf"
    else:
        config_path = options.config_path

    if config_path:
        if options.verbose:
            print("Using configuration file %s" % config_path)
        config = configobj.ConfigObj(config_path)
    else:
        # test only
        print("Using test configuration")
        config = {
            'Station': {
                'latitude':49.632270,
                'longitude':12.056186,
                'altitude':[394,'meter']
            },
            'DatabaseTypes': {
                'SQLite': {
                    'SQLITE_ROOT':'.'
                }
            },
            'WeatherServices': {
                'path':'/home/weewx/public_html/data/dwd',
                'forecast':{
                    'icons':'/home/weewx/public_html/data/dwd/icons'}}}
    
    if len(args)>0:
        location = args[0]
        if not location: location = None
    else:
        location = 'Weiden'
    
    if 'WeatherServices' in config and 'forecast' in config['WeatherServices']:
        ws = 'WeatherServices'
    else:
        # deprecated
        ws = 'DeutscherWetterdienst'
    
    if options.orientation:
        config[ws]['forecast']['orientation'] = options.orientation
    if options.iconset:
        config[ws]['forecast']['icon_set'] = options.iconset
    if options.aqisource:
        if 'Belchertown' not in config['WeatherServices']:
            config['WeatherServices']['Belchertown'] = dict()
        config['WeatherServices']['Belchertown']['aqi_source'] = options.aqisource
    if options.hideplacemark is not None:
        config[ws]['forecast']['show_placemark'] = not options.hideplacemark

    dwd = DwdMosmix(config,options.verbose)

    if options.uba:
        zz = dwd.download_uba(options.uba,location,lang=options.lang)
        print(json.dumps(zz,indent=4,ensure_ascii=False))
        exit()

    if options.openmeteo is None:
        zz = dwd.download_kml(location,'l')
        mmos = dwd.process_kml(zz,options.log_tags)
    else:
        loc = location.split(',')
        lat = float(loc[0])
        lon = float(loc[1])
        om = options.openmeteo
        if isinstance(om,str) and ',' in om:
            om = om.split(',')
        mmos = dwd.download_openmeteo(lat,lon,om)
    #print(json.dumps(mmos,indent=4,ensure_ascii=False))
    if not mmos:
        print('no data')
    
    output = []
    if options.all: output.append('all')
    if options.hourly: output.append('hourly')
    if options.belchertown: output.append('belchertown')
    if options.database: output.append('database')
    if options.daily or len(output)==0: output.append('daily')
    
    if options.html: output.append('html')
    if options.json: output.append('json')
    if not options.html and not options.json and not options.belchertown and not options.database:
        output.append('html')
        if options.daily:
            output.append('json')
    
    dwd.forecast_all(mmos,output,options.dry_run,lang=options.lang)