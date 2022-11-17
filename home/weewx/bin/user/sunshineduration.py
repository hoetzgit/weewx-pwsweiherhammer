"""
    Copyright (C) 2022 Henry Ott

    this weewx extension is based on code from https://github.com/Jterrettaz/sunduration

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

VERSION = "0.2"

import syslog
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

        sunshineduration_dict = config_dict.get('SunshineDuration', {})
        enable = to_bool(sunshineduration_dict.get('enable', 'false'))
        if enable:
            loginf("Service is enabled.")
        else:
            loginf("Service is disabled. Enable it in the CurrentHelper section of weewx.conf.")
            return

        self.radiation_min = to_int(sunshineduration_dict.get("radiation_min", 50))
        self.debug = to_int(sunshineduration_dict.get("debug", config_dict.get("debug", 0)))
        self.lastDate = 0
        self.sunshineDur = 0
        self.sunshineDurMonth = 0
        self.sunshineDurOriginal = 0

        loginf("Radiation min is %d" % self.radiation_min)

        # Start intercepting events:
        self.bind(weewx.NEW_LOOP_PACKET, self.newLoopPacket)
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.newArchiveRecord)


    def newLoopPacket(self, event):
        """Gets called on a new loop packet event."""
        radiation = event.packet.get('radiation', None)
        if radiation is None:
            logerr("Calculation LOOP sunshineDur not possible, radiation not present!")
            return None
        loopDate = event.packet.get('dateTime', None)
        if loopDate is None:
            logerr("Calculation LOOP sunshineDur not possible, dateTime not present!")
            return None
        loopInterval = 0
        stationInterval = event.packet.get('foshk_interval', None)
        if stationInterval is not None:
            loopInterval = stationInterval
            self.lastDate = loopDate
        elif self.lastDate > 0 and loopDate is not None:
            loopInterval = loopDate - self.lastDate
            self.lastDate = loopDate
        else:
            logerr("Calculation LOOP sunshineDur not possible, interval could not be determined!")
            return None

        # Calculation LOOP sunshineDur
        # Version with static coeff over the year
        loopSunshineDur = 0
        threshold = event.packet.get('sunshineThreshold', None)
        if threshold is None:
            logerr("Calculation LOOP sunshineDur not possible, sunshineThreshold not present!")
        else:
            if threshold > 0 and radiation > threshold and radiation > self.radiation_min:
                loopSunshineDur = to_int(loopInterval)
        self.sunshineDur += loopSunshineDur
        if self.debug >= 1:
            logdbg("Version 1: LOOP dateTime=%d interval=%d threshold=%.2f radiation=%.2f LOOP sunshineDur=%d" % (
                loopDate, loopInterval, threshold, radiation, int(self.sunshineDur)))

        # Original Version
        # https://github.com/Jterrettaz/sunduration
        # https://github.com/hoetzgit/sunduration/tree/sunshineDur_seconds
        loopSunshineDur = 0
        threshold = event.packet.get('sunshineThresholdOriginal', None)
        if threshold is None:
            logerr("Calculation LOOP sunshineDurOriginal not possible, sunshineThresholdOriginal not present!")
        else:
            if threshold > 0 and radiation > threshold:
                loopSunshineDur = to_int(loopInterval)
        self.sunshineDurOriginal += loopSunshineDur
        if self.debug >= 1:
            logdbg("Version 2: LOOP dateTime=%d interval=%d threshold=%.2f radiation=%.2f LOOP sunshineDur=%d" % (
                loopDate, loopInterval, threshold, radiation, int(self.sunshineDur)))

        # Calculation LOOP sunshineDur
        # Version with coeff per month
        loopSunshineDur = 0
        threshold = event.packet.get('sunshineThresholdMonth', None)
        if threshold is None:
            logerr("Calculation LOOP sunshineDurMonth not possible, sunshineThresholdMonth not present!")
        else:
            if threshold > 0 and radiation > threshold and radiation > self.radiation_min:
                loopSunshineDur = to_int(loopInterval)
        self.sunshineDurMonth += loopSunshineDur
        if self.debug >= 1:
            logdbg("Version 3: LOOP dateTime=%d interval=%d threshold=%.2f radiation=%.2f LOOP sunshineDur=%d" % (
                loopDate, loopInterval, threshold, radiation, int(self.sunshineDur)))


    def newArchiveRecord(self, event):
        """Gets called on a new archive record event."""
        target_data = {}
        target_data['sunshineDur'] = to_int(self.sunshineDur)
        target_data['sunshineDurOriginal'] = to_int(self.sunshineDurOriginal)
        target_data['sunshineDurMonth'] = to_int(self.sunshineDurMonth)
        event.record.update(target_data)
        self.sunshineDur = 0
        self.sunshineDurOriginal = 0
        self.sunshineDurMonth = 0
        if self.debug >= 1:
            logdbg("Version 1: ARCHIVE sunshineDur=%d" % (event.record['sunshineDur']))
            logdbg("Version 2: ARCHIVE sunshineDurOriginal=%d" % (event.record['sunshineDurOriginal']))
            logdbg("Version 3: ARCHIVE sunshineDurMonth=%d" % (event.record['sunshineDurMonth']))