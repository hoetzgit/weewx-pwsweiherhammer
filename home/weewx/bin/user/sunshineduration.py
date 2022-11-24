"""
    Copyright (C) 2022 Henry Ott

    based on code from https://github.com/Jterrettaz/sunduration

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
        syslog.syslog(level, 'sunshineduration: %s' % msg)

    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)

VERSION = "0.2"

class SunshineDuration(StdService):
    def __init__(self, engine, config_dict):
        # Pass the initialization information on to my superclass:
        super(SunshineDuration, self).__init__(engine, config_dict)
        loginf("Service version is %s" % VERSION)

        cust_dict = config_dict.get('SunshineDurationWeiherhammer', {})
        enable = to_bool(cust_dict.get('enable', True))
        if enable:
            loginf("Service is enabled.")
        else:
            loginf("Service is disabled. Enable it in the SunshineDurationWeiherhammer section of weewx.conf.")
            return

        # extension defaults
        self.debug = 0
        self.radiation_min = 0.0

        # optional customizations by the user.
        self.debug = to_int(cust_dict.get('debug', self.debug))
        loginf("debug level is %d" % self.debug)
        self.radiation_min = to_float(cust_dict.get('radiation_min', self.radiation_min))
        loginf("radiation min threshold is %.2f" % self.radiation_min)

        # dateTime from the last loop package with valid 'radiation'
        self.lastLoop = 0
        # dateTime from the last archiv record
        self.lastArchiv = 0
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

            if self.lastLoop == 0:
                # It's the first loop packet, more is not to be done
                # To calculate the time we wait for the next loop packet
                # ..L
                if self.debug > 0:
                    logdbg("first loop packet with 'radiation' during archiv interval received.")
            elif radiation >= self.radiation_min:
                # .L..L..L..L
                threshold = event.packet.get('sunshineThreshold')
                if threshold is not None:
                    loopDuration = loopdateTime - self.lastLoop
                    loopSunshineDur = 0
                    if threshold > 0.0 and radiation > threshold:
                        loopSunshineDur = loopDuration
                    self.sunshineDur += loopSunshineDur
                    if self.debug > 0:
                        logdbg("LOOP sunshineDur=%d, based on threshold=%.2f radiation=%.2f loopDuration=%d loopSunshineDur=%d" % (
                            self.sunshineDur, threshold, radiation, loopDuration, loopSunshineDur))
                else:
                    logerr("LOOP no calculation, sunshineThreshold not present!")
            elif self.debug > 0:
                logdbg("LOOP no calculation, radiation=%.2f lower than radiation_min=%.2f" % (radiation, self.radiation_min))

            self.lastLoop = loopdateTime

    def newArchiveRecord(self, event):
        """Gets called on a new archive record event."""
        target_data = {}
        target_data['sunshineDur'] = 0.0
        archivedateTime = event.record.get('dateTime')

        if self.lastArchiv > 0 and self.lastLoop > 0 and self.lastLoop < self.lastArchiv:
            # no loop packets with 'radiation' during the last archiv interval
            # .L..L..L..L..A..........A
            if self.debug > 0:
                logdbg("No loop packets with 'radiation' during the last archiv interval, disacard loop indicator.")
            self.lastLoop = 0

        self.lastArchiv = archivedateTime

        if self.lastLoop == 0:
            # loop packets with 'radiation' not yet captured
            # ...A..........A
            radiation = event.record.get('radiation')
            if radiation is not None:
                if radiation >= self.radiation_min:
                    # We assume here that the radiation is an average value over the whole archive period.
                    # If this value is higher than the threshold value, we assume that the sun shone during
                    # the whole archive interval.
                    threshold = event.record.get('sunshineThreshold')
                    if threshold is not None:
                        interval = event.record.get('interval') * 60 # seconds
                        if threshold > 0.0 and radiation > threshold:
                            target_data['sunshineDur'] = interval
                        if self.debug > 0:
                            logdbg("ARCHIV sunshineDur=%d, based on threshold=%.2f radiation=%.2f interval=%d" % (
                                target_data['sunshineDur'], threshold, radiation, interval))
                    else:
                        logerr("ARCHIV no calculation, sunshineThreshold not present!")
                else:
                    if self.debug > 1:
                        logdbg("ARCHIV no calculation, radiation=%.2f lower than radiation_min=%.2f" % (radiation, self.radiation_min))
        else:
            # sum from loop packets
            # .L..L..L..L..L..A
            target_data['sunshineDur'] = self.sunshineDur
            if self.debug > 0:
                logdbg("ARCHIV sunshineDur=%d, based on loop packets." % (target_data['sunshineDur']))

        event.record.update(target_data)
        # reset internal sum
        self.sunshineDur = 0
