#!/usr/bin/python
# Copyright (c) 2021 Henry Ott
# Author: Henry Ott hoetz@gmx.net

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import json
# import urllib
import time
import datetime
import requests
import configobj
import os.path
import paho.mqtt.client as paho 
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

if __name__ == "__main__":
    import optparse
    import sys
    def loginf(x):
        print(x, file=sys.stderr)
    def logerr(x):
        print(x, file=sys.stderr)

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

def nround(x,n=None):
    if x is None: return None
    return round(x,n)

def tobool(x):
    """Convert an object to boolean.
    
    Examples:
    >>> print(tobool('TRUE'))
    True
    >>> print(tobool(True))
    True
    >>> print(tobool(1))
    True
    >>> print(tobool('FALSE'))
    False
    >>> print(tobool(False))
    False
    >>> print(tobool(0))
    False
    >>> print(tobool('Foo'))
    Traceback (most recent call last):
    ValueError: Unknown boolean specifier: 'Foo'.
    >>> print(tobool(None))
    Traceback (most recent call last):
    ValueError: Unknown boolean specifier: 'None'.
    """

    try:
        if x.lower() in ('true', 'yes', 'y'):
            return True
        elif x.lower() in ('false', 'no', 'n'):
            return False
    except AttributeError:
        pass
    try:
        return bool(int(x))
    except (ValueError, TypeError):
        pass
    raise ValueError("Unknown boolean specifier: '%s'." % x)

to_bool = tobool

###############################################################################
#    process UBA AIRQUALITY data                                              #
###############################################################################
        
