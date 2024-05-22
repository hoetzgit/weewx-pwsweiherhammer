# weewx-aqi
# Copyright 2018-2021 - Jonathan Koren <jonathan@jonathankoren.com>
# License: GPL 3

from abc import ABCMeta, abstractmethod

from six import with_metaclass

#from . import calculators
import calculators

UBA_AQI_ID = 1
UBA_CAQI_ID = 2
UBA_AQI_PWS_ID = 3
UBA_CAQI_PWS_ID = 4
UBA_AQI_509_ID = 5
UBA_CAQI_509_ID = 6

EU_AQI_ID = 10
EU_CAQI_ID = 11
EU_AQI_PWS_ID = 12
EU_CAQI_PWS_ID = 13
EU_AQI_506_ID = 14
EU_CAQI_506_ID = 15
EU_AQI_509_ID = 16
EU_CAQI_509_ID = 17

US_AQI_ID = 20
US_AQI_PWS_ID = 21
US_NOWCAST_ID = 22
US_NOWCAST_PWS_ID = 23
US_AQI_506_ID = 24
US_NOWCAST_506_ID = 25
US_AQI_509_ID = 26
US_NOWCAST_509_ID = 27


class AqiStandards(with_metaclass(ABCMeta)):
    def __init__(self, colors, categories, guid):
        '''Creates an AqiStandard with the specified color and categorical scales.
        self.calculators is initalized to an empty dictionary. It is up to
        implementations to populate this dictionary as a map of pollutants to
        aqi.AqiCalculator calulators.'''
        self.colors = colors
        self.categories = categories
        self.guid = guid
        self.calculators = {}

    def max_duration(self):
        '''Returns the maximum duration window for the calculator.'''
        max = -1
        for c in list(self.calculators.values()):
            if c.max_duration() > max:
                max = c.max_duration()
        return max

    def get_pollutants(self):
        '''Returns a map of the pollutants monitored by the standard to their
        required units.'''
        d = {}
        for (pollutant, calculator) in list(self.calculators.items()):
            d[pollutant] = calculator.unit
        return d

    def calculate_aqi(self, pollutant, observation_unit, observations):
        '''Calculates the AQI for the specified pollutant. If the AQI is undefined
        for the pollutant, raises KeyError. If the calculated AQI value is undefined,
        raises ValueError. If the data is recorded in the wrong units, raises ValueError
        Observations are recorded as an array of maps containing keys `dateTime`
        (containing epoch seconds for the observation) and the key specified by
        `pollutant` with a value recorded in units of `observation_unit`.
        Returns a pair containing the AQI and the index to the AQI category.'''
        return self.calculators[pollutant].calculate(pollutant, observation_unit, observations)

    def calculate_composite_aqi(self, pollutants_and_units, observations):
        '''Calculates the AQI over the list of pollutants. Throws the appropriate
        error if the any of the AQIs can not calculated.'''
        # Per https://www3.epa.gov/airnow/aqi-technical-assistance-document-may2016.pdf ,
        # multiple AQIs (i.e. AQIs from multiple pollutants) can be combined by
        # simply taking the maximum value of the AQIs.
        #
        # (Yes, the is a US-centric standard, but it also the most common method,
        # of combining AQIs.)
        max_aqi = -1
        max_aqi_index = -1
        for pollutant in pollutants_and_units:
            observation_unit = pollutants_and_units[pollutant]
            (aqi, aqi_index) = self.calculate_aqi(pollutant, observation_unit, observations)
            if aqi > max_aqi:
                max_aqi = aqi
                max_aqi_index = aqi_index
        return (max_aqi, max_aqi_index)

    def interpret_aqi_index(self, aqi_index):
        '''Returns the color and category name associated with the pollutant
        with the aqi_index (not aqi value).'''
        if aqi_index is None:
            return {
                'color': 'None',
                'category': 'None'
            }
        return {
            'color': self.colors[int(aqi_index)],
            'category': self.categories[int(aqi_index)]
        }
