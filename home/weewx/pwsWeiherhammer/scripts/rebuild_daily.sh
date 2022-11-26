#!/bin/bash
DB=weewx
DB_USER=weewx
DB_PASSWD=weewx
#DB_HOST=192.168.0.182
DB_HOST=localhost
DB_EXPORT="/tmp/weewx-dump-$(date +"%Y%m%d%H%M").sql"

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

#sudo echo "y" | sudo /home/weewx/bin/wee_database --config=/home/weewx/weewx.conf --drop-daily
#sudo echo "y" | sudo /home/weewx/bin/wee_database --config=/home/weewx/weewx.conf --rebuild-daily
/home/weewx/bin/wee_database --config=/home/weewx/weewx.conf --drop-daily
/home/weewx/bin/wee_database --config=/home/weewx/weewx.conf --rebuild-daily

/home/weewx/pwsWeiherhammer/scripts/update_archiv_day_lightning_rows_2019_to_2022-01.sh
/home/weewx/pwsWeiherhammer/scripts/update_archiv_day_xxx_rows_2019_01to07.sh

