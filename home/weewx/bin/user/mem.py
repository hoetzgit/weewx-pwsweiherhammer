
#
# mem.py - Tom's memory add-on and Matthew's v3 pmon extension
#          combined into a Franken-extension by Vince
#
#    vinceskahan@gmail.com - 2014-1128 - original
#
# Changes:
# - changed it to use Tom's /proc method including
#     using all three memory fields, not just rss+shared
# - deleted the __main__ code, which I gave up trying to
#     get working.  Go for smoke !!!!!
# - changed variable names and Monitor name to match
#     Tom's terminology a little closer
# - commented out the pruning of old data as the default
#     It would be cool to have this configurable perhaps
#
# bugs are mine (vinceskahan@gmail.com)
#
#    2014-1127 - Happy Thanksgiving and GO EAGLES !!!!
#
#



#---------------------------
#
# (copyright for the original pmon this is based on)
#
# weewx v# $Id: mem.py 2692 2014-11-25 01:07:48Z mwall $
# Copyright 2013 Matthew Wall
#
#---------------------------


"""weewx module that records memory information.

Installation
============

Put this file in the bin/user directory.

Configuration
============

Add the following to weewx.conf:

[MemoryMonitor]
    data_binding = mem_binding

[DataBindings]
    [[mem_binding]]
        database = mem_sqlite
        manager = weewx.manager.DaySummaryManager
        table_name = archive
        schema = user.mem.schema

[Databases]
    [[mem_sqlite]]
        root = %(WEEWX_ROOT)s
        database_name = archive/mem.sdb
        driver = weedb.sqlite

[Engine]
    [[Services]]
        archive_services = ..., user.mem.MemoryMonitor
"""

import os
import platform
import re
import syslog
import time
from subprocess import Popen, PIPE
import resource

import weewx
import weeutil.weeutil
from weewx.engine import StdService

VERSION = "0.1"

def logmsg(level, msg):
    syslog.syslog(level, 'mem: %s' % msg)

def logdbg(msg):
    logmsg(syslog.LOG_DEBUG, msg)

def loginf(msg):
    logmsg(syslog.LOG_INFO, msg)

def logerr(msg):
    logmsg(syslog.LOG_ERR, msg)

schema = [
    ('dateTime', 'INTEGER NOT NULL PRIMARY KEY'),
    ('usUnits', 'INTEGER NOT NULL'),
    ('interval', 'INTEGER NOT NULL'),
    ('mem_size','INTEGER'),
    ('mem_rss','INTEGER'),
    ('mem_share','INTEGER'),
    ]


class MemoryMonitor(StdService):

    def __init__(self, engine, config_dict):
        super(MemoryMonitor, self).__init__(engine, config_dict)

        d = config_dict.get('MemoryMonitor', {})
        self.process = d.get('process', 'weewxd')
        self.max_age = weeutil.weeutil.to_int(d.get('max_age', 2592000))
        self.page_size = resource.getpagesize()

        # get the database parameters we need to function
        binding = d.get('data_binding', 'mem_binding')
        self.dbm = self.engine.db_binder.get_manager(data_binding=binding,
                                                     initialize=True)

        # be sure database matches the schema we have
        dbcol = self.dbm.connection.columnsOf(self.dbm.table_name)
        dbm_dict = weewx.manager.get_manager_dict(
            config_dict['DataBindings'], config_dict['Databases'], binding)
        memcol = [x[0] for x in dbm_dict['schema']]
        if dbcol != memcol:
            raise Exception('mem schema mismatch: %s != %s' % (dbcol, memcol))

        self.last_ts = None
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

    def shutDown(self):
        try:
            self.dbm.close()
        except:
            pass

    def new_archive_record(self, event):
        """save data to database then prune old records as needed"""
        now = int(time.time() + 0.5)
        delta = now - event.record['dateTime']
        if delta > event.record['interval'] * 60:
            logdbg("Skipping record: time difference %s too big" % delta)
            return
        if self.last_ts is not None:
            self.save_data(self.get_data(now, self.last_ts))
        self.last_ts = now
        #-- TBD: make this tunable on/off via variable
        #-- if self.max_age is not None:
        #--     self.prune_data(now - self.max_age)

    def save_data(self, record):
        """save data to database"""
        self.dbm.addRecord(record)

    def prune_data(self, ts):
        """delete records with dateTime older than ts"""
        sql = "delete from %s where dateTime < %d" % (self.dbm.table_name, ts)
        self.dbm.getSql(sql)
        try:
            # sqlite databases need some help to stay small
            self.dbm.getSql('vacuum')
        except Exception as e:
            pass

    COLUMNS = re.compile('[\S]+\s+[\d]+\s+[\d.]+\s+[\d.]+\s+([\d]+)\s+([\d]+)')

    def get_data(self, now_ts, last_ts):
        record = {}
        record['dateTime'] = now_ts
        record['usUnits'] = weewx.METRIC
        record['interval'] = int((now_ts - last_ts) / 60)
        # try:
        #     cmd = 'ps aux'
        #     p = Popen(cmd, shell=True, stdout=PIPE)
        #     o = p.communicate()[0]
        #     for line in o.split('\n'):
        #         if line.find(self.process) >= 0:
        #             m = self.COLUMNS.search(line)
        #             if m:
        #                 record['mem_vsz'] = int(m.group(1))
        #                 record['mem_rss'] = int(m.group(2))
        # except (ValueError, IOError, KeyError), e:
        #     logerr('apcups_info failed: %s' % e)
        #
        # return record

        try:
            #---- from Tom ---
            pid = os.getpid()
            procfile = "/proc/%s/statm" % pid
            try:
                mem_tuple = open(procfile).read().split()
            except (IOError, ):
                return
                # Unpack the tuple:
            (size, resident, share, text, lib, data, dt) = mem_tuple
            mb = 1024 * 1024
            record['mem_size']  = float(size)     * self.page_size / mb 
            record['mem_rss']   = float(resident) * self.page_size / mb
            record['mem_share'] = float(share)    * self.page_size / mb
       	    #---- from Tom ---
        except (ValueError, IOError, KeyError) as e:
            logerr('memory_info failed: %s' % e)

        return record


# what follows is a basic unit test of this module.  to run the test:
#
# cd /home/weewx
# PYTHONPATH=bin python bin/user/mem.py
#
if __name__=="__main__":
    from weewx.engine import StdEngine
    config = {
        'Station': {
            'station_type': 'Simulator',
            'altitude': [0,'foot'],
            'latitude': 0,
            'longitude': 0},
        'Simulator': {
            'driver': 'weewx.drivers.simulator',
            'mode': 'simulator'},
        'MemoryMonitor': {
            'data_binding': 'mem_binding',
            'process': 'weewxd'},
        'DataBindings': {
            'mem_binding': {
                'database': 'mem_sqlite',
                'manager': 'weewx.manager.DaySummaryManager',
                'table_name': 'archive',
                'schema': 'user.mem.schema'}},
        'Databases': {
            'mem_sqlite': {
                'root': '/tmp',
                'database_name': 'mem.sdb',
                'driver': 'weedb.sqlite'}},
        'Engines': {
            'Services': {
                'process_services': 'user.mem.MemoryMonitor'}}}
    engine = StdEngine(config)
    svc = MemoryMonitor(engine, config)
    record = svc.get_data()
    print(record)

    time.sleep(5)
    record = svc.get_data()
    print(record)

    time.sleep(5)
    record = svc.get_data()
    print(record)

    os.remove('/tmp/mem.sdb')

