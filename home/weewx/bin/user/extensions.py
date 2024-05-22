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
# Ecowitt GW1100 Sainlogic WS3500 WH65 and calculated values
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
# Ecowitt Temperaure & Humidity Sensoren WH31
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
# Ecowitt Bodenfeuchte Sensoren WH51
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
# Solar Station (BME280, Batt & Wifi) and calculated values
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
# Nova PM Sensor SDS011, DHT22(AM2302), BME280 and Wifi
weewx.units.obs_group_dict['airrohr_altimeter'] = 'group_pressure'
weewx.units.obs_group_dict['airrohr_barometer'] = 'group_pressure'
weewx.units.obs_group_dict['airrohr_bme280_dewpoint'] = 'group_temperature'
weewx.units.obs_group_dict['airrohr_bme280_outHumidity'] = 'group_percent'
weewx.units.obs_group_dict['airrohr_bme280_outTemp'] = 'group_temperature'
weewx.units.obs_group_dict['airrohr_dht22_dewpoint'] = 'group_temperature'
weewx.units.obs_group_dict['airrohr_dht22_outHumidity'] = 'group_percent'
weewx.units.obs_group_dict['airrohr_dht22_outTemp'] = 'group_temperature'
weewx.units.obs_group_dict['airrohr_pm10_0'] = 'group_concentration'
weewx.units.obs_group_dict['airrohr_pm2_5'] = 'group_concentration'
weewx.units.obs_group_dict['airrohr_pressure'] = 'group_pressure'
weewx.units.obs_group_dict['airrohr_sig'] = 'group_count'
weewx.units.obs_group_dict['airrohr_sig_percent'] = 'group_percent'
weewx.units.obs_group_dict['airrohr_signal_level'] = 'group_signal_strength'
#
# Cloudwatcher Sensor MLX90614 and Wifi
weewx.units.obs_group_dict['cloudwatcher_ambTemp'] = 'group_temperature'
weewx.units.obs_group_dict['cloudwatcher_skyTemp'] = 'group_temperature'
weewx.units.obs_group_dict['cloudwatcher_corrSkyTemp'] = 'group_temperature'
weewx.units.obs_group_dict['cloudwatcher_origCloudpercent'] = 'group_percent'
weewx.units.obs_group_dict['cloudwatcher_origWeathercode'] = 'group_count'
weewx.units.obs_group_dict['cloudwatcher_cloudpercent'] = 'group_percent'
weewx.units.obs_group_dict['cloudwatcher_weathercode'] = 'group_count'
weewx.units.obs_group_dict['cloudwatcher_sig'] = 'group_count'
weewx.units.obs_group_dict['cloudwatcher_sig_percent'] = 'group_percent'
weewx.units.obs_group_dict['cloudwatcher_signal_level'] = 'group_signal_strength'
#
# possibly snow
weewx.units.obs_group_dict['possibly_snow'] = 'group_count'
#
# PWS Current Weather Service
weewx.units.obs_group_dict['pws_Day'] = 'group_count'
weewx.units.obs_group_dict['pws_Altitude'] = 'group_altitude'
weewx.units.obs_group_dict['pws_Latitude'] = 'group_coordinate'
weewx.units.obs_group_dict['pws_Longitude'] = 'group_coordinate'
#
# Allsky 01 Kamera (BME280, DS18B20, Fan, CPU & Wifi)
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
weewx.units.obs_group_dict['asky_cam_temperature'] = 'group_temperature'
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
# PWS Weiherhammer und UBA Mix Air Quality
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
# AerisWeather Air Quality API
weewx.units.obs_group_dict['aeris_aqi'] = 'group_count'
weewx.units.obs_group_dict['aeris_co'] = 'group_concentration'
weewx.units.obs_group_dict['aeris_no2']  = 'group_concentration'
weewx.units.obs_group_dict['aeris_o3'] = 'group_concentration'
weewx.units.obs_group_dict['aeris_pm10_0'] = 'group_concentration'
weewx.units.obs_group_dict['aeris_pm2_5'] = 'group_concentration'
weewx.units.obs_group_dict['aeris_so2'] = 'group_concentration'
#
# Open-Meteo Air Quality API
weewx.units.obs_group_dict['om_aqi'] = 'group_count'
weewx.units.obs_group_dict['om_co'] = 'group_concentration'
weewx.units.obs_group_dict['om_nh3'] = 'group_concentration'
weewx.units.obs_group_dict['om_no2'] = 'group_concentration'
weewx.units.obs_group_dict['om_o3'] = 'group_concentration'
weewx.units.obs_group_dict['om_pm10_0'] = 'group_concentration'
weewx.units.obs_group_dict['om_pm2_5'] = 'group_concentration'
weewx.units.obs_group_dict['om_so2'] = 'group_concentration'
#
# OpenWeatherMap Air Quality API
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
# Umweltbundesamt Air Quality API
weewx.units.obs_group_dict['uba_aqi'] = 'group_count'
weewx.units.obs_group_dict['uba_no2'] = 'group_concentration'
weewx.units.obs_group_dict['uba_o3'] = 'group_concentration'
weewx.units.obs_group_dict['uba_pm10_0'] = 'group_concentration'
weewx.units.obs_group_dict['uba_pm2_5'] = 'group_concentration'
#
# open meteo Weather API
weewx.units.obs_group_dict['visibility'] = 'group_distance'
#
# dwd-mosmix
weewx.units.obs_group_dict['pop'] = 'group_percent'
weewx.units.obs_group_dict['cloudcover'] = 'group_percent'
weewx.units.obs_group_dict['rainDur'] = 'group_deltatime'
#
# weewx-GTS (also defined in the extension)
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
weewx.units.obs_group_dict['cloudwatcher_cloudpercent_avg10m'] = 'group_percent'
weewx.units.obs_group_dict['cloudwatcher_cloudpercent_avg20m'] = 'group_percent'
weewx.units.obs_group_dict['cloudwatcher_cloudpercent_avg2m'] = 'group_percent'
weewx.units.obs_group_dict['cloudwatcher_cloudpercent_avg30m'] = 'group_percent'
weewx.units.obs_group_dict['cloudwatcher_cloudpercent_avg5m'] = 'group_percent'
weewx.units.obs_group_dict['cloudwatcher_cloudpercent_avg60m'] = 'group_percent'
weewx.units.obs_group_dict['lightning_strike_count_sum10m'] = 'group_count'
weewx.units.obs_group_dict['lightning_strike_count_sum20m'] = 'group_count'
weewx.units.obs_group_dict['lightning_strike_count_sum2m'] = 'group_count'
weewx.units.obs_group_dict['lightning_strike_count_sum30m'] = 'group_count'
weewx.units.obs_group_dict['lightning_strike_count_sum5m'] = 'group_count'
weewx.units.obs_group_dict['lightning_strike_count_sum60m'] = 'group_count'
weewx.units.obs_group_dict['rain_sum10m'] = 'group_rain'
weewx.units.obs_group_dict['rain_sum20m'] = 'group_rain'
weewx.units.obs_group_dict['rain_sum2m'] = 'group_rain'
weewx.units.obs_group_dict['rain_sum30m'] = 'group_rain'
weewx.units.obs_group_dict['rain_sum5m'] = 'group_rain'
weewx.units.obs_group_dict['rain_sum60m'] = 'group_rain'
weewx.units.obs_group_dict['rain_trend'] = 'group_rain'
weewx.units.obs_group_dict['sunshine_avg10m'] = 'group_count'
weewx.units.obs_group_dict['sunshine_avg20m'] = 'group_count'
weewx.units.obs_group_dict['sunshine_avg2m'] = 'group_count'
weewx.units.obs_group_dict['sunshine_avg30m'] = 'group_count'
weewx.units.obs_group_dict['sunshine_avg5m'] = 'group_count'
weewx.units.obs_group_dict['sunshine_avg60m'] = 'group_count'
weewx.units.obs_group_dict['sunshine_trend'] = 'group_count'
weewx.units.obs_group_dict['trend_airrohr_barometer'] = 'group_pressure'
weewx.units.obs_group_dict['trend_asky_box_barometer'] = 'group_pressure'
weewx.units.obs_group_dict['trend_barometer'] = 'group_pressure'
weewx.units.obs_group_dict['trend_barometer_code'] = 'group_count'
weewx.units.obs_group_dict['trend_cloudwatcher_cloudpercent'] = 'group_percent'
weewx.units.obs_group_dict['trend_lightning_strike_count'] = 'group_count'
weewx.units.obs_group_dict['trend_outTemp'] = 'group_temperature'
weewx.units.obs_group_dict['trend_rain'] = 'group_rain'
weewx.units.obs_group_dict['trend_solar_barometer'] = 'group_pressure'
weewx.units.obs_group_dict['trend_solar_batt'] = 'group_volt'
weewx.units.obs_group_dict['trend_sunshine'] = 'group_count'
#
weewx.units.obs_group_dict['usUnits'] = 'group_count'
weewx.units.obs_group_dict['windrun_E'] = 'group_distance'
weewx.units.obs_group_dict['windrun_ENE'] = 'group_distance'
weewx.units.obs_group_dict['windrun_ESE'] = 'group_distance'
weewx.units.obs_group_dict['windrun_N'] = 'group_distance'
weewx.units.obs_group_dict['windrun_NE'] = 'group_distance'
weewx.units.obs_group_dict['windrun_NNE'] = 'group_distance'
weewx.units.obs_group_dict['windrun_NNW'] = 'group_distance'
weewx.units.obs_group_dict['windrun_NW'] = 'group_distance'
weewx.units.obs_group_dict['windrun_S'] = 'group_distance'
weewx.units.obs_group_dict['windrun_SE'] = 'group_distance'
weewx.units.obs_group_dict['windrun_SSE'] = 'group_distance'
weewx.units.obs_group_dict['windrun_SSW'] = 'group_distance'
weewx.units.obs_group_dict['windrun_SW'] = 'group_distance'
weewx.units.obs_group_dict['windrun_W'] = 'group_distance'
weewx.units.obs_group_dict['windrun_WNW'] = 'group_distance'
weewx.units.obs_group_dict['windrun_WSW'] = 'group_distance'
#
#weewx-mqtt [[[augmentations]]]
weewx.units.obs_group_dict['day_barometer_max'] = 'group_pressure'
weewx.units.obs_group_dict['day_barometer_maxtime'] = 'group_time'
weewx.units.obs_group_dict['day_barometer_min'] = 'group_pressure'
weewx.units.obs_group_dict['day_barometer_mintime'] = 'group_time'
weewx.units.obs_group_dict['day_lightning_strike_count_sum'] = 'group_count'
weewx.units.obs_group_dict['day_outTemp_avg'] = 'group_temperature'
weewx.units.obs_group_dict['day_outTemp_max'] = 'group_temperature'
weewx.units.obs_group_dict['day_outTemp_maxtime'] = 'group_time'
weewx.units.obs_group_dict['day_outTemp_min'] = 'group_temperature'
weewx.units.obs_group_dict['day_outTemp_mintime'] = 'group_time'
weewx.units.obs_group_dict['day_rainRate_max'] = 'group_rainrate'
weewx.units.obs_group_dict['day_rainRate_maxtime'] = 'group_time'
weewx.units.obs_group_dict['day_sunshineDur_sum'] = 'group_deltatime'
weewx.units.obs_group_dict['day_wind_avg'] = 'group_speed'
weewx.units.obs_group_dict['day_wind_max'] = 'group_speed'
weewx.units.obs_group_dict['day_wind_maxtime'] = 'group_time'
weewx.units.obs_group_dict['day_windGust_avg'] = 'group_speed'
weewx.units.obs_group_dict['day_windGust_max'] = 'group_speed'
weewx.units.obs_group_dict['day_windGust_maxtime'] = 'group_time'
weewx.units.obs_group_dict['day_windrun_sum'] = 'group_distance'
weewx.units.obs_group_dict['day_windSpeed_avg'] = 'group_speed'
weewx.units.obs_group_dict['day_windSpeed_max'] = 'group_speed'
weewx.units.obs_group_dict['day_windSpeed_maxtime'] = 'group_time'
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
# weewx-celestial observation types
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
weewx.units.obs_group_dict['yesterdaySunshine'] = 'group_deltatime'
weewx.units.obs_group_dict['daySunshine'] = 'group_deltatime'
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
# weewx-cmon observation types
weewx.units.obs_group_dict['disk_root_total']  = 'group_data_disk'
weewx.units.obs_group_dict['disk_root_used']  = 'group_data_disk'
weewx.units.obs_group_dict['mem_available']  = 'group_data_memory'
weewx.units.obs_group_dict['mem_total']  = 'group_data_memory'
weewx.units.obs_group_dict['mem_used']  = 'group_data_memory'
weewx.units.obs_group_dict['net_ens160_rbytes']  = 'group_data_network'
weewx.units.obs_group_dict['net_ens160_tbytes']  = 'group_data_network'
weewx.units.obs_group_dict['net_eth0_rbytes']  = 'group_data_network'
weewx.units.obs_group_dict['net_eth0_tbytes']  = 'group_data_network'
weewx.units.obs_group_dict['net_tun0_rbytes']  = 'group_data_network'
weewx.units.obs_group_dict['net_tun0_tbytes']  = 'group_data_network'
weewx.units.obs_group_dict['net_wg0_rbytes']  = 'group_data_network'
weewx.units.obs_group_dict['net_wg0_tbytes']  = 'group_data_network'
weewx.units.obs_group_dict['net_wlan0_rbytes']  = 'group_data_network'
weewx.units.obs_group_dict['net_wlan0_tbytes']  = 'group_data_network'
#
# Open-Meteo API -dwd-icon
weewx.units.obs_group_dict['freezinglevelHeight'] = 'group_altitude'
weewx.units.obs_group_dict['snowfallHeight'] = 'group_altitude'
#
#===================================================================================
# Tests
#===================================================================================
#
#weewx-mqttpublish [[[[[aggregates]]]]]
weewx.units.obs_group_dict['day_sunshineDur_sum2'] = 'group_deltatime'
#
#===================================================================================
# New unit groups with default unit
#===================================================================================
#
# weewx-GTS
weewx.units.USUnits['group_radiation_energy'] = 'watt_hour_per_meter_squared'
weewx.units.MetricUnits['group_radiation_energy'] = 'watt_hour_per_meter_squared'
weewx.units.MetricWXUnits['group_radiation_energy'] = 'watt_hour_per_meter_squared'
#
# weewx-DWD
weewx.units.USUnits['group_coordinate'] = 'degree_compass'
weewx.units.MetricUnits['group_coordinate'] = 'degree_compass'
weewx.units.MetricWXUnits['group_coordinate'] = 'degree_compass'
#
# Wifi Signal
weewx.units.USUnits['group_signal_strength'] = 'decibels_relative_to_one_milliwatt'
weewx.units.MetricUnits['group_signal_strength'] = 'decibels_relative_to_one_milliwatt'
weewx.units.MetricWXUnits['group_signal_strength'] = 'decibels_relative_to_one_milliwatt'
#
# Data memory
weewx.units.USUnits['group_data_memory'] = 'kilobyte'
weewx.units.MetricUnits['group_data_memory'] = 'kilobyte'
weewx.units.MetricWXUnits['group_data_memory'] = 'kilobyte'
#
# Data disk
weewx.units.USUnits['group_data_disk'] = 'kilobyte'
weewx.units.MetricUnits['group_data_disk'] = 'kilobyte'
weewx.units.MetricWXUnits['group_data_disk'] = 'kilobyte'
#
# Data network
weewx.units.USUnits['group_data_network'] = 'kilobyte'
weewx.units.MetricUnits['group_data_network'] = 'kilobyte'
weewx.units.MetricWXUnits['group_data_network'] = 'kilobyte'
#
# other groups
weewx.units.MetricUnits['group_altitude'] = 'meter'
weewx.units.MetricUnits['group_degree_day'] = 'degree_C_day'
weewx.units.MetricUnits['group_pressure'] = 'hPa'
weewx.units.MetricUnits['group_rain'] = 'mm'
weewx.units.MetricUnits['group_rainrate'] = 'mm_per_hour'
weewx.units.MetricUnits['group_speed'] = 'km_per_hour'
weewx.units.MetricUnits['group_speed2'] = 'km_per_hour2'
weewx.units.MetricUnits['group_temperature'] = 'degree_C'
#
#===================================================================================
# Defaults
#===================================================================================
#
# default values for formats
weewx.units.default_unit_format_dict.setdefault('count', '%.0f')
weewx.units.default_unit_format_dict.setdefault('kg_per_meter_qubic', '%.3f')
weewx.units.default_unit_format_dict.setdefault('kilowatt_hour_per_meter_squared', '%.3f')
weewx.units.default_unit_format_dict.setdefault('microgram_per_meter_cubed', '%.0f')
weewx.units.default_unit_format_dict.setdefault('N_per_meter_squared', '%.3f')
weewx.units.default_unit_format_dict.setdefault('uv_index', '%.0f')
weewx.units.default_unit_format_dict.setdefault('watt_hour_per_meter_squared', '%.0f')
weewx.units.default_unit_format_dict.setdefault('joule_per_meter_squared', '%.0f')
weewx.units.default_unit_format_dict.setdefault('gram_per_meter_cubed', '%.1f')
weewx.units.default_unit_format_dict.setdefault('milligram_per_meter_cubed', '%.1f')
weewx.units.default_unit_format_dict.setdefault('grains_per_meter_cubed', '%.1f')
#
# Wifi Signal
weewx.units.default_unit_format_dict.setdefault('decibels_relative_to_one_milliwatt', '%.0f')
#
# Ecowitt uvradiation
weewx.units.default_unit_format_dict.setdefault('microwatt_per_meter_squared', '%.0f')
#
# Data memory / disk / network
weewx.units.default_unit_format_dict.setdefault('bit', '%.2f')
weewx.units.default_unit_format_dict.setdefault('byte', '%.2f')
weewx.units.default_unit_format_dict.setdefault('kilobyte', '%.2f')
weewx.units.default_unit_format_dict.setdefault('megabyte', '%.2f')
weewx.units.default_unit_format_dict.setdefault('gigabyte', '%.2f')
weewx.units.default_unit_format_dict.setdefault('terabyte', '%.2f')
#
# default unit labels
weewx.units.default_unit_label_dict.setdefault('count', '')
weewx.units.default_unit_label_dict.setdefault('lux', ' Lux')
weewx.units.default_unit_label_dict.setdefault('kg_per_meter_qubic', u' kg/m³')
weewx.units.default_unit_label_dict.setdefault('kilowatt_hour_per_meter_squared', u' kWh/m²')
weewx.units.default_unit_label_dict.setdefault('N_per_meter_squared', u' N/m²')
weewx.units.default_unit_label_dict.setdefault('watt_hour_per_meter_squared', u' Wh/m²')
weewx.units.default_unit_label_dict.setdefault('joule_per_meter_squared', u' J/m²')
weewx.units.default_unit_label_dict.setdefault('joule_per_cm_squared', u' J/cm²')
weewx.units.default_unit_label_dict.setdefault('kilojoule_per_meter_squared', u' kJ/m²')
weewx.units.default_unit_label_dict.setdefault('megajoule_per_meter_squared', u' MJ/m²')
weewx.units.default_unit_label_dict.setdefault('gram_per_meter_cubed', u' g/m³')
weewx.units.default_unit_label_dict.setdefault('milligram_per_meter_cubed', u' mg/m³')
weewx.units.default_unit_label_dict.setdefault('grains_per_meter_cubed', u' grains/m³')
#
# Wifi Signal
weewx.units.default_unit_label_dict.setdefault('decibels_relative_to_one_milliwatt', ' dBm')
#
# Ecowitt uvradiation
weewx.units.default_unit_label_dict.setdefault('microwatt_per_meter_squared', u' μW/m²')
#
# Data memory / disk / network
weewx.units.default_unit_label_dict.setdefault('bit', ' Bit')
weewx.units.default_unit_label_dict.setdefault('byte', ' B')
weewx.units.default_unit_label_dict.setdefault('kilobyte', ' kB')
weewx.units.default_unit_label_dict.setdefault('megabyte', ' MB')
weewx.units.default_unit_label_dict.setdefault('gigabyte', ' GB')
weewx.units.default_unit_label_dict.setdefault('terabyte', ' TB')
#
# power plugs
weewx.units.default_unit_format_dict.setdefault('watt_hour', '%.3f')
weewx.units.default_unit_format_dict.setdefault('kilowatt_hour', '%.3f')
weewx.units.default_unit_format_dict.setdefault('watt', '%.2f')
#
#===================================================================================
# PWS Weiherhammer Luftqualität
#===================================================================================
#
weewx.units.obs_group_dict['co'] = 'group_concentration'
weewx.units.obs_group_dict['nh3'] = 'group_concentration'
weewx.units.obs_group_dict['no'] = 'group_concentration'
weewx.units.obs_group_dict['no2'] = 'group_concentration'
weewx.units.obs_group_dict['o3'] = 'group_concentration'
weewx.units.obs_group_dict['pm10_0'] = 'group_concentration'
weewx.units.obs_group_dict['pm2_5'] = 'group_concentration'
weewx.units.obs_group_dict['so2'] = 'group_concentration'
weewx.units.obs_group_dict['pb'] = 'group_concentration'
#
# AQI
weewx.units.obs_group_dict['eu_aqi_standard'] = 'group_count'
weewx.units.obs_group_dict['eu_aqi_composite'] = 'group_count'
weewx.units.obs_group_dict['eu_aqi_composite_category'] = 'group_count'
weewx.units.obs_group_dict['eu_aqi_co'] = 'group_count'
weewx.units.obs_group_dict['eu_aqi_co_category'] = 'group_count'
weewx.units.obs_group_dict['eu_aqi_nh3'] = 'group_count'
weewx.units.obs_group_dict['eu_aqi_nh3_category'] = 'group_count'
weewx.units.obs_group_dict['eu_aqi_no'] = 'group_count'
weewx.units.obs_group_dict['eu_aqi_no_category'] = 'group_count'
weewx.units.obs_group_dict['eu_aqi_no2'] = 'group_count'
weewx.units.obs_group_dict['eu_aqi_no2_category'] = 'group_count'
weewx.units.obs_group_dict['eu_aqi_o3'] = 'group_count'
weewx.units.obs_group_dict['eu_aqi_o3_category'] = 'group_count'
weewx.units.obs_group_dict['eu_aqi_pb'] = 'group_count'
weewx.units.obs_group_dict['eu_aqi_pb_category'] = 'group_count'
weewx.units.obs_group_dict['eu_aqi_pm10_0'] = 'group_count'
weewx.units.obs_group_dict['eu_aqi_pm10_0_category'] = 'group_count'
weewx.units.obs_group_dict['eu_aqi_pm2_5'] = 'group_count'
weewx.units.obs_group_dict['eu_aqi_pm2_5_category'] = 'group_count'
weewx.units.obs_group_dict['eu_aqi_so2'] = 'group_count'
weewx.units.obs_group_dict['eu_aqi_so2_category'] = 'group_count'
weewx.units.obs_group_dict['us_aqi_co'] = 'group_count'
weewx.units.obs_group_dict['us_aqi_co_category'] = 'group_count'
weewx.units.obs_group_dict['us_aqi_nh3'] = 'group_count'
weewx.units.obs_group_dict['us_aqi_nh3_category'] = 'group_count'
weewx.units.obs_group_dict['us_aqi_no'] = 'group_count'
weewx.units.obs_group_dict['us_aqi_no_category'] = 'group_count'
weewx.units.obs_group_dict['us_aqi_no2'] = 'group_count'
weewx.units.obs_group_dict['us_aqi_no2_category'] = 'group_count'
weewx.units.obs_group_dict['us_aqi_o3'] = 'group_count'
weewx.units.obs_group_dict['us_aqi_o3_category'] = 'group_count'
weewx.units.obs_group_dict['us_aqi_pb'] = 'group_count'
weewx.units.obs_group_dict['us_aqi_pb_category'] = 'group_count'
weewx.units.obs_group_dict['us_aqi_pm10_0'] = 'group_count'
weewx.units.obs_group_dict['us_aqi_pm10_0_category'] = 'group_count'
weewx.units.obs_group_dict['us_aqi_pm2_5'] = 'group_count'
weewx.units.obs_group_dict['us_aqi_pm2_5_category'] = 'group_count'
weewx.units.obs_group_dict['us_aqi_so2'] = 'group_count'
weewx.units.obs_group_dict['us_aqi_so2_category'] = 'group_count'
weewx.units.obs_group_dict['uba_aqi_co'] = 'group_count'
weewx.units.obs_group_dict['uba_aqi_co_category'] = 'group_count'
weewx.units.obs_group_dict['uba_aqi_nh3'] = 'group_count'
weewx.units.obs_group_dict['uba_aqi_nh3_category'] = 'group_count'
weewx.units.obs_group_dict['uba_aqi_no'] = 'group_count'
weewx.units.obs_group_dict['uba_aqi_no_category'] = 'group_count'
weewx.units.obs_group_dict['uba_aqi_no2'] = 'group_count'
weewx.units.obs_group_dict['uba_aqi_no2_category'] = 'group_count'
weewx.units.obs_group_dict['uba_aqi_o3'] = 'group_count'
weewx.units.obs_group_dict['uba_aqi_o3_category'] = 'group_count'
weewx.units.obs_group_dict['uba_aqi_pb'] = 'group_count'
weewx.units.obs_group_dict['uba_aqi_pb_category'] = 'group_count'
weewx.units.obs_group_dict['uba_aqi_pm10_0'] = 'group_count'
weewx.units.obs_group_dict['uba_aqi_pm10_0_category'] = 'group_count'
weewx.units.obs_group_dict['uba_aqi_pm2_5'] = 'group_count'
weewx.units.obs_group_dict['uba_aqi_pm2_5_category'] = 'group_count'
weewx.units.obs_group_dict['uba_aqi_so2'] = 'group_count'
weewx.units.obs_group_dict['uba_aqi_so2_category'] = 'group_count'

