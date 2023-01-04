#
#    Copyright (c) 2009-2020 Tom Keffer <tkeffer@gmail.com>
#
#    See the file LICENSE.txt for your rights.
#
"""The extended wview PWS Weiherhammer schema."""

# =============================================================================
# This is a list containing the default schema of the archive database.  It is
# only used for initialization --- afterwards, the schema is obtained
# dynamically from the database.  Although a type may be listed here, it may
# not necessarily be supported by your weather station hardware.
# =============================================================================
# NB: This schema is specified using the WeeWX V4 "new-style" schema.
# =============================================================================
table = [('dateTime',             'INTEGER NOT NULL UNIQUE PRIMARY KEY'),
         ('usUnits',              'INTEGER NOT NULL'),
         ('interval',             'INTEGER NOT NULL'),
         ('altimeter',            'REAL'),
         ('appTemp',              'REAL'),
         ('appTemp1',             'REAL'),
         ('barometer',            'REAL'),
         ('batteryStatus1',       'REAL'),
         ('batteryStatus2',       'REAL'),
         ('batteryStatus3',       'REAL'),
         ('batteryStatus4',       'REAL'),
         ('batteryStatus5',       'REAL'),
         ('batteryStatus6',       'REAL'),
         ('batteryStatus7',       'REAL'),
         ('batteryStatus8',       'REAL'),
         ('cloudbase',            'REAL'),
         ('co',                   'REAL'),
         ('co2',                  'REAL'),
         ('consBatteryVoltage',   'REAL'),
         ('dewpoint',             'REAL'),
         ('dewpoint1',            'REAL'),
         ('ET',                   'REAL'),
         ('extraHumid1',          'REAL'),
         ('extraHumid2',          'REAL'),
         ('extraHumid3',          'REAL'),
         ('extraHumid4',          'REAL'),
         ('extraHumid5',          'REAL'),
         ('extraHumid6',          'REAL'),
         ('extraHumid7',          'REAL'),
         ('extraHumid8',          'REAL'),
         ('extraTemp1',           'REAL'),
         ('extraTemp2',           'REAL'),
         ('extraTemp3',           'REAL'),
         ('extraTemp4',           'REAL'),
         ('extraTemp5',           'REAL'),
         ('extraTemp6',           'REAL'),
         ('extraTemp7',           'REAL'),
         ('extraTemp8',           'REAL'),
         ('forecast',             'REAL'),
         ('hail',                 'REAL'),
         ('hailBatteryStatus',    'REAL'),
         ('hailRate',             'REAL'),
         ('heatindex',            'REAL'),
         ('heatindex1',           'REAL'),
         ('heatingTemp',          'REAL'),
         ('heatingVoltage',       'REAL'),
         ('humidex',              'REAL'),
         ('humidex1',             'REAL'),
         ('inDewpoint',           'REAL'),
         ('inHumidity',           'REAL'),
         ('inTemp',               'REAL'),
         ('inTempBatteryStatus',  'REAL'),
         ('leafTemp1',            'REAL'),
         ('leafTemp2',            'REAL'),
         ('leafWet1',             'REAL'),
         ('leafWet2',             'REAL'),
         ('lightning_distance',   'REAL'),
         ('lightning_disturber_count', 'REAL'),
         ('lightning_energy',          'REAL'),
         ('lightning_noise_count',     'REAL'),
         ('lightning_strike_count',    'REAL'),
         ('luminosity',           'REAL'),
         ('maxSolarRad',          'REAL'),
         ('nh3',                  'REAL'),
         ('no2',                  'REAL'),
         ('noise',                'REAL'),
         ('o3',                   'REAL'),
         ('outHumidity',          'REAL'),
         ('outTemp',              'REAL'),
         ('outTempBatteryStatus', 'REAL'),
         ('pb',                   'REAL'),
         ('pm10_0',               'REAL'),
         ('pm1_0',                'REAL'),
         ('pm2_5',                'REAL'),
         ('pressure',             'REAL'),
         ('radiation',            'REAL'),
         ('rain',                 'REAL'),
         ('rainBatteryStatus',    'REAL'),
         ('rainRate',             'REAL'),
         ('referenceVoltage',     'REAL'),
         ('rxCheckPercent',       'REAL'),
         ('signal1',              'REAL'),
         ('signal2',              'REAL'),
         ('signal3',              'REAL'),
         ('signal4',              'REAL'),
         ('signal5',              'REAL'),
         ('signal6',              'REAL'),
         ('signal7',              'REAL'),
         ('signal8',              'REAL'),
         ('snow',                 'REAL'),
         ('snowBatteryStatus',    'REAL'),
         ('snowDepth',            'REAL'),
         ('snowMoisture',         'REAL'),
         ('snowRate',             'REAL'),
         ('so2',                  'REAL'),
         ('soilMoist1',           'REAL'),
         ('soilMoist2',           'REAL'),
         ('soilMoist3',           'REAL'),
         ('soilMoist4',           'REAL'),
         ('soilTemp1',            'REAL'),
         ('soilTemp2',            'REAL'),
         ('soilTemp3',            'REAL'),
         ('soilTemp4',            'REAL'),
         ('supplyVoltage',        'REAL'),
         ('txBatteryStatus',      'REAL'),
         ('UV',                   'REAL'),
         ('uvBatteryStatus',      'REAL'),
         ('windBatteryStatus',    'REAL'),
         ('windchill',            'REAL'),
         ('windDir',              'REAL'),
         ('windGust',             'REAL'),
         ('windGustDir',          'REAL'),
         ('windrun',              'REAL'),
         ('windSpeed',            'REAL'),
#
# Allsky 01 Kamera (BME280 und DS18B20)
('asky_dome_temperature', 'REAL'),
('asky_dome_dewpoint', 'REAL'),
('asky_dome_heater', 'INTEGER'),
('asky_box_temperature', 'REAL'),
('asky_box_dewpoint', 'REAL'),
('asky_box_humidity', 'REAL'),
('asky_box_pressure', 'REAL'),
('asky_box_altimeter', 'REAL'),
('asky_box_barometer', 'REAL'),
('asky_box_fan', 'INTEGER'),
('asky_cpu_fan', 'INTEGER'),
('asky_cpu_temperature', 'REAL'),
#
# FOSHKplugin added obervations
('foshk_cloudbase', 'REAL'),
('foshk_dewpoint', 'REAL'),
('foshk_feelslike', 'REAL'),
('foshk_heatindex', 'REAL'),
('foshk_sunhours', 'REAL'),
('foshk_windchill', 'REAL'),
('foshk_winddir_avg10m', 'REAL'),
('foshk_windgust_max10m', 'REAL'),
('foshk_windspeed_avg10m', 'REAL'),
#
# Ecowitt GW1100 Sainlogic WS3500 WH65
('dayRain', 'REAL'),
('gainRain', 'REAL'),
('hourRain', 'REAL'),
('monthRain', 'REAL'),
('stormRain', 'REAL'),
('totalRain', 'REAL'),
('weekRain', 'REAL'),
('yearRain', 'REAL'),
('daymaxwind', 'REAL'),
('uvradiation', 'REAL'),
('wh65_batt', 'REAL'),
('wh65_sig', 'REAL'),
#
# Ecowitt WH31
('wh31_ch1_batt', 'REAL'),
('wh31_ch2_batt', 'REAL'),
('wh31_ch3_batt', 'REAL'),
('wh31_ch1_sig', 'REAL'),
('wh31_ch2_sig', 'REAL'),
('wh31_ch3_sig', 'REAL'),
#
# Ecowitt Bodenfeuchte WH51
('wh51_ch1_batt', 'REAL'),
('wh51_ch1_sig', 'REAL'),
#
# Ecowitt Blitzsensor WH57
('wh57_batt', 'REAL'),
('wh57_sig', 'REAL'),
('wh57_lightning_time', 'REAL'),
('wh57_lightning_distance', 'REAL'),
#
# Solar Station (BME280)
('solar_altimeter', 'REAL'),
('solar_appTemp', 'REAL'),
('solar_barometer', 'REAL'),
('solar_dewpoint', 'REAL'),
('solar_heatindex', 'REAL'),
('solar_humidex', 'REAL'),
('solar_humidity', 'REAL'),
('solar_pressure', 'REAL'),
('solar_temperature', 'REAL'),
('solar_thswIndex', 'REAL'),
('solar_thwIndex', 'REAL'),
('solar_voltage', 'REAL'),
('solar_wetBulb', 'REAL'),
('solar_windchill', 'REAL'),
#
# Nova PM Sensor SDS011
('sds011_pm2_5', 'REAL'),
('sds011_pm10_0', 'REAL'),
('sds011_temperature', 'REAL'),
('sds011_humidity', 'REAL'),
#
# ****** API / Extensions ******
#
# PWS Weiherhammer AQI
('pws_aqi', 'REAL'),
('pws_aqi_category', 'REAL'),
('pws_aqi_no2', 'REAL'),
('pws_aqi_no2_category', 'REAL'),
('pws_aqi_o3', 'REAL'),
('pws_aqi_o3_category', 'REAL'),
('pws_aqi_pm10_0', 'REAL'),
('pws_aqi_pm10_0_category', 'REAL'),
('pws_aqi_pm2_5', 'REAL'),
('pws_aqi_pm2_5_category', 'REAL'),
#
# OpenWeatherMap Air Pollution API
('owm_aqi', 'REAL'),
('owm_co', 'REAL'),
('owm_nh3', 'REAL'),
('owm_no', 'REAL'),
('owm_no2', 'REAL'),
('owm_o3', 'REAL'),
('owm_pm10_0', 'REAL'),
('owm_pm2_5', 'REAL'),
('owm_so2', 'REAL'),
#
# AerisWeatherMap Airquality API
('aeris_aqi', 'REAL'),
('aeris_co', 'REAL'),
('aeris_no2', 'REAL'),
('aeris_o3', 'REAL'),
('aeris_pm10_0', 'REAL'),
('aeris_pm2_5', 'REAL'),
('aeris_so2', 'REAL'),
#
# Umweltbundesamt API
('uba_aqi', 'REAL'),
('uba_aqi_category', 'REAL'),
('uba_no2', 'REAL'),
('uba_no2_category', 'REAL'),
('uba_o3', 'REAL'),
('uba_o3_category', 'REAL'),
#
# additional Values 
('outEquiTemp', 'REAL'),
('outHumAbs', 'REAL'),
('sunshine', 'REAL'),
('sunshineDur', 'REAL'),
('thswIndex', 'REAL'),
('thwIndex', 'REAL'),
('wetBulb', 'REAL'),
]

day_summaries = [(e[0], 'scalar') for e in table
                 if e[0] not in ('dateTime', 'usUnits', 'interval'
                   ,'asky_box_fan', 'asky_dome_heater', 'asky_cpu_fan'
                   ,'aeris_aqi', 'owm_aqi'
                   ,'pws_aqi', 'pws_aqi_category', 'pws_aqi_no2_category', 'pws_aqi_o3_category', 'pws_aqi_pm10_0_category', 'pws_aqi_pm2_5_category'
                   ,'uba_aqi', 'uba_aqi_category', 'uba_no2_category', 'uba_o3_category'
                   ,'sunshine'
                   )] + [('wind', 'VECTOR')]

schema = {
    'table': table,
    'day_summaries' : day_summaries
}


