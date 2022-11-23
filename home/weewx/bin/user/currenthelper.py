"""
currenthelper.py

Copyright (C) 2022 Henry Ott

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

Example weewx.conf configuration:

[CurrentHelper]
    enable = true
    debug = 1
    observations = raining, thunderstorm, sunshine, fog, snow
    timeintervals = 10, 20, 30, 60
    loopinterval = 16
    radiation_min = 50.0
    # TODO: to adjust coeffizient month 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, --, 12
    coeff_monthly = "{1: 0.79, 2: 0.79, 3: 0.79, 4: 0.79, 5: 0.79, 6: 0.79, 7: 0.79, 8: 0.79, 9: 0.79, 10: 0.78, 11: 0.71, 12: 0.7}"
    # If the coeff_monthly is incorrectly configured, this value will be used
    coeff_fallback = 0.79

Status: work in progress
My Python knowledge is rudimentary. Hints are welcome!
"""

VERSION = "0.1"

import syslog
import ast
from datetime import datetime
import time
import weewx
from weewx.wxengine import StdService
from weeutil.weeutil import to_bool, to_int, to_float, to_sorted_string
from collections import deque
from datetime import datetime
from math import sin, cos, pi, asin

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
        syslog.syslog(level, 'currenthelper: %s' % msg)

    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)

