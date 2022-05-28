sudo echo "y" | /home/weewx/bin/wee_database --add-column=uba_aqi --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=uba_aqi_category --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=uba_no2 --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=uba_no2_category --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=uba_o3 --type=REAL
sudo echo "y" | /home/weewx/bin/wee_database --add-column=uba_o3_category --type=REAL