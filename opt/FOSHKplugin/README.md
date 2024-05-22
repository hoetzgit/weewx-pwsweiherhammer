# generic Plugin: FOSHKplugin
# for english docs check https://foshkplugin.phantasoft.de/generic/

Dieses Plugin bindet verschiedene Wetterstationen bzw. -sensoren des Hersteller Fine Offset Electronics (FOSHK) an beliebige Smarthome-Systeme über UDP an.

Entwickelt wurde das Plugin für und mit einem Gateway Froggit DP1500 das auch unter dem Namen Ecowitt GW1000 verkauft wird.
Zu den unterstützen Sensoren gehören derzeit Innen-Temperatur/Luftfeuchte-, Bodenfeuchte- und PM 2.5 Luftqualitätssensoren sowie verschiedene All-In-One Außenmessstationen für Temperatur, Luftfeuchte, Windgeschwindigkeit, Windrichtung, Niederschlag, Licht und UV.

Das Plugin unterstützt pro Installation (Instanz) eine Wetterstation mit allen aktuell verfügbaren Sensoren.

nähere Informationen unter http://foshkplugin.phantasoft.de

## Installation und Konfiguration
Verzeichnis erzeugen
sudo mkdir /opt/FOSHKplugin

in das erzeugte Verzeichnis wechseln
cd /opt/FOSHKplugin

aktuelle Version des Plugins per wget holen
wget -N http://foshkplugin.phantasoft.de/files/generic-FOSHKplugin.zip
oder
curl -O https://foshkplugin.phantasoft.de/files/generic-FOSHKplugin.zip

ZIP-File entpacken
unzip generic-FOSHKplugin.zip

Start-Rechte für Script vergeben:
chmod 711 -v generic-FOSHKplugin-install.sh

generic-FOSHKplugin-install.sh (dieses Script) ausführen
sudo ./generic-FOSHKplugin-install.sh --install

## Upgrade-Installation
Um die vorhandene Konfiguration bei einer erneuten Installation zu erhalten, ist das Script mit dem Parameter --upgrade auszuführen:

sudo ./generic-FOSHKplugin-install.sh --upgrade

Diese Funktion holt die letzte Version des ZIP-Files vom Server, sichert die aktuelle Konfiguration, packt das ZIP aus und stellt die ursprüngliche Konfiguration wieder her.
Zusätzlich wird der Dienst (so aktiv) neugestartet.

## Dienst stoppen & entfernen

sudo ./generic-FOSHKplugin-install.sh --uninstall

Alle Dateien bleiben dabei erhalten. Es wird nur der systemd-Dienst gestoppt und deaktiviert.

## Feedback und Diskussion
Das PlugIn wird von mir aktiv genutzt und weiterentwickelt und ich freue mich über Anregungen und Feedback. Hierzu habe ich im Loxforum einen Thread eröffnet:

<a href="https://www.loxforum.com/forum/projektforen/loxberry/plugins/222662">https://www.loxforum.com/forum/projektforen/loxberry/plugins/222662</a>

## Rechtliche Hinweise
Ich übernehme keine Garantien hinsichtlich des Einsatzes dieser Software - die Nutzung geschieht auf eigene Gefahr. 
Treffen Sie Entscheidungen die zu Personen- oder Sachschäden führen können niemals auf Grundlage dieser Software.
Durch das Programm generierte Warnungen (z.B. Sturm oder Gewitter) können eintreffen. Das Fehlen dieser Warnungen impliziert jedoch nicht, dass diese Dinge nicht möglich sind.

Oliver Engel, 13.06.2022
http://foshkplugin.phantasoft.de
FOSHKplugin@phantasoft.de

## Change-Log
- 2019-12-15 Release v0.01  erste öffentliche Version
- 2019-12-28 Release v0.02  ### aus FWD-Log-Nachricht entfernt
                            Umrechnung temp1f in temp1c für Innensensor auf Kanal 1 implementiert
                            Timeout bei sendReboot, setWSconfig und getWSINTERVAL von 1 auf 2 Sekunden erhöht (somit sollte WS-Set sicherer funktionieren)
                            Probleme beim Setzen der Wetterstationsparameter via WS-Set behoben (Id & Key werden - wenn nicht schon vorhanden - gesetzt)
- 2020-01-18 Release v0.03  USE_METRIC wieder funktional (jetzt also auch imperiale Werte per UDP und CSV möglich)
                            weitere mögliche Probleme beim Setzen der Wetterstationsparameter via WS-Set behoben (Path wird nun immer auf defaults gesetzt)
                            Prüfung der nutzbaren LoxBerry-Ports (http/udp) optimiert
                            Kommunikation mit der Wetterstation überarbeitet - nun jeweils 5 Versuche bei Lesen und Schreiben
                            besseres Logging/Debugging bei Fehlern bei Set-WS; "buntere" und besser parse-bare Log-Files; ### entfernt
                            generic: conf-File - Vorlage und Hilfstexte überarbeitet
                            Ignorierliste Forward\FWD_IGNORE für Forwards eingebaut: definiert - kommasepariert - Felder, die NICHT verschickt werden sollen
                            Forward\FWD_TYPE=WU/UDP/EW/RAW für http-Forward der Werte (UDP-Ausgabezeile) an andere Ziele als WU eingeführt
                            nun bis zu 10 Forwards mit unterschiedlichen Einstellungen möglich
                              aktuell nur im Config-File zu pflegen: Forward-1..9 analog zu Forward
                            Watchdog: kommen seit 3*eingestelltem Intervall keine Werte von der Wetterstation, Fehler melden!
                              es erfolgt EINE Warnung und bei erneuter Übermittlung der Wetterstation eine Entwarnung im Log sowie per UDP:
                              SID=FOSHKweather wswarning=1 last=346611722
                              SID=FOSHKweather wswarning=0 last=346616459
                              standardmäßig aktiv; kann im Config-File deaktiviert werden: Warning\WSDOG_WARNING=False
                              Intervall kann im Config-File eingestellt werden: Warning\WSDOG_INTERVAL=3
                            Alarm senden (Log, UDP) wenn Sensor (auch mehrere) keine Daten liefert (etwa weil Akku/Batterie leer)
                              SID=FOSHKweather sensorwarning=1 missed=wh65batt time=347196201
                              SID=FOSHKweather sensorwarning=1 back=wh65batt time=347196201
                              aktuell nur im Config-File zu pflegen:
                            Sturmwarnung: fällt oder steigt der Luftdruck um mehr als 1.75 Hektopascal in einer Stunde, erfolgt eine Warnung vor Starkwind/Sturm
                              vgl. http://www.bohlken.net/luftdruck2.htm
                              es erfolgt EINE Warnung und bei Entspannung des Luftdrucks eine Entwarnung im Log und per UDP:
                              SID=FOSHKweather stormwarning=1 last=346611722
                              SID=FOSHKweather stormwarning=0 last=346616459
                              standardmäßig aktiv; kann im Config-File deaktiviert werden: Warning\STORM_WARNING=False
                              WarnDiff kann im Config-File eingestellt werden: Warning\STORM_WARNDIFF=1.5
                            Vorbereitung Wassersensor WH55 und Blitzsensor WH57 (noch unklar ob lightning_time = timestring oder unixtime!)
                            UDP-Versand an das Zielsystem lässt sich mit UDP_ENABLE=False abschalten
                            Ignorierliste für den UDP-Versand eingeführt: Config\UDP_IGNORE (nur im Config-File zu pflegen)
