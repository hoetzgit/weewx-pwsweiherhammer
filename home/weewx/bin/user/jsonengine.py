# -*- coding: utf-8 -*-
#    See the file LICENSE.txt for your rights.
#    Author: Michael Kainzbauer (github: mkainzbauer)
"""generator for configuration and initializing live data skin

Tested on Weewx release 4.10.1.
Tested with sqlite, may not work with other databases.

Directions for use:

1) Put this file in the weewx/bin/user directory.
2) Add user.jsonengine.JSONGenerator to the list of Generators in skin.conf.
3) Add a [JSONGenerator] section to skin.conf.
   Any data contained in this section are created when the report generator
   runs.
4) Object member names must match the Weewx field name, e.g. outTemp or barometer
5) Here is an example [JSONGenerator] section:

############################################################################################
#
# Settings for JSON Generator
#
TODO: example
"""
import sys
import time
import logging
import json
import os.path

import weeutil.weeutil
import weewx.reportengine
from weewx.units import convert

from user.sunevents import SunEvents

log = logging.getLogger(__name__)

class JSONGenerator(weewx.reportengine.ReportGenerator):
    """Class for managing the JSON generator."""

    def run(self):
        enabled = False
        try:
            enabled = self.skin_dict['JSONGenerator']['enabled'].lower() == 'true'
        except KeyError:
            log.info("JSONGenerator failed to read config or config missing")
        else:
            if enabled:
                self.setup()
                self.gen_data()
            else:
                log.info("JSONGenerator is not enabled")
    def setup(self):
        self.json_dict = self.skin_dict['JSONGenerator']
        self.gauge_dict = self.skin_dict['LiveGauges']
        self.chart_dict = self.skin_dict['LiveCharts']
        self.units_dict = self.skin_dict['Units']
        self.labels_dict = self.skin_dict['Labels']
        self.frontend_data = {}

        # Create a converter to get this into the desired units
        self.converter = weewx.units.Converter(self.units_dict['Groups'])

        # Lookup the last reading in the archive
        db_manager = self.db_binder.get_manager()
        self.lastGoodStamp = db_manager.lastGoodStamp()

        self.record_dict_vtd = None
        batch_records = db_manager.genBatchRecords(self.lastGoodStamp - 1, self.lastGoodStamp)

        self.transition_angle = 8
        try:
            self.transition_angle = int(self.chart_dict['transition_angle'])
        except KeyError:
            log.debug('Using default transition_angle %s' % self.transition_angle)

        self.show_daynight = True
        try:
            self.show_daynight = weeutil.weeutil.to_bool(self.chart_dict['show_daynight'])
        except KeyError:
            log.debug('show_daynight is on')

        try:
            for rec in batch_records:
                if self.record_dict_vtd is None:
                    self.record_dict_vtd = rec

        except:
            log.info("JSONGenerator: Cannot find the current reading")

        # For checking development code deals with 'None' readings correctly
        if self.gauge_dict.get('test_none_readings', None) is not None:
            for key, value in list(self.record_dict_vtd.items()):
                self.record_dict_vtd[key] = None

    def gen_data(self):
        start_time = time.time()
        ngen = 0
        unit_systems = {'US': weewx.units.USUnits, 'METRIC': weewx.units.MetricUnits, 'METRICWX': weewx.units.MetricWXUnits}
        source_unit_system = self.config_dict['StdConvert']['target_unit']

        self.frontend_data['config'] = self.json_dict
        self.frontend_data['config']['archive_interval'] = self.config_dict['StdArchive']['archive_interval']

        self.frontend_data['gauges'] = self.gauge_dict
        self.frontend_data['charts'] = self.chart_dict
        self.frontend_data['source_unit_system'] = {'type': source_unit_system}
        for unit_system_item in unit_systems[source_unit_system].items():
            self.frontend_data['source_unit_system'][unit_system_item[0]] = unit_system_item[1]
        self.frontend_data['units'] = self.units_dict
        self.frontend_data['labels'] = self.labels_dict
        live_options = weeutil.weeutil.accumulateLeaves(self.json_dict)

        for gauge in self.gauge_dict.sections:
            data_type = self.gauge_dict[gauge].get('data_type', gauge)
            ret, gauge_history = self.gen_history_data(gauge, data_type, live_options, self.gauge_dict[gauge].get('data_binding', None))
            self.frontend_data['gauges'][gauge]['target_unit'] = self.get_target_unit(gauge)
            self.frontend_data['gauges'][gauge]['obs_group'] = self.get_obs_group(gauge)

            if ret is not None:
                ngen += 1
                log.debug("Adding %s to frontend_data." % gauge)
                self.frontend_data[gauge] = gauge_history
        for chart in self.chart_dict.sections:
            for category in self.chart_dict[chart].sections:
                data_type = self.chart_dict[chart][category].get('data_type', category)
                ret, category_history = self.gen_history_data(category, data_type, live_options, self.chart_dict[chart][category].get('data_binding'))
                self.frontend_data['charts'][chart][category]['target_unit'] = self.get_target_unit(category)
                self.frontend_data['charts'][chart][category]['obs_group'] = self.get_obs_group(category)

                if ret is not None:
                    ngen += 1
                    log.debug("Adding %s to frontend_data." % category)
                    self.frontend_data[category] = category_history

        timespan = int(live_options.get('timespan'))
        first_value_timestamp = self.lastGoodStamp - timespan * 60 * 60
        last_value_timestamp = self.lastGoodStamp

        altitude = self.config_dict['Station']['altitude']
        altitude_m = altitude[0]
        if altitude[1] == 'foot':
            altitude_m = convert(altitude[0], 'meter')[0]
        events = self.get_day_night_events(first_value_timestamp, last_value_timestamp, self.config_dict['Station']['longitude'], self.config_dict['Station']['latitude'], altitude_m)
        self.frontend_data['day_night_events'] = events

        # Write JSON self.frontend_data output if a filename is specified
        data_filename = 'weewxData.json'
        timestamp_filename = 'ts.json'
        html_root = os.path.join(self.config_dict['WEEWX_ROOT'], live_options['HTML_ROOT'])

        if not os.path.exists(html_root):
            os.makedirs(html_root)
        self.write_json(os.path.join(html_root, data_filename))
        self.write_ts_file(os.path.join(html_root, timestamp_filename))

        finish_time = time.time()

        log.info("JSONGenerator: Generated %d data items for %s in %.2f seconds" %
                 (ngen, self.skin_dict['REPORT_NAME'], finish_time - start_time))

    def get_target_unit(self, column_name):
        try:
            return self.units_dict['Groups'][weewx.units.obs_group_dict[column_name]]
        except KeyError:
            log.info("JSONGenerator: self.units_dict['Groups'][weewx.units.obs_group_dict['%s']] is not present, using the empty string." % column_name)
            return ""

    def get_obs_group(self, column_name):
        try:
            return weewx.units.obs_group_dict[column_name]
        except KeyError:
            log.info("JSONGenerator: weewx.units.obs_group_dict['%s'] is not present, using the empty string." % column_name)
            return ""

    def gen_history_data(self, obs_name, column_name, live_options, binding_name):
        log.debug("Generating history for obs_name %s and column_name %s with binding %s" % (obs_name, column_name, binding_name))
        if obs_name in self.frontend_data:
            log.debug("Data for observation %s has already been collected." % obs_name)
            return None, None
        # Find display unit of measure
        try:
            target_unit = self.get_target_unit(column_name)
        except:
            log.info("JSONGenerator: *** Could not find target unit of measure for column '%s' ***" % column_name)
            return 0, None
        try:
            timespan = int(live_options.get('timespan'))
        except:
            logging.exception("Error getting timespan:")
        else:
            history_list = []
            time_list = []

            try:
                if binding_name:
                    db_manager = self.db_binder.get_manager(binding_name)
                else:
                    db_manager = self.db_binder.get_manager()

            except:
                if binding_name:
                    logging.exception("Could not get db_manager for binding %s" % binding_name)
                else:
                    logging.exception("Could not get db_manager for default binding")

            batch_records = db_manager.genBatchRecords(self.lastGoodStamp - timespan * 60 * 60, self.lastGoodStamp)
            for rec in batch_records:
                db_value_tuple = weewx.units.as_value_tuple(rec, column_name)
                if target_unit == "":
                    history_value = rec[column_name]
                else:
                    history_value = weewx.units.convert(db_value_tuple, target_unit)[0]
                try:
                    history_list.append(float(history_value))
                    time_list.append(rec['dateTime'] * 1000)
                except:
                    log.debug("JSONGenerator: Cannot decode reading of '%s' for column '%s'" % (history_value, column_name))

        log.debug("returning history list")
        return 1, list(zip(time_list, history_list))

    def write_json(self, data_filename):

        try:
            fp = open(data_filename, 'w')
        except IOError:
            log.error("JSONGenerator: Could not open %s for writing" % data_filename)
        else:
            with fp:
                json_string = json.dumps(self.frontend_data, indent=None)
                fp.write(json_string)

    def write_ts_file(self, timestamp_filename):
        try:
            fp = open(timestamp_filename, 'w')
        except IOError:
            log.error("JSONGenerator: Could not open %s for writing" % timestamp_filename)
        else:
            with fp:
                fp.write('{"lastGoodStamp":"' + str(self.lastGoodStamp) + '"}')


    def get_day_night_events(self, start, end, lon, lat, altitude_m):
        if 'ephem' not in sys.modules or not self.show_daynight:
            return []

        events = SunEvents(start, end, lon, lat, int(altitude_m)).get_transits(self.transition_angle)
        for event in events:
            event[0] = event[0] * 1000
            angle = event[1]
            darkening_extent = abs(((event[1] - self.transition_angle) / 2) / self.transition_angle)
            if angle >= self.transition_angle:
                darkening_extent = 0
            if angle <= -self.transition_angle:
                darkening_extent = 1
            event[1] = darkening_extent
        return events