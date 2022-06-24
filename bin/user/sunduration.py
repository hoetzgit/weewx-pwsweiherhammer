import syslog
from math import sin, cos, pi, asin
from datetime import datetime
import time
import weewx
from weewx.wxengine import StdService
from weeutil.weeutil import to_bool
from collections import deque
import schemas.wview

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
        syslog.syslog(level, 'sunduration: %s' % msg)

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

        # Start intercepting events:
        self.bind(weewx.NEW_LOOP_PACKET, self.newLoopPacket)
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.newArchiveRecord)
        self.lastDate = 0
        self.sunshineDur = 0
        self.sunshineDurOriginal = 0
        self.sunshineObs = deque(maxlen=(int(10*60/int(16)))) # 10 minutes sunshine oberservations
        self.debug = to_bool(self.config_dict["debug"])

    def avgSunshine(self):
       s = 0
       a = 0
       l = len(self.sunshineObs)
       if l > 0:
           for i in range(l):
               s = s + self.sunshineObs[i]
           a = round(s/l,2)
       return a

    def newLoopPacket(self, event):
        """Gets called on a new loop packet event."""
        radiation = event.packet.get('radiation')
        if radiation is None:
            logerr("Calculation LOOP sunshineDur not possible, radiation not present!")
            return None
        loopDate = event.packet.get('dateTime')
        if loopDate is None:
            logerr("Calculation LOOP sunshineDur not possible, dateTime not present!")
            return None
        threshold = event.packet.get('sunshineThreshold')
        if threshold is None:
            logdbg("Calculation LOOP sunshineDur not possible, sunshineThreshold not present!")
            return None
        loopInterval = 0
        stationInterval = event.packet.get('foshk_interval')
        if stationInterval is not None:
            loopInterval = stationInterval
            self.lastDate = loopDate
        elif self.lastDate > 0 and loopDate is not None:
            loopInterval = loopDate - self.lastDate
            self.lastDate = loopDate
        else:
            logerr("Calculation LOOP sunshineDur not possible, interval could not be determined!")
            return None

        # Calculation LOOP sunshineDur is possible
        # Classic Version
        loopSunshineDur = 0
        sunshining = 0
        if radiation > threshold and radiation > 20:
            loopSunshineDur = int(loopInterval)
            sunshining = 1
        self.sunshineDur += loopSunshineDur
        self.sunshineObs.append(sunshining)
        if self.debug:
            logdbg("Added LOOP Interval=%d, based on sunshine=%d, radiation=%f and threshold=%f. LOOP sunshineDur=%d" % (
                    loopSunshineDur, sunshining, radiation, threshold, int(self.sunshineDur)))

        # Original Version
        loopSunshineDurOriginal = 0
        sunshining = 0
        threshold = event.packet.get('sunshineThresholdOriginal')
        if threshold is None:
            logdbg("Calculation LOOP sunshineDurOriginal not possible, sunshineThresholdOriginal not present!")
            return None
        if radiation > threshold and radiation > 20:
            loopSunshineDurOriginal = int(loopInterval)
            sunshining = 1
        self.sunshineDurOriginal += loopSunshineDurOriginal
        if self.debug:
            logdbg("Original Version:")
            logdbg("Added LOOP Interval=%d, based on sunshine=%d, radiation=%f and threshold=%f. LOOP sunshineDur=%d" % (
                    loopSunshineDurOriginal, sunshining, radiation, threshold, int(self.sunshineDurOriginal)))

        if self.debug:
            logdbg("sunshineObs: %s Avg10: %0.2f" % (str(self.sunshineObs), self.avgSunshine()))

    def newArchiveRecord(self, event):
        """Gets called on a new archive record event."""
        event.record['sunshineDur'] = int(self.sunshineDur)
        event.record['sunshine_avg10m'] = self.avgSunshine()
        event.record['sunshineDurOriginal'] = int(self.sunshineDurOriginal)
        self.sunshineDur = 0
        self.sunshineDurOriginal = 0
        if self.debug:
            logdbg("Total ARCHIVE sunshineDur=%d sunshine_avg10m=%0.2f" % (event.record['sunshineDur'], event.record['sunshine_avg10m']))
            logdbg("Original Version:")
            logdbg("Total ARCHIVE sunshineDur=%d" % (event.record['sunshineDurOriginal']))

    schema_with_sunshine_time = schemas.wview.schema + [('sunshineDur', 'REAL')]
