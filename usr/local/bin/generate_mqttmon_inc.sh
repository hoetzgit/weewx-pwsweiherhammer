#!/bin/bash

# Generiert die inc Seite für den "MQTT Monitor" Weiherhammer skin
# TODO: automatisch per jquery?

BROKER="${HOSTNAME}.fritz.box"
USER=""
PW=""
PORT=1883
QOS=1
CLIENTID="${HOSTNAME}-mqttmon-inc-generator"
MAINTOPIC="weewx-mqtt"
TOPICFILTER="-T weewx-mqtt/loop"
SUBSCRIBETIMEOUT=2

TMPDIR="/tmp"
TMPFILE="${TMPDIR}/${MAINTOPIC}.tmp"

PAGE="mqttmon"
INCDESTDIR="/home/weewx/skins/Weiherhammer/${PAGE}"
INCDESTFILE="${INCDESTDIR}/${PAGE}.inc"
CSSDESTDIR="/home/weewx/skins/Weiherhammer/css"
CSSDESTFILE="${CSSDESTDIR}/${PAGE}.css"

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

if [[ ! -e ${INCDESTDIR} ]]; then
    mkdir -p ${INCDESTDIR}
fi

if [[ ! -e ${CSSDESTDIR} ]]; then
    mkdir -p ${CSSDESTDIR}
fi

if [ -f "${TMPFILE}" ]; then
  rm -f "${TMPFILE}"
fi
echo "${TMPFILE}"

TMPINCDESTFILE="${TMPDIR}/${PAGE}.inc"
if [ -f "${TMPINCDESTFILE}" ]; then
  rm -f "${TMPINCDESTFILE}"
fi
echo "${TMPINCDESTFILE}"

TMPCSSDESTFILE="${TMPDIR}/${PAGE}.css"
if [ -f "${TMPCSSDESTFILE}" ]; then
  rm -f "${TMPCSSDESTFILE}"
fi
echo "${TMPCSSDESTFILE}"

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

# write css file
printf "/*\n" >>"${TMPCSSDESTFILE}"
printf "Generator: %s\n" "${ME}" >>"${TMPCSSDESTFILE}"
printf "generated: %s\n" "${DATETIME}" >>"${TMPCSSDESTFILE}"
printf "*/\n\n" >>"${TMPCSSDESTFILE}"
printf ":root {\n" >>"${TMPCSSDESTFILE}"
printf "  --mqttmon-rcv-none:#FF0000;\n" >>"${TMPCSSDESTFILE}"
printf "  --mqttmon-rcv:#00bb00;\n" >>"${TMPCSSDESTFILE}"
printf "  --mqttmon-rcv-outdated:#236d1b;\n" >>"${TMPCSSDESTFILE}"
printf "}\n\n" >>"${TMPCSSDESTFILE}"
printf ".mqttmon-rcv-none-dot {\n" >>"${TMPCSSDESTFILE}"
printf "  height: 8px;\n" >>"${TMPCSSDESTFILE}"
printf "  width: 8px;\n" >>"${TMPCSSDESTFILE}"
printf "  background-color: var(--mqttmon-rcv-none);\n" >>"${TMPCSSDESTFILE}"
printf "  border-radius: 50%s;\n" "%" >>"${TMPCSSDESTFILE}"
printf "  display: inline-block;\n" >>"${TMPCSSDESTFILE}"
printf "  margin-left: 5px;\n" >>"${TMPCSSDESTFILE}"
printf "  margin-right: 5px;\n" >>"${TMPCSSDESTFILE}"
printf "}\n\n" >>"${TMPCSSDESTFILE}"
printf ".mqttmon-rcv-dot {\n" >>"${TMPCSSDESTFILE}"
printf "  height: 8px;\n" >>"${TMPCSSDESTFILE}"
printf "  width: 8px;\n" >>"${TMPCSSDESTFILE}"
printf "  background-color: var(--mqttmon-rcv);\n" >>"${TMPCSSDESTFILE}"
printf "  border-radius: 50%s;\n" "%" >>"${TMPCSSDESTFILE}"
printf "  display: inline-block;\n" >>"${TMPCSSDESTFILE}"
printf "  margin-left: 10px;\n" >>"${TMPCSSDESTFILE}"
printf "  margin-right: 5px;\n" >>"${TMPCSSDESTFILE}"
printf "}\n\n" >>"${TMPCSSDESTFILE}"
printf ".mqttmon-rcv-outdated-dot {\n" >>"${TMPCSSDESTFILE}"
printf "  height: 8px;\n" >>"${TMPCSSDESTFILE}"
printf "  width: 8px;\n" >>"${TMPCSSDESTFILE}"
printf "  background-color: var(--mqttmon-rcv-outdated);\n" >>"${TMPCSSDESTFILE}"
printf "  border-radius: 50%s;\n" "%" >>"${TMPCSSDESTFILE}"
printf "  display: inline-block;\n" >>"${TMPCSSDESTFILE}"
printf "  margin-left: 5px;\n" >>"${TMPCSSDESTFILE}"
printf "  margin-right: 5px;\n" >>"${TMPCSSDESTFILE}"
printf "}\n\n" >>"${TMPCSSDESTFILE}"

# write inc file
printf "    <!-- Generator: %s %s\n" "${ME}" "-->" >>"${TMPINCDESTFILE}"
printf "    <!-- generated: %s %s\n" "${DATETIME}" "-->" >>"${TMPINCDESTFILE}"

while IFS="=" read -r value
do
  # write css file
  printf ".%s-mqttmon-rcv-dot {\n" "${value}" >>"${TMPCSSDESTFILE}"
  printf "  height: 8px;\n" >>"${TMPCSSDESTFILE}"
  printf "  width: 8px;\n" >>"${TMPCSSDESTFILE}"
  printf "  background-color: var(--mqttmon-rcv-none);\n" >>"${TMPCSSDESTFILE}"
  printf "  border-radius: 50%s;\n" "%" >>"${TMPCSSDESTFILE}"
  printf "  display: inline-block;\n" >>"${TMPCSSDESTFILE}"
  printf "  margin-right: 5px;\n" >>"${TMPCSSDESTFILE}"
  printf "}\n\n" >>"${TMPCSSDESTFILE}"

  # write inc file
  printf "    <tr>\n" >>"${TMPINCDESTFILE}"
  printf '        <th scope="row" class="mqttmon-table-body-obs"><div class="%s-mqttmon-rcv-dot"></div><abbr rel="tooltip" title="$obs.label.%s">%s</abbr></th>\n' "${value}" "${value}" "${value}" >>"${TMPINCDESTFILE}"
  printf '        <td class="mqttmon-table-body-obs-val"><span class="%s" rel="tooltip" title="">---</span></td>\n' "${value}" >>"${TMPINCDESTFILE}"
  printf "    </tr>\n" >>"${TMPINCDESTFILE}"
done < <(cat "${TMPFILE}")

rm -f "${TMPFILE}"

echo "${CSSDESTFILE}"
mv "${TMPCSSDESTFILE}" "${CSSDESTFILE}"

echo "${INCDESTFILE}"
mv "${TMPINCDESTFILE}" "${INCDESTFILE}"

exit 0
