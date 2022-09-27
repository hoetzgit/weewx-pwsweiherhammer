#
# installer for the mem extension - see the readme.txt and CREDITS
# files for more details....
#
#-----
# (original mwall copyright for the installer this is based on)
# $Id: install.py 2689 2014-11-24 23:51:08Z mwall $
# installer for mem
# Copyright 2014 Matthew Wall
#-----

from setup import ExtensionInstaller

def loader():
    return MemoryMonitorInstaller()

class MemoryMonitorInstaller(ExtensionInstaller):
    def __init__(self):
        super(MemoryMonitorInstaller, self).__init__(
            version="1.2",
            name='mem',
            description='Collect and display process memory usage.',
            author="Vince Skahan",
            author_email="vinceskahan@gmail.com",
            process_services='user.mem.MemoryMonitor',
            config={
                'MemoryMonitor': {
                    'data_binding': 'mem_binding',
                    'process': 'weewxd'},
                'DataBindings': {
                    'mem_binding': {
                        'database': 'mem_sqlite',
                        'table_name': 'archive',
                        'manager': 'weewx.manager.DaySummaryManager',
                        'schema': 'user.mem.schema'}},
                'Databases': {
                    'mem_sqlite': {
                        'database_name': 'mem.sdb',
                        'driver': 'weedb.sqlite'}},
                'StdReport': {
                    'mem': {
                        'skin': 'mem',
                        'HTML_ROOT': 'mem'}}},
            files=[('bin/user', ['bin/user/mem.py']),
                   ('skins/mem', ['skins/mem/skin.conf',
                                   'skins/mem/index.html.tmpl',
                                   'skins/mem/weewx.css'])]
            )
