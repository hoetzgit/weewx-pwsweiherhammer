# weewx-aqi
# Copyright 2018-2021 - Jonathan Koren <jonathan@jonathankoren.com>
# License: GPL 3

import operator

from . import calculators
from . import standards

CUSTAQI_VERY_GOOD = '50F0E6'
CUSTAQI_GOOD = '50CDAA'
CUSTAQI_MODERATE = 'F0E641'
CUSTAQI_POOR = 'FF5050'
CUSTAQI_VERY_POOR = '960032'

CAQI_GREEN = '7ABC6A'
CAQI_LIGHT_GREEN = 'BBCF4C'
CAQI_YELLOW = 'EEC209'
CAQI_ORANGE = 'DB8503'
CAQI_RED = 'E8416F'

def custom_24hr_mean(observations, obs_frequency_in_sec, req_hourly_obs_ratio, min_hours):
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
        raise ValueError('custom_24hr_mean required %d hours of data, but only had %d' % (min_hours, valid_hours))

    total = 0
    for m in hourly_means:
        total += m
    return total / valid_hours


class CommonAirQualityHourlyIndex(standards.AqiStandards):
    '''Calculates the Common Air Quality hourly Index as defined at
    http://www.airqualitynow.eu/download/CITEAIR-Comparing_Urban_Air_Quality_across_Borders.pdf
    Section 4.1, Table 7.
    '''
    def __init__(self, obs_frequency_in_sec):
        super(CommonAirQualityIndex, self).__init__(
            [CAQI_GREEN, CAQI_LIGHT_GREEN, CAQI_YELLOW, CAQI_ORANGE, CAQI_RED],
            ['Very Low', 'Low', 'Medium', 'High', 'Very High'],
            standards.EU_CAQI_H_GUID)
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

        self.calculators[calculators.CO] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            unit='microgram_per_meter_cubed',
            duration_in_secs=1 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(  0,   25,     0,   5000) \
            .add_breakpoint( 26,   50,  5001,   7500) \
            .add_breakpoint( 51,   75,  7501,  10000) \
            .add_breakpoint( 76,  100, 10001,  20000) \
            .add_breakpoint(101, 1000, 20001, 359600)   # undefined excessive range

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


class CustomAirQualityIndex(standards.AqiStandards):
    '''Calculates the Custom Air Quality Index as defined at
    https://www.umweltbundesamt.de/sites/default/files/medien/1/dokumente/lqi_dokumentation_final_202104.pdf

    Note that the Umweltbundesamt does not have index values, but rather just categories.
    Therefore we define the index values as 1 through 5.

    Additional to the Umweltbundesamt: PM2.5
....https://de.euronews.com/wetter/copernicus-air-quality-index
    '''
    def __init__(self, obs_frequency_in_sec):
        super(CustomAirQualityIndex, self).__init__(
            [CUSTAQI_VERY_GOOD, CUSTAQI_GOOD, CUSTAQI_MODERATE, CUSTAQI_POOR, CUSTAQI_VERY_POOR],
            ['Very Good', 'Good', 'Moderate', 'Poor', 'Very Poor'],
            standards.EU_CUSTAQI_GUID)
        self.calculators[calculators.NO2] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            unit='microgram_per_meter_cubed',
            duration_in_secs=1 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(1, 1,   0,   20) \
            .add_breakpoint(2, 2,  21,   40) \
            .add_breakpoint(3, 3,  41,  100) \
            .add_breakpoint(4, 4, 101,  200) \
            .add_breakpoint(5, 5, 201, 1000)

        self.calculators[calculators.PM2_5] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            mean_calculator=lambda obs: custom_24hr_mean(obs, obs_frequency_in_sec, 0.75, 18),
            unit='microgram_per_meter_cubed',
            duration_in_secs=24 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(1, 1,   0,  10) \
            .add_breakpoint(2, 2,  11,  20) \
            .add_breakpoint(3, 3,  21,  25) \
            .add_breakpoint(4, 4,  26,  50) \
            .add_breakpoint(5, 5,  51, 800)

        self.calculators[calculators.PM10_0] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            mean_calculator=lambda obs: custom_24hr_mean(obs, obs_frequency_in_sec, 0.75, 18),
            unit='microgram_per_meter_cubed',
            duration_in_secs=24 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(1, 1,   0,   20) \
            .add_breakpoint(2, 2,  21,   35) \
            .add_breakpoint(3, 3,  36,   50) \
            .add_breakpoint(4, 4,  51,  100) \
            .add_breakpoint(5, 5, 101, 1200)

        self.calculators[calculators.O3] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            unit='microgram_per_meter_cubed',
            duration_in_secs=1 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(1, 1,  0,   60) \
            .add_breakpoint(2, 2,  61, 120) \
            .add_breakpoint(3, 3, 121, 180) \
            .add_breakpoint(4, 4, 181, 240) \
            .add_breakpoint(5, 5, 241, 800)
