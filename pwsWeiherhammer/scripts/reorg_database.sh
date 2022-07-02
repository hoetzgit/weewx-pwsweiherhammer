#!/bin/bash
DB_ADMIN=weewx
DB_PASSWD=weewx
DB_BACKUP=weewx

sudo systemctl stop weewx

mysqldump --single-transaction -h localhost -u$DB_ADMIN -p$DB_PASSWD $DB_BACKUP > /home/weewx/reorg_database.sql

sudo /home/weewx/bin/wee_database --config=/home/weewx/weewx.conf --reconfigure

mysql -u$DB_ADMIN -p$DB_PASSWD -e "DROP DATABASE weewx;"
mysql -u$DB_ADMIN -p$DB_PASSWD -e "CREATE DATABASE weewx;"
mysql -u$DB_ADMIN -p$DB_PASSWD -e "RENAME TABLE weewx_new.archive TO weewx.archive;"

sudo /home/weewx/bin/wee_database --config=/home/weewx/weewx.conf --rebuild-daily

sudo systemctl restart weewx
