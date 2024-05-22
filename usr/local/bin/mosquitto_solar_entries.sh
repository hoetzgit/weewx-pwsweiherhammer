#!/bin/bash
#sudo /bin/systemctl stop mosquitto && sudo rm /var/lib/mosquitto/mosquitto.db && sudo /bin/systemctl start mosquitto

MQTTSERVER="${HOSTNAME}.fritz.box"

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
    mosquitto_pub -h ${MQTTSERVER} -m "0" -t "${STATION}/${TOPIC}" -q 1 -r
  done
done

mosquitto_pub -h ${MQTTSERVER} -m "0" -t "${STATION}/correction/BME280_TEMPERATURE_OFFSET" -q 1 -r
mosquitto_pub -h ${MQTTSERVER} -m "0" -t "${STATION}/correction/BME280_PRESSURE_OFFSET" -q 1 -r
mosquitto_pub -h ${MQTTSERVER} -m "-2" -t "${STATION}/correction/BME280_BAROMETER_OFFSET" -q 1 -r
mosquitto_pub -h ${MQTTSERVER} -m "5" -t "${STATION}/correction/BME280_HUMIDITY_OFFSET" -q 1 -r
mosquitto_pub -h ${MQTTSERVER} -m "5" -t "${STATION}/correction/SLEEP_DAY_HOUR" -q 1 -r
mosquitto_pub -h ${MQTTSERVER} -m "22" -t "${STATION}/correction/SLEEP_NIGHT_HOUR" -q 1 -r
mosquitto_pub -h ${MQTTSERVER} -m "30" -t "${STATION}/correction/SLEEP_DAY_SECONDS" -q 1 -r
mosquitto_pub -h ${MQTTSERVER} -m "30" -t "${STATION}/correction/SLEEP_NIGHT_SECONDS" -q 1 -r
