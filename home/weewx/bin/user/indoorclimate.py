"""
    Copyright (C) 2022 Henry Ott

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

    Threshold values:
    https://www.tfa-dostmann.de/luftfeuchtigkeit/?utm_source=pocket_saves
"""
import syslog
from datetime import datetime
import time

import weewx
from weewx.wxengine import StdService
from weeutil.weeutil import to_bool, to_int, to_float, to_list

try:
    # Test for new-style weewx logging by trying to import weeutil.logger
    import weeutil.logger
    import logging
    log = logging.getLogger(__name__)

    def logdbg(msg):
        log.debug(msg)

    def loginf(msg):
        log.info(msg)

    def logerr(msg):
        log.error(msg)

except ImportError:
    # Old-style weewx logging
    import syslog

    def logmsg(level, msg):
        syslog.syslog(level, 'indoorclimate: %s' % msg)

    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)

DEFAULTS_INI = """
[IndoorClimate]
    enable = true
    debug = 0
    [[temperature]]
        unit = degree_C
        observation = inTemp
        level = -2, -1, 0, 1, 2
        level_opt = 0
        # Temperatur (Wohnzimmer, Arbeitszimmer)
        # -2 = sehr kalt  = blau     = #0000FF = <=12
        # -1 = kalt       = hellblau = #0088FF = <=20
        #  0 = optimal    = grün     = #84D862 = <=22
        # +1 = warm       = orange   = #FF8800 = <=30
        # +2 = sehr warm  = rot      = #FF0000 = <=70
        max = 12, 20, 22, 30, 70
        color = #0000FF, #0088FF, #84D862, #FF8800, #FF0000
        name = very cold, cold, optimal, warm, very warm
        action = heating, heating, nothing to do, cool, cool
    [[humidity]]
        observation = inHumidity
        level = -2, -1, 0, 1, 2
        level_opt = 0
        # Luftfeuchte (Wohnzimmer, Arbeitszimmer, Schlafzimmer)
        # -2 = sehr trocken = orange    = #FF8800 = <=35
        # -1 = trocken      = hellgrün  = #B2DF8A = <=40
        #  0 = optimal      = grün      = #84D862 = <=60
        # +1 = feucht       = hellgrün  = #B2DF8A = <=65
        # +2 = sehr feucht  = blau      = #0077FF = <=100
        max = 35, 40, 60, 65, 100
        color = #FF8800, #B2DF8A, #84D862, #B2DF8A, #0077FF
        name = very dry, dry, optimal, moist, very moist
        action = humidify, humidify, nothing to do, airing, airing
    [[rooms]]
        level = 0, 1
        level_opt = 0
        color = #84D862, #FF0000
        name = optimal, action required
        action = nothing to do, action required
        [[[livingroom]]]
        [[[office]]]
            [[[[temperature]]]]
                observation = extraTemp1
            [[[[humidity]]]]
                observation = extraHumid1
        [[[bathroom]]]
            [[[[temperature]]]]
                observation = extraTemp2
                # Temperatur (Bad)
                # -2 = sehr kalt  = blau     = #0000FF = <=15
                # -1 = kalt       = hellblau = #0088FF = <=20
                #  0 = optimal    = grün     = #84D862 = <=23
                # +1 = warm       = orange   = #FF8800 = <=30
                # +2 = sehr warm  = rot      = #FF0000 = <=70
                max = 15, 20, 23, 30, 70
            [[[[humidity]]]]
                observation = extraHumid2
                # Luftfeuchte (Bad)
                # -2 = sehr trocken = orange    = #FF8800 = <=40
                # -1 = trocken      = hellgrün  = #B2DF8A = <=50
                #  0 = optimal      = grün      = #84D862 = <=70
                # +1 = feucht       = hellgrün  = #B2DF8A = <=80
                # +2 = sehr feucht  = blau      = #0077FF = <=100
                max = 40, 50, 70, 80, 100
        [[[bedroom]]]
            [[[[temperature]]]]
                observation = extraTemp3
                # Temperatur (Schlafzimmer)
                # -2 = sehr kalt  = blau     = #0000FF = <=10
                # -1 = kalt       = hellblau = #0088FF = <=16
                #  0 = optimal    = grün     = #84D862 = <=18
                # +1 = warm       = orange   = #FF8800 = <=25
                # +2 = sehr warm  = rot      = #FF0000 = <=70
                max = 10, 16, 18, 25, 70
            [[[[humidity]]]]
                observation = extraHumid3
"""
defaults_dict = weeutil.config.config_from_str(DEFAULTS_INI)

VERSION = "0.1"