class UBAAirquality(object):

    def __init__(self, config_dict, verbose=False, force=False, station=None):
        # target path
        conf_dict = config_dict['API_Umweltbundesamt_Airquality']
        self.target_path = conf_dict.get('path', '/tmp')
        self.enable = to_bool(conf_dict.get('enable',False))

        # API config data
        api_dict = config_dict['API_Umweltbundesamt_Airquality']['API']
        if station is not None:
            self.station_id = int(station)
        else:
            self.station_id = int(api_dict.get('station_id',509))
        self.station_name = api_dict.get('station_name','Weiden')
        self.station_state = api_dict.get('station_state','de')
        self.station_name = api_dict.get('station_county','by')
        self.api_lang = api_dict.get('lang','de')
        self.api_stale_timer = api_dict.get('stale_timer',3600)
        self.api_is_stale = False
        self.force = force

        # Output file config data
        file_dict = config_dict['API_Umweltbundesamt_Airquality']['FILE']
        self.filename = file_dict.get('filename','uba_airquality.json')

        # MQTT config data
        mqtt_dict = config_dict['API_Umweltbundesamt_Airquality']['MQTT']
        self.mqtt_enable = to_bool(mqtt_dict.get('enable',False))
        self.mqtt_server_url = mqtt_dict.get('server_url','mqtt://127.0.0.1:1883')
        self.mqtt_topic = mqtt_dict.get('topic','uba/airquality')
        self.mqtt_client_id = mqtt_dict.get('client_id','UBAAirquality')
        self.mqtt_qos = mqtt_dict.get('qos',0)
        self.mqtt_retain = to_bool(mqtt_dict.get('retain',False))
        self.mqtt_connected = False

        # logging
        self.verbose = verbose
        self.log_success = to_bool(config_dict['API_Umweltbundesamt_Airquality'].get('log_success',config_dict.get('log_success',False)))
        self.log_failure = to_bool(config_dict['API_Umweltbundesamt_Airquality'].get('log_failure',config_dict.get('log_failure',False)))

        if int(config_dict.get('debug',0))>0 or verbose:
            self.log_success = True
            self.log_failure = True
            self.verbose = True

        # Location Lat/Lon/Alt
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
 
        # Belchertown
        try:
            belchertown_dict = config_dict['UBAAirquality'].get('Belchertown',{})
            belchertown_section = config_dict['StdReport']['Belchertown']
            if 'HTML_ROOT' in belchertown_section:
                self.belchertown_html_root = os.path.join(
                    config_dict['WEEWX_ROOT'],
                    belchertown_section['HTML_ROOT'])
            else:
                self.belchertown_html_root = os.path.join(
                    config_dict['WEEWX_ROOT'],
                    config_dict['StdReport']['HTML_ROOT'])
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
            self.forecast_api_id = ew.get('forecast_api_id',es.get('forecast_api_id',api_dict.get('client_id')))
            self.forecast_api_secret = ew.get('forecast_api_secret',es.get('forecast_api_secret',api_dict.get('client_secret')))
        except LookupError:
            belchertown_section = {}
            self.belchertown_html_root = None
            self.belchertown_forecast = None
            self.forecast_api_id = None
            self.forecast_api_secret = None
        if __name__ == "__main__" and verbose:
            print('-- configuration data ----------------------------------')
            print('log success:      ',self.log_success)
            print('log failure:      ',self.log_failure)
            print('target path:      ',self.target_path)
            print('station location: ','lat',self.latitude,'lon',self.longitude,'alt',self.altitude)
            print('MQTT Server URL:  ',self.mqtt_server_url)
            print('MQTT Topic:       ',self.mqtt_topic)
            print('--------------------------------------------------------')

    #create function for callback
    def on_connect(self, client, userdata, flags, rc):
        """ MQTT in disconnect """
        if self.log_success or self.verbose:
            loginf('MQTT client connected with Result: {}'.format(rc))
        if rc == 0:
            self.mqtt_connected = True

    def on_publish(self, client, userdata, rc):
        """ MQTT on publish """
        if self.log_success or self.verbose:
            loginf('MQTT data published.')
        pass

    def on_disconnect(self, client, userdata, rc):
        """ MQTT in disconnect """
        if self.log_success or self.verbose:
            loginf('MQTT client disconnected.')
        self.mqtt_connected = False
   
    def publish_uba_airquality(self, jsondata):
        """ Publish data from UBAWeather Airquality API tp Message Broker """
        try:
            url = urlparse(self.mqtt_server_url)
            #create client object
            mqttclient = paho.Client(self.mqtt_client_id)
            if self.log_success or self.verbose:
                loginf('MQTT initialized.')

            #assign function to callback
            # mqttclient.on_connect = on_connect
            # mqttclient.on_publish = on_publish
            # mqttclient.on_disconnect = on_disconnect

            #connect broker
            mqttclient.connect(url.hostname, url.port)
            if self.log_success or self.verbose:
                loginf('MQTT connected.')

            res = mqttclient.publish(self.mqtt_topic, json.dumps(jsondata), retain=self.mqtt_retain, qos=int(self.mqtt_qos))
            if self.log_success or self.verbose:
                loginf('MQTT data uploaded with status: %s' % str(res))
            mqttclient.disconnect()
            if self.log_success or self.verbose:
                loginf('MQTT disconnected.')
        except Exception as e:
            if self.log_failure or self.verbose:
                logerr('Error publishing to broker: %s' % e)

    def read_uba_airquality_file(self, fn):
        """ Read data from UBAWeather Airquality API to JSON file """
        try:
            with open(fn, "r") as infile:
                erg = json.load(infile)
            if self.log_success or self.verbose:
                loginf("File '%s' succuessfully read." % fn)
            erg['originalUBATimestamp'] = erg['dateTime']
            # mod date
            erg['dateTime'] = int(time.time() + 0.5)
            return erg
        except Exception as e:
            if self.log_failure or self.verbose:
                logerr('Error reading file %s: %s' % (fn,e))


    def write_uba_airquality_file(self, fn, jsondata):
        """ Write data from UBAWeather Airquality API to JSON file """
        # Save json data to file. w+ creates the file if it doesn't
        # exist, and truncates the file and re-writes it everytime
        try:
            jd = json.dumps(jsondata) #,indent=4,ensure_ascii=False)
            with open(fn, "wb+") as outfile:
                outfile.write(jd.encode("utf-8"))
            if self.log_success or self.verbose:
                loginf("File '%s' succuessfully updated." % fn)
        except Exception as e:
            if self.log_failure or self.verbose:
                logerr('Error writing file %s: %s' % (fn,e))

    def convert_uba_airquality(self, jsondata):
        """ convert data from UBAWeather Airquality API 

https://www.umweltbundesamt.de/api/air_data/v2/airquality/json?date_from=2022-03-11&date_to=2022-03-12&lang=de&station=509

From:
[
    {
        "success": true,
        "error": null,
        "response": [
            {
                "id": "509",
                "loc": {
                    "long": null,
                    "lat": null
                },
                "place": {
                    "name": "Weiden",
                    "state": "de",
                    "country": "BY"
                },
                "periods": [
                    {
                        "dateTimeISO": "2022-03-12 09:00:00",
                        "timestamp": null,
                        "uba_index": 1,
                        "aqi": 33,
                        "category": "gut",
                        "color": "FFFF00",
                        "method": "airnow",
                        "dominant": null,
                        "pollutants": [
                            {
                                "type": "O3",
                                "name": "Ozon",
                                "valuePPB": null,
                                "valueUGM3": 72,
                                "uba_index": 1,
                                "aqi": 33,
                                "category": "gut",
                                "color": "FFFF00",
                                "unit": "µg/m³"
                            },
                            {
                                "type": "NO2",
                                "name": "Stickstoffdioxid",
                                "valuePPB": null,
                                "valueUGM3": 13,
                                "uba_index": 0,
                                "aqi": 6,
                                "category": "sehr gut",
                                "color": "00E400",
                                "unit": "µg/m³"
                            }
                        ]
                    }
                ],
                "profile": {
                    "tz": null,
                    "sources": [],
                    "stations": []
                },
                "relativeTo": {
                    "lat": 49.63227,
                    "long": 12.056186,
                    "bearing": null,
                    "bearingENG": null,
                    "distanceKM": null,
                    "distanceMI": null
                }
            }
        ]
    }
]
To:
{
  "dateTime" : 1646895281,
  "aqi" : 56,
  "aqi_category": 1,
  "o3" : 72,
  "o3_aqi": 33,
  "o3_category": 1,
  "no2" : 13,
  "no2_aqi": 6,
  "no2_category": 0,
}

"""
        if self.log_success or self.verbose:
            loginf('convert json')
        aq = dict()
        try:
            aq['dateTime'] = int(time.time() + 0.5)
            # aq['usUnits'] = 1
            aq['aqi'] = int(jsondata['response'][0]['periods'][0]['aqi'])
            aq['aqi_category'] = int(jsondata['response'][0]['periods'][0]['uba_index'])
            for pollutants in jsondata['response'][0]['periods'][0]['pollutants']:
                aqtype = str(pollutants['type'])
                aqtype = aqtype.lower()
                aq[aqtype] = float(pollutants['valueUGM3'])
                if aqtype == 'o3':
                    aq['o3_aqi'] = int(pollutants['aqi'])
                    aq['o3_category'] = int(pollutants['uba_index'])
                if aqtype == 'no2':
                    aq['no2_aqi'] = int(pollutants['aqi'])
                    aq['no2_category'] = int(pollutants['uba_index'])
            if self.log_success or self.verbose:
                loginf('Converted JSON:\n%s' % json.dumps(aq,indent=4,ensure_ascii=False))
            return aq
        except Exception as e:
            if self.log_failure or self.verbose:
                logerr(e)
            return None

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
            use = 'aqi'
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
            # return []
            return None
        url = 'https://www.umweltbundesamt.de/api/air_data/v2/' + url
        if self.verbose:
            loginf('API:\n%s' % url)

        # download data
        headers={'User-Agent':'weewx-DWD'}
        try:
            reply = requests.get(url,headers=headers)
        except ConnectionError as e:
            if self.log_failure:
                logerr(e)
            # return []
            return None
        
        if reply.status_code==200:
            if self.log_success or self.verbose:
                loginf('successfully downloaded %s' % reply.url)
            try:
                rtn = json.loads(reply.content)
                if self.verbose:
                    loginf('Original JSON:\n%s' % json.dumps(rtn,indent=4,ensure_ascii=False))
            except Exception as e:
                # return [{'success':False,'error':{'code':e.__name__,'description':str(e)},'response':[]}]
                return None
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
                        aqi['response'].append({
                            'id':ii,
                            'loc':{'long':None,'lat':None},
                            'place':{'name':'Weiden','state':'de','country':'by'},
                            'periods':[{
                                'dateTimeISO':vals['date end'],
                                'timestamp':None,
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

            if self.verbose:
                loginf('Aeris JSON:\n%s' % json.dumps(res,indent=4,ensure_ascii=False))

            if what=='aqi':
                # return [res]
                return res
            else:
                return res
        else:
            if self.log_failure or self.verbose:
                logerr('error downloading %s: %s %s' % (reply.url,reply.status_code,reply.reason))
            return None
            # return [{
                # 'success':False,
                # 'error':{'code':reply.status_code,'description':reply.reason},
                # 'response':[] }]

    def worker_uba_airquality(self, output):
        """ Worker UBAWeather Airquality """

        if not self.enable:
            loginf('Module disabled, skipping execution.')
            return

        if self.verbose:
            loginf('what to output: %s' % output)

        try:
            # Determine if the file exists and get it's modified time, enhanced
            # for 1 hr forecast to load close to the hour
            fn = os.path.join(self.target_path,self.filename)
            if os.path.exists(fn):
                if self.verbose:
                    loginf('API file %s exists.' % fn)
                if (int(time.time()) - int(os.path.getmtime(fn))) > int(
                    self.api_stale_timer
                ):
                    self.api_is_stale = True
                else:
                    # catches repeated calls every archive interval (300secs)
                    if (
                        time.strftime("%M") < "05"
                        and int(time.time()) - int(os.path.getmtime(fn))
                    ) > int(300):
                        self.api_is_stale = True
            else:
                # File doesn't exist, download a new copy
                if self.verbose:
                    loginf('API file %s not exists.' % fn)
                self.api_is_stale = True

            if self.api_is_stale or self.force:
                if self.verbose:
                    loginf('API is stale or force, download new data.')
                erg = self.download_uba('aqi', self.station_id, self.api_lang)
                if erg is None:
                    raise Exception

                erg = self.convert_uba_airquality(erg)
                if erg is None:
                    raise Exception

                self.write_uba_airquality_file(fn, erg)
            else:
                if self.verbose:
                    loginf('API is not stale, read last data from file.')
                erg = self.read_uba_airquality_file(fn)

            if 'mqtt' in output and self.mqtt_enable:
                if erg is None:
                    raise Exception
                self.publish_uba_airquality(erg)

            if self.verbose:
                loginf('UBAAirquality finished.')
        except Exception as e:
            if self.log_failure or self.verbose:
                logerr(e)

if __name__ == "__main__":

    usage = None

#    epilog = """Station list:
#https://www.dwd.de/DE/leistungen/met_verfahren_mosmix/mosmix_stationskatalog.cfg?view=nasPublication&nn=16102
#"""
    epilog = """"""

    # Create a command line parser:
    parser = optparse.OptionParser(usage=usage, epilog=epilog)

    # options
    parser.add_option("--config", dest="config_path", type=str,
                      metavar="CONFIG_FILE",
                      default=None,
                      help="Use configuration file CONFIG_FILE.")
    parser.add_option("--weewx", action="store_true",
                      help="Read config from weewx.conf.")

    group = optparse.OptionGroup(parser,"Output and logging options")
    group.add_option("-v","--verbose", action="store_true",
                      help="Verbose output")
    group.add_option("-f","--force", action="store_true",
                      help="Force API Download")
    parser.add_option_group(group)

    # commands
    group = optparse.OptionGroup(parser,"Commands")
    group.add_option("--mqtt", action="store_true", dest='mqtt',
                     help="Publish JSON to MQTT broker")

    parser.add_option_group(group)

    (options, args) = parser.parse_args()

    if len(args)>0:
        station = args[0]
#        if not location: location = None
    else:
        station = None
        
    if options.weewx:
        config_path = "/home/weewx/weewx.conf"
    else:
        config_path = options.config_path

    if config_path:
        print("Using configuration file %s" % config_path)
        config = configobj.ConfigObj(config_path)
    else:
        config = {}

    uba = UBAAirquality(config,options.verbose,options.force,station)

    output = []
    if options.mqtt: output.append('mqtt')
    
    uba.worker_uba_airquality(output)
