#
# Copyright (c) 2013-2016  Nick Dajda <nick.dajda@gmail.com>
#
# Distributed under the terms of the GNU GENERAL PUBLIC LICENSE
#
"""Extends the Cheetah generator search list to add html historic data tables in a nice color scheme.

Tested on Weewx release 4.10.2.
Works with all databases.
Observes the units of measure and display formats specified in skin.conf.

WILL NOT WORK with Weewx prior to release 3.0.
  -- Use this version for 2.4 - 2.7:  https://github.com/brewster76/fuzzy-archer/releases/tag/v2.0

To use it, add this generator to search_list_extensions in skin.conf:

[CheetahGenerator]
    search_list_extensions = user.historygenerator.MyXSearch

1) The $alltime tag:

Allows tags such as $alltime.outTemp.max for the all-time max
temperature, or $seven_day.rain.sum for the total rainfall in the last
seven days.

2) Nice colorful tables summarising history data by month and year

Check out the preconfigured skin.conf [HistoryReport] Section
"""

from datetime import datetime
import time
import logging
import os.path

from configobj import ConfigObj

from weewx.cheetahgenerator import SearchList
from weewx.tags import TimespanBinder
import weeutil.weeutil
import weewx.units

log = logging.getLogger(__name__)

class MyXSearch(SearchList):
    def __init__(self, generator):
        SearchList.__init__(self, generator)

        self.table_dict = generator.skin_dict['HistoryReport']
        self.color_dict = generator.skin_dict['HistoryColors']

        self.units_dict = generator.skin_dict['Units']

        # Calculate the tables once every refresh_interval mins
        self.refresh_interval = int(self.table_dict.get('refresh_interval', 5))
        self.cache_time = 0

        self.search_list_extension = {}

        # Make some config available to templates
        self.add_to_extension_list('BootstrapLabels', generator.skin_dict)
        self.add_to_extension_list('Labels', generator.skin_dict)
        self.add_to_extension_list('Units', generator.skin_dict)
        self.add_to_extension_list('LiveGauges', generator.skin_dict)
        self.add_to_extension_list('Stats', generator.skin_dict)
        self.add_to_extension_list('LiveCharts', generator.skin_dict)
        self.add_to_extension_list('locale', generator.skin_dict)

        # Make ImageGenerator specific labels in config file available to templates
        image_dict = {}
        image_config_path = os.path.join(generator.config_dict['WEEWX_ROOT'], generator.config_dict['StdReport']['SKIN_ROOT'],
                                         'Bootstrap', "skin.conf")
        try:
            image_dict = ConfigObj(image_config_path)
        except:
            log.info("%s: Could not import image dictionary %s" %
                     os.path.basename(__file__), image_config_path)
        self.add_to_extension_list('ImageGenerator', image_dict)

    def add_to_extension_list(self, key, source):
        if key in source:
            self.search_list_extension[key] = source[key]
        else:
            log.debug("%s: No %s specific labels found" % (key, os.path.basename(__file__)))

    def get_extension_list(self, valid_timespan, db_lookup):
        """For weewx V3.x extensions. Should return a list
        of objects whose attributes or keys define the extension.

        valid_timespan:  An instance of weeutil.weeutil.TimeSpan. This will hold the
        start and stop times of the domain of valid times.

        db_lookup: A function with call signature db_lookup(data_binding), which
        returns a database manager and where data_binding is an optional binding
        name. If not given, then a default binding will be used.
        """

        # Time to recalculate?
        if (time.time() - (self.refresh_interval * 60)) > self.cache_time:
            self.cache_time = time.time()

            #
            #  The html history tables
            #

            t1 = time.time()
            ngen = 0
            self.search_list_extension["history_tables"] = []

            for table in self.table_dict.sections:
                noaa = True if table == 'NOAA' else False

                table_options = weeutil.weeutil.accumulateLeaves(self.table_dict[table])


                # Get the binding where the data is allocated
                binding = table_options.get('data_binding', 'wx_binding')

                #
                # The all time statistics
                #

                # If this generator has been called in the [SummaryByMonth] or [SummaryByYear]
                # section in skin.conf then valid_timespan won't contain enough history data for
                # the colorful summary tables. Use the data binding provided as table option.
                alltime_timespan = weeutil.weeutil.TimeSpan(db_lookup(data_binding=binding).first_timestamp, db_lookup(data_binding=binding).last_timestamp)


                # First, get a TimeSpanStats object for all time. This one is easy
                # because the object valid_timespan already holds all valid times to be
                # used in the report. se the data binding provided as table option.
                all_stats = TimespanBinder(alltime_timespan, db_lookup, data_binding=binding, formatter=self.generator.formatter,
                                           converter=self.generator.converter)

                # Now create a small dictionary with keys 'alltime' and 'seven_day':
                self.search_list_extension['alltime'] = all_stats

                # Show all time unless starting date specified
                startdate = table_options.get('startdate', None)
                if startdate is not None:
                    startdate = weeutil.weeutil.startOfDay(int(startdate))
                    table_timespan = weeutil.weeutil.TimeSpan(int(startdate), db_lookup(binding).last_timestamp)
                    table_stats = TimespanBinder(table_timespan, db_lookup, data_binding=binding, formatter=self.generator.formatter,
                                                 converter=self.generator.converter)
                else:
                    table_stats = all_stats

                new_table = self._statsDict(table_options, table_stats, table, binding, NOAA=noaa)
                if new_table is not None:
                    self.search_list_extension["history_tables"].append(new_table)
                    ngen += 1

            t2 = time.time()

            log.info("%s: Generated %d tables in %.2f seconds" %
                     (os.path.basename(__file__), ngen, t2 - t1))

        return [self.search_list_extension]

    def _parseTableOptions(self, table_options, table_name):
        """Create an orderly list containing lower and upper thresholds, cell background and foreground colors
        """
        if table_name == 'NOAA':
            return 'NOAA', None

        obs_type = table_options.get('obs_type')
        colors_key = obs_type

        unit = self.units_dict["Groups"][weewx.units.obs_group_dict[obs_type]]
        if "colors" in table_options:
            colors_key = table_options.get("colors")[0]
            unit = table_options.get("colors")[1]

        if colors_key in self.color_dict and unit in self.color_dict[colors_key]:
            table_colors = self.color_dict[colors_key][unit]
        else:
            log.info("No colors defined for %s" % table_name)
            table_colors = {"minvalues": [0], "maxvalues": [0], "colors": ["#ffffff"]}

        # Check everything's the same length
        l = len(table_colors['minvalues'])

        for i in [table_colors['maxvalues'], table_colors['colors']]:
            if len(i) != l:
                log.info("%s: minvalues, maxvalues and colors must have the same number of elements in table: %s"
                         % (os.path.basename(__file__), table_name))
                return None, None

        summary_colors = None
        if colors_key in self.color_dict and unit in self.color_dict[colors_key] and "summary" in self.color_dict[colors_key][unit]:
            summary_colors = self.color_dict[colors_key][unit]["summary"]

            # Check everything's the same length
            l = len(summary_colors['minvalues'])

            for i in [summary_colors['maxvalues'], summary_colors['colors']]:
                if len(i) != l:
                    log.info("%s: minvalues, maxvalues and colors must have the same number of elements in table: %s[summary]"
                             % (os.path.basename(__file__), table_name))
                    return None, None

        font_color_list = table_colors['fontColors'] if 'fontColors' in table_colors else ['#000000'] * l
        cell_colors = list(zip(table_colors['minvalues'], table_colors['maxvalues'], table_colors['colors'], font_color_list))

        summary_cell_colors = None
        if None is not summary_colors:
            font_color_list = summary_colors['fontColors'] if 'fontColors' in summary_colors else ['#000000'] * l
            summary_cell_colors = list(zip(summary_colors['minvalues'], summary_colors['maxvalues'], summary_colors['colors'], font_color_list))

        return cell_colors, summary_cell_colors

    def _statsDict(self, table_options, table_stats, table, binding, NOAA=False):
        """
        table_options: Dictionary containing skin.conf options for particluar table
        all_stats: Link to all_stats TimespanBinder
        """

        cell_colors, summary_cell_colors = self._parseTableOptions(table_options, table)

        table_name = table + '_table'
        summary_column = weeutil.weeutil.to_bool(table_options.get("summary_column", False))

        if None is cell_colors:
            log.error("Cell colors are not defined for [HistoryTable]%s" % table)
            return None

        if None is summary_cell_colors:
            summary_cell_colors = cell_colors

        unit_formatted = ""
        unit_type = None

        if NOAA is False:
            obs_type = table_options['obs_type']
            aggregate_type = table_options['aggregate_type']
            converter = table_stats.converter

            # obs_type
            reading_binder = getattr(table_stats, obs_type)

            # Some aggregate come with an argument
            if aggregate_type in ['max_ge', 'max_le', 'min_ge', 'min_le',
                                  'sum_ge', 'sum_le', 'avg_ge', 'avg_le']:

                try:
                    threshold_value = float(table_options['aggregate_threshold'][0])
                except KeyError:
                    log.info("%s: Problem with aggregate_threshold. Should be in the format: [value], [units]" %
                             (os.path.basename(__file__)))
                    return "Could not generate table %s" % table_name

                threshold_units = table_options['aggregate_threshold'][1]

                try:
                    reading = getattr(reading_binder, aggregate_type)((threshold_value, threshold_units, weewx.units.obs_group_dict[obs_type]))
                except IndexError:
                    log.info("%s: Problem with aggregate_threshold units: %s" % (os.path.basename(__file__),
                                                                                 str(threshold_units)))
                    return "Could not generate table %s" % table_name
            else:
                try:
                    reading = getattr(reading_binder, aggregate_type)
                except KeyError:
                    log.info("%s: aggregate_type %s not found" % (os.path.basename(__file__),
                                                                  aggregate_type))
                    return "Could not generate table %s" % table_name

            try:
                unit_type = reading.converter.group_unit_dict[reading.value_t[2]]
            except KeyError:
                log.info("%s: obs_type %s no unit found" % (os.path.basename(__file__),
                                                            obs_type))

            # 'units' option in skin.conf?
            if 'units' in table_options:
                unit_formatted = table_options['units']
            else:
                if unit_type in reading.formatter.unit_label_dict:
                    unit_formatted = reading.formatter.unit_label_dict[unit_type]

            # For aggregrate types which return number of occurrences (e.g. max_ge), set format to integer

            # Don't catch error here - we absolutely need the string format
            if None is unit_type or unit_type == 'count':
                format_string = '%d'
            else:
                format_string = reading.formatter.unit_format_dict[unit_type]

        header_text = table_name + "header_text"

        if "header_text" in table_options:
            header_text = table_options["header_text"]

        table_dict = {
            "noaa": NOAA,
            "header_text": header_text,
            "header": {"head": unit_formatted, "values": ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']},
            "lines": []}

        if NOAA is False and summary_column:
            table_dict["header"]["summary"] = 'Year'

        for year in table_stats.years():
            year_number = datetime.fromtimestamp(year.timespan[0]).year
            value = {"value": str(year_number)}
            if NOAA is True:
                dt = datetime.fromtimestamp(year.timespan[0])
                value["url"] = dt.strftime(table_options['year_filename'])
            line = {"head": value, "values": []}

            for month in year.months():
                if NOAA is True:
                    noaa_value = {"value": ""}
                    if (month.timespan[1] >= table_stats.timespan.start) and (month.timespan[0] <= table_stats.timespan.stop):
                        dt = datetime.fromtimestamp(month.timespan[0])
                        noaa_value["value"] = dt.strftime("%m-%y")
                        noaa_value["url"] = dt.strftime(table_options['month_filename'])
                    line["values"].append(noaa_value)
                else:
                    # update the binding to access the right DB
                    obs_month = getattr(month, obs_type)
                    obs_month.data_binding = binding
                    if unit_type == 'count':
                        value = self.getCount(obs_month, aggregate_type,threshold_value, threshold_units, obs_type)
                    elif unit_type is not None:
                        value = converter.convert(getattr(obs_month, aggregate_type).value_t)
                    else:
                        log.error("Error in [HistoryReport][[%s]]: check units" % table)
                        return None

                    line["values"].append(self._colorCell(value[0], format_string, cell_colors))

            if summary_column:
                obs_year = getattr(year, obs_type)
                obs_year.data_binding = binding

                if unit_type == 'count':
                    value = self.getCount(obs_year, aggregate_type,threshold_value, threshold_units, obs_type)
                else:
                    value = converter.convert(getattr(obs_year, aggregate_type).value_t)

                line["summary"] = self._colorCell(value[0], format_string, summary_cell_colors)

            table_dict["lines"].append(line)

        return table_dict
    
    def getCount(self, obs_month, aggregate_type,threshold_value, threshold_units, obs_type):
        try:
           return getattr(obs_month, aggregate_type)((threshold_value, threshold_units, weewx.units.obs_group_dict[obs_type])).value_t
        except:
           return [0, 'count']

    def _colorCell(self, value, format_string, cell_colors):
        """Returns a '<div style= background-color: XX; color: YY"> z.zz </div>' html table entry string.

        value: Numeric value for the observation
        format_string: How the numberic value should be represented in the table cell.
        cellColors: An array containing 4 lists. [minvalues], [maxvalues], [background color], [foreground color]
        """
        cell = {"value": "", "bgcolor": "", "fontcolor": ""}
        if value is not None:
            for c in cell_colors:
                if (value >= float(c[0])) and (value < float(c[1])):
                    cell["bgcolor"] = c[2]
                    cell["fontcolor"] = c[3]
                    break
            cell["value"] = format_string % value
        return cell