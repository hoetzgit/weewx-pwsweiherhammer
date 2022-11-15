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
        self.sunshineDurMonth = 0
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
            logdbg("Calculation LOOP sunshineDur not possible, sunshineThreshold not present!")
        else:
            if threshold > 0 and radiation > threshold and radiation > self.radiation_min:
                loopSunshineDur = int(loopInterval)
        self.sunshineDur += loopSunshineDur
        if self.debug:
            logdbg("Version 1: dateTime=%d interval=%d threshold=%.2f radiation=%.2f LOOP sunshineDur=%d" % (
                loopDate, loopInterval, threshold, radiation, int(self.sunshineDur)))

        # Original Version
        # https://github.com/hoetzgit/sunduration/blob/master/sunduration.py
        loopSunshineDur = 0
        threshold = event.packet.get('sunshineThresholdOriginal', None)
        if threshold is None:
            logdbg("Calculation LOOP sunshineDurOriginal not possible, sunshineThresholdOriginal not present!")
        else:
            if threshold > 0 and radiation > threshold:
                loopSunshineDur = int(loopInterval)
        self.sunshineDurOriginal += loopSunshineDur
        if self.debug:
            logdbg("Version 2: dateTime=%d interval=%d threshold=%.2f radiation=%.2f LOOP sunshineDur=%d" % (
                loopDate, loopInterval, threshold, radiation, int(self.sunshineDur)))

        # Calculation LOOP sunshineDur
        # Version with coeff per month
        loopSunshineDur = 0
        threshold = event.packet.get('sunshineThresholdMonth', None)
        if threshold is None:
            logdbg("Calculation LOOP sunshineDurMonth not possible, sunshineThresholdMonth not present!")
        else:
            if threshold > 0 and radiation > threshold and radiation > self.radiation_min:
                loopSunshineDur = int(loopInterval)
        self.sunshineDurMonth += loopSunshineDur
        if self.debug:
            logdbg("Version 3: dateTime=%d interval=%d threshold=%.2f radiation=%.2f LOOP sunshineDur=%d" % (
                loopDate, loopInterval, threshold, radiation, int(self.sunshineDur)))


    def newArchiveRecord(self, event):
        """Gets called on a new archive record event."""
        event.record['sunshineDur'] = int(self.sunshineDur)
        event.record['sunshineDurOriginal'] = int(self.sunshineDurOriginal)
        event.record['sunshineDurMonth'] = int(self.sunshineDurMonth)
        self.sunshineDur = 0
        self.sunshineDurOriginal = 0
        self.sunshineDurMonth = 0
        if self.debug:
            logdbg("Version 1: ARCHIVE sunshineDur=%d" % (event.record['sunshineDur']))
            logdbg("Version 2: ARCHIVE sunshineDur=%d" % (event.record['sunshineDurOriginal']))
            logdbg("Version 3: ARCHIVE sunshineDur=%d" % (event.record['sunshineDurMonth']))

    schema_with_sunshine_time = schemas.wview.schema + [('sunshineDur', 'REAL')]
