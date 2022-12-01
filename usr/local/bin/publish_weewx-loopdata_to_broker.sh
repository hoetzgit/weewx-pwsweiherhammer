#!/bin/bash
QOS=1
BROKER="mqtt.fritz.box"
PORT=1883
TOPIC="weewx_loopdata"
SOURCEFILE="/home/weewx/public_html/loopdata/loopdata.json"
RETAIN="-r"

if [ ! -f "$SOURCEFILE" ]; then
    echo "ERROR: weewx-loopata file [${SOURCEFILE}] does not exist! Abort." >&2
    exit 126 # Command invoked cannot execute
fi

# publish JSON file
subtopic="${TOPIC}/json"
/usr/bin/mosquitto_pub -h ${BROKER} -p ${PORT} -f "${SOURCEFILE}" -t "${subtopic}" -q ${QOS} ${RETAIN}
ret=$?
if [ ${ret} -ne 0 ] ; then
  echo "ERROR: mosquitto_pub, code=${ret}" >&2
  exit ${ret}
fi

# publish JSON values
# https://stackoverflow.com/questions/25378013/how-to-convert-a-json-object-to-key-value-format-in-jq
# https://stackoverflow.com/questions/26717277/accessing-a-json-object-in-bash-associative-array-list-another-model
while IFS="=" read -r key value
do
  subtopic="${TOPIC}/${key}"
  message="${value}"
  #echo "${subtopic} = ${message}"
  /usr/bin/mosquitto_pub -h ${BROKER} -p ${PORT} -m "${message}" -t "${subtopic}" -q ${QOS} ${RETAIN}
  ret=$?
  if [ ${ret} -ne 0 ] ; then
    echo "ERROR: mosquitto_pub, code=${ret}" >&2
    exit ${ret}
  fi
done < <(jq -r 'to_entries|map("\(.key)=\(.value|tostring)")|.[]' "${SOURCEFILE}")

exit 0