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
# This data structure maps user observation types to a "unit group"
#
import weewx.units
#
# Ecowitt GW1100 Sainlogic WS3500 WH65
weewx.units.obs_group_dict['daymaxwind'] = 'group_speed'
weewx.units.obs_group_dict['eventRain'] = 'group_rain'
weewx.units.obs_group_dict['gainRain'] = 'group_rain'
weewx.units.obs_group_dict['luminosity'] = 'group_illuminance'
weewx.units.obs_group_dict['station_interval'] = 'group_deltatime'
weewx.units.obs_group_dict['stormRain'] = 'group_rain'
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
weewx.units.obs_group_dict['solar_outHumidity'] = 'group_percent'
weewx.units.obs_group_dict['solar_outTemp'] = 'group_temperature'
weewx.units.obs_group_dict['solar_pressure'] = 'group_pressure'
weewx.units.obs_group_dict['solar_sig'] = 'group_count'
weewx.units.obs_group_dict['solar_sig_percent'] = 'group_percent'
weewx.units.obs_group_dict['solar_signal_level'] = 'group_signal_strength'
weewx.units.obs_group_dict['solar_thswIndex'] = 'group_temperature'
weewx.units.obs_group_dict['solar_thwIndex'] = 'group_temperature'
weewx.units.obs_group_dict['solar_batt'] = 'group_volt'
weewx.units.obs_group_dict['solar_batt_percent'] = 'group_percent'
weewx.units.obs_group_dict['solar_wetBulb'] = 'group_temperature'
weewx.units.obs_group_dict['solar_windchill'] = 'group_temperature'
#
# Nova PM Sensor SDS011
weewx.units.obs_group_dict['airrohr_outHumidity'] = 'group_percent'
weewx.units.obs_group_dict['airrohr_outTemp'] = 'group_temperature'
weewx.units.obs_group_dict['airrohr_pm10_0'] = 'group_concentration'
weewx.units.obs_group_dict['airrohr_pm2_5'] = 'group_concentration'
weewx.units.obs_group_dict['airrohr_sig'] = 'group_count'
weewx.units.obs_group_dict['airrohr_sig_percent'] = 'group_percent'
weewx.units.obs_group_dict['airrohr_signal_level'] = 'group_signal_strength'
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
weewx.units.obs_group_dict['asky_sig'] = 'group_count'
weewx.units.obs_group_dict['asky_sig_percent'] = 'group_percent'
weewx.units.obs_group_dict['asky_signal_level'] = 'group_signal_strength'
#
# FOSHKplugin
weewx.units.obs_group_dict['foshk_cloudbase'] = 'group_altitude'
weewx.units.obs_group_dict['foshk_dewpoint'] = 'group_temperature'
weewx.units.obs_group_dict['foshk_feelslike'] = 'group_temperature'
weewx.units.obs_group_dict['foshk_heatindex'] = 'group_temperature'
weewx.units.obs_group_dict['foshk_interval'] = 'group_deltatime'
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
# open meteo API
weewx.units.obs_group_dict['visibility'] = 'group_distance'
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
weewx.units.obs_group_dict['cdc_MESS_DATUM'] = 'group_count' #TODO check this
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
#dwd.py [OPENMETEO] (but are also defined in the extension)
weewx.units.obs_group_dict['om_appTemp'] = 'group_temperature'
weewx.units.obs_group_dict['om_Barometer'] = 'group_pressure'
weewx.units.obs_group_dict['om_Cloudcover'] = 'group_percent'
weewx.units.obs_group_dict['om_Interval'] = 'group_interval'
weewx.units.obs_group_dict['om_DateTime'] = 'group_time'
weewx.units.obs_group_dict['om_Dewpoint'] = 'group_temperature'
weewx.units.obs_group_dict['om_Et'] = 'group_rain'
weewx.units.obs_group_dict['om_FreezinglevelHeight'] = 'group_altitude'
weewx.units.obs_group_dict['om_OutHumidity'] = 'group_percent'
weewx.units.obs_group_dict['om_OutTemp'] = 'group_temperature'
weewx.units.obs_group_dict['om_Rain'] = 'group_rain'
weewx.units.obs_group_dict['om_Shower'] = 'group_rain'
weewx.units.obs_group_dict['om_Snow'] = 'group_rain'
weewx.units.obs_group_dict['om_SnowDepth'] = 'group_rain'
weewx.units.obs_group_dict['om_snowfallHeight'] = 'group_altitude'
weewx.units.obs_group_dict['om_Weathercode'] = 'group_count'
weewx.units.obs_group_dict['om_WindDir'] = 'group_direction'
weewx.units.obs_group_dict['om_WindGust'] = 'group_speed'
weewx.units.obs_group_dict['om_WindSpeed'] = 'group_speed'
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
weewx.units.obs_group_dict['trend_asky_box_barometer'] = 'group_pressure'
weewx.units.obs_group_dict['trend_barometer'] = 'group_pressure'
weewx.units.obs_group_dict['trend_barometer_code'] = 'group_count'
weewx.units.obs_group_dict['trend_solar_barometer'] = 'group_pressure'
weewx.units.obs_group_dict['trend_outTemp'] = 'group_temperature'
weewx.units.obs_group_dict['usUnits'] = 'group_count' #TODO check this
weewx.units.obs_group_dict['windrun_NW'] = 'group_distance' #TODO check this
weewx.units.obs_group_dict['windrun_SSW'] = 'group_distance' #TODO check this
weewx.units.obs_group_dict['windrun_SW'] = 'group_distance' #TODO check this
weewx.units.obs_group_dict['windrun_W'] = 'group_distance' #TODO check this
weewx.units.obs_group_dict['windrun_WNW'] = 'group_distance' #TODO check this
weewx.units.obs_group_dict['windrun_WSW'] = 'group_distance' #TODO check this
#
#weewx-mqtt [[[augmentations]]]
weewx.units.obs_group_dict['day_sunshineDur_sum'] = 'group_deltatime'
weewx.units.obs_group_dict['day_windrun_sum'] = 'group_distance'
weewx.units.obs_group_dict['day_outTemp_min'] = 'group_temperature'
weewx.units.obs_group_dict['day_outTemp_mintime'] = 'group_time'
weewx.units.obs_group_dict['day_outTemp_avg'] = 'group_temperature'
weewx.units.obs_group_dict['day_outTemp_max'] = 'group_temperature'
weewx.units.obs_group_dict['day_outTemp_maxtime'] = 'group_time'
weewx.units.obs_group_dict['day_barometer_min'] = 'group_pressure'
weewx.units.obs_group_dict['day_barometer_mintime'] = 'group_time'
weewx.units.obs_group_dict['day_barometer_max'] = 'group_pressure'
weewx.units.obs_group_dict['day_barometer_maxtime'] = 'group_time'
weewx.units.obs_group_dict['day_wind_avg'] = 'group_speed'
weewx.units.obs_group_dict['day_windSpeed_avg'] = 'group_speed'
weewx.units.obs_group_dict['day_windGust_avg'] = 'group_speed'
weewx.units.obs_group_dict['day_wind_max'] = 'group_speed'
weewx.units.obs_group_dict['day_wind_maxtime'] = 'group_time'
weewx.units.obs_group_dict['day_windSpeed_max'] = 'group_speed'
weewx.units.obs_group_dict['day_windSpeed_maxtime'] = 'group_time'
weewx.units.obs_group_dict['day_windGust_max'] = 'group_speed'
weewx.units.obs_group_dict['day_windGust_maxtime'] = 'group_time'
weewx.units.obs_group_dict['day_rainRate_max'] = 'group_rainrate'
weewx.units.obs_group_dict['day_rainRate_maxtime'] = 'group_time'
weewx.units.obs_group_dict['month_outTemp_min'] = 'group_temperature'
weewx.units.obs_group_dict['month_outTemp_mintime'] = 'group_time'
weewx.units.obs_group_dict['month_outTemp_avg'] = 'group_temperature'
weewx.units.obs_group_dict['month_outTemp_max'] = 'group_temperature'
weewx.units.obs_group_dict['month_outTemp_maxtime'] = 'group_time'
weewx.units.obs_group_dict['month_barometer_min'] = 'group_pressure'
weewx.units.obs_group_dict['month_barometer_mintime'] = 'group_time'
weewx.units.obs_group_dict['month_barometer_max'] = 'group_pressure'
weewx.units.obs_group_dict['month_barometer_maxtime'] = 'group_time'
weewx.units.obs_group_dict['month_wind_avg'] = 'group_speed'
weewx.units.obs_group_dict['month_windSpeed_avg'] = 'group_speed'
weewx.units.obs_group_dict['month_windGust_avg'] = 'group_speed'
weewx.units.obs_group_dict['month_wind_max'] = 'group_speed'
weewx.units.obs_group_dict['month_wind_maxtime'] = 'group_time'
weewx.units.obs_group_dict['month_windSpeed_max'] = 'group_speed'
weewx.units.obs_group_dict['month_windSpeed_maxtime'] = 'group_time'
weewx.units.obs_group_dict['month_windGust_max'] = 'group_speed'
weewx.units.obs_group_dict['month_windGust_maxtime'] = 'group_time'
weewx.units.obs_group_dict['month_rainRate_max'] = 'group_rainrate'
weewx.units.obs_group_dict['month_rainRate_maxtime'] = 'group_time'
#
# Set up weewx-celestial observation type.
weewx.units.obs_group_dict['EarthSunDistance'] = 'group_distance'
weewx.units.obs_group_dict['EarthMoonDistance'] = 'group_distance'
weewx.units.obs_group_dict['EarthMercuryDistance'] = 'group_distance'
weewx.units.obs_group_dict['EarthVenusDistance'] = 'group_distance'
weewx.units.obs_group_dict['EarthMarsDistance'] = 'group_distance'
weewx.units.obs_group_dict['EarthJupiterDistance'] = 'group_distance'
weewx.units.obs_group_dict['EarthSaturnDistance'] = 'group_distance'
weewx.units.obs_group_dict['EarthUranusDistance'] = 'group_distance'
weewx.units.obs_group_dict['EarthNeptuneDistance'] = 'group_distance'
weewx.units.obs_group_dict['EarthPlutoDistance'] = 'group_distance'
weewx.units.obs_group_dict['SunAzimuth'] = 'group_direction'
weewx.units.obs_group_dict['SunAltitude'] = 'group_direction'
weewx.units.obs_group_dict['SunRightAscension'] = 'group_direction'
weewx.units.obs_group_dict['SunDeclination'] = 'group_direction'
weewx.units.obs_group_dict['Sunrise'] = 'group_time'
weewx.units.obs_group_dict['SunTransit'] = 'group_time'
weewx.units.obs_group_dict['Sunset'] = 'group_time'
weewx.units.obs_group_dict['yesterdaySunshineDur'] = 'group_deltatime'
weewx.units.obs_group_dict['AstronomicalTwilightStart'] = 'group_time'
weewx.units.obs_group_dict['NauticalTwilightStart'] = 'group_time'
weewx.units.obs_group_dict['CivilTwilightStart'] = 'group_time'
weewx.units.obs_group_dict['CivilTwilightEnd'] = 'group_time'
weewx.units.obs_group_dict['NauticalTwilightEnd'] = 'group_time'
weewx.units.obs_group_dict['AstronomicalTwilightEnd'] = 'group_time'
weewx.units.obs_group_dict['NextEquinox'] = 'group_time'
weewx.units.obs_group_dict['NextSolstice'] = 'group_time'
weewx.units.obs_group_dict['MoonAzimuth'] = 'group_direction'
weewx.units.obs_group_dict['MoonAltitude'] = 'group_direction'
weewx.units.obs_group_dict['MoonRightAscension'] = 'group_direction'
weewx.units.obs_group_dict['MoonDeclination'] = 'group_direction'
weewx.units.obs_group_dict['MoonFullness'] = 'group_percent'
weewx.units.obs_group_dict['MoonPhase']  = 'group_data'
weewx.units.obs_group_dict['NextNewMoon'] = 'group_time'
weewx.units.obs_group_dict['NextFullMoon'] = 'group_time'
weewx.units.obs_group_dict['NextFullMoon'] = 'group_time'
weewx.units.obs_group_dict['Moonrise']  = 'group_time'
weewx.units.obs_group_dict['MoonTransit'] = 'group_time'
weewx.units.obs_group_dict['Moonset']  = 'group_time'
#
# Set up weewx-cmon observation type.
weewx.units.obs_group_dict['net_ens160_rbytes']  = 'group_data_network'
weewx.units.obs_group_dict['net_ens160_tbytes']  = 'group_data_network'
weewx.units.obs_group_dict['mem_total']  = 'group_data_memory'
weewx.units.obs_group_dict['mem_used']  = 'group_data_memory'
weewx.units.obs_group_dict['disk_root_total']  = 'group_data_disk'
weewx.units.obs_group_dict['disk_root_used']  = 'group_data_disk'
#
# Tests
#
#weewx-mqttpublish [[[[[aggregates]]]]]
weewx.units.obs_group_dict['day_sunshineDur_sum2'] = 'group_deltatime'
#
# END using WeeWX standard unit groups
#
#===================================================================================
# New unit groups
#===================================================================================
#
weewx.units.USUnits['group_radiation_energy'] = 'watt_hour_per_meter_squared'
weewx.units.MetricUnits['group_radiation_energy'] = 'watt_hour_per_meter_squared'
weewx.units.MetricWXUnits['group_radiation_energy'] = 'watt_hour_per_meter_squared'
#
# e.g. Wifi Signal
weewx.units.USUnits['group_signal_strength'] = 'decibels_relative_to_one_milliwatt'
weewx.units.MetricUnits['group_signal_strength'] = 'decibels_relative_to_one_milliwatt'
weewx.units.MetricWXUnits['group_signal_strength'] = 'decibels_relative_to_one_milliwatt'
#
# Data memory / disk / network
weewx.units.USUnits['group_data_memory'] = 'kilobyte'
weewx.units.MetricUnits['group_data_memory'] = 'kilobyte'
weewx.units.MetricWXUnits['group_data_memory'] = 'kilobyte'
#
weewx.units.USUnits['group_data_disk'] = 'kilobyte'
weewx.units.MetricUnits['group_data_disk'] = 'kilobyte'
weewx.units.MetricWXUnits['group_data_disk'] = 'kilobyte'
#
weewx.units.USUnits['group_data_network'] = 'kilobyte'
weewx.units.MetricUnits['group_data_network'] = 'kilobyte'
weewx.units.MetricWXUnits['group_data_network'] = 'kilobyte'
#
#
#===================================================================================
# Defaults
#===================================================================================
#
# default values for formats and labels
weewx.units.default_unit_format_dict['count'] = '%.0f'
weewx.units.default_unit_format_dict['kg_per_meter_qubic'] = '%.3f'
weewx.units.default_unit_format_dict['kilowatt_hour_per_meter_squared'] = '%.3f'
weewx.units.default_unit_format_dict['microgram_per_meter_cubed'] = '%.0f'
weewx.units.default_unit_format_dict['N_per_meter_squared'] = '%.3f'
weewx.units.default_unit_format_dict['uv_index'] = '%.0f'
weewx.units.default_unit_format_dict['watt_hour_per_meter_squared'] = '%.0f'
weewx.units.default_unit_format_dict['gram_per_meter_cubed'] = '%.1f'
weewx.units.default_unit_format_dict['milligram_per_meter_cubed'] = '%.1f'
# e.g. Wifi Signal
weewx.units.default_unit_format_dict['decibels_relative_to_one_milliwatt'] = '%.0f'
# Ecowitt uvradiation
weewx.units.default_unit_format_dict['microwatt_per_meter_squared'] = '%.0f'
# Data memory / disk / network
weewx.units.default_unit_format_dict['bit'] = '%.2f'
weewx.units.default_unit_format_dict['byte'] = '%.2f'
weewx.units.default_unit_format_dict['kilobyte'] = '%.2f'
weewx.units.default_unit_format_dict['megabyte'] = '%.2f'
weewx.units.default_unit_format_dict['gigabyte'] = '%.2f'
weewx.units.default_unit_format_dict['terabyte'] = '%.2f'
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
# e.g. Wifi Signal
weewx.units.default_unit_label_dict['decibels_relative_to_one_milliwatt'] = ' dBm'
# Ecowitt uvradiation
weewx.units.default_unit_label_dict['microwatt_per_meter_squared'] = ' μW/m²'
# Data memory / disk / network
weewx.units.default_unit_label_dict['bit'] = ' Bit'
weewx.units.default_unit_label_dict['byte'] = ' B'
weewx.units.default_unit_label_dict['kilobyte'] = ' kB'
weewx.units.default_unit_label_dict['megabyte'] = ' MB'
weewx.units.default_unit_label_dict['gigabyte'] = ' GB'
weewx.units.default_unit_label_dict['terabyte'] = ' TB'
#
#
#===================================================================================
# Conversion functions to go from one unit type to another.
#===================================================================================
#
weewx.units.conversionDict['kilowatt_hour_per_meter_squared'] = {'watt_hour_per_meter_squared': lambda x : x * 1000.0}
weewx.units.conversionDict['watt_hour_per_meter_squared'] = {'kilowatt_hour_per_meter_squared': lambda x : x / 1000.0}
weewx.units.conversionDict['milligram_per_meter_cubed'] = {'microgram_per_meter_cubed': lambda x : x * 1000,
                                                           'gram_per_meter_cubed': lambda x : x * 0.001}
