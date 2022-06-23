import syslog
from math import sin, cos, pi, asin
from datetime import datetime
import time
import weewx
from weewx.wxengine import StdService
from weeutil.weeutil import to_int, to_float, to_bool
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
        self.debug = to_bool(self.config_dict["debug"])

    def sunshineThreshold(self, mydatetime):
        coeff = 0.76  # change to calibrate with your sensor
        utcdate = datetime.utcfromtimestamp(mydatetime)
        dayofyear = int(time.strftime("%j", time.gmtime(mydatetime)))
        theta = 360 * dayofyear / 365
        equatemps = 0.0172 + 0.4281 * cos((pi / 180) * theta) - 7.3515 * sin(
            (pi / 180) * theta) - 3.3495 * cos(2 * (pi / 180) * theta) - 9.3619 * sin(
            2 * (pi / 180) * theta)
        latitude = float(self.config_dict["Station"]["latitude"])
        longitude = float(self.config_dict["Station"]["longitude"])
        corrtemps = longitude * 4
        declinaison = asin(0.006918 - 0.399912 * cos((pi / 180) * theta) + 0.070257 * sin(
            (pi / 180) * theta) - 0.006758 * cos(2 * (pi / 180) * theta) + 0.000908 * sin(
            2 * (pi / 180) * theta)) * (180 / pi)
        minutesjour = utcdate.hour * 60 + utcdate.minute
        tempsolaire = (minutesjour + corrtemps + equatemps) / 60
        angle_horaire = (tempsolaire - 12) * 15
        hauteur_soleil = asin(sin((pi / 180) * latitude) * sin((pi / 180) * declinaison) + cos(
            (pi / 180) * latitude) * cos((pi / 180) * declinaison) * cos((pi / 180) * angle_horaire)) * (180 / pi)
        if hauteur_soleil > 3:
            seuil = (0.73 + 0.06 * cos((pi / 180) * 360 * dayofyear / 365)) * 1080 * pow(
                (sin(pi / 180) * hauteur_soleil), 1.25) * coeff
        else:
            seuil = 0
        return seuil

    def sunshineThresholdOriginal(self, mydatetime):
        coeff = 0.9  # change to calibrate with your sensor
        utcdate = datetime.utcfromtimestamp(mydatetime)
        dayofyear = int(time.strftime("%j", time.gmtime(mydatetime)))
        theta = 360 * dayofyear / 365
        equatemps = 0.0172 + 0.4281 * cos((pi / 180) * theta) - 7.3515 * sin(
            (pi / 180) * theta) - 3.3495 * cos(2 * (pi / 180) * theta) - 9.3619 * sin(
            2 * (pi / 180) * theta)

        latitude = float(self.config_dict["Station"]["latitude"])
        longitude = float(self.config_dict["Station"]["longitude"])
        corrtemps = longitude * 4
        declinaison = asin(0.006918 - 0.399912 * cos((pi / 180) * theta) + 0.070257 * sin(
            (pi / 180) * theta) - 0.006758 * cos(2 * (pi / 180) * theta) + 0.000908 * sin(
            2 * (pi / 180) * theta)) * (180 / pi)
        minutesjour = utcdate.hour * 60 + utcdate.minute
        tempsolaire = (minutesjour + corrtemps + equatemps) / 60
        angle_horaire = (tempsolaire - 12) * 15
        hauteur_soleil = asin(sin((pi / 180) * latitude) * sin((pi / 180) * declinaison) + cos(
            (pi / 180) * latitude) * cos((pi / 180) * declinaison) * cos((pi / 180) * angle_horaire)) * (180 / pi)
        if hauteur_soleil > 0:
            seuil = (0.97 + 0.2 * cos((pi / 180) * 360 * dayofyear / 365)) * 830 * pow(
                (sin(pi / 180) * hauteur_soleil), 1.25) 
        else :
            seuil=0
        return seuil

    def newLoopPacket(self, event):
        """Gets called on a new loop packet event."""
        radiation = event.packet.get('radiation')
        loopDate = event.packet.get('dateTime')
        stationInterval = event.packet.get('foshk_interval')
        if radiation is None:
            logerr("Calculation LOOP sunshineDur not possible, radiation not present!")
            return None
        if loopDate is None:
            logerr("Calculation LOOP sunshineDur not possible, dateTime not present!")
            return None
        loopInterval = 0
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
        loopSunshineDur = 0
        sunshining = 'NO'
        threshold = self.sunshineThreshold(loopDate)
        if radiation > threshold and radiation > 20:
            loopSunshineDur = loopInterval
            sunshining = 'YES'
        self.sunshineDur += loopSunshineDur
        if self.debug:
            logdbg("Calculated LOOP sunshineDur=%f, based on sunshining %s, radiation=%f and threshold=%f. LOOP Sum=%f" % (
                    loopSunshineDur, sunshining, radiation, threshold, self.sunshineDur))

        # Original Version
        loopSunshineDurOriginal = 0
        sunshining = 'NO'
        threshold = self.sunshineThresholdOriginal(loopDate)
        if radiation > threshold and radiation > 20:
            loopSunshineDurOriginal = loopInterval
            sunshining = 'YES'
        self.sunshineDurOriginal += loopSunshineDurOriginal
        if self.debug and (loopSunshineDur != loopSunshineDurOriginal):
            logdbg("Calculated DIFF sunshineDur=%f, based on sunshining %s, radiation=%f and threshold=%f. LOOP Sum=%f" % (
                    loopSunshineDurOriginal, sunshining, radiation, threshold, self.sunshineDurOriginal))


    def newArchiveRecord(self, event):
        """Gets called on a new archive record event."""
        event.record['sunshineDur'] = self.sunshineDur
        self.sunshineDur = 0
        if self.debug:
            logdbg("Total ARCHIVE sunshineDur=%f" % (event.record['sunshineDur']))
            logdbg(" ORIG ARCHIVE sunshineDur=%f" % (self.sunshineDurOriginal))
        self.sunshineDurOriginal = 0

    schema_with_sunshine_time = schemas.wview.schema + [('sunshineDur', 'REAL')]
