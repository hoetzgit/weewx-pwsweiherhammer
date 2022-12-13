# Copyright 2015-2021 Matthew Wall
# Distributed under the terms of the GNU Public License (GPLv3)
#
# Copyright 2022 Henry Ott "extended" Version (Status: MVP)
# LOOP packets with contents not previously stored in the CSV file trigger a restructuring of the existing CSV file.
# TODO different Archive Records after user changes on DB Structure?
import os
import os.path
import time
import csv
import shutil

import weewx
import weewx.engine
import weeutil.weeutil

VERSION = "0.1"

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
        enable = weeutil.weeutil.to_bool(d.get('enable', True))
        if not enable:
            loginf("Service is disabled. Enable it in the [CSVEXT] section of weewx.conf.")
            return

        # optional debug level
        self.debug = weeutil.weeutil.to_int(d.get('debug', 0))
        # location of the output file
        filedir = d.get('filedir', '/var/tmp')
        # mode can be append or overwrite
        self.mode = d.get('mode', 'append')
        # optionally append a datestamp to the filename
        self.append_datestamp = weeutil.weeutil.to_bool(d.get('append_datestamp', True))
        # format for the filename datestamp
        self.datestamp_format = d.get('datestamp_format', '%Y-%m')
        # format for the per-record timestamp
        self.timestamp_format = d.get('timestamp_format')
        # bind to either loop or archive events
        binding = d.get('binding', 'loop')
        # optional field delimiter
        self.field_separator = d.get('field_separator', ',')

        if 'loop' in binding:
            self.bind(weewx.NEW_LOOP_PACKET, self.handle_new_loop)
            self.filename_loop = "%s/%s" % (filedir, "loop.csv")
            if self.mode == 'append':
                self.csv_structure = None
                self.column_field_mapping = None
        if 'archive' in binding:
            self.bind(weewx.NEW_ARCHIVE_RECORD, self.handle_new_archive)
            self.filename_archive = "%s/%s" % (filedir, "archive.csv")

    def handle_new_loop(self, event):
        self.new_loop_data(event.packet)

    def handle_new_archive(self, event):
        self.new_archive_data(event.record)

    def sort_keys(self, record):
        fields = ['dateTime']
        for k in sorted(record):
            if k != 'dateTime':
                fields.append(k)
        return fields

    def sort_data(self, record):
        tstr = str(record['dateTime'])
        if self.timestamp_format is not None:
            tstr = time.strftime(self.timestamp_format,
                                 time.gmtime(record['dateTime']))
        fields = [tstr]
        for k in sorted(record):
            if k != 'dateTime':
                fields.append(str(record[k]))
        return fields

    def sort_data_dict(self, to_sort_dict):
        to_sort_dict = dict(sorted(sort_dict.items()))
        if 'dateTime' in to_sort_dict:
            # set dateTime as first element
            tmp_dict = dict()
            tmp_dict['dateTime'] = to_sort_dict['dateTime']
            # remove dateTime from sorted dict
            del to_sort_dict['dateTime']
            # new sorted dict with dateTime as first element
            tmp_dict.update(to_sort_dict)
            to_sort_dict = tmp_dict
        return to_sort_dict

    def build_column_field_mapping(self, sorted_dict):
        mapping_dict = dict()
        col = 0
        for k in sorted_dict:
            mapping_dict[col] = k
            col += 1
        return mapping_dict

    def write_loop_csv(self, filename, loop_data):
        flag = "a" if self.mode == 'append' else "w"
        header = None
        if not os.path.exists(filename) or flag == "w":
            header = '%s\n' % self.field_separator.join(self.sort_keys(loop_data))
        new_csv_structure = self.csv_structure
        with open(filename, flag) as outfile:
            if header is not None:
                outfile.write(header)

            if flag == "a":
                # init new data with new data structure dict
                new_data = new_csv_structure
            
                for k in loop_data:
                    new_data[k] = loop_data[k]

                tstr = str(loop_data['dateTime'])
                if self.timestamp_format is not None:
                    tstr = time.strftime(self.timestamp_format,
                                         time.gmtime(loop_data['dateTime']))
                fields = [tstr]
                for k in new_data:
                    if k != 'dateTime':
                        fields.append(str(new_data[k]) if new_data[k] is not None else "")
                outfile.write('%s\n' % self.field_separator.join(fields))
                if self.debug > 0:
                    logdbg("New LOOP data appended to CSV file.")
            else:
                outfile.write('%s\n' % ','.join(self.sort_data(loop_data)))
                if self.debug > 0:
                    logdbg("New LOOP data saved to CSV file.")
            outfile.close()

    def write_loop_restructured_csv(self, filename, loop_data):
        filenametmp = filename + '.tmp'
        # init new structure with the last saved csv structure
        new_csv_structure = self.csv_structure
        # add new fields to new csv structure
        for k in loop_data:
            if k not in new_csv_structure:
                new_csv_structure[k] = ""
        # sort new structure
        new_csv_structure = self.sort_data_dict(new_csv_structure)
        header = '%s\n' % self.field_separator.join(self.sort_keys(new_csv_structure))
        with open (filename, 'r') as infile, open (filenametmp, 'w') as outfile:
            # write new header to tmp csv file
            outfile.write(header)

            # read old data, convert old data to new csv header structure and write to tmp csv file
            csv_reader = csv.reader(infile, delimiter = self.field_separator)
            first_line = True
            for row in csv_reader:
                # first line header
                if not first_line:
                    # init old data dict with new csv data structure dict
                    old_data = new_csv_structure
                    # copy old data to new structure
                    col = 0
                    for data in row:
                        # get field name from mapping dict
                        field = self.column_field_mapping.get(col)
                        if field is None:
                            # clean up
                            infile.close()
                            outfile.close()
                            if os.path.exists(filenametmp):
                                os.remove(filenametmp)
                            logerr("Error during CSV restructuring, column-field-mapping is incorrect. Abort!")
                            if self.debug > 0:
                                logdbg("row: %s" % str(row))
                                logdbg("field mapping: %s" % str(self.column_field_mapping))
                                logdbg("old csv structure: %s" % str(self.csv_structure))
                                logdbg("new csv structure: %s" % str(new_csv_structure))
                            return
                        old_data[field] = data
                        col += 1

                    # now write the old data with new csv structure
                    fields = list()
                    for k in old_data:
                        fields.append(str(old_data[k]))
                    outfile.write('%s\n' % self.field_separator.join(fields))
                else:
                    first_line = False

            # write now the new loop data
            # init new data dict with new data structure dict
            new_data = new_csv_structure
            for k in loop_data:
                new_data[k] = loop_data[k]

            tstr = str(loop_data['dateTime'])
            if self.timestamp_format is not None:
                tstr = time.strftime(self.timestamp_format,
                                     time.gmtime(loop_data['dateTime']))
            fields = [tstr]
            for k in new_data:
                if k != 'dateTime':
                    fields.append(str(new_data[k]) if new_data[k] is not None else "")
            outfile.write('%s\n' % self.field_separator.join(fields))

            # close infile/outfile
            infile.close()
            outfile.close()

        # save new csv structure
        self.csv_structure = new_csv_structure
        # build new field mapping with new csv data structure
        self.column_field_mapping = self.build_column_field_mapping(self.csv_structure)

        # move temp file to result csv file
        if os.path.exists(filenametmp):
            shutil.move(filenametmp, filename)
        # clean up after previous failures?
        if os.path.exists(filenametmp):
            os.remove(filenametmp)
        if self.debug > 0:
            logdbg("LOOP data contained new fields. CSV file was restructured.")

    def init_loop_csv_structure_and_field_mapping(self, filename, loop_data):
        self.csv_structure = dict()
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                cols = list()
                csv_reader = csv.reader(f, delimiter = self.field_separator)
                # first line is header
                for row in csv_reader:
                    cols.append(row)
                    break;
                f.close()
                for k in cols[0]:
                    self.csv_structure[k] = ""
        else:
            loop_dict = dict()
            for k in loop_data:
                loop_dict[k] = ""
            self.csv_structure = self.sort_data_dict(loop_dict)
        # build new field mapping with new data structure dict
        self.column_field_mapping = self.build_column_field_mapping(self.csv_structure)
        if self.debug > 0:
            logdbg("CSV structure and the column field mapping is initialized.")

    def new_loop_data(self, loop_data):
        flag = "a" if self.mode == 'append' else "w"
        filename = self.filename_loop
        if self.append_datestamp:
            basename = filename
            ext = ''
            idx = filename.find('.')
            if idx > -1:
                basename = filename[:idx]
                ext = filename[idx:]
            tstr = time.strftime(self.datestamp_format,
                                 time.gmtime(loop_data['dateTime']))
            filename = "%s_%s%s" % (basename, tstr, ext)

        if flag == "a":
            if self.csv_structure is None:
                self.init_loop_csv_structure_and_field_mapping(filename, loop_data)

            new_fields = False
            if self.csv_structure is not None:
                #check if the loop field has ever been saved in the csv file before
                for field in loop_data:
                    if field != 'dateTime':
                        if field not in self.csv_structure:
                            new_fields = True
                            break
            if new_fields:
                if self.debug > 0:
                    logdbg("LOOP data with not yet previously stored fields detected.")
                self.write_loop_restructured_csv(filename, loop_data)
            else:
                # the structure is the same as before or it's a new file
                if self.debug > 0:
                    if not os.path.exists(filename):
                        logdbg("A new LOOP CSV file will be created.")
                    else:
                        logdbg("LOOP data contains only previously stored values.")
                self.write_loop_csv(filename, loop_data)
        else:
            if self.debug > 0:
                logdbg("A new LOOP CSV file will be created.")
            self.write_loop_csv(filename, loop_data)

    def new_archive_data(self, data):
        flag = "a" if self.mode == 'append' else "w"
        filename = self.filename_archive
        if self.append_datestamp:
            basename = filename
            ext = ''
            idx = filename.find('.')
            if idx > -1:
                basename = filename[:idx]
                ext = filename[idx:]
            tstr = time.strftime(self.datestamp_format,
                                 time.gmtime(data['dateTime']))
            filename = "%s_%s%s" % (basename, tstr, ext)
        header = None
        if not os.path.exists(filename) or flag == "w":
            header = '%s\n' % ','.join(self.sort_keys(data))
            logdbg("A new Archive CSV file will be created.")
        with open(filename, flag) as f:
            if header is not None:
                f.write(header)
            f.write('%s\n' % ','.join(self.sort_data(data)))
        if self.debug > 0:
            if flag == "a":
                logdbg("New Archive data appended to the CSV file.")
            else:
                logdbg("New Archive data saved to CSV file.")
