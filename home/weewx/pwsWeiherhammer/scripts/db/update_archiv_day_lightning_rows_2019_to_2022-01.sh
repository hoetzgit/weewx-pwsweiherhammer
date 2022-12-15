#!/bin/bash
###################################################################################################
#
# Die Wetterstation speichert Datensätze Gewitterblitze seit dem 20.01.2022 in der WeeWX Datenbank.
#
# Bei einem --rebuild-daily Lauf werden vom Wert her gültige
# sum=0.0, count=0, wsum=0.0, sumtime=0 Werte in der archiv_day_lightning_* Tabelle erzeugt.
# Werden diese Werte in Diagrammen, Tabellen etc ausgewertet, müssen sie auf NULL gesetzt werden,
# da vor dem Start der Messung keine gültigen Werte entstanden sind.
#
# 1642633200 = Thu Jan 20 2022 00:00:00 GMT+0100 (Mitteleuropäische Normalzeit)
#
###################################################################################################
DB=weewx
DB_USER=weewx
DB_PASSWD=weewx
#DB_HOST=192.168.0.182
DB_HOST=localhost
STARTDATE=1642633200
DB_EXPORT="/tmp/weewx-dump-$(date +"%Y%m%d%H%M").sql"
WHAT="${DB}.archive_day_lightning_* vor dem 20.01.2022"

TABLES=(
"archive_day_lightning_distance"
"archive_day_lightning_disturber_count"
"archive_day_lightning_energy"
"archive_day_lightning_last_time"
"archive_day_lightning_noise_count"
"archive_day_lightning_strike_count"
)

echo ""
read -r -p "Datenbank ${DB} vorher sichern? (y/n) [y]? " response
if [[ "$response" =~ ^([nN])$ ]]; then
    echo "Datenbank ${DB} wurde NICHT gesichert."
else
    echo "Datenbank ${DB} wird in ${DB_EXPORT} gesichert..."
    sudo mysqldump --single-transaction -v -h${DB_HOST} -u${DB_USER} -p${DB_PASSWD} ${DB} >${DB_EXPORT}
    RET=$?
    if [ ${RET} -ne 0 ]; then
        echo "Fehler bei Sicherung, Code=${RET}. Skript wird abgebrochen!"
        exit ${RET}
    fi
    echo "OK."
fi

echo ""
echo "Achtung! Werte in den Tabellen ${WHAT} werden auf NULL gesetzt."
read -r -p "Weiter (y/n) [n]? " response
if [[ "$response" =~ ^([yY]|[jJ])$ ]]; then
    echo "Update der Tabellen ${WHAT} wird gestartet..."
    for TABLE in "${TABLES[@]}"
    do
        echo "Update in ${DB}.${TABLE}..."
        mysql -h${DB_HOST} -u${DB_USER} -p${DB_PASSWD} -v -e "UPDATE ${DB}.${TABLE} SET sum=NULL, count=0, wsum=NULL, sumtime=0 WHERE dateTime<${STARTDATE};"
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