#!/bin/bash
###################################################################################################
#
# Die Tabelle archive_day_luminosity leeren und Feld luminosity in archive Tabelle auf NULL setzen
#
# Wert luminosity aus der radiation zu berechnen, scheint Quatsch zu sein.
# siehe auch: https://github.com/weewx/weewx/wiki/Watts-and-lux
#
###################################################################################################
DB=weewx
DB_USER=weewx
DB_PASSWD=weewx
#DB_HOST=192.168.0.182
DB_HOST=localhost
DB_EXPORT="/tmp/weewx-dump-$(date +"%Y%m%d%H%M").sql"
WHAT="${DB}.archive_day_luminosity leeren und ${DB}.archive Feld luminosity auf NULL setzen."

TABLES=(
"archive_day_luminosity"
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
echo "Achtung! Folgende Aktionen werden gestartet: ${WHAT}"
read -r -p "Weiter (y/n) [n]? " response
if [[ "$response" =~ ^([yY]|[jJ])$ ]]; then
    echo "Update der Tabellen ${WHAT} wird gestartet..."
    for TABLE in "${TABLES[@]}"
    do
        echo "Update in ${DB}.${TABLE}..."
        mysql -h${DB_HOST} -u${DB_USER} -p${DB_PASSWD} -v -e "UPDATE ${DB}.${TABLE} SET min=NULL, mintime=NULL, max=NULL, maxtime=NULL, sum=0, count=0, wsum=0, sumtime=0;"
        RET=$?
        if [ ${RET} -ne 0 ]; then
            echo "Fehler beim Update, Code=${RET}. Skript wird abgebrochen!"
            exit ${RET}
        fi
        echo "OK."
    done

    mysql -h${DB_HOST} -u${DB_USER} -p${DB_PASSWD} -v -e "UPDATE ${DB}.archive SET luminosity=NULL WHERE luminosity is not NULL;"
    RET=$?
    if [ ${RET} -ne 0 ]; then
        echo "Fehler beim Update, Code=${RET}. Skript wird abgebrochen!"
        exit ${RET}
    fi
    echo "OK."
else
    echo "Datensätze wurden NICHT geändert."
fi

echo -e "\nSkript abgeschlossen."