class CurrentHelper(StdService):
    def __init__(self, engine, config_dict):
        # Pass the initialization information on to my superclass:
        super(CurrentHelper, self).__init__(engine, config_dict)
        loginf("Service version is %s" % VERSION)

        cust_dict = config_dict.get('CurrentHelper', {})
        enable = to_bool(cust_dict.get('enable', True))
        if enable:
            loginf("Service is enabled.")
        else:
            loginf("Service is disabled. Enable it in the CurrentHelper section of weewx.conf.")
            return

        # inits
        self.debug = to_int(cust_dict.get('debug', config_dict.get('debug', 0)))
        loginf("debug level is %d" % self.debug)
        self.radiation_min = to_float(cust_dict.get('radiation_min', 0))
        loginf("radiation min threshold is %.2f" % self.radiation_min)

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

        self.observations = cust_dict.get('observations', 'raining')
        if self.observations is not None and not isinstance(self.observations, list):
            tmplist = []
            tmplist.append(self.observations)
            self.observations = tmplist
        if self.debug >= 2:
            logdbg("Observations %s" % str(self.observations))

        self.timeintervals = cust_dict.get('timeintervals', '10')
        if self.timeintervals is not None and not isinstance(self.timeintervals, list):
            tmplist = []
            tmplist.append(self.timeintervals)
            self.timeintervals = tmplist
        if self.debug >= 2:
            logdbg("Time intervals %s" % str(self.timeintervals))

        self.loopinterval = to_int(cust_dict.get('loopinterval', 16))
        if self.debug >= 2:
            logdbg("Loop interval %d" % self.loopinterval)

        self.obsvalues = dict()
        for obs in self.observations:
            self.obsvalues[obs] = dict()
            for ti in self.timeintervals:
                ti = to_int(ti)
                maxlen = to_int(ti*60/self.loopinterval)
                self.obsvalues[obs][ti] = deque(maxlen=(maxlen))

        loginf("radiation min threshold is %.2f" % self.radiation_min)
        self.last_strikes_total = None

        # Start intercepting events:
        self.bind(weewx.NEW_LOOP_PACKET, self.newLoopPacket)

    @staticmethod
    def avg_Deque(val):
        sumval = 0
        avgval = 0
        elems = len(val)
        if elems > 0:
            for i in range(elems):
                sumval += val[i]
            avgval = round(sumval/elems,2)
        else:
            return None
        return avgval

    @staticmethod
    def delta_total(new_total, old_total):
        if new_total is None:
            return None
        if old_total is None:
            return None
        if new_total < old_total:
            return new_total
        return new_total - old_total

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
        target_data = {}
        if self.debug >= 2:
            logdbg('new_loop: %s' % event.packet)

        # TODO: check self.observations

        #################################
        # thunderstorm?
        #################################
        strikes_total = event.packet.get('lightning_num')
        if strikes_total is not None:
            new_delta = self.delta_total(strikes_total, self.last_strikes_total)
            thunderstorm = 0
            if new_delta is not None:
                if (to_int(new_delta) > 0):
                    thunderstorm = 1
            # Add thunderstorm to loop packet
            target_data['thunderstorm'] = thunderstorm
            if self.debug >= 1:
                logdbg("Thunderstorm: %s" % ("YES" if thunderstorm > 0 else "NO"))
            for ti in self.timeintervals:
                ti = to_int(ti)
                self.obsvalues['thunderstorm'][ti].append(thunderstorm)
                avgvalname = 'thunderstorm_avg' + str(ti) + 'm'
                target_data[avgvalname] = self.avg_Deque(self.obsvalues['thunderstorm'][ti])
                if self.debug >= 3:
                    logdbg("%s=%s, len=%d, avg=%.2f" % (avgvalname, str(self.obsvalues['thunderstorm'][ti]),len(self.obsvalues['thunderstorm'][ti]),target_data[avgvalname]))
        else:
            if self.debug >= 3:
                logerr("lightning_num not present!")

        #################################
        # rain?
        #################################
        rain = event.packet.get('rain')
        if rain is not None:
            raining = 0
            if (rain > 0.0):
                raining = 1
            # Add raining to loop packet
            target_data['raining'] = raining
            if self.debug >= 1:
                logdbg("Rain: %s" % ("YES" if raining > 0 else "NO"))
            for ti in self.timeintervals:
                ti = to_int(ti)
                self.obsvalues['raining'][ti].append(raining)
                avgvalname = 'raining_avg' + str(ti) + 'm'
                target_data[avgvalname] = self.avg_Deque(self.obsvalues['raining'][ti])
                if self.debug >= 3:
                    logdbg("%s=%s, len=%d, avg=%.2f" % (avgvalname, str(self.obsvalues['raining'][ti]),len(self.obsvalues['raining'][ti]),target_data[avgvalname]))
        else:
            if self.debug >= 3:
                logdbg("rain not present!")

        #################################
        # sunshine?
        #################################
        sunshine = event.packet.get('sunshine')
        if sunshine is None:
            sunshine = 0
            radiation = event.packet.get('radiation')
            if radiation is not None:
                threshold = event.packet.get('sunshineThreshold')
                if threshold is None:
                    loopDate = event.packet.get('dateTime')
                    threshold = self.sunshineThreshold(loopDate)

                if threshold > 0.0 and radiation > threshold and radiation >= self.radiation_min:
                    sunshine = 1
            elif self.debug >= 3:
                logdbg("radiation not present!")

        if sunshine is not None:
            # Add raining to loop packet
            #target_data['sunshine'] = sunshine

            if self.debug >= 1:
                logdbg("Sunshine: %s" % ("YES" if sunshine > 0 else "NO"))

            for ti in self.timeintervals:
                ti = to_int(ti)
                self.obsvalues['sunshine'][ti].append(sunshine)
                avgvalname = 'sunshine_avg' + str(ti) + 'm'
                target_data[avgvalname] = self.avg_Deque(self.obsvalues['sunshine'][ti])
                if self.debug >= 3:
                    logdbg("%s=%s, len=%d, avg=%.2f" % (avgvalname, str(self.obsvalues['sunshine'][ti]),len(self.obsvalues['sunshine'][ti]),target_data[avgvalname]))

        #################################
        # Fog?
        #################################
        #################################
        # Snow?
        #################################
        #dewpoint = event.packet.get('dewpoint', None)
        #outTemp = event.packet.get('outTemp', None)
        #outHumidity = event.packet.get('outHumidity', None)
        #windSpeed = event.packet.get('windSpeed', None)

        # Add values to LOOP
        event.packet.update(target_data)
        if self.debug >= 2:
            logdbg('modded loop: %s' % event.packet)
