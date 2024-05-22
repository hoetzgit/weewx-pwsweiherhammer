# weewx-aqi
# Copyright 2018-2021 - Jonathan Koren <jonathan@jonathankoren.com>
# License: GPL 3

import operator

import calculators
import standards

EAQI_BRIGHT_TEAL = '51F0E6'
EAQI_TEAL = '51CBA9'
EAQI_YELLOW = 'F0E640'
EAQI_PINK = 'FF5050'
EAQI_RED = '960032'
EAQI_PURPLE = '7D2181'

def eu_24hr_mean(observations, obs_frequency_in_sec, req_hourly_obs_ratio, min_hours):
    hourly_samples = [0] * 24
    hourly_means = [0] * 24

    max_hourly_obs = calculators.HOUR / obs_frequency_in_sec

    start_time = observations[0][0]
    for obs in observations:
        index = int((start_time - obs[0]) / calculators.HOUR)
        hourly_samples[index] += 1
        hourly_means[index] += obs[1]

    valid_hours = 0
    for i in range(24):
        if (hourly_samples[i] / max_hourly_obs) >= req_hourly_obs_ratio:
            hourly_means[i] = hourly_means[i] / hourly_samples[i]
            valid_hours += 1
        else:
            hourly_means[i] = 0

    if valid_hours < min_hours:
        raise ValueError('eu_24hr_mean required %d hours of data, but only had %d' % (min_hours, valid_hours))

    total = 0
    for m in hourly_means:
        total += m
    return total / valid_hours

class EuropeanAirQualityIndex(standards.AqiStandards):
    '''Calculates the European Air Quality Index as defined at
    https://airindex.eea.europa.eu/Map/AQI/Viewer/#

    Note that the EAQI does not have index values, but rather just categories.
    Therefore we define the index values as 1 through 6.

    Implementation note: The EAQI describes how missing data can be interpolated
    based on the CAMS prediction model, but this code does not do that. Instead
    it simply flags missing data.'''
    def __init__(self, obs_frequency_in_sec):
        super(EuropeanAirQualityIndex, self).__init__(
            [EAQI_BRIGHT_TEAL, EAQI_TEAL, EAQI_YELLOW, EAQI_PINK, EAQI_RED, EAQI_PURPLE],
            ['Good', 'Fair', 'Moderate', 'Poor', 'Very Poor', 'Extremely Poor'],
            standards.EU_AQI_ID)
        self.calculators[calculators.PM2_5] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            mean_calculator=lambda obs: eu_24hr_mean(obs, obs_frequency_in_sec, 0.75, 18),
            unit='microgram_per_meter_cubed',
            duration_in_secs=24 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(1, 1,  0,   10) \
            .add_breakpoint(2, 2,  11,  20 ) \
            .add_breakpoint(3, 3,  21,  25) \
            .add_breakpoint(4, 4,  26,  50) \
            .add_breakpoint(5, 5,  51,  75) \
            .add_breakpoint(6, 6,  76, 800)

        self.calculators[calculators.PM10_0] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            mean_calculator=lambda obs: eu_24hr_mean(obs, obs_frequency_in_sec, 0.75, 18),
            unit='microgram_per_meter_cubed',
            duration_in_secs=24 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(1, 1,   0,   20) \
            .add_breakpoint(2, 2,  21,   40) \
            .add_breakpoint(3, 3,  41,   50) \
            .add_breakpoint(4, 4,  51,  100) \
            .add_breakpoint(5, 5, 101,  150) \
            .add_breakpoint(6, 6, 151, 1200)

        self.calculators[calculators.NO2] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            unit='microgram_per_meter_cubed',
            duration_in_secs=1 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(1, 1,   0,   40) \
            .add_breakpoint(2, 2,  41,   90) \
            .add_breakpoint(3, 3,  91,  120) \
            .add_breakpoint(4, 4, 121,  230) \
            .add_breakpoint(5, 5, 231,  340) \
            .add_breakpoint(6, 6, 341, 1000)

        self.calculators[calculators.O3] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            unit='microgram_per_meter_cubed',
            duration_in_secs=1 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(1, 1,  0,   50) \
            .add_breakpoint(2, 2,  51, 100) \
            .add_breakpoint(3, 3, 101, 130) \
            .add_breakpoint(4, 4, 131, 240) \
            .add_breakpoint(5, 5, 241, 380) \
            .add_breakpoint(6, 6, 381, 800)

        self.calculators[calculators.SO2] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            unit='microgram_per_meter_cubed',
            duration_in_secs=1 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(1, 1,    0,  100) \
            .add_breakpoint(2, 2,  101,  200) \
            .add_breakpoint(3, 3,  201,  350) \
            .add_breakpoint(4, 4,  351,  500) \
            .add_breakpoint(5, 5,  501,  750) \
            .add_breakpoint(6, 6,  751, 1250)

