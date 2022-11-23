"""
sunduration.py

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

Example weewx.conf configuration:

[SunshineDuration]
    enable = true
    debug = 1
    radiation_min = 50.0
    add_sunshine_to_loop = true
    coeff_monthly = "'{1: 0.69, 2: 0.71, 3: 0.74, 4: 0.77, 5: 0.78, 6: 0.79, 7: 0.79, 8: 0.78, 9: 0.77, 10: 0.74, 11: 0.71, 12: 0.69}'"
    # If the coeff_monthly is incorrectly configured, this value will be used
    coeff_fallback = 0.79

Status: work in progress
My Python knowledge is rudimentary. Hints are welcome!
"""

VERSION = "0.1"

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
        loginf("Service version is %s" % VERSION)

        cust_dict = config_dict.get('SunshineDuration', {})
        enable = to_bool(cust_dict.get('enable', True))
        if enable:
            loginf("Service is enabled.")
        else:
            loginf("Service is disabled. Enable it in the SunshineDuration section of weewx.conf.")
            return

        # extension defaults
        self.debug = 0
        self.radiation_min = 0.0
        self.coeff_fallback = 1.0
        self.coeff_monthly = {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0, 7: 1.0, 8: 1.0, 9: 1.0, 10: 1.0, 11: 1.0, 12: 1.0}
        self.add_sunshine_to_loop = False

        # optional customizations by the user.
        self.debug = to_int(cust_dict.get('debug', self.debug))
        loginf("debug level is %d" % self.debug)
        self.radiation_min = to_float(cust_dict.get('radiation_min', self.radiation_min))
        loginf("radiation min threshold is %.2f" % self.radiation_min)
        self.add_sunshine_to_loop = to_bool(cust_dict.get("add_sunshine_to_loop", self.add_sunshine_to_loop))
        loginf("add_sunshine_to_loop is %s" % ("True" if self.add_sunshine_to_loop else "False"))

        # TODO?
        self.coeff_fallback = to_float(cust_dict.get('coeff_fallback', 1.0))
        loginf("coeff_fallback is %s" % str(self.coeff_fallback))
        coeff_monthly = cust_dict.get('coeff_monthly', None)
        if coeff_monthly is not None:
            coeff_valid = True
            if isinstance(coeff_monthly, str):
                try:
                    coeff_monthly = ast.literal_eval(coeff_monthly)
                except ValueError:
                    coeff_valid = False
            if not isinstance(coeff_monthly, dict):
                coeff_valid = False

            if coeff_valid:
                self.coeff_monthly = coeff_monthly
                loginf("User configured coeff_monthly is a valid dict! Using user coeff_monthly.")
            else:
                logerr("User configured coeff_monthly is not a valid dict! Using default coeff_monthly instead.")

        loginf("coeff_monthly is %s" % str(self.coeff_monthly))

        # dateTime from the last loop package with valid 'radiation'
        self.lastLoop = 0
        # dateTime from the last archiv record
        self.lastArchiv = 0
        # sum sunshineDur within archiv interval
        self.sunshineDur = 0

        # Start intercepting events:
        self.bind(weewx.NEW_LOOP_PACKET, self.newLoopPacket)
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.newArchiveRecord)

    def sunshineThreshold(self, mydatetime):
        utcdate = datetime.utcfromtimestamp(mydatetime)
        dayofyear = to_int(time.strftime("%j", time.gmtime(mydatetime)))
        monthofyear = to_int(time.strftime("%m", time.gmtime(mydatetime)))
        coeff = self.coeff_monthly.get(monthofyear, None)
        if coeff is None:
            coeff = self.coeff_fallback
            logerr("User configured coeff_monthly month=%d is not valid! Using coeff_fallback=%.2f instead." % (monthofyear, self.coeff_fallback))
        if self.debug > 1:
            logdbg("sunshineThreshold coeff=%.2f" % coeff) 
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
                sin((pi / 180) * hauteur_soleil), 1.25) * to_float(coeff)
        else:
            seuil = 0
        return seuil

    def newLoopPacket(self, event):
        """Gets called on a new loop packet event."""
        radiation = event.packet.get('radiation')
        if radiation is not None:
            loopdateTime = event.packet.get('dateTime')
            sunshine = 0
            if radiation >= self.radiation_min:
                threshold = self.sunshineThreshold(loopdateTime)
                if threshold > 0.0 and radiation > threshold:
                   sunshine = 1
            elif self.debug > 0:
                logdbg("LOOP no calculation, radiation=%.2f lower than radiation_min=%.2f" % (radiation, self.radiation_min))

            if self.lastLoop == 0:
                # It's the first loop packet, more is not to be done
                # To calculate the time we wait for the next loop packet
                # ..L
                if self.debug > 0:
                    logdbg("first loop packet with 'radiation' during archiv interval received.")
            elif radiation >= self.radiation_min:
                # .L..L..L..L
                loopDuration = loopdateTime - self.lastLoop
                loopSunshineDur = 0
                if sunshine > 0:
                    loopSunshineDur = loopDuration
                self.sunshineDur += loopSunshineDur
                if self.debug > 0:
                    logdbg("LOOP sunshineDur=%d, based on threshold=%.2f radiation=%.2f loopDuration=%d loopSunshineDur=%d" % (
                        self.sunshineDur, threshold, radiation, loopDuration, loopSunshineDur))

            self.lastLoop = loopdateTime

            if self.add_sunshine_to_loop:
                target_data = {}
                target_data['sunshine'] = sunshine
                # add sunshine to LOOP
                event.packet.update(target_data)
                if self.debug > 1:
                    logdbg("LOOP sunshine=%d" % (sunshine))

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
                    threshold = self.sunshineThreshold(event.record.get('dateTime'))
                    interval = event.record.get('interval') * 60 # seconds
                    if threshold > 0.0 and radiation > threshold:
                        target_data['sunshineDur'] = interval
                    if self.debug > 0:
                        logdbg("ARCHIV sunshineDur=%d, based on threshold=%.2f radiation=%.2f interval=%d" % (
                            target_data['sunshineDur'], threshold, radiation, interval))
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
    
