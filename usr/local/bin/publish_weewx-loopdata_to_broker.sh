#!/bin/bash
QOS=1
BROKER="${HOSTNAME}.fritz.box"
USER=""
PW=""
PORT=1883
TOPIC="weewx-loopdata"
SOURCEFILE="/home/weewx/public_html/loopdata/loopdata.json"
RETAIN="-r"
CLIENTID="${HOSTNAME}-weewx-loopdata-publisher"

if [ ! -f "$SOURCEFILE" ]; then
    echo "ERROR: weewx-loopata file [${SOURCEFILE}] does not exist! Abort." >&2
    exit 126 # Command invoked cannot execute
fi

# publish mod date
subtopic="${TOPIC}/dateTime"
# time of last data modification, seconds since Epoch
message="$(/usr/bin/stat -c %Y ${SOURCEFILE})"
/usr/bin/mosquitto_pub -h ${BROKER} ${USER} ${PW} -p ${PORT} -m "${message}" -t "${subtopic}" -i ${CLIENTID} -q ${QOS} ${RETAIN}
ret=$?
if [ ${ret} -ne 0 ] ; then
  echo "ERROR: mosquitto_pub, code=${ret}" >&2
  exit ${ret}
fi
subtopic="${TOPIC}/dateTimeHuman"
# time of last data modification, human-readable
message="$(/usr/bin/stat -c %y ${SOURCEFILE})"
/usr/bin/mosquitto_pub -h ${BROKER} ${USER} ${PW} -p ${PORT} -m "${message}" -t "${subtopic}" -i ${CLIENTID} -q ${QOS} ${RETAIN}
ret=$?
if [ ${ret} -ne 0 ] ; then
  echo "ERROR: mosquitto_pub, code=${ret}" >&2
  exit ${ret}
fi

# publish JSON file
subtopic="${TOPIC}/loop"
/usr/bin/mosquitto_pub -h ${BROKER} ${USER} ${PW} -p ${PORT} -f "${SOURCEFILE}" -t "${subtopic}" -i ${CLIENTID} -q ${QOS} ${RETAIN}
ret=$?
if [ ${ret} -ne 0 ] ; then
  echo "ERROR: mosquitto_pub, code=${ret}" >&2
  exit ${ret}
fi

# publish JSON values
# https://stackoverflow.com/questions/25378013/how-to-convert-a-json-object-to-key-value-format-in-jq
# https://stackoverflow.com/questions/26717277/accessing-a-json-object-in-bash-associative-array-list-another-model
#while IFS="=" read -r key value
#do
#  subtopic="${TOPIC}/${key}"
#  message="${value}"
#  #echo "${subtopic} = ${message}"
#  /usr/bin/mosquitto_pub -h ${BROKER} ${USER} ${PW} -p ${PORT} -m "${message}" -t "${subtopic}" -i ${CLIENTID} -q ${QOS} ${RETAIN}
#  ret=$?
#  if [ ${ret} -ne 0 ] ; then
#    echo "ERROR: mosquitto_pub, code=${ret}" >&2
#    exit ${ret}
#  fi
#done < <(jq -r 'to_entries|map("\(.key)=\(.value|tostring)")|.[]' "${SOURCEFILE}")

exit 0
