#
# Copyright (c) 2013-2016  Nick Dajda <nick.dajda@gmail.com>
#
# Distributed under the terms of the GNU GENERAL PUBLIC LICENSE
#
# 2022-10-10 Henry Ott
# This version was modified to better fit my WeeWX installation with the Belchertown skin.
#
"""Extends the Cheetah generator search list to add html historic data tables in a nice colour scheme.

Tested on Weewx release 4.8.0
Works with all databases.
Observes the units of measure and display formats specified in skin.conf.

WILL NOT WORK with Weewx prior to release 3.0.
  -- Use this version for 2.4 - 2.7:  https://github.com/brewster76/fuzzy-archer/releases/tag/v2.0

To use it, add this generator to search_list_extensions in skin.conf:

[TableGenerator]
    search_list_extensions = user.tablegenerator.TableGenerator

1) Nice colourful tables summarising history data by month and year:

Adding the section below to your skins.conf file will create these new tags:
   $min_temp_table
   $max_temp_table
   $avg_temp_table
   $rain_table
   $noaa_table
etc.

############################################################################################
#
# HTML month/year colour coded summary table generator
#
[TableGenerator]
    # original: https://github.com/brewster76/fuzzy-archer/blob/master/bin/user/historygenerator.py
    # Set to 1 for extra debug info, otherwise comment it out or set to zero
    debug = 1
    # refresh in minutes
    refresh_interval = 20
    # table_type [normal|noaa]
    table_type = normal
    data_binding = wx_binding
    year_heading = Jahr
    summary_column = true
    summary_colored = false
    monthnames = Jan, Feb, M&auml;rz, Apr, Mai, Juni, Juli, Aug, Sep, Okt, Nov, Dez
    # temperature tables as defaults:
    minvalues = -50, -10, -5, 0, 5, 10, 15, 20, 25, 30, 35
    maxvalues = -10, -5, 0, 5, 10, 15, 20, 25, 30, 35, 60
    colours = "#0029E5", "#0186E7", "#02E3EA", "#04EC97", "#05EF3D", "#2BF207", "#8AF408", "#E9F70A", "#F9A90B", "#FC4D0D", "#FF0F2D"
    fontColours = "#FFFFFF", "#FFFFFF", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#FFFFFF", "#FFFFFF", "#FFFFFF"
    
    [[min_temp_table]]
        obs_type = outTemp
        aggregate_type = min
        summary_heading = Min
        summary_colored = true
    
    [[max_temp_table]]
        obs_type = outTemp
        aggregate_type = max
        summary_heading = Max
        summary_colored = true
    
    [[avg_temp_table]]
        obs_type = outTemp
        aggregate_type = avg
        summary_heading = "&#8709;"
        summary_colored = true
    
    [[ice_days_table]]
        obs_type = outTemp
        aggregate_type = max_le
        aggregate_threshold = -0.001, degree_C
        summary_heading = "&#931;"
        minvalues = 1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 16, 18
        maxvalues = 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 365
        colours = "#EDEDFC", "#E0E0FC", "#D0D0FC", "#C0C0FC", "#B0B0FC", "#A0A0FC", "#9090FC", "#8080FC", "#7070FC", "#6060FC", "#5050FC", "#4040FC", "#6020FC", "#9015FC", "#AF10FC", "#CC10FC"
        fontColours = "#000000", "#000000", "#000000", "#000000", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF"
    
    [[frost_days_table]]
        obs_type = outTemp
        aggregate_type = min_le
        aggregate_threshold = -0.001, degree_C
        summary_heading = "&#931;"
        minvalues = 1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 31
        maxvalues = 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 31, 365
        colours = "#EDEDFC", "#E0E0FC", "#D0D0FC", "#C0C0FC", "#B0B0FC", "#A0A0FC", "#9090FC", "#8080FC", "#7070FC", "#6060FC", "#5050FC", "#4040FC", "#6020FC", "#9015FC", "#AF10FC", "#CC10FC"
        fontColours = "#000000", "#000000", "#000000", "#000000", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF"
    
    [[summer_days_table]]
        obs_type = outTemp
        aggregate_type = max_ge
        aggregate_threshold = 25.0, degree_C
        summary_heading = "&#931;"
        minvalues = 1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22
        maxvalues = 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 365
        colours = "#fceded", "#fcdbdb", "#fcc0c0", "#fcaaaa", "#fc9090", "#fc7a7a", "#fc6060", "#fc4c4c", "#fc3030", "#fc1b1b", "#fc1b1b", "#fc0000"
        fontColours = "#000000", "#000000", "#000000", "#000000", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF"
    
    [[hot_days_table]]
        obs_type = outTemp
        aggregate_type = max_ge
        aggregate_threshold = 30.0, degree_C
        summary_heading = "&#931;"
        minvalues = 1, 1, 2, 3, 5, 7, 9, 11, 13, 15, 18, 22
        maxvalues = 1, 2, 3, 5, 7, 9, 11, 13, 15, 18, 22, 365
        colours = "#fceded", "#fcdbdb", "#fcc0c0", "#fcaaaa", "#fc9090", "#fc7a7a", "#fc6060", "#fc4c4c", "#fc3030", "#fc1b1b", "#fc1b1b", "#fc0000"
        fontColours = "#000000", "#000000", "#000000", "#000000", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF"
    
    [[desert_days_table]]
        obs_type = outTemp
        aggregate_type = max_ge
        aggregate_threshold = 35.0, degree_C
        summary_heading = "&#931;"
        minvalues = 1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
        maxvalues = 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 365
        colours = "#fceded", "#fcdbdb", "#fcc0c0", "#fcaaaa", "#fc9090", "#fc7a7a", "#fc6060", "#fc4c4c", "#fc3030", "#fc1b1b", "#fc1b1b", "#fc0000"
        fontColours = "#000000", "#000000", "#000000", "#000000", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF"
    
    [[tropical_nights_table]]
        obs_type = outTemp
        aggregate_type = min_ge
        aggregate_threshold = 20.0, degree_C
        summary_heading = "&#931;"
        minvalues = 1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
        maxvalues = 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 365
        colours = "#fceded", "#fcdbdb", "#fcc0c0", "#fcaaaa", "#fc9090", "#fc7a7a", "#fc6060", "#fc4c4c", "#fc3030", "#fc1b1b", "#fc1b1b", "#fc0000"
        fontColours = "#000000", "#000000", "#000000", "#000000", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF"
    
    [[sultry_days_table]]
        obs_type = dewpoint
        aggregate_type = max_ge
        aggregate_threshold = 17.0, degree_C
        summary_heading = "&#931;"
        minvalues = 1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
        maxvalues = 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 365
        colours = "#fceded", "#fcdbdb", "#fcc0c0", "#fcaaaa", "#fc9090", "#fc7a7a", "#fc6060", "#fc4c4c", "#fc3030", "#fc1b1b", "#fc1b1b", "#fc0000"
        fontColours = "#000000", "#000000", "#000000", "#000000", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF"
    
    [[vegetation_days_table]]
        obs_type = outTemp
        aggregate_type = avg_ge
        aggregate_threshold = 5.001, degree_C
        summary_heading = "&#931;"
        minvalues = 1, 1, 5, 10, 20, 27, 32, 190, 220, 240, 260, 280
        maxvalues = 1, 5, 10, 20, 27, 32, 190, 220, 240, 260, 280, 365
        colours = "#f0f0f0", "#c6fcc6", "#9bfc9b", "#64fc64", "#28fc28", "#00c800", "#f0f0f0", "#c6fcc6", "#9bfc9b", "#64fc64", "#28fc28", "#00c800"
        fontColours = "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000"
    
    [[rain_table]]
        obs_type = rain
        aggregate_type = sum
        summary_heading = "&#931;"
        minvalues = 0, 25, 50, 75, 100, 150, 200, 250, 300, 350, 390, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900
        maxvalues = 25, 50, 75, 100, 150, 200, 250, 300, 350, 390, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 5000
        colours = "#e6e5fc", "#cccafc", "#acaafc", "#8486fc", "#6c6efc", "#5c5afc", "#fc02fc", "#d402d4", "#9c029c", "#6d016d", "#ffffff", "#e6e5fc", "#cccafc", "#acaafc", "#8486fc", "#6c6efc", "#5c5afc", "#fc02fc", "#d402d4", "#9c029c", "#6d016d"
        fontColours = "#000000", "#000000", "#000000", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#FFFFFF", "#FFFFFF"
    
    [[rain_days_table]]
        obs_type = rain
        aggregate_type = sum_ge
        aggregate_threshold = 0.1, mm
        summary_heading = "&#931;"
        minvalues = 1, 5, 10, 15, 20, 25, 31, 100, 120, 140, 160, 180, 200
        maxvalues = 5, 10, 15, 20, 25, 31, 100, 120, 140, 160, 180, 200, 365
        colours = "#e6e5fc", "#cccafc", "#acaafc", "#8486fc", "#6c6efc", "#5c5afc", "#ffffff", "#e6e5fc", "#cccafc", "#acaafc", "#8486fc", "#6c6efc", "#5c5afc"
        fontColours = "#000000", "#000000", "#000000", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000"
    
    [[lightning_days_table]]
        obs_type = lightning_strike_count
        aggregate_type = sum
        summary_heading = "&#931;"
        minvalues = 1, 5, 10, 20, 40, 80, 160, 250, 350, 450, 600
        maxvalues = 5, 10, 20, 40, 80, 160, 250, 350, 450, 600, 20000
        colours = "#F7F8E0", "#F3F781", "#FFFF00", "#F7D358", "#FFBF00", "#FAAC58", "#FF8000", "#FE642E", "#F9A90B", "#FC4D0D", "#FF0F2D"
        fontColours = "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#FFFFFF", "#FFFFFF"
        # 01.01.2022 00:00:00
        startdate = 1640991600
    
    [[max_wind_table]]
        obs_type = windGust
        aggregate_type = max
        summary_heading = Max
        summary_colored = true
        minvalues = 0, 1, 5, 11, 19, 29, 39, 50, 61, 74, 88, 102, 118
        maxvalues = 1, 5, 11, 19, 29, 39, 50, 61, 74, 88, 102, 118, 200
        colours = "#ffffff", "#72d475", "#10cd24", "#00b900", "#f1eea5", "#f6ef27", "#fed6d3", "#ffb6b3", "#ff9e9a", "#ff8281", "#ff6160", "#ff453c", "#ff200e"
        fontColours = "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000"
    
    [[sunshineDur_table]]
        obs_type = sunshineDur
        unit_type = hour
        aggregate_type = sum
        summary_heading = "&#931;"
        minvalues = 0.01, 50, 100, 150, 200, 300, 400
        maxvalues = 50, 100, 150, 200, 250, 350, 10000
        colours = "#FFC83F", "#FFC83F", "#FFC83F", "#FFC83F", "#FFC83F", "#FFC83F", "#FFC83F"
        fontColours = "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000"
        # 01.06.2022 00:00:00
        startdate = 1654034400
    
    [[noaa_table]]
        table_type = noaa
        # https://www.weiherhammer-wetter.de/reports/?yr=2020
        #year_link = ?yr=%Y
        year_link = ../NOAA/NOAA-%Y.txt
        # https://www.weiherhammer-wetter.de/reports/?yr=2020&mo=01
        #month_link = ?yr=%Y&mo=%m
        month_link = ../NOAA/NOAA-%Y-%m.txt
"""

