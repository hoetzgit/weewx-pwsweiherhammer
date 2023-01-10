"""
rainrate.py

Copyright (C)2022-2023 by John A Kline (john@johnkline.com)
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

RAINRATE_VERSION = '0.32'

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
    dont_merge: bool  # Will be true if this rain entry is written as part of a merge

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

        # Get archive interval
        try:
            std_archive_dict = config_dict.get('StdArchive', {})
            self.archive_interval = to_int(std_archive_dict.get('archive_interval'))
        except Exception as e:
            log.info("Cannot determine archive_interval.  Exiting. (%s)" % e)
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
            archive_recs: List[Dict[str, Any]] = RainRate.get_archive_records(
                dbm, archive_columns, earliest_time)

            # Save rain events (if any).
            rec_count = 0
            for rec in archive_recs:
                if 'rain' in rec and rec['rain'] is not None and rec['rain'] > 0.0000001:
                    rec_count += 1
                    RainRate.archive_records_to_rain_entries(rec, self.archive_interval, self.rain_entries)
            log.debug('Collected %d archive records containing rain in %f seconds.' % (rec_count, time.time() - start))
        except Exception as e:
            # Print problem to log and give up.
            log.error('Error in RainRate setup.  RainRate is exiting. Exception: %s' % e)
            weeutil.logger.log_traceback(log.error, "    ****  ")

    @staticmethod
    def archive_records_to_rain_entries(rec: Dict[str, Any], archive_interval: int, rain_entries: List[RainEntry])->None:
        archive_time = rec['dateTime']
        archive_amt = rec['rain']
        if archive_amt < 0.0100001:
            # Add the single tip midway through archive period.
            rec_time = round(archive_time - (archive_interval / 2.0))
            rain_entries.append(RainEntry(timestamp = rec_time, amount = archive_amt, expiration = rec_time + 1800, dont_merge=True))
        else:
            # Evenly space the tips
            number_of_tips: int = round(archive_amt / 0.01)
            interval: int = round(archive_interval / number_of_tips)
            time_of_rain: int = archive_time
            for _ in range(number_of_tips):
                time_of_rain -= interval
                rain_entries.append(
                    RainEntry(timestamp = time_of_rain, amount = archive_amt / number_of_tips, expiration = time_of_rain + 1800, dont_merge=True))

    @staticmethod
    def get_archive_records(dbm, archive_columns: List[str],
            earliest_time: int) -> List[Dict[str, Any]]:
        """At startup, gather previous 15 of rain."""
        records = []
        for cols in dbm.genSql('SELECT * FROM archive' \
                ' WHERE dateTime > %d ORDER BY dateTime ASC' % earliest_time):
            rec: Dict[str, Any] = {}
            for i in range(len(cols)):
                rec[archive_columns[i]] = cols[i]
            records.append(rec)
            log.debug('get_archive_records: rec(%s): %s' % (
                timestamp_to_string(rec['dateTime']), rec))
        return records

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
            rainRate  = pkt['rainRate']))

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
                # We have no help from loop records--probably an archive record during catchup (when WeeWX restarted).
                # We'll average the rain reported over the length of the archive period.
                archive_rain_rate = record['rain'] / self.archive_interval

        # TODO: Verify that this archive record is received in the same units as loop data (i.e., before any conversion that might be needed).

        record['rainRate'] = archive_rain_rate

    @staticmethod
    def add_packet(pkt, rain_entries, dont_merge=False):
        """If the pkt contains rain, add a new RainEntry to rain_entries (add to
        the beginning) and include the timestamp and an expiration (30m later).
        Also, delete any expired entries in rain_entries."""

        # Process new packet.  Be careful, the first time through, pkt['rain'] may be None.
        pkt_time: int       = to_int(pkt['dateTime'])
        if 'rain' in pkt and pkt['rain'] is not None and pkt['rain'] > 0.0:
            pkt_rain = pkt['rain']
            if pkt_rain > 0.0100001:
                log.info("Multi-tip pkt[%d] rain: %f" % (pkt['dateTime'], pkt['rain']))
            if len(rain_entries) == 0:
                # Record the first tip.  It doesn't matter if it is a multitip as we have no idea when the rain
                # actually accumulated. As such, we'll record it as a single tip (0.01).
                rain_entries.insert(0, RainEntry(timestamp = pkt_time, amount = 0.01, expiration = pkt_time + 1800, dont_merge = dont_merge))
            elif pkt_rain < 0.0100001:
                    # Record the single tip
                    rain_entries.insert(0, RainEntry(timestamp = pkt_time, amount = pkt_rain, expiration = pkt_time + 1800, dont_merge = dont_merge))
            else:
                # Spread the rain over equally (between last tip and now).
                number_of_tips: int = round(pkt_rain / 0.01)
                interval: int = round((pkt_time - rain_entries[0].timestamp) / number_of_tips)
                time_of_rain: int = pkt_time - (interval * (number_of_tips - 1))
                for _ in range(number_of_tips):
                    rain_entries.insert(
                        0, RainEntry(timestamp = time_of_rain, amount = pkt_rain / number_of_tips, expiration = time_of_rain + 1800, dont_merge = dont_merge))
                    time_of_rain += interval

        # If we have rain entries extremely close together, treat as a multi-tip.
        if len(rain_entries) > 1 and not dont_merge and not rain_entries[1].dont_merge and rain_entries[0].timestamp - rain_entries[1].timestamp < 2.5:
            log.info("Merging pkt[%d]rain:%f and pkt[%d]rain:%f" % (rain_entries[1].timestamp, rain_entries[1].amount, rain_entries[0].timestamp, rain_entries[0].amount))
            combined_pkt: Dict[str, Any] = { 'dateTime': pkt_time, 'rain': rain_entries[0].amount + rain_entries[1].amount }
            del rain_entries[0]
            del rain_entries[0]
            RainRate.add_packet(combined_pkt, rain_entries, dont_merge=True)

        # Delete any entries that have matured.
        while len(rain_entries) > 0 and rain_entries[-1].expiration <= pkt_time:
            del rain_entries[-1]

    @staticmethod
    def compute_rain_rate(pkt, rain_entries):
        """Add/update rainRate in packet"""

        if len(rain_entries) < 2:
            pkt['rainRate'] = 0.0
        else:
            # Rain rate between the last two tips.
            rainRate1 = 3600 * rain_entries[0].amount / (rain_entries[0].timestamp - rain_entries[1].timestamp)
            # Rain rate imagining that there was a tip in the current packet (as such, between now and the actual last tip).
            rainRate2 = 10000.0 # Pick a silly large number as we take the min below.
            if pkt['dateTime'] != rain_entries[0].timestamp:
                rainRate2 = 3600 * 0.01 / (pkt['dateTime'] - rain_entries[0].timestamp)
            # Pick the lower of the two rates.
            pkt['rainRate'] = min(rainRate1, rainRate2)
            if pkt['rainRate'] < 0.035:
                pkt['rainRate'] = 0.0
        log.debug('new_loop(%d): Added/updated pkt[rainRate] of %f' % (pkt['dateTime'], pkt['rainRate']))
