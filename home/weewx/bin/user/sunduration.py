"""
    Copyright (C) 2022 Henry Ott
    based on code from https://github.com/Jterrettaz/sunduration
    Status: work in progress

    Adds new observation fields containing sunshine duration and
    sunshine yes/no
    Condition for determining the values:
      - radiation is present in loop/archive and is not None
      - radiation does not fall below a minimum threshold defined by the user
    If these conditions are not met, a calculation ist not possible and then 
    the results are None.

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
        syslog.syslog(level, 'sunduration: %s' % msg)

    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)

VERSION = "0.1"

DEFAULTS_INI = """
[SunDuration]
    enable = true
    debug = 0
    radiation_min = 0.0
    add_sunshine_to_loop = false
    [[coeff]]
        1 = 1.0
        2 = 1.0
        3 = 1.0
        4 = 1.0
        5 = 1.0
        6 = 1.0
        7 = 1.0
        8 = 1.0
        9 = 1.0
        10 = 1.0
        11 = 1.0
        12 = 1.0
"""
defaults_dict = weeutil.config.config_from_str(DEFAULTS_INI)

class SunDuration(StdService):
    def __init__(self, engine, config_dict):
        # Pass the initialization information on to my superclass:
        super(SunDuration, self).__init__(engine, config_dict)
        loginf("Service version is %s" % VERSION)

        # Get any user-defined overrides
        override_dict = config_dict.get('SunDuration', {})
        # Get the default values, then merge the user overrides into it
        option_dict = weeutil.config.deep_copy(defaults_dict['SunDuration'])
        option_dict.merge(override_dict)

        # Only continue if the plugin is enabled.
        enable = to_bool(option_dict['enable'])
        if enable:
            loginf("SunDuration is enabled...continuing.")
        else:
            loginf("SunDuration is disabled. Enable it in the SunDuration section of weewx.conf.")
            return
        self.debug = to_int(option_dict.get('debug', 0))
        self.radiation_min = to_float(option_dict.get('radiation_min', 0.0))
        self.add_sunshine_to_loop = to_bool(option_dict.get("add_sunshine_to_loop", False))
        self.coeff_dict = option_dict.get('coeff', {})

        if self.debug > 0:
            logdbg("debug level is %d" % self.debug)
            logdbg("radiation min threshold is %.2f" % self.radiation_min)
            logdbg("add_sunshine_to_loop is %s" % ("True" if self.add_sunshine_to_loop else "False"))
            logdbg("coeff monthly is %s" % str(self.coeff_dict))

        # dateTime from the last loop package with valid 'radiation'
        self.lastLoop = None
        # dateTime from the last archive record
        self.lastArchive = None
        # sum sunshineDur within archive interval
        self.sunshineDur = None

        # Start intercepting events:
        self.bind(weewx.NEW_LOOP_PACKET, self.newLoopPacket)
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.newArchiveRecord)

    def sunshineThreshold(self, mydatetime):
        utcdate = datetime.utcfromtimestamp(mydatetime)
        dayofyear = to_int(time.strftime("%j", time.gmtime(mydatetime)))
        monthofyear = to_int(time.strftime("%m", time.gmtime(mydatetime)))
        coeff = to_float(self.coeff_dict.get(str(monthofyear)))
        if coeff is None:
            coeff = to_float(defaults_dict.get(str(monthofyear), 1.0))
            logerr("User configured coeff month=%d is not valid! Using default coeff instead." % (monthofyear))
        if self.debug >= 4:
            logdbg("sunshineThreshold, month=%d coeff=%.2f" % (monthofyear, coeff)) 
        theta = 360 * dayofyear / 365
        equatemps = 0.0172 + 0.4281 * cos((pi / 180) * theta) - 7.3515 * sin(
            (pi / 180) * theta) - 3.3495 * cos(2 * (pi / 180) * theta) - 9.3619 * sin(
            2 * (pi / 180) * theta)
        latitude = to_float(self.config_dict["Station"]["latitude"])
        longitude = to_float(self.config_dict["Station"]["longitude"])
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
                sin((pi / 180) * hauteur_soleil), 1.25) * coeff
        else:
            seuil = 0.0
        return seuil

    def newLoopPacket(self, event):
        """Gets called on a new loop packet event."""
        radiation = event.packet.get('radiation')
        sunshine = None
        if radiation is not None:
            if radiation >= self.radiation_min:
                loopdateTime = event.packet.get('dateTime')
                sunshine = 0
                threshold = self.sunshineThreshold(loopdateTime)
                if threshold > 0.0 and radiation > threshold:
                    sunshine = 1

                if self.lastLoop is None:
                    # It's the first loop packet, more is not to be done
                    # To calculate the time we wait for the next loop packet
                    # ...L
                    # ??>|
                    self.sunshineDur = 0
                    if self.debug >= 3:
                        logdbg("first loop packet with 'radiation' during archive interval received.")
                else:
                    # L..A..L....L....L....L
                    #                 |<==>|   loopDuration
                    # |<==================>|   self.sunshineDur
                    loopDuration = loopdateTime - self.lastLoop
                    loopSunshineDur = 0
                    if sunshine > 0:
                        loopSunshineDur = loopDuration
                    self.sunshineDur += loopSunshineDur
                    if self.debug >= 2:
                        logdbg("LOOP sunshineDur=%d, based on threshold=%.2f radiation=%.2f loopDuration=%d loopSunshineDur=%d" % (
                            self.sunshineDur, threshold, radiation, loopDuration, loopSunshineDur))

                self.lastLoop = loopdateTime

            elif self.debug >= 2:
                logdbg("LOOP no calculation, radiation=%.2f lower than radiation_min=%.2f" % (radiation, self.radiation_min))
        elif self.debug >= 3:
            logdbg("LOOP no calculation, 'radiation' not in loop packet or is None.")

        if self.add_sunshine_to_loop:
            target_data = {}
            target_data['sunshine'] = sunshine
            # add sunshine to LOOP
            event.packet.update(target_data)
            if self.debug >= 3:
                logdbg("LOOP sunshine=%s" % (str(to_int(sunshine)) if sunshine is not None else 'None'))

    def newArchiveRecord(self, event):
        """Gets called on a new archive record event."""
        target_data = {}
        target_data['sunshineDur'] = None
        archivedateTime = event.record.get('dateTime')
        interval = event.record.get('interval')

        if self.lastArchive is not None and self.lastLoop is not None and self.lastLoop < self.lastArchive:
            # No loop packets with values for 'radiation' or 'radiation' < min during the last archive interval, discard loop indicator.
            # ..L....L....L....L....A...........................A
            #                  |????|
            if self.debug >= 3:
                logdbg("No loop packets with values for 'radiation' or 'radiation' < min during the last archive interval, discard loop indicator.")
            self.lastLoop = None
            self.sunshineDur = None

        if self.lastLoop is None:
            # loop packets with 'radiation' not yet captured
            # A...........................A
            # |<=========================>|    interval
            radiation = event.record.get('radiation')
            if radiation is not None:
                if interval is not None:
                    if radiation >= self.radiation_min:
                        # We assume here that the radiation is an average value over the whole archive period.
                        # If this value is higher than the threshold value, we assume that the sun shone during
                        # the whole archive interval.
                        threshold = self.sunshineThreshold(event.record.get('dateTime'))
                        interval = interval * 60 # seconds
                        target_data['sunshineDur'] = 0
                        if threshold > 0.0 and radiation > threshold:
                            target_data['sunshineDur'] = interval
                        if self.debug >= 2:
                            logdbg("ARCHIVE sunshineDur=%d, based on threshold=%.2f radiation=%.2f interval=%d" % (
                                target_data['sunshineDur'], threshold, radiation, interval))
                    elif self.debug >= 2:
                        logdbg("ARCHIVE no calculation, radiation=%.2f lower than radiation_min=%.2f" % (radiation, self.radiation_min))
                elif self.debug >= 2:
                    logdbg("ARCHIVE no calculation, 'interval' not in archive record or is None.")
            elif self.debug >= 3:
                logdbg("ARCHIVE no calculation, 'radiation' not in archive record or is None.")
        else:
            # sum from loop packets
            # The period from the last loop packet before the archive time to the first loop packet after the archive time is calculated in the following run.
            # L..A..L....L....L....L....L..A
            # |<=======================>|           = self.sunshineDur
            #                           |<====      = calculate on next loop
            target_data['sunshineDur'] = self.sunshineDur
            # reset loop sum
            self.sunshineDur = 0
            if self.debug >= 2:
                logdbg("ARCHIVE sunshineDur=%d, based on loop packets." % (target_data['sunshineDur']))

        event.record.update(target_data)
        self.lastArchive = archivedateTime
    
# Tell the unit system what group our new observation types, 'sunshineDur' and 'sunshine', belongs to:
weewx.units.obs_group_dict['sunshineDur'] = "group_deltatime"
weewx.units.obs_group_dict['sunshine'] = "group_count"
