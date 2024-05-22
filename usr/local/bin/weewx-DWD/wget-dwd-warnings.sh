#!/bin/bash
# Herunterladen von Dateien beim Deutschen Wetterdienst
# Copyright (C) 2021 Johanna Roedenbeck
# licensed under the terms of the General Public License (GPL) v3
#
# 21.10.2022 Henry Ott
#            etwas Formatierung der DWD Vorhersage VHDL50*/VHDL54*
# 17.10.2022 Henry Ott
#            mehrere Ausgabepfade

# vom Benutzer anzupassen

# URLs der herunterzuladenden Dateien beim DWD
# (muss ggf. an das eigene Bundesland angepasst werden)
DWD_URL="https://opendata.dwd.de/weather/text_forecasts/html"
DWD_BUNDESLAND="DWMG"
DWD_MAP="https://www.dwd.de/DWD/wetter/wv_spez/hobbymet/wetterkarten/bwk_bodendruck_na_ana.png"
DWD_MAP2="https://www.dwd.de/DWD/wetter/wv_spez/hobbymet/wetterkarten/bwk_bodendruck_weu_ana.png"
DWD_WARN="https://www.dwd.de/DWD/warnungen/warnstatus/SchilderMS.jpg"
DWD_WARNJ="https://www.dwd.de/DWD/warnungen/warnapp/json/warnings.json"

# Log-Datei
LOG_FN="/var/log/weewx/wget-dwd.log"

# Zielpfad(e) zum Speichern der Dateien
# (Das Verzeichnis muss vorher vom Benutzer angelegt werden.)
# PTH="/etc/weewx/skins/Belchertown/dwd"
EXPORTS=(
"/home/weewx/skins/Weiherhammer/dwd"
"/home/weewx/skins/weewx-wdc/dwd"
"/home/weewx/public_html/data/dwd"
)

# Ende des vom Benutzer anzupassenden Bereichs

# Programm zum Herunterladen
WGET="/usr/bin/wget -a ${LOG_FN}"
TOUCH="/usr/bin/touch -r"
MV="/usr/bin/mv -vf"
CP="/usr/bin/cp -vf"
RM="/usr/bin/rm -vf"
TMP="/tmp/wget-dwd.tmp"
TMP2="/tmp/wget-dwd2.tmp"
HTML2ENT="/usr/local/bin/weewx-DWD/html2ent.ansi"
UML2DUMMY="/usr/local/bin/weewx-DWD/uml2dummy.ansi"
DUMMY2UML="/usr/local/bin/weewx-DWD/dummy2uml.ansi"

# Logdatei loeschen
/bin/rm "$LOG_FN" 2>/dev/null

# Herunterladen der Vorhersage-Dateien und Zeichensatz konvertieren
for i in 50 51 52 53 54; do
    FN="VHDL${i}_${DWD_BUNDESLAND}_LATEST"
    ${WGET} -O "${TMP}" "${DWD_URL}/${FN}_html"

    # Hinweis: => <\p><p><strong>Hinweis:<\strong>
    sed -i 's/Hinweis:/<\/p><p><strong>Hinweis:<\/strong>/' "${TMP}"

    if [[ i -ne 54 ]]; then
        # In der Nacht zum => <\p><p>In der Nacht zum
        sed -i 's/In der Nacht zum/<\/p><p>In der Nacht zum/' "${TMP}"
    fi
    
    #TODO: Im Moment gehe ich davon aus, dass die jeweiligen Dateien mit <p> </p> eingebunden sind.
    if [[ i -eq 50 ]]; then
        sed -i 's/<\/strong>/&<\/p><p>/g' "${TMP}"
    elif [[ i -eq 54 ]]; then