from datetime import datetime
import time
import logging
import os.path

from configobj import ConfigObj

import weewx
from weewx.cheetahgenerator import SearchList
from weewx.tags import TimespanBinder
import weeutil.weeutil
import weewx.units

log = logging.getLogger(__name__)

class TableGenerator(SearchList):
    def __init__(self, generator):
        SearchList.__init__(self, generator)
        self.search_list_extension = {}
        self.tabcache = {}
        self.table_dict = generator.skin_dict['TableGenerator']
        self.debug = int(self.table_dict.get('debug', 0))
        if self.debug > 1:
            log.debug("Initialization completed.")

    def get_extension_list(self, timespan, db_lookup):
        """Returns a search list extension with two additions.

        Parameters:
          timespan: An instance of weeutil.weeutil.TimeSpan. This will
                    hold the start and stop times of the domain of
                    valid times.

          db_lookup: This is a function that, given a data binding
                     as its only parameter, will return a database manager
                     object.
        """

        # Time to recalculate a table?
        check_ts = time.time()
        refreshed_count = 0
        for table_name in self.table_dict.sections:
            if self.debug > 1:
                log.debug("Check table %s" % table_name)
            start_ts = time.time()
            table_options = weeutil.weeutil.accumulateLeaves(self.table_dict[table_name])
            obs_type = table_options.get('obs_type', None)
            table_type = table_options.get('table_type', 'normal').lower()
            refresh_interval = int(table_options.get('refresh_interval', 60))
            monthnames = table_options.get('monthnames', 'Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec')

            if table_type == 'normal':
                 if obs_type is None:
                     log.error("Table %s without obs_type!" % table_name)
                     continue

            if table_name not in self.tabcache:
                self.tabcache = {}
                self.tabcache[table_name] = {}
                self.tabcache[table_name]['refreshed_ts'] = 0
                self.tabcache[table_name]['html'] = ''
            refreshed_ts = int(self.tabcache[table_name].get('refreshed_ts', 0))

            if (start_ts - (refresh_interval * 60)) > refreshed_ts:
                if self.debug > 0:
                    log.debug("Generate table %s." % (table_name))
                binding = table_options.get('data_binding', 'wx_binding')
                startdate = table_options.get('startdate', None)

                if startdate is not None:
                    table_timespan = weeutil.weeutil.TimeSpan(int(startdate), db_lookup(binding).last_timestamp)
                else:
                    table_timespan = weeutil.weeutil.TimeSpan(db_lookup(data_binding=binding).first_timestamp, db_lookup(data_binding=binding).last_timestamp)

                table_stats = TimespanBinder(table_timespan, db_lookup, data_binding=binding, formatter=self.generator.formatter, converter=self.generator.converter)

                if table_type == 'normal':
                    self.search_list_extension[table_name] = self._HTMLTable(table_options, table_stats, table_name, binding, monthnames)
                else:
                    self.search_list_extension[table_name] = self._NOAATable(table_options, table_stats, table_name, binding, monthnames)
                end_ts = time.time()
                self.tabcache[table_name]['refreshed_ts'] = end_ts
                self.tabcache[table_name]['html'] = self.search_list_extension[table_name]
                refreshed_count += 1
                if self.debug > 1:
                    log.debug("Generated %s in %.2f seconds." % (table_name, (end_ts - start_ts)))
            else:
                self.search_list_extension[table_name] = self.tabcache[table_name]['html']
                if self.debug > 1:
                    log.debug("Skip generation table %s, the refresh time is not reached yet. Using cached table." % (table_name))

        if self.debug > 0 and refreshed_count > 0:
            log.debug("Generated %d tables in %.2f seconds." % (refreshed_count, (time.time() - check_ts)))

        return [self.search_list_extension]

    def _parseTableOptions(self, table_options, table_name):
        """Create an orderly list containing lower and upper thresholds, cell background and foreground colors
        """
        minvalues = table_options.get('minvalues', None)
        maxvalues = table_options.get('maxvalues', None)
        colours = table_options.get('colours', None)
        fontColours = table_options.get('fontColours', None)

        # Check everything's the same length
        l = len(minvalues)

        for i in maxvalues, colours:
            if len(i) != l:
                log.error("minvalues, maxvalues and colours must have the same number of elements! Table: %s." % (table_name))
                return None

        if fontColours is None:
            # default black
            fontColours = ['#000000'] * l

        return list(zip(minvalues, maxvalues, colours, fontColours))

    def _HTMLTable(self, table_options, table_stats, table_name, binding, monthnames):
        """Generate a table type "normal"

        table_options: Dictionary containing skin.conf options for particluar table
        table_stats: Link to alltime TimespanBinder
        table_name: Table name
        binding: binding where the data is allocated
        monthnames: configured Month names
        """

        cellColours = self._parseTableOptions(table_options, table_name)
        if None is cellColours:
            # Give up
            return None

        try:
            obs_type = table_options['obs_type']
            unit_type = table_options.get('unit_type', None)
            aggregate_type = table_options['aggregate_type']
        except KeyError:
            log.error("Problem with config! Table: %s." % (table_name))
            return "Error: Could not generate table %s" % table_name

        summary_column = weeutil.weeutil.to_bool(table_options.get('summary_column', False))
        summary_colored = weeutil.weeutil.to_bool(table_options.get('summary_colored', False))
        converter = table_stats.converter

        # obs_type
        readingBinder = getattr(table_stats, obs_type)

        # Some aggregate come with an argument
        aggregation = False
        if aggregate_type in ['max_ge', 'max_le', 'min_ge', 'min_le',
                              'sum_ge', 'sum_le', 'avg_ge', 'avg_le']:
            aggregation = True
            try:
                threshold_value = float(table_options['aggregate_threshold'][0])
                threshold_unit = table_options['aggregate_threshold'][1]
                reading = getattr(readingBinder, aggregate_type)((threshold_value, threshold_unit))
            except KeyError:
                log.error("Problem with aggregate_threshold! Table: %s. Should be in the format: [value], [unit]" % (table_name))
                return "Error: Could not generate table %s" % table_name
            except IndexError:
                log.error("Problem with aggregate_threshold! Table: %s. Should be in the format: [value], [unit]" % (table_name))
                return "Error: Could not generate table %s" % table_name
        else:
            try:
                reading = getattr(readingBinder, aggregate_type)
            except KeyError:
                log.error("Table %s, aggregate_type %s not found!" % (table_name, aggregate_type))
                return "Error: Could not generate table %s" % table_name

        try:
            reading_unit_type = reading.converter.group_unit_dict[reading.value_t[2]]
        except KeyError:
            log.error("Table %s, obs_type %s no unit found!" % (table_name, obs_type))

        if unit_type is None:
            unit_type = reading_unit_type

        year_heading = table_options.get('year_heading', None)
        if year_heading is None:
            if aggregation:
                year_heading = ""
            else:
                if unit_type in reading.formatter.unit_label_dict:
                    year_heading = reading.formatter.unit_label_dict[unit_type]

        if unit_type == 'count':
            format_string = '%d'
        else:
            format_string = reading.formatter.unit_format_dict[unit_type]

        # Table head
        htmlText  = '<table class="table table-striped align-middle history-table">\n'
        htmlText += '    <thead class="table-light history-table-head">\n'
        htmlText += '        <tr>\n'
        htmlText += '            <th class="text-center history-table-head-unit">%s</th>\n' % year_heading

        for mon in monthnames:
            htmlText += '            <th scope="col" class="text-center history-table-head-month">%s</th>\n' % mon

        if summary_column and 'summary_heading' in table_options:
            htmlText += '            <th scope="col" class="text-center history-table-head-summary">%s</th>\n' % table_options['summary_heading']

        htmlText += "        </tr>"
        htmlText += "    </thead>\n"

        # Table body
        htmlText += '    <tbody class="table-group-divider history-table-body">\n'

        for year in table_stats.years():
            year_number = datetime.fromtimestamp(year.timespan[0]).year
            htmlText += "        <tr>\n"
            htmlText += '            <th scope="row" class="text-center history-table-body-year">%d</th>\n' % year_number

            for month in year.months():
                # update the binding to access the right DB
                obsMonth = getattr(month, obs_type)
                obsMonth.data_binding = binding;
                if aggregation:
                    try:
                        value = getattr(obsMonth, aggregate_type)((threshold_value, threshold_unit)).value_t
                    except:
                        #value = [0, 'count']
                        value = [None, '', '']
                else:
                    value = converter.convert(getattr(obsMonth, aggregate_type).value_t)

                if value[0] is None:
                    value = None
                else:
                    if reading_unit_type != unit_type:
                        value = weewx.units.convert(value, unit_type)
                    value = value[0]

                htmlText += "            %s\n" % self._colorCell(value, format_string, cellColours)

            if summary_column:
                obsYear = getattr(year, obs_type)
                obsYear.data_binding = binding;
                if aggregation:
                    try:
                        value = getattr(obsYear, aggregate_type)((threshold_value, threshold_unit)).value_t
                    except:
                        #value = [0, 'count']
                        value = [None, '', '']
                else:
                    value = converter.convert(getattr(obsYear, aggregate_type).value_t)

                if value[0] is None:
                    value = None
                else:
                    if reading_unit_type != unit_type:
                        value = weewx.units.convert(value, unit_type)
                    value = value[0]

                htmlText += "            %s\n" % self._colorCell(value, format_string, cellColours, summary=True, summary_colored=summary_colored)
            htmlText += "        </tr>\n"

        htmlText += "    </tbody>\n"
        htmlText += "</table>\n"

        return htmlText

    def _colorCell(self, value, format_string, cellColours, summary=False, summary_colored=False):
        """Returns a table cell html code.

        value: Numeric value for the observation
        format_string: How the numberic value should be represented in the table cell.
        cellColours: An array containing 4 lists. [minvalues], [maxvalues], [background color], [foreground color]
        summary: summary cell
        summary_colored: summary cell colored
        """

        if summary:
            htmlText = '<th scope="row" class="text-center history-table-body-summary"'
        else:
            htmlText = '<td class="text-center history-table-body-month"'

        if value is not None:
            if not summary or summary_colored:
                for c in cellColours:
                    if (value >= float(c[0])) and (value < float(c[1])):
                        htmlText += ' style="background-color:%s; color:%s"' % (c[2], c[3])
                        break
            formatted_value = format_string % value
        else:
            formatted_value = '-'

        if summary:
            htmlText += '>%s</th>' % formatted_value
        else:
            htmlText += '>%s</td>' % formatted_value

        return htmlText

    def _NOAATable(self, table_options, table_stats, table_name, binding, monthnames):
        """Generate a table type "noaa"

        table_options: Dictionary containing skin.conf options for particluar table
        table_stats: Link to alltime TimespanBinder
        table_name: Table name
        binding: binding where the data is allocated
        monthnames: configured Month names
        """

        try:
            month_link = table_options['month_link']
            year_link = table_options['year_link']
        except KeyError:
            log.error("Problem with config! Table: %s." % (table_name))
            return "Error: Could not generate table %s" % table_name

        htmlText  = '<table class="table table-striped align-middle history-table-noaa">\n'
        htmlText += '    <tbody class="table-group-divider history-table-body-noaa">\n'

        for year in table_stats.years():
            year_number = datetime.fromtimestamp(year.timespan[0]).year

            htmlText += "        <tr>\n"
            htmlText += "            %s\n" % self._NOAAYear(datetime.fromtimestamp(year.timespan[0]), year_link)

            for month in year.months():
                if (month.timespan[1] < table_stats.timespan.start) or (month.timespan[0] > table_stats.timespan.stop):
                    htmlText += '            <td class="text-center history-table-body-month-noaa">-</td>\n'
                else:
                    htmlText += "            %s\n" % self._NOAAMonth(datetime.fromtimestamp(month.timespan[0]), month_link, monthnames)

            htmlText += "        </tr>\n"

        htmlText += "    </tbody>\n"
        htmlText += "</table>\n"

        return htmlText

    def _NOAAYear(self, dt, year_link):
        """Generate noaa table year cell

        dt: datetime object
        year_link: Link to noaa year file
        """
        htmlText = '<th class="text-center history-table-body-year-noaa"><a href="%s" class="history-table-body-year-nav-noaa">%s</a></th>' % (dt.strftime(year_link), dt.strftime('%Y'))
        return htmlText

    def _NOAAMonth(self, dt, month_link, monthnames):
        """Generate noaa table year cell

        dt: datetime object
        month_link: Link to noaa month file
        monthnames: configured Month names
        """
        month_name = monthnames[int(dt.strftime('%m')) - 1]
        htmlText = '<td class="text-center history-table-body-month-noaa"><a href="%s" class="history-table-body-month-nav-noaa">%s</a></td>' % (dt.strftime(month_link), month_name)
        return htmlText