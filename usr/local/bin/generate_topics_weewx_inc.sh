#!/bin/bash

# Generiert die inc Seite für alle WeeWX Topics für den "MQTT Monitor" Weiherhammer skin

BROKER="${HOSTNAME}.fritz.box"
#BROKER="mqtt01.fritz.box"
USER=""
PW=""
PORT=1883
QOS=1
CLIENTID="${HOSTNAME}-topics-weewx-inc-generator"
MAINTOPIC="weewx-mqtt"
TOPICFILTER="-T ${MAINTOPIC}/loop"
SUBSCRIBETIMEOUT=2

TMPDIR="/tmp"
TMPFILE="${TMPDIR}/${MAINTOPIC}.tmp"
TMPFILE2="${TMPDIR}/${MAINTOPIC}_2.tmp"

PAGE="stationmon"
DESTDIR="/home/weewx/skins/Weiherhammer/${PAGE}"
DESTFILE="${DESTDIR}/topics_weewx.inc"

ME="$(basename "${BASH_ARGV0}")"
DATETIME=$(date '+%d.%m.%Y %H:%M:%S')

#weewx-loopdata windrun_* topics
#windrun_bucket_suffixes: List[str] = [ 'N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
#                                       'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW' ]
WINDRUNTOPICS=(
"windrun_N"
"windrun_NNE"
"windrun_NE"
"windrun_ENE"
"windrun_E"
"windrun_ESE"
"windrun_SE"
"windrun_SSE"
"windrun_S"
"windrun_SSW"
"windrun_SW"
"windrun_WSW"
"windrun_W"
"windrun_WNW"
"windrun_NW"
"windrun_NNW"
)
# Erst windrun_* Topics filtern, da evtl. (noch) nicht im Broker
for WINDTOPIC in ${WINDRUNTOPICS[@]}
do
  TOPICFILTER="${TOPICFILTER} -T ${MAINTOPIC}/${WINDTOPIC}"
done

TMPMTOPICS=(
"cloudwatcher_cloudpercent_avg02m"
"cloudwatcher_cloudpercent_avg05m"
"lightning_strike_count_sum02m"
"lightning_strike_count_sum05m"
"rain_sum02m"
"rain_sum05m"
"sunshine_avg02m"
"sunshine_avg05m"
)

MTOPICS=(
"cloudwatcher_cloudpercent_avg2m"
"cloudwatcher_cloudpercent_avg5m"
"lightning_strike_count_sum2m"
"lightning_strike_count_sum5m"
"rain_sum2m"
"rain_sum5m"
"sunshine_avg2m"
"sunshine_avg5m"
)
for MTOPIC in ${MTOPICS[@]}
do
  TOPICFILTER="${TOPICFILTER} -T ${MAINTOPIC}/${MTOPIC}"
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

for TMPMTOPIC in ${TMPMTOPICS[@]}
do
  printf "%s\n" ${TMPMTOPIC} >>"${TMPFILE}"
done

cmd="sed -i 's/${MAINTOPIC}\///g' ${TMPFILE}"
bash -c "${cmd}"
grep -v '^$' "${TMPFILE}" | sort | uniq | grep -v '^$' > "${TMPFILE2}"
cmd="sed -i 's/02m/2m/g' ${TMPFILE2}"
bash -c "${cmd}"
cmd="sed -i 's/05m/5m/g' ${TMPFILE2}"
bash -c "${cmd}"

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
done < <(cat "${TMPFILE2}")

rm -f "${TMPFILE}"
rm -f "${TMPFILE2}"

echo "${DESTFILE}"
mv "${TMPDESTFILE}" "${DESTFILE}"

exit 0
