#!/bin/bash
# Herunterladen DWD Waldbrandgefahrenindex Bayern
# Copyright (C) 2023 Henry Ott
# licensed under the terms of the General Public License (GPL) v3

# Zielpfad zum Speichern der Dateien
SKINS=(
"/home/weewx/skins/Weiherhammer/dwd"
#"/home/weewx/skins/weewx-wdc/dwd"
)

DATAS=(
"/home/weewx/public_html/data/dwd"
)

TMPPATH="/tmp"

# bash with parameters
CURL="/usr/bin/curl -s -X POST https://html2json.com/api/v1"
MV="/usr/bin/mv -vf"
CP="/usr/bin/cp -vf"
RM="/usr/bin/rm -vf"

# URLs der herunterzuladenden Dateien beim DWD
DWD_WBX="https://www.dwd.de/DWD/warnungen/agrar/wbx/wbx_tab_alle_BY.html"
DWD_WBXJ="$TMPPATH"/$(basename "/TMPPATH/${DWD_WBX##*/}" .html).json

# DWD Webseite mit WBX laden und in JSON konvertieren
echo "Loading DWD Website $DWD_WBX and convert to json file $DWD_WBXJ"
$CURL -o $DWD_WBXJ -d "$(/usr/bin/curl -s -L $DWD_WBX)" >/dev/null
if test $? -eq 0; then
    for SKIN in ${SKINS[@]}; do
        echo "copy to ${SKIN}"
        ${CP} ${DWD_WBXJ} ${SKIN}
    done
    for DATA in ${DATAS[@]}; do
        echo "copy to ${DATA}"
        ${CP} ${DWD_WBXJ} ${DATA}
    done
    ${RM} "DWD_WBXJ"
    echo "finished successful."
else
    echo "finished with error(s)"
fi