- 2020-02-20 Release v0.04  default-config angepasst - Kommentare hinter Block nicht zulässig!
                            myDebug für zusätzliche Debug-Informationen auch im Python-Programm implementiert
                            Beschreiben der Wetterstation via WS-Set sollte nun (endlich) vollumfänglich funktionieren
                            Id & Key in den Einstellungen der Wetterstation werden ignoriert und nicht vom Plugin überschrieben
- 2020-04-26 Release v0.05  Sturmwarnung bleibt für 60 Minuten nach letzer Grenzwertunter-/überschreitung aktiv; Zeitraum kann via STORM_EXPIRE im Config-File angepasst werden
                            Übermittlung des UV-Wertes im WU-Format angepasst, nun in Großbuchstaben UV= statt uv=
- 2020-07-20 Release v0.06  Gewittererkennung/-warnung implementiert - sendet bei vorhandenen Blitzsensor WH57/DP60 Gewitterwarnung
                            Überarbeitung der Sturmwarn-Funktion, Ausgabe der Luftdrucktendenz 1h/3h sowie Änderung des Luftdrucks 1h/3h
                            WU-Forward von AqPM2.5 wenn Feinstaubsensor vorhanden (nur pm25_ch1 wird weitergeleitet!)
                            AQI-Berechnung bei EVAL_DATA=True und vorhandenem DP200/WH41/43 aktiviert
                            experimentell: Forward des PM2.5-Wertes zu luftdaten.info als Typ LD, Angabe der ID unter FWD_SID im Config-File nötig
                            Batterie-Warnung per Log und UDP implementiert; fällt der mitgelieferte batt-Wert unter einen intern definierten Schwellwert, erfolgt eine Warnung
                            Fehler bei Ausgabe des Namens des wieder Daten liefernden Sensors (SENSOR_MANDATORY) behoben
                            Sprachen NL/FR/ES/SK für WetterNow, WetterPrognose hinzugefügt
                            Status der Warnungen für Sturm, Gewitter, Sensor und Batterie werden zwischengespeichert und sind somit remanent
                            WU-Forward/JSON Umbenennung von solarRadiation zu solarradiation
                            WU-Forward/JSON Unterstützung von Bodenfeuchtesensoren
                            WU-Forward: keys mit leerem value werden nicht übermittelt
                            WU-Forward: Upload von dewptf (war dewpt) und rainin (war rainratein) repariert
                            neue Formel für Taupunkt-Berechnung (dewpoint) aktiv (erfordert math)
                            sendet nun bei http-Empfang der Daten einen response-code 200 zum Sender
                            UDP-Nachricht für time bei wswarning von "time: " auf "time=" geändert
                            bei allen get/post-Aktionen: Prüfung des Rückgabewertes 200..202 --> ok (war 200)
                            Text-Fehler in Hilfe behoben
                            Aktualisierung der generic-FOSHKplugin-install.sh; Fehler beim Erzeugen der conf-Datei behoben
                            Forward der Eingangsdaten ohne Konvertierung per UDP als Typ RAWUDP möglich
                            Forward der Eingangsdaten ohne Konvertierung per EW/POST als Typ RAWEW möglich
                            Forward der Eingangsdaten ohne Konvertierung per POST als Typ RAWCSV möglich
                            Forward der Ausgabedaten per UDP als Typ UDP möglich
                              ### Achtung! bisheriger Forward-Type UDP heisst nun UDPGET ###
                            Forward der Ausgabedaten als CSV als Typ CSV möglich
                            Timeout-Handling bei Forward angepasst (nun 3 Sekunden)
                            Ausgabesprache kann per LANGUAGE=DE/EN etc. im Config-File eingestellt werden
                            Plugin kann per UDP-Befehl beendet werden und den aktuellen Status senden (Plugin.shutdown, Plugin.getStatus implementiert)
                            Debug-Modus zur Laufzeit änderbar über UDP-Befehle Plugin.debug=enable/disable
                            Separator bei http-GET /RAW auswählbar
                            neue http-GET-Ausgabe /STRING zur Ausgabe der Ausgabezeile mit wählbaren Separator
                            im JSON und bei der Ausgabe per STRING und UDP können nun auch die Statusmeldungen abgefragt werden
                            einfache Authentifizierung per AUTH_PWD implementiert; Daten und Anfragen werden per http nur angenommen, wenn dieser String in der URL enthalten ist
                            Inhalt von PASSKEY wird in Logfiles maskiert wenn AUTH_PWD aktiv
                            Behandlung von unnötigen Hochkommas im Config-File angepasst
                            Vorbereitung für kommenden Boden/Wasser-Temperatursensor WH34 (tf_chNc, tf_battN - wobei N=1..8)
                            Status auch via http/GET abfragbar: http://ipadresse:portnummer/FOSHKplugin/status gibt Status wswarning, sensorwarning, batterywarning, ... aus
                            fake-Modus implementiert: Werte eines Innensensors (WH31/DP50) können als Werte eines Außensensors WH32 ausgegeben werden (Temperatur, Luftfeuchte)
                            updatewarning implementiert, meldet per Log/UDP und ggf. per http ein verfügbares Update für die Wetterstation
                            für Gewitterwarnung wird nun tswarning statt tstormwarning als Status ausgegeben
                              ### Achtung! dies betrifft sämtliche Ausgaben sowohl per UDP als auch per http