class EuropeanCommonAirQualityIndex(standards.AqiStandards):
    ''' Calculates the Common Air Quality hourly Index '''
    def __init__(self, obs_frequency_in_sec):
        super(EuropeanCommonAirQualityIndex, self).__init__(
            [EAQI_BRIGHT_TEAL, EAQI_TEAL, EAQI_YELLOW, EAQI_PINK, EAQI_RED, EAQI_PURPLE],
            ['Good', 'Fair', 'Moderate', 'Poor', 'Very Poor', 'Extremely Poor'],
            standards.EU_CAQI_ID)
        self.calculators[calculators.PM2_5] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            unit='microgram_per_meter_cubed',
            duration_in_secs=1 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(  0,   25,   0,   15) \
            .add_breakpoint( 26,   50,  16,   30) \
            .add_breakpoint( 51,   75,  31,   55) \
            .add_breakpoint( 76,  100,  56,  110) \
            .add_breakpoint(101, 1000, 111, 1010)       # undefined excessive range

        self.calculators[calculators.PM10_0] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            unit='microgram_per_meter_cubed',
            duration_in_secs=1 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(  0,   25,   0,   25) \
            .add_breakpoint( 26,   50,  26,   50) \
            .add_breakpoint( 51,   75,  51,   90) \
            .add_breakpoint( 76,  100,  91,  180) \
            .add_breakpoint(101, 1000, 181, 1080)       # undefined excessive range

        self.calculators[calculators.NO2] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            unit='microgram_per_meter_cubed',
            duration_in_secs=1 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(  0,   25,   0,   50) \
            .add_breakpoint( 26,   50,  51,  100) \
            .add_breakpoint( 51,   75, 101,  200) \
            .add_breakpoint( 76,  100, 201,  400) \
            .add_breakpoint(101, 1000, 401, 1300)       # undefined excessive range

        self.calculators[calculators.O3] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            unit='microgram_per_meter_cubed',
            duration_in_secs=1 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(  0,   25,   0,   60) \
            .add_breakpoint( 26,   50,  61,  120) \
            .add_breakpoint( 51,   75, 121,  180) \
            .add_breakpoint( 76,  100, 181,  240) \
            .add_breakpoint(101, 1000, 241, 1140)       # undefined excessive range

        self.calculators[calculators.SO2] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            unit='microgram_per_meter_cubed',
            duration_in_secs=1 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(  0,   25,   0,   50) \
            .add_breakpoint( 26,   50,  51,  100) \
            .add_breakpoint( 51,   75, 101,  350) \
            .add_breakpoint( 76,  100, 351,  500) \
            .add_breakpoint(101, 1000, 501, 1400)       # undefined excessive range


# ============================================================================
#
# PWS Weiherhammer Special (only pm2_5, pm10_0)
#
# ============================================================================

