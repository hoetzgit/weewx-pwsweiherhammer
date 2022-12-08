"""
    currenthelper.py
    Copyright (C) 2022 Henry Ott
    Status: DRAFT, WORK IN PROGRESS

    Determination of values to compare the API values for the current weather
    with the values of the station.
    Values are read from loopdata.json. This is generated by the extension weewx-loopdata

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
"""
import os
import syslog
from datetime import datetime
import time
from typing import Any, Dict, Generator, List, Optional, Set, Tuple, Union
import json

import weewx
import weewx.manager
from weewx.wxengine import StdService
from weeutil.weeutil import to_bool, to_int, to_float

try:
    # Test for new-style weewx logging by trying to import weeutil.logger
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
    # Old-style weewx logging
    import syslog

    def logmsg(level, msg):
        syslog.syslog(level, 'currenthelper: %s' % msg)

    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)

VERSION = "0.1"

DEFAULTS_INI = """
[CurrentHelper]
    enable = true
    debug = 0
"""
defaults_dict = weeutil.config.config_from_str(DEFAULTS_INI)

class CurrentHelper(StdService):
    def __init__(self, engine, config_dict):
        # Pass the initialization information on to my superclass:
        super(CurrentHelper, self).__init__(engine, config_dict)
        log.info("Service version is %s." % VERSION)

        # Get any user-defined overrides
        override_dict = config_dict.get('CurrentHelper', {})
        # Get the default values, then merge the user overrides into it
        option_dict = weeutil.config.deep_copy(defaults_dict['CurrentHelper'])
        option_dict.merge(override_dict)

        # Only continue if the plugin is enabled.
        enable = to_bool(option_dict['enable'])
        if enable:
            loginf("CurrentHelperCurrentHelper is enabled...continuing.")
        else:
            loginf("CurrentHelper is disabled. Enable it in the CurrentHelper section of weewx.conf.")
            return
        self.debug = to_int(option_dict['debug'])
        loginf("debug level is %d" % self.debug)

        # Get the unit_system as specified by StdConvert->target_unit.
        # Note: this value will be overwritten if the day accumulator has a a unit_system.
        db_binder = weewx.manager.DBBinder(config_dict)
        default_binding = config_dict.get('StdReport')['data_binding']
        dbm = db_binder.get_manager(default_binding)
        unit_system = dbm.std_unit_system
        if unit_system is None:
            unit_system = weewx.units.unit_constants[config_dict['StdConvert'].get('target_unit', 'US').upper()]
        # Get the column names of the archive table.
        self.archive_columns: List[str] = dbm.connection.columnsOf('archive')

        # LoopData
        loop_config_dict = config_dict.get('LoopData', {})
        file_spec_dict = loop_config_dict.get('FileSpec', {})
        formatting_spec_dict = loop_config_dict.get('Formatting', {})
        loop_frequency_spec_dict = loop_config_dict.get('LoopFrequency', {})

        # Get a target report dictionary we can use for converting units and formatting.
        target_report = formatting_spec_dict.get('target_report', 'LoopDataReport')
        try:
            target_report_dict = self.get_target_report_dict(
                config_dict, target_report)
        except Exception as e:
            logerr('Could not find target_report: %s. CurrentHelper is exiting. Exception: %s' % (target_report, e))
            return

        self.loopdata_dir = self.compose_loopdata_dir(config_dict, target_report_dict, file_spec_dict)
        self.loopdata_filename = file_spec_dict.get('filename', 'loop-data.txt')
        self.loopdata_file = os.path.join(self.loopdata_dir, self.loopdata_filename)
        loginf('LoopData file is: %s' % self.loopdata_file)

        # Start intercepting events:
        self.bind(weewx.NEW_LOOP_PACKET, self.newLoopPacket)

    def newLoopPacket(self, event):
        """Gets called on a new loop packet event."""
        if self.debug > 1:
            logdbg("incomming loop packet: %s" % str(event.packet))
        elif self.debug > 0:
            logdbg("incomming loop packet")

        target_data = {}

        if self.debug > 0:
            logdbg("working...")
        content = self.read_loopdata_file(self.loopdata_file, self.debug)
        if self.debug > 0:
            logdbg("json = %s" % str(content))

        # add to LOOP
        event.packet.update(target_data)
        if self.debug > 1:
            logdbg("outgoing loop packet: %s" % str(event.packet))
        elif self.debug > 0:
            logdbg("outgoing loop packet")

    @staticmethod
    def compose_loopdata_dir(config_dict: Dict[str, Any],
            target_report_dict: Dict[str, Any], file_spec_dict: Dict[str, Any]
            ) -> str:
        # Compose the directory in which to write the file (if
        # relative it is relative to the target_report_directory).
        weewx_root   : str = str(config_dict.get('WEEWX_ROOT'))
        html_root    : str = str(target_report_dict.get('HTML_ROOT'))
        loopdata_dir: str = str(file_spec_dict.get('loop_data_dir', '.'))
        return os.path.join(weewx_root, html_root, loopdata_dir)

    @staticmethod
    def get_target_report_dict(config_dict, report) -> Dict[str, Any]:
        try:
            return weewx.reportengine._build_skin_dict(config_dict, report)
        except AttributeError:
            pass # Load the report dict the old fashioned way below
        try:
            skin_dict = weeutil.config.deep_copy(weewx.defaults.defaults)
        except Exception:
            # Fall back to copy.deepcopy for earlier than weewx 4.1.2 installs.
            skin_dict = copy.deepcopy(weewx.defaults.defaults)
        skin_dict['REPORT_NAME'] = report
        skin_config_path = os.path.join(
            config_dict['WEEWX_ROOT'],
            config_dict['StdReport']['SKIN_ROOT'],
            config_dict['StdReport'][report].get('skin', ''),
            'skin.conf')
        try:
            merge_dict = configobj.ConfigObj(skin_config_path, file_error=True, encoding='utf-8')
            logdbg("Found configuration file %s for report '%s'", skin_config_path, report)
            # Merge the skin config file in:
            weeutil.config.merge_config(skin_dict, merge_dict)
        except IOError as e:
            logdbg("Cannot read skin configuration file %s for report '%s': %s",
                    skin_config_path, report, e)
        except SyntaxError as e:
            logerr("Failed to read skin configuration file %s for report '%s': %s",
                    skin_config_path, report, e)
            raise

        # Now add on the [StdReport][[Defaults]] section, if present:
        if 'Defaults' in config_dict['StdReport']:
            # Because we will be modifying the results, make a deep copy of the [[Defaults]]
            # section.
            try:
                merge_dict = weeutil.config.deep_copy(config_dict['StdReport']['Defaults'])
            except Exception:
                # Fall back to copy.deepcopy for earlier weewx 4 installs.
                merge_dict = copy.deepcopy(config_dict['StdReport']['Defaults'])
            weeutil.config.merge_config(skin_dict, merge_dict)

        # Inject any scalar overrides. This is for backwards compatibility. These options should now go
        # under [StdReport][[Defaults]].
        for scalar in config_dict['StdReport'].scalars:
            skin_dict[scalar] = config_dict['StdReport'][scalar]

        # Finally, inject any overrides for this specific report. Because this is the last merge, it will have the
        # final say.
        weeutil.config.merge_config(skin_dict, config_dict['StdReport'][report])

        return skin_dict

    @staticmethod
    def read_loopdata_file(loopdata_file: str, debug: int = 0) -> None:
        content = None
        if debug > 1:
            logdbg('Reading file %s' % loopdata_file)
        with open(loopdata_file) as f:
            content = json.load(f)
        return content