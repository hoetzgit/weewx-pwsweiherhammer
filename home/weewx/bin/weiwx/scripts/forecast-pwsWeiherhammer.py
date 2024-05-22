#!/usr/bin/python3
# Wettervorhersage
# Copyright (C) 2022 Johanna Roedenbeck
# licensed under the terms of the General Public License (GPL) v3
# https://github.com/roe-dl/weewx-DWD/blob/master/usr/local/bin/dwd-mosmix

# nicht aktueller Stand von dwd-mosmix temporär zum Testen mit einigen API calls ergänzt

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
from datetime import timezone, timedelta

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
DWD_WEATHER_CODE_LIST = [
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

WEATHERBIT_WEATHER_CODE_LIST = [
    (200,'Gewitter mit leichtem Regen','Thunderstorm with light rain',1,'thunderstorm.png','27.png','tstorm',':L:T'),
    (201,'Gewitter mit Regen','Thunderstorm with rain',2,'thunderstorm.png','27.png','tstorm','::T'),
    (202,'Geitter mit starkem Regen','Thunderstorm with heavy rain',3,'thunderstorm.png','28.png','tstorm',':H:T'),
    (230,'Gewitter mit leichtem Nieselregen','Thunderstorm with light drizzle',4,'thunderstorm.png','27.png','tstorm',':L:T'),
    (231,'Gewitter mit Nieselregen','Thunderstorm with drizzle',5,'thunderstorm.png','27.png','tstorm','::T'),
    (232,'Gewitter mit starkem Nieselregen','Thunderstorm with heavy drizzle',6,'thunderstorm.png','28.png','tstorm',':H:T'),
    (233,'Gewitter mit Hagel','Thunderstorm with Hail',7,'thunderstorm.png','30.png','tstorm',':H:T'),
    (300,'leichter Nieselregen','Light Drizzle',8,'drizzle.png','7.png','drizzle',':L:L'),
    (301,'Nieselregen','Drizzle',9,'drizzle.png','8.png','drizzle','::L'),
    (302,'starker Nieselregen','Heavy Drizzle',10,'drizzle.png','9.png','drizzle',':H:L'),
    (500,'leichter Regen','Light Rain',11,'rain.png','7.png','rain',':L:R'),
    (501,'mäßiger Regen','Moderate Rain',12,'rain.png','8.png','rain','::R'),
    (502,'starker Regen','Heavy Rain',13,'rain.png','9.png','rain',':H:R'),
    (511,'gefrierender Regen','Freezing rain',14,'sleet.png','67.png','freezingrain','::ZR'),
    (520,'leichte Regenschauer','Light shower rain',15,'rain.png','80.png','showers',':L:RW'),
    (521,'Regenschauer','Shower rain',16,'rain.png','80.png','showers','::RW'),
    (522,'starke Regenschauer','Heavy shower rain',17,'rain.png','82.png','showers',':H:RW'),
    (600,'leichter Schneefall','Light snow',18,'snow.png','14.png','snow',':L:S'),
    (601,'Schneefall','Snow',19,'snow.png','15.png','snow','::S'),
    (602,'starker Schneefall','Heavy Snow',20,'snow.png','16.png','snow',':H:S'),
    (610,'Regen-/Schneemix','Mix snow/rain',21,'sleet.png','13.png','rainandsnow','::WM'),
    (611,'Schneeregen','Sleet',22,'sleet.png','12.png','rainandsnow','::RS'),
    (612,'starker Schneeregen','Heavy sleet',23,'sleet.png','13.png','rainandsnow',':H:RS'),
    (621,'Schneeschauer','Snow shower',24,'sleet.png','85.png','snowshowers','::SW'),
    (622,'starke Schneeschauer','Heavy snow shower',25,'snow.png','86.png','snowshowers',':H:SW'),
    (623,'Wirbel','Flurries',26,'snow.png','14.png','flurries','::SW'),
    (700,'Dunst','Mist',27,'fog.png','40.png','fog','::BR'),
    (711,'Rauch','Smoke',28,'fog.png','40.png','smoke','::K'),
    (721,'Trübe','Haze',29,'fog.png','40.png','fog','::H'),
    (731,'Sand/dust','Sand/dust',30,'fog.png','40.png','dust','::BN'),
    (741,'Nebel','Fog',31,'fog.png','40.png','fog','::F'),
    (751,'gefrierender Nebel','Freezing Fog',32,'fog.png','48.png','drizzlef','::ZF'),
    (4,'bedeckt','Overcast clouds',33,None,None,None,None),     #804
    (3,'bewölkt','Broken clouds',34,None,None,None,None), #803
    (2,'wolkig','Scattered clouds',35,None,None,None,None),    #802
    (1,'heiter','Few clouds',36,None,None,None,None),   #801
    (0,'wolkenlos','Clear sky',37,None,None,None,None),     #800
    (900,'unbekanntes Niederschlag','Unknown Precipitation',38,'unknown.png','9.png','rain','::R')
]

OWM_WEATHER_CODE_LIST = [
    (200,'Gewitter mit leichtem Regen','thunderstorm with light rain',1,'thunderstorm.png','27.png','tstorm',':L:T'),
    (201,'Gewitter mit Regen','thunderstorm with rain',2,'thunderstorm.png','27.png','tstorm','::T'),
    (202,'Geitter mit starkem Regen','thunderstorm with heavy rain',3,'thunderstorm.png','28.png','tstorm',':H:T'),
    (210,'leichtes Gewitter','light thunderstorm',4,'thunderstorm.png','26.png','tstorm',':L:T'),
    (211,'Gewitter','thunderstorm',5,'thunderstorm.png','26.png','tstorm','::T'),
    (212,'starkes Gewitter','heavy thunderstorm',6,'thunderstorm.png','26.png','tstorm',':H:T'),
    (221,'vereinzelne Gewitter','ragged thunderstorm',7,'thunderstorm.png','26.png','tstorm','SC::T'),
    (230,'Gewitter mit leichtem Nieselregen','thunderstorm with light drizzle',8,'thunderstorm.png','28.png','tstorm',':H:T'),
    (231,'Gewitter mit Nieselregen','thunderstorm with drizzle',9,'thunderstorm.png','27.png','tstorm','::T'),
    (232,'Gewitter mit starkem Nieselregen','thunderstorm with heavy drizzle',10,'thunderstorm.png','28.png','tstorm',':H:T'),
    (300,'leichter Nieselregen','light intensity drizzle',11,'drizzle.png','7.png','drizzle',':L:L'),
    (301,'Nieselregen','drizzle',12,'drizzle.png','8.png','drizzle','::L'),
    (302,'starker Nieselregen','heavy intensity drizzle',13,'drizzle.png','9.png','drizzle',':H:L'),
    (310,'leichter Nieselregen','light intensity drizzle rain',14,'drizzle.png','7.png','drizzle',':L:L'),
    (311,'Nieselregen','drizzle rain',15,'drizzle.png','8.png','drizzle','::L'),
    (312,'starker Nieselregen','heavy intensity drizzle rain',16,'drizzle.png','9.png','drizzle',':H:L'),
    (500,'leichter Regen','light Rain',17,'rain.png','7.png','rain',':L:R'),
    (501,'mäßiger Regen','moderate rain',18,'rain.png','8.png','rain','::R'),
    (502,'starker Regen','heavy intensity rain',19,'rain.png','9.png','rain',':H:R'),
    (503,'sehr starker Regen','very heavy rain',20,'rain.png','9.png','rain',':VH:R'),
    (504,'extrem starker Regen','extreme rain',21,'rain.png','9.png','rain',':VH:R'),
    (511,'gefrierender Regen','freezing rain',22,'sleet.png','67.png','freezingrain','::ZR'),
    (520,'leichte Regenschauer','light intensity shower rain',23,'rain.png','80.png','showers','SC:L:RW'),
    (521,'Regenschauer','shower rain',24,'rain.png','80.png','showers','SC::RW'),
    (522,'starke Regenschauer','heavy shower rain and drizzle',25,'rain.png','82.png','showers','SC:H:RW'),
    (531,'vereinzelte Regenschauer','ragged shower rain',26,'rain.png','80.png','showers','SC::RW'),
    (600,'leichter Schneefall','light snow',27,'snow.png','14.png','snow',':L:S'),
    (601,'Schneefall','snow',28,'snow.png','15.png','snow','::S'),
    (602,'starker Schneefall','heavy Snow',29,'snow.png','16.png','snow',':H:S'),
    (611,'Schneeregen','sleet',30,'sleet.png','12.png','rainandsnow','::RS'),
    (612,'leichte Schneeregenschauer','light shower sleet',31,'sleet.png','12.png','rainandsnow','SC:L:RS'),
    (613,'Schneeregenschauer','shower sleet',32,'sleet.png','12.png','rainandsnow','SC::RS'),
    (615,'leichter Regen-/Schneemix','light rain and snow',33,'sleet.png','13.png','rainandsnow',':L:WM'),
    (616,'Regen-/Schneemix','rain and snow',34,'sleet.png','13.png','rainandsnow','::WM'),
    (620,'leichte Schneeschauer','light shower snow',35,'sleet.png','85.png','snowshowers',':L:SW'),
    (621,'Schneeschauer','shower snow',36,'sleet.png','85.png','snowshowers','::SW'),
    (622,'starke Schneeschauer','heavy snow shower',37,'snow.png','86.png','snowshowers',':H:SW'),
    (701,'Dunst','mist',38,'fog.png','40.png','fog','::BR'),
    (711,'Rauch','smoke',39,'fog.png','40.png','smoke','::K'),
    (721,'Trübe','haze',40,'fog.png','40.png','fog','::H'),
    (731,'Sand/dust','sand/ dust whirls',41,'fog.png','40.png','dust','::BN'),
    (741,'Nebel','fog',42,'fog.png','40.png','fog','::F'),
    (751,'Sand','sand',43,'fog.png','40.png','dust','::BN'),
    (761,'Staub','dust',44,'fog.png','40.png','dust','::BD'),
    (762,'Vulkan Asche','dust',45,'fog.png','40.png','dust','::VA'),
    (771,'Sturmböen','squalls',46,'wind.png','18.png','flurriesw','::BD'),
    (781,'Tornado','tornado',47,'tornado.png','18.png','flurriesw','::BD'),
    (4,'bedeckt','overcast clouds',52,None,None,None,None),     #804
    (3,'bewölkt','broken clouds',51,None,None,None,None), #803
    (2,'wolkig','scattered clouds',50,None,None,None,None),    #802
    (1,'heiter','few clouds',49,None,None,None,None),   #801
    (0,'wolkenlos','clear sky',48,None,None,None,None),     #800
]

BRIGHTSKY_WEATHER_CODE_LIST = [
    (900,'Gewitter','thunderstorm',1,'thunderstorm.png','26.png','tstorm','::T'),
    (600,'Hagel','hail',2,'hail.png','13.png','freezingrain','::EIN'),
    (500,'Schneefall','snow',3,'snow.png','16.png','snow','::S'),
    (400,'Schneeregen/Graupel','sleet',4,'sleet.png','13.png','sleet','::IP'),
    (300,'Regen','rain',5,'rain.png','27.png','rain','::R'),
    (200,'Wind','wind',6,'wind.png','18.png','wind','::BD'),
    (100,'Nebel','fog',8,'fog.png','27.png','fog','::F'),
    (4,'bedeckt','Overcast clouds',8,None,None,None,None),
    (2,'bewölkt','Partly cloudy',9,None,None,None,None),
    (0,'wolkenlos','Clear sky',10,None,None,None,None),
]

# condition - dry┃fog┃rain┃sleet┃snow┃hail┃thunderstorm┃
# icon - clear-day┃clear-night┃partly-cloudy-day┃partly-cloudy-night┃cloudy┃fog┃wind┃rain┃sleet┃snow┃hail┃thunderstorm┃
BRIGHSKY_WEATHER_CODE_MAPPING = {
    'thunderstorm':900,
    'hail':600,
    'snow':500,
    'sleet':400,
    'rain':300,
    'wind':200,
    'fog':100,
    'dry-cloudy':4,
    'dry-partly-cloudy-day':2,
    'dry-partly-cloudy-night':2,
    'dry-clear-day':0,
    'dry-clear-night':0,
}

# IDX: 0=belchertown,1=dwd,2=aeris,3=Aeris Cloud code,4=Aeris Weather Code
CLOUDCOVER_CODE_LIST = [
    ('clear','0-8.png','clear','CL','::CL',0),
    ('mostly-clear','2-8.png','fair','FW','::FW',1),
    ('partly-cloudy','5-8.png','pcloudy','SC','::SC',2),
    ('mostly-cloudy','5-8.png','mcloudy','BK','::BK',3),
    ('cloudy','8-8.png','cloudy','OV','::OV',4),
]

def weather_decode(weathercode,cloudcover,night,weatherprovider='dwd'):
    """ get icon and description for the current weather """
    # If weathercode is within the list of xxx_WEATHER_CODE_LIST (which means
    # it is important over cloud coverage), get the data from that
    # list.
    WEATHERDATA_UNKNOWN = (9999,'unbekannt','unknown',0,'unknown.png',None,'na','::')
    if (weatherprovider=='dwd'):
        code_list = DWD_WEATHER_CODE_LIST
    elif (weatherprovider=='_brightsky'):
        code_list = BRIGHTSKY_WEATHER_CODE_LIST
        weathercode = BRIGHSKY_WEATHER_CODE_MAPPING[weathercode]
        weathercode = [weathercode] #compatible to DWD ww code
    elif (weatherprovider=='owm'):
        code_list = OWM_WEATHER_CODE_LIST
        if (weathercode >= 800) and (weathercode < 900):
            weathercode = weathercode - 800
        weathercode = [weathercode] #compatible to DWD ww code
    elif (weatherprovider=='weatherbit'):
        code_list = WEATHERBIT_WEATHER_CODE_LIST
        if (weathercode >= 800) and (weathercode < 900):
            weathercode = weathercode - 800
        weathercode = [weathercode] #compatible to DWD ww code
    else:
        return WEATHERDATA_UNKNOWN

    #print("searching wether_code %s provider %s" % (weathercode, weatherprovider))
    for ii in code_list:
        if ii[0] in weathercode:
            weatherdata = ii
            break
    else:
        weatherdata = WEATHERDATA_UNKNOWN
    # Otherwise use cloud coverage
    # see aerisweather for percentage values
    # https://www.aerisweather.com/support/docs/api/reference/weather-codes/
    if weatherdata[0]>=0 and weatherdata[0]<=4:
        ccdata = cloudcover_decode(cloudcover,weatherprovider)
        #belchertown cloudcover icons day / night ?
        ccdata = list(ccdata)
        ccdata[0] = ccdata[0] + ('-night' if night else '-day') + '.png'
        #weatherdata = (weatherdata[0],weatherdata[1],weatherdata[2],weatherdata[3],ccdata[0],ccdata[1],ccdata[2],ccdata[4])
        weatherdata = (ccdata[5],weatherdata[1],weatherdata[2],weatherdata[3],ccdata[0],ccdata[1],ccdata[2],ccdata[4])
    return weatherdata

def cloudcover_decode(cloudcover, weatherprovider='dwd'):
    if weatherprovider == 'dwd':
    # https://www.dwd.de/DE/service/lexikon/Functions/glossar.html?lv2=100932&lv3=101016
        if cloudcover<12.5:
            ccdata = CLOUDCOVER_CODE_LIST[0]
        elif cloudcover<=37.5:
            ccdata = CLOUDCOVER_CODE_LIST[1]
        elif cloudcover<=75.0:
            ccdata = CLOUDCOVER_CODE_LIST[2]
        elif cloudcover<=87.5:
            ccdata = CLOUDCOVER_CODE_LIST[3]
        else:
            ccdata = CLOUDCOVER_CODE_LIST[4]

    # see aerisweather for percentage values
    # https://www.aerisweather.com/support/docs/api/reference/weather-codes/
    else:
        if cloudcover<=7:
            ccdata = CLOUDCOVER_CODE_LIST[0]
        elif cloudcover<=32:
            ccdata = CLOUDCOVER_CODE_LIST[1]
        elif cloudcover<=70:
            ccdata = CLOUDCOVER_CODE_LIST[2]
        elif cloudcover<=95:
            ccdata = CLOUDCOVER_CODE_LIST[3]
        else:
            ccdata = CLOUDCOVER_CODE_LIST[4]
    #print("Provider: <%s> Cover: <%s> Code: <%s>" % (weatherprovider,str(cloudcover),ccdata[3]))
    return ccdata

# week day names
WEEKDAY = {
    'de':['Mo','Di','Mi','Do','Fr','Sa','So'],
    'en':['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],
    'fr':['lu','ma','me','je','ve','sa','di'],
    'it':['lun.','mar.','mer.','gio.','ven.','sab.','dom.'],
    'cz':['Po','Út','St','Čt','Pá','So','Ne']
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
    except Exception:
        print("Error humidity calculation, TEMP=%f, DEWPT=%f" % (temperature,dewpoint))
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

AERIS_VALID_ALLSTATIONS = {
    'PWS_IWEIHE1':'pws_iweihe1',
    'ETIC':'metar',
    'MID_F0887':'f0887',
    'PWS_001D0A00D16B':'pws_001d0a00d16b'
}


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
        
class ForecastPWS(object):

    def __init__(self, config_dict, verbose=False):
        # target path
        self.target_path = config_dict['forecast-pwsWeiherhammer']['path']
        # forecast config data
        forecast_dict = config_dict['forecast-pwsWeiherhammer']['forecast']
        # database config data
        database_dict = config_dict['forecast-pwsWeiherhammer']['database']
        # weather icons
        self.icon_pth = forecast_dict['icons']
        # station-specific configuration
        self.stations_dict = forecast_dict.get('stations',{})
        # forecast Waldbrandgefahrenindex
        wbx_dict = config_dict['forecast-pwsWeiherhammer']['forecast-wbx']
        self.wbx_stations = wbx_dict.get('stations',None)
        self.wbx_input_file = wbx_dict.get('input','forecast-wbx-input-not-defined.json')
        self.wbx_output_file = wbx_dict.get('output','forecast-wbx-onput-not-defined.inc')
        self.wbx_radius_km = wbx_dict.get('radius_km', None)
        if self.wbx_radius_km == '':
            self.wbx_radius_km = None
        if self.wbx_radius_km is not None:
            self.wbx_radius_km = int(self.wbx_radius_km)
        # HTML config
        self.show_obs_symbols = tobool(forecast_dict.get('show_obs_symbols',True))
        self.show_obs_description = tobool(forecast_dict.get('show_obs_description',False))
        self.show_obs_units = tobool(forecast_dict.get('show_obs_units',False))
        self.show_placemark = tobool(forecast_dict.get('show_placemark',False))
        self.html_max_days = int(forecast_dict.get('max_days',None))
        # database config
        self.database_max_days = int(database_dict.get('max_days',None))
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
        self.log_success = tobool(forecast_dict.get('log_success',config_dict['forecast-pwsWeiherhammer'].get('log_success',config_dict.get('log_success',False))))
        self.log_failure = tobool(forecast_dict.get('log_failure',config_dict['forecast-pwsWeiherhammer'].get('log_failure',config_dict.get('log_failure',False))))
        if (int(config_dict.get('debug',0))>0) or verbose:
            self.log_success = True
            self.log_failure = True
            # self.verbose = True
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
            belchertown_dict = config_dict['forecast-pwsWeiherhammer'].get('Belchertown',{})
            belchertown_section = config_dict['StdReport'][belchertown_dict['section']]
            if 'HTML_ROOT' in belchertown_section:
                self.belchertown_html_root = os.path.join(
                    config_dict['WEEWX_ROOT'],
                    belchertown_section['HTML_ROOT'])
            else:
                self.belchertown_html_root = os.path.join(
                    config_dict['WEEWX_ROOT'],
                    config_dict['StdReport']['HTML_ROOT'])
            self.belchertown_forecast = belchertown_dict['forecast']
            self.belchertown_warning = belchertown_dict['warnings']
            self.belchertown_include_advance_warning = int(belchertown_dict.get('include_advance_warnings',0))
            self.belchertown_aqi_source = str(belchertown_dict.get('aqi_source',None)).lower()
            self.belchertown_compasslang = str(belchertown_dict.get('compass_lang','en')).lower()
            self.belchertown_max_days = int(belchertown_dict.get('max_days',7))
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
            self.aeris_api_id = ew.get('aeris_api_id',es.get('aeris_api_id', None))
            self.aeris_api_secret = ew.get('aeris_api_secret',es.get('aeris_api_secret', None))
            self.current_provider = ew.get('current_provider',es.get('current_provider','dwd_mosmix'))
            self.current_provider_list = ew.get('current_provider_list',es.get('current_provider_list', self.current_provider))
            self.weatherbit_api_key = ew.get('weatherbit_api_key',es.get('weatherbit_api_key', None))
            self.owm_api_key = ew.get('owm_api_key',es.get('owm_api_key', None))
        except LookupError:
            belchertown_section = {}
            self.belchertown_html_root = None
            self.belchertown_warning = None
            self.belchertown_forecast = None
            self.aeris_api_id = None
            self.aeris_api_secret = None
            self.current_provider_list = 'dwd_mosmix'
            self.weatherbit_api_key = None
            self.owm_api_key = None
        # Database
        try:
            self.SQLITE_ROOT = config_dict['DatabaseTypes']['SQLite']['SQLITE_ROOT']
        except LookupError:
            self.SQLITE_ROOT = None
        self.connection = None
        # Log config
        if __name__ == "__main__" and verbose:
            print('-- configuration data ----------------------------------')
            print('log success                : ',self.log_success)
            print('log failure                : ',self.log_failure)
            print('target path                : ',self.target_path)
            print('horiz. tab                 : ',self.horizontal_table)
            print('vertical tab               : ',self.vertical_table)
            print('icon set                   : ',self.iconset)
            print('station location           : ','lat',self.latitude,'lon',self.longitude,'alt',self.altitude)
            print('aeris api id               : ',self.aeris_api_id)
            print('aeris api secret           : ',self.aeris_api_secret)
            print('SQLITE_ROOT                : ',self.SQLITE_ROOT)
            print('current provider list      : ',self.current_provider_list)
            print('weatherbit api key         : ',self.weatherbit_api_key)
            print('owm api key                : ',self.owm_api_key)
            print('forecast wbx stations      : ',self.wbx_stations)
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
                djd = ForecastPWS.timestamp_to_djd(ts)
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

    def get_station_location(self):
        """ determine the location of the station """
        if has_pyephem:
            try:
                location = ephem.Observer()
                location.lat = self.latitude*0.017453292519943
                location.lon = self.longitude*0.017453292519943
                location.elevation = self.altitude
            except Exception as e:
                logerr('Observer: %s' % e)
        else:
            location = None
        return location
        
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

    def write_html(self, placemark, timesteps, daynights, issue, obstypes, dryrun, range=None, lang='de'):
        """ create HTML hourly """
        #timesteps = mos['ForecastTimeSteps']
        try:
            start_day = range[0]
            end_day = range[1]
            count = 9999
            #ho Test analog Belchertown
            if (self.html_max_days) is not None:
                end_day = self.html_max_days
        except TypeError:
            start_day = 0
            end_day = 9999
            count = range if range else 9999
        now = time.time()*1000
        # config
        symbols = self.show_obs_symbols and obstypes
        desc = self.show_obs_description or not obstypes
        units = self.show_obs_units
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
                s += '<tr>'
                if symbols: s += '<td></td>'
                if desc: s += '<td></td>'
                if units: s += '<td></td>'
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
                s += '<tr class="icons">'
                if symbols: s += '<td></td>'
                if desc: s += '<td></td>'
                if units: s += '<td></td>'
                for idx,ii in enumerate(timesteps):
                    if idx<start_ct: continue
                    if idx>=count+start_ct: break
                    #night = self.is_night(location,ii*0.001)
                    night = daynights[idx]
                    wwcode = weather_decode([placemark['Forecast']['ww'][idx]],placemark['Forecast']['Neff'][idx],night)
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
                    if symbols: s += '<td style="text-align:left%s" title="%s">%s</td>' % (color,self.OBS_LABEL.get(ii,('',ii,''))[1],self.OBS_LABEL.get(ii,(ii,'',''))[0])
                    # observation type description column
                    if desc:
                        if obstypes:
                            s += '<td>%s</td>' % self.OBS_LABEL.get(ii,('',ii,''))[1]
                        else:
                            s += '<td>%s</td>' % ii
                    # measuring unit column
                    if units:
                        color = ' style="color:%s"' % prec_color if prec_color else ''
                        s += '<td%s>%s</td>' % (color,self.OBS_LABEL.get(ii,(ii,'',''))[2])
                    # values columns
                    for idx,jj in enumerate(placemark['Forecast'][ii]):
                        if idx<start_ct: continue
                        if idx>=count+start_ct: break
                        try:
                            color = ' style="color:%s"' % prec_color if prec_color else ''
                            if ii=='TTT': color = ' style="color:%s"' % ForecastPWS._temp_color(jj)
                            dp = 1 if ii[0]=='T' or (ii in ['RR1c','RRL1c','RRS1c','RR3c','RR6c']) else 0
                            if ii=='DD':
                                s += '<td><i class="wi wi-direction-down" style="transform:rotate(%sdeg);font-size:150%%" title="%s"></i></td>' % (jj,compass(jj,lang))
                                #s += '<td><i class="wi wi-wind-direction" style="transform:rotate(%sdeg);font-size:150%%"></i></td>' % ((jj+180)%360)
                            else:
                                s += '<td%s>%.*f</td>' % (color,dp,jj)
                        except Exception:
                            s += '<td>%s</td>' % jj
                    s += '</tr>\n'
                fn = placemark['id']
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
                    wwcode = weather_decode([placemark['Forecast']['ww'][idx]],placemark['Forecast']['Neff'][idx],night)
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
                        s += '<td style="color:%s">%s<span style="font-size:50%%"> °C</span></td>' % (ForecastPWS._temp_color(temp),temp_s)
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
                # Copyright notice
                s += '<p style="font-size:65%%;display:inline">herausgegeben vom <a href="https://www.dwd.de" target="_blank">DWD</a> am %s</p>\n' % time.strftime('%d.%m.%Y %H:%M',time.localtime(issue['IssueTime']/1000.0))
                s += '<p style="font-size:65%%;display:inline">| Vorhersage erstellt am %s</p>\n' % time.strftime('%d.%m.%Y %H:%M')
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
                s += '<tr>'
                if symbols: s += '<td></td>'
                if desc: s += '<td></td>'
                if units: s += '<td></td>'
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
                    prec_color = '#7cb5ec' if (ii in ['RR1c','Rd00','Rd01','Rd05','Rd10'] or ii in POP) else None
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
                    if units: s += '<td'+color+'>'+self.OBS_LABEL.get(ii,('',ii,''))[2]+'</td>'
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
                                if ii[0:3]=='TTT': color = ' style="color:%s"' % ForecastPWS._temp_color(days[day][ii])
                                if prec_color: color = ' style="color:%s"' % prec_color
                                if ii in POP:
                                    val = ('%.*f' % (dp, days[day].get('Rd10',days[day].get('Rh10',days[day].get('R610',days[day].get('R101',None)))))).replace('.',',')
                                else:
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
                    if units: s += '<td>kWh</td>'
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
                        color = ' style="color:%s"' % ForecastPWS._temp_color(days[day]['TTTmax'])
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
                        color = ' style="color:%s"' % ForecastPWS._temp_color(days[day]['TTTmin'])
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
            s += '<p style="font-size:65%%;display:inline">herausgegeben vom <a href="https://www.dwd.de" target="_blank">DWD</a> am %s</p>\n' % time.strftime('%d.%m.%Y %H:%M',time.localtime(issue['IssueTime']/1000.0))
            s += '<p style="font-size:65%%;display:inline">| Vorhersage erstellt am %s</p>\n' % time.strftime('%d.%m.%Y %H:%M')
            fn = os.path.join(self.target_path,'forecast-'+placemark['id']+'.inc')
            if dryrun:
                print(s)
            else:
                with open(fn,"w") as file:
                    file.write(s)
    
    def dump(self, placemark, days, recs3hr, timesteps, daynights, issue, dryrun, lang='de'):
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
                'Forecast3hr':recs3hr,
                'ForecastHourly':hours}
            json.dump(x,file,indent=4,ensure_ascii=False)
            

    def belchertown(self, placemark, days, recs3h, timesteps, daynights, issue, dryrun):
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
            geodata = ForecastPWS.geo(geo[1],geo[0])
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
        forecast_dwd = {'timestamp':int(now)}
        #ho Test mit idxold, ob nicht der Wert der aktuellen Stunde für "current" besser ist, als der Wert der nächsten Stunde
        # idxold = None
        # for idx,ii in enumerate(timesteps):
            # if now<=ii*0.001:
                # if self.verbose:
                    # loginf("current OLD: now %s timestep %s" % (time.strftime('%H:%M:%S',time.localtime(now)),time.strftime('%H:%M:%S',time.localtime(timesteps[idx]*0.001))))
                # break
            # idxold = idx
        # #night = self.is_night(location,timesteps[idx]*0.001)
        # if idxold is not None:
            # idx = idxold
        # if self.verbose:
            # loginf("current NEW: now %s timestep %s" % (time.strftime('%H:%M:%S',time.localtime(now)),time.strftime('%H:%M:%S',time.localtime(timesteps[idx]*0.001))))

        # wieder original
        for idx,ii in enumerate(timesteps):
            if now<=ii*0.001:
                if self.verbose:
                    loginf("now %s timestep %s" % (time.strftime('%H:%M:%S',time.localtime(now)),time.strftime('%H:%M:%S',time.localtime(timesteps[idx]*0.001))))
                break
        #night = self.is_night(location,timesteps[idx]*0.001)
 
        night = daynights[idx]
        wwcode = weather_decode([placemark['Forecast']['ww'][idx]],placemark['Forecast']['Neff'][idx],night)
        forecast_dwd['current'] = [{
            'success':True,
            'error':None,
            'source':'DWD MOSMIX',
            'response':[{
                'id':placemark['id'],
                'dataSource':issue['ReferenceModel']['name'],
                'loc':{
                    'long':geo[0],
                    'lat':geo[1]
                },
                'place':{
                    'name':placemark['description'],
                    'city':placemark['description'],
                    'state':geodata['state'] if geodata else '',
                    'country':geodata['country_code'] if geodata else ''
                },
                'profile':{
                    'tz':'Europe/Berlin',
                    'tzname':'CET',
                    'tzoffset':3600,
                    'isDST':False,
                    'elevM':geo[2]
                },
                'obTimestamp':int(issue['IssueTime']*0.001),
                'obDateTime':issue['IssueTimeISO'],
                'ob':{
                    'timestamp':int(timesteps[idx]*0.001),
                    'dateTimeISO':ForecastPWS.isoformat(timesteps[idx]*0.001),
                    'tempC':nround(placemark['Forecast']['TTT'][idx],1),
                    'dewpointC':nround(placemark['Forecast']['Td'][idx],1),
                    'humidity':nround(humidity(placemark['Forecast']['TTT'][idx],placemark['Forecast']['Td'][idx]),0),
                    'pressureMB':nround(placemark['Forecast']['PPPP'][idx]),
                    'windKPH':nround(placemark['Forecast']['FF'][idx]),
                    'windSpeedKPH':nround(placemark['Forecast']['FF'][idx]),
                    'windDir':compass(nround(placemark['Forecast']['DD'][idx]),self.belchertown_compasslang,False),
                    'windDirDEG':nround(placemark['Forecast']['DD'][idx]),
                    'visibilityKM':placemark['Forecast']['VV'][idx]*0.001,
                    'weather':wwcode[1],
                    'weatherCoded':wwcode[7],
                    'weatherPrimary':wwcode[1],
                    'weatherPrimaryCoded':wwcode[7],
                    'cloudsCoded':cloudcover_decode(placemark['Forecast']['N'][idx])[3],
                    'icon':wwcode[6]+('n' if night else '')+'.png',
                    'solradWM2':placemark['Forecast']['Rad1h'][idx],
                    'isDay':not night,
                    'sky':int(placemark['Forecast']['N'][idx]),
                    'ww':wwcode[0]
                },
                'raw':'',
                'relativeTo':{
                    'lat':self.latitude,
                    'long':self.longitude,
                    'distanceKM':nround(rel_dist_km,1),
                    'distanceMI':nround(rel_dist_mi,1)
                }
            }]
        }]
        belchertown_days = []
        for day in days:
            wwcode = weather_decode(days[day]['ww'],days[day]['Neffavg'],False)
            belchertown_days.append({
                'timestamp':days[day]['timestamp'],
                'validTime':ForecastPWS.isoformat(days[day]['timestamp']),
                'dateTimeISO':ForecastPWS.isoformat(days[day]['timestamp']),
                'maxTempC':nround(days[day]['TTTmax'],1),
                'minTempC':nround(days[day]['TTTmin'],1),
                'avgTempC':nround(days[day]['TTTavg'],1),
                'tempC':nround(days[day]['TTTavg'],1),
                'maxDewpointC':nround(days[day]['Tdmax'],1),
                'minDewpointC':nround(days[day]['Tdmin'],1),
                'avgDewpointC':nround(days[day]['Tdavg'],1),
                'dewpointC':nround(days[day]['Tdavg'],1),
                'humidity':nround(humidity(days[day]['TTTavg'],days[day]['Tdavg']),0),
                'pop':days[day].get('Rd10',days[day].get('Rh10',days[day].get('R610',days[day].get('R101',None)))),
                'precipMM':nround(days[day].get('RR1c'),1),
                'pressureMB':nround(days[day]['PPPPavg']),
                'windDir':compass(days[day]['DDavg'],self.belchertown_compasslang,False),
                'windDirDEG':nround(days[day]['DDavg']),
                'windSpeedKPH':nround(days[day]['FFavg']),
                'windGustKPH':nround(days[day]['FX1max']),
                'sky':nround(days[day]['Neffavg']),
                'cloudsCoded':cloudcover_decode(days[day]['Neffavg'])[3],
                'weather':wwcode[1],
                'weatherCoded':wwcode[7],
                'weatherPrimary':wwcode[1],
                'weatherPrimaryCoded':wwcode[7],
                'icon':wwcode[6]+'.png',
                'isDay':True,
                'ww':wwcode[0], #ho Debug
            })
            if len(belchertown_days)>=self.belchertown_max_days: break
        forecast_dwd['forecast_24hr'] = [{
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
                wwcode = weather_decode([rec['ww3']],rec['Neffavg'],rec['night'])
                hour = {
                    'timestamp':rec['timestamp'],
                    'validTime':ForecastPWS.isoformat(rec['timestamp']),
                    'dateTimeISO':ForecastPWS.isoformat(rec['timestamp']),
                    'maxTempC':rec['TTTmax'],
                    'minTempC':rec['TTTmin'],
                    'avgTempC':rec['TTTavg'],
                    'tempC':rec['TTT'],
                    'maxDewpointC':rec['Tdmax'],
                    'minDewpointC':rec['Tdmin'],
                    'avgDewpointC':rec['Tdavg'],
                    'dewpointC':rec['Td'],
                    'humidity':nround(humidity(rec['TTT'],rec['Td']),0),
                    'pop':rec['R101max'],
                    'pressureMB':rec['PPPPavg'],
                    'windDir':compass(rec['DDavg'],self.belchertown_compasslang,False),
                    'windDirDEG':rec['DDavg'],
                    'windSpeedKPH':rec['FFavg'],
                    'windSpeedMaxKPH':rec['FFmax'],
                    'windSpeedMinKPH':rec['FFmin'],
                    'windGustKPH':rec.get('FX3'),
                    'sky':int(rec['Neffavg']),
                    'cloudsCoded':cloudcover_decode(rec['Neffavg'])[3],
                    'weather':wwcode[1],
                    'weatherCoded':[],
                    'weatherPrimary':wwcode[1],
                    'weatherPrimaryCoded':wwcode[7],
                    'icon':wwcode[6]+('n' if night else '')+'.png',
                    'visibilityKM':rec['VVmin']/1000.0 if rec['VVmin'] is not None else None,
                    'isDay':not rec['night'],
                    'maxCoverage':'',
                    'ww':wwcode[0], #ho Debug
                    }
                belchertown_hours.append(hour)
            if len(belchertown_hours)>=8: break
        forecast_dwd['forecast_3hr'] = [{
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
            wwcode = weather_decode([placemark['Forecast']['ww'][idx]],placemark['Forecast']['Neff'][idx],night)
            hour = {
                'timestamp':int(ii*0.001),
                'validTime':ForecastPWS.isoformat(ii*0.001),
                'dateTimeISO':ForecastPWS.isoformat(ii*0.001),
                'maxTempC':placemark['Forecast']['TTT'][idx],
                'minTempC':placemark['Forecast']['TTT'][idx],
                'avgTempC':placemark['Forecast']['TTT'][idx],
                'tempC':placemark['Forecast']['TTT'][idx],
                'maxDewpointC':placemark['Forecast']['Td'][idx],
                'minDewpointC':placemark['Forecast']['Td'][idx],
                'avgDewpointC':placemark['Forecast']['Td'][idx],
                'dewpointC':placemark['Forecast']['Td'][idx],
                'humidity':nround(humidity(placemark['Forecast']['TTT'][idx],placemark['Forecast']['Td'][idx]),0),
                'pop':placemark['Forecast']['R101'][idx],
                'precipMM':placemark['Forecast']['RR1c'][idx],
                'pressureMB':placemark['Forecast']['PPPP'][idx],
                'windDir':compass(placemark['Forecast']['DD'][idx],self.belchertown_compasslang,False),
                'windDirDEG':placemark['Forecast']['DD'][idx],
                'windSpeedKPH':placemark['Forecast']['FF'][idx],
                'windGustKPH':placemark['Forecast']['FX1'][idx],
                'sky':int(placemark['Forecast']['Neff'][idx]),
                'cloudsCoded':cloudcover_decode(placemark['Forecast']['Neff'][idx])[3],
                'weather':wwcode[1],
                'weatherCoded':wwcode[7],
                'weatherPrimary':wwcode[1],
                'weatherPrimaryCoded':wwcode[7],
                'icon':wwcode[6]+('n' if night else '')+'.png',
                'visibilityKM':placemark['Forecast']['VV'][idx]*0.001,
                'solradWM2':placemark['Forecast']['Rad1h'][idx],
                'solradMinWM2':placemark['Forecast']['Rad1h'][idx],
                'solradMaxWM2':placemark['Forecast']['Rad1h'][idx],
                'isDay':not night,
                'ww':[placemark['Forecast']['ww'][idx]], #ho Debug
                }
            belchertown_hours.append(hour)
            if len(belchertown_hours)>=16: break
        forecast_dwd['forecast_1hr'] = [{
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
        forecast_dwd['alerts'] = [{
            'success':success,
            'error':None if success else {'code':str(err),'description':str(err)},
            'response':belchertown_alerts }]
        # AQI
        if self.belchertown_aqi_source=='aeris':
            try:
                if self.aeris_api_id and self.aeris_api_secret:
                    forecast_dwd['aqi'] = self.download_aeris('aqi')
                else:
                    raise Exception
            except Exception as e:
                if self.log_failure or self.verbose:
                    logerr(e)
                forecast_dwd['aqi'] = [{
                    'success':False,
                    'error':{'code':e.__name__,
                             'description':str(e)},
                    'response':[] }]
        elif self.belchertown_aqi_source[0:3]=='uba':
            try:
                forecast_dwd['aqi'] = self.download_uba('aqi',self.belchertown_aqi_source[3:])
            except Exception as e:
                if self.log_failure or self.verbose:
                    logerr(e)
                forecast_dwd['aqi'] = [{
                    'success':False,
                    'error':{'code':e.__name__,
                             'description':str(e)},
                    'response':[] }]
        else:
            forecast_dwd['aqi'] = [{
                'success':False,
                'error':{'code':'not_configured',
                         'description':'no AQI source configured'},
                'response':[] }]
        
        ###############################################
        #
        # final forecast result data
        #
        ###############################################

        # DWD_MOSMIX
        forecast_result = {'timestamp':int(now)}
        forecast_result['dwd_mosmix'] = forecast_dwd

        # Brightsky (no API Limit)
        #TODO: stale timer
        #TODO: forecast
        #TODO: alerts
        #TODO: aqi
        src = "Brightsky (DWD Daten)"
        if ('_brightsky' in self.current_provider_list):
            try:
                data = self.download_brightsky('current_weather', src)
                forecast_result['_brightsky'] = {
                    'timestamp':int(now),
                    'current': data
                }
            except Exception as e:
                if self.log_failure or self.verbose:
                   logerr(e)
                forecast_result['_brightsky'] = {
                    'timestamp':int(now),
                    'current':[{'success':False,'error':{'code':e.__name__,'description':str(e)},'source':src,'response':[]}],
                }
        else:
            forecast_result['_brightsky'] = {
                'timestamp':int(now),
                'current':[{'success':False,'error':{'code':'N/A','description':'_brightsky is not enabled'},'source':src,'response':[]}]
            }

        # Weatherbit.io (API Limit)
        #TODO: stale timer
        #TODO: forecast
        #TODO: alerts
        #TODO: aqi
        src = "Weatherbit"
        if ('weatherbit' in self.current_provider_list):
            data = self.download_weatherbit('current', src)
            try:
                forecast_result['weatherbit'] = {
                    'timestamp':int(now),
                    'current': data
                }
            except Exception as e:
                if self.log_failure or self.verbose:
                   logerr(e)
                forecast_result['weatherbit'] = {
                   'timestamp':int(now),
                   'current':[{'success':False,'error':{'code':e.__name__,'description':str(e)},'source':src,'response':[]}],
                }
        else:
            forecast_result['weatherbit'] = {
                'timestamp':int(now),
                'current':[{'success':False,'error':{'code':'N/A','description':'weatherbit is not enabled'},'source':src,'response':[]}]
            }

        # OpenWeatherMap (no API Limit)
        #TODO: stale timer
        #TODO: forecast
        #TODO: alerts
        #TODO: aqi
        src = "OpenWeatherMap"
        if ('owm' in self.current_provider_list):
            try:
                data = self.download_owm('weather', src)
                forecast_result['owm'] = {
                    'timestamp':int(now),
                    'current': data
                }
            except Exception as e:
                if self.log_failure or self.verbose:
                   logerr(e)
                forecast_result['owm'] = {
                   'timestamp':int(now),
                   'current':[{'success':False,'error':{'code':e.__name__,'description':str(e)},'source':src,'response':[]}],
                }
        else:
            forecast_result['owm'] = {
                'timestamp':int(now),
                'current':[{'success':False,'error':{'code':'N/A','description':'owm is not enabled'},'source':src,'response':[]}]
            }

        # AerisWeather "Metar ETIC" (API Limit)
        #TODO: stale timer
        #TODO: forecast
        #TODO: alerts
        #TODO: aqi
        src = "Vaisala Xweather (METAR ETIC)"
        if ('aeris_metar' in self.current_provider_list):
            try:
                data = self.download_aeris('aeris_metar', src)
                forecast_result['aeris_metar'] = {
                   'timestamp':int(now),
                   'current': data
                }
            except Exception as e:
                if self.log_failure or self.verbose:
                   logerr(e)
                forecast_result['aeris_metar'] = {
                   'timestamp':int(now),
                   'current':[{'success':False,'error':{'code':e.__name__,'description':str(e)},'source':src,'response':[]}],
                }
        else:
            forecast_result['aeris_metar'] = {
                'timestamp':int(now),
                'current':[{'success':False,'error':{'code':'N/A','description':'aeris_metar is not enabled'},'source':src,'response':[]}]
            }

        # AerisWeather "conditions" (API Limit)
        #TODO: stale timer
        #TODO: forecast
        #TODO: alerts
        #TODO: aqi
        src = "Vaisala Xweather (Mesonet F0887)"
        if ('aeris_mesonet' in self.current_provider_list):
            try:
                data = self.download_aeris('aeris_mesonet', src)
                forecast_result['aeris_mesonet'] = {
                   'timestamp':int(now),
                   'current': data
                }
            except Exception as e:
                if self.log_failure or self.verbose:
                   logerr(e)
                forecast_result['aeris_mesonet'] = {
                   'timestamp':int(now),
                   'current':[{'success':False,'error':{'code':e.__name__,'description':str(e)},'source':src,'response':[]}],
                }
        else:
            forecast_result['aeris_mesonet'] = {
                'timestamp':int(now),
                'current':[{'success':False,'error':{'code':'N/A','description':'aeris_mesonet is not enabled'},'source':src,'response':[]}]
            }


        if self.belchertown_html_root and self.belchertown_forecast and self.belchertown_forecast==placemark['id']:
            fn = os.path.join(self.belchertown_html_root,'json','forecast.json')
            fnt = os.path.join(self.belchertown_html_root,'json','forecast.json.tmp')
        else:
            fn = os.path.join(self.target_path,'forecast-%s-belchertown.json' % placemark['id'])
            fnt = os.path.join(self.target_path,'forecast-%s-belchertown.json.tmp' % placemark['id'])
        if dryrun:
            s = json.dumps(forecast_result,indent=4,ensure_ascii=False)
            print(s)
        else:
            if self.verbose:
                loginf("write Belchertown JSON file to %s" % fnt)
            try:
                with open(fnt,"w") as file:
                    json.dump(forecast_result,file,indent=4,ensure_ascii=False)
                    if self.verbose:
                        loginf("move Belchertown JSON file to %s" % fn)
                    shutil.move(fnt, fn)
            except Exception as e:
                logerr("error writing to '%s': %s" % (fn,e))
    
    # Aeris Weather API download
    def download_aeris(self, what, src=""):
        if what=='aqi' or what=='aeris_aqi':
            src = src + " Airquality"
            url = (
                "https://api.aerisapi.com/airquality/closest?p=%s,%s&format=json&radius=50mi&limit=1&client_id=%s&client_secret=%s"
                % (self.latitude, self.longitude, self.aeris_api_id, self.aeris_api_secret)
                )
        elif what=='aeris_metar':
            url = (
                "https://api.aerisapi.com/observations/closest?p=%s,%s&format=json&filter=metar&limit=1&client_id=%s&client_secret=%s"
                % (self.latitude, self.longitude, self.aeris_api_id, self.aeris_api_secret)
                )
        elif what=='aeris_mesonet':
            url = (
                "https://api.aerisapi.com/observations/closest?p=%s,%s&format=json&filter=mesonet&limit=1&client_id=%s&client_secret=%s"
                % (self.latitude, self.longitude, self.aeris_api_id, self.aeris_api_secret)
                )
        else:
            if self.log_failure or self.verbose:
                logerr('%s not configured' % what)
            return [{'success':False,'error':{'code':'not configured','description':'%s not configured' % what,'source':src,'response':[]}}]

        headers={'User-Agent':'weewx-DWD'}
        try:
            reply = requests.get(url,headers=headers)
        except ConnectionError as e:
            if self.log_failure or self.verbose:
                logerr(e)
            return [{'success':False,'error':{'code':e.__name__,'description':str(e)},'source':src,'response':[]}]
        
        if reply.status_code==200:
            if self.log_success or self.verbose:
                loginf('successfully downloaded %s' % reply.url)
            try:
                res = json.loads(reply.content)
                res['source'] = src
                return [res]
            except Exception as e:
                if self.log_failure or self.verbose:
                    logerr(e)
                return [{'success':False,'error':{'code':e.__name__,'description':str(e)},'source':src,'response':[]}]
        else:
            return [{
                'success':False,
                'error':{'code':reply.status_code,'description':reply.reason},
                'source':src,
                'response':[] 
            }]

    # AQI API download
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
                        tse = ForecastPWS.timestamp(vals['date end'])
                        te = ForecastPWS.isoformat(tse) if tse is not None else vals['date end']
                        aqi['response'].append({
                            'id':ii,
                            'loc':{'long':None,'lat':None},
                            #ho Test
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

    #Brightsky API Download
    def download_brightsky(self, what, src):
        if what=='current_weather':
            url = (
               "https://api.brightsky.dev/current_weather?tz=Europe/Berlin&units=dwd&wmo_station_id=%s"
                % (self.belchertown_forecast)
                )
        else:
            if self.log_failure or self.verbose:
                logerr('%s not configured' % what)
            return [{'success':False,'error':{'code':'not configured','description':'%s not configured' % what,'source':src,'response':[]}}]

        headers={'User-Agent':'weewx-DWD'}
        try:
            reply = requests.get(url,headers=headers)
        except ConnectionError as e:
            if self.log_failure or self.verbose:
                logerr(e)
            return [{'success':False,'error':{'code':e.__name__,'description':str(e)},'source':src,'response':[]}]
        
        if reply.status_code==200:
            if self.log_success or self.verbose:
                loginf('successfully downloaded %s' % reply.url)
            try:
                rtn = json.loads(reply.content)
                location = self.get_station_location()
                ts = int(KmlParser._mktime(rtn['weather']['timestamp'])*0.001)
                night = self.is_night(location,ts)
                condition = rtn['weather']['condition']
                cloudcover = int(rtn['weather']['cloud_cover'])
                icon = rtn['weather']['icon']
                if condition == 'dry':
                    condition = condition + "-" + icon
                #print("Brightsky Condition: ", condition)
                bscode = weather_decode(condition,cloudcover,night,'brightsky')
                #print("Brightsky Weather decoded: ", bscode)

                # Icons nach https://github.com/jdemaeyer/brightsky/issues/111
                # Icons nach https://github.com/jdemaeyer/brightsky/blob/master/brightsky/web.py#L146-L174
                # condition - dry┃fog┃rain┃sleet┃snow┃hail┃thunderstorm┃
                # icon - clear-day┃clear-night┃partly-cloudy-day┃partly-cloudy-night┃cloudy┃fog┃wind┃rain┃sleet┃snow┃hail┃thunderstorm┃
                res = [{
                    'success':True,
                    'error':None,
                    'source':src,
                    'response':[{
                        'id':rtn['sources'][0]['id'],
                        'dataSource':rtn['sources'][0]['observation_type'],
                        'dwd_station_id':rtn['sources'][0]['dwd_station_id'],
                        'wmo_station_id':rtn['sources'][0]['wmo_station_id'],
                        'loc':{
                            'long':rtn['sources'][0]['lon'],
                            'lat':rtn['sources'][0]['lat']
                        },
                       'place':{
                           'name':rtn['sources'][0]['station_name'],
                           'city':'Weiden',
                           'state':'by',
                           'country':'de'
                        },
                        'profile':{
                            'tz':'Europe/Berlin',
                            'tzname':'CET',
                            'tzoffset':3600,
                            'isDST':False,
                            'elevM':rtn['sources'][0]['height']
                        },
                        'ob':{
                            'timestamp':ts,
                            'dateTimeISO':rtn['weather']['timestamp'],
                            'tempC':nround(rtn['weather']['temperature'],1),
                            'dewpointC':nround(rtn['weather']['dew_point'],1),
                            'humidity':rtn['weather']['relative_humidity'],
                            'pressureMB':nround(rtn['weather']['pressure_msl'],1),
                            'windKPH':nround(rtn['weather']['wind_speed_10']),
                            'windSpeedKPH':nround(rtn['weather']['wind_speed_10']),
                            'windDir':compass(nround(rtn['weather']['wind_direction_10']),self.belchertown_compasslang,False),
                            'windDirDEG':nround(rtn['weather']['wind_direction_10']),
                            'visibilityKM':rtn['weather']['visibility']*0.001,
                            'weather':bscode[1],
                            'weatherCoded':bscode[7],
                            'weatherPrimary':bscode[1],
                            'weatherPrimaryCoded':bscode[7],
                            'cloudsCoded':cloudcover_decode(cloudcover,'brightsky')[3],
                            'icon':bscode[6]+('n' if night else '')+'.png',
                            'solradWM2':None,
                            'isDay':not night,
                            'sky':cloudcover
                        }
                    }]
                }]

                return res
            except Exception as e:
                if self.log_failure or self.verbose:
                    logerr(e)
                return [{'success':False,'error':{'code':e.__name__,'description':str(e)},'source':src,'response':[]}]
        else:
            if self.log_failure or self.verbose:
                logerr('error downloading %s: %s %s' % (reply.url,reply.status_code,reply.reason))
            return [{
                'success':False,
                'error':{'code':reply.status_code,'description':reply.reason},
                'source':src,
                'response':[] }]

    #Weatherbit.io API Download
    def download_weatherbit(self, what, src):
        if what=='current':
            url = (
               "https://api.weatherbit.io/v2.0/current?lat=%s&lon=%s&units=M&lang=de&key=%s"
                % (self.latitude, self.longitude, self.weatherbit_api_key)
                )
        else:
            if self.log_failure or self.verbose:
                logerr('%s not configured' % what)
            return [{'success':False,'error':{'code':'not configured','description':'%s not configured' % what,'source':src,'response':[]}}]

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
                location = self.get_station_location()
                ts = int(rtn['data'][0]['ts'])
                night = self.is_night(location,ts)

                # Icons/Codes https://www.weatherbit.io/api/codes

                code = rtn['data'][0]['weather']['code']
                cloudcover = int(rtn['data'][0]['clouds'])
                wbcode = weather_decode(code,cloudcover,night,'weatherbit')

                res = [{
                    'success':True,
                    'error':None,
                    'source':src,
                    'response':[{
                        'id':rtn['data'][0]['station'],
                        'dataSource':None,
                        'loc':{
                            'long':None,
                            'lat':None
                        },
                       'place':{
                           'name':'Schirmitz',
                           'city':'Schirmitz',
                           'state':'by',
                           'country':rtn['data'][0]['country_code']
                        },
                        'profile':{
                            'tz':'Europe/Berlin',
                            'tzname':'CET',
                            'tzoffset':3600,
                            'isDST':False,
                            'elevM':None
                        },
                        'ob':{
                            'timestamp':rtn['data'][0]['ts'],
                            'dateTimeISO':ForecastPWS.isoformat(rtn['data'][0]['ts']),
                            'tempC':nround(rtn['data'][0]['temp'],1),
                            'dewpointC':nround(rtn['data'][0]['dewpt'],1),
                            'humidity':rtn['data'][0]['rh'],
                            'pressureMB':nround(rtn['data'][0]['slp'],1),
                            'windKPH':nround(rtn['data'][0]['wind_spd']),
                            'windSpeedKPH':nround(rtn['data'][0]['wind_spd']),
                            'windDir':compass(nround(rtn['data'][0]['wind_dir']),self.belchertown_compasslang,False),
                            'windDirDEG':nround(rtn['data'][0]['wind_dir']),
                            'visibilityKM':rtn['data'][0]['vis'],
                            'weather':wbcode[1],
                            'weatherCoded':wbcode[7],
                            'weatherPrimary':wbcode[1],
                            'weatherPrimaryCoded':wbcode[7],
                            'cloudsCoded':cloudcover_decode(cloudcover,'weatherbit')[3],
                            'icon':wbcode[6]+('n' if night else '')+'.png',
                            'solradWM2':rtn['data'][0]['solar_rad'],
                            'isDay':not night,
                            'sky':cloudcover
                        },
                    }]
                }]

                return res
            except Exception as e:
                if self.log_failure or self.verbose:
                    logerr(e)
                return [{'success':False,'error':{'code':e.__name__,'description':str(e)},'source':src,'response':[]}]
        else:
            if self.log_failure or self.verbose:
                logerr('error downloading %s: %s %s' % (reply.url,reply.status_code,reply.reason))
            return [{
                'success':False,
                'error':{'code':reply.status_code,'description':reply.reason},
                'source':src,
                'response':[] }]

    #ho OpenWeatherMap API Download
    def download_owm(self, what, src):
        if what=='weather':
            url = (
               "https://api.openweathermap.org/data/2.5/weather?lat=%s&lon=%s&units=metric&lang=de&appid=%s"
                % (self.latitude, self.longitude, self.owm_api_key)
                )
        else:
            if self.log_failure or self.verbose:
                logerr('%s not configured' % what)
            return [{'success':False,'error':{'code':'not configured','description':'%s not configured' % what,'source':src,'response':[]}}]

        headers={'User-Agent':'weewx-DWD'}
        try:
            reply = requests.get(url,headers=headers)
        except ConnectionError as e:
            if self.log_failure or self.verbose:
                logerr(e)
            return [{'success':False,'error':{'code':e.__name__,'description':str(e)},'source':src,'response':[]}]
        
        if reply.status_code==200:
            if self.log_success or self.verbose:
                loginf('successfully downloaded %s' % reply.url)
            try:
                rtn = json.loads(reply.content)
                location = self.get_station_location()
                ts = int(rtn['dt'])
                night = self.is_night(location,ts)

                # Icons/Codes https://openweathermap.org/weather-conditions

                code = rtn['weather'][0]['id']
                cloudcover = int(rtn['clouds']['all'])
                owmcode = weather_decode(code,cloudcover,night,'owm')

                res = [{
                    'success':True,
                    'error':None,
                    'source':src,
                    'response':[{
                        'id':rtn['id'],
                        'dataSource':rtn['base'],
                        'loc':{
                            'long':rtn['coord']['lon'],
                            'lat':rtn['coord']['lat']
                        },
                       'place':{
                           'name':rtn['name'],
                           'city':rtn['name'],
                           'state':'by',
                           'country':rtn['sys']['country']
                        },
                        'profile':{
                            'tz':'Europe/Berlin',
                            'tzname':'CEST',
                            'tzoffset':rtn['timezone'],
                            'isDST':False,
                            'elevM':None
                        },
                        'ob':{
                            'timestamp':ts,
                            'dateTimeISO':ForecastPWS.isoformat(ts),
                            'tempC':nround(rtn['main']['temp'],1),
                            'dewpointC':None, #TODO
                            'humidity':rtn['main']['humidity'],
                            'pressureMB':nround(rtn['main']['pressure'],1),
                            'windKPH':nround(rtn['wind']['speed']),
                            'windSpeedKPH':nround(rtn['wind']['speed']),
                            'windDir':compass(nround(rtn['wind']['deg']),self.belchertown_compasslang,False),
                            'windDirDEG':nround(rtn['wind']['deg']),
                            'visibilityKM':int(rtn['visibility']*0.001),
                            'weather':owmcode[1],
                            'weatherCoded':owmcode[7],
                            'weatherPrimary':owmcode[1],
                            'weatherPrimaryCoded':owmcode[7],
                            'cloudsCoded':cloudcover_decode(cloudcover,'owm')[3],
                            'icon':owmcode[6]+('n' if night else '')+'.png',
                            'solradWM2':None,
                            'isDay':not night,
                            'sky':cloudcover
                        },
                    }]
                }]

                return res
            except Exception as e:
                if self.log_failure or self.verbose:
                    logerr(e)
                return [{'success':False,'error':{'code':e.__name__,'description':str(e)},'source':src,'response':[]}]
        else:
            if self.log_failure or self.verbose:
                logerr('error downloading %s: %s %s' % (reply.url,reply.status_code,reply.reason))
            return [{
                'success':False,
                'error':{'code':reply.status_code,'description':reply.reason},
                'source':src,
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
            if placemark['Forecast']['ww3'][idx] is not None:
                vals = {ii:placemark['Forecast'][ii][idx] for ii in placemark['Forecast'] if placemark['Forecast'][ii][idx] is not None}
                vals['timestamp'] = int(val*0.001)
                try:
                    ww = []
                    if idx>=2: ww.append(int(placemark['Forecast']['ww'][idx-2]))
                    if idx>=1: ww.append(int(placemark['Forecast']['ww'][idx-1]))
                    ww.append(int(placemark['Forecast']['ww'][idx]))
                    vals['ww'] = ww
                except Exception:
                    pass
                try:
                    vals['ww3'] = int(placemark['Forecast']['ww3'][idx])
                except Exception:
                    pass
                # calculate min, max, and avg for hourly observerations
                for ii in ['PPPP','TTT','Td','T5cm','DD','FF','N','Neff','VV','R101']:
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
                        logerr(e)
                # Is the timestamp night or day?
                try:
                    #night = self.is_night(location,val*0.001)
                    night = daynights[idx]
                except Exception:
                    night = None
                # weather symbol
                try:
                    wwcode = weather_decode([vals['ww3']],vals['Neffavg'],night)
                    icon = self.icon_pth+'/'+wwcode[self.iconset]
                    if self.iconset==6: icon += ('n' if night else '')+'.png'
                    vals['night'] = night
                    vals['icon'] = icon
                    vals['icontitle'] = wwcode[2] if lang=='en' else wwcode[1]
                except Exception as e:
                    logerr(e)
                # append new record to the list
                recs.append(vals)
        return recs
                
    
    def calculate_daily_forecast(self, placemark, timesteps, daynights, lang='de'):
        # observation types to calculate average for
        AVGS = ['TTT','Td','FF','DD','PPPP','N','Neff','VV']
        days = dict()
        # loop over all timestamps
        #ho Test, xx Tage analog Belchertown, keine weiteren Checks, ob option belchertown ...
        if self.database_max_days is not None:
            actDate = datetime.datetime.now()
            endDate = actDate + datetime.timedelta(days=self.database_max_days)
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
            if self.database_max_days is not None:
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
            wwcode = weather_decode(days[day]['ww'],days[day]['Neffavg'],False)
            if wwcode[self.iconset] is None:
                days[day]['icon'] = 'unknown.png'
            else:
                days[day]['icon'] = self.icon_pth+'/'+wwcode[self.iconset]+('.png' if self.iconset==6 else '')
            days[day]['icontitle'] = wwcode[2] if lang=='en' else wwcode[1]
            # print(json.dumps(days[day],indent=4,ensure_ascii=False))
        return days


    def write_database(self, placemark, timesteps):
        if has_sqlite and self.SQLITE_ROOT:
            self.dbm_open(placemark['id'])
            cursor = self.dbm_cursor()
            self.dbm_truncate(cursor)
            #ho Test, xx Tage analog Belchertown, keine weiteren Checks, ob option belchertown ...
            if self.database_max_days is not None:
                actDate = datetime.datetime.now()
                endDate = actDate + datetime.timedelta(days=self.database_max_days)
                actDate = int(actDate.strftime('%Y%m%d%H00'))
                endDate = int(endDate.strftime('%Y%m%d0000'))
                print("DEBUG actDate %s" % actDate)
                print("DEBUG endDate %s" % endDate)
            for idx,ii in enumerate(timesteps):
                #ho Test, xx Tage analog Belchertown, keine weiteren Checks, ob option belchertown ...
                if self.database_max_days is not None:
                    checkDate = int(time.strftime('%Y%m%d%H%M',time.localtime(ii*0.001-1)))
                    if (checkDate < actDate) or (checkDate > endDate):
                        if self.verbose:
                            print('write_database: >>> skip forecast %s' % time.strftime('%d.%m.%Y %H:%M',time.localtime(ii*0.001)))
                        continue
                if self.verbose:
                    print('write_database: insert forecast %s' % time.strftime('%d.%m.%Y %H:%M',time.localtime(ii*0.001)))
                values = {'dateTime':int(ii*0.001),
                          'usUnits':0x10,  # METRIC
                          'interval':60,
                          'hour':time.localtime(ii*0.001).tm_hour,  # min.
                          'outTemp':None,
                          'dewpoint':None,
                          'humidity':None
                         }
                for jj in placemark['Forecast']:
                    key = dwd_schema_dict.get(jj)
                    if key:
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
        
        if 'html' in output:
        
            if 'all' in output:
                if self.verbose:
                    loginf('output all data')
                self.write_html(placemark,timesteps,daynights,issue,None,dryrun,lang=lang)

            if 'daily' in output:
                if self.verbose:
                    loginf('output daily forecast')
                self.write_html_daily(placemark,days,timesteps,issue,None,dryrun,lang=lang)

            if 'hourly' in output:
                if self.verbose:
                    loginf('output hourly forecast')
                self.write_html(placemark,timesteps,daynights,issue,['TTT','FF','DD','RR1c','R101','PPPP','Rad1h'],dryrun,range=11,lang=lang)
        
        if 'json' in output:
            if self.verbose:
                loginf('json')
            self.dump(placemark,days,recs3hr,timesteps,daynights,issue,dryrun,lang=lang)
            
        if 'belchertown' in output:
            if self.verbose:
                loginf('belchertown')
            self.belchertown(placemark,days,recs3hr,timesteps,daynights,issue,dryrun)
            
        if 'database' in output:
            if self.verbose:
                loginf('database')
            self.write_database(placemark,timesteps)
            
        if self.verbose:
            loginf('placemark id "%s" processed' % placemark.get('id'))

    def forecast_wbx_location(self, dest):
        """ get the longitude and latitude of a city """
        data = None
        if has_geopy:
            try:
                locator = Nominatim(user_agent="forecast-pwsWeiherhammer")
                dest = dest.replace('/',',')
                dest = dest.replace('-',',')
                dest = dest.replace('.',',')
                dest = dest.replace(' ',',')
                dest = dest.split(',')
                dest = dest[0] + ', Germany, Bavaria'
                location = locator.geocode(dest)
                if location is not None:
                    data = {
                        'name':location.address,
                        'lat':location.latitude,
                        'lon':location.longitude,
                    }
                elif self.verbose:
                    loginf("forecast_wbx_location: longitude and latitude '%s' not found!" % (dest))
            except Exception as e:
                logerr("forecast_wbx_location: getting longitude and latitude '%s' failed: %s" % (dest,e))
        return data

    # TODO Write once in json file and if it exists then read this one. (wbx_radius_km_<self.wbx_radius_km>.json)
    def forecast_wbx_radius_km(self, dest):
        if self.verbose:
            loginf("forecast_wbx_radius_km: get distance to '%s'" % (dest))
        dist_km = None
        geodata = self.forecast_wbx_location(dest)
        if has_geopy and geodata:
            try:
                dist_km = distance.distance((geodata['lat'],geodata['lon']),(self.latitude,self.longitude)).km
            except Exception:
                logerr("forecast_wbx_radius_km: getting distance to '%s' failed: %s" % (dest,e))
        elif self.verbose:
            loginf("forecast_wbx_radius_km: get distance to '%s' not possible!" % (dest))
        return dist_km

    # TODO css, error handling, opt issued time, change table to divs?
    # https://www.dwd.de/DWD/warnungen/agrar/wbx/wbx_tab_alle_BY.html
    def forecast_wbx_html(self, keymapping_dict, tabheader_list, tabcontent_dict, issued_time, output, dryrun, lang='de'):
        if self.verbose:
            loginf('forecast_wbx_html: started.')
        html  = '<!-- DWD Waldbrandgefahrenindex -->\n'
        html += '<div class="col-md-12 wbx-headline">\n'
        html += '    $obs.label.forecast_header_wbx\n'
        html += '    <span class="issued-DWD"> $obs.label.forecast_issuedWBX_dwd ' + issued_time + '</span>\n'
        html += '</div>\n'
        html += '<style>\n'
        html += '    .farbidx0 {background-color:#FFFFFF; color:#000000;}\n'
        html += '    .farbidx1 {background-color:#FFFFCD; color:#000000;}\n'
        html += '    .farbidx2 {background-color:#FFD879; color:#000000;}\n'
        html += '    .farbidx3 {background-color:#FF8C39; color:#000000;}\n'
        html += '    .farbidx4 {background-color:#E9161D; color:#000000;}\n'
        html += '    .farbidx5 {background-color:#7F0126; color:#FFFFFF;}\n'
        html += '</style>\n'
        html += '<div class="col-md-12 wbx-table-container" style="margin-top:5px">\n'
        html += '    <table class="table table-striped wbx-table">\n'
        html += '        <thead class="table-light wbx-table-head">\n'
        html += '            <tr>\n'
        for col, cellcontent in enumerate(tabheader_list):
            if (col == 0):
                html += '                <th scope="col" class="wbx-table-head-station">'
            else:
                html += '                <th scope="col" class="wbx-table-head-day">'
            html += str(cellcontent)
            html += '</th>\n'
        html += '            </tr>\n'
        html += '        </thead>\n'
        html += '        <tbody class="table-group-divider wbx-table-body">\n'
        for station, content_list in tabcontent_dict.items():
            html += '            <tr>\n'
            for col, cellcontent in enumerate(content_list):
                if (col == 0):
                    html += '                <th scope="row" class="wbx-table-body-station">'
                    html += cellcontent
                    html += '</th>\n'
                else:
                    html += '                <td class="wbx-table-body-day'
                    if keymapping_dict[cellcontent]['class'] is not None:
                        html += ' ' + keymapping_dict[cellcontent]['class']
                    html += '">'
                    #html += (cellcontent + ' - ')
                    html += keymapping_dict[cellcontent]['description']
                    html += '</td>\n'
        html += '            </tr>\n'
        html += '        </tbody>\n'
        html += '    </table>\n'
        html += '</div>\n'
        if dryrun:
            print(html)
        else:
            try:
                with open("%s/%s" % (self.target_path,self.wbx_output_file),"w") as file:
                    file.write(html)
            except Exception as e:
                logerr("error writing file %s/%s: %s" % (self.target_path,self.wbx_output_file,e))

        if self.verbose:
            loginf('forecast_wbx_html: finished.')
    
    # TODO error handling, optimizations
    def forecast_wbx_read(self, data, output, dryrun, lang='de'):
        if self.verbose:
            loginf('forecast_wbx_read: started.')
        tabheader_list = []
        tabcontent_dict = dict()
        keymapping_dict = dict()
        htmlcontent_dict = dict()
        htmlsource = ''
        wbx_found = False
        try:
            # Mapping index to description and class
            for key, row in enumerate(data['data']['tables'][0]['rows']):
                if (key > 0):
                    keymapping_dict[row['cols'][0]['nodeValue']] = dict()
                    keymapping_dict[row['cols'][0]['nodeValue']]['description'] = row['cols'][1]['nodeValue']
                    keymapping_dict[row['cols'][0]['nodeValue']]['class'] = None
                    classes = row['cols'][0]['attr']['class'].split(' ')
                    for elem in classes:
                        if elem.find('farbidx') > -1:
                            keymapping_dict[row['cols'][0]['nodeValue']]['class'] = elem
            if self.verbose:
                loginf('forecast_wbx_read: keymapping_dict: %s' % str(keymapping_dict))

            # Tab Header
            for key, col in enumerate(data['data']['tables'][1]['rows'][0]['cols']):
                tabheader_list.append(col['nodeValue'])
            if self.verbose:
                loginf('forecast_wbx_read: tabheader_list:  %s' % str(tabheader_list))

            # Tab content wbx stations
            if not isinstance(self.wbx_stations,list):
                # self.wbx_stations = list(self.wbx_stations) hat irgendwie nicht funktioniert
                tmplist = []
                tmplist.append(self.wbx_stations)
                self.wbx_stations = tmplist
            if self.verbose:
                print("forecast_wbx_read: Searching Stations '%s'" % str(self.wbx_stations))
                if self.wbx_radius_km is not None:
                    print("forecast_wbx_read: and cities with distance < '%f'km" % self.wbx_radius_km)
            # load stations
            wbx_stations = [element.lower() for element in self.wbx_stations]
            stationidx = 0
            for row in data['data']['tables'][1]['rows']:
                station_found = False
                distkm = None
                for key, cols in enumerate(row['cols']):
                    if (key == 0) and (cols['nodeValue'] != 'Stationsname'):
                        if self.wbx_radius_km is not None:
                            distkm = self.forecast_wbx_radius_km(cols['nodeValue'])
                            if distkm is not None:
                                if (distkm > self.wbx_radius_km):
                                    distkm = None
                                else:
                                    print(">>> Station: '%s', Entfernung: '%f'km" % (cols['nodeValue'], distkm))
                        if (distkm is not None) or (cols['nodeValue'].lower() in wbx_stations):
                            if self.verbose:
                                print("forecast_wbx_read: Station '%s' found" % cols['nodeValue'])
                            wbx_found = True
                            station_found = True
                            tabcontent_dict[stationidx] = []
                    if station_found:
                        tabcontent_dict[stationidx].append(cols['nodeValue'])
                if station_found:
                    stationidx += 1
            if self.verbose:
                loginf('forecast_wbx_read: tabcontent_dict: %s' % str(tabcontent_dict))

            # DWD issued time. I can't do better so far
            if wbx_found:
                issued_time = None
                startpos = data['data']['content'].find("Deutscher Wetterdienst, erstellt") + len("Deutscher Wetterdienst, erstellt")
                if startpos > -1:
                    endpos = startpos + data['data']['content'][startpos:].find("UTC")
                    issued_time = data['data']['content'][startpos:endpos].strip()
                if issued_time is not None:
                    is_zone = tz.gettz('UTC')
                    to_zone = tz.gettz('Europe/Berlin')
                    utc = datetime.datetime.strptime(issued_time, '%d.%m.%Y %H:%M')
                    utc = utc.replace(tzinfo=is_zone)
                    central = utc.astimezone(to_zone)
                    issued_time = central.strftime('%d.%m.%Y %H:%M')
                    if self.verbose:
                        loginf("forecast_wbx_read: issued_time:     '%s'" % issued_time)
                else:
                    issued_time = 'N/A'
                    if self.log_failure:
                        logerr("forecast_wbx_read: No data for issued_time found!")
                # build html table
                self.forecast_wbx_html(keymapping_dict, tabheader_list, tabcontent_dict, issued_time, output, dryrun, lang)
            elif self.log_failure:
                logerr("forecast_wbx_read: No data for stations '%s' found!" % str(self.wbx_stations))
        except Exception as e:
            logerr("forecast_wbx_read: Exception '%s'" % (e))
        if self.verbose:
            loginf('forecast_wbx_read: finished.')
    
    def forecast_wbx(self, output, dryrun, lang='de'):
        if self.verbose:
            loginf('forecast_wbx: started.')
        fn = os.path.join(self.target_path,self.wbx_input_file)
        try:
            with open(fn, 'r') as file:
                data = json.load(file)
                self.forecast_wbx_read(data, output, dryrun, lang='de')
        except Exception as e:
            logerr("error opening file '%s': %s" % (fn,e))
        if self.verbose:
            loginf('forecast_wbx: finished.')
    
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
            for ii in DWD_WEATHER_CODE_LIST:
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
            for ii in DWD_WEATHER_CODE_LIST:
                if ii[5] not in icons: icons[ii[5]] = []
                icons[ii[5]].append(ii[0])
            print('DWD icons')
            print('=================')
            for ii in icons:
                print('%-16s: %s' % (ii,icons[ii]))
                
    def dbm_open(self, id):
        if has_sqlite and self.SQLITE_ROOT:
            fn = os.path.join(self.SQLITE_ROOT,'dwd-forecast-%s.sdb' % id)
            new = not os.path.exists(fn)
            self.connection = sqlite3.connect(fn)
            if new:
                s = ','.join([x[0]+' '+x[1] for x in schema])
                s = 'CREATE TABLE forecast ('+s+')'
                cur = self.dbm_cursor()
                if cur:
                    cur.execute(s)
                    self.dbm_commit()
            self.columns = [x[0] for x in schema]
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
    group.add_option("--wbx", action="store_true", dest="wbx",
                     help="Create Waldbrandgefahrenindex HTML inc file")
    group.add_option("--wbx-only", action="store_true", dest="wbxonly",
                     help="Create ONLY Waldbrandgefahrenindex HTML inc file")
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
        ForecastPWS.print_icons_ww(options.iconset)
        sys.exit(0)
        
    if options.weewx:
        config_path = "/home/weewx/weewx.conf"
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
                'altitude':[394,'meter']},
            'forecast-pwsWeiherhammer': {
                'path':'/home/weewx/skins/Weiherhammer/dwd',
                'forecast':{
                    'icons':'../images'}}}
    
    if len(args)>0:
        location = args[0]
        if not location: location = None
    else:
        location = 'Weiden'
        
    if options.orientation:
        config['forecast-pwsWeiherhammer']['forecast']['orientation'] = options.orientation
    if options.iconset:
        config['forecast-pwsWeiherhammer']['forecast']['icon_set'] = options.iconset
    if options.aqisource:
        if 'Belchertown' not in config['forecast-pwsWeiherhammer']:
            config['forecast-pwsWeiherhammer']['Belchertown'] = dict()
        config['forecast-pwsWeiherhammer']['Belchertown']['aqi_source'] = options.aqisource
    if options.hideplacemark is not None:
        config['forecast-pwsWeiherhammer']['forecast']['show_placemark'] = not options.hideplacemark

    forecastPws = ForecastPWS(config,options.verbose)
    
    output = []
    if options.all: output.append('all')
    if options.hourly: output.append('hourly')
    if options.belchertown: output.append('belchertown')
    if options.daily or len(output)==0: output.append('daily')
    
    if options.html: output.append('html')
    if options.json: output.append('json')
    if options.database: output.append('database')
    if options.wbx: output.append('wbx')
    if options.wbxonly: output.append('wbx-only')
    if not options.html and not options.json and not options.belchertown:
        output.append('html')
        if options.daily:
            output.append('json')

    if not ('wbx-only' in output):
        if options.uba:
            zz = forecastPws.download_uba(options.uba,location,lang=options.lang)
            print(json.dumps(zz,indent=4,ensure_ascii=False))
            exit()

        zz = forecastPws.download_kml(location,'l')
        mmos = forecastPws.process_kml(zz,options.log_tags)
        # print(json.dumps(mmos,indent=4,ensure_ascii=False))
        forecastPws.forecast_all(mmos,output,options.dry_run,lang=options.lang)

    if ('wbx' in output) or ('wbx-only' in output):
        forecastPws.forecast_wbx(output, options.dry_run, lang=options.lang)

