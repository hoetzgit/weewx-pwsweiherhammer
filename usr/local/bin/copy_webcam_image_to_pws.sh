#!/bin/bash
WEBCAM="http://192.168.0.133:88"
SNAPSHOT_CMD="${WEBCAM}/cgi-bin/CGIProxy.fcgi?usr=snapshot&pwd=snapshot4711&cmd=snapPicture2"
SNAPSHOT="webcam.jpg"
SNAPSHOT_SMALL="webcam_small.jpg"
SNAPSHOT_SMALL_SIZE="650x366"
SNAPSHOT_TMP_PATH="/tmp"
SNAPSHOT_COPYRIGHT=$(printf "\u00A9")
SNAPSHOT_PWS="PWS Weiherhammer"
SNAPSHOT_DATETIME=$(date '+%d.%m.%Y %H:%M:%S')
FONT="Nimbus-Sans"

SNAPSHOT_DEST_FOLDERS=(
"/var/www/html/pwsWD/img"
"/home/weewx/public_html/weiherhammer/images"
)

# Snapshot from Webcam
/usr/bin/curl --silent --connect-timeout 5 ${SNAPSHOT_CMD} -o ${SNAPSHOT_TMP_PATH}/${SNAPSHOT}
ls -rtl ${SNAPSHOT_TMP_PATH}/${SNAPSHOT}

# convert Snapshot
/usr/bin/convert ${SNAPSHOT_TMP_PATH}/${SNAPSHOT} -font ${FONT} \
-fill white -pointsize 25 -gravity NorthEast -annotate +5+5 "${SNAPSHOT_DATETIME}" \
-fill white -pointsize 15 -gravity SouthEast -annotate +5+5 "${SNAPSHOT_COPYRIGHT} ${SNAPSHOT_PWS}" \
${SNAPSHOT_TMP_PATH}/${SNAPSHOT}

/usr/bin/convert ${SNAPSHOT_TMP_PATH}/${SNAPSHOT} -resize ${SNAPSHOT_SMALL_SIZE} ${SNAPSHOT_TMP_PATH}/${SNAPSHOT_SMALL}

# copy Snapshots to dest
for DEST in ${SNAPSHOT_DEST_FOLDERS[@]}
do
  cp -fv ${SNAPSHOT_TMP_PATH}/${SNAPSHOT} ${DEST}/${SNAPSHOT}
  cp -fv ${SNAPSHOT_TMP_PATH}/${SNAPSHOT_SMALL} ${DEST}/${SNAPSHOT_SMALL} 
done

# remove tmp Snapshots
rm -fv ${SNAPSHOT_TMP_PATH}/${SNAPSHOT}
rm -fv ${SNAPSHOT_TMP_PATH}/${SNAPSHOT_SMALL}

exit 0

