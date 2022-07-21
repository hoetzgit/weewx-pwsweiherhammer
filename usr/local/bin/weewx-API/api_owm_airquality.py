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
#    process AERIS AIRQUALITY data                                            #
###############################################################################
        
class OpenWeatherAirquality(object):

    def __init__(self, config_dict, verbose=False):
        # target path
        conf_dict = config_dict['API_OpenWeather_Airquality']
        self.target_path = conf_dict.get('path', '/tmp')
        self.enable = to_bool(conf_dict.get('enable',False))

        # API config data
        api_dict = config_dict['API_OpenWeather_Airquality']['API']
        self.app_id = api_dict.get('app_id','c1423a871e174ae102401bf7b8144c66')
        self.station_id = api_dict.get('station_id','61a488f209e7430001ba2725')
        self.units = api_dict.get('units','metric')
        self.api_stale_timer = api_dict.get('stale_timer',3600)
        self.api_is_stale = False

        # Output file config data
        file_dict = config_dict['API_OpenWeather_Airquality']['FILE']
        self.filename = file_dict.get('filename','openweather_airquality.json')

        # MQTT config data
        mqtt_dict = config_dict['API_OpenWeather_Airquality']['MQTT']
        self.mqtt_enable = to_bool(mqtt_dict.get('enable',False))
        self.mqtt_server_url = mqtt_dict.get('server_url','mqtt://127.0.0.1:1883')
        self.mqtt_topic = mqtt_dict.get('topic','openweather/airquality')
        self.mqtt_client_id = mqtt_dict.get('client_id','OpenWeatherAirquality')
        self.mqtt_qos = mqtt_dict.get('qos',0)
        self.mqtt_retain = to_bool(mqtt_dict.get('retain',False))
        self.mqtt_connected = False

        # logging
        self.verbose = verbose
        self.log_success = to_bool(config_dict['API_OpenWeather_Airquality'].get('log_success',config_dict.get('log_success',False)))
        self.log_failure = to_bool(config_dict['API_OpenWeather_Airquality'].get('log_failure',config_dict.get('log_failure',False)))

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
            belchertown_dict = config_dict['API_OpenWeather_Airquality'].get('Belchertown',{})
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
            print('openweather api id:     ',self.forecast_api_id)
            print('openweather api secret: ',self.forecast_api_secret)
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
   
    def publish_openweather_airquality(self, jsondata):
        """ Publish data from OpenWeather Airquality API to Message Broker """
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

    def read_openweather_airquality_file(self, fn):
        """ Read data from AerisWeather Airquality API to JSON file """
        try:
            with open(fn, "r") as infile:
                erg = json.load(infile)
            if self.log_success or self.verbose:
                loginf("File '%s' succuessfully read." % fn)
            erg['originalOpenWeatherTimestamp'] = erg['dateTime']
            # mod date
            erg['dateTime'] = int(time.time() + 0.5)
            return erg
        except Exception as e:
            if self.log_failure or self.verbose:
                logerr('Error reading file %s: %s' % (fn,e))


    def write_openweather_airquality_file(self, fn, jsondata):
        """ Write data from AerisWeather Airquality API to JSON file """
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

    def convert_openweather_airquality(self, jsondata):
        """ convert data from AerisWeather Airquality API 

https://api.openweathermap.org/data/2.5/air_pollution?lat=49.632270&lon=12.056186&units=metric&appid=c1423a871e174ae102401bf7b8144c66

From:
{
    "coord": {
        "lon": 12.0562,
        "lat": 49.6323
    },
    "list": [
        {
            "main": {
                "aqi": 2
            },
            "components": {
                "co": 260.35,
                "no": 0.29,
                "no2": 1.89,
                "o3": 104.43,
                "so2": 1.16,
                "pm2_5": 6.38,
                "pm10": 6.96,
                "nh3": 7.79
            },
            "dt": 1647097200
        }
    ]
}
To:
{
  "dateTime" : 1647097200,
  "owm_aqi" : 2,
  "owm_co" : 260.35,
  "owm_no" : 0.29,
  "owm_no2" : 1.89,
  "owm_o3" : 104.43,
  "owm_so2" : 1.16,
  "owm_pm2_5" : 6.38,
  "owm_pm10_0" : 6.96,
  "owm_nh3" : 7.79
}

"""
        if self.log_success or self.verbose:
            loginf('convert json')
        aq = dict()
        try:
            aq['dateTime'] = int(time.time() + 0.5)
            # aq['usUnits'] = 1
            aq['owm_aqi'] = jsondata['list'][0]['main']['aqi']
            aq['owm_co'] = jsondata['list'][0]['components']['co']
            aq['owm_no'] = jsondata['list'][0]['components']['no']
            aq['owm_no2'] = jsondata['list'][0]['components']['no2']
            aq['owm_o3'] = jsondata['list'][0]['components']['o3']
            aq['owm_so2'] = jsondata['list'][0]['components']['so2']
            aq['owm_pm2_5'] = jsondata['list'][0]['components']['pm2_5']
            aq['owm_pm10_0'] = jsondata['list'][0]['components']['pm10']
            aq['owm_nh3'] = jsondata['list'][0]['components']['nh3']
            if self.log_success or self.verbose:
                loginf('Converted JSON:\n%s' % json.dumps(aq,indent=4,ensure_ascii=False))
            return aq
        except Exception as e:
            if self.log_failure or self.verbose:
                logerr(e)
            return None

    def download_openweather_airquality(self):
        """ Download data from AerisWeather Airquality API """
        url = (
            "https://api.openweathermap.org/data/2.5/air_pollution?lat=%s&lon=%s&units=%s&appid=%s"
            % (self.latitude, self.longitude, self.units, self.app_id)
            )

        if self.verbose:
            loginf('API:\n%s' % url)

        headers={'User-Agent':'weewx-OPENWEATHER-AQI'}

        try:
            reply = requests.get(url,headers=headers)
        except ConnectionError as e:
            if self.log_failure or self.verbose:
                logerr(e)
            return None
        
        if reply.status_code==200:
            if self.log_success or self.verbose:
                loginf('successfully downloaded')
            try:
                aq = json.loads(reply.content)
                if self.verbose:
                    loginf('Original JSON:\n%s' % json.dumps(aq,indent=4,ensure_ascii=False))
                return aq
            except Exception as e:
                if self.log_failure or self.verbose:
                    logerr(e)
                return None
        else:
            if self.log_failure or self.verbose:
                logerr('error downloading %s: %s %s' % (reply.url,reply.status_code,reply.reason))
            return None

    def worker_openweather_airquality(self, output):
        """ Worker AerisWeather Airquality """

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

            if self.api_is_stale:
                if self.verbose:
                    loginf('API is stale, download new data.')
                erg = None
                if self.forecast_api_id and self.forecast_api_secret:
                    erg = self.download_openweather_airquality()
                    if erg is None:
                        raise Exception
                else:
                    raise Exception

                erg = self.convert_openweather_airquality(erg)
                if erg is None:
                    raise Exception

                self.write_openweather_airquality_file(fn, erg)
            else:
                if self.verbose:
                    loginf('API is not stale, read last data from file.')
                erg = self.read_openweather_airquality_file(fn)

            if 'mqtt' in output and self.mqtt_enable:
                if erg is None:
                    raise Exception
                self.publish_openweather_airquality(erg)

            if self.verbose:
                loginf('OpenWeatherAirquality finished.')
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
    parser.add_option_group(group)

    # commands
    group = optparse.OptionGroup(parser,"Commands")
    group.add_option("--mqtt", action="store_true", dest='mqtt',
                     help="Publish JSON to MQTT broker")

    parser.add_option_group(group)

    (options, args) = parser.parse_args()

#    if len(args)>0:
#        location = args[0]
#        if not location: location = None
#    else:
#        location = 'Döbeln'
        
    if options.weewx:
        config_path = "/home/weewx/weewx.conf"
    else:
        config_path = options.config_path

    if config_path:
        print("Using configuration file %s" % config_path)
        config = configobj.ConfigObj(config_path)
    else:
        config = {}

    openweather = OpenWeatherAirquality(config,options.verbose)

    output = []
    if options.mqtt: output.append('mqtt')
    
    openweather.worker_openweather_airquality(output)