"""
rainrate.py

Copyright (C)2020 by John A Kline (john@johnkline.com)
Distributed under the terms of the GNU Public License (GPLv3)

weewx-rainrate is a WeeWX service that attempts to produce a
"better" rainRate in loop packets.

The impetus for this extension is that author purchased a
high quality HyQuest Solutions TB3 siphoning rain gauge.
It is accurate to 2% at any rain intensity, but with the
siphon, two tips can come in quick succession.  As such
the rainRate produced by measuring the time delta between
two tips can be wildly overstated.

weewx-rainrate ignores the rainRate in the loop packet (if present)
by overwriting/inserting rainRate to be the max of the
3 through 15m rain rate (in 30s increments)  as computed by the extension.

For low rain cases:

If there was just one bucket tip (in the first 30s), we would see a rate of 1.2
selected (which is absurdly high).  For cases where 0.01 is observed in the
last 15m, no matter when in that 15m it occurred, only the 15m bucket is considered
(rate of 0.04).

Similarly, for cases where only 0.02 has been observed in the last 15m, the
30s-9.5m buckets will report unreasonably high rates, so they will not be
considered.

Lasttly, for cases where 0.03 has been observed in the last 15m, the 30s-4.5m
buckets will not be considered.
"""

import logging
import sys
import time

from dataclasses import dataclass
from typing import Any, Dict, List

import weewx
import weewx.manager
import weeutil.logger


from weeutil.weeutil import timestamp_to_string
from weeutil.weeutil import to_bool
from weeutil.weeutil import to_int
from weewx.engine import StdService

# get a logger object
log = logging.getLogger(__name__)

RAIN24H_VERSION = '0.12'

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
    expiration: int   # timestamp at which this entry should be removed


class RainRate(StdService):
    """RainRate keep track of rain in loop pkts and updates each loop pkt with rainRate."""
    def __init__(self, engine, config_dict):
        """Init RainRate instance and bind to PRE_LOOP and NEW_LOOP_PACKET."""
        super(RainRate, self).__init__(engine, config_dict)
        log.info("Service version is %s." % RAIN24H_VERSION)

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

        # Flag used to gather up archive records in pre_loop only once (at startup).
        self.initialized = False

        self.bind(weewx.PRE_LOOP, self.pre_loop)
        self.bind(weewx.NEW_LOOP_PACKET, self.new_loop)

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

        # Log rain (to be used in simulation testing.
        if 'rain' in pkt and pkt['rain'] is not None and pkt['rain'] > 0.0:
            log.info('rain event: %d %f (%r)' % (pkt['dateTime'], pkt['rain'], pkt['rainRate']))

        # Process new packet.
        # Add rain (if any) to rain_entries, also delete expired entries.
        RainRate.add_packet(pkt, self.rain_entries)
        # Compute a rainRate and add it to the pkt.
        RainRate.compute_rain_rate(pkt, self.rain_entries)

    @staticmethod
    def add_packet(pkt, rain_entries):
        """If the pkt contains rain, add a new RainEntry to rain_entries (add to
        the beginning) and include the timestamp and an expiration (15m later).
        Also, delete any expired entries in rain_entries."""

        # Process new packet.  Be careful, the first time through, pkt['rain'] may be None.
        pkt_time: int       = to_int(pkt['dateTime'])
        if 'rain' in pkt and pkt['rain'] is not None and pkt['rain'] > 0.0:
            pkt_time = pkt['dateTime']
            rain_entries.insert(0, RainEntry(timestamp = pkt_time, amount = pkt['rain'], expiration = pkt_time + 900))
            log.debug('pkt_time: %d, found rain of %f.' % (pkt_time, pkt['rain']))

        # Debit and remove any entries that have matured.
        while len(rain_entries) > 0 and rain_entries[-1].expiration <= pkt_time:
            del rain_entries[-1]

    @staticmethod
    def compute_rain_buckets(pkt, rain_entries)->List[float]:
        """ Accumulate rate in 30s buckets (which are cumulative); e.g., for
            the 9.5m bucket, all rain in the last 9.5m is reflected in it's value."""
        pkt_time = pkt['dateTime']
        rain_buckets = [ 0.0 ] * 31 # cell 0 will remain 0.0 as we're only using buckets 1-30.
        for entry in rain_entries:
            for bucket in range(1, 31):
                if pkt_time - entry.timestamp < bucket * 30:
                    rain_buckets[bucket] += entry.amount
        return rain_buckets

    @staticmethod
    def eliminate_buckets(rain_buckets):
        """ Eliminate (i.e., zero out) any buckets that our algorithm requires us
            not to consider.  This includes:
            1. Always eliminate the 30s through 2.5m buckets (inclusive).
            2. If total rain in the last 15m is 0.01,
               - Eliminate buckets up to and including 14.5m.
            3. If total rain in the last 15m is 0.02,
               - Eliminate buckets up to and including 9.5m.
            4. If total rain in the last 15m is 0.03,
               - Eliminate buckets up to and including 4.5m."""

        # Zero out the 30s-2.5m (1-3) buckets as it is thought they will always be too noisy.
        for i in range(1,6):
            rain_buckets[i] = 0.0

        # The total amount of rain in the last 15m will be reflected in the last (15m) bucket.
        total_rain = rain_buckets[30]

        # Consider low rain cases.
        #
        # If there was just one bucket tip (in the first two minutes), we would see a rate of 0.3
        # selected (which is absurdly high).  As such, we'll only consider the 15m bucket
        # (rate of 0.04).
        #
        # Similarly, for cases where only 0.02 has been observed in the last 15m, the
        # 2-9.5m buckets will report unreasonably high rates, so zero them out.
        #
        # Lasttly, for cases where 0.03 has been observed in the last 15m, zero out the
        # 3-4.5m buckets.
        if total_rain == 0.01:
            # Zero everthing but bucket 30.
            for bucket in range(6, 30):
                rain_buckets[bucket] = 0.0
        elif total_rain  == 0.02:
            # Zero buckets 2-19.
            for bucket in range(6, 20):
                rain_buckets[bucket] = 0.0
        elif total_rain  == 0.03:
            # Zero buckets 6-9.
            for bucket in range(6, 10):
                rain_buckets[bucket] = 0.0

    @staticmethod
    def compute_rain_rates(rain_buckets)->List[float]:
        """ Rain rates are computed simply by dividing the rain by the time span (and
        multiplying by the number of seconds in a hour (to get an hourly rate).
        Rain rates are rounded to three decimals."""
        rain_rates = [ 0.0 ] * 31
        for bucket in range(1, 31):
            rain_rates[bucket] = round(3600.0 * rain_buckets[bucket] / (bucket * 30), 3)
        return rain_rates

    @staticmethod
    def compute_rain_rate(pkt, rain_entries):
        """Add/update rainRate in packet"""

        rain_buckets = RainRate.compute_rain_buckets(pkt, rain_entries)
        RainRate.eliminate_buckets(rain_buckets)
        rainrates = RainRate.compute_rain_rates(rain_buckets)

        pkt['rainRate'] = max(rainrates)
        log.debug('new_loop(%d): raterates: %r' % (pkt['dateTime'], rainrates))
        log.debug('new_loop(%d): Added/updated pkt[rainRate] of %f' % (pkt['dateTime'], pkt['rainRate']))
