#!/bin/bash
SNAPSHOT_SMALL_SIZE="480x360"
CONVERT_CMD="/usr/bin/convert"
PING_CMD="/usr/bin/ping -c4 -W1"
TOUCH_CMD="/usr/bin/touch"
RM_CMD="/usr/bin/rm -vf"
CP_CMD="/usr/bin/cp -vf"
CONVERT_CMD="/usr/bin/convert -verbose -resize ${SNAPSHOT_SMALL_SIZE}"

ALLSKY_CAMS=(
"01"
)

SNAPSHOT_DEST_FOLDERS=(
"/var/www/html/pwsWD/img"
"/home/weewx/public_html/weiherhammer/images"
)

# AllSky image to dest
for CAM in ${ALLSKY_CAMS[@]}
do
  ALLSKY_IMAGE_PATH="/mnt/Daten/allskycam${CAM}/www/html/allsky-website"

  for DEST in ${SNAPSHOT_DEST_FOLDERS[@]}
  do
    ${CP_CMD} ${ALLSKY_IMAGE_PATH}/image.jpg ${DEST}/allskycam${CAM}.jpg
    ${CONVERT_CMD} ${ALLSKY_IMAGE_PATH}/image.jpg ${DEST}/allskycam${CAM}_small.jpg
  done
done

# AllSky online status to dest
ALLSKY_CAMS=(
"01"
)
HEALTH_DEST_FOLDERS=(
"/home/weewx/skins/Weiherhammer/allsky"
)

for CAM in ${ALLSKY_CAMS[@]}
do
  for DEST in ${HEALTH_DEST_FOLDERS[@]}
  do
    ${PING_CMD} allskycam${CAM}.fritz.box && \
    (${RM_CMD} ${DEST}/allskycam${CAM}.down >/dev/null 2>&1 ; \
    ${TOUCH_CMD} ${DEST}/allskycam${CAM}.up) || (${RM_CMD} ${DEST}/allskycam${CAM}.up >/dev/null 2>&1 ; ${TOUCH_CMD} ${DEST}/allskycam${CAM}.down)
  done
done