weewx.units.conversionDict['microgram_per_meter_cubed'] = {'gram_per_meter_cubed': lambda x : x * 0.000001,
                                                           'milligram_per_meter_cubed': lambda x : x * 0.001}
weewx.units.conversionDict['gram_per_meter_cubed'] = {'microgram_per_meter_cubed': lambda x : x * 1000000,
                                                      'milligram_per_meter_cubed': lambda x : x * 1000}
# Ecowitt uvradiation
weewx.units.conversionDict['microwatt_per_meter_squared'] = {'milliwatt_per_meter_squared': lambda x : x * 0.001,
                                                             'watt_per_meter_squared': lambda x : x * 0.000001}
weewx.units.conversionDict['milliwatt_per_meter_squared'] = {'microwatt_per_meter_squared': lambda x : x * 1000.0,
                                                             'watt_per_meter_squared': lambda x : x * 0.001}
weewx.units.conversionDict['watt_per_meter_squared'] = {'microwatt_per_meter_squared': lambda x : x * 1000000.0,
                                                        'milliwatt_per_meter_squared': lambda x : x * 1000.0}
# Data memory / disk / network
weewx.units.conversionDict['byte'] = {'kilobyte': lambda x : x / 1024,
                                      'megabyte': lambda x : x / (1024 * 1024),
                                      'gigabyte': lambda x : x / (1024 * 1024 * 1024),
                                      'terabyte': lambda x : x / (1024 * 1024 * 1024 * 1024)}
weewx.units.conversionDict['kilobyte'] = {'byte': lambda x : x * 1024,
                                          'megabyte': lambda x : x / 1024,
                                          'gigabyte': lambda x : x / (1024 * 1024),
                                          'terabyte': lambda x : x / (1024 * 1024 * 1024)}
weewx.units.conversionDict['megabyte'] = {'byte': lambda x : x * 1024 * 1024,
                                          'kilobyte': lambda x : x * 1024,
                                          'gigabyte': lambda x : x / 1024,
                                          'terabyte': lambda x : x / (1024 * 1024)}
weewx.units.conversionDict['gigabyte'] = {'byte': lambda x : x * 1024 * 1024 *1024,
                                          'kilobyte': lambda x : x * 1024 * 1024,
                                          'megabyte': lambda x : x * 1024,
                                          'terabyte': lambda x : x / 1024}
weewx.units.conversionDict['terabyte'] = {'byte': lambda x : x * 1024 * 1024 * 1024 * 1024,
                                          'kilobyte': lambda x : x * 1024 * 1024 * 1024,
                                          'megabyte': lambda x : x * 1024 * 1024,
                                          'gigabyte': lambda x : x * 1024}
