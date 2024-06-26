# weewx-aqi
# Copyright 2018-2021 - Jonathan Koren <jonathan@jonathankoren.com>
# License: GPL 3

import weewx.units
import calculators

# molar masses (aka molecular mass) in units of grams per mole
MOLAR_MASSES = {
    'c': 12.011,    # carbon
    'o': 15.999,    # oxygen
    's': 32.06,     # sulfur
    'n': 14.007,    # nitrogen
    'h':  1.008     # hydrogen
}
MOLAR_MASSES.update({
    calculators.CO:  MOLAR_MASSES['c'] + MOLAR_MASSES['o'],
    calculators.NO:  MOLAR_MASSES['n'] + MOLAR_MASSES['o'],
    calculators.NO2: MOLAR_MASSES['n'] + (2 * MOLAR_MASSES['o']),
    calculators.SO2: MOLAR_MASSES['s'] + (2 * MOLAR_MASSES['o']),
    calculators.O3:  3 * MOLAR_MASSES['o'],
    calculators.NH3: MOLAR_MASSES['n'] + (3 * MOLAR_MASSES['h']),
    calculators.PB:  207.2
})

GAS_CONSTANT = 8.31446  # in units of ((Pa m^3) / (K mol))
IDEAL_GAS_TEMP_IN_KELVIN = 273.15               # 0 centigrade
IDEAL_GAS_PRESSURE_IN_KILOPASCALS = 101.325     # 1 atmosphere

def convert_pollutant_units(pollutant, obs_value, obs_unit, required_unit, temp_in_kelvin, pressure_in_kilopascals):
    if obs_unit == required_unit:
        return obs_value

    if obs_unit in ('ppm', 'ppb') and required_unit.endswith('_per_meter_cubed'):
        ppb = obs_value
        if obs_unit == 'ppm':
            ppb = weewx.units.conversionDict[obs_unit]['ppb'](obs_value)
        ug_per_m3 = ppb_to_microgram_per_meter_cubed(pollutant, ppb, temp_in_kelvin, pressure_in_kilopascals)
        if required_unit == 'microgram_per_meter_cubed':
            return ug_per_m3
        else:
            return weewx.units.conversionDict['microgram_per_meter_cubed'][required_unit](ug_per_m3)

    elif obs_unit.endswith('_per_meter_cubed') and required_unit in ('ppm', 'ppb'):
        ug_per_m3 = obs_value
        if obs_unit == 'milligram_per_meter_cubed':
            ug_per_m3 = weewx.units.conversionDict[obs_unit]['microgram_per_meter_cubed'](obs_value)
        ppb = microgram_per_meter_cubed_to_ppb(pollutant, ug_per_m3, temp_in_kelvin, pressure_in_kilopascals)
        if required_unit == 'ppb':
            return ug_per_m3
        else:
            return weewx.units.conversionDict['ppb'][required_unit](ppb)

    else:
        return weewx.units.conversionDict[obs_unit][required_unit](obs_value)

def ppb_to_microgram_per_meter_cubed(pollutant, ppb, sensor_temp_in_kelvin=IDEAL_GAS_TEMP_IN_KELVIN, sensor_pressure_in_kilopascals=IDEAL_GAS_PRESSURE_IN_KILOPASCALS):
    '''Converts parts per billion to micrograms per cubic meters at temperature and pressure'''
    ugm3 = ppb * (sensor_pressure_in_kilopascals / GAS_CONSTANT) * MOLAR_MASSES[pollutant] / sensor_temp_in_kelvin
    return round(ugm3, 3)

def microgram_per_meter_cubed_to_ppb(pollutant, ug_per_m3, sensor_temp_in_kelvin=IDEAL_GAS_TEMP_IN_KELVIN, sensor_pressure_in_kilopascals=IDEAL_GAS_PRESSURE_IN_KILOPASCALS):
    '''Converts parts per million to micrograms per cubic meters at temperature and pressure'''
    ppb = (ug_per_m3 * sensor_temp_in_kelvin) / ((sensor_pressure_in_kilopascals / GAS_CONSTANT) * MOLAR_MASSES[pollutant])
    return round(ppb, 3)