- 2021-02-19 Release v0.07  Fehler bei IGNORE_EMPTY behoben: UDP-Versand an Loxone funktionierte nicht, wenn IGNORE_EMPTY deaktiviert war
                            Log-Ausgaben: "custom mode" umbenannt nach "custom server"
                            Fehlerbehebung Gewitterwarnung (nicht jedes Gewitter wurde gemeldet)
                            Fehlerbehebung: known issue bzgl. socket-Problemen und Chrome - nach 5 Sekunden sollte der socket wieder freigegeben werden
                            Fehlerbehebung: Programmfehler bei PM2.5-Werten oberhalb von 500 behoben
                            Fehlerbehebung: Behandlung von %20 im Feld dateutc (etwa von der WH2600 LAN) eingeführt
                            Config-parsing hinsichtlich Boolean-Werten robuster gestaltet (mkBoolean)
                            sendet nun bei http-Empfang der Daten neben dem response-code 200 auch den Text OK zum Sender
                            Forwards können nun im Config-File aktiviert/deaktiviert (FWD_ENABLE=True/False) und kommentiert werden (FWD_CMT)
                            Multi-Instanz: mehrere Instanzen von FOSHKplugin können nun parallel - in unterschiedlichen Verzeichnissen - betrieben werden
                              über DEF_SID im Config-File kann die Kennung für ausgehende UDP-Nachrichten geändert werden (default: FOSHKweather)
                            Unterstützung des Ambient Weather-Formats sowohl für eingehende Nachrichten als auch als Forward (AMB/RAWAMB)
                              bei Fehlen von yearlyrainin wird totalrainin und bei Fehlen von rainratein wird hourlyrainin genutzt
                            Forward der Eingangsdaten im Weathercloud-Format per GET als Typ WC möglich
                            Forward der Eingangsdaten im Meteotemplate-Format per GET als Typ MT möglich
                            Forward der Eingangsdaten im Awekas-Format per GET als Typ AWEKAS möglich
                            Vorbereitung WH45 (PM25, PM10, CO2-Sensor)
                            Vorbereitung für den neuen Blattfeuchtesensor WN35
                            AQI-Berechnung bei EVAL_DATA=True und vorhandenem WH45 aktiviert
                              keys: co2lvl, pm25_AQI_co2, pm25_AQIlvl_co2, pm25_AQI_24h_co2, pm25_AQIlvl_24h_co2, pm10_AQI_co2, pm10_AQIlvl_co2, pm10_AQI_24h_co2, pm10_AQIlvl_24h_co2
                            Gewitterentwarnung: Anzahl der Blitze (lcount) sowie min. und max. Entfernung (ldmin und ldmax) werden übermittelt 
                            Verbesserung hinsichtlich TimeOut-Verhalten; http hat nun einen TimeOut von 5 und UDP von 3 Sekunden
                            Ecowitt-Forward: ist totalrain vorhanden - yearlyrain aber nicht, wird yearlyrain automatisch mit Wert von totalrain gesetzt
                            neue Konfigurationsoption Export\OUT_TIME = True setzt Zeitstempel eingehender Nachrichten von der Wetterstation auf Empfangszeit
                            fake-Modus nun auch für eingehende Nachrichten im WU- und Ambient-Format aktiviert
                            ein automatischer Restart bei ausbleibenden Daten der Wetterstation über Warning\WSDOG_RESTART konfigurierbar
                            Leckage-Warnung implementiert - bei vorhandenen WH55/DP70 und Aktivierung von Warning\LEAKAGE_WARNING erfolgen entsprechende Warnungen im Log sowie per UDP/http oder Pushover (leakwarning) wenn eine Leckage erkannt wurde
                            wichtige Status-Mitteilungen können nun zusätzlich per Pushover übermittelt werden (Update-, Sensor-, Watchdog-, Batterie-, Sturm-, Gewitter- und Leckagewarnung)
                              Anleitung:
                              1. App Pushover aus dem jeweiligen Store holen
                              2. App Pushover starten und credentials vergeben
                              3. per Webbrowser anmelden: https://pushover.net/login
                              4. Key unter "Your User Key" notieren, das ist bei PO_USER anzugeben
                              5. unter "Your Applications" einen API-Token für FOSHKplugin erzeugen - dieser Schlüssel ist unter PO_TOKEN anzugeben
                              6. Config foshkplugin.conf anpassen: Pushover\PO_ENABLE=True Pushover\PO_USER="Your User Key" und Pushover\PO_TOKEN=API-TOKEN eintragen
                              7. FOSHKplugin neustarten
                            generic: Anzeige aller erkannten Wetterstationen während Installation via generic-FOSHKplugin-install.sh sowie ./foshkplugin.py -scanWS
                            Mittelwertberechnung (bei EVAL_DATA=True) für Wind und Windrichtung implementiert, gibt windspdmph_avg10m, winddir_avg10m aus
                            Böen-Maximum der letzten 10 Minuten implementiert: windgustmph_max10m/windgustkmh_max10m gibt die max. Böe in den letzten 10 Minuten aus
                            Ausgabe des Lux-Wertes (solarradiation*126.7) als Feld brightness (bei EVAL_DATA=True)
                            mit Logging\IGNORE_LOG lassen sich Zeilen vom Logging im Standard-Log ausnehmen (Komma-getrennte Liste von Suchworten) - etwa crondaemon
                            mit FWD_EXEC lässt sich bei jedem Forward ein Script angeben, dass mit dem Ausgabestring als Parameter gestartet wird und dessen letzte Ausgabezeile als neuer Ausgabestring für den Versand übernommen wird
                            Wert-Abfrage: ein http-Request http://ipadresse:portnummer/getvalue?key=[key] gibt den Wert für den Schlüssel [key] aus, wobei der Schlüssel der RAW-Schlüssel wie auch der umgewandelte Schlüsselname sein darf
                              Beipiel: curl http://192.168.15.236:8080/getvalue?key=windspeedmph gibt den Wert "1.34" des Schlüssels windspeedmph aus
                              in Verbindung mit FWD_EXEC können somit Daten anderer Instanzen abgefragt und eingebunden werden
                            zusätzlich zur http-GET-Abfrage /CSV und /CSVHDR mit dynamischer Feldeinteilung wird nun auch /SSV und /SSVHDR mit statischen Feldern unterstützt, Grundlage ist die Feldbeschreibung in CSV\CSV_FIELDS
                              somit ist Reihenfolge der Felder fix; Felder ohne Inhalt (etwa bei Sensorausfall) werden nicht übersprungen sondern als "" ausgegeben
                            Prüfung der Datei-Rechte mit entsprechender Fehlermeldung in generic-FOSHKplugin-install.sh
                            ist Export\FIX_LIGHTNING aktiv (default) werden bei fehlenden Werten für lightning und lightning_time die letzten bekannten Werte als Eingangsdaten genutzt
                              da die Blitz-Daten im GW1000/DP1500 nicht im NVRAM gespeichert werden, gehen diese Werte bei einem Neustart des Geräts verloren
                              FOSHKplugin speichert Zeit und Entfernung des letzten übertragenen Blitzes im Config-File ab und nutzt diese, wenn keine Werte vom Blitzsensor übermittelt werden
                              diese Werte werden allen Ausgangsformaten zur Verfügung gestellt
                            bei jedem erfolgreichen Start wird ein Backup der foshkplugin.conf angelegt (foshkplugin.conf.foshkbackup)
                            Übersichtsseite http://ipadresse:portnummer/ gibt bei Zusatz von "?units=e" auch im amerik. Einheitensystem aus; kombinierbar mit "/status"
                              Beispiel: http://ipadresse:portnummer/status?units=e gibt den letzten Datensatz inkl. Status mit den amerikanischen Einheiten als html-Seite aus
