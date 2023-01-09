#!/bin/bash
BROKER="${HOSTNAME}.fritz.box"
USER=""
PW=""
PORT=1883
QOS=1
CLIENTID="${HOSTNAME}-weewx-mqtt-inc-generator"
TOPIC="weewx-mqtt"

TMPDIR="/tmp"
TMPFILE="${TMPDIR}/${TOPIC}.tmp"
INCDESTDIR="/home/weewx/skins/Weiherhammer/mqtt"
CSSDESTDIR="/home/weewx/skins/Weiherhammer/css"

ME="$(basename "${BASH_ARGV0}")"
DATETIME=$(date '+%d.%m.%Y %H:%M:%S')

if [ -f "${TMPFILE}" ]; then
  rm -f "${TMPFILE}"
fi
echo "${TMPFILE}"

TMPINCDESTFILE="${TMPDIR}/${TOPIC}.inc"
if [ -f "${TMPINCDESTFILE}" ]; then
  rm -f "${TMPINCDESTFILE}"
fi
echo "${TMPINCDESTFILE}"

TMPCSSDESTFILE="${TMPDIR}/${TOPIC}.css"
if [ -f "${TMPCSSDESTFILE}" ]; then
  rm -f "${TMPCSSDESTFILE}"
fi
echo "${TMPCSSDESTFILE}"

mosquitto_sub -h ${BROKER} ${USER} ${PW} -i ${CLIENTID} -q ${QOS} -t ${TOPIC}/# -F %t -T weewx-mqtt/loop -W 1 >"${TMPFILE}"
cmd="sed -i 's/${TOPIC}\///g' ${TMPFILE}"
bash -c "${cmd}"
sort -o "${TMPFILE}" "${TMPFILE}"

# write css file
printf "/*\n" >>"${TMPCSSDESTFILE}"
printf "Generator: %s\n" "${ME}" >>"${TMPCSSDESTFILE}"
printf "generated: %s\n" "${DATETIME}" >>"${TMPCSSDESTFILE}"
printf "*/\n\n" >>"${TMPCSSDESTFILE}"
printf ":root {\n" >>"${TMPCSSDESTFILE}"
printf "  --mqtt-rec-none:#FF0000;\n" >>"${TMPCSSDESTFILE}"
printf "  --mqtt-rec:#00bb00;\n" >>"${TMPCSSDESTFILE}"
printf "  --mqtt-rec-outdated:#236d1b;\n" >>"${TMPCSSDESTFILE}"
printf "}\n\n" >>"${TMPCSSDESTFILE}"

# write inc file
printf "                                        <!-- Generator: %s %s\n" "${ME}" "-->" >>"${TMPINCDESTFILE}"
printf "                                        <!-- generated: %s %s\n" "${DATETIME}" "-->" >>"${TMPINCDESTFILE}"

while IFS="=" read -r value
do
  # write css file
  printf ".%s-mqtt-rec-dot {\n" "${value}" >>"${TMPCSSDESTFILE}"
  printf "  height: 8px;\n" >>"${TMPCSSDESTFILE}"
  printf "  width: 8px;\n" >>"${TMPCSSDESTFILE}"
  printf "  background-color: var(--mqtt-rec-none);\n" >>"${TMPCSSDESTFILE}"
  printf "  border-radius: 50%s;\n" "%" >>"${TMPCSSDESTFILE}"
  printf "  display: inline-block;\n" >>"${TMPCSSDESTFILE}"
  printf "  margin-right: 5px;\n" >>"${TMPCSSDESTFILE}"
  printf "}\n\n" >>"${TMPCSSDESTFILE}"

  # write inc file
  printf "                                        <tr>\n" >>"${TMPINCDESTFILE}"
  printf '                                            <th scope="row" class="mqtt-table-body-obs"><div class="%s-mqtt-rec-dot"></div><abbr rel="tooltip" title="Label: $obs.label.%s">%s</abbr></th>\n' "${value}" "${value}" "${value}" >>"${TMPINCDESTFILE}"
  printf '                                            <td class="mqtt-table-body-obs-val"><span class="%s" data-mqttrec="0">---</span></td><!-- AJAX -->\n' "${value}" >>"${TMPINCDESTFILE}"
  printf "                                        </tr>\n" >>"${TMPINCDESTFILE}"
done < <(cat "${TMPFILE}")

rm -f "${TMPFILE}"

CSSDESTFILE="${CSSDESTDIR}/${TOPIC}.css"
echo "${CSSDESTFILE}"
mv "${TMPCSSDESTFILE}" "${CSSDESTFILE}"

INCDESTFILE="${INCDESTDIR}/${TOPIC}.inc"
echo "${INCDESTFILE}"
mv "${TMPINCDESTFILE}" "${INCDESTFILE}"

exit 0
