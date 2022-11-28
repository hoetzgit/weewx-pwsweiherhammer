#!/bin/bash

#SDS011
sudo echo "y" | /home/weewx/bin/wee_database --add-column=sds011_pm2_5 --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=sds011_pm10_0 --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=sds011_temperature --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=sds011_humidity --type=REAL

#Aeris AQI
sudo echo "y" | /home/weewx/bin/wee_database --add-column=aeris_aqi --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=aeris_co --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=aeris_no2 --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=aeris_o3 --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=aeris_pm2_5 --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=aeris_pm10_0 --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=aeris_so2 --type=REAL

#UBA AQI
sudo echo "y" | /home/weewx/bin/wee_database --add-column=uba_aqi --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=uba_aqi_category --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=uba_no2 --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=uba_no2_category --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=uba_o3 --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=uba_o3_category --type=REAL

#PWS AQI
sudo echo "y" | /home/weewx/bin/wee_database --add-column=pws_aqi --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=pws_aqi_category --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=pws_aqi_no2 --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=pws_aqi_no2_category --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=pws_aqi_o3 --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=pws_aqi_o3_category --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=pws_aqi_pm10_0 --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=pws_aqi_pm10_0_category --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=pws_aqi_pm2_5 --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=pws_aqi_pm2_5_category --type=REAL

#sudo echo "y" | /home/weewx/bin/wee_database --add-column=wetBulb --type=REAL
#sudo echo "y" | /home/weewx/bin/wee_database --add-column=solar_humidex --type=REAL
#sudo echo "y" | /home/weewx/bin/wee_database --add-column=solar_wetBulb --type=REAL
#sudo echo "y" | /home/weewx/bin/wee_database --add-column=solar_windchill --type=REAL
#sudo echo "y" | /home/weewx/bin/wee_database --add-column=solar_appTemp --type=REAL
#sudo echo "y" | /home/weewx/bin/wee_database --add-column=asky_cpu_fan --type=INTEGER
#sudo echo "y" | /home/weewx/bin/wee_database --add-column=airDensity --type=REAL
#sudo echo "y" | /home/weewx/bin/wee_database --add-column=thwIndex --type=REAL
#sudo echo "y" | /home/weewx/bin/wee_database --add-column=thswIndex --type=REAL
#sudo echo "y" | /home/weewx/bin/wee_database --add-column=vaporPressure --type=REAL
#sudo echo "y" | /home/weewx/bin/wee_database --add-column=windPressure --type=REAL
#sudo echo "y" | /home/weewx/bin/wee_database --add-column=sunshineDur --type=REAL
#sudo echo "y" | /home/weewx/bin/wee_database --add-column=lightning --type=REAL
#sudo echo "y" | /home/weewx/bin/wee_database --add-column=outEquiTemp --type=REAL
#sudo echo "y" | /home/weewx/bin/wee_database --add-column=outHumAbs --type=REAL
#sudo echo "y" | /home/weewx/bin/wee_database --add-column=gw1100_rain_total --type=REAL
#
#TEST
#sudo echo "y" | /home/weewx/bin/wee_database --add-column=sunshineDur1 --type=REAL
#sudo echo "y" | /home/weewx/bin/wee_database --add-column=sunshineDur2 --type=REAL
#sudo echo "y" | /home/weewx/bin/wee_database --add-column=sunshineDur3 --type=REAL
#sudo echo "y" | /home/weewx/bin/wee_database --add-column=sunshineDur4 --type=REAL
#sudo echo "y" | /home/weewx/bin/wee_database --add-column=sunshineDur5 --type=REAL
#sudo echo "y" | /home/weewx/bin/wee_database --add-column=sunshineDur6 --type=REAL
#sudo echo "y" | /home/weewx/bin/wee_database --add-column=sunshineDur7 --type=REAL
#sudo echo "y" | /home/weewx/bin/wee_database --add-column=sunshineDur8 --type=REAL
