# weewx-aqi
# Copyright 2018-2021 - Jonathan Koren <jonathan@jonathankoren.com>
# License: GPL 3

import operator

import calculators
import standards

AQI_VERY_GOOD = '50F0E6'
AQI_GOOD = '50CDAA'
AQI_MODERATE = 'F0E641'
AQI_POOR = 'FF5050'
AQI_VERY_POOR = '960032'

def uba_24hr_mean(observations, obs_frequency_in_sec, req_hourly_obs_ratio, min_hours):
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
        raise ValueError('uba_24hr_mean required %d hours of data, but only had %d' % (min_hours, valid_hours))

    total = 0
    for m in hourly_means:
        total += m
    return total / valid_hours


class UmweltbundesamtAirQualityIndex(standards.AqiStandards):
    '''Calculates the Umweltbundesamt Air Quality Index as defined at
    https://www.umweltbundesamt.de/sites/default/files/medien/4031/publikationen/umid_01-2021-luftqualitaetsindex.pdf
    https://www.umweltbundesamt.de/berechnungsgrundlagen-luftqualitaetsindex
    
    Note that the Umweltbundesamt does not have index values, but rather just categories.
    Therefore we define the index values as 1 through 5.
    '''
    def __init__(self, obs_frequency_in_sec):
        super(UmweltbundesamtAirQualityIndex, self).__init__(
            [AQI_VERY_GOOD, AQI_GOOD, AQI_MODERATE, AQI_POOR, AQI_VERY_POOR],
            ['Very Good', 'Good', 'Moderate', 'Poor', 'Very Poor'],
            standards.UBA_AQI_ID)
        self.calculators[calculators.PM2_5] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            mean_calculator=lambda obs: uba_24hr_mean(obs, obs_frequency_in_sec, 0.75, 18),
            unit='microgram_per_meter_cubed',
            duration_in_secs=24 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(1, 1,   0,   10) \
            .add_breakpoint(2, 2,  11,   20) \
            .add_breakpoint(3, 3,  21,   25) \
            .add_breakpoint(4, 4,  26,   50) \
            .add_breakpoint(5, 5,  51, 1000)

        self.calculators[calculators.PM10_0] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            mean_calculator=lambda obs: uba_24hr_mean(obs, obs_frequency_in_sec, 0.75, 18),
            unit='microgram_per_meter_cubed',
            duration_in_secs=24 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(1, 1,   0,   20) \
            .add_breakpoint(2, 2,  21,   35) \
            .add_breakpoint(3, 3,  36,   50) \
            .add_breakpoint(4, 4,  51,  100) \
            .add_breakpoint(5, 5, 101, 1200)

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


class UmweltbundesamtCommonAirQualityIndex(standards.AqiStandards):
    ''' Calculates the Common Air Quality hourly Index '''
    def __init__(self, obs_frequency_in_sec):
        super(UmweltbundesamtCommonAirQualityIndex, self).__init__(
            [AQI_VERY_GOOD, AQI_GOOD, AQI_MODERATE, AQI_POOR, AQI_VERY_POOR],
            ['Very Good', 'Good', 'Moderate', 'Poor', 'Very Poor'],
            standards.UBA_CAQI_ID)
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
# PWS Weiherhammer Special (only pm2_5, pm10_0)
#
# ============================================================================