weewx.units.default_unit_format_dict.setdefault('ppm', '%.0f')
weewx.units.default_unit_format_dict.setdefault('ppb', '%.0f')

weewx.units.default_unit_label_dict.setdefault('ppm', ' ppm')
weewx.units.default_unit_label_dict.setdefault('ppb', ' ppb')

#
#===================================================================================
# Power plugs
#===================================================================================
#
weewx.units.obs_group_dict['deviceTemp1'] = 'group_temperature'
weewx.units.obs_group_dict['deviceTemp2'] = 'group_temperature'
weewx.units.obs_group_dict['deviceTemp3'] = 'group_temperature'
weewx.units.obs_group_dict['deviceTemp4'] = 'group_temperature'
weewx.units.obs_group_dict['deviceTemp5'] = 'group_temperature'
weewx.units.obs_group_dict['deviceTemp6'] = 'group_temperature'
weewx.units.obs_group_dict['deviceTemp7'] = 'group_temperature'
weewx.units.obs_group_dict['deviceTemp8'] = 'group_temperature'
weewx.units.obs_group_dict['deviceTemp9'] = 'group_temperature'
weewx.units.obs_group_dict['currentAmp1'] = 'group_amp'
weewx.units.obs_group_dict['currentAmp2'] = 'group_amp'
weewx.units.obs_group_dict['currentAmp3'] = 'group_amp'
weewx.units.obs_group_dict['currentAmp4'] = 'group_amp'
weewx.units.obs_group_dict['currentAmp5'] = 'group_amp'
weewx.units.obs_group_dict['currentAmp6'] = 'group_amp'
weewx.units.obs_group_dict['currentAmp7'] = 'group_amp'
weewx.units.obs_group_dict['currentAmp8'] = 'group_amp'
weewx.units.obs_group_dict['currentAmp9'] = 'group_amp'
weewx.units.obs_group_dict['currentPwr1'] = 'group_power'
weewx.units.obs_group_dict['currentPwr2'] = 'group_power'
weewx.units.obs_group_dict['currentPwr3'] = 'group_power'
weewx.units.obs_group_dict['currentPwr4'] = 'group_power'
weewx.units.obs_group_dict['currentPwr5'] = 'group_power'
weewx.units.obs_group_dict['currentPwr6'] = 'group_power'
weewx.units.obs_group_dict['currentPwr7'] = 'group_power'
weewx.units.obs_group_dict['currentPwr8'] = 'group_power'
weewx.units.obs_group_dict['currentPwr9'] = 'group_power'
weewx.units.obs_group_dict['dayEnergy1'] = 'group_energy'
weewx.units.obs_group_dict['dayEnergy2'] = 'group_energy'
weewx.units.obs_group_dict['dayEnergy3'] = 'group_energy'
weewx.units.obs_group_dict['dayEnergy4'] = 'group_energy'
weewx.units.obs_group_dict['dayEnergy5'] = 'group_energy'
weewx.units.obs_group_dict['dayEnergy6'] = 'group_energy'
weewx.units.obs_group_dict['dayEnergy7'] = 'group_energy'
weewx.units.obs_group_dict['dayEnergy8'] = 'group_energy'
weewx.units.obs_group_dict['dayEnergy9'] = 'group_energy'
weewx.units.obs_group_dict['totalEnergy1'] = 'group_energy'
weewx.units.obs_group_dict['totalEnergy2'] = 'group_energy'
weewx.units.obs_group_dict['totalEnergy3'] = 'group_energy'
weewx.units.obs_group_dict['totalEnergy4'] = 'group_energy'
weewx.units.obs_group_dict['totalEnergy5'] = 'group_energy'
weewx.units.obs_group_dict['totalEnergy6'] = 'group_energy'
weewx.units.obs_group_dict['totalEnergy7'] = 'group_energy'
weewx.units.obs_group_dict['totalEnergy8'] = 'group_energy'
weewx.units.obs_group_dict['totalEnergy9'] = 'group_energy'
weewx.units.obs_group_dict['currentEnergy1'] = 'group_energy'
weewx.units.obs_group_dict['currentEnergy2'] = 'group_energy'
weewx.units.obs_group_dict['currentEnergy3'] = 'group_energy'
weewx.units.obs_group_dict['currentEnergy4'] = 'group_energy'
weewx.units.obs_group_dict['currentEnergy5'] = 'group_energy'
weewx.units.obs_group_dict['currentEnergy6'] = 'group_energy'
weewx.units.obs_group_dict['currentEnergy7'] = 'group_energy'
weewx.units.obs_group_dict['currentEnergy8'] = 'group_energy'
weewx.units.obs_group_dict['currentEnergy9'] = 'group_energy'

