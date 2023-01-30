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
import weewx.units
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
        syslog.syslog(level, 'roomclimate: %s' % msg)

    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)

DEFAULTS_INI = """
[roomclimate]
    enable = true
    debug = 2
    [[observations]]
        [[[inTemp]]]
            unit = degree_C
            group = temperature
            location = livingroom
            threshold = 12, 20, 23, 30, 70
        [[[extraTemp1]]]
            unit = degree_C
            group = temperature
            location = office
            threshold = 12, 20, 23, 30, 70
        [[[extraTemp2]]]
            unit = degree_C
            group = temperature
            location = bathroom
            threshold = 15, 20, 24, 30, 70
        [[[extraTemp3]]]
            unit = degree_C
            group = temperature
            location = bedroom
            threshold = 10, 16, 19, 25, 70
        [[[inHumidity]]]
            unit = percent
            group = humidity
            location = livingroom
            threshold = 35, 40, 61, 65, 100
        [[[extraHumid1]]]
            unit = percent
            group = humidity
            location = office
            threshold = 35, 40, 61, 65, 100
        [[[extraHumid2]]]
            unit = percent
            group = humidity
            location = bathroom
            threshold = 40, 50, 71, 80, 100
        [[[extraHumid3]]]
            unit = percent
            group = humidity
            location = bedroom
            threshold = 35, 40, 61, 65, 100
    [[group]]
        [[[temperature]]]
            level = -2, -1, 0, 1, 2
            level_optimal = 0
            color = "#0000FF", "#0088FF", "#84D862", "#FF8800", "#FF0000"
            name = very cold, cold, optimal, warm, very warm
            action = heating, heating, nothing to do, cool, cool
        [[[humidity]]]
            level = -2, -1, 0, 1, 2
            level_optimal = 0
            color = "#FF8800", "#B2DF8A", "#84D862", "#B2DF8A", "#0077FF"
            name = very dry, dry, optimal, moist, very moist
            action = humidify, humidify, nothing to do, airing, airing
        [[[room]]]
            level = 0, 1
            level_optimal = 0
            color = "#84D862", "#FF0000"
            name = optimal, action required
            action = nothing to do, action required
"""
defaults_dict = weeutil.config.config_from_str(DEFAULTS_INI)

# unit system new observations
# xxx_tqi = Temperature Quality Index
# xxx_hqi = Humidity Quality Index
# xxx_rqi = Room Quality Index
weewx.units.obs_group_dict['bathroom_tqi'] = "group_count"
weewx.units.obs_group_dict['bathroom_hqi'] = "group_count"
weewx.units.obs_group_dict['bathroom_rqi'] = "group_count"
weewx.units.obs_group_dict['bedroom_tqi'] = "group_count"
weewx.units.obs_group_dict['bedroom_hqi'] = "group_count"
weewx.units.obs_group_dict['bedroom_rqi'] = "group_count"
weewx.units.obs_group_dict['livingroom_tqi'] = "group_count"
weewx.units.obs_group_dict['livingroom_hqi'] = "group_count"
weewx.units.obs_group_dict['livingroom_rqi'] = "group_count"
weewx.units.obs_group_dict['office_tqi'] = "group_count"
weewx.units.obs_group_dict['office_hqi'] = "group_count"
weewx.units.obs_group_dict['office_rqi'] = "group_count"

def list_get (l, idx, default):
    try:
        return l[idx]
    except IndexError:
        return default

VERSION = "0.2"

class RoomClimate(StdService):
    def __init__(self, engine, config_dict):
        super(RoomClimate, self).__init__(engine, config_dict)
        log.info("Service version is %s." % VERSION)

        # Get any user-defined overrides
        override_dict = config_dict.get('roomclimate', {})
        # Get the default values, then merge the user overrides into it
        self.option_dict = weeutil.config.deep_copy(defaults_dict['roomclimate'])
        self.option_dict.merge(override_dict)

        # Only continue if the plugin is enabled.
        enable = to_bool(self.option_dict['enable'])
        if enable:
            loginf("RoomClimate is enabled...continuing.")
        else:
            loginf("Roomclimate is disabled. Enable it in the [roomclimate] section of weewx.conf.")
            return
        self.debug = to_int(self.option_dict.get('debug', 0))
        if self.debug > 0:
            logdbg("debug level is %d" % self.debug)
        if self.debug >= 3:
            logdbg("RoomClimate conf is %s" % str(self.option_dict))

        # Start intercepting events:
        self.bind(weewx.NEW_LOOP_PACKET, self.newLoopPacket)

    def newLoopPacket(self, event):
        """Gets called on a new loop packet event."""
        if self.debug >= 3:
            logdbg("incomming loop packet: %s" % str(event.packet))

        target_data = {}
        result_dict = dict()
        for obs, obs_dict in self.option_dict['observations'].items():
            if obs in event.packet:
                unit = obs_dict.get('unit')
                if unit is not None:
                    obs_vt = weewx.units.as_value_tuple(event.packet, obs)
                    if unit != obs_vt[1]:
                        obs_val = weewx.units.convert(obs_vt, unit)[0]
                    else:
                        obs_val = obs_vt[0]
                else:
                    obs_val = event.packet[obs]
                threshold_lst = obs_dict.get('threshold')
                group = obs_dict.get('group')
                room = obs_dict.get('location')
                if threshold_lst is not None and group is not None and room is not None:
                    for i in range(len(threshold_lst)):
                        if to_float(obs_val) < to_float(threshold_lst[i]):
                            if group == 'temperature':
                                # room temperature quality index
                                tqi = list_get(self.option_dict['group']['temperature']['level'], i, -99)
                                tqi_key = i
                                target_data[room + '_tqi'] = tqi
                            if group == 'humidity':
                                # room humidity quality index
                                hqi = list_get(self.option_dict['group']['humidity']['level'], i, -99)
                                hqi_key = i
                                target_data[room + '_hqi'] = hqi
                            break
                    if result_dict.get(room) is None:
                        result_dict[room] = dict()
                    if result_dict[room].get('tqi') is None:
                        result_dict[room]['tqi'] = tqi
                        result_dict[room]['tqi_key'] = tqi_key
                    if result_dict[room].get('hqi') is None:
                        result_dict[room]['hqi'] = tqi
                        result_dict[room]['hqi_key'] = tqi_key

        tqi_opt = self.option_dict['group']['temperature'].get('level_optimal', 0)
        hqi_opt = self.option_dict['group']['humidity'].get('level_optimal', 0)
        rqi_opt = self.option_dict['group']['room'].get('level_optimal', 0)
        level_lst = to_list(self.option_dict['group']['room'].get('level'))

        if level_lst is not None:
            for room, room_dict in result_dict.items():
                # room quality index
                rqi = rqi_key = None
                tqi = result_dict[room].get('tqi')
                hqi = result_dict[room].get('tqi')
                if tqi is not None and hqi is not None:
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

        # add to LOOP
        event.packet.update(target_data)
        if self.debug >=2:
            logdbg("outgoing loop data: %s" % str(target_data))
        if self.debug >= 3:
            logdbg("outgoing loop packet: %s" % str(event.packet))
