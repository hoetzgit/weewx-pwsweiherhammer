#!/bin/bash

DB_HOST=192.168.0.182
DB_ADMIN=weewx
DB_PASSWD=weewx
DB_BACKUP=weewx
DB_EXPORT="/home/weewx/reorg_db_change001.sql"

BACKUPDB_SOURCE_HOST=192.168.0.182
BACKUPDB=weewx
BACKUPDB_ADMIN=weewx
BACKUPDB_PASSWD=weewx
BACKUPDB_STORE=/tmp
BACKUPDB_FILE=$BACKUPDB_STORE/weewx_prod.sql

echo "systemctl stop weewx.service"
systemctl stop weewx.service

echo "mysqldump --single-transaction -h $DB_HOST -u$DB_ADMIN -p$DB_PASSWD $DB_BACKUP > $DB_EXPORT"
mysqldump --single-transaction -h $DB_HOST -u$DB_ADMIN -p$DB_PASSWD $DB_BACKUP > $DB_EXPORT
RET=$?
if [ $RET -ne 0 ] ; then
  echo "Error! Code=$RET"
  exit $RET
fi

#echo "sudo mysqldump --single-transaction -h $BACKUPDB_SOURCE_HOST -u$BACKUPDB_ADMIN -p$BACKUPDB_PASSWD $BACKUPDB > $BACKUPDB_FILE"
#sudo mysqldump --single-transaction -h $BACKUPDB_SOURCE_HOST -u$BACKUPDB_ADMIN -p$BACKUPDB_PASSWD $BACKUPDB > $BACKUPDB_FILE
#RET=$?
#if [ $RET -ne 0 ] ; then
#  echo "Error! Code=$RET"
#  exit $RET
#fi

#echo 'mysql -u$DB_ADMIN -p$DB_PASSWD -e "DROP DATABASE weewx;"'
#mysql -u$DB_ADMIN -p$DB_PASSWD -e "DROP DATABASE weewx;"
#echo 'mysql -u$DB_ADMIN -p$DB_PASSWD -e "CREATE DATABASE weewx;"'
#mysql -u$DB_ADMIN -p$DB_PASSWD -e "CREATE DATABASE weewx;"
#echo "sudo mysql -u$BACKUPDB_ADMIN -p$BACKUPDB_PASSWD $BACKUPDB < $BACKUPDB_FILE"
#sudo mysql -u$BACKUPDB_ADMIN -p$BACKUPDB_PASSWD $BACKUPDB < $BACKUPDB_FILE
#RET=$?
#if [ $RET -ne 0 ] ; then
#  echo "Error! Code=$RET"
#  exit $RET
#fi
#echo "rm -rdf $BACKUPDB_FILE"
#rm -rdf $BACKUPDB_FILE

#echo "systemctl stop mariadb.service"
#systemctl stop mariadb.service
#echo "rm -rdf /var/log/mysql/*"
#rm -rdf /var/log/mysql/*
#echo "systemctl restart mariadb.service"
#systemctl restart mariadb.service
#RET=$?
#if [ $RET -ne 0 ] ; then
#  echo "Error! Code=$RET"
#  exit $RET
#fi

echo "cp -a -v /home/weewx/bin/schemas/wview_pwsott-change001_temp.py /home/weewx/bin/schemas/wview_pwsott.py"
cp -a -v /home/weewx/bin/schemas/wview_pwsott-change001_temp.py /home/weewx/bin/schemas/wview_pwsott.py
RET=$?
if [ $RET -ne 0 ] ; then
  echo "Error! Code=$RET"
  exit $RET
fi

echo "cp -a -v /home/weewx/bin/weeutil/weeutil.py-immer-y /home/weewx/bin/weeutil/weeutil.py"
cp -a -v /home/weewx/bin/weeutil/weeutil.py-immer-y /home/weewx/bin/weeutil/weeutil.py
RET=$?
if [ $RET -ne 0 ] ; then
  echo "Error! Code=$RET"
  exit $RET
fi

echo "sudo /home/weewx/bin/wee_database --config=/home/weewx/weewx.conf --reconfigure"
sudo /home/weewx/bin/wee_database --config=/home/weewx/weewx.conf --reconfigure
RET=$?
if [ $RET -ne 0 ] ; then
  echo "Error! Code=$RET"
  exit $RET
fi
echo -e "finished.\n"

