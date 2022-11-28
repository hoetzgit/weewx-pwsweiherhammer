#!/bin/bash

#backfilled
exit 0
##################################################################################################
#
# Die Wetterstation speichert Datensätze sunshineDur seit dem 06.06.2022 in der WeeWX Datenbank.
#
# Bei einem --rebuild-daily Lauf werden vom Wert her gültige
# sum=0.0, count=0, wsum=0.0, sumtime=0 Werte in der archiv_day_sunshineDur* Tabelle erzeugt.
# Werden diese Werte in Diagrammen, Tabellen etc ausgewertet, müssen sie auf NULL gesetzt werden,
# da vor dem Start der Messung keine gültigen Werte entstanden sind.
#
# 1654466400 = Mon Jun 06 2022 00:00:00 GMT+0200 (Mitteleuropäische Sommerzeit)
#
##################################################################################################
DB=weewx
DB_USER=weewx
DB_PASSWD=weewx
DB_HOST=192.168.0.182
STARTDATE=1654466400
DB_EXPORT="/tmp/weewx-dump-$(date +"%Y%m%d%H%M").sql"
WHAT="${DB}.archiv_day_sunshineDur* vor dem 06.06.2022"

TABLES=(
"archive_day_sunshineDur"
)

echo ""
read -r -p "Datenbank ${DB} vorher sichern? [j/N] " response
if [[ "$response" =~ ^([yY]|[jJ])$ ]]; then
    echo "Datenbank ${DB} wird in ${DB_EXPORT} gesichert..."
    sudo mysqldump --single-transaction -v -h${DB_HOST} -u${DB_USER} -p${DB_PASSWD} ${DB} >${DB_EXPORT}
    RET=$?
    if [ ${RET} -ne 0 ]; then
        echo "Fehler bei Sicherung, Code=${RET}. Skript wird abgebrochen!"
        exit ${RET}
    fi
    echo "OK."
else
    echo "Datenbank ${DB} wurde NICHT gesichert."
fi

echo ""
echo "Achtung! Werte in den Tabellen ${WHAT} werden auf NULL gesetzt."
read -r -p "Weiter? [j/N] " response
if [[ "$response" =~ ^([yY]|[jJ])$ ]]; then
    echo "Update der Tabellen ${WHAT} wird gestartet..."
    for TABLE in "${TABLES[@]}"
    do
        echo "Update in ${DB}.${TABLE}..."
        mysql -h${DB_HOST} -u${DB_USER} -p${DB_PASSWD} -v -e "UPDATE ${DB}.${TABLE} SET sum=NULL, count=NULL, wsum=NULL, sumtime=NULL WHERE dateTime<${STARTDATE};"
        RET=$?
        if [ ${RET} -ne 0 ]; then
            echo "Fehler beim Update, Code=${RET}. Skript wird abgebrochen!"
            exit ${RET}
        fi
        echo "OK."
    done
else
    echo "Datensätze wurden NICHT geändert."
fi

echo -e "\nSkript abgeschlossen."