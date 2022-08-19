#!/usr/bin/python3
# Henry Ott
# based on scripts by Johanna Roedenbeck
# https://github.com/roe-dl

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
#    process Brightsky Weather data                                           #
###############################################################################
        
class BrightskyWeather(object):

    def __init__(self, config_dict, verbose=False):
        # target path
        conf_dict = config_dict['API_Brightsky_Weather']
        self.target_path = conf_dict.get('path', '/tmp')
        self.enable = to_bool(conf_dict.get('enable',False))

        # API config data
        api_dict = config_dict['API_Brightsky_Weather']['API']
        self.wmo_station_id = api_dict.get('wmo_station_id','10688')
        self.current_source_id = int(api_dict.get('current_source_id',6228))
        self.units = api_dict.get('units','dwd')
        self.timezone = api_dict.get('timezone','Europe/Berlin')
        self.station_name = api_dict.get('station_name','Weiden')
        self.station_state = api_dict.get('station_state','de')
        self.station_country = api_dict.get('station_country','by')
        self.api_stale_timer = api_dict.get('stale_timer',3600)
        self.api_is_stale = False

        # Output file config data
        file_dict = config_dict['API_Brightsky_Weather']['FILE']
        self.filename = file_dict.get('filename','brightsky_weather.json')

        # MQTT config data
        mqtt_dict = config_dict['API_Brightsky_Weather']['MQTT']
        self.mqtt_enable = to_bool(mqtt_dict.get('enable',False))
        self.mqtt_server_url = mqtt_dict.get('server_url','mqtt://127.0.0.1:1883')
        self.mqtt_topic = mqtt_dict.get('topic','brightsky/weather')
        self.mqtt_client_id = mqtt_dict.get('client_id','BrightskyWeather')
        self.mqtt_qos = mqtt_dict.get('qos',0)
        self.mqtt_retain = to_bool(mqtt_dict.get('retain',False))
        self.mqtt_connected = False

        # logging
        self.verbose = verbose
        self.log_success = to_bool(config_dict['API_Brightsky_Weather'].get('log_success',config_dict.get('log_success',False)))
        self.log_failure = to_bool(config_dict['API_Brightsky_Weather'].get('log_failure',config_dict.get('log_failure',False)))

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
            belchertown_dict = config_dict['API_Brightsky_Weather'].get('Belchertown',{})
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
        except LookupError:
            belchertown_section = {}
            self.belchertown_html_root = None
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
   
    def publish_brightsky_weather(self, jsondata):
        """ Publish data from Brightsky Weather API to Message Broker """
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

    def read_brightsky_weather_file(self, fn):
        """ Read data from Brightsky Weather API to JSON file """
        try:
            with open(fn, "r") as infile:
                erg = json.load(infile)
            if self.log_success or self.verbose:
                loginf("File '%s' succuessfully read." % fn)
            erg['originalBrightskyWeatherTimestamp'] = erg['dateTime']
            # mod date
            erg['dateTime'] = int(time.time() + 0.5)
            return erg
        except Exception as e:
            if self.log_failure or self.verbose:
                logerr('Error reading file %s: %s' % (fn,e))


    def write_brightsky_weather_file(self, fn, jsondata):
        """ Write data from Brightsky Weather API to JSON file """
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

    def convert_brightsky_weather(self, jsondata):
        """ convert data from Brightsky Weather API 

https://api.brightsky.dev/weather?wmo_station_id=10688&tz=Europe%2FBerlin&units=dwd&date=2022-04-25T11%3A00%2B02%3A00&last_date=2022-04-25T12%3A00%2B02%3A00&source_id=6228

From:
{
    "weather": [
        {
            "timestamp": "2022-04-25T11:00:00+02:00",
            "source_id": 6228,
            "precipitation": 0.3,
            "pressure_msl": 1009.7,
            "sunshine": 0.0,
            "temperature": 7.8,
            "wind_direction": 270,
            "wind_speed": 6.1,
            "cloud_cover": 88,
            "dew_point": 6.3,
            "relative_humidity": 90,
            "visibility": 6400,
            "wind_gust_direction": null,
            "wind_gust_speed": 10.1,
            "condition": "rain",
            "icon": "cloudy"
        }
    ],
    "sources": [
        {
            "id": 6228,
            "dwd_station_id": "05397",
            "observation_type": "current",
            "lat": 49.67,
            "lon": 12.18,
            "height": 438.0,
            "station_name": "WEIDEN",
            "wmo_station_id": "10688",
            "first_record": "2022-04-23T10:00:00+00:00",
            "last_record": "2022-04-25T09:00:00+00:00"
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

    def download_brightsky_weather(self):
        """ Download data from Brightsky Weather API """
        url = (
            "https://api.brightsky.dev/weather?wmo_station_id=%s&tz=%s&units=%s&date=%s&last_date=&s&source_id=%s"
            % (self.wmo_station_id, self.timezone, self.units, start, end, self.current_source_id)
            )

        if self.verbose:
            loginf('API:\n%s' % url)

        headers={'User-Agent':'weewx-BRIGHTSKY-WEATHER'}

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

    def worker_brightsky_weather(self, output):
        """ Worker Brightsky Weather """

        if not self.enable:
            loginf('Module disabled, skipping execution.')
            return

        if self.verbose:
            loginf('what to output: %s' % output)

        try:
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

                erg = self.download_brightsky_weather()
                if erg is None:
                    raise Exception

                erg = self.convert_brightsky_weather(erg)
                if erg is None:
                    raise Exception

                self.write_brightsky_weather_file(fn, erg)
            else:
                if self.verbose:
                    loginf('API is not stale, read last data from file.')
                erg = self.read_brightsky_weather_file(fn)
                if erg is None:
                    raise Exception

            if 'mqtt' in output and self.mqtt_enable:
                self.publish_brightsky_weather(erg)

            if self.verbose:
                loginf('BrightskyWeather finished.')
        except Exception as e:
            if self.log_failure or self.verbose:
                logerr(e)

if __name__ == "__main__":

    usage = None

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

    if options.verbose is None:
       options.verbose = False

    if options.weewx:
        config_path = "/home/weewx/weewx.conf"
    else:
        config_path = options.config_path

    if config_path:
        print("Using configuration file %s" % config_path)
        config = configobj.ConfigObj(config_path)
    else:
        config = {}

    brightsky = BrightskyWeather(config,options.verbose)

    output = []
    if options.mqtt: output.append('mqtt')
    
    brightsky.worker_brightsky_weather(output)