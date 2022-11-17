#!/bin/bash

WEEWX_FILE="/mnt/Daten/weewx/allsky.txt"
WEEWX_ALLSKY_FILE="/mnt/Daten/weewx/allsky_weewx_data.txt"

echo $(cat /home/weewx/public_html/weiherhammer/json/forecast.json | jq -r '.current[].response.ob.weather') \
>${WEEWX_ALLSKY_FILE} \
&& cat ${WEEWX_FILE} >>${WEEWX_ALLSKY_FILE} \
#&& echo "Cloud cover: $(cat /home/weewx/public_html/weiherhammer/json/weewx_data.json | jq -r '.station_observations[].cloud_cover')" \
#>>/mnt/Daten/weewx/allsky2.txt \
#&& echo "Visibility: $(cat /home/weewx/public_html/weiherhammer/json/weewx_data.json | jq -r '.station_observations[].visibility')" \
#>>/mnt/Daten/weewx/allsky2.txt
