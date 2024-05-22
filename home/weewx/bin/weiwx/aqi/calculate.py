# weewx-aqi
# Copyright 2018-2021 - Jonathan Koren <jonathan@jonathankoren.com>
# License: GPL 3

import sys
import time
import json
import os

import weeutil.weeutil
import weewx
import weewx.cheetahgenerator
import weewx.engine
import weewx.units

sys.path.append('/home/weewx/bin/weiwx/aqi')
import calculators
import standards
import units

try:
    # Test for new-style weewx logging by trying to import weeutil.logger
    import weeutil.logger
    import logging
    log = logging.getLogger("weiwx.aqi.calculate")

    def logdbg(msg):
        log.debug(msg)

    def loginf(msg):
        log.info(msg)

    def logerr(msg):
        log.error(msg)

    def logwrn(msg):
        log.warning(msg)

except ImportError:
    # Old-style weewx logging
    import syslog

    def logmsg(level, msg):
        syslog.syslog(level, "weiwx.aqi.calculate: %s" % msg)

    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)

    def logwrn(msg):
        logmsg(syslog.LOG_WARNING, msg)

def _trim_dict(d):
    '''Removes all entries in the dict where value is None.'''
    for (k, v) in list(d.items()):
        if v is None:
            d.pop(k)
    return d

def _make_dict(row, colnames):
    if type(row) == dict:
        return row
    d = {}
    for i in range(len(row)):
        d[colnames[i]] = row[i]
    return d

@staticmethod
def exception_output(class_name, e, addcontent=None, debug=1, log_failure=True):
    if log_failure or debug > 0:
        exception_type, exception_object, exception_traceback = sys.exc_info()
        filename = os.path.split(exception_traceback.tb_frame.f_code.co_filename)[1]
        line = exception_traceback.tb_lineno
        logerr("%s: Exception: %s - %s File: %s Line: %s" % (class_name, e.__class__.__name__, e, str(filename), str(line)))
        if addcontent is not None:
            logerr("%s: Exception: %s" % (class_name, str(addcontent)))

def get_unit_from_column(obs_column, usUnits):
    pollutant_group = weewx.units.obs_group_dict.get(obs_column)
    obs_unit = None
    if usUnits == weewx.US:
        obs_unit = weewx.units.USUnits[pollutant_group]
    elif usUnits == weewx.METRIC:
        obs_unit = weewx.units.MetricUnits[pollutant_group]
    elif usUnits == weewx.METRICWX:
        obs_unit = weewx.units.MetricWXUnits[pollutant_group]
    return obs_unit

class AbstractClass:
    def __init__(self, name=None, engine=None, config_dict=None, event=None, debug=0, log_success=False, log_failure=True):
        self.name = name

class Calculate(AbstractClass):

    def get_data_result(self):
        return self.data_result

    def __init__(self, name, engine, config_dict, event, debug=0, log_success=False, log_failure=True):
        super(Calculate,self).__init__(name=name, engine=engine, config_dict=config_dict, event=event, debug=debug, log_success=log_success, log_failure=log_failure)

        self.name = name
        self.engine = engine
        self.config = config_dict
        self.event = event
        self.data_result = dict()

        self.debug = weeutil.weeutil.to_int(config_dict.get('debug', debug))
        self.log_success = weeutil.weeutil.to_bool(config_dict.get('log_success', log_success))
        self.log_failure = weeutil.weeutil.to_bool(config_dict.get('log_failure', log_failure))

        if self.debug > 0:
            logdbg("%s: init started" % self.name)
        if self.debug > 2:
            logdbg("%s: init 'standard' config %s" % (self.name, json.dumps(config_dict['standard'])))
            logdbg("%s: init 'sensor' config %s" % (self.name, json.dumps(config_dict['aq'])))
            logdbg("%s: init 'weather' config %s" % (self.name, json.dumps(config_dict['weather'])))

        # configure the aqi standard
        standard_config_dict = config_dict['standard']
        fq_standard = standard_config_dict['standard']
        standard_path = '.'.join(fq_standard.split('.')[:-1])
        standard_name = fq_standard.split('.')[-1]
        __import__(standard_path)
        standard_class = getattr(sys.modules[standard_path], standard_name)
        self.aqi_standard = standard_class(int(config_dict['StdArchive']['archive_interval']))

        # configure the sensor readings
        sensor_config_dict = config_dict['aq']
        self.sensor_units_column = sensor_config_dict.get('usUnits', 'usUnits')
        self.sensor_epoch_seconds_column = sensor_config_dict.get('dateTime', 'dateTime')
        self.sensor_co_column = sensor_config_dict.get('co', None)
        self.sensor_nh3_column = sensor_config_dict.get('nh3', None)
        self.sensor_no_column = sensor_config_dict.get('no', None)
        self.sensor_no2_column = sensor_config_dict.get('no2', None)
        self.sensor_o3_column = sensor_config_dict.get('o3', None)
        self.sensor_pb_column = sensor_config_dict.get('pb', None)
        self.sensor_pm10_0_column = sensor_config_dict.get('pm10_0', None)
        self.sensor_pm2_5_column = sensor_config_dict.get('pm2_5', None)
        self.sensor_so2_column = sensor_config_dict.get('so2', None)
        self.sensor_dbm = self.engine.db_binder.get_manager(data_binding=sensor_config_dict['data_binding'], initialize=False)

        # configure the main weather sensor if needed
        sensor_config_dict = config_dict['weather']
        self.sensor_temp_column = sensor_config_dict.get('temp', None)
        self.sensor_pressure_column = sensor_config_dict.get('pressure', None)
        self.use_weather_temp = (self.sensor_temp_column is None)
        self.use_weather_pressure = (self.sensor_pressure_column is None)
        self.weather_us_units = weewx.units.unit_constants[config_dict['StdConvert']['target_unit']]
        self.weather_dbm = self.engine.db_binder.get_manager(data_binding=sensor_config_dict['data_binding'], initialize=False)

        if self.log_success or self.debug > 0:
            loginf("%s: init finished" % self.name)

    def _get_polution_sensor_columns(self):
        '''Returns a mapping from canonical to configured column names. If a
        column is not configured it will not be in the map.'''
        return _trim_dict({
            'dateTime': self.sensor_epoch_seconds_column,
            'usUnits': self.sensor_units_column,
            calculators.PM2_5: self.sensor_pm2_5_column,
            calculators.PM10_0: self.sensor_pm10_0_column,
            calculators.CO: self.sensor_co_column,
            calculators.NO: self.sensor_no_column,
            calculators.NO2: self.sensor_no2_column,
            calculators.SO2: self.sensor_so2_column,
            calculators.O3: self.sensor_o3_column,
            calculators.NH3: self.sensor_nh3_column,
            calculators.PB: self.sensor_pb_column,
        })

    def _get_weather_sensor_columns(self):
        '''Returns the epoch second column, followed by the temperature and
        pressure readings from the air pollution sensor.'''
        return _trim_dict({
            'dateTime': self.sensor_epoch_seconds_column,
            'weather_usUnits': self.sensor_units_column,
            'outTemp': self.sensor_temp_column,
            'pressure': self.sensor_pressure_column,
        })

    def _join_sensor_results(self, pollutant_observations, pollutant_cols, weather_observations, weather_cols, epsilon):
        '''Returns an array containing the join of the pollutant and weather
        observations. All joined observations must have occured within epsilon
        seconds of each other.'''
        joined = []
        try:
            po = _make_dict(next(pollutant_observations), pollutant_cols)
            wo = _make_dict(next(weather_observations), weather_cols)
            while True:
                delta = po['dateTime'] - wo['dateTime']
                if abs(delta) < epsilon:
                    # close enough.
                    d = dict.copy(po)
                    for (k, v) in list(wo.items()):
                        if k not in d or d[k] is None:
                            d[k] = v
                    joined.append(d)
                    po = _make_dict(next(pollutant_observations), pollutant_cols)
                    wo = _make_dict(next(weather_observations), weather_cols)
                elif delta > 0:
                    # pollutant is future, increment weather
                    wo = _make_dict(next(weather_observations), weather_cols)
                else:
                    # Weather is future, increment pollutant
                    po = _make_dict(next(pollutant_observations), pollutant_cols)
        except StopIteration as e:
            pass
        return joined

    def new_archive_record(self):
        '''This event is triggered when a new archive is ready from the main
        weather sensor. PurpleAir (and presumably other air sensor plugins) uses
        this event to query air sensor. This has the added benefit of
        (approximately) syncing the readings from weather and air quality
        sensors.'''
        if self.debug > 2:
            loginf("%s: new_archive_record started" % self.name)
        try:
            event = self.event
            max_time_difference = weeutil.weeutil.to_int(event.record['interval']) * 60
            now = weeutil.weeutil.to_int(event.record['dateTime'])
            start_time = now - self.aqi_standard.max_duration()
            end_time = now - max_time_difference

            # query the pollutant sensors
            sql = 'SELECT '
            pollution_sensor_real_cols = []
            pollution_sensor_as_cols = []
            first = True
            for (as_col, real_col) in list(self._get_polution_sensor_columns().items()):
                pollution_sensor_real_cols.append(real_col)
                pollution_sensor_as_cols.append(as_col)
                if not first:
                    sql += ', '
                sql += real_col + ' AS ' + as_col
                first = False
            sql += ' FROM %s WHERE %s >= ? AND %s <= ? ORDER BY %s ASC' % (self.sensor_dbm.table_name,
                self.sensor_epoch_seconds_column, self.sensor_epoch_seconds_column,
                self.sensor_epoch_seconds_column)
            #logdbg("%s: SQL1: %s --Start: %s Ende: %s" % (self.name,sql, str(start_time),str(end_time)))
            pollutant_observations = self.sensor_dbm.genSql(sql, (start_time, end_time))

            # query the weather sensors
            weather_observations = iter([])
            weather_cols = self._get_weather_sensor_columns()
            weather_observations_real_cols = []
            weather_observations_as_cols = []
            if len(weather_cols) == 4:
                # the sensor has the proper confiruration, so use it
                sql = 'SELECT '
                first = True
                for (as_col, real_col) in list(weather_cols.items()):
                    weather_observations_real_cols.append(real_col)
                    weather_observations_as_cols.append(as_col)
                    if not first:
                        sql += ', '
                    sql += real_col + ' AS ' + as_col
                    first = False
                sql += ' FROM %s WHERE %s >= ? AND %s <= ? ORDER BY %s ASC' % (
                    self.sensor_dbm.table_name,
                    self.sensor_epoch_seconds_column,
                    self.sensor_epoch_seconds_column,
                    self.sensor_epoch_seconds_column)
                #logdbg("%s: SQL2: %s --Start: %s Ende: %s" % (self.name,sql, str(start_time),str(end_time)))
                weather_observations = self.sensor_dbm.genSql(sql, (start_time, end_time))
            else:
                # We can't get the weather data from the air sensor, so use the main sensor instead
                # See https://github.com/weewx/weewx/wiki/Barometer,-pressure,-and-altimeter
                weather_observations_real_cols = [ 'dateTime', 'outTemp', 'barometer', 'usUnits' ]
                weather_observations_as_cols = [ 'dateTime', 'outTemp', 'pressure', 'weather_usUnits' ]
                sql = 'SELECT '
                first = True
                for i in range(len(weather_observations_real_cols)):
                    real_col = weather_observations_real_cols[i]
                    as_col = weather_observations_as_cols[i]
                    if not first:
                        sql += ', '
                    sql += real_col + ' AS ' + as_col
                    first = False
                sql += ' FROM archive WHERE dateTime >= ? AND dateTime <= ? ORDER BY dateTime ASC'
                #logdbg("%s: SQL3: %s --Start: %s Ende: %s" % (self.name,sql, str(start_time),str(end_time)))
                weather_observations = self.weather_dbm.genSql(sql, (start_time, end_time))

            # we need to be able to map back to underlying column for unit conversion
            as_column_to_real_column = {}
            for i in range(len(pollution_sensor_as_cols)):
                as_column_to_real_column[pollution_sensor_as_cols[i]] = pollution_sensor_real_cols[i]
            for i in range(len(weather_observations_as_cols)):
                as_column_to_real_column[weather_observations_as_cols[i]] = weather_observations_real_cols[i]

            # join the weather and pollutant tables. We do the join in code, because
            # the data could have come through two different tables.
            joined = self._join_sensor_results(
                pollutant_observations, pollution_sensor_as_cols,
                weather_observations, weather_observations_as_cols,
                max_time_difference)

            if len(joined) == 0:
                return

            # convert sensor units to aqi required units, possibly using the weather columns
            for i in range(len(joined)):
                row = joined[i]
                # convert temperature to kelvin
                outTemp_unit = get_unit_from_column(as_column_to_real_column['outTemp'], row['weather_usUnits'])
                temp_kelvin = None
                try:
                    if row['outTemp']:
                        if outTemp_unit == 'degree_C':
                            temp_kelvin = weewx.units.CtoK(row['outTemp'])
                        else:
                            temp_kelvin = weewx.units.CtoK(weewx.units.FtoC(row['outTemp']))
                except TypeError as e:
                    exception_output(self.name, e)
                    logerr("%s: outTemp is missing, some AQIs may be skipped" % (self.name))

                # convert pressure to pascals
                pressure_unit = get_unit_from_column(as_column_to_real_column['pressure'], row['weather_usUnits'])
                press_kilopascals = row['pressure']
                try:
                    if pressure_unit != 'hPa':
                        press_kilopascals = weewx.units.conversionDict[pressure_unit]['hPa'](press_kilopascals)
                    press_kilopascals /= 10
                except TypeError as e:
                    exception_output(self.name, e)
                    logerr("%s: pressure is missing, some AQIs may be skipped" % (self.name))

                for (pollutant, required_unit) in list(self.aqi_standard.get_pollutants().items()):
                    if pollutant in row and row[pollutant] is not None:
                        # convert the observed pollution units to what's required by the standard
                        try:
                            obs_unit = get_unit_from_column(as_column_to_real_column[pollutant], row['usUnits'])
                        except KeyError as e:
                            exception_output(self.name, e)
                            logerr("%s: AQI calculation could not find unit for column %s, assuming %s" \
                                % (self.name, as_column_to_real_column[pollutant], required_unit))
                            obs_unit = required_unit
                        try:
                            #logdbg("%s: pollutant=%s row[pollutant]=%s obs_unit=%s required_unit=%s temp_kelvin=%s press_kilopascals=%s" % 
                            #    (self.name, pollutant, str(row[pollutant]), obs_unit, required_unit, temp_kelvin, press_kilopascals))
                            joined[i][pollutant] = units.convert_pollutant_units(pollutant, row[pollutant], obs_unit, required_unit, temp_kelvin, press_kilopascals)
                        except TypeError as e:
                            exception_output(self.name, e)
                            logerr("%s: Could not convert %s from %s units to %s units (%f %s, %f K, %f kPa)" \
                                % (self.name, pollutant, obs_unit, required_unit, row[pollutant], obs_unit, required_unit, temp_kelvin, press_kilopascals))
                            joined[i][pollutant] = None

            # calculate the AQIs
            record = {
                'dateTime': event.record['dateTime'],
                'interval': event.record['interval'],
                'aqi_standard': self.aqi_standard.guid,
            }
            all_pollutants_available = True
            for (pollutant, required_unit) in list(self.aqi_standard.get_pollutants().items()):
                if pollutant in joined[0]:
                    try:
                        (record['aqi_' + pollutant], record['aqi_' + pollutant + '_category']) = \
                            self.aqi_standard.calculate_aqi(pollutant, required_unit, joined)
                    except ValueError as e:
                        # exception_output(self.name, e)
                        # logerr("%s AQI calculation for %s on %s failed: %s" % (type(e).__name__, pollutant, event.record['dateTime'], str(e)))
                        logerr("%s: AQI '%s' failed: %s" % (self.name, pollutant, str(e)))
                    except NotImplementedError as e:
                        exception_output(self.name, e)
                        # Canada's AQHI does not define indcies for individual pollutants
                        pass
                else:
                    all_pollutants_available = False
            if all_pollutants_available:
                try:
                    (record['aqi_composite'], record['aqi_composite_category']) = \
                        self.aqi_standard.calculate_composite_aqi(self.aqi_standard.get_pollutants(), joined)
                except (ValueError, TypeError) as e:
                    # exception_output(self.name, e)
                    # logerr("%s AQI calculation for composite on %s failed: %s" % (type(e).__name__, event.record['dateTime'], str(e)))
                    logerr("%s: AQI 'composite' failed: %s" % (self.name, str(e)))

            if len(record) > 4:
                self.data_result = record
            else:
                logerr("%s: not storing record %s for dateTime %d" % (self.name, json.dumps(record), now))
        except Exception as e:
            exception_output(self.name, e)

        if self.debug > 2:
            loginf("%s: new_archive_record finished" % self.name)


class AqiSearchList(weewx.cheetahgenerator.SearchList):
    '''Class that implements the '$aqi' tag in cheetah templates'''
    def __init__(self, generator):
        weewx.cheetahgenerator.SearchList.__init__(self, generator)
        config_dict = generator.config_dict

        # configure the aqi standard
        standard_config_dict = config_dict['AqiService']['standard']
        fq_standard = standard_config_dict['standard']
        standard_path = '.'.join(fq_standard.split('.')[:-1])
        standard_name = fq_standard.split('.')[-1]
        __import__(standard_path)
        standard_class = getattr(sys.modules[standard_path], standard_name)
        self.aqi_standard = standard_class(int(config_dict['StdArchive']['archive_interval']))

        self.search_list_extension = {
            'aqi': lambda x: self.aqi_standard.interpret_aqi_index(x.raw)
        }

    def get_extension_list(self, timespan, db_lookup):
        return [self.search_list_extension]