class IndoorClimate(StdService):
    def __init__(self, engine, config_dict):
        super(IndoorClimate, self).__init__(engine, config_dict)
        log.info("Service version is %s." % VERSION)

        # Get any user-defined overrides
        override_dict = config_dict.get('IndoorClimate', {})
        # Get the default values, then merge the user overrides into it
        self.option_dict = weeutil.config.deep_copy(defaults_dict['IndoorClimate'])
        self.option_dict.merge(override_dict)

        # Only continue if the plugin is enabled.
        enable = to_bool(self.option_dict['enable'])
        if enable:
            loginf("IndoorClimate is enabled...continuing.")
        else:
            loginf("IndoorClimate is disabled. Enable it in the IndoorClimate section of weewx.conf.")
            return
        self.debug = to_int(self.option_dict.get('debug', 0))
        if self.debug > 0:
            logdbg("debug level is %d" % self.debug)

        # defaults
        self.temp_dict = self.option_dict.get('temperature', {})
        self.humid_dict = self.option_dict.get('humidity', {})

        # Start intercepting events:
        self.bind(weewx.NEW_LOOP_PACKET, self.newLoopPacket)

    def newLoopPacket(self, event):
        """Gets called on a new loop packet event."""
        if self.debug >= 3:
            logdbg("incomming loop packet: %s" % str(event.packet))

        target_data = {}
        for room, room_dict in self.option_dict['rooms'].items():
            if isinstance(room_dict, dict):
                # temperature
                tqi = tqi_key = obs_val = None
                room_temp_dict = self.temp_dict
                room_temp_dict.merge(room_dict.get('temperature', {}))
                tqi_opt = room_temp_dict.get('level_opt', 0)
                obs = room_temp_dict.get('observation')
                if obs in event.packet:
                    unit = room_temp_dict.get('unit')
                    if unit is not None:
                        obs_vt = weewx.units.as_value_tuple(event.packet, obs)
                        if unit != obs_vt[1]:
                            obs_val = weewx.units.convert(obs_vt, unit)[0]
                        else:
                            obs_val = obs_vt[0]
                    else:
                        obs_val = event.packet[obs]
                    max_lst = to_list(room_temp_dict.get('max'))
                    level_lst = to_list(room_temp_dict.get('level'))
                    for i in range(len(max_lst)):
                        if to_float(obs_val) <= to_float(max_lst[i]):
                            tqi = level_lst[i]
                            tqi_key = i
                            break

                # loop room temperature quality result
                target_data[str(room) + '_tqi'] = tqi

                if tqi is not None:
                    name_lst = to_list(room_temp_dict.get('name'))
                    action_lst = to_list(room_temp_dict.get('action'))
                    tqi_name = name_lst[tqi_key]
                    tqi_action = action_lst[tqi_key]
                    obs_val = ("%.2f" % obs_val) # debug
                else:
                    tqi = 'N/A'
                    tqi_name = 'N/A'
                    tqi_action = 'N/A'
                    obs_val = 'N/A'

                if self.debug >= 2:
                    logdbg("room=%s temperature=%s level=%s name=%s action=%s" % (str(room), str(obs_val), str(tqi), tqi_name, tqi_action))

                # Humidity
                hqi = hqi_key = obs_val = None
                room_humid_dict = self.humid_dict
                room_humid_dict.merge(room_dict.get('humidity', {}))
                hqi_opt = room_humid_dict.get('level_opt', 0)
                obs = room_humid_dict.get('observation')
                if obs in event.packet:
                    unit = room_humid_dict.get('unit')
                    if unit is not None:
                        obs_vt = weewx.units.as_value_tuple(event.packet, obs)
                        if unit != obs_vt[1]:
                            obs_val = weewx.units.convert(obs_vt, unit)[0]
                        else:
                            obs_val = obs_vt[0]
                    else:
                        obs_val = event.packet[obs]
                    max_lst = to_list(room_humid_dict.get('max'))
                    level_lst = to_list(room_humid_dict.get('level'))
                    for i in range(len(max_lst)):
                        if to_float(obs_val) <= to_float(max_lst[i]):
                            hqi = level_lst[i]
                            hqi_key = i
                            break

                # loop room humidity quality result
                target_data[str(room) + '_hqi'] = hqi

                if hqi is not None:
                    name_lst = to_list(room_humid_dict.get('name'))
                    action_lst = to_list(room_humid_dict.get('action'))
                    hqi_name = name_lst[hqi_key]
                    hqi_action = action_lst[hqi_key]
                    obs_val = ("%d" % obs_val) # debug
                else:
                    hqi = 'N/A'
                    hqi_name = 'N/A'
                    hqi_action = 'N/A'
                    obs_val = 'N/A'

                if self.debug >= 2:
                    logdbg("room=%s humidity=%s level=%s name=%s action=%s" % (str(room), obs_val, str(hqi), hqi_name, hqi_action))

                # room quality index
                rqi = rqi_key = None
                if tqi is not None and hqi is not None:
                    level_lst = to_list(self.option_dict['rooms'].get('level'))
                    rqi_opt = self.option_dict['rooms'].get('level_opt', 0)

                    for i in range(len(level_lst)):
                        if tqi != tqi_opt or hqi != hqi_opt:
                            if level_lst[i] != rqi_opt:
                                rqi = level_lst[i]
                                rqi_key = i
                                break
                        elif level_lst[i] == rqi_opt:
                            rqi = level_lst[i]
                            rqi_key = i
                            break

                # loop room quality result
                target_data[str(room) + '_rqi'] = rqi

                if rqi is not None:
                    name_lst = to_list(self.option_dict['rooms'].get('name'))
                    action_lst = to_list(self.option_dict['rooms'].get('action'))
                    rqi_name = name_lst[rqi_key]
                    rqi_action = action_lst[rqi_key]
                else:
                    rqi = 'N/A'
                    rqi_name = 'N/A'
                    rqi_action = 'N/A'

                if self.debug >= 2:
                    logdbg("room=%s level=%s name=%s action=%s" % (str(room), str(rqi), rqi_name, rqi_action))

        # add to LOOP
        event.packet.update(target_data)
        if self.debug >= 3:
            logdbg("outgoing loop packet: %s" % str(event.packet))