class EuropeanAirQualityIndexPws(standards.AqiStandards):
    '''Calculates the European Air Quality Index as defined at
    https://airindex.eea.europa.eu/Map/AQI/Viewer/#

    Note that the EAQI does not have index values, but rather just categories.
    Therefore we define the index values as 1 through 6.

    Implementation note: The EAQI describes how missing data can be interpolated
    based on the CAMS prediction model, but this code does not do that. Instead
    it simply flags missing data.'''
    def __init__(self, obs_frequency_in_sec):
        super(EuropeanAirQualityIndexPws, self).__init__(
            [EAQI_BRIGHT_TEAL, EAQI_TEAL, EAQI_YELLOW, EAQI_PINK, EAQI_RED, EAQI_PURPLE],
            ['Good', 'Fair', 'Moderate', 'Poor', 'Very Poor', 'Extremely Poor'],
            standards.EU_AQI_PWS_ID)
        self.calculators[calculators.PM2_5] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            mean_calculator=lambda obs: eu_24hr_mean(obs, obs_frequency_in_sec, 0.75, 18),
            unit='microgram_per_meter_cubed',
            duration_in_secs=24 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(1, 1,  0,   10) \
            .add_breakpoint(2, 2,  11,  20 ) \
            .add_breakpoint(3, 3,  21,  25) \
            .add_breakpoint(4, 4,  26,  50) \
            .add_breakpoint(5, 5,  51,  75) \
            .add_breakpoint(6, 6,  76, 800)

        self.calculators[calculators.PM10_0] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            mean_calculator=lambda obs: eu_24hr_mean(obs, obs_frequency_in_sec, 0.75, 18),
            unit='microgram_per_meter_cubed',
            duration_in_secs=24 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(1, 1,   0,   20) \
            .add_breakpoint(2, 2,  21,   40) \
            .add_breakpoint(3, 3,  41,   50) \
            .add_breakpoint(4, 4,  51,  100) \
            .add_breakpoint(5, 5, 101,  150) \
            .add_breakpoint(6, 6, 151, 1200)

class EuropeanCommonAirQualityIndexPws(standards.AqiStandards):
    ''' Calculates the Common Air Quality hourly Index '''
    def __init__(self, obs_frequency_in_sec):
        super(EuropeanCommonAirQualityIndexPws, self).__init__(
            [EAQI_BRIGHT_TEAL, EAQI_TEAL, EAQI_YELLOW, EAQI_PINK, EAQI_RED, EAQI_PURPLE],
            ['Good', 'Fair', 'Moderate', 'Poor', 'Very Poor', 'Extremely Poor'],
            standards.EU_CAQI_PWS_ID)
        self.calculators[calculators.PM2_5] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            unit='microgram_per_meter_cubed',
            duration_in_secs=1 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(  0,   25,   0,   15) \
            .add_breakpoint( 26,   50,  16,   30) \
            .add_breakpoint( 51,   75,  31,   55) \
            .add_breakpoint( 76,  100,  56,  110) \
            .add_breakpoint(101, 1000, 111, 1010)       # undefined excessive range

        self.calculators[calculators.PM10_0] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            unit='microgram_per_meter_cubed',
            duration_in_secs=1 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(  0,   25,   0,   25) \
            .add_breakpoint( 26,   50,  26,   50) \
            .add_breakpoint( 51,   75,  51,   90) \
            .add_breakpoint( 76,  100,  91,  180) \
            .add_breakpoint(101, 1000, 181, 1080)       # undefined excessive range


# ============================================================================
#
# UBA Station Tiefenbach/Altenschneeberg (DEBY072) Special (only pm2_5, pm10_0, o2, no2)
#
# ============================================================================

