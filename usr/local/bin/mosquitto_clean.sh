#!/bin/bash
sudo /bin/systemctl stop mosquitto && sudo rm /var/lib/mosquitto/mosquitto.db && sudo /bin/systemctl start mosquitto

STATIONS_TO_PUBLISH=(
"solar"
)

TOPICS_TO_PUBLISH=(
"action/bufferclean"
"action/configclean"
"action/ota"
"action/reboot"
"action/stop_publish_buffer"
"action/stop_publish_debug"
"action/stop_publish_error"
"action/stop_publish_sensor"
"action/stop_publish_weewx"
)

for STATION in ${STATIONS_TO_PUBLISH[@]}
do
  for TOPIC in ${TOPICS_TO_PUBLISH[@]}
  do
    mosquitto_pub -h weewx.fritz.box -m "0" -t "${STATION}/${TOPIC}" -q 1 -r
  done
done
