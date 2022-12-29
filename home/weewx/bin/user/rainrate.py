"""
rainrate.py

Copyright (C)2022 by John A Kline (john@johnkline.com)
Distributed under the terms of the GNU Public License (GPLv3)

weewx-rainrate is a WeeWX service that attempts to produce a
"better" rainRate in loop packets (and archive records) for
siphon tipping bucket rain gauges.

This extension will be useful for tipping
rain gauges that use a siphon for better accuracy over a wide
range of rainfall.  These industrial gauges maintain their
accuracy over a wide range of rain intensity, but are
unsuitable for computing rain rate via the time
between two tips.  The reason for the unsuitability is that
a single discharge of the siphon may result in multiple tips
(in close sucession).  The result of two tips in close
succession will be a wildly overstated rain rate.

The impetus for this extension was the author's purchase of a
HyQuest Solutions TB3 tipping rain gauge with siphon.  It is
accurate to 2% at any rain intensity, but with the siphon, two
tips can come in quick succession.

The extension was tested with a HyQuest Solutions TB3 siphon
tipping bucket rain gauge and using a HyQuest Solutions TB7 (non-siphon)
tipping bucket rain gauge as a reference (for rain rate).
"""

import logging
import sys
import time

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import weewx
import weewx.manager
import weeutil.logger


from weeutil.weeutil import timestamp_to_string
from weeutil.weeutil import to_bool
from weeutil.weeutil import to_int
from weewx.engine import StdService

# get a logger object
log = logging.getLogger(__name__)

RAINRATE_VERSION = '0.19'

if sys.version_info[0] < 3 or (sys.version_info[0] == 3 and sys.version_info[1] < 7):
    raise weewx.UnsupportedFeature(
        "weewx-rainrate requires Python 3.7 or later, found %s.%s" % (sys.version_info[0], sys.version_info[1]))

if weewx.__version__ < "4":
    raise weewx.UnsupportedFeature(
        "weewx-rainrate requires WeeWX, found %s" % weewx.__version__)

@dataclass
class RainEntry:
    """A list of RainEntry is kept for the last 15 minutes."""
    timestamp : int   # timestamp when this rain occurred
    amount    : float # amount of rain
    expiration: int   # timestamp at which this entry should be removed (30m later)

@dataclass
class LoopRainRate:
    """A list of rain rates, used to compute rate for archive record."""
    timestamp: int
    rainRate : float