# TEST
# echo -e "\
# \nFROST/SCHNEE/GLÄTTE/GLATTEIS: \
# \nFROST/SCHNEE/GLÄTTE: \
# \nFROST/GLATTEIS: \
# \nGLÄTTE: \
# \nDAUERREGEN/TAUWETTER (teils UNWETTER): \
# \nGLATTEIS (teils UNWETTER): \
# \nGLATTEIS/ÜBERFRIERENDE NÄSSE (UNWETTER): \
# \nERGIEBIGER DAUERREGEN (UNWETTER): \
# \nGLATTEIS/ÜBERFRIERENDE NÄSSE (UNWETTER im ALLGÄU): \
# \nGLATTEIS/ÜBERFRIERENDE NÄSSE (UNWETTER in NIEDERBAYERN): \
# \nGLATTEIS/ÜBERFRIERENDE NÄSSE (UNWETTER in der OBERPFALZ): \
# \nDAUERREGEN/TAUWETTER (UNWETTER im ALLGÄU): \
# \nGLATTEIS(Unwettergefahr): \
# \nGLATTEIS (UNWETTER): \
# \n(UNWETTER) \
# \n" >"${TMP}"

        sed -i 's/\<Uhr\><\/strong>/&<\/p><p>/g' "${TMP}"
        #TODO: sed zusammenfassen
        #TODO: UML2DUMMY/DUMMY2UML: bessere Lösung möglich? Grund: :upper: und Umlaute (z.B. SCHNEE/GLÄTTE:)
        ${UML2DUMMY} <"${TMP}" >"${TMP2}"
        ${MV} ${TMP2} ${TMP}

        # XXX/XXX/XXX/XXX: ===> <\p><p><strong>Xxx/Xxx/Xxx/Xxx:<\strong>
        sed -i 's/\([[:upper:]]\)\([[:upper:]]*\)\/\([[:upper:]]\)\([[:upper:]]*\)\/\([[:upper:]]\)\([[:upper:]]*\)\/\([[:upper:]]\)\([[:upper:]]*\):/<\/p><p><strong>\u\1\L\2\/\u\3\L\4\/\u\5\L\6\/\u\7\L\8:<\/strong>/g' "${TMP}"

        # GLÄTTE/GLATTEIS/SCHNEE: ===> <\p><p><strong>Xxx/Xxx/Xxx:<\strong>
        sed -i 's/\([[:upper:]]\)\([[:upper:]]*\)\/\([[:upper:]]\)\([[:upper:]]*\)\/\([[:upper:]]\)\([[:upper:]]*\):/<\/p><p><strong>\u\1\L\2\/\u\3\L\4\/\u\5\L\6:<\/strong>/g' "${TMP}"

        # GLÄTTE/GLATTEIS/SCHNEE ===> <\p><p><strong>Xxx/Xxx/Xxx:<\strong>
        sed -i 's/\([[:upper:]]\)\([[:upper:]]*\)\/\([[:upper:]]\)\([[:upper:]]*\)\/\([[:upper:]]\)\([[:upper:]]*\)/<\/p><p><strong>\u\1\L\2\/\u\3\L\4\/\u\5\L\6:<\/strong>/g' "${TMP}"

        # GLÄTTE/SCHNEE: ===> <\p><p><strong>Glätte/Schnee:<\strong>
        sed -i 's/\([[:upper:]]\)\([[:upper:]]*\)\/\([[:upper:]]\)\([[:upper:]]*\):/<\/p><p><strong>\u\1\L\2\/\u\3\L\4:<\/strong>/g' "${TMP}"

        # GLÄTTE/SCHNEE ===> <\p><p><strong>Glätte/Schnee:<\strong>
        sed -i 's/\([[:upper:]]\)\([[:upper:]]*\)\/\([[:upper:]]\)\([[:upper:]]*\)/<\/p><p><strong>\u\1\L\2\/\u\3\L\4:<\/strong>/g' "${TMP}"

        # STARK-/DAUERREGEN: ===> <\p><p><strong>Stark-/Dauerregen:<\strong>
        sed -i 's/\([[:upper:]]\)\([[:upper:]]*\)-\/\([[:upper:]]\)\([[:upper:]]*\):/<\/p><p><strong>\u\1\L\2-\/\u\3\L\4:<\/strong>/g' "${TMP}"

        # NEBEL: ===> <\p><p><strong>Nebel:<\strong>
        sed -i 's/\([[:upper:]]\)\([[:upper:]]*\):/<\/p><p><strong>\u\1\L\2:<\/strong>/g' "${TMP}"

        # DAUERREGEN/TAUWETTER (teils UNWETTER): ===> <\p><p><strong>Dauerregen/Tauwetter (teils Unwetter):<\strong>
        sed -i 's/\([[:upper:]]\)\([[:upper:]]*\)\/\([[:upper:]]\)\([[:upper:]]*\) (\([[:lower:]]*\) \([[:upper:]]\)\([[:upper:]]*\)):/<\/p><p><strong>\u\1\L\2\/\u\3\L\4 (\L\5 \u\6\L\7):<\/strong>/g' "${TMP}"

        # GLATTEIS (teils UNWETTER): ===> <\p><p><strong>Glatteis (teils Unwetter):<\strong>
        sed -i 's/\([[:upper:]]\)\([[:upper:]]*\) (\([[:lower:]]*\) \([[:upper:]]\)\([[:upper:]]*\)):/<\/p><p><strong>\u\1\L\2 (\L\3 \u\4\L\5):<\/strong>/g' "${TMP}"

        # GLATTEIS/ÜBERFRIERENDE NÄSSE (UNWETTER): ===> <\p><p><strong>Glatteis/überfrierende Nässe (Unwetter):<\strong>
        sed -i 's/\([[:upper:]]\)\([[:upper:]]*\)\/\([[:upper:]]\)\([[:upper:]]*\) \([[:upper:]]\)\([[:upper:]]*\) (\([[:upper:]]\)\([[:upper:]]*\)):/<\/p><p><strong>\u\1\L\2\/\L\3\L\4 \u\5\L\6 (\u\7\L\8):<\/strong>/g' "${TMP}"

        # ERGIEBIGER DAUERREGEN (UNWETTER):
        sed -i 's/\([[:upper:]]\)\([[:upper:]]*\) \([[:upper:]]\)\([[:upper:]]*\) (\([[:upper:]]\)\([[:upper:]]*\)):/<\/p><p><strong>\u\1\L\2 \u\3\L\4 (\u\5\L\6):<\/strong>/g' "${TMP}"

        # DAUERREGEN/TAUWETTER (UNWETTER im ALLGÄU): ===> <\p><p><strong>Dauerregen/Tauwetter (Unwetter im Allgäu):<\strong>
        sed -i 's/\([[:upper:]]\)\([[:upper:]]*\)\/\([[:upper:]]\)\([[:upper:]]*\) (\([[:upper:]]\)\([[:upper:]]*\) \([[:lower:]]*\) \([[:upper:]]\)\([[:upper:]]*\)):/<\/p><p><strong>\u\1\L\2\/\u\3\L\4 (\u\5\L\6 \L\7 \u\8\L\9):<\/strong>/g' "${TMP}"

        #TODO z.B. \u10\L\11 funktioniert nicht. Problem >9
        # GLATTEIS/ÜBERFRIERENDE NÄSSE (UNWETTER im ALLGÄU): ===> <\p><p><strong>Glatteis/überfrierende Nässe (Unwetter im Allgäu):<\strong>
        #sed -i 's/\([[:upper:]]\)\([[:upper:]]*\)\/\([[:upper:]]\)\([[:upper:]]*\) \([[:upper:]]\)\([[:upper:]]*\) (\([[:upper:]]\)\([[:upper:]]*\) \([[:lower:]]*\) \([[:upper:]]\)\([[:upper:]]*\)):/<\/p><p><strong>\u\1\L\2\/\L\3\L\4 \u\5\L\6 (\u\7\L\8 \L\9 \u\10\L\11):<\/strong>/g' "${TMP}"
        sed -i 's/\([[:upper:]]\)\([[:upper:]]*\)\/\([[:upper:]]*\) \([[:upper:]]\)\([[:upper:]]*\) (\([[:upper:]]\)\([[:upper:]]*\) im \([[:upper:]]\)\([[:upper:]]*\)):/<\/p><p><strong>\u\1\L\2\/\L\3 \u\4\L\5 (\u\6\L\7 im \u\8\L\9):<\/strong>/g' "${TMP}"

        #TODO z.B. \u10\L\11 funktioniert nicht. Problem >9
        # GLATTEIS/ÜBERFRIERENDE NÄSSE (UNWETTER in NIEDERBAYERN): ===> <\p><p><strong>Glatteis/überfrierende Nässe (Unwetter in Niederbayern):<\strong>
        #sed -i 's/\([[:upper:]]\)\([[:upper:]]*\)\/\([[:upper:]]\)\([[:upper:]]*\) \([[:upper:]]\)\([[:upper:]]*\) (\([[:upper:]]\)\([[:upper:]]*\) \([[:lower:]]*\) \([[:upper:]]\)\([[:upper:]]*\)):/<\/p><p><strong>\u\1\L\2\/\L\3\L\4 \u\5\L\6 (\u\7\L\8 \L\9 \u\10\L\11):<\/strong>/g' "${TMP}"
        sed -i 's/\([[:upper:]]\)\([[:upper:]]*\)\/\([[:upper:]]*\) \([[:upper:]]\)\([[:upper:]]*\) (\([[:upper:]]\)\([[:upper:]]*\) in \([[:upper:]]\)\([[:upper:]]*\)):/<\/p><p><strong>\u\1\L\2\/\L\3 \u\4\L\5 (\u\6\L\7 in \u\8\L\9):<\/strong>/g' "${TMP}"

        #TODO z.B. \u10\L\11 funktioniert nicht. Problem >9
        # GLATTEIS/ÜBERFRIERENDE NÄSSE (UNWETTER in der OBERPFALZ): ===> <\p><p><strong>Glatteis/überfrierende Nässe (Unwetter in der Oberpfalz):<\strong>
        #sed -i 's/\([[:upper:]]\)\([[:upper:]]*\)\/\([[:upper:]]\)\([[:upper:]]*\) \([[:upper:]]\)\([[:upper:]]*\) (\([[:upper:]]\)\([[:upper:]]*\) \([[:lower:]]*\) \([[:upper:]]\)\([[:upper:]]*\)):/<\/p><p><strong>\u\1\L\2\/\L\3\L\4 \u\5\L\6 (\u\7\L\8 \L\9 \u\10\L\11):<\/strong>/g' "${TMP}"
        sed -i 's/\([[:upper:]]\)\([[:upper:]]*\)\/\([[:upper:]]*\) \([[:upper:]]\)\([[:upper:]]*\) (\([[:upper:]]\)\([[:upper:]]*\) in der \([[:upper:]]\)\([[:upper:]]*\)):/<\/p><p><strong>\u\1\L\2\/\L\3 \u\4\L\5 (\u\6\L\7 in der \u\8\L\9):<\/strong>/g' "${TMP}"

        # GLATTEIS(Unwettergefahr): ===> <\p><p><strong>Glatteis (Unwettergefahr):<\strong>
        sed -i 's/\([[:upper:]]\)\([[:upper:]]*\)(\([[:upper:]]\)\([[:lower:]]*\)):/<\/p><p><strong>\u\1\L\2 (\u\3\L\4):<\/strong>/g' "${TMP}"

        # GLATTEIS (UNWETTER): ===> <\p><p><strong>Glatteis (Unwetter):<\strong>
        sed -i 's/\([[:upper:]]\)\([[:upper:]]*\) (\([[:upper:]]\)\([[:upper:]]*\)):/<\/p><p><strong>\u\1\L\2 (\u\3\L\4):<\/strong>/g' "${TMP}"

        # GLATTEIS(UNWETTER): ===> <\p><p><strong>Glatteis (Unwetter):<\strong>
        sed -i 's/\([[:upper:]]\)\([[:upper:]]*\)(\([[:upper:]]\)\([[:upper:]]*\)):/<\/p><p><strong>\u\1\L\2 (\u\3\L\4):<\/strong>/g' "${TMP}"

        # (UNWETTER) ===> <\p><p><strong>(Unwetter)<\strong>
        #sed -i 's/(\([[:upper:]]\)\([[:upper:]]*\))/<\/p><p><strong>(\u\1\L\2)<\/strong>/g' "${TMP}"
        # (UNWETTER) ===> <strong>(Unwetter)<\strong>
        sed -i 's/(\([[:upper:]]\)\([[:upper:]]*\))/<strong>(\u\1\L\2)<\/strong>/g' "${TMP}"

        ${DUMMY2UML} <"${TMP}" >"${TMP2}"
        ${MV} ${TMP2} ${TMP}
    fi
    if [ "$?" -eq 0 ]; then
        for EXPORT in ${EXPORTS[@]}; do
            ${HTML2ENT} <"${TMP}" >"${EXPORT}/${FN}.html"
            ${TOUCH} "${TMP}" "${EXPORT}/${FN}.html"
        done
        ${RM} "${TMP}"
    fi
done

# Herunterladen der uebrigen Dateien
${WGET} -O "/tmp/${DWD_MAP##*/}" ${DWD_MAP}
${WGET} -O "/tmp/${DWD_MAP2##*/}" ${DWD_MAP2}
${WGET} -O "/tmp/${DWD_WARN##*/}" ${DWD_WARN}
${WGET} -O "/tmp/${DWD_WARNJ##*/}" ${DWD_WARNJ}
for EXPORT in ${EXPORTS[@]}; do
    ${CP} "/tmp/${DWD_MAP##*/}" ${EXPORT}/
    ${CP} "/tmp/${DWD_MAP2##*/}" ${EXPORT}/
    ${CP} "/tmp/${DWD_WARN##*/}" ${EXPORT}/
    ${CP} "/tmp/${DWD_WARNJ##*/}" ${EXPORT}/
done
${RM} "/tmp/${DWD_MAP##*/}"
${RM} "/tmp/${DWD_MAP2##*/}"
${RM} "/tmp/${DWD_WARN##*/}"
${RM} "/tmp/${DWD_WARNJ##*/}"

exit 0