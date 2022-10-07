#
#    Copyright (c) 2009-2021 Tom Keffer <tkeffer@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#

"""User extensions module

This module is imported from the main executable, so anything put here will be
executed before anything else happens. This makes it a good place to put user
extensions.
"""

import locale
# This will use the locale specified by the environment variable 'LANG'
# Other options are possible. See:
# http://docs.python.org/2/library/locale.html#locale.setlocale
locale.setlocale(locale.LC_ALL, '')

#
# PWS Weiherhammer AddOns
#
import weewx.units
#
# AS3935 Lightning Sensor
weewx.units.obs_group_dict['as3935_lightning_distance'] = 'group_distance'
weewx.units.obs_group_dict['as3935_lightning_disturber_count'] = 'group_count'
weewx.units.obs_group_dict['as3935_lightning_energy'] = 'group_count'
weewx.units.obs_group_dict['as3935_lightning_noise_count'] = 'group_count'
weewx.units.obs_group_dict['as3935_lightning_strike_count'] = 'group_count'
weewx.units.obs_group_dict['as3935_lightning_last_time'] = 'group_time'
#
# Allsky 01 Kamera (BME280 und DS18B20)
weewx.units.obs_group_dict['asky_box_barometer'] = 'group_pressure'
weewx.units.obs_group_dict['asky_box_dewpoint'] = 'group_temperature'
weewx.units.obs_group_dict['asky_box_fan'] = 'group_count'
weewx.units.obs_group_dict['asky_box_heatindex'] = 'group_temperature'
weewx.units.obs_group_dict['asky_box_humidity'] = 'group_percent'
weewx.units.obs_group_dict['asky_box_pressure'] = 'group_pressure'
weewx.units.obs_group_dict['asky_box_temperature'] = 'group_temperature'
weewx.units.obs_group_dict['asky_cpu_fan'] = 'group_count'
weewx.units.obs_group_dict['asky_cpu_temperature'] = 'group_temperature'
weewx.units.obs_group_dict['asky_dome_dewpoint'] = 'group_temperature'
weewx.units.obs_group_dict['asky_dome_heater'] = 'group_count'
weewx.units.obs_group_dict['asky_dome_heatindex'] = 'group_temperature'
weewx.units.obs_group_dict['asky_dome_temperature'] = 'group_temperature'
#
# FOSHKplugin AddOns
weewx.units.obs_group_dict['foshk_brightness'] = 'group_illuminance'
weewx.units.obs_group_dict['foshk_cloudbase'] = 'group_altitude'
weewx.units.obs_group_dict['foshk_dewpoint'] = 'group_temperature'
weewx.units.obs_group_dict['foshk_feelslike'] = 'group_temperature'
weewx.units.obs_group_dict['foshk_heatindex'] = 'group_temperature'
weewx.units.obs_group_dict['foshk_sunhours'] = 'group_count'
weewx.units.obs_group_dict['foshk_windchill'] = 'group_temperature'
weewx.units.obs_group_dict['foshk_winddir_avg10m'] = 'group_direction'
weewx.units.obs_group_dict['foshk_windgust_max10m'] = 'group_speed'
weewx.units.obs_group_dict['foshk_windspeed_avg10m'] = 'group_speed'
#
# Ecowitt GW1100A und Ecowitt Blitz (WH65 & WH57)
weewx.units.obs_group_dict['gw1100_dailyrain'] = 'group_rain'
weewx.units.obs_group_dict['gw1100_eventrain'] = 'group_rain'
weewx.units.obs_group_dict['gw1100_hourlyrain'] = 'group_rain'
weewx.units.obs_group_dict['gw1100_maxdailygust'] = 'group_speed'
weewx.units.obs_group_dict['gw1100_monthlyrain'] = 'group_rain'
weewx.units.obs_group_dict['gw1100_weeklyrain'] = 'group_rain'
weewx.units.obs_group_dict['gw1100_yearlyrain'] = 'group_rain'
weewx.units.obs_group_dict['lightning_last_time'] = 'group_time'
weewx.units.obs_group_dict['lightning'] = 'group_distance'
weewx.units.obs_group_dict['wh57_batt'] = 'group_count'
weewx.units.obs_group_dict['wh65_batt'] = 'group_count'
#
# Solar Station (BME280)
weewx.units.obs_group_dict['solar_appTemp'] = 'group_temperature'
weewx.units.obs_group_dict['solar_barometer'] = 'group_pressure'
weewx.units.obs_group_dict['solar_dewpoint'] = 'group_temperature'
weewx.units.obs_group_dict['solar_heatindex'] = 'group_temperature'
weewx.units.obs_group_dict['solar_humidex'] = 'group_temperature'
weewx.units.obs_group_dict['solar_humidity'] = 'group_percent'
weewx.units.obs_group_dict['solar_pressure'] = 'group_pressure'
weewx.units.obs_group_dict['solar_temperature'] = 'group_temperature'
weewx.units.obs_group_dict['solar_voltage'] = 'group_volt'
weewx.units.obs_group_dict['solar_wetBulb'] = 'group_temperature'
weewx.units.obs_group_dict['solar_windchill'] = 'group_temperature'
#
# Nova PM Sensor SDS011
weewx.units.obs_group_dict['sds011_pm2_5'] = 'group_concentration'
weewx.units.obs_group_dict['sds011_pm10_0'] = 'group_concentration'
weewx.units.obs_group_dict['sds011_temperature'] = 'group_temperature'
weewx.units.obs_group_dict['sds011_humidity'] = 'group_percent'
#
# ****** API / Extensions ******
#
# PWS Weiherhammer AQI
weewx.units.obs_group_dict['pws_aqi'] = 'group_count'
weewx.units.obs_group_dict['pws_aqi_category'] = 'group_count'
weewx.units.obs_group_dict['pws_aqi_no2'] = 'group_count'
weewx.units.obs_group_dict['pws_aqi_no2_category'] = 'group_count'
weewx.units.obs_group_dict['pws_aqi_o3'] = 'group_count'
weewx.units.obs_group_dict['pws_aqi_o3_category'] = 'group_count'
weewx.units.obs_group_dict['pws_aqi_pm10_0'] = 'group_count'
weewx.units.obs_group_dict['pws_aqi_pm10_0_category'] = 'group_count'
weewx.units.obs_group_dict['pws_aqi_pm2_5'] = 'group_count'
weewx.units.obs_group_dict['pws_aqi_pm2_5_category'] = 'group_count'
#
# OpenWeatherMap Air Pollution API
weewx.units.obs_group_dict['owm_aqi'] = 'group_count'
weewx.units.obs_group_dict['owm_co'] = 'group_concentration'
weewx.units.obs_group_dict['owm_nh3'] = 'group_concentration'
weewx.units.obs_group_dict['owm_no'] = 'group_concentration'
weewx.units.obs_group_dict['owm_no2'] = 'group_concentration'
weewx.units.obs_group_dict['owm_o3'] = 'group_concentration'
weewx.units.obs_group_dict['owm_pm10_0'] = 'group_concentration'
weewx.units.obs_group_dict['owm_pm2_5'] = 'group_concentration'
weewx.units.obs_group_dict['owm_so2'] = 'group_concentration'
#
# AerisWeather Airquality API
weewx.units.obs_group_dict['aeris_aqi'] = 'group_count'
weewx.units.obs_group_dict['aeris_co'] = 'group_concentration'
weewx.units.obs_group_dict['aeris_no2']  = 'group_concentration'
weewx.units.obs_group_dict['aeris_o3'] = 'group_concentration'
weewx.units.obs_group_dict['aeris_pm10_0'] = 'group_concentration'
weewx.units.obs_group_dict['aeris_pm2_5'] = 'group_concentration'
weewx.units.obs_group_dict['aeris_so2'] = 'group_concentration'
#
# Umweltbundesamt API
weewx.units.obs_group_dict['uba_aqi'] = 'group_count'
weewx.units.obs_group_dict['uba_aqi_category'] = 'group_count'
weewx.units.obs_group_dict['uba_no2'] = 'group_concentration'
weewx.units.obs_group_dict['uba_no2_category'] = 'group_count'
weewx.units.obs_group_dict['uba_o3'] = 'group_concentration'
weewx.units.obs_group_dict['uba_o3_category'] = 'group_count'
#
# TODO: additional Values, Groups, Units, Formats ...
weewx.units.obs_group_dict['airDensity'] = 'group_pressure3'
weewx.units.obs_group_dict['dayET'] = 'group_rain'
weewx.units.obs_group_dict['dayRain'] = 'group_rain'
weewx.units.obs_group_dict['dayRain2'] = 'group_rain'
weewx.units.obs_group_dict['lightning_strike_count1'] = 'group_count'
weewx.units.obs_group_dict['lightning_strike_count2'] = 'group_count'
weewx.units.obs_group_dict['outEquiTemp'] = 'group_temperature'
weewx.units.obs_group_dict['outHumAbs'] = 'group_concentration'
weewx.units.obs_group_dict['rain2'] = 'group_rain'
weewx.units.obs_group_dict['rain3'] = 'group_rain'
weewx.units.obs_group_dict['solarEnergy'] = 'group_radiation_energy'
weewx.units.obs_group_dict['sunshineDurOriginal'] = 'group_deltatime'
weewx.units.obs_group_dict['thswIndex'] = 'group_temperature'
weewx.units.obs_group_dict['thwIndex'] = 'group_temperature'
weewx.units.obs_group_dict['vaporPressure'] = 'group_pressure2'
weewx.units.obs_group_dict['vaporPressure2'] = 'group_pressure'
weewx.units.obs_group_dict['wetBulb'] = 'group_temperature'
weewx.units.obs_group_dict['windPressure'] = 'group_pressure2'
#
weewx.units.USUnits['group_pressure2'] = 'N_per_meter_squared'
weewx.units.USUnits['group_pressure3'] = 'kg_per_meter_qubic'
weewx.units.USUnits['group_radiation_energy'] = 'watt_hour_per_meter_squared'
#
weewx.units.MetricUnits['group_pressure2'] = 'N_per_meter_squared'
weewx.units.MetricUnits['group_pressure3'] = 'kg_per_meter_qubic'
weewx.units.MetricUnits['group_radiation_energy'] = 'watt_hour_per_meter_squared'
#
weewx.units.MetricWXUnits['group_pressure2'] = 'N_per_meter_squared'
weewx.units.MetricWXUnits['group_pressure3'] = 'kg_per_meter_qubic'
weewx.units.MetricWXUnits['group_radiation_energy'] = 'watt_hour_per_meter_squared'
#
weewx.units.default_unit_format_dict['count'] = '%.0f'
weewx.units.default_unit_format_dict['kg_per_meter_qubic'] = '%.3f'
weewx.units.default_unit_format_dict['kilowatt_hour_per_meter_squared'] = '%.3f'
weewx.units.default_unit_format_dict['microgram_per_meter_cubed'] = '%.0f'
weewx.units.default_unit_format_dict['N_per_meter_squared'] = '%.3f'
weewx.units.default_unit_format_dict['uv_index'] = '%.0f'
weewx.units.default_unit_format_dict['watt_hour_per_meter_squared'] = '%.0f'
weewx.units.default_unit_format_dict['gram_per_meter_cubed'] = '%.1f'
weewx.units.default_unit_format_dict['milligram_per_meter_cubed'] = '%.1f'
#
weewx.units.default_unit_label_dict['count'] = ''
weewx.units.default_unit_label_dict['kg_per_meter_qubic'] = ' kg/m³'
weewx.units.default_unit_label_dict['kilowatt_hour_per_meter_squared'] = ' kWh/m²'
weewx.units.default_unit_label_dict['N_per_meter_squared'] = ' N/m²'
weewx.units.default_unit_label_dict['watt_hour_per_meter_squared'] = ' Wh/m²'
weewx.units.default_unit_label_dict['gram_per_meter_cubed'] = ' g/m³'
weewx.units.default_unit_label_dict['milligram_per_meter_cubed'] = ' mg/m³'
#
weewx.units.conversionDict['kilowatt_hour_per_meter_squared'] = {'watt_hour_per_meter_squared': lambda x : x * 1000.0}
weewx.units.conversionDict['watt_hour_per_meter_squared'] = {'kilowatt_hour_per_meter_squared': lambda x : x / 1000.0}
weewx.units.conversionDict['gram_per_meter_cubed'] = {'microgram_per_meter_cubed': lambda x : x * 1000000}
weewx.units.conversionDict['milligram_per_meter_cubed'] = {'microgram_per_meter_cubed': lambda x : x * 1000}
weewx.units.conversionDict['microgram_per_meter_cubed'] = {'gram_per_meter_cubed': lambda x : x * 0.000001}
weewx.units.conversionDict['microgram_per_meter_cubed'] = {'milligram_per_meter_cubed': lambda x : x * 0.001}
weewx.units.conversionDict['milligram_per_meter_cubed'] = {'gram_per_meter_cubed': lambda x : x * 0.001}
weewx.units.conversionDict['gram_per_meter_cubed'] = {'milligram_per_meter_cubed': lambda x : x * 1000}
#
# END