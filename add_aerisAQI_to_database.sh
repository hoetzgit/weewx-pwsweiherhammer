#!/bin/bash
sudo echo "y" | /home/weewx/bin/wee_database --add-column=aeris_aqi --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=aeris_co --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=aeris_no2 --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=aeris_o3 --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=aeris_pm2_5 --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=aeris_pm10_0 --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=aeris_so2 --type=REAL
