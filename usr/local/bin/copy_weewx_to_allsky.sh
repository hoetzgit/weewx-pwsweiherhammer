#!/bin/bash

BROKER="mqtt.fritz.box"
PORT=1883
TOPIC="weewx-mqtt/loop"
OUTPUT_FILE1="/mnt/Daten/weewx/weewx.json"
OUTPUT_FILE2="/home/weewx/public_html/data/weewx.json"
OUTPUT_FILE3="/home/weewx/public_html/data/weewx_mlx90614.json"
OUTPUT_TEST="/mnt/Daten/weewx/weewx.tmp"
CLIENT_ID="weewx_to_allsky"
LOCK_FILE="/tmp/weewx_to_allsky.lock"
USERNAME="weewx"
PASSWORD="weewx"
QOS=1
SLEEPTIME=60
LOGLEVEL=4

# Funktion zum Abfangen des SIGINT-Signals (CTRL + C) und SIGTERM (z.B. kill -15)
handle_stop() {
    echo ""
    echo "$(get_formatted_date) - Skript wird beendet."
    remove_lockfile
    exit 0
}

# Signal-Handling für SIGINT (CTRL + C) und SIGTERM (z.B. kill -15) registrieren
trap handle_stop SIGINT SIGTERM

# Funktion zur Formatierung des Datums
get_formatted_date() {
    date +'%d.%m.%Y %H:%M:%S'
}

# Logausgaben
log() {
  local loglevel=$1
  local logclass=$2

  class="unknown"
  if [ "$logclass" == "I" ] || [ "$logclass" == "i" ]; then
    class="   INFO:"
  fi
  if [ "$logclass" == "W" ] || [ "$logclass" == "w" ]; then
    class="WARNING:"
  fi
  if [ "$logclass" == "E" ] || [ "$logclass" == "e" ]; then
    class=" ERROR:"
  fi
  shift 2

  if [ "$loglevel" -le "$LOGLEVEL" ]; then
    echo "$(get_formatted_date): $class $@"
  fi
}

# Überprüfung der Erreichbarkeit des Brokers
check_broker_reachability() {
    if ping -c 1 "$BROKER" &> /dev/null; then
        echo "$(get_formatted_date) - Der Mosquitto-Broker ist erreichbar."
        return 0
    else
        echo "$(get_formatted_date) - Der Mosquitto-Broker $BROKER ist nicht erreichbar."
        return 1
    fi
}

# Überprüfung der Topic-Existenz
check_topic_existence() {
    if mosquitto_sub -h "$BROKER" -p "$PORT" -t "$TOPIC" -C 1 -u "$USERNAME" -P "$PASSWORD" -q $QOS &> /dev/null; then
        echo "$(get_formatted_date) - Das Topic $TOPIC existiert."
        return 0
    else
        echo "$(get_formatted_date) - Das Topic $TOPIC existiert nicht."
        return 1
    fi
}

# Überprüfung der Schreibberechtigungen für die Datei
check_file_permissions() {
    if touch "$OUTPUT_TEST" &> /dev/null; then
        rm "$OUTPUT_TEST"
        echo "$(get_formatted_date) - Die Schreibberechtigungen für $OUTPUT_TEST sind vorhanden."
        return 0
    else
        echo "$(get_formatted_date) - Keine Schreibberechtigungen für $OUTPUT_TEST vorhanden."
        return 1
    fi
}

# Prüfung, ob eine gültige Lock-Datei vorhanden ist
check_valid_lockfile() {
    if [[ -f "$LOCK_FILE" ]]; then
        pid=$(cat "$LOCK_FILE")
        if [[ -n "$(ps -p "$pid" -o pid=)" ]]; then
            echo "$(get_formatted_date) - Das Skript ist bereits ausgeführt (PID: $pid)."
            echo "$(get_formatted_date) - Beenden Sie das Skript oder entfernen Sie die Lock-Datei, falls das Skript nicht ausgeführt wird."
            return 1
        else
            echo "$(get_formatted_date) - Ungültige Lock-Datei gefunden. Das Skript wird fortgesetzt."
            return 0
        fi
    fi
    return 0
}

# Erstellung der Lock-Datei
create_lockfile() {
    echo "$$" > "$LOCK_FILE"
    ret=$?
    if [ ${ret} -ne 0 ] ; then
      log 0 "E" "Lock-Datei konnte nicht erstellt werden! code=${ret}"
      return ${ret}
    fi    
    log 4 "I" "Lock-Datei erstellt (PID: $$)."
    return 0
}

