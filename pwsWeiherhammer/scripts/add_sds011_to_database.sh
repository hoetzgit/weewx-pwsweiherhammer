#!/bin/bash
sudo echo "y" | /home/weewx/bin/wee_database --add-column=sds011_pm2_5 --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=sds011_pm10_0 --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=sds011_temperature --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=sds011_humidity --type=REAL
