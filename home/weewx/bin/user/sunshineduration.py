"""
    Copyright (C) 2022 Henry Ott
    based on code from https://github.com/Jterrettaz/sunduration
    Status: WORK IN PROGRESS

    Adds new observation fields containing sunshine duration
    Condition for calculation:
      - 'sunshine' is present in loop packet and is not None

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

VERSION = "0.1"

DEFAULTS_INI = """
[SunshineDuration]
    enable = true
    debug = 0
    radiation_min = 0.0
"""
defaults_dict = weeutil.config.config_from_str(DEFAULTS_INI)

class SunshineDuration(StdService):
    def __init__(self, engine, config_dict):
        # Pass the initialization information on to my superclass:
        super(SunshineDuration, self).__init__(engine, config_dict)
        loginf("Service version is %s" % VERSION)

        # Get any user-defined overrides
        override_dict = config_dict.get('SunshineDuration', {})
        # Get the default values, then merge the user overrides into it
        option_dict = weeutil.config.deep_copy(defaults_dict['SunshineDuration'])
        option_dict.merge(override_dict)

        # Only continue if the plugin is enabled.
        enable = to_bool(option_dict['enable'])
        if enable:
            loginf("SunshineDuration is enabled...continuing.")
        else:
            loginf("SunshineDuration is disabled. Enable it in the SunshineDuration section of weewx.conf.")
            return
        self.debug = to_int(option_dict.get('debug', 0))
        if self.debug > 0:
            logdbg("debug level is %d" % self.debug)

        # dateTime from the last loop package with valid 'radiation'
        self.lastLoop = None
        # dateTime from the last archive record
        self.lastArchive = None
        # sum sunshineDur within archive interval
        self.sunshineDur = None

        # Start intercepting events:
        self.bind(weewx.NEW_LOOP_PACKET, self.newLoopPacket)
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.newArchiveRecord)

    def newLoopPacket(self, event):
        """Gets called on a new loop packet event."""
        sunshine = event.packet.get('sunshine')
        if sunshine is not None:
            loopdateTime = event.packet.get('dateTime')

            if self.lastLoop is None:
                # It's the first loop packet, more is not to be done
                # To calculate the time we wait for the next loop packet
                # ..L
                self.sunshineDur = 0
                if self.debug >= 3:
                    logdbg("first loop packet with valid 'sunshine' during archive interval received.")
            else:
                # .L....L....L....L
                loopDuration = loopdateTime - self.lastLoop
                loopSunshineDur = 0
                if sunshine > 0:
                    loopSunshineDur = loopDuration
                self.sunshineDur += loopSunshineDur
                if self.debug >= 2:
                    logdbg("LOOP sunshineDur=%d, based on sunshine=%.2f loopDuration=%d loopSunshineDur=%d" % (
                        self.sunshineDur, sunshine, loopDuration, loopSunshineDur))

            self.lastLoop = loopdateTime

        elif self.debug >= 3:
            logdbg("LOOP no calculation, 'sunshine' not in loop packet or is None.")

    def newArchiveRecord(self, event):
        """Gets called on a new archive record event."""
        target_data = {}
        target_data['sunshineDur'] = None
        archivedateTime = event.record.get('dateTime')

        if self.lastArchive is not None and self.lastLoop is not None and self.lastLoop < self.lastArchive:
            # no loop packets with 'sunshine' during the last archive interval
            # ..L....L....L....L....A...........................A
            #                  |????|
            if self.debug >= 3:
                logdbg("No loop packets with valid 'sunshine' values during last archive interval, disacard loop indicator.")
            self.lastLoop = None
            self.sunshineDur = None

        if self.lastLoop is not None and self.sunshineDur is not None:
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
        self.lastArchiv = archivedateTime
    
# Tell the unit system what group our new observation type, 'sunshineDur', belongs to:
weewx.units.obs_group_dict['sunshineDur'] = "group_deltatime"