SQL_STATEMENTS=(
"DROP DATABASE weewx;"
"CREATE DATABASE weewx;"
"RENAME TABLE weewx_new.archive TO weewx.archive;"
"-- Feldanpassungen Solar"
"UPDATE weewx.archive SET solar_temperature = extraTemp1 WHERE extraTemp1 IS NOT NULL;"
"UPDATE weewx.archive SET solar_barometer = barometer1 WHERE barometer1 IS NOT NULL;"
"UPDATE weewx.archive SET solar_humidity = extraHumid1 WHERE extraHumid1 IS NOT NULL;"
"UPDATE weewx.archive SET solar_dewpoint = dewpoint1 WHERE dewpoint1 IS NOT NULL;"
"UPDATE weewx.archive SET solar_heatindex = heatindex1 WHERE heatindex1 IS NOT NULL;"
"UPDATE weewx.archive SET solar_pressure = pressure1 WHERE pressure1 IS NOT NULL;"
"UPDATE weewx.archive SET solar_voltage = stationVoltage1 WHERE stationVoltage1 IS NOT NULL;"
"UPDATE weewx.archive SET extraTemp1 = NULL WHERE extraTemp1 IS NOT NULL;"
"UPDATE weewx.archive SET extraHumid1 = NULL WHERE extraHumid1 IS NOT NULL;"
"UPDATE weewx.archive SET dewpoint1 = NULL WHERE dewpoint1 IS NOT NULL;"
"-- Feldanpassungen Blitz alt"
"UPDATE weewx.archive SET extraTemp2 = NULL WHERE extraTemp2 IS NOT NULL;"
"UPDATE weewx.archive SET extraHumid2 = NULL WHERE extraHumid2 IS NOT NULL;"
"-- Feldanpassungen Allsky"
"UPDATE weewx.archive SET asky_box_temperature = extraTemp3 WHERE extraTemp3 IS NOT NULL;"
"UPDATE weewx.archive SET asky_box_humidity = extraHumid3 WHERE extraHumid3 IS NOT NULL;"
"UPDATE weewx.archive SET asky_box_dewpoint = dewpoint3 WHERE dewpoint3 IS NOT NULL;"
"UPDATE weewx.archive SET asky_box_heatindex = heatindex3 WHERE heatindex3 IS NOT NULL;"
"UPDATE weewx.archive SET asky_box_pressure = pressure3 WHERE pressure3 IS NOT NULL;"
"UPDATE weewx.archive SET asky_box_barometer = barometer3 WHERE barometer3 IS NOT NULL;"
"UPDATE weewx.archive SET asky_box_fan = fan1 WHERE fan1 IS NOT NULL;"
"UPDATE weewx.archive SET asky_dome_temperature = extraTemp4 WHERE extraTemp4 IS NOT NULL;"
"UPDATE weewx.archive SET asky_dome_dewpoint = dewpoint4 WHERE dewpoint4 IS NOT NULL;"
"UPDATE weewx.archive SET asky_dome_heatindex = heatindex4 WHERE heatindex4 IS NOT NULL;"
"UPDATE weewx.archive SET asky_dome_heater = heater1 WHERE heater1 IS NOT NULL;"
"UPDATE weewx.archive SET asky_cpu_temperature = extraTemp5 WHERE extraTemp5 IS NOT NULL;"
"UPDATE weewx.archive SET extraTemp3 = NULL WHERE extraTemp3 IS NOT NULL;"
"UPDATE weewx.archive SET extraHumid3 = NULL WHERE extraHumid3 IS NOT NULL;"
"UPDATE weewx.archive SET extraTemp4 = NULL WHERE extraTemp4 IS NOT NULL;"
"UPDATE weewx.archive SET extraTemp5 = NULL WHERE extraTemp5 IS NOT NULL;"
"-- Feldanpassungen OWM"
"UPDATE weewx.archive SET owm_co = co WHERE co IS NOT NULL;"
"UPDATE weewx.archive SET owm_no = no WHERE no IS NOT NULL;"
"UPDATE weewx.archive SET owm_no2 = no2 WHERE no2 IS NOT NULL;"
"UPDATE weewx.archive SET owm_o3 = o3 WHERE o3 IS NOT NULL;"
"UPDATE weewx.archive SET owm_so2 = so2 WHERE so2 IS NOT NULL;"
"UPDATE weewx.archive SET owm_pm2_5 = pm2_5 WHERE pm2_5 IS NOT NULL;"
"UPDATE weewx.archive SET owm_pm10_0 = pm10_0 WHERE pm10_0 IS NOT NULL;"
"UPDATE weewx.archive SET owm_nh3 = nh3 WHERE nh3 IS NOT NULL;"
"UPDATE weewx.archive SET co = NULL WHERE co IS NOT NULL;"
"UPDATE weewx.archive SET no = NULL WHERE no IS NOT NULL;"
"UPDATE weewx.archive SET no2 = NULL WHERE no2 IS NOT NULL;"
"UPDATE weewx.archive SET o3 = NULL WHERE o3 IS NOT NULL;"
"UPDATE weewx.archive SET so2 = NULL WHERE so2 IS NOT NULL;"
"UPDATE weewx.archive SET pm2_5 = NULL WHERE pm2_5 IS NOT NULL;"
"UPDATE weewx.archive SET pm10_0 = NULL WHERE pm10_0 IS NOT NULL;"
"UPDATE weewx.archive SET nh3 = NULL WHERE nh3 IS NOT NULL;"
"-- Feldanpassungen Sicherheit"
"UPDATE weewx.archive SET extraHumid4 = NULL WHERE extraHumid4 IS NOT NULL;"
"UPDATE weewx.archive SET extraHumid5 = NULL WHERE extraHumid5 IS NOT NULL;"
"-- Feldanpassungen Blitze"
"update weewx.archive set lightning_energy = null WHERE lightning_energy IS NOT NULL;"
"update weewx.archive set lightning_unknown_count = null WHERE lightning_unknown_count IS NOT NULL;"
"update weewx.archive set lightning_disturber_count = null WHERE lightning_disturber_count IS NOT NULL;"
"update weewx.archive set lightning_strike_count = null WHERE lightning_strike_count IS NOT NULL AND dateTime < 1642674960;"
"update weewx.archive set lightning_noise_count = null WHERE lightning_noise_count IS NOT NULL;"
"update weewx.archive set lightning_distance = null WHERE lightning_distance IS NOT NULL AND dateTime < 1642674960;"
"update weewx.archive set lightning_last_time = 1642674952 WHERE dateTime = 1642674960;"
)

