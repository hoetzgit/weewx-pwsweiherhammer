"""
    Copyright (C) 2023 Henry Ott
    based on code from Matthew Wall, https://github.com/matthewwall/weewx-csv
    Status: WORK IN PROGRESS
    
    This service will emit either loop and/or archive data from weewx in CSV format.
    
    Archive Records: The archive records will be written to a CSV file.
    LOOP Packets: Two CSV files are written for LOOP data. One file contains all
    possible fields that a LOOP packet can theoretically contain, the second file
    contains only LOOP data that are also contained in the archive table.
    
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
    
    Configuration example:
    
    [CSVEXT]
        # optinal enable/disable service. Default is True
        enable = True
        # optional debug level. Default is 0
        debug = 0
        # The full path for the output files without final '/'. Default is '/var/tmp'
        filedir = /var/tmp
        # Indicates whether to append or overwrite each time data is written to file. Default is 'append'.
        mode = append
        # The format for the appended datestamp. For example, %Y-%m-%d would result in filenames such as
        # data-2017-10-01.csv, with a new file each day. Default is %Y-%m, which results in a new file each month.
        # Default is True
        append_datestamp = True
        # format for the filename datestamp, Default is %Y-%m, which results in a new file each month.
        datestamp_format = %Y-%m
        # The format for the data timestamp. For example, %Y-%m-%d %H:%M:%S results in a
        # dateTime field like 2017-10-01 14:23:03. All times are UTC. Default is no format, which results in a unix epoch.
        timestamp_format =
        # The binding determines whether the file will be updated with every LOOP packet
        # and/or archive record. Possible values are loop and/or archive. Default is 'loop'
        binding = loop, archive
        # optional field separator. Default is ';'
        field_separator = ;
"""
import os
import os.path
import time

import weewx
import weewx.engine
from weeutil.weeutil import to_bool, to_int

VERSION = "0.2"

try:
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
    import syslog

    def logmsg(level, msg):
        syslog.syslog(level, 'csvext: %s' % msg)
    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)
    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)
    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)