#
#===================================================================================
# Conversion functions to go from one unit type to another.
#===================================================================================
#
# weewx-GTS, Sonnenenergie
weewx.units.conversionDict.setdefault('gram_per_meter_cubed',{})
weewx.units.conversionDict.setdefault('joule_per_cm_squared',{})
weewx.units.conversionDict.setdefault('joule_per_meter_squared',{})
weewx.units.conversionDict.setdefault('kilojoule_per_meter_squared',{})
weewx.units.conversionDict.setdefault('kilowatt_hour_per_meter_squared',{})
weewx.units.conversionDict.setdefault('microgram_per_meter_cubed',{})
weewx.units.conversionDict.setdefault('milligram_per_meter_cubed',{})
weewx.units.conversionDict.setdefault('watt_hour_per_meter_squared',{})
weewx.units.conversionDict.setdefault('watt_per_meter_squared',{})
weewx.units.conversionDict.setdefault('grains_per_meter_cubed',{})
#
weewx.units.conversionDict['gram_per_meter_cubed']['microgram_per_meter_cubed']              = lambda x : x * 1000000
weewx.units.conversionDict['gram_per_meter_cubed']['milligram_per_meter_cubed']              = lambda x : x * 1000
weewx.units.conversionDict['joule_per_cm_squared']['kilowatt_hour_per_meter_squared']        = lambda x : (x * 0.0001) / 3.6
weewx.units.conversionDict['joule_per_cm_squared']['watt_hour_per_meter_squared']            = lambda x : (x * 0.01) / 3.6
weewx.units.conversionDict['joule_per_meter_squared']['kilowatt_hour_per_meter_squared']     = lambda x : x * 0.00000027778
weewx.units.conversionDict['joule_per_meter_squared']['watt_hour_per_meter_squared']         = lambda x : x / 3600
weewx.units.conversionDict['kilowatt_hour_per_meter_squared']['watt_hour_per_meter_squared'] = lambda x : x * 1000.0
weewx.units.conversionDict['microgram_per_meter_cubed']['gram_per_meter_cubed']              = lambda x : x * 0.000001
weewx.units.conversionDict['microgram_per_meter_cubed']['milligram_per_meter_cubed']         = lambda x : x * 0.001
weewx.units.conversionDict['milligram_per_meter_cubed']['gram_per_meter_cubed']              = lambda x : x * 0.001
weewx.units.conversionDict['milligram_per_meter_cubed']['microgram_per_meter_cubed']         = lambda x : x * 1000
weewx.units.conversionDict['watt_hour_per_meter_squared']['kilowatt_hour_per_meter_squared'] = lambda x : x / 1000.0
weewx.units.conversionDict['watt_per_meter_squared']['joule_per_cm_squared']                 = lambda x : x * 1000000
#
# Ecowitt uvradiation
weewx.units.conversionDict.setdefault('microwatt_per_meter_squared',{})
weewx.units.conversionDict.setdefault('milliwatt_per_meter_squared',{})
weewx.units.conversionDict.setdefault('watt_per_meter_squared',{})
#
weewx.units.conversionDict['microwatt_per_meter_squared']['milliwatt_per_meter_squared'] = lambda x : x * 0.001
weewx.units.conversionDict['microwatt_per_meter_squared']['watt_per_meter_squared']      = lambda x : x * 0.000001
weewx.units.conversionDict['milliwatt_per_meter_squared']['microwatt_per_meter_squared'] = lambda x : x * 1000.0
weewx.units.conversionDict['milliwatt_per_meter_squared']['watt_per_meter_squared']      = lambda x : x * 0.001
weewx.units.conversionDict['watt_per_meter_squared']['microwatt_per_meter_squared']      = lambda x : x * 1000000.0
weewx.units.conversionDict['watt_per_meter_squared']['milliwatt_per_meter_squared']      = lambda x : x * 1000.0
#
# OPEN-METEO forecast endpoint, shortwave_radiation_sum (MJ/m²) The sum of solar radiation on a given day in Megajoules
weewx.units.conversionDict.setdefault('megajoule_per_meter_squared',{})
#
# TODO check this. source bard.google.com
weewx.units.conversionDict['megajoule_per_meter_squared']['watt_per_meter_squared'] = lambda x : x * 1000 / 3600
#
# Data memory / disk / network
weewx.units.conversionDict.setdefault('byte',{})
weewx.units.conversionDict.setdefault('kilobyte',{})
weewx.units.conversionDict.setdefault('megabyte',{})
weewx.units.conversionDict.setdefault('gigabyte',{})
weewx.units.conversionDict.setdefault('terabyte',{})
#
weewx.units.conversionDict['byte']['kilobyte']     = lambda x : x / 1024
weewx.units.conversionDict['byte']['megabyte']     = lambda x : x / (1024 * 1024)
weewx.units.conversionDict['byte']['gigabyte']     = lambda x : x / (1024 * 1024 * 1024)
weewx.units.conversionDict['byte']['terabyte']     = lambda x : x / (1024 * 1024 * 1024 * 1024)
weewx.units.conversionDict['kilobyte']['byte']     = lambda x : x * 1024,
weewx.units.conversionDict['kilobyte']['megabyte'] = lambda x : x / 1024
weewx.units.conversionDict['kilobyte']['gigabyte'] = lambda x : x / (1024 * 1024)
weewx.units.conversionDict['kilobyte']['terabyte'] = lambda x : x / (1024 * 1024 * 1024)
weewx.units.conversionDict['megabyte']['byte']     = lambda x : x * 1024 * 1024
weewx.units.conversionDict['megabyte']['kilobyte'] = lambda x : x * 1024
weewx.units.conversionDict['megabyte']['gigabyte'] = lambda x : x / 1024
weewx.units.conversionDict['megabyte']['terabyte'] = lambda x : x / (1024 * 1024)
weewx.units.conversionDict['gigabyte']['byte']     = lambda x : x * 1024 * 1024 *1024
weewx.units.conversionDict['gigabyte']['kilobyte'] = lambda x : x * 1024 * 1024
weewx.units.conversionDict['gigabyte']['megabyte'] = lambda x : x * 1024
weewx.units.conversionDict['gigabyte']['terabyte'] = lambda x : x / 1024
weewx.units.conversionDict['terabyte']['byte']     = lambda x : x * 1024 * 1024 * 1024 * 1024
weewx.units.conversionDict['terabyte']['kilobyte'] = lambda x : x * 1024 * 1024 * 1024
weewx.units.conversionDict['terabyte']['megabyte'] = lambda x : x * 1024 * 1024
weewx.units.conversionDict['terabyte']['gigabyte'] = lambda x : x * 1024
#
# aqi
weewx.units.conversionDict.setdefault('ppm',{})
weewx.units.conversionDict.setdefault('ppb',{})
weewx.units.conversionDict.setdefault('liter',{})
weewx.units.conversionDict.setdefault('meter_cubed',{})
#
weewx.units.conversionDict['liter']['meter_cubed'] = lambda x : x / 1000.0
weewx.units.conversionDict['meter_cubed']['liter'] = lambda x : x * 1000.0
weewx.units.conversionDict['ppb']['ppm']           = lambda x : x * 1000.0
weewx.units.conversionDict['ppm']['ppb']           = lambda x : x / 1000.0
#
# rain
weewx.units.conversionDict.setdefault('meter',{})
weewx.units.conversionDict.setdefault('cm',{})
weewx.units.conversionDict.setdefault('mm',{})
#
weewx.units.conversionDict['meter']['cm']   = lambda x : x * 100
weewx.units.conversionDict['meter']['mm']   = lambda x : x * 1000
weewx.units.conversionDict['cm']['mm']      = lambda x : x * 10
weewx.units.conversionDict['cm']['meter']   = lambda x : x * 0.01
weewx.units.conversionDict['mm']['meter']   = lambda x : x * 0.001