- 2021-06-27 Release v0.08  kleinere Fehlerbehebungen und Optimierungen
                            besseres Logging im Sende-Log: Nummer des Forwards wird mitprotokolliert um fehlerhaften Block im Config-File leichter finden zu können
                            flexiblerer Firmware-Update-Check (duplicate options)
                            erhöhte Sende-Sicherheit bei http-Forwards durch Sendungswiederholung:
                              jetzt erfolgen 3 Versuche, die Daten zuzustellen; der zweite Versuch findet nach 5 und der dritte nach weiteren 10 Sekunden statt
                              die Wiederholung erfolgt jedoch nicht, wenn der Rückgabecode auf einen lokalen Fehler hinweist (400..499)
                            Unterstützung des Forward per MQTT sowohl für metrische Werte (FWD_TYPE=MQTTMET) als auch für imp. Werte (FWD_TYPE=MQTTIMP)
                              erfordert python3-setuptools und paho-mqtt  (wird automatisch installiert)
                              MQTT-Broker muss in FWD_URL definiert werden: ipaddress:port@hierarchy%prefix - topic name ist der Name des Keys
                            Unterstützung der wetter.com-API (noch unter weewx-Pseudonym)
                            Unterstützung der weather365.net API
                            Unterstützung der wettersektor.de API
                            Exportmöglichkeit der Daten als realtime.txt und clientraw.txt per file, http(s), ftp(s) mit FWD_Typ = REALTIMETXT bzw. CLIENTRAWTXT
                              dabei legt die FWD_URL fest, ob die Datei per http(s) geposted, per ftp(s) übertragen oder als Datei abgelegt werden soll
                              ein realtime.txt-kompatibler String kann per http://ipadresse:portnummer/realtime.txt abgefragt und gespeichert werden
                              ein clientraw.txt-kompatibler String kann per http://ipadresse:portnummer/clientraw.txt abgefragt und gespeichert werden
                            Speicherung als WSWin-kompatible CSV-Datei wswin.csv zum automatischen Import durch WSWin per Dateiüberwachung
                              der Speicherort muss per Samba-Freigabe für Windows-Rechner lesbar (ggf. schreibbar) sein
                              der Import kann durch WSWin automatisch und auch unregelmäßig erfolgen - WSWin liest einfach alle bisher noch nicht verarbeiteten Zeilen ein
                              dabei ist keine X-CSV nötig
                            min/max-Werte sowie Zeiten werden für den aktuellen Tag protokolliert und bei Änderungen auch per UDP versandt, wenn Export\UDP_MINMAX = True (default)
                              betrifft die Keys tempc_min, tempc_min_time, tempc_max, tempc_max_time sowie mit gleichem Aufbau für windchillc, heatindexc, tempinc, baromrelhpa, 
                              feelslike, dewptc, humidity, windspeedkmh, windgustkmh
                              Achtung! alle Werte im metrischen System, Zeit ist jeweils Unixtime der Lokalzeit (bei UDP als Loxone-Zeit)
                            Loxone-Version: FWD_PWD kann für Forward über das Web-Interface eingegeben werden
                            Unterstützung der erweiterten Temperatur/Feuchte-Sensoren bei WU-Abfragen (/observations/current/json/units=m bzw. e)
                            Berechnung der Wolkenhöhe cloudf (in feet) cloudm (in Meter) implementiert, Coordinates\ALT = True im Config-File mit Höhe über NN in Metern nötig - erfordert EVAL_VALUES = True
                            Sonnenscheindauer sunhours implementiert - zeigt die Dauer der täglichen Sonnenscheindauer in Stunden an (solarradiation >= 120W/m²) - erfordert EVAL_VALUES = True
                            sunhours, co2 und leafwetness (für den kommenden WN34) in Meteotemplate unterstuetzt; sunhours auch bei Awekas-API
                            Koordinaten können unter Coordinates\ALT, LAT, LON konfiguriert werden
                              ALT wird zur Ermittlung der Wolkenhöhe genutzt (spread * 122)
                              LAT/LON werden nur zur Übertragung in die Exportformate Awekas-API, clientraw.txt und Weather365.net genutzt
                            Config\UDP_MAXLEN (default=2000) legt maximale Länge eines UDP-Datagrams fest 
                              Ist die Länge des zu sendenden Paketes größer als festgelegt wird das Paket in mehrere Datagramme aufgeteilt, die jeweils eine ungefähre Länge UDP_MAXLEN haben und den Identifier SID=DEF_SID am Anfang jedes Datagrams enthalten.
                              Dabei wird die Ursprungszeile aber so getrennt, dass die key=value-Zuordnung erhalten bleibt - die Trennung erfolgt also immer HINTER UDP_MAXLEN beim nächsten Auffinden eines Leerzeichens.
                              Werte mit enthaltenen Leerzeichen werden durch doppelte Anführungsstriche eingefasst, damit man auf UDP-Serverseite eine Möglichkeit zum Parsen hat.
                              Beispiel neighborhood="Hohen Neuendorf" bei einem Wert mit Leerzeichen - jedoch neighborhood=Berlin (ohne Leerzeichen)
                            neue Forward-Typen CSVFILE und TXTFILE - Ausgabe der Werte aus CSV-Datei (mit Keys) oder Text (mit Keys, zeilenweise) - Datei wird jeweils überschrieben
                            anpassbares Logging-Level - weniger Logging mit Blick auf das Wesentliche
                              über Logging\LOG_LEVEL im Config-File lässt sich nun das Logging feinjustieren - bei
                              - ALL werden wie bisher alle Zeilen protokolliert
                              - INFO - alle Zeilen außer ERROR, WARNING, INFO und OK werden ausgeblendet
                              - WARNING - alle Zeilen au0er ERROR und WARNING und OK werden ausgeblendet
                              - ERROR - nur Zeilen mit ERROR und OK werden ausgegeben
                              aus Kompatibilitätsgründen ist ALL voreingestellt - ich empfehle jedoch LOG_LEVEL INFO - somit wird alles, was nicht problemlos erfolgreich war, protokolliert
                            LOG_LEVEL lässt sich auch im Betrieb per http://ipadresse:port/FOSHKplugin/loglevel=[ALL,INFO,WARNING,ERROR] anpassen - bei Neustart gilt jedoch wieder der im Config-File eingestellte Wert
                            mit Logging\LOG_ENABLE = False lässt sich das Logging global abschalten, ohne Änderungen an den Logfile-Namen vorzunehmen (default = True)
                            mit Warning\CO2_WARNING = True kann eine Warnung (per UDP, http, Log, Pushover) aktiviert werden, wenn der CO2-Messwert höher als der unter Warning\CO2_WARNLEVEL konfigurierte liegt
                            mit Config\UDP_STATRESEND = n kann eine Zykluszeit (Sekunden) definiert werden, in der die Warnmeldungen unabhängig von Statusänderungen versandt werden
                            Änderung bei ptrend1 und ptrend3 - bei starkem Anstieg oder Abfall des Luftdrucks (+0.7/-0.7 bzw. +2/-2) wird als Trend eine 2 bzw- -2 ausgegeben
                            ptrend1, pchange1, ptrend3 und pchange3 werden nun auch per Ecowitt (Type=EW) weitergeleitet, wenn EVAL_VALUES = True
                              pchange1 und pchange3 enthalten dabei die Differenz zwischen dem aktuellen Wert und dem Wert von vor 1 oder 3 Stunden in inHg
                            mit CSV\CSV_DAYFILE = /path/to/filename.csv wird die Erstellung eines Tages-CSV /path/to/filename.csv mit den min/max-Werten des Tages aktiviert
                            Parameter bool, status, units und separator sind nun bei allen Request möglich (soweit sinnvoll - bei RAW also nicht)
                            Abfrage /JSON erweitert - erzeugt bei Abruf mit Parameter bool ein JSON mit numerischen/boolschen Werten - kann mit minmax, status und units erweitert werden
                              Beispiel: http://ipadresse:portnummer/JSON?minmax&status&bool gibt den letzten Datensatz mit numerischen/boolschen Werten statt mit Strings aus
                            MQTTMET/MQTTIMP-Forward gibt nun numerische/boolsche Werte aus
                            InfluxDB-Unterstützung: sowohl per pull (als JSON via telegraf) als auch nativ (FWD_TYPE = INFLUXMET/INFLUXIMP) integriert
                              die Angabe der Datenbank erfolgt in der FWD_URL-Zeile: FWD_URL = http://192.168.15.237:8086@Database erzeugt eine Datenbank Database auf 192.168.15.237:8086
                              und überträgt die Daten unverschlüsselt im konfigurierten Intervall; Nutzername und Password können per FWD_SID und FWD_PWD übergeben werden
                            neue Config-Optionen REBOOT_ENABLE und RESTART_ENABLE - ermöglichen den Neustart der Wetterstation und von FOSHKplugin per http/UDP
                            neuer Forward-Typ RAWTEXT ermöglicht die Ablage der eingehenden Werte der Wetterstation als Textdatei lokal im Dateisystem und remote per http(s)/POST und ftp(s)
                            Firmware-Update-Status (updatewarning) wird nun sofort nach Eingang neuer Daten der aktualisierten Wetterstation aktualisiert
                            leicht verbesserte Installationsroutine generic-FOSHKplugin-install.sh - Klarstellung von UDP-Server und -Port, Abfangen fehlerhafter URL-Dateinamen beim Update
                            Anpassung für WH6006 (dateutc mit "%3A" statt ":", indoorhumidity)
- 2022-03-05 Release v0.09  kleinere Fehlerbehebungen und Optimierungen
                            intensives Code-Cleaning - Umbenennung und Vereinheitlichung der Konvertierfunktionen
                            Installationsscript generic-FOSHKplugin-install.sh angepasst - nun besser erklärt und Zugriffsrechte auf Dateien sollten passen
                            Fehler bei eingehenden Daten im WU-Protokoll und aktiviertem EVAL_VALUES behoben
                            Fehler behoben: UDP_MAXLEN zur Festlegung der max. Länge eines UDP-Datagramms wurde nicht beachtet
                            http-Anfragen mit &refresh=n aktualisiert die angezeigte Seite alle n Sekunden
                              Beispiel: http://ipadresse:portnummer/APRS&refresh=30 aktualisiert die Anzeigeseite des APRS-Ausgabestrings alle 30 Sekunden
                              oder: http://ipadresse:portnummer/status&minmax&refresh=60 zeigt die aktuellen Werte inkl. Status und Min/Max an und aktualisiert alle 60 Sekunden
                            bei eingehenden Daten im WU-Format barominrelin mit baromrelhpa gleichsetzen, Konvertierung von WU nach EW für WH6006 modifiziert
                            WH45-Kompatibilität für Ambient Weather (AQIN) sichergestellt
                            Kompatibilität zu GW1100 sichergestellt
                            interner WU-Server: WN34- und WN35-Kompatibilität hergestellt
                            bei Konvertierung nach Ambient Weather wird wh80batt korrekt auf battout gesetzt
                            bessere Protokollierung für FWD_EXEC - FWD-Nummer wird für bessere Zuordnung protokolliert; Anzeige einer Änderung erfolgt nur bei tatsächlicher Änderung
                            Blattfeuchte-Level für Meteotemplate, WC, Awekas, Weather365 und WSWin - statt 0..99 wird nun als Level 0..15 (float) gesendet
                            alternative Namen für RAWEW (EWRAW), RAWUDP (UDPRAW), RAWCSV (CSVRAW), AMBRAW (RAWAMB) und TXTFILE (TEXTFILE) eingeführt
                            in der FWD_URL kann nun für Ausgabeformate REALTIMETXT, CLIENTRAWTXT, CSVFILE, WSWIN, TXTFILE und RAWTEXT auch ein Dateiname übergeben werden
                            bei Erzeugung der WSWin-CSV erfolgt nun auch per http(s)/POST und ftp(s) ein Anhängen neuer Daten an die bereits vorhandene Datei (append)
                            neue, verbesserte Sonnenstundenberechnung sunhours (nach https://github.com/Jterrettaz/sunduration) mit dynamischen, ortsabhängigen Schwellwert (vielen Dank Werner!), erfordert Coordinates\LAT und Coordinates\LON
                              ohne LAT/LON oder bei Sunduration\SUN_CALC = False wird die bereits bekannte Berechnung mit fixem Schwellwert von 120W/m² genutzt
                              kann mit Sunduration\SUN_MIN (minimaler Schwellwert, default=0) und Sunduration\SUN_COEF (default=0.8 - zu wenig Sonnenschein erfasst: Wert verkleinern; zuviel: vergrößern) modifiziert werden
                              aus Kompatibilitätsgründen muss diese Funktion mit Sunduration\SUN_CALC = True aktiviert werden
                            html-Abfrage für WSWIN implementiert - http://ipadresse:portnummer/WSWIN gibt eine WSWin-kompatible Datenzeile der letzten Werte aus
                            neuer Forward-Type EWUDP (UDPEW) - konvertiert eingehende EW-, WU- und AMB-Meldungen nach Ecowitt/UDP (etwa für Personal Weather Tablet/UDP broadcast listener)
                            FWD_IGNORE zum Filtern aller ausgehenden Keys jetzt gültig für alle Forwards - Keys in dieser Liste werden nicht verschickt
                            Remap-Funktion FWD_REMAP implementiert - Ausgabe-Keys können jetzt mit Werten aller bekannten internen Keys definiert werden
                              Einige Ziele unterstützen nur eine Auswahl an Sensoren, Ambient Weather unterstützt z.B. nur einen internen/externen PM2.5-Sensor oder Awekas oder WSWin nur 4 Bodenfeuchtesensoren.
                              FOSHKplugin überträgt jedoch immer logisch fortlaufend - beginnt also beim jeweils ersten Sensor und sendet die jeweils gültige max. Anzahl der Kanäle.
                              Mit FWD_REMAP kann eine entsprechende Zuordnung bzw. Auswahl erfolgen.
                              Beispiel: FWD_REMAP = @tf_ch1c=@tf_ch8c # setzt den metrischen Key tf_ch1c (entspricht metr. Temperaturwert 1. Kanal) auf den Wert von tf_ch8c (8. Kanal)
                              dabei können Werte anderer Keys (mit @) und statische Werte zugewiesen (etwa @tf_ch1c=12.3) sowie eigene Keys definiert werden (soiltemp2=@tf_ch7c);
                            neuer Forward-Typ APRS ermöglicht das Versenden der Daten an CWOP
                              call sign wird als FWD_SID übergeben, ein ggf. nötiges Passwort kann mit FWD_PWD übergeben werden; FWD_URL enthält die Adresse:Port des Ziels
                              kann auch per http mit http://ipadresse:portnummer/APRS?user=CALLSIGN abgerufen werden
                            Weather365: Bodentemperaturen der Sensoren 2..4 werden nun auch übertragen - beachte das ggf. nötige Remappen!
                            MeteoTemplate: Unterstützung von WN35 (Blattfeuchte) und WN34 als soil temp/TSn - die Tiefe kann mit TS0n=cm als ADD_ITEM oder per FWD_REMAP hinzugefügt werden
                            MeteoTemplate: Batteriewerte von PM2.5-Sensoren werden nun statt mit PMnBAT mit PPnBAT ausgegeben
                            Unterstützung des WS90-Sensors (wh90batt) und der WS19xx-Konsole (ws1900batt)
                            Sollen Ausgabedaten zwar per Script (FWD_EXEC) verarbeitet, nicht jedoch versendet werden, kann dies mit einer Rückmeldung von "EXECONLY" aus dem Script realisiert werden: echo EXECONLY als letzter Ausgabebefehl im Script.
                            bei EVAL_VALUES erfolgt jetzt auch die Ausgabe des tatsächlichen Intervalls mit isintvl sowie des Mittelwertes der letzten 10 Intervalle als isintvl10
                              zusätzliche Warnung (Log, UDP, Pushover, ...) mit Warning\INTVL_WARNING = True in Config-File aktivierbar
                              mit Warning\INTVL_PCT = n lässt sich der Prozentwert n der Überschreitun, der zu einer Warnung führt, anpassen (default: 10%)
                            fehlerhafte Daten bei Einlieferung durch GW2000 mit Firmware v2.1.0 korrigiert (Ecowitt muss ein Firmware-Update nachliefern)
                            Problem bei Einlieferung durch GW2000 mit Firmware v2.1.1 behoben (Hochkommas in rfdata)
                            in den Pushover-Benachrichtigungen erfolgt nun zusätzlich die Anzeige des meldenden Hosts mit Direktlink zur Weboberläche von FOSHKplugin
                              somit sollte bei mehreren parallelen Installationen von FOSHKplugin der Verursacher schneller zugeordnet werden können
                              der Link http://ipaddress:port/FOSHKplugin/help führt zu einer Seite, wo etwaige Push-Benachrichtigungen zur Laufzeit auch deaktiviert werden können
                            Übersichtsseite für alle intern genutzten Variablen implementiert: http://ipaddress:port/FOSHKplugin/keyhelp
                            neue Option -checkConfig - prüft die Config-Datei und zeigt nächsten freien/nutzbaren Forward-n an
                            neue Config-Option Logging\BUT_PRINT = False respektiert IGNORE_LOG auch für Ausgaben auf der Konsole (default: True)
                              lässt sich auch zur Laufzeit ändern mit http://ipaddress:port/FOSHKplugin/printignored=disable/enable
                            neue Config-Option Weatherstation\WS90_CONVERT = True um bei alleiniger Anwesenheit von Regenwerten eines WS90 dessen Sonder-Keys für Regenwerte in die konventionellen zu konvertieren (default=True)
                              Die Regen-Werte eines WS90-Kombisensors werden von der Station mit eigenen, separaten Keys übertragen.
                              Ist diese Option aktiviert (WS90_CONVERT = True) werden diese - sofern der WS90 der einzige Regensensor im System ist - konvertiert:
                              rrain_piezo --> rainratein
                              erain_piezo --> eventrainin
                              hrain_piezo --> hourlyrainin
                              drain_piezo --> dailyrainin
                              wrain_piezo --> wekklyrainin
                              mrain_piezo --> monthlyrainin
                              yrain_piezo --> yearlyrainin
                              Ist ein weiterer Regensensor vorhanden, werden die Werte beider Regensensoren für die Weiterverarbeitung genutzt, wobei die des klassischen Sensors als Regenwerte ausgegeben werden.
                            neue Config-Option Export\URL_REPAIR = True (default) fügt automatisch ein ggf. fehlendes aber für den jeweiligen Forward erforderliches "http://" in der FWD_URL ein - kann mit URL_REPAIR = False deaktiviert werden
                              es gab mehrere Fehlerberichte von Nutzern, das ein Forward (meist im EW-Format) nicht funktioniert - Grund war aber jeweils, das das "http://" in der FWD_URL vergessen wurde
                              mit diesem Automatismus erfährt der Nutzer über ein Warning im Log-File weiterhin, das die Konfiguration nicht korrekt ist - der Forward funktioniert jedoch durch diesen Eingriff
- 2024-02-04 Release v0.10  changed: maxdailygust is now maxdailygustkmh in metric data (kmh) - the unit of maxdailygust is mph - ATTENTION! may cause compatibility issues!
                            fixed: typo in generic-FOSHKplugin-install.sh fixed sytemd –> systemd
                            fixed: UDP command Plugin.intvlwarning=enable/disable triggered co2warning instead (copy/paste-Error)
                            fixed: min/max values for leaf moisture sensors 1-8 were not written to the daily CSV
                            fixed: WS90 rain-handling - replacing the new names with the old ones now works correctly (e.g. „rrain_piezo“ –> „rainratein“)
                            fixed: scanWS MAC address output
                            fixed: Sending of additional temp/hum sensors now according to WeatherCloud API documentation: temp02/hum02
                            fixed: sunhours calculation - formula corrected like WeeWX extension (Jterrettaz)
                            fixed: modifications for altered AWEKAS-API (response OK)
                            fixed: possible error in the creation of the daily CSV fixed
                            fixed: LoxBerry - piezo variable names in Loxone template fixed (added mm to the name)
                            improved: improved 10 minutes average calculation „winddir_avg10m“ (avgWind)
                            improved: ignore „@“ in the field identifier of OUT_TEMP and OUT_HUM to standardise the assignments as with FWD_REMAP
                            improved: Pushover notification for missing weather station changed to red text color
                            improved: existing values can now be assigned via FWD_REMAP to the WeatherCloud keys co, no, no2, so2, o3, tempagro, et, pwrsply, battery and noise
                            improved: sending pm25 & aqi of WH41/43 channel #1 to WeatherCloud if no WH45 present (WH45 still preferred)
                            improved: conversion to WU: tempNf, humidityN, qcStatus, softwareType
                            improved: better error handling for saving as file via ftp(s)
                            improved: InfluxDB: missed forwards are queued and transmitted when the destination is available again
                            improved: error handling for Weathercloud forwards
                            improved: error handling for Pushover push notifications (automatic retry)
                            improved: parameter -scanWS gathers all weather stations now - including GW2000
                            improved: WH45 for WU - if no WH41 present, use data from WH45 instead
                            improved: internal functions stringToDict & getfromDict
                            improved: if the structure of the daily CSV is changed, a new file is created
                            new: introducing REBOOT_WARNING - check wether current runtime < last runtime - if so: warn (log, push, UDP: rebootwarning=1 dailyboot=#count)
                              can be deactivated with http: /FOSHKplugin/rebootwarning=disable and UDP: Plugin.rebootwarning=disable
                              LoxBerry: commands are included as virtual outputs in the template
                            new: „dailyboot“ (number of restarts) and „rebootwarning“ as keys, reset at midnight and is also part of the daily CSV (if EVAL_VALUES active)
                              LoxBerry: Keys „rebootwarning“ and „dailyboot“ are included as virtual inputs in the template
                            new: „sunshine“ represents the presence of sunshine; can be artificially prolonged with SUNSHINE_HOLD to prevent constant changes
                              LoxBerry: key „sunshine“ also included in template as virtual input
                            new: introducing SUNSHINE_HOLD = seconds - Hold time in seconds for value sunshine, this time continues to be output sunshine = True, even if there is no sunshine (default: 0)
                            new: FWD_TYPE = MIYO; sends temperature, wind and rain state (rain = rainratemm > 0 or hourlyrainmm > 1 or dailyrainmm > 1) to a MIYO cube (irrigation system)
                             rain forecast is still missing; could be implemented too via API AerisWeather or AccuWeather (both in test)
                            new FWD_TYPE = INFLUX2MET and INFLUX2IMP - support of InfluxDB2 - Python 3.6 or later and Python lib influxdb-client are required!
                              bucket = dbname; org = fwd_sid; token = fwd_pwd
                              missed forwards are queued and transmitted when the destination is available again
                            new: (LoxBerry) virtual input FOSHK-getMinMax for command Plugin.getminmax integrated in Loxone template
                            new: send the fwd_type, prgname & prgver as an argument with postFile
                            new: FWD_WARNING, FWD_WARNINT, http://ipaddress:portnumber/FOSHKplugin/fwdstat, enable/disable via http & UDP
                            new: BATTERY_WARNING may be enabled/disabled via http & UDP
                            new: support for leafwetness sensors for Ambient Weather stations
                            new: change the date/time output format via Config\DT_FORMAT (default = %d.%m.%Y %H:%M:%S - dd.mm.yyyy hh:mm:ss) for all (!) date/time outputs: log, csv, push
                            new: forward warning via Pushover
                              after a configurable number of successive unsuccessful attempts, a push message is sent through Pushover
                            new: statistics page for forwards: http://ipaddress:portnumber/FOSHKplugin/fwdstat
                            new: scan weather station page: http://ipaddress:portnumber/FOSHKplugin/scanWS
                            new: missed forwards for forward types EW and RAWEW may be queued and sent when destination is available again (with FWD-xx\FWD_QUEUE = True)
                            new: exclude list for battery warning: BATTERY_WARNEXCLUDE - a comma separated list of keys to exclude from battery warning e.g. wh90batt
                            new: Awekas-API: deliver weather report conditions & tendency
                              missed forwards are automatically queued as FOSHKplugin-queue/FWD-nr/FOSHKplugin-queued-data-nr.csv in config dir (or dir configured as FWD_QDIR)
                            new: Adaptations for installation under (Open)Suse, Synology, Fedora (zypper, ipkg, dnf) in generic version
                            new: custom push notifications via Pushover (user-defined push messages when values exceed or fall below a definable value)
                            new: Conversion to UTF-8 of all programme parts (may cause problems)
                            new: Weather Report for Awekas - automatically report rain, storm and thunderstorm
                            new: FWD_TYPE = BANNER - automatic generation of banners and stickers with current weather data
                            new: further queryable key names for getvalue, JSON, ... and forward types MQTT, InfluxDB, BANNER and TAGFILE:
                              prgname (FOSHKplugin)
                              prgver (current version number)
                              prgbuild (complete version number with beta status)
                              winddirtext (if available, 10min winddir-mean otherwise winddir as short text (N, NE, NNO, ...)
                              aqtime (Time of processing by FOSHKplugin)
                              pchange1in (1 hour pressure change in inHg)
                              pchange3in (3 hour pressure change in inHg)
                              lightningmi (lightning distance in miles)
                              starttime (start time of FOSHKplugin)
                            new: FWD_TYPE = TAGFILE - user-defined output format based on tags and templates
                            new: config option Export\LIMIT_WINDGUST = n to prevent processing of unrealistic values for windgustmph and maxdailygust (e.g. for WS80/WS90).
                              if value >= n the windgustmph will be renamed to _windgustmph (thus not processed); last "good" maxdailygust will be used as maxdailygust
                            new: calculation of windrun (in miles) and windrunkm (in km) and daily solar radiation sum (srsum) - also included in Loxone template
                            new: with getvalue, the additional parameter &comma can be used to force the output of a comma (",") instead of the dot (".") in numeric values
                            new: with Config\LINK_ADR = address in Config file you may specify a name or address for all links created by FOSHKplugin (e.g. for use on public web server)
                            new: support of Debian Bookworm based distributions by using virtual environment venv (problem with installation of required Python libraries with pip - PEP 668)
                            new: with Export\ADD_DEWPT = True you can enable/disable the dew point calculation for indoor sensor, WH31 and WH45 - default: False
                              the keys are dewptinf (indoor T/H sensor), dewptNf (WH31; where N=1..8), dewptf_co2 (for WH45) and for metric units: dewptinc, dewptNc, dewptc_co2
                              Loxone: new metric keys dewptinc, dewptNc, dewptc_co2 added to the Loxone template
                            new: get complete dictionary with http://ipaddress:portnumber/FOSHKplugin/getFullDict (with options like separator, sorted, json)
                            new: with Logging\COLOR_PRINT (default: True), messages in the console window are highlighted in colour (ERROR = red, WARNING = yellow and after a warning has been cancelled = green; can be deactivated with COLOR_PRINT = False
                            new: supports the Prometheus time series database - see https://foshkplugin.phantasoft.de/generic#prometheus
                            new: Support for the old HP1001 console (conversion to WU format)
                            new: use "&human" to output the time as readable time (e.g. dd.mm.yyyy hh:mm:ss) for time-specific getvalue queries; output format and locale may be specified (defaults to DT_FORMAT & LANGUAGE)
                              Example: http://192.168.15.100:8096/FOSHKplugin/getvalue?key=aqtime&human&format="%A %x %H:%M:%S"&locale=nl_NL.UTF-8 --> zaterdag 03-02-24 10:17:22
                            new: with Export\ADD_SPREAD = True (default: False) there will be additionally spread values for indoor, outdoor and WH45 sensor as well as all WH31 calculated
                            changed: all incoming get-requests will be URL-decoded now
                            new: enable/disable signal quality acquisition on supported consoles with Export\ADD_SIGNAL = True (default: False)
                            changed: with FWD_OPTION = blacklist=False, the additional values for spread and signal quality are forwarded also in Ecowitt format for this specific forward
                            new: Introduction of a naming scheme for beta versions ("Beta YYMMDD") - displayed at startup, in the log files and on the web pages generated by FOSHKplugin
                            new: enable debug mode if file debug.enable found in the config directory
                              enable debug mode with bin/service.sh debug-enable and disable with bin/service.sh debug-disable - LoxBerry only
                            changed: changed default SUN_COEF from 0.8 to 0.92 - should fit better for Germany
                            changed: all sun related values (e.g. sunshine, srsum, sunhours, ...) are only transmitted if solarradiation is present
                            changed: better integration with Home Assistant (MQTT discovery) - see https://foshkplugin.phantasoft.de/generic#hass

## Known-Issues

