"""
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
"""

VERSION = "0.3.1"

import syslog
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

        currenthelper_dict = config_dict.get('CurrentHelper', {})
        enable = to_bool(currenthelper_dict.get('enable', 'false'))
        if enable:
            loginf("Service is enabled.")
        else:
            loginf("Service is disabled. Enable it in the CurrentHelper section of weewx.conf.")
            return

        # inits
        self.last_strikes_total = None
        self.debug = to_int(currenthelper_dict.get('debug', config_dict.get('debug', 0)))
        self.lat = to_float(config_dict.get('latitude', 49.632270))
        self.lon = to_float(config_dict.get('longitude', 12.056186))
        self.radiation_min = to_float(currenthelper_dict.get('radiation_min', 0))
        self.sunshine_coeff_default = to_float(currenthelper_dict.get('sunshine_coeff_default', 1.0))

        sunshine_coeff_monthly = currenthelper_dict.get('sunshine_coeff_monthly')
        if sunshine_coeff_monthly is not None and not isinstance(sunshine_coeff_monthly, list):
            tmplist = []
            tmplist.append(sunshine_coeff_monthly)
            sunshine_coeff_monthly = tmplist
        self.sunshine_coeff_monthly = dict()
        for i in range(0, len(sunshine_coeff_monthly), 1):
            self.sunshine_coeff_monthly[i+1] = float(sunshine_coeff_monthly[i])
        if self.debug >= 2:
            logdbg("sunshine_coeff_monthly %s" % str(self.sunshine_coeff_monthly))

        self.observations = currenthelper_dict.get('observations', 'raining')
        if self.observations is not None and not isinstance(self.observations, list):
            tmplist = []
            tmplist.append(self.observations)
            self.observations = tmplist
        if self.debug >= 2:
            logdbg("Observations %s" % str(self.observations))

        self.timeintervals = currenthelper_dict.get('timeintervals', '10')
        if self.timeintervals is not None and not isinstance(self.timeintervals, list):
            tmplist = []
            tmplist.append(self.timeintervals)
            self.timeintervals = tmplist
        if self.debug >= 2:
            logdbg("Time intervals %s" % str(self.timeintervals))

        self.loopinterval = to_int(currenthelper_dict.get('loopinterval', 16))
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

    @staticmethod
    # calculate sunshine threshold for sunshining yes/no
    def sunshine_Threshold(dateval, lat, lon, coeff):
        utcdate = datetime.utcfromtimestamp(to_int(dateval))
        dayofyear = to_int(time.strftime("%j",time.gmtime(to_int(dateval))))
        theta = 360 * dayofyear / 365
        equatemps = 0.0172 + 0.4281 * cos((pi / 180) * theta) - 7.3515 * sin(
            (pi / 180) * theta) - 3.3495 * cos(2 * (pi / 180) * theta) - 9.3619 * sin(
            2 * (pi / 180) * theta)
        corrtemps = lon * 4
        declinaison = asin(0.006918 - 0.399912 * cos((pi / 180) * theta) + 0.070257 * sin(
            (pi / 180) * theta) - 0.006758 * cos(2 * (pi / 180) * theta) + 0.000908 * sin(
            2 * (pi / 180) * theta)) * (180 / pi)
        minutesjour = utcdate.hour * 60 + utcdate.minute
        tempsolaire = (minutesjour + corrtemps + equatemps) / 60
        angle_horaire = (tempsolaire - 12) * 15
        hauteur_soleil = asin(sin((pi / 180) * lat) * sin((pi / 180) * declinaison) + cos(
            (pi / 180) * lat) * cos((pi / 180) * declinaison) * cos((pi / 180) * angle_horaire)) * (180 / pi)
        if hauteur_soleil > 3:
            seuil = (0.73 + 0.06 * cos((pi / 180) * 360 * dayofyear / 365)) * 1080 * pow(
                sin((pi / 180) * hauteur_soleil), 1.25) * coeff
        else:
            seuil = 0.0
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
                logdbg("Thunderstorm now: %s" % ("yes" if thunderstorm > 0 else "no"))
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
                logdbg("Raining now: %s" % ("yes" if raining > 0 else "no"))
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
            radiation = event.packet.get('radiation')
            if radiation is not None:
                threshold = event.packet.get('sunshineThreshold')
                if threshold is None:
                    loopDate = to_int(target_data.get('dateTime', to_int(datetime.now().timestamp())))
                    monthofyear = to_int(time.strftime("%m", time.gmtime(loopDate)))
                    coeff = self.sunshine_coeff_monthly.get(monthofyear)
                    if coeff is None:
                        logerr("Monthly based coeff is not valid, using coeff_default instead!")
                        coeff = self.sunshine_coeff_default
                    threshold = float(self.sunshine_Threshold(loopDate, self.lat, self.lon, coeff))

                sunshine = 0
                if threshold > 0.0 and radiation > threshold and radiation >= self.radiation_min:
                    sunshine = 1
            elif self.debug >= 3:
                logdbg("radiation not present!")

        if sunshine is not None:
            if self.debug >= 1:
                logdbg("Sun is shining now: %s" % ("yes" if sunshine > 0 else "no"))

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