# Entfernen der Lock-Datei
remove_lockfile() {
    pid=$(cat "$LOCK_FILE")
    rm -f "$LOCK_FILE"
    ret=$?
    if [ ${ret} -ne 0 ] ; then
      log 0 "E" "Lock-Datei konnte nicht gelöscht werden! code=${ret}"
      return ${ret}
    fi    
    log 4 "I" "Lock-Datei gelöscht (PID: $pid)."
    return 0
}

# MQTT Subscribe durchführen und empfangene Nachrichten in die Datei schreiben
subscribe_and_write_to_file() {
    while true; do
        if [[ -f "$OUTPUT_FILE1" ]]; then
            if [[ $(find "$OUTPUT_FILE1" -mmin +5) ]]; then
                echo "$(get_formatted_date) - $OUTPUT_FILE1 ist älter als 5 Minuten. Die Datei wird gelöscht."
                rm "$OUTPUT_FILE1"
            fi
        fi
        if [[ -f "$OUTPUT_FILE2" ]]; then
            if [[ $(find "$OUTPUT_FILE2" -mmin +5) ]]; then
                echo "$(get_formatted_date) - $OUTPUT_FILE2 ist älter als 5 Minuten. Die Datei wird gelöscht."
                rm "$OUTPUT_FILE2"
            fi
        fi
        if [[ -f "$OUTPUT_FILE2" ]]; then
            if [[ $(find "$OUTPUT_FILE3" -mmin +5) ]]; then
                echo "$(get_formatted_date) - $OUTPUT_FILE3 ist älter als 5 Minuten. Die Datei wird gelöscht."
                rm "$OUTPUT_FILE3"
            fi
        fi
        echo "$(get_formatted_date) - Warte auf Nachricht in Topic $TOPIC ..."
        mosquitto_sub -h "$BROKER" -p "$PORT" -t "$TOPIC" -i "$CLIENT_ID" -u "$USERNAME" -P "$PASSWORD" -q $QOS | while read -r line; do
            echo "$(get_formatted_date) - Nachricht von Topic $TOPIC empfangen."
            dateTime_timestamp=$(echo "$line" | jq -r '.dateTime')
            dateTime_formatted=$(date -d "@$dateTime_timestamp" "+%d.%m.%Y %H:%M:%S")
            echo "$dateTime_timestamp - $dateTime_formatted"

            if [[ "$line" == *'"cloudwatcher_skyTemp"'* && "$line" == *'"outTemp"'* ]]; then
                echo "$line" | python3 -m json.tool > "$OUTPUT_FILE1"
                echo "$(get_formatted_date) - Empfangene Nachricht wurde formatiert in $OUTPUT_FILE1 gespeichert."
            else
                echo "$(get_formatted_date) - Die Felder 'cloudwatcher_skyTemp' und 'outTemp' sind nicht im JSON-Inhalt vorhanden."
                echo "$(get_formatted_date) - Datei $OUTPUT_FILE1 wird nicht gespeichert."
            fi

            echo "$line" | python3 -m json.tool > "$OUTPUT_FILE2"
            echo "$(get_formatted_date) - Empfangene Nachricht wurde formatiert in $OUTPUT_FILE2 gespeichert."

            if [[ "$line" == *'"cloudwatcher_dateTime"'* && "$line" == *'"cloudwatcher_weathercode"'* ]]; then
                echo "$line" | python3 -m json.tool > "$OUTPUT_FILE3"
                echo "$(get_formatted_date) - Empfangene Nachricht wurde formatiert in $OUTPUT_FILE3 gespeichert."
            else
                echo "$(get_formatted_date) - Die Felder 'cloudwatcher_dateTime' und 'cloudwatcher_weathercode' sind nicht im JSON-Inhalt vorhanden."
                echo "$(get_formatted_date) - Datei $OUTPUT_FILE3 wird nicht gespeichert."
            fi

            echo "$(get_formatted_date) - Warte auf Nachricht in Topic $TOPIC ..."
        done
    done
}

# Hauptprogramm
if check_valid_lockfile; then
    create_lockfile
    while true; do
        if check_broker_reachability && check_topic_existence && check_file_permissions; then
            subscribe_and_write_to_file
        fi
        echo "$(get_formatted_date) - Warte nach Fehler $SLEEPTIME Sekunden und starte dann erneut ..."
        sleep $SLEEPTIME
    done
fi