class UmweltbundesamtAirQualityIndexPws(standards.AqiStandards):
    '''Calculates the Umweltbundesamt Air Quality Index as defined at
    https://www.umweltbundesamt.de/sites/default/files/medien/4031/publikationen/umid_01-2021-luftqualitaetsindex.pdf
    https://www.umweltbundesamt.de/berechnungsgrundlagen-luftqualitaetsindex
    
    Note that the Umweltbundesamt does not have index values, but rather just categories.
    Therefore we define the index values as 1 through 5.
    '''
    def __init__(self, obs_frequency_in_sec):
        super(UmweltbundesamtAirQualityIndexPws, self).__init__(
            [AQI_VERY_GOOD, AQI_GOOD, AQI_MODERATE, AQI_POOR, AQI_VERY_POOR],
            ['Very Good', 'Good', 'Moderate', 'Poor', 'Very Poor'],
            standards.UBA_AQI_PWS_ID)
        self.calculators[calculators.PM2_5] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            mean_calculator=lambda obs: uba_24hr_mean(obs, obs_frequency_in_sec, 0.75, 18),
            unit='microgram_per_meter_cubed',
            duration_in_secs=24 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(1, 1,   0,   10) \
            .add_breakpoint(2, 2,  11,   20) \
            .add_breakpoint(3, 3,  21,   25) \
            .add_breakpoint(4, 4,  26,   50) \
            .add_breakpoint(5, 5,  51, 1000)

        self.calculators[calculators.PM10_0] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            mean_calculator=lambda obs: uba_24hr_mean(obs, obs_frequency_in_sec, 0.75, 18),
            unit='microgram_per_meter_cubed',
            duration_in_secs=24 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(1, 1,   0,   20) \
            .add_breakpoint(2, 2,  21,   35) \
            .add_breakpoint(3, 3,  36,   50) \
            .add_breakpoint(4, 4,  51,  100) \
            .add_breakpoint(5, 5, 101, 1200)


class UmweltbundesamtCommonAirQualityIndexPws(standards.AqiStandards):
    ''' Calculates the Common Air Quality hourly Index '''
    def __init__(self, obs_frequency_in_sec):
        super(UmweltbundesamtCommonAirQualityIndexPws, self).__init__(
            [AQI_VERY_GOOD, AQI_GOOD, AQI_MODERATE, AQI_POOR, AQI_VERY_POOR],
            ['Very Good', 'Good', 'Moderate', 'Poor', 'Very Poor'],
            standards.UBA_CAQI_PWS_ID)
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
# UBA Station Weiden (DEBY075) Special (only pm2_5, o2, no2)
#
# ============================================================================


class UmweltbundesamtAirQualityIndex509(standards.AqiStandards):
    '''Calculates the Umweltbundesamt Air Quality Index as defined at
    https://www.umweltbundesamt.de/sites/default/files/medien/4031/publikationen/umid_01-2021-luftqualitaetsindex.pdf
    https://www.umweltbundesamt.de/berechnungsgrundlagen-luftqualitaetsindex
    
    Note that the Umweltbundesamt does not have index values, but rather just categories.
    Therefore we define the index values as 1 through 5.
    '''
    def __init__(self, obs_frequency_in_sec):
        super(UmweltbundesamtAirQualityIndex509, self).__init__(
            [AQI_VERY_GOOD, AQI_GOOD, AQI_MODERATE, AQI_POOR, AQI_VERY_POOR],
            ['Very Good', 'Good', 'Moderate', 'Poor', 'Very Poor'],
            standards.UBA_AQI_509_ID)
        self.calculators[calculators.PM2_5] = calculators.BreakpointTable(
            data_cleaner=calculators.TRUNCATE_TO_0,
            mean_cleaner=calculators.TRUNCATE_TO_0,
            mean_calculator=lambda obs: uba_24hr_mean(obs, obs_frequency_in_sec, 0.75, 18),
            unit='microgram_per_meter_cubed',
            duration_in_secs=24 * calculators.HOUR,
            obs_frequency_in_sec=obs_frequency_in_sec) \
            .add_breakpoint(1, 1,   0,   10) \
            .add_breakpoint(2, 2,  11,   20) \
            .add_breakpoint(3, 3,  21,   25) \
            .add_breakpoint(4, 4,  26,   50) \
            .add_breakpoint(5, 5,  51, 1000)

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


class UmweltbundesamtCommonAirQualityIndex509(standards.AqiStandards):
    ''' Calculates the Common Air Quality hourly Index '''
    def __init__(self, obs_frequency_in_sec):
        super(UmweltbundesamtCommonAirQualityIndex509, self).__init__(
            [AQI_VERY_GOOD, AQI_GOOD, AQI_MODERATE, AQI_POOR, AQI_VERY_POOR],
            ['Very Good', 'Good', 'Moderate', 'Poor', 'Very Poor'],
            standards.UBA_CAQI_509_ID)
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