class CSVEXT(weewx.engine.StdService):
    def __init__(self, engine, config_dict):
        super(CSVEXT, self).__init__(engine, config_dict)
        loginf("Service version is %s" % VERSION)
        d = config_dict.get('CSVEXT', {})
        # optional enable/disable service
        enable = to_bool(d.get('enable', True))
        if not enable:
            loginf("Service is disabled. Enable it in the [CSVEXT] section of weewx.conf.")
            return

        # optional debug level
        self.debug = to_int(d.get('debug', config_dict.get('debug', 0)))
        # location of the output file
        filedir = d.get('filedir', '/var/tmp')
        # mode can be append or overwrite
        self.mode = d.get('mode', 'append')
        # optionally append a datestamp to the filename
        self.append_datestamp = to_bool(d.get('append_datestamp', True))
        # format for the filename datestamp
        self.datestamp_format = d.get('datestamp_format', '%Y-%m')
        # format for the per-record timestamp
        self.timestamp_format = d.get('timestamp_format')
        # bind to either loop or archive events
        binding = d.get('binding', 'loop')
        # optional field delimiter
        self.field_separator = d.get('field_separator', ';').strip()

        if 'loop' not in binding and 'archive' not in binding:
            logerr("Error configuration. binding = 'loop' and/or 'archive' required!")
            return

        self.loop_fields_list = []
        self.archive_cols_list = []
        self.archive_cols_list.append('dateTime')
        self.archive_cols_list.append('usUnits')
        self.archive_cols_list.append('interval')
        try:
            db_binder = weewx.manager.DBBinder(self.config_dict)
            db_binding = self.config_dict.get('StdReport')['data_binding']
            dbm = db_binder.get_manager(db_binding)
            # Get the column names of the archive table.
            archive_cols_list = dbm.connection.columnsOf('archive')
            for field in sorted(archive_cols_list):
                if field not in self.archive_cols_list:
                    self.archive_cols_list.append(field)
        except Exception as e:
            logerr('Error initialization. Exception: %s' % e)

        if 'loop' in binding:
            self.bind(weewx.NEW_LOOP_PACKET, self.handle_new_loop)
            self.filename_loop = "%s/%s" % (filedir, "loop.csv")
            self.filename_loop_db = "%s/%s" % (filedir, "loop_db.csv")
            self.loop_fields_list.append('dateTime')
            self.loop_fields_list.append('usUnits')
            self.loop_fields_list.append('interval')
            for field in sorted(weewx.units.obs_group_dict):
                if field not in self.loop_fields_list:
                    self.loop_fields_list.append(field)

        if 'archive' in binding:
            self.bind(weewx.NEW_ARCHIVE_RECORD, self.handle_new_archive)
            self.filename_archive = "%s/%s" % (filedir, "archive.csv")

    def handle_new_loop(self, event):
        self.new_loop_data(event.packet)

    def handle_new_archive(self, event):
        self.new_archive_data(event.record)

    def write_csv(self, filename, csv_data):
        flag = "a" if self.mode == 'append' else "w"
        header = None
        if not os.path.exists(filename) or flag == "w":
            header = '%s\n' % self.field_separator.join(csv_data)
        with open(filename, flag) as outfile:
            if header is not None:
                outfile.write(header)
            outfile.write('%s\n' % self.field_separator.join(str(value) for field, value in csv_data.items()))
            outfile.close()

    def new_loop_data(self, loop_data):
        # write loop csv with all possible loop fields
        filename = self.filename_loop
        if self.append_datestamp:
            basename = filename
            ext = ''
            idx = filename.find('.')
            if idx > -1:
                basename = filename[:idx]
                ext = filename[idx:]
            tstr = time.strftime(self.datestamp_format,
                                 time.gmtime(to_int(loop_data['dateTime'])))
            filename = "%s_%s%s" % (basename, tstr, ext)

        # init a new csv data line dict
        csv_dict = {}
        for field in self.loop_fields_list:
            csv_dict[field] = ''
        for field, value in loop_data.items():
            if field in csv_dict:
                if value is None:
                    csv_dict[field] = ''
                elif self.timestamp_format is not None and self.timestamp_format != '' and field == 'dateTime':
                    csv_dict[field] = time.strftime(self.timestamp_format,
                                                    time.gmtime(value))
                else:
                    csv_dict[field] = str(value)
        self.write_csv(filename, csv_dict)

        # write loop csv only with archive table columns
        filename = self.filename_loop_db
        if self.append_datestamp:
            basename = filename
            ext = ''
            idx = filename.find('.')
            if idx > -1:
                basename = filename[:idx]
                ext = filename[idx:]
            tstr = time.strftime(self.datestamp_format,
                                 time.gmtime(to_int(loop_data['dateTime'])))
            filename = "%s_%s%s" % (basename, tstr, ext)

        # init a new csv data line dict
        csv_dict = {}
        for field in self.archive_cols_list:
            csv_dict[field] = ''
        for field, value in loop_data.items():
            if field in csv_dict:
                if value is None:
                    csv_dict[field] = ''
                elif self.timestamp_format is not None and self.timestamp_format != '' and field == 'dateTime':
                    csv_dict[field] = time.strftime(self.timestamp_format,
                                                    time.gmtime(value))
                else:
                    csv_dict[field] = str(value)
        self.write_csv(filename, csv_dict)

    def new_archive_data(self, archive_data):
        filename = self.filename_archive
        if self.append_datestamp:
            basename = filename
            ext = ''
            idx = filename.find('.')
            if idx > -1:
                basename = filename[:idx]
                ext = filename[idx:]
            tstr = time.strftime(self.datestamp_format,
                                 time.gmtime(to_int(archive_data['dateTime'])))
            filename = "%s_%s%s" % (basename, tstr, ext)

        # init a new csv data line dict
        csv_dict = {}
        for field in self.archive_cols_list:
            csv_dict[field] = ''
        for field, value in archive_data.items():
            if field in csv_dict:
                if value is None:
                    csv_dict[field] = ''
                elif self.timestamp_format is not None and self.timestamp_format != '' and field == 'dateTime':
                    csv_dict[field] = time.strftime(self.timestamp_format,
                                                    time.gmtime(value))
                else:
                    csv_dict[field] = str(value)
        self.write_csv(filename, csv_dict)
