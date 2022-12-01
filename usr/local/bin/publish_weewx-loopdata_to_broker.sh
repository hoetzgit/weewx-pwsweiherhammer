#!/bin/bash
QOS=1
BROKER="mqtt.fritz.box"
PORT=1883
TOPIC="weewx_loopdata"
SOURCEFILE="/home/weewx/public_html/loopdata/loopdata.json"
RETAIN="-r"

# publish JSON file
subtopic="${TOPIC}/json"
/usr/bin/mosquitto_pub -h ${BROKER} -p ${PORT} -f "${SOURCEFILE}" -t "${subtopic}" -q ${QOS} ${RETAIN}

# publish JSON values
# https://stackoverflow.com/questions/25378013/how-to-convert-a-json-object-to-key-value-format-in-jq
# https://stackoverflow.com/questions/26717277/accessing-a-json-object-in-bash-associative-array-list-another-model
declare -A kvarray
while IFS="=" read -r key value
do
  kvarray[$key]="$value"
done < <(jq -r 'to_entries|map("\(.key)=\(.value|tostring)")|.[]' "${SOURCEFILE}")

for key in "${!kvarray[@]}"
do
  subtopic="${TOPIC}/${key}"
  message="${kvarray[$key]}"
  #echo "${subtopic} = ${message}"
  /usr/bin/mosquitto_pub -h ${BROKER} -p ${PORT} -m "${message}" -t "${subtopic}" -q ${QOS} ${RETAIN}
done