class RainRate(StdService):
    """RainRate keep track of rain in loop pkts and updates each loop pkt with rainRate."""
    def __init__(self, engine, config_dict):
        """Init RainRate instance and bind to PRE_LOOP and NEW_LOOP_PACKET."""
        super(RainRate, self).__init__(engine, config_dict)
        log.info("Service version is %s." % RAINRATE_VERSION)

        # Only continue if >= the prereq Python version.
        if sys.version_info[0] < 3 or (sys.version_info[0] == 3 and sys.version_info[1] < 7):
            raise Exception("Python 3.7 or later is required for the rainrate plugin.")

        # Only continue if the plugin is enabled.
        rainrate_config_dict = config_dict.get('RainRate', {})
        enable = to_bool(rainrate_config_dict.get('enable'))
        if enable:
            log.info("RainRate is enabled...continuing.")
        else:
            log.info("RainRate is disabled. Enable it in the RainRate section of weewx.conf.")
            return

        # List of rain events, including when they "expire" (15m later).
        self.rain_entries : List[RainEntry] = []

        # Save computed loop rain rates (for determining archive record rain rate).
        self.loop_rain_rates: List[LoopRainRate] = []

        # Flag used to gather up archive records in pre_loop only once (at startup).
        self.initialized = False

        self.bind(weewx.PRE_LOOP, self.pre_loop)
        self.bind(weewx.NEW_LOOP_PACKET, self.new_loop)
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

    def pre_loop(self, event):
        """At WeeWX start, gather up the rain in 15m of archive records and same them
          in rain_entries."""
        if self.initialized:
            return
        self.initialized = True

        try:
            binder = weewx.manager.DBBinder(self.config_dict)
            binding = self.config_dict.get('StdReport')['data_binding']
            dbm = binder.get_manager(binding)
            # Get the column names of the archive table.
            archive_columns: List[str] = dbm.connection.columnsOf('archive')

            # Get last n seconds of archive records.
            earliest_time: int = to_int(time.time()) - 900

            log.debug('Earliest time selected is %s' % timestamp_to_string(earliest_time))

            # Fetch the records.
            start = time.time()
            archive_pkts: List[Dict[str, Any]] = RainRate.get_archive_packets(
                dbm, archive_columns, earliest_time)

            # Save rain events (if any).
            pkt_count = 0
            for pkt in archive_pkts:
                pkt_time = pkt['dateTime']
                if 'rain' in pkt and pkt['rain'] is not None and pkt['rain'] > 0.0:
                    self.rain_entries.append(RainEntry(timestamp = pkt_time, amount = pkt['rain'], expiration = pkt_time + 900))
                    pkt_count += 1
            log.debug('Collected %d archive packets containing rain in %f seconds.' % (pkt_count, time.time() - start))
        except Exception as e:
            # Print problem to log and give up.
            log.error('Error in RainRate setup.  RainRate is exiting. Exception: %s' % e)
            weeutil.logger.log_traceback(log.error, "    ****  ")

    @staticmethod
    def get_archive_packets(dbm, archive_columns: List[str],
            earliest_time: int) -> List[Dict[str, Any]]:
        """At startup, gather previous 15 of rain."""
        packets = []
        for cols in dbm.genSql('SELECT * FROM archive' \
                ' WHERE dateTime > %d ORDER BY dateTime ASC' % earliest_time):
            pkt: Dict[str, Any] = {}
            for i in range(len(cols)):
                pkt[archive_columns[i]] = cols[i]
            packets.append(pkt)
            log.debug('get_archive_packets: pkt(%s): %s' % (
                timestamp_to_string(pkt['dateTime']), pkt))
        return packets

    def new_loop(self, event):
        """ Record rain, compute rainRate and add/update rainRate in the pkt."""
        pkt: Dict[str, Any] = event.packet

        assert event.event_type == weewx.NEW_LOOP_PACKET
        log.debug(pkt)

        # Add rain (if any) to rain_entries, also delete expired entries.
        RainRate.add_packet(pkt, self.rain_entries)

        # Compute a rainRate and add it to the pkt.
        RainRate.compute_rain_rate(pkt, self.rain_entries)

        # Save the computed rain rates (to be used to compute archive rain rate.
        self.loop_rain_rates.append(LoopRainRate(
            timestamp = pkt['dateTime'],
            rainRate  = pkt['rainRate2']))

    def new_archive_record(self, event):
        """ Overwrite archive rainRate with current rainRate."""
        record: Dict[str, Any] = event.record

        assert event.event_type == weewx.NEW_ARCHIVE_RECORD
        log.debug(record)

        # Consume the loop rain rates in loop_rain_rates that
        # are for this archive record's period.
        # Pick the highest rain rate for the archive record.
        archive_rain_rate: Optional[float] = None
        while len(self.loop_rain_rates) != 0 and self.loop_rain_rates[0].timestamp <= record['dateTime']:
            if archive_rain_rate is None or self.loop_rain_rates[0].rainRate > archive_rain_rate:
                archive_rain_rate = self.loop_rain_rates[0].rainRate
            self.loop_rain_rates.pop(0)

            if archive_rain_rate is None:
                # We have no help from loop records (it's probably an archive record during catchup (when WeeWX restarted).
                # We'll average the rain reported in the archive record over 15m.
                archive_rain_rate = record['rain'] / 900.0

        # TODO: Verify that this archive record is received in the same units as loop data (i.e., before any conversion that might be needed).

        record['rainRate2'] = archive_rain_rate

    @staticmethod
    def add_packet(pkt, rain_entries):
        """If the pkt contains rain, add a new RainEntry to rain_entries (add to
        the beginning) and include the timestamp and an expiration (15m later).
        Also, delete any expired entries in rain_entries."""

        # Process new packet.  Be careful, the first time through, pkt['rain'] may be None.
        pkt_time: int       = to_int(pkt['dateTime'])
        if 'rain' in pkt and pkt['rain'] is not None and pkt['rain'] > 0.0:
            pkt_rain = pkt['rain']
            if len(rain_entries) == 0:
                rain_entries.insert(0, RainEntry(timestamp = pkt_time, amount = 0.01, expiration = pkt_time + 1800))
                pkt_rain = pkt_rain - 0.01
                if pkt_rain > 0.001:
                    # We have a multiple tip on the first tip of the storm.  Put the rest of the rain 900s ago, just beyond
                    # the 15m span.
                    rain_entries.append(RainEntry(timestamp = pkt_time - 900, amount = pkt_rain, expiration = pkt_time + 900))
            elif pkt_rain < 0.011:
                    rain_entries.insert(0, RainEntry(timestamp = pkt_time, amount = pkt_rain, expiration = pkt_time + 1800))
            else:
                # Spread the rain over equally (in halves) from last rain in rain_entries.
                earlier_pkt_time: int = pkt_time - ((pkt_time - rain_entries[0].timestamp) / 2)
                rain_entries.insert(0, RainEntry(timestamp = earlier_pkt_time, amount = pkt_rain / 2.0, expiration = earlier_pkt_time + 1800))
                rain_entries.insert(0, RainEntry(timestamp = pkt_time, amount = pkt_rain / 2.0, expiration = pkt_time + 1800))

        # Delete any entries that have matured.
        while len(rain_entries) > 0 and rain_entries[-1].expiration <= pkt_time:
            del rain_entries[-1]

    @staticmethod
    def compute_rain_rate(pkt, rain_entries):
        """Add/update rainRate in packet"""

        if len(rain_entries) < 2:
            pkt['rainRate2'] = 0.0
        else:
            # Immediately after a bucket tip, the rainRate is entirely composed of:
            # 3600 * last_tip_amount / (time_of_last_tip - time_of_next_to_last_tip)
            rainRate1 = 3600 * rain_entries[0].amount / (rain_entries[0].timestamp - rain_entries[1].timestamp)
            rainRate2 = 3600 * rain_entries[0].amount / (pkt['dateTime'] - rain_entries[1].timestamp)
            # As time passes, rainRate2 becomes more prominent
            secs_since_last_tip = pkt['dateTime'] - rain_entries[0].timestamp
            if secs_since_last_tip >= 900.0:
                factor1, factor2 = 0.0, 1.0
            else:
                factor2 = (secs_since_last_tip / 900.0) ** 2
                factor1 = 1 - factor2
            pkt['rainRate2'] = rainRate1 * factor1 + rainRate2 * factor2
        log.debug('new_loop(%d): Added/updated pkt[rainRate2] of %f' % (pkt['dateTime'], pkt['rainRate2']))
