"""
    Copyright (C) 2022 Henry Ott

    based on code from https://github.com/Jterrettaz/sunduration

    Determination of some values to better compare current weather
    conditions delivered via an API with local conditions.

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

VERSION = "0.3.1"

import syslog
import ast
from math import sin, cos, pi, asin
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
        syslog.syslog(level, 'sunshineduration: %s' % msg)

    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)

class SunshineDuration(StdService):
    def __init__(self, engine, config_dict):
        # Pass the initialization information on to my superclass:
        super(SunshineDuration, self).__init__(engine, config_dict)
        loginf("Service version is %s" % VERSION)

        # extension defaults
        enable = True
        self.debug = 0
        self.radiation_min = 0.0
        self.add_sunshine_to_loop = False

        # optional customizations by the user.
        cust_dict = config_dict.get('SunshineDuration', {})
        enable = to_bool(cust_dict.get('enable', enable))
        if enable:
            loginf("Service is enabled.")
        else:
            loginf("Service is disabled. Enable it in the SunshineDuration section of weewx.conf.")
            return
        self.debug = to_int(cust_dict.get('debug', self.debug))
        loginf("debug level is %d" % self.debug)
        self.radiation_min = to_float(cust_dict.get('radiation_min', self.radiation_min))
        loginf("radiation min threshold is %.2f" % self.radiation_min)
        self.add_sunshine_to_loop = to_bool(cust_dict.get("add_sunshine_to_loop", self.add_sunshine_to_loop))
        loginf("add_sunshine_to_loop is %s" % ("True" if self.add_sunshine_to_loop else "False"))

        # last dateTime loop package with valid 'radiation'
        self.lastdateTime = 0
        # sum sunshineDur within archiv interval
        self.sunshineDur = 0

        # Start intercepting events:
        self.bind(weewx.NEW_LOOP_PACKET, self.newLoopPacket)
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.newArchiveRecord)

    def newLoopPacket(self, event):
        """Gets called on a new loop packet event."""
        radiation = event.packet.get('radiation')
        if radiation is not None:
            loopdateTime = event.packet.get('dateTime')
            if self.lastdateTime == 0:
                # It's the first LOOP packet, more is not to be done
                # To calculate the time we wait for the next loop packet
                self.lastdateTime = loopdateTime
            else:
                loopDuration = loopdateTime - self.lastdateTime
                self.lastdateTime = event.packet.get('dateTime')
                if radiation >= self.radiation_min:
                    threshold = event.packet.get('sunshineThreshold')
                    if threshold is None:
                        logerr("Loop calculation not possible, sunshineThreshold not present!")
                        raise weewx.CannotCalculate('sunshineDur')
                    loopSunshineDur = 0
                    sunshine = 0
                    if threshold > 0.0 and radiation > threshold:
                        loopSunshineDur = loopDuration
                        sunshine = 1
                    self.sunshineDur += loopSunshineDur
                    if self.debug >= 1:
                        logdbg("Loop sunshineDur=%d, based on radiation=%.2f threshold=%.2f loopDuration=%d loopSunshineDur=%d" % (
                            self.sunshineDur, radiation, threshold, loopDuration, loopSunshineDur))
                    if self.add_sunshine_to_loop:
                        target_data = {}
                        target_data['sunshine'] = sunshine
                        # add sunshine to LOOP
                        event.packet.update(target_data)
                elif self.debug >= 1:
                    logdbg("Loop calculation not done because radiation=%.2f is lower than radiation_min=%.2f" % (
                        radiation, self.radiation_min))

    def newArchiveRecord(self, event):
        """Gets called on a new archive record event."""
        target_data = {}
        target_data['sunshineDur'] = 0.0
        if self.lastdateTime == 0:
            # LOOP packets with 'radiation' not yet captured
            radiation = event.record.get('radiation')
            if radiation is not None:
                if radiation >= self.radiation_min:
                    # We assume here that the radiation is an average value over the whole archive period.
                    # If this value is higher than the threshold value, we assume that the sun shone during
                    # the whole archive interval.
                    archivInterval = event.record.get('interval') * 60 # seconds
                    threshold = event.record.get('sunshineThreshold')
                    if threshold is None:
                        logerr("Archiv calculation not possible, sunshineThreshold not present!")
                        raise weewx.CannotCalculate('sunshineDur')
                    if threshold > 0.0 and radiation > threshold:
                        target_data['sunshineDur'] = archivInterval 
                    if self.debug >= 1:
                        loginf("Archiv sunshineDur=%d, based on radiation=%.2f threshold=%.2f archivInterval=%d" % (
                            target_data['sunshineDur'], radiation, threshold, archivInterval))
                elif self.debug >= 1:
                    logdbg("Archiv calculation not done because radiation=%.2f is lower than radiation_min=%.2f" % (
                        radiation, self.radiation_min))
            else:
                logerr("Archiv Calculation not possible, radiation not present!")
                raise weewx.CannotCalculate('sunshineDur')
        else:
            # sum from loop packets
            target_data['sunshineDur']  = self.sunshineDur
            if self.debug >= 1:
                loginf("Archiv sunshineDur=%d, based on loop packets." % (target_data['sunshineDur']))

        event.record.update(target_data)
        # reset internal sum
        self.sunshineDur = 0
