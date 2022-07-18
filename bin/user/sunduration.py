import syslog
from math import sin, cos, pi, asin
from datetime import datetime
import time
import weewx
from weewx.wxengine import StdService
from weeutil.weeutil import to_bool
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
        self.radiation_min = 20
        self.lastDate = 0
        self.sunshineDur = 0
        self.sunshineDurOriginal = 0
        self.debug = to_bool(self.config_dict["debug"])

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
        threshold = event.packet.get('sunshineThreshold', None)
        if threshold is None:
            logdbg("Calculation LOOP sunshineDur not possible, sunshineThreshold not present!")
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

        # Calculation LOOP sunshineDur is possible
        # Classic Version
        # packet = event.packet
        loopSunshineDur = 0
        if threshold > 0 and radiation > threshold and radiation > self.radiation_min:
            loopSunshineDur = int(loopInterval)
            event.packet['sunshineDurTest'] = loopSunshineDur
        self.sunshineDur += loopSunshineDur
        if self.debug:
            logdbg("Added LOOP Interval=%d, based on radiation=%f and threshold=%f. LOOP sunshineDur=%d" % (
                    loopSunshineDur, radiation, threshold, int(self.sunshineDur)))

        # Original Version
        loopSunshineDurOriginal = 0
        threshold = event.packet.get('sunshineThresholdOriginal', None)
        if threshold is None:
            logdbg("Calculation LOOP sunshineDurOriginal not possible, sunshineThresholdOriginal not present!")
            return None
        if threshold > 0 and radiation > threshold and radiation > self.radiation_min:
            loopSunshineDurOriginal = int(loopInterval)
        self.sunshineDurOriginal += loopSunshineDurOriginal
        if self.debug:
            logdbg("Original Version:")
            logdbg("Added LOOP Interval=%d, based on radiation=%f and threshold=%f. LOOP sunshineDur=%d" % (
                    loopSunshineDurOriginal, radiation, threshold, int(self.sunshineDurOriginal)))

    def newArchiveRecord(self, event):
        """Gets called on a new archive record event."""
        event.record['sunshineDur'] = int(self.sunshineDur)
        event.record['sunshineDurOriginal'] = int(self.sunshineDurOriginal)
        self.sunshineDur = 0
        self.sunshineDurOriginal = 0
        if self.debug:
            logdbg("Total ARCHIVE sunshineDur=%d" % (event.record['sunshineDur']))
            logdbg("Original Version:")
            logdbg("Total ARCHIVE sunshineDur=%d" % (event.record['sunshineDurOriginal']))

    schema_with_sunshine_time = schemas.wview.schema + [('sunshineDur', 'REAL')]
