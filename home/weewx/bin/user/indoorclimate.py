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
"""
import syslog
from datetime import datetime
import time
import weewx
from weewx.wxengine import StdService
from weeutil.weeutil import to_bool, to_int, to_float

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

VERSION = "0.1"

DEFAULTS_INI = """
[IndoorClimate]
    enable = true
    debug = 0
    [[livingroom]]
        [[[temperature]]]
            observation = inTemp
            unit = degree_C
            min = 20.0
            max = 23.0
        [[[humidity]]]
            observation = inHumidity
            min = 40.0
            max = 60.0
    [[office]]
        [[[temperature]]]
            observation = extraTemp1
            unit = degree_C
            min = 20.0
            max = 23.0
        [[[humidity]]]
            observation = extraHumid1
            min = 40.0
            max = 60.0
    [[bathroom]]
        [[[temperature]]]
            observation = extraTemp2
            unit = degree_C
            min = 20.0
            max = 23.0
        [[[humidity]]]
            observation = extraHumid2
            min = 50.0
            max = 70.0
    [[bedroom]]
        [[[temperature]]]
            observation = extraTemp3
            unit = degree_C
            min = 17.0
            max = 20.0
        [[[humidity]]]
            observation = extraHumid3
            min = 40.0
            max = 60.0
"""
defaults_dict = weeutil.config.config_from_str(DEFAULTS_INI)

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
        self.debug = to_int(self.option_dict['debug'])
        loginf("debug level is %d" % self.debug)

        # Start intercepting events:
        self.bind(weewx.NEW_LOOP_PACKET, self.newLoopPacket)

    def newLoopPacket(self, event):
        """Gets called on a new loop packet event."""
        if self.debug > 1:
            logdbg("incomming loop packet: %s" % str(event.packet))
        target_data = {}
        for room, room_dict in self.option_dict.items():
            if isinstance(room_dict, dict):
                room_opt = None
                for check, check_dict in room_dict.items():
                    if isinstance(check_dict, dict):
                        check_obs = check_dict.get('observation')
                        if check_obs is not None:
                            check_unit = check_dict.get('unit')
                            if check_unit is not None:
                                obs_vt = weewx.units.as_value_tuple(event.packet, check_obs)
                                if check_unit != obs_vt[1]:
                                    check_val = weewx.units.convert(obs_vt,check_unit)[0]
                                else:
                                    check_val = obs_vt[0]
                            else:
                                check_val = to_float(event.packet.get(check_obs))
                            if check_val is not None:
                                check_min = to_float(check_dict.get('min'))
                                check_max = to_float(check_dict.get('max'))
                                if check_min is not None and check_max is not None:
                                    check_opt = 1 if check_val >= check_min and check_val <= check_max else 0
                                    res_key = str(room) + '_' + str(check) + '_opt'
                                    target_data[res_key] = check_opt
                                    if room_opt is None:
                                        room_opt = check_opt
                                    else:
                                        room_opt = check_opt if check_opt < room_opt else room_opt
                                    if self.debug > 0:
                                        logdbg("room=%s check=%s obs=%s val=%.2f optimal=%s" % (str(room), str(check), str(check_obs), check_val, ('YES' if check_opt > 0 else 'NO')))
                if room_opt is not None:
                    res_key = str(room) + '_opt'
                    target_data[res_key] = room_opt
                    if self.debug > 0:
                        logdbg("room=%s optimal=%s" % (str(room), ('YES' if room_opt > 0 else 'NO')))

        # add to LOOP
        event.packet.update(target_data)
        if self.debug > 1:
            logdbg("outgoing loop packet: %s" % str(event.packet))
