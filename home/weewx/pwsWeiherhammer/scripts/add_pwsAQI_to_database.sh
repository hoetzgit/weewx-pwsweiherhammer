#!/bin/bash
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
