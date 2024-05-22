#!/bin/bash

# Generiert die inc Seite für alle WeeWX Topics für den "MQTT Monitor" Weiherhammer skin

BROKER="${HOSTNAME}.fritz.box"
#BROKER="mqtt01.fritz.box"
USER=""
PW=""
PORT=1883
QOS=1
CLIENTID="${HOSTNAME}-topics-currentwx-inc-generator"
MAINTOPIC="currentwx/result"
TOPICFILTER="-T ${MAINTOPIC}/loop"
SUBSCRIBETIMEOUT=2

PAGE="stationmon"
DESTDIR="/home/weewx/skins/Weiherhammer/${PAGE}"
DESTFILENAME="topics_currentwx.inc"
DESTFILE="${DESTDIR}/${DESTFILENAME}"

TMPDIR="/tmp"
TMPFILE="${TMPDIR}/${DESTFILENAME}.tmp"
TMPFILE2="${TMPDIR}/${DESTFILENAME}_2.tmp"

ME="$(basename "${BASH_ARGV0}")"
DATETIME=$(date '+%d.%m.%Y %H:%M:%S')

FTOPICS=(
"dateTime"
"dateTimeISO"
"generatedMin"
"generatedMinISO"
"generatedMax"
"generatedMaxISO"
"published"
"publishedISO"
"usUnits"
)
for FTOPIC in ${FTOPICS[@]}
do
  TOPICFILTER="${TOPICFILTER} -T ${MAINTOPIC}/${FTOPIC}"
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

MAINTOPIC="currentwx\/result"
cmd="sed -i 's/${MAINTOPIC}\///g' ${TMPFILE}"
bash -c "${cmd}"
#sort -o "${TMPFILE}" "${TMPFILE}"
grep -v '^$' "${TMPFILE}" | sort | uniq | grep -v '^$' > "${TMPFILE2}"

for FTOPIC in ${FTOPICS[@]}
do
  printf "%s\n" ${FTOPIC} >>"${TMPFILE2}"
done

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
