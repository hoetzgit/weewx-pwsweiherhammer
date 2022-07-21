import syslog
from math import sin, cos, pi, asin
from datetime import datetime
import time
import weewx
from weewx.wxengine import StdService
from weeutil.weeutil import to_bool
from collections import deque

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
        syslog.syslog(level, 'thunderstormDur: %s' % msg)

    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)


def avgDeque(thunderstorm):
   s = 0
   a = 0
   l = len(thunderstorm)
   if l > 0:
       for i in range(l):
           s = s + thunderstorm[i]
       a = round(s/l,2)
   else:
       return None
   return a

class ThunderstormDuration(StdService):
    def __init__(self, engine, config_dict):
        # Pass the initialization information on to my superclass:
        super(ThunderstormDuration, self).__init__(engine, config_dict)

        # Start intercepting events:
        self.bind(weewx.NEW_LOOP_PACKET, self.newLoopPacket)
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.newArchiveRecord)
        self.thunderstorm_10 = deque(maxlen=(int(10*60/int(16)))) # 10 minutes thunderstorm oberservations
        self.thunderstorm_20 = deque(maxlen=(int(20*60/int(16)))) # 20 minutes thunderstorm oberservations
        self.thunderstorm_30 = deque(maxlen=(int(30*60/int(16)))) # 30 minutes thunderstorm oberservations
        self.thunderstorm_60 = deque(maxlen=(int(60*60/int(16)))) # 60 minutes thunderstorm oberservations
        self.debug = to_bool(self.config_dict["debug"])


    def newLoopPacket(self, event):
        """Gets called on a new loop packet event."""
        lightning_strikes = event.packet.get('lightning_strike_count')
        if lightning_strikes is None:
            loginf("LOOP check thunderstorm not possible, lightning_strike_count not present!")
            return None
        thunderstorm = 0
        if lightning_strikes > 0.0:
            thunderstorm = 1
        self.thunderstorm_10.append(thunderstorm)
        self.thunderstorm_20.append(thunderstorm)
        self.thunderstorm_30.append(thunderstorm)
        self.thunderstorm_60.append(thunderstorm)

        if self.debug:
            logdbg("Loop: Thunderstorm=%d" % (thunderstorm))
            logdbg("Loop: Avg10: %0.2f" % (avgDeque(self.thunderstorm_10)))
            logdbg("Loop: Avg20: %0.2f" % (avgDeque(self.thunderstorm_20)))
            logdbg("Loop: Avg30: %0.2f" % (avgDeque(self.thunderstorm_30)))
            logdbg("Loop: Avg60: %0.2f" % (avgDeque(self.thunderstorm_60)))

    def newArchiveRecord(self, event):
        """Gets called on a new archive record event."""
        event.record['thunderstorm_avg10m'] = avgDeque(self.thunderstorm_10)
        event.record['thunderstorm_avg20m'] = avgDeque(self.thunderstorm_20)
        event.record['thunderstorm_avg30m'] = avgDeque(self.thunderstorm_30)
        event.record['thunderstorm_avg60m'] = avgDeque(self.thunderstorm_60)
        if self.debug:
            logdbg("Archive: Avg10: %0.2f" % (event.record['thunderstorm_avg10m']))
            logdbg("Archive: Avg20: %0.2f" % (event.record['thunderstorm_avg20m']))
            logdbg("Archive: Avg30: %0.2f" % (event.record['thunderstorm_avg30m']))
            logdbg("Archive: Avg60: %0.2f" % (event.record['thunderstorm_avg60m']))

class RainDuration(StdService):
    def __init__(self, engine, config_dict):
        # Pass the initialization information on to my superclass:
        super(RainDuration, self).__init__(engine, config_dict)

        # Start intercepting events:
        self.bind(weewx.NEW_LOOP_PACKET, self.newLoopPacket)
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.newArchiveRecord)
        self.rain_10 = deque(maxlen=(int(10*60/int(16)))) # 10 minutes rain oberservations
        self.rain_20 = deque(maxlen=(int(20*60/int(16)))) # 20 minutes rain oberservations
        self.rain_30 = deque(maxlen=(int(30*60/int(16)))) # 30 minutes rain oberservations
        self.rain_60 = deque(maxlen=(int(60*60/int(16)))) # 60 minutes rain oberservations
        self.debug = to_bool(self.config_dict["debug"])


    def newLoopPacket(self, event):
        """Gets called on a new loop packet event."""
        rain = event.packet.get('rain')
        if rain is None:
            loginf("LOOP check rain not possible, rain not present!")
            return None
        raining = 0
        if rain > 0.0:
            raining = 1
        self.rain_10.append(raining)
        self.rain_20.append(raining)
        self.rain_30.append(raining)
        self.rain_60.append(raining)

        if self.debug:
            logdbg("Loop: Raining=%d" % (raining))
            logdbg("Loop: Avg10: %0.2f" % (avgDeque(self.rain_10)))
            logdbg("Loop: Avg20: %0.2f" % (avgDeque(self.rain_20)))
            logdbg("Loop: Avg30: %0.2f" % (avgDeque(self.rain_30)))
            logdbg("Loop: Avg60: %0.2f" % (avgDeque(self.rain_60)))

    def newArchiveRecord(self, event):
        """Gets called on a new archive record event."""
        event.record['rain_avg10m'] = avgDeque(self.rain_10)
        event.record['rain_avg20m'] = avgDeque(self.rain_20)
        event.record['rain_avg30m'] = avgDeque(self.rain_30)
        event.record['rain_avg60m'] = avgDeque(self.rain_60)
        if self.debug:
            logdbg("Archive: Avg10: %0.2f" % (event.record['rain_avg10m']))
            logdbg("Archive: Avg20: %0.2f" % (event.record['rain_avg20m']))
            logdbg("Archive: Avg30: %0.2f" % (event.record['rain_avg30m']))
            logdbg("Archive: Avg60: %0.2f" % (event.record['rain_avg60m']))
