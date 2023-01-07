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

import weewx.units
#
# Ecowitt GW1100 Sainlogic WS3500 WH65
weewx.units.obs_group_dict['daymaxwind'] = 'group_speed'
weewx.units.obs_group_dict['gainRain'] = 'group_rain'
weewx.units.obs_group_dict['luminosity'] = 'group_illuminance'
weewx.units.obs_group_dict['sunshine'] = 'group_count'
weewx.units.obs_group_dict['sunshineRadiationMin'] = "group_radiation"
weewx.units.obs_group_dict['sunshineThreshold'] = "group_radiation"
weewx.units.obs_group_dict['sunshineThresholdMin'] = "group_radiation"
weewx.units.obs_group_dict['thswIndex'] = 'group_temperature'
weewx.units.obs_group_dict['thwIndex'] = 'group_temperature'
weewx.units.obs_group_dict['uvradiation'] = 'group_radiation'
weewx.units.obs_group_dict['weekRain'] = 'group_rain'
weewx.units.obs_group_dict['wetBulb'] = 'group_temperature'
weewx.units.obs_group_dict['wh65_batt'] = 'group_count'
weewx.units.obs_group_dict['wh65_batt_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh65_sig'] = 'group_count'
weewx.units.obs_group_dict['wh65_sig_percent'] = 'group_percent'
#
# Ecowitt WH31
weewx.units.obs_group_dict['wh31_ch1_batt'] = 'group_count'
weewx.units.obs_group_dict['wh31_ch2_batt'] = 'group_count'
weewx.units.obs_group_dict['wh31_ch3_batt'] = 'group_count'
weewx.units.obs_group_dict['wh31_ch4_batt'] = 'group_count'
weewx.units.obs_group_dict['wh31_ch5_batt'] = 'group_count'
weewx.units.obs_group_dict['wh31_ch6_batt'] = 'group_count'
weewx.units.obs_group_dict['wh31_ch7_batt'] = 'group_count'
weewx.units.obs_group_dict['wh31_ch8_batt'] = 'group_count'
weewx.units.obs_group_dict['wh31_ch1_batt_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh31_ch2_batt_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh31_ch3_batt_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh31_ch4_batt_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh31_ch5_batt_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh31_ch6_batt_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh31_ch7_batt_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh31_ch8_batt_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh31_ch1_sig'] = 'group_count'
weewx.units.obs_group_dict['wh31_ch2_sig'] = 'group_count'
weewx.units.obs_group_dict['wh31_ch3_sig'] = 'group_count'
weewx.units.obs_group_dict['wh31_ch4_sig'] = 'group_count'
weewx.units.obs_group_dict['wh31_ch5_sig'] = 'group_count'
weewx.units.obs_group_dict['wh31_ch6_sig'] = 'group_count'
weewx.units.obs_group_dict['wh31_ch7_sig'] = 'group_count'
weewx.units.obs_group_dict['wh31_ch8_sig'] = 'group_count'
weewx.units.obs_group_dict['wh31_ch1_sig_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh31_ch2_sig_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh31_ch3_sig_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh31_ch4_sig_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh31_ch5_sig_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh31_ch6_sig_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh31_ch7_sig_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh31_ch8_sig_percent'] = 'group_percent'
#
# Ecowitt Blitzsensor WH57
weewx.units.obs_group_dict['wh57_batt'] = 'group_count'
weewx.units.obs_group_dict['wh57_batt_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh57_sig'] = 'group_count'
weewx.units.obs_group_dict['wh57_sig_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh57_lightning_count'] = 'group_count'
weewx.units.obs_group_dict['wh57_lightning_distance'] = 'group_distance'
weewx.units.obs_group_dict['wh57_lightning_time'] = 'group_time'
#
# Ecowitt Bodenfeuchte Sensor WH51
weewx.units.obs_group_dict['soilMoist1'] = 'group_percent'
weewx.units.obs_group_dict['soilMoist2'] = 'group_percent'
weewx.units.obs_group_dict['soilMoist3'] = 'group_percent'
weewx.units.obs_group_dict['soilMoist4'] = 'group_percent'
weewx.units.obs_group_dict['soilMoist5'] = 'group_percent'
weewx.units.obs_group_dict['soilMoist6'] = 'group_percent'
weewx.units.obs_group_dict['soilMoist7'] = 'group_percent'
weewx.units.obs_group_dict['soilMoist8'] = 'group_percent'
weewx.units.obs_group_dict['wh51_ch1_batt'] = 'group_volt'
weewx.units.obs_group_dict['wh51_ch2_batt'] = 'group_volt'
weewx.units.obs_group_dict['wh51_ch3_batt'] = 'group_volt'
weewx.units.obs_group_dict['wh51_ch4_batt'] = 'group_volt'
weewx.units.obs_group_dict['wh51_ch5_batt'] = 'group_volt'
weewx.units.obs_group_dict['wh51_ch6_batt'] = 'group_volt'
weewx.units.obs_group_dict['wh51_ch7_batt'] = 'group_volt'
weewx.units.obs_group_dict['wh51_ch8_batt'] = 'group_volt'
weewx.units.obs_group_dict['wh51_ch1_batt_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh51_ch2_batt_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh51_ch3_batt_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh51_ch4_batt_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh51_ch5_batt_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh51_ch6_batt_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh51_ch7_batt_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh51_ch8_batt_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh51_ch1_sig'] = 'group_count'
weewx.units.obs_group_dict['wh51_ch2_sig'] = 'group_count'
weewx.units.obs_group_dict['wh51_ch3_sig'] = 'group_count'
weewx.units.obs_group_dict['wh51_ch4_sig'] = 'group_count'
weewx.units.obs_group_dict['wh51_ch5_sig'] = 'group_count'
weewx.units.obs_group_dict['wh51_ch6_sig'] = 'group_count'
weewx.units.obs_group_dict['wh51_ch7_sig'] = 'group_count'
weewx.units.obs_group_dict['wh51_ch8_sig'] = 'group_count'
weewx.units.obs_group_dict['wh51_ch1_sig_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh51_ch2_sig_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh51_ch3_sig_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh51_ch4_sig_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh51_ch5_sig_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh51_ch6_sig_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh51_ch7_sig_percent'] = 'group_percent'
weewx.units.obs_group_dict['wh51_ch8_sig_percent'] = 'group_percent'