class EuropeanAirQualityIndex506(standards.AqiStandards):
    '''Calculates the European Air Quality Index as defined at
    https://airindex.eea.europa.eu/Map/AQI/Viewer/#

    Note that the EAQI does not have index values, but rather just categories.
    Therefore we define the index values as 1 through 6.

    Implementation note: The EAQI describes how missing data can be interpolated
    based on the CAMS prediction model, but this code does not do that. Instead
    it simply flags missing data.'''
    def __init__(self, obs_frequency_in_sec):
        super(EuropeanAirQualityIndex506, self).__init__(
            [EAQI_BRIGHT_TEAL, EAQI_TEAL, EAQI_YELLOW, EAQI_PINK, EAQI_RED, EAQI_PURPLE],
            ['Good', 'Fair', 'Moderate', 'Poor', 'Very Poor', 'Extremely Poor'],
            standards.EU_AQI_506_ID)
        self.calculators[calculators.PM2_5] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            mean_calculator=lambda obs: eu_24hr_mean(obs, obs_frequency_in_sec, 0.75, 18),
            unit='microgram_per_meter_cubed',
            duration_in_secs=24 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(1, 1,  0,   10) \
            .add_breakpoint(2, 2,  11,  20 ) \
            .add_breakpoint(3, 3,  21,  25) \
            .add_breakpoint(4, 4,  26,  50) \
            .add_breakpoint(5, 5,  51,  75) \
            .add_breakpoint(6, 6,  76, 800)

        self.calculators[calculators.PM10_0] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            mean_calculator=lambda obs: eu_24hr_mean(obs, obs_frequency_in_sec, 0.75, 18),
            unit='microgram_per_meter_cubed',
            duration_in_secs=24 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(1, 1,   0,   20) \
            .add_breakpoint(2, 2,  21,   40) \
            .add_breakpoint(3, 3,  41,   50) \
            .add_breakpoint(4, 4,  51,  100) \
            .add_breakpoint(5, 5, 101,  150) \
            .add_breakpoint(6, 6, 151, 1200)

        self.calculators[calculators.NO2] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            unit='microgram_per_meter_cubed',
            duration_in_secs=1 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(1, 1,   0,   40) \
            .add_breakpoint(2, 2,  41,   90) \
            .add_breakpoint(3, 3,  91,  120) \
            .add_breakpoint(4, 4, 121,  230) \
            .add_breakpoint(5, 5, 231,  340) \
            .add_breakpoint(6, 6, 341, 1000)

        self.calculators[calculators.O3] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            unit='microgram_per_meter_cubed',
            duration_in_secs=1 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(1, 1,  0,   50) \
            .add_breakpoint(2, 2,  51, 100) \
            .add_breakpoint(3, 3, 101, 130) \
            .add_breakpoint(4, 4, 131, 240) \
            .add_breakpoint(5, 5, 241, 380) \
            .add_breakpoint(6, 6, 381, 800)

class EuropeanCommonAirQualityIndex506(standards.AqiStandards):
    ''' Calculates the Common Air Quality hourly Index '''
    def __init__(self, obs_frequency_in_sec):
        super(EuropeanCommonAirQualityIndex506, self).__init__(
            [EAQI_BRIGHT_TEAL, EAQI_TEAL, EAQI_YELLOW, EAQI_PINK, EAQI_RED, EAQI_PURPLE],
            ['Good', 'Fair', 'Moderate', 'Poor', 'Very Poor', 'Extremely Poor'],
            standards.EU_CAQI_506_ID)
        self.calculators[calculators.PM2_5] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            unit='microgram_per_meter_cubed',
            duration_in_secs=1 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(  0,   25,   0,   15) \
            .add_breakpoint( 26,   50,  16,   30) \
            .add_breakpoint( 51,   75,  31,   55) \
            .add_breakpoint( 76,  100,  56,  110) \
            .add_breakpoint(101, 1000, 111, 1010)       # undefined excessive range

        self.calculators[calculators.PM10_0] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            unit='microgram_per_meter_cubed',
            duration_in_secs=1 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(  0,   25,   0,   25) \
            .add_breakpoint( 26,   50,  26,   50) \
            .add_breakpoint( 51,   75,  51,   90) \
            .add_breakpoint( 76,  100,  91,  180) \
            .add_breakpoint(101, 1000, 181, 1080)       # undefined excessive range

        self.calculators[calculators.NO2] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            unit='microgram_per_meter_cubed',
            duration_in_secs=1 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(  0,   25,   0,   50) \
            .add_breakpoint( 26,   50,  51,  100) \
            .add_breakpoint( 51,   75, 101,  200) \
            .add_breakpoint( 76,  100, 201,  400) \
            .add_breakpoint(101, 1000, 401, 1300)       # undefined excessive range

        self.calculators[calculators.O3] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            unit='microgram_per_meter_cubed',
            duration_in_secs=1 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(  0,   25,   0,   60) \
            .add_breakpoint( 26,   50,  61,  120) \
            .add_breakpoint( 51,   75, 121,  180) \
            .add_breakpoint( 76,  100, 181,  240) \
            .add_breakpoint(101, 1000, 241, 1140)       # undefined excessive range


# ============================================================================
#
# UBA Station Weiden (DEBY075) Special (only pm2_5, o2, no2)
#
# ============================================================================

class EuropeanAirQualityIndex509(standards.AqiStandards):
    '''Calculates the European Air Quality Index as defined at
    https://airindex.eea.europa.eu/Map/AQI/Viewer/#

    Note that the EAQI does not have index values, but rather just categories.
    Therefore we define the index values as 1 through 6.

    Implementation note: The EAQI describes how missing data can be interpolated
    based on the CAMS prediction model, but this code does not do that. Instead
    it simply flags missing data.'''
    def __init__(self, obs_frequency_in_sec):
        super(EuropeanAirQualityIndex509, self).__init__(
            [EAQI_BRIGHT_TEAL, EAQI_TEAL, EAQI_YELLOW, EAQI_PINK, EAQI_RED, EAQI_PURPLE],
            ['Good', 'Fair', 'Moderate', 'Poor', 'Very Poor', 'Extremely Poor'],
            standards.EU_AQI_509_ID)
        self.calculators[calculators.PM2_5] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            mean_calculator=lambda obs: eu_24hr_mean(obs, obs_frequency_in_sec, 0.75, 18),
            unit='microgram_per_meter_cubed',
            duration_in_secs=24 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(1, 1,  0,   10) \
            .add_breakpoint(2, 2,  11,  20 ) \
            .add_breakpoint(3, 3,  21,  25) \
            .add_breakpoint(4, 4,  26,  50) \
            .add_breakpoint(5, 5,  51,  75) \
            .add_breakpoint(6, 6,  76, 800)

        self.calculators[calculators.NO2] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            unit='microgram_per_meter_cubed',
            duration_in_secs=1 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(1, 1,   0,   40) \
            .add_breakpoint(2, 2,  41,   90) \
            .add_breakpoint(3, 3,  91,  120) \
            .add_breakpoint(4, 4, 121,  230) \
            .add_breakpoint(5, 5, 231,  340) \
            .add_breakpoint(6, 6, 341, 1000)

        self.calculators[calculators.O3] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            unit='microgram_per_meter_cubed',
            duration_in_secs=1 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(1, 1,  0,   50) \
            .add_breakpoint(2, 2,  51, 100) \
            .add_breakpoint(3, 3, 101, 130) \
            .add_breakpoint(4, 4, 131, 240) \
            .add_breakpoint(5, 5, 241, 380) \
            .add_breakpoint(6, 6, 381, 800)

class EuropeanCommonAirQualityIndex509(standards.AqiStandards):
    ''' Calculates the Common Air Quality hourly Index '''
    def __init__(self, obs_frequency_in_sec):
        super(EuropeanCommonAirQualityIndex509, self).__init__(
            [EAQI_BRIGHT_TEAL, EAQI_TEAL, EAQI_YELLOW, EAQI_PINK, EAQI_RED, EAQI_PURPLE],
            ['Good', 'Fair', 'Moderate', 'Poor', 'Very Poor', 'Extremely Poor'],
            standards.EU_CAQI_509_ID)
        self.calculators[calculators.PM2_5] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            unit='microgram_per_meter_cubed',
            duration_in_secs=1 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(  0,   25,   0,   15) \
            .add_breakpoint( 26,   50,  16,   30) \
            .add_breakpoint( 51,   75,  31,   55) \
            .add_breakpoint( 76,  100,  56,  110) \
            .add_breakpoint(101, 1000, 111, 1010)       # undefined excessive range

        self.calculators[calculators.NO2] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            unit='microgram_per_meter_cubed',
            duration_in_secs=1 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(  0,   25,   0,   50) \
            .add_breakpoint( 26,   50,  51,  100) \
            .add_breakpoint( 51,   75, 101,  200) \
            .add_breakpoint( 76,  100, 201,  400) \
            .add_breakpoint(101, 1000, 401, 1300)       # undefined excessive range

        self.calculators[calculators.O3] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            unit='microgram_per_meter_cubed',
            duration_in_secs=1 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(  0,   25,   0,   60) \
            .add_breakpoint( 26,   50,  61,  120) \
            .add_breakpoint( 51,   75, 121,  180) \
            .add_breakpoint( 76,  100, 181,  240) \
            .add_breakpoint(101, 1000, 241, 1140)       # undefined excessive range