echo "Changing Fields ..."
for STATEMENT in "${SQL_STATEMENTS[@]}"
do
  echo "${STATEMENT}"
  mysql -u$DB_ADMIN -p$DB_PASSWD -e "${STATEMENT}"
  RET=$?
  if [ $RET -ne 0 ] ; then
    echo "Error! Code=$RET"
    exit $RET
  fi
  echo -e "finished.\n" 
done

echo "systemctl stop mariadb.service"
systemctl stop mariadb.service
echo "rm -rdf /var/log/mysql/*"
rm -rdf /var/log/mysql/*
echo "systemctl restart mariadb.service"
systemctl restart mariadb.service
RET=$?
if [ $RET -ne 0 ] ; then
  echo "Error! Code=$RET"
  exit $RET
fi

echo "cp -a -v /home/weewx/bin/schemas/wview_pwsott-change001_final.py /home/weewx/bin/schemas/wview_pwsott.py"
cp -a -v /home/weewx/bin/schemas/wview_pwsott-change001_final.py /home/weewx/bin/schemas/wview_pwsott.py
RET=$?
if [ $RET -ne 0 ] ; then
  echo "Error! Code=$RET"
  exit $RET
fi

echo "sudo /home/weewx/bin/wee_database --config=/home/weewx/weewx.conf --reconfigure"
sudo /home/weewx/bin/wee_database --config=/home/weewx/weewx.conf --reconfigure
RET=$?
if [ $RET -ne 0 ] ; then
  echo "Error! Code=$RET"
  exit $RET
fi
echo -e "finished.\n"

SQL_STATEMENTS=(
"DROP DATABASE weewx;"
"CREATE DATABASE weewx;"
"RENAME TABLE weewx_new.archive TO weewx.archive;"
)

echo "Kopiere weewx_new to weewx ..."
for STATEMENT in "${SQL_STATEMENTS[@]}"
do
  echo "${STATEMENT}"
  mysql -u$DB_ADMIN -p$DB_PASSWD -e "${STATEMENT}"
  RET=$?
  if [ $RET -ne 0 ] ; then
    echo "Error! Code=$RET"
    exit $RET
  fi
  echo -e "finished.\n" 
done

echo "systemctl stop mariadb.service"
systemctl stop mariadb.service
echo "rm -rdf /var/log/mysql/*"
rm -rdf /var/log/mysql/*
echo "systemctl restart mariadb.service"
systemctl restart mariadb.service
RET=$?
if [ $RET -ne 0 ] ; then
  echo "Error! Code=$RET"
  exit $RET
fi

echo "Rebuild Daily"
echo "sudo /home/weewx/bin/wee_database --config=/home/weewx/weewx.conf --rebuild-daily"
sudo /home/weewx/bin/wee_database --config=/home/weewx/weewx.conf --rebuild-daily
RET=$?
if [ $RET -ne 0 ] ; then
  echo "Error! Code=$RET"
  exit $RET
fi
echo -e "finished.\n"

echo "systemctl stop mariadb.service"
systemctl stop mariadb.service
echo "rm -rdf /var/log/mysql/*"
rm -rdf /var/log/mysql/*
echo "systemctl restart mariadb.service"
systemctl restart mariadb.service
RET=$?
if [ $RET -ne 0 ] ; then
  echo "Error! Code=$RET"
  exit $RET
fi

echo "cp -a -v /home/weewx/bin/weeutil/weeutil.py-original /home/weewx/bin/weeutil/weeutil.py"
cp -a -v /home/weewx/bin/weeutil/weeutil.py-original /home/weewx/bin/weeutil/weeutil.py
RET=$?
if [ $RET -ne 0 ] ; then
  echo "Error! Code=$RET"
  exit $RET
fi

echo "systemctl restart weewx.service"
systemctl restart weewx.service
RET=$?
if [ $RET -ne 0 ] ; then
  echo "Error! Code=$RET"
  exit $RET
fi

echo "END: $(date)"