#
# Ecowitt Sende - Signal in Prozent
weewx.units.obs_group_dict['signal1'] = 'group_percent'
weewx.units.obs_group_dict['signal2'] = 'group_percent'
weewx.units.obs_group_dict['signal3'] = 'group_percent'
weewx.units.obs_group_dict['signal4'] = 'group_percent'
weewx.units.obs_group_dict['signal5'] = 'group_percent'
weewx.units.obs_group_dict['signal6'] = 'group_percent'
weewx.units.obs_group_dict['signal7'] = 'group_percent'
weewx.units.obs_group_dict['signal8'] = 'group_percent'
#
# Solar Station (BME280)
weewx.units.obs_group_dict['solar_altimeter'] = 'group_pressure'
weewx.units.obs_group_dict['solar_appTemp'] = 'group_temperature'
weewx.units.obs_group_dict['solar_barometer'] = 'group_pressure'
weewx.units.obs_group_dict['solar_dewpoint'] = 'group_temperature'
weewx.units.obs_group_dict['solar_heatindex'] = 'group_temperature'
weewx.units.obs_group_dict['solar_humidex'] = 'group_temperature'
weewx.units.obs_group_dict['solar_humidity'] = 'group_percent'
weewx.units.obs_group_dict['solar_pressure'] = 'group_pressure'
weewx.units.obs_group_dict['solar_temperature'] = 'group_temperature'
weewx.units.obs_group_dict['solar_thswIndex'] = 'group_temperature'
weewx.units.obs_group_dict['solar_thwIndex'] = 'group_temperature'
weewx.units.obs_group_dict['solar_voltage'] = 'group_volt'
weewx.units.obs_group_dict['solar_voltage_percent'] = 'group_percent'
weewx.units.obs_group_dict['solar_wetBulb'] = 'group_temperature'
weewx.units.obs_group_dict['solar_windchill'] = 'group_temperature'
#
# Nova PM Sensor SDS011
weewx.units.obs_group_dict['sds011_pm2_5'] = 'group_concentration'
weewx.units.obs_group_dict['sds011_pm10_0'] = 'group_concentration'
weewx.units.obs_group_dict['sds011_temperature'] = 'group_temperature'
weewx.units.obs_group_dict['sds011_humidity'] = 'group_percent'
#
# Allsky 01 Kamera (BME280 und DS18B20)
weewx.units.obs_group_dict['asky_box_altimeter'] = 'group_pressure'
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
# FOSHKplugin
weewx.units.obs_group_dict['foshk_cloudbase'] = 'group_altitude'
weewx.units.obs_group_dict['foshk_dewpoint'] = 'group_temperature'
weewx.units.obs_group_dict['foshk_feelslike'] = 'group_temperature'
weewx.units.obs_group_dict['foshk_heatindex'] = 'group_temperature'
weewx.units.obs_group_dict['foshk_interval'] = 'group_count' #check this
weewx.units.obs_group_dict['foshk_sunhours'] = 'group_count'
weewx.units.obs_group_dict['foshk_sunshine'] = 'group_count'
weewx.units.obs_group_dict['foshk_windchill'] = 'group_temperature'
weewx.units.obs_group_dict['foshk_winddir_avg10m'] = 'group_direction'
weewx.units.obs_group_dict['foshk_windgust_max10m'] = 'group_speed'
weewx.units.obs_group_dict['foshk_windspeed_avg10m'] = 'group_speed'
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
# weewx-DWD
# dwd-mosmix
weewx.units.obs_group_dict['pop'] = 'group_percent'
weewx.units.obs_group_dict['cloudcover'] = 'group_percent'
weewx.units.obs_group_dict['rainDur'] = 'group_deltatime'
# dwd.py [CDC] (but are also defined in the extension)
weewx.units.obs_group_dict['unix_epoch'] = 'group_time'
weewx.units.obs_group_dict['cdc_Altimeter'] = 'group_pressure'
weewx.units.obs_group_dict['cdc_Altitude'] = 'group_altitude'
weewx.units.obs_group_dict['cdc_Barometer'] = 'group_pressure'
weewx.units.obs_group_dict['cdc_DateTime'] = 'group_time'
weewx.units.obs_group_dict['cdc_Dewpoint'] = 'group_temperature'
weewx.units.obs_group_dict['cdc_ExtraTemp1'] = 'group_temperature'
weewx.units.obs_group_dict['cdc_FMX_10'] = 'group_temperature' #TODO check this
weewx.units.obs_group_dict['cdc_FNX_10'] = 'group_temperature' #TODO check this
weewx.units.obs_group_dict['cdc_Latitude'] = 'group_count' #TODO check this
weewx.units.obs_group_dict['cdc_Longitude'] = 'group_count' #TODO check this
weewx.units.obs_group_dict['cdc_MESS_DATUM'] = 'group_time'
weewx.units.obs_group_dict['cdc_OutHumidity'] = 'group_percent'
weewx.units.obs_group_dict['cdc_OutTemp'] = 'group_temperature'
weewx.units.obs_group_dict['cdc_Pressure'] = 'group_pressure'
weewx.units.obs_group_dict['cdc_Quality_level'] = 'group_count' #TODO check this
weewx.units.obs_group_dict['cdc_Radiation'] = 'group_radiation'
weewx.units.obs_group_dict['cdc_Rain'] = 'group_rain'
weewx.units.obs_group_dict['cdc_RainDur'] = 'group_deltatime'
weewx.units.obs_group_dict['cdc_RainIndex'] = 'group_count' #TODO check this
weewx.units.obs_group_dict['cdc_SolarRad'] = 'group_radiation'
weewx.units.obs_group_dict['cdc_Station_id'] = 'group_count'
weewx.units.obs_group_dict['cdc_SunshineDur'] = 'group_deltatime'
weewx.units.obs_group_dict['cdc_WindDir'] = 'group_direction'
weewx.units.obs_group_dict['cdc_WindDir10'] = 'group_direction'
weewx.units.obs_group_dict['cdc_WindGust'] = 'group_speed'
weewx.units.obs_group_dict['cdc_WindGustDir'] = 'group_direction'
weewx.units.obs_group_dict['cdc_WindSpeed'] = 'group_speed'
weewx.units.obs_group_dict['cdc_WindSpeed10'] = 'group_speed'
# dwd.py [POI] (but are also defined in the extension)
weewx.units.obs_group_dict['poi_Barometer'] = 'group_pressure'
weewx.units.obs_group_dict['poi_Cloudbase'] = 'group_altitude'
weewx.units.obs_group_dict['poi_Cloudcover'] = 'group_percent'
weewx.units.obs_group_dict['poi_DateTime'] = 'group_time'
weewx.units.obs_group_dict['poi_Dewpoint'] = 'group_temperature'
weewx.units.obs_group_dict['poi_ExtraTemp1'] = 'group_temperature'
weewx.units.obs_group_dict['poi_OutHumidity'] = 'group_percent'
weewx.units.obs_group_dict['poi_OutTemp'] = 'group_temperature'
weewx.units.obs_group_dict['poi_PresentWeather'] = 'group_count' #TODO check this
weewx.units.obs_group_dict['poi_Radiation'] = 'group_radiation'
weewx.units.obs_group_dict['poi_Rain'] = 'group_rain'
weewx.units.obs_group_dict['poi_SnowDepth'] = 'group_rain' #TODO check this
weewx.units.obs_group_dict['poi_SolarRad'] = 'group_radiation'
weewx.units.obs_group_dict['poi_Visibility'] = 'group_distance'
weewx.units.obs_group_dict['poi_WindDir'] = 'group_direction'
weewx.units.obs_group_dict['poi_WindSpeed'] = 'group_speed'
#
# weewx-GTS (but are also defined in the extension)
weewx.units.obs_group_dict['boilingTemp'] = 'group_temperature'
weewx.units.obs_group_dict['dayET'] = 'group_rain'
weewx.units.obs_group_dict['energy_integral'] = 'group_radiation_energy'
weewx.units.obs_group_dict['ET24'] = 'group_rain'
weewx.units.obs_group_dict['GDD'] = 'group_degree_day'
weewx.units.obs_group_dict['growdeg'] = 'group_degree_day'
weewx.units.obs_group_dict['GTS'] = 'group_degree_day'
weewx.units.obs_group_dict['GTSdate'] = 'group_time'
weewx.units.obs_group_dict['LMTtime'] = 'group_time'
weewx.units.obs_group_dict['outEquiTemp'] = 'group_temperature'
weewx.units.obs_group_dict['outHumAbs'] = 'group_concentration'
weewx.units.obs_group_dict['outSVP'] = 'group_pressure'
weewx.units.obs_group_dict['outThetaE'] = 'group_temperature'
weewx.units.obs_group_dict['outVaporP'] = 'group_pressure'
weewx.units.obs_group_dict['seasonGDD'] = 'group_degree_day'
weewx.units.obs_group_dict['solarEnergy'] = 'group_radiation_energy'
weewx.units.obs_group_dict['utcoffsetLMT'] = 'group_deltatime'
weewx.units.obs_group_dict['yearGDD'] = 'group_degree_day'
#
# data from weewx-loopdata
weewx.units.obs_group_dict['lightning_strike_count_sum10m'] = 'group_count' #TODO check this
weewx.units.obs_group_dict['lightning_strike_count_sum2m'] = 'group_count' #TODO check this
weewx.units.obs_group_dict['lightning_strike_count_sum30m'] = 'group_count' #TODO check this
weewx.units.obs_group_dict['lightning_strike_count_sum5m'] = 'group_count' #TODO check this
weewx.units.obs_group_dict['lightning_strike_count_sum60m'] = 'group_count' #TODO check this
weewx.units.obs_group_dict['rain_sum10m'] = 'group_rain' #TODO check this
weewx.units.obs_group_dict['rain_sum2m'] = 'group_rain' #TODO check this
weewx.units.obs_group_dict['rain_sum30m'] = 'group_rain' #TODO check this
weewx.units.obs_group_dict['rain_sum5m'] = 'group_rain' #TODO check this
weewx.units.obs_group_dict['rain_sum60m'] = 'group_rain' #TODO check this
weewx.units.obs_group_dict['sunshine_avg10m'] = 'group_count' #TODO check this
weewx.units.obs_group_dict['sunshine_avg2m'] = 'group_count' #TODO check this
weewx.units.obs_group_dict['sunshine_avg30m'] = 'group_count' #TODO check this
weewx.units.obs_group_dict['sunshine_avg5m'] = 'group_count' #TODO check this
weewx.units.obs_group_dict['sunshine_avg60m'] = 'group_count' #TODO check this
weewx.units.obs_group_dict['trendBarometerCode'] = 'group_count' #TODO check this
weewx.units.obs_group_dict['usUnits'] = 'group_count' #TODO check this
weewx.units.obs_group_dict['windrun_NW'] = 'group_distance' #TODO check this
weewx.units.obs_group_dict['windrun_SSW'] = 'group_distance' #TODO check this
weewx.units.obs_group_dict['windrun_SW'] = 'group_distance' #TODO check this
weewx.units.obs_group_dict['windrun_W'] = 'group_distance' #TODO check this
weewx.units.obs_group_dict['windrun_WNW'] = 'group_distance' #TODO check this
weewx.units.obs_group_dict['windrun_WSW'] = 'group_distance' #TODO check this
#
# units
weewx.units.USUnits['group_radiation_energy'] = 'watt_hour_per_meter_squared'
weewx.units.MetricUnits['group_radiation_energy'] = 'watt_hour_per_meter_squared'
weewx.units.MetricWXUnits['group_radiation_energy'] = 'watt_hour_per_meter_squared'
#
# unit format
weewx.units.default_unit_format_dict['count'] = '%.0f'
weewx.units.default_unit_format_dict['kg_per_meter_qubic'] = '%.3f'
weewx.units.default_unit_format_dict['kilowatt_hour_per_meter_squared'] = '%.3f'
weewx.units.default_unit_format_dict['microgram_per_meter_cubed'] = '%.0f'
weewx.units.default_unit_format_dict['N_per_meter_squared'] = '%.3f'
weewx.units.default_unit_format_dict['uv_index'] = '%.0f'
weewx.units.default_unit_format_dict['watt_hour_per_meter_squared'] = '%.0f'
weewx.units.default_unit_format_dict['gram_per_meter_cubed'] = '%.1f'
weewx.units.default_unit_format_dict['milligram_per_meter_cubed'] = '%.1f'
# Ecowitt uvradiation
weewx.units.default_unit_format_dict['microwatt_per_meter_squared'] = '%.0f'
#
# unit label
weewx.units.default_unit_label_dict['count'] = ''
weewx.units.default_unit_label_dict['lux'] = ' Lux'
weewx.units.default_unit_label_dict['kg_per_meter_qubic'] = ' kg/m³'
weewx.units.default_unit_label_dict['kilowatt_hour_per_meter_squared'] = ' kWh/m²'
weewx.units.default_unit_label_dict['N_per_meter_squared'] = ' N/m²'
weewx.units.default_unit_label_dict['watt_hour_per_meter_squared'] = ' Wh/m²'
weewx.units.default_unit_label_dict['gram_per_meter_cubed'] = ' g/m³'
weewx.units.default_unit_label_dict['milligram_per_meter_cubed'] = ' mg/m³'
# Ecowitt uvradiation
weewx.units.default_unit_label_dict['microwatt_per_meter_squared'] = ' μW/m²'
#
# unit conversations
weewx.units.conversionDict['kilowatt_hour_per_meter_squared'] = {'watt_hour_per_meter_squared': lambda x : x * 1000.0}
weewx.units.conversionDict['watt_hour_per_meter_squared'] = {'kilowatt_hour_per_meter_squared': lambda x : x / 1000.0}
weewx.units.conversionDict['gram_per_meter_cubed'] = {'microgram_per_meter_cubed': lambda x : x * 1000000}
weewx.units.conversionDict['milligram_per_meter_cubed'] = {'microgram_per_meter_cubed': lambda x : x * 1000}
weewx.units.conversionDict['microgram_per_meter_cubed'] = {'gram_per_meter_cubed': lambda x : x * 0.000001}
weewx.units.conversionDict['microgram_per_meter_cubed'] = {'milligram_per_meter_cubed': lambda x : x * 0.001}
weewx.units.conversionDict['milligram_per_meter_cubed'] = {'gram_per_meter_cubed': lambda x : x * 0.001}
weewx.units.conversionDict['gram_per_meter_cubed'] = {'milligram_per_meter_cubed': lambda x : x * 1000}
# Ecowitt uvradiation
weewx.units.conversionDict['microwatt_per_meter_squared'] = {'milliwatt_per_meter_squared': lambda x : x * 0.001}
weewx.units.conversionDict['milliwatt_per_meter_squared'] = {'microwatt_per_meter_squared': lambda x : x * 1000.0}
weewx.units.conversionDict['microwatt_per_meter_squared'] = {'watt_per_meter_squared': lambda x : x * 0.000001}
weewx.units.conversionDict['watt_per_meter_squared'] = {'microwatt_per_meter_squared': lambda x : x * 1000000.0}
weewx.units.conversionDict['milliwatt_per_meter_squared'] = {'watt_per_meter_squared': lambda x : x * 0.001}
weewx.units.conversionDict['watt_per_meter_squared'] = {'milliwatt_per_meter_squared': lambda x : x * 1000.0}
#
# Tests
weewx.units.obs_group_dict['daySunshineDur'] = 'group_deltatime' #test weewx-mqtt
weewx.units.obs_group_dict['dayWindrun'] = 'group_distance' #test weewx-mqtt
weewx.units.obs_group_dict['daySunshineDurSum'] = 'group_deltatime' #test weewx-mqttpublish
weewx.units.obs_group_dict['dayWindrunSum'] = 'group_distance' #test weewx-mqttpublish
#
# END