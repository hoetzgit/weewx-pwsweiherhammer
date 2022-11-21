# Copyright 2015-2021 Matthew Wall
# Distributed under the terms of the GNU Public License (GPLv3)

import os
import os.path
import time

import weewx
import weewx.engine
import weeutil.weeutil

VERSION = "0.11"

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
        syslog.syslog(level, 'csv: %s' % msg)
    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)
    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)
    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)

class CSV(weewx.engine.StdService):
    def __init__(self, engine, config_dict):
        super(CSV, self).__init__(engine, config_dict)
        loginf("service version is %s" % VERSION)
        d = config_dict.get('CSV', {})
        # location of the output file
        self.filename = d.get('filename', '/var/tmp/data.csv')
        # optionally emit a header line as the first line of the file
        self.emit_header = weeutil.weeutil.to_bool(d.get('header', True))
        # mode can be append or overwrite
        self.mode = d.get('mode', 'append')
        # optionally append a datestamp to the filename
        self.append_datestamp = weeutil.weeutil.to_bool(d.get('append_datestamp', True))
        # format for the filename datestamp
        self.datestamp_format = d.get('datestamp_format', '%Y-%m')
        # format for the per-record timestamp
        self.timestamp_format = d.get('timestamp_format')
        # bind to either loop or archive events
        self.binding = d.get('binding', 'loop')
        if self.binding == 'loop':
            self.bind(weewx.NEW_LOOP_PACKET, self.handle_new_loop)
        else:
            self.bind(weewx.NEW_ARCHIVE_RECORD, self.handle_new_archive)

    def handle_new_loop(self, event):
        self.write_data(event.packet)

    def handle_new_archive(self, event):
        self.write_data(event.record)

    def write_data(self, data):
        flag = "a" if self.mode == 'append' else "w"
        filename = self.filename
        if self.append_datestamp:
            basename = filename
            ext = ''
            idx = filename.find('.')
            if idx > -1:
                basename = filename[:idx]
                ext = filename[idx:]
            tstr = time.strftime(self.datestamp_format,
                                 time.gmtime(data['dateTime']))
            filename = "%s-%s%s" % (basename, tstr, ext)
        header = None
        if self.emit_header and (
            not os.path.exists(filename) or flag == "w"):
            header = '# %s\n' % ','.join(self.sort_keys(data))
        with open(filename, flag) as f:
            if header:
                f.write(header)
            f.write('%s\n' % ','.join(self.sort_data(data)))

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