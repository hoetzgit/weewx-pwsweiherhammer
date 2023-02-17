#!/bin/bash

# Generiert die inc Seite für den "MQTT Monitor" Weiherhammer skin
# TODO: automatisch per jquery?

BROKER="${HOSTNAME}.fritz.box"
USER=""
PW=""
PORT=1883
QOS=1
CLIENTID="${HOSTNAME}-mqttmontopics-inc-generator"
MAINTOPIC="weewx-mqtt"
TOPICFILTER="-T weewx-mqtt/loop"
SUBSCRIBETIMEOUT=2

TMPDIR="/tmp"
TMPFILE="${TMPDIR}/${MAINTOPIC}.tmp"

PAGE="stationmon"
DESTDIR="/home/weewx/skins/Weiherhammer/${PAGE}"
DESTFILE="${DESTDIR}/mqttmontopics.inc"

ME="$(basename "${BASH_ARGV0}")"
DATETIME=$(date '+%d.%m.%Y %H:%M:%S')

#weewx-loopdata windrun_* topics
#windrun_bucket_suffixes: List[str] = [ 'N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
#                                       'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW' ]
WINDRUNTOPICS=(
"weewx-mqtt/windrun_N"
"weewx-mqtt/windrun_NNE"
"weewx-mqtt/windrun_NE"
"weewx-mqtt/windrun_ENE"
"weewx-mqtt/windrun_E"
"weewx-mqtt/windrun_ESE"
"weewx-mqtt/windrun_SE"
"weewx-mqtt/windrun_SSE"
"weewx-mqtt/windrun_S"
"weewx-mqtt/windrun_SSW"
"weewx-mqtt/windrun_SW"
"weewx-mqtt/windrun_WSW"
"weewx-mqtt/windrun_W"
"weewx-mqtt/windrun_WNW"
"weewx-mqtt/windrun_NW"
"weewx-mqtt/windrun_NNW"
)
# Erst windrun_* Topics filtern, da evtl. (noch) nicht im Broker
for WINDTOPIC in ${WINDRUNTOPICS[@]}
do
  TOPICFILTER="${TOPICFILTER} -T ${WINDTOPIC}"
done

if [[ ! -e ${DESTDIR} ]]; then
    mkdir -p ${DESTDIR}
fi

if [ -f "${TMPFILE}" ]; then
  rm -f "${TMPFILE}"
fi
echo "${TMPFILE}"

TMPDESTFILE="${TMPDIR}/${PAGE}.inc"
if [ -f "${TMPDESTFILE}" ]; then
  rm -f "${TMPDESTFILE}"
fi
echo "${TMPDESTFILE}"

mosquitto_sub -h ${BROKER} ${USER} ${PW} -i ${CLIENTID} -q ${QOS} -t ${MAINTOPIC}/# -F %t ${TOPICFILTER} -W ${SUBSCRIBETIMEOUT} >"${TMPFILE}"

#Die Liste nun mit allen windrun_* Topics erweitern
for WINDTOPIC in ${WINDRUNTOPICS[@]}
do
  printf "%s\n" ${WINDTOPIC} >>"${TMPFILE}"
done

cmd="sed -i 's/${MAINTOPIC}\///g' ${TMPFILE}"
bash -c "${cmd}"
sort -o "${TMPFILE}" "${TMPFILE}"
#uniq -u "${TMPFILE}" "${TMPFILE}"

# write inc file
# head
printf "\n" >>"${TMPDESTFILE}"
printf "            <!-- Generator: %s %s\n" "${ME}" "-->" >>"${TMPDESTFILE}"
printf "            <!-- generated: %s %s\n" "${DATETIME}" "-->" >>"${TMPDESTFILE}"
printf "\n\n" >>"${TMPDESTFILE}"

# write <tr></tr>
while IFS="=" read -r value
do
  printf "                <tr>\n" >>"${TMPDESTFILE}"
  printf '                    <th scope="row" class="mqttmon-table-body-obs"><div class="mqttmon-rcv-dot %s-mqttmon-rcv-dot" style="background-color: var(--mqttmon-rcv-dot-none);"></div><abbr rel="tooltip" title="$obs.label.%s">%s</abbr></th>\n' "${value}" "${value}" "${value}" >>"${TMPDESTFILE}"
  printf '                    <td class="mqttmon-table-body-obs-val"><span class="%s" rel="tooltip" title="">---</span></td>\n' "${value}" >>"${TMPDESTFILE}"
  printf "                </tr>\n" >>"${TMPDESTFILE}"
done < <(cat "${TMPFILE}")

rm -f "${TMPFILE}"

echo "${DESTFILE}"
mv "${TMPDESTFILE}" "${DESTFILE}"

exit 0
