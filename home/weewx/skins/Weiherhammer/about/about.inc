#errorCatcher Echo
#encoding UTF-8
<div class="entry-content about-outer" itemprop="text">

    <!-- Willkommen -->
    <div class="row about-row">
        <div class="col-sm-12">
            <h2>Herzlich willkommen</h2>
            <p>auf meiner Wetterseite. Ich habe hier ein paar zus&auml;tzliche Informationen f&uuml;r Interessierte zusammengestellt. Über freundliche Kontakte, Tipps und Anregungen freue ich mich immer.</p>
        </div>
    </div>

    <!-- Allgemein -->
    <div class="row about-row">
        <div class="col-sm-12">
            <h2>Allgemein</h2>
            <p>Wie wird denn das Wetter in <a href="https://www.weiherhammer.de/" target="_blank" rel="noreferrer">Weiherhammer</a> heute? &Uuml;blich war der Blick aus dem Fenster und auf das analoge Thermometer. Es sollte aber eine smartere L&ouml;sung her. 
            Nach einigen Funkthermometern mit Display und diversen selbstgebastelten und selbst programmierten Wetterstationen entschied ich mich, eine fertige Station zu installieren.</p>
            <p>Seit dem 25. August 2019 nutze ich meine private Wetterstation (PWS) in Weiherhammer. Mit der Webseite habe ich das aktuelle Wetter vor Ort jederzeit und &uuml;berall im Blick.
            Ein Kombisensor ist sicher nicht optimal und auch der Aufstellstandort entspricht keiner Vorgabe, aber die Station und die Webseite erfüllt ihren Zweck und hat den Blick auf mein Fensterthermometer ersetzt.</p>
        </div>
    </div>

    <div class="row about-row">
        <div class="col-sm-12">
            <h2>Sensoren und Messwerte</h2>
        </div>
    </div>

    <!-- Sainlogic WS3500 -->
    <div class="row about-row">
        <div class="col-sm-12">
            <h3>Sainlogic WS3500</h3>
            <p>Die Y-f&ouml;rmige Station <a href="https://www.amazon.de/Sainlogic-Profi-WLAN-Wetterstation-Wettervorhersage/dp/B07TVMQ2CK" target="_blank" rel="noreferrer">Sainlogic WS3500</a> 
            ist ein <a href="http://www.foshk.com" target="_blank" rel="noreferrer">Fine Offset</a>/<a href="https://www.ecowitt.com/shop/homePage" target="_blank" rel="noreferrer">Ecowitt</a> Klon. 
            Sie besteht aus einem Kombinationssensor WH65 und der Konsole WH2910. Im Januar 2022 wurde die Station mit dem <a href="https://www.ecowitt.com/shop/goodsDetail/107" target="_blank" rel="noreferrer">Ecowitt Funkgateway GW1100</a> 
            und einem <a href="https://www.ecowitt.com/shop/goodsDetail/64" target="_blank" rel="noreferrer">Ecowitt WH57</a> Blitzsensor erg&auml;nzt. Der WH57 Sensor befindet sich unterhalb der 
            Wetterstation und wurde in einer <a href="https://www.tfa-dostmann.de/produkt/schutzhuelle-fuer-aussensender-98-1114/" target="_blank" rel="noreferrer">TFA Dostmann Schutzh&uuml;lle</a> untergebracht.</p>
        </div>

        <div class="col-sm-4">
            <img src="$relative_url/images/Wetterstation_Sainlogic.jpg" alt="Sainlogic WS3500 Wetterstation in Weiherhammer" rel="tooltip" title="Sainlogic WS3500 Wetterstation in Weiherhammer" style="horizontal-align: middle;"/>
            <p><small>Sainlogic WS3500 im Garten, ca. 5m H&ouml;he</small></p>
        </div>

        <div class="col-sm-8">
            <h4>Messwerte WH65 Sensor</h4>
            <ul>
                <li>Temperatur</li>
                <li>Luftfeuchtigkeit</li>
                <li>Windgeschwindigkeit</li>
                <li>Windrichtung</li>
                <li>Niederschlag (Regen)</li>
                <li>UV-Index</li>
                <li>Sonnenstrahlung</li>
                <li>Luftdruck</li>
            </ul>
            <h4>Messwerte WH57 Blitzdetektor</h4>
            <ul>
                <li>Anzahl Gewitterblitze</li>
                <li>Entfernung des Blitzes (ca. 40 km Reichweite)</li>
                <li>Zeitpunkt des letzten Blitzes</li>
            </ul>
        </div>
        <div class="col-sm-12">
        <p>Mehrere Innenraumsensoren <a href="https://www.ecowitt.com/shop/goodsDetail/55" target="_blank" rel="noreferrer">Ecowitt WH31</a> zur Messung der Raumtemperatur und Luftfeuchtigkeit, sowie ein
        <a href="https://www.ecowitt.com/shop/goodsDetail/19" target="_blank" rel="noreferrer">Ecowitt WH51</a> Sensor zur Messung der Bodenfeuchte in Prozent, ergänzen die Messwerte.</p>
        </div>
        </div>

    <!-- Solar Station -->
    <div class="row about-row">
        <div class="col-sm-12">
            <h3>Solar Station</h3>
            <p>Im Juni 2020 installierte ich eine kleine Eigenbau Station, meine "Solar Station". In den Sommermonaten kann die Stromversorgung autark mit Solarstrom erfolgen. Gepuffert wird in 
            einem 18650 Akku. Im Winter muss ich jedoch mit einem Netzteil unterst&uuml;tzen. Basierend auf einem ESP8266 Mikrocontroller (Wemos D1 Mini Pro)
            und dem <a href="https://www.bosch-sensortec.com/products/environmental-sensors/humidity-sensors-bme280/" target="_blank" rel="noreferrer">BME280 Sensor</a> werden die Messwerte per 
            MQTT alle 30 Sekunden &uuml;ber W-LAN &uuml;bertragen. Als Grundlage zum Bau war die Anleitung "<a href="https://www.instructables.com/Solar-Powered-WiFi-Weather-Station-V20/" target="_blank" rel="noreferrer">Solar Powered WiFi Weather Station V2.0</a>" sehr hilfreich.</p>
        </div>

        <div class="col-sm-4">
            <img src="$relative_url/images/Wetterstation_Solar.jpg" alt="Solar Wetterstation in Weiherhammer" rel="tooltip" title="Solar Wetterstation in Weiherhammer" style="horizontal-align: middle;"/>
            <p><small>Solar Station am Balkon, ca. 4,5m H&ouml;he</small></p>
        </div>

        <div class="col-sm-8">
            <h4>Messwerte BME280</h4>
            <ul>
                <li>Temperatur</li>
                <li>Luftfeuchtigkeit</li>
                <li>Luftdruck</li>
            </ul>
            <p>Die Messwerte k&ouml;nnen <a href="https://www.weiherhammer-wetter.de/graphs/?graph=SolarStation" target="_blank" rel="noreferrer">hier</a> angesehen werden.</p>
        </div>

        <div class="col-sm-12">
        </div>
    </div>

    <!-- Nova PM Sensor SDS011 -->
    <div class="row about-row">
        <div class="col-sm-12">
            <h3>AirRohr Feinstaubmessungen</h3>
            <p>Seit M&auml;rz 2022 ist ein Feinstaubsensor Nova PM SDS011 und ein DHT22 Sensor installiert. Dabei habe ich mich an dieser 
            <a href="https://sensor.community/de/sensors/airrohr/" target="_blank" rel="noreferrer">Anleitung</a> der 
            <a href="https://sensor.community/de/" target="_blank" rel="noreferrer">Sensor.Community</a> orientiert.</p>
        </div>

        <div class="col-sm-4">
            <img src="$relative_url/images/airRohr_SDS011.jpg" alt="AirRohr Feinstaubsensor Nova PM SDS011 PWS Weiherhammer" rel="tooltip" title="AirRohr Feinstaubsensor Nova PM SDS011 PWS Weiherhammer" style="horizontal-align: middle;"/>
            <p><small>Feinstaubsensor am Balkon in ca. 4,5m H&ouml;he</small></p>
        </div>

        <div class="col-sm-8">
            <h4>Messwerte Nova PM SDS011 Sensor</h4>
            <ul>
                <li>Feinstaub - PM<sub>2.5</sub></li>
                <li>Feinstaub - PM<sub>10</sub></li>
            </ul>
            <h4>Messwerte DHT22 Sensor</h4>
            <ul>
                <li>Temperatur</li>
                <li>Luftfeuchtigkeit</li>
            </ul>
            <p>Die Daten k&ouml;nnen <a href="https://www.weiherhammer-wetter.de/graphs/?graph=SDS011_PM" target="_blank" rel="noreferrer">hier</a> angesehen werden. Einen Vergleich 
            des PM Sensors zu den geladenen Werten der Luftqualit&auml;t-APIs gibt es <a href="https://www.weiherhammer-wetter.de/graphs/?graph=APIAQ" target="_blank" rel="noreferrer">hier</a>.</p>
        </div>
    </div>

    <!-- AllSky Kamera -->
    <div class="row about-row">
        <div class="col-sm-12">
            <h3>AllSky Kamera mit einer 360&deg Ansicht</h3>
            <p>Meine AllSky Kameras - 
            #if os.path.exists("allsky/allskycam01.up")
            <a href="https://allsky01.ott24.net" target="_blank" rel="noreferrer">Kamera 1</a>
            #else if os.path.exists("allsky/allskycam01.down")
            Kamera 1 <span style="color:red;">(offline)</span>
            #else
            Kamera 1 
            #end if
            /
            #if os.path.exists("allsky/allskycam02.up")
            <a href="https://allsky02.ott24.net" target="_blank" rel="noreferrer">Kamera 2</a>
            #else if os.path.exists("allsky/allskycam02.down")
            Kamera 2 <span style="color:red;">(offline)</span>
            #else
            Kamera 2 
            #end if
            - wurden im November 2020 installiert.</p>
            <p>Die Kamera 1 dient hauts&auml;chlich der Himmelsbeobachtung in der Nacht, um z.B. den Verlauf der Sterne oder Meteoriten zu sehen. Durch die 360&deg Ansicht ist sie ebenfalls  
            sehr gut zur Beobachtung der aktuellen Wetterbedingungen geeignet. Im Inneren der Kamera arbeitet ein Raspberry Pi 4 mit einer Raspberry HQ Kamera und einem Fischaugenobjektiv. 
            In der Nacht werden - entsprechend den Lichtverh&auml;ltnissen - l&auml;nger belichtete Fotos aufgenommen. Wenn der Tag wieder startet, werden diese zu einem
            <a href="https://allsky.ott24.net/videos/" target="_blank" rel="noreferrer">Timelaps Video</a> und zu 
            <a href="https://allsky.ott24.net/startrails/" target="_blank" rel="noreferrer">Startrail</a> und 
            <a href="https://allsky.ott24.net/keograms/" target="_blank" rel="noreferrer">Keogram</a> Bildern zusammengef&uuml;gt.</p>
            <p>Um eine &Uuml;berhitzung an sehr warmen Tagen zu verhindern, versuche ich die Temperatur im Geh&auml;use mit zwei L&uuml;ftern zu k&uuml;hlen. Im Winter hingegen wird die Kuppel 
            beheizt. Dies habe ich mit einer selbstgebauten Widerstandsheizung (<a href="https://www.dewbuster.com/heater-resistors.html" target="_blank" rel="noreferrer">Anleitung</a>) umgesetzt. 
            Auftretende Tau-Tropfen innerhalb der Kuppel oder Reif- und Schneebel&auml;ge au&szlig;erhalb der Kuppel werden wirksam verhindert, die Kamera hat freie Sicht. Es sind nat&uuml;rlich Sensoren verbaut, 
            damit dies per Software sinnvoll gesteuert werden kann. Die Messwerte der Sensoren werden zus&auml;tzlich an die Station gesendet und 
            <a href="https://www.weiherhammer-wetter.de/graphs/?graph=AllSky" target="_blank" rel="noreferrer">visualisiert</a>.</p>
            <p>Der Raspberry Pi, die L&uuml;fter und die Heizung m&uuml;ssen mit gen&uuml;gend Power versorgt werden. Die Kamera ist mit einem 20m Stromkabel und einem st&auml;rkeren Netzteil verbunden, welches 
            gen&uuml;gend Leistung liefert. Die Bauteile im Inneren sind &uuml;ber einen 
            <a href="https://www.amazon.de/dp/B092VRTS7Z/?coliid=I2QFJ21HVTT0U8&colid=2OFTVJIQKSNN1&psc=1&ref_=lv_ov_lig_dp_it" target="_blank" rel="noreferrer">Buck Converter</a> angeschlossen und 
            erhalten so ihre 5V oder 12V Spannung.</p>
            <p>Als AllSky Backend und zur Darstellung der AllSky Webseite verwende ich das Projekt von <a href="https://github.com/thomasjacquin/allsky" target="_blank" rel="noreferrer">Thomas Jacquin</a>.</p>
            <p>Kamera 2 ist ein Testsystem und daher nicht immer online. Sie liefert keine Sensordaten.</p>
        </div>

        <div class="col-sm-4">
            <img src="$relative_url/images/Allsky_Kamera_1.jpg" alt="360&deg; AllSky Himmelskamera in Weiherhammer, Kamera 1" rel="tooltip" title="360&deg; AllSky Himmelskamera in Weiherhammer, Kamera 1" style="horizontal-align: middle;"/>
            <p><small>AllSky Kamera 1</small></p>
        </div>

        <div class="col-sm-2">
            <img src="$relative_url/images/Allsky_Kamera_2.jpg" alt="360&deg; AllSky Himmelskamera in Weiherhammer, Kamera 2" rel="tooltip" title="360&deg; AllSky Himmelskamera in Weiherhammer, Kamera 2" style="horizontal-align: middle;"/>
            <p><small>AllSky Kamera 2</small></p>
        </div>

        <div class="col-sm-6">
            <h4>Messwerte DS18B20 in der Kuppel Kamera 1</h4>
            <ul>
                <li>Temperatur</li>
            </ul>
            <h4>Messwerte BME280 im Geh&auml;use Kamera 1</h4>
            <ul>
                <li>Temperatur</li>
                <li>Luftfeuchtigkeit</li>
                <li>Luftdruck</li>
            </ul>
            <p>Die Messwerte k&ouml;nnen <a href="https://www.weiherhammer-wetter.de/graphs/?graph=AllSky" target="_blank" rel="noreferrer">hier</a> angesehen werden.</p>
        </div>
    </div>

    <!-- Webcam -->
    <div class="row about-row">
        <div class="col-sm-12">
            <h3>Foscam FI9900P IP Camera</h3>
            <p>Im Mai 2020 kam eine Webcam hinzu (<a href="$relative_url/webcam/">Anzeige des aktuellen Bildes</a>). Die Blickrichtung ist ungef&auml;hr SSW.</p>
        </div>

        <div class="col-sm-4">
            <img src="$relative_url/images/Wetterstation_Webcam.jpg" alt="Webcam Wetterstation Weiherhammer" rel="tooltip" title="Webcam Wetterstation Weiherhammer" style="horizontal-align: middle;"/>
            <p><small>Webcam Foscam FI9900P</small></p>
        </div>

        <div class="col-sm-8">
        </div>
    </div>

    <!-- Externe Datenquellen -->
    <div class="row about-row">
        <div class="col-sm-12">
            <h2>Externe Datenquellen</h2>
            <p>Nicht alle auf der Webseite angezeigten Daten können durch die eigene Station gemessen werden. Um z.B. eine Wettervorhersage nutzen zu k&ouml;nnen oder zur Darstellung des allgemeinen 
            Wetterzustandes werden zus&auml;tzliche Daten von externen Quellen geladen und verarbeitet. Diverse Anbieter stellen - oft kostenfrei - Schnittstellen (sog. API's) zum Abruf diverser Daten bereit.
            Der Deutsche Wetterdienst (DWD) stellt eine Vielzahl von Daten in Dateiform auf den <a href="https://opendata.dwd.de" target="_blank" rel="noreferrer">Open Data Servern</a> bereit.</p>
        </div>
    </div>

    <!-- Daten externer Dienste -->
    <div class="row about-row">
        <div class="col-sm-12">
            <h3>Externe Wetterdaten</h3>
            <ul>
                <li><a href="https://www.windy.com/de/-Widget-auf-Seite-einbetten/widgets?49.676,12.154,5" target="_blank" rel="noreferrer">Windy Widget</a> zur Anzeige von Wetterdaten auf der Startseite</li>
                <li>Vorhersagen und Warnmeldungen vom <a href="https://www.dwd.de" target="_blank" rel="noreferrer">Deutscher Wetterdienst</a> (DWD). Abgefragt werden Daten der
                  <a href="http://www.wzforum.de/forum2/read.php?38,3255813" target="_blank" rel="noreferrer">Station Weiden i.d.OPf</a> (WMO ID: 10688). Die Abfrage und Aufbereitung erfolgt mit Erweiterungen aus
                  <a href="https://github.com/roe-dl/weewx-DWD" target="_blank" rel="noreferrer">weewx-DWD</a>.
                </li>
                <li>Vorhersagen und Warnmeldungen von <a href="https://open-meteo.com" target="_blank" rel="noreferrer">Open-Meteo</a>. Abgefragt werden Daten des DWD für den Standort der Station.
                  Die Abfrage und Aufbereitung erfolgt mit Erweiterungen aus <a href="https://github.com/roe-dl/weewx-DWD" target="_blank" rel="noreferrer">weewx-DWD</a>.
                </li>
                <li>Vorhersagen und Warnmeldungen von <a href="https://www.aerisweather.com" target="_blank" rel="noreferrer">AerisWeather</a>. Die Abfrage erfolgt mit Hilfe der 
                  <a href="https://www.aerisweather.com/support/docs/api/" target="_blank" rel="noreferrer">AerisWeather API</a>. Abgefragt werden Daten des 
                  <a href="https://metar-taf.com/de/ETIC" target="_blank" rel="noreferrer">Army Air Field</a> (ICAO-Code ETIC) in Grafenw&ouml;hr.
                </li>
            </ul>
            <h3>Erdbeben</h3>
            <ul>
                <li>Anzeige von Erdbeben mit Daten der <a href="http://earthquake.usgs.gov/fdsnws/event/1/" target="_blank" rel="noreferrer">USGS.gov Earthquake Catalog Developer API</a>.</li>
            </ul>
            <h3>Luftqualit&auml;t</h3>
            <p>Erg&auml;nzend zu meinen AirRohr-Feinstaubdaten (PM<sub>2.5</sub>/PM<sub>10</sub>) werden zur Berechnung des Luftqualit&auml;tslevels weitere Daten - Ozon (O<sub>3</sub>) und Stickstoffdioxid (NO<sub>2</sub>) - der <a href="https://www.umweltbundesamt.de/daten/luft/luftdaten/stationen/" target="_blank" rel="noreferrer">Station Weiden i.d. OPf</a>, Nikolaistra&szlig;e (Stationscode DEBY075) geladen.
            Die Berechnung und Einteilung der Luftqualit&auml;t orientiert sich an den <a href="https://www.umweltbundesamt.de/berechnungsgrundlagen-luftqualitaetsindex" target="_blank" rel="noreferrer">Berechnungsgrundlagen Luftqualit&auml;tsindex</a> des <a href="https://www.umweltbundesamt.de" target="_blank" rel="noreferrer">Umweltbundesamtes</a> (UBA).</p>
            <ul>
                <li><a href="https://www.umweltbundesamt.de/daten/luft/luftdaten/doc" target="_blank" rel="noreferrer">Umweltbundesamt Air Data API</a></li>
            </ul>
            <p>Weitere Daten zum <a href="https://www.weiherhammer-wetter.de/graphs/?graph=APIAQ" target="_blank" rel="noreferrer">Vergleich</a> von diesen Diensten<p>
            <ul>
                <li><a href="https://www.aerisweather.com/support/docs/api/reference/endpoints/airquality/" target="_blank" rel="noreferrer">AerisWeather Airquality API</a></li>
                <li><a href="https://openweathermap.org/api/air-pollution" target="_blank" rel="noreferrer">OpenWeatherMap Air Pollution API</a></li>
            </ul>
        </div>
    </div>

    <!-- Verarbeitung -->
    <div class="row about-row">
        <div class="col-sm-12">
            <h2>Aufbereitung der Daten</h2>
            <p>Um die Sensordaten sowie die externen Daten aufzubereiten, verwende ich die Open Source Software <a href="https://weewx.com" target="_blank" rel="noreferrer">WeeWX</a>. 
            Der Leistungsumfang von WeeWX wird durch die eingebundenen Erweiterungen erheblich gesteigert.<p>
        </div>
    </div>

    <!-- Software -->
    <div class="row about-row">
        <div class="col-sm-12">
            <h3>&Uuml;bersicht der intern verwendeten Software</h3>
            <ul>
                <li>Wettersoftware <a href="https://github.com/weewx/weewx" target="_blank" rel="noreferrer">WeeWX</a>, Version: $station.version</li>
                <li>MQTT Broker <a href="https://obrienlabs.net/go/mqttbroker" target="_blank" rel="noreferrer">Mosquitto</a> zur Aufnahme von Nachrichten per MQTT</li>
                <li>Visualisierung dieser Webseite mit einer angepassten Version der <a href="https://github.com/poblabs/weewx-belchertown" target="_blank" rel="noreferrer">Belchertown skin</a>. Basierend auf Belchertown skin Version: 1.3</li>
                <li>Erweiterung <a href="https://www.highcharts.com" target="_blank" rel="noreferrer">HighCharts</a> zur Erstellung von Charts auf dieser Webseite</li>
                <li>Das <a href="https://wiki.loxberry.de/plugins/foshkplugin/start" target="_blank" rel="noreferrer">FOSHKplugin</a> (<a href="https://wiki.loxberry.de/plugins/foshkplugin/foshkplugin_generic_version" target="_blank" rel="noreferrer">generic Version</a>) zum Empfang der GW1100 Daten per HTTP, deren Aufbereitung und Weiterleitung zu WeeWX und weiteren Zielen, Version: 0.09</li>
                <li>WeeWX Treiber <a href="https://github.com/matthewwall/weewx-interceptor" target="_blank" rel="noreferrer">weewx-interceptor</a> (ecowitt-client) zum Empfang der Daten per HTTP von FOSHKplugin. An eigene Sensoren angepasst, basierend auf Version: 0.60</li>
                <li>WeeWX Service <a href="https://github.com/gjr80/weewx-gw1000" target="_blank" rel="noreferrer">Ecowitt Gateway</a> (weewx-gw1000) zum direkten Auslesen des GW1100 f&uuml;r weitere Daten (Batteriestatus, Signalst&auml;rken), Version: 0.5.0b6</li>
                <li>WeeWX Service <a href="https://github.com/bellrichm/WeeWX-MQTTSubscribe" target="_blank" rel="noreferrer">WeeWX-MQTTSubscribe</a> zum Empfang weiterer Daten (Solar Station, Wetter API's u.s.w.) per MQTT, Version: 2.2.3-rc01</li>
                <li>WeeWX Service <a href="https://github.com/bellrichm/weewx-mqttpublish" target="_blank" rel="noreferrer">weewx-mqttpublish</a> zum Upload der WeeWX Daten per MQTT in den MQTT Broker, Version: 0.2.0-rc02a</li>
                <li>Erweiterung <a href="https://github.com/matthewwall/weewx-mqtt" target="_blank" rel="noreferrer">weewx-mqtt</a>, angepasste <a href="https://github.com/roe-dl/weewx-mqtt/tree/aggregate_values" target="_blank" rel="noreferrer">Version</a> zum Upload der WeeWX Daten per MQTT in den MQTT Broker, Version: 0.25</li>
                <li>Erweiterungen aus <a href="https://github.com/roe-dl/weewx-DWD" target="_blank" rel="noreferrer">weewx-DWD</a>, um eine Vielzahl externer Daten abzurufen und aufzubereiten.</li>
                <li>Erweiterung <a href="https://github.com/roe-dl/weewx-GTS" target="_blank" rel="noreferrer">weewx-GTS</a>, generiert die <a href="https://de.wikipedia.org/wiki/Gr%C3%BCnlandtemperatursumme" target="_blank" rel="noreferrer">Grünlandtemperatursumme</a> und viele weitere Daten, Version: 0.9a2</li>
                <li>Erweiterung <a href="https://github.com/jonathankoren/weewx-aqi" target="_blank" rel="noreferrer">weewx-aqi</a>, angepasste <a href="https://github.com/hoetzgit/weewx-aqi/tree/CustomAirQualityIndex" target="_blank" rel="noreferrer">Version</a>, diese orientiert sich an den <a href="https://www.umweltbundesamt.de/berechnungsgrundlagen-luftqualitaetsindex" target="_blank" rel="noreferrer">Berechnungsgrundlagen Luftqualit&auml;tsindex</a> des Umweltbundesamtes</li>
                <li>Erweiterung <a href="https://github.com/Jterrettaz/sunduration" target="_blank" rel="noreferrer">sunduration</a>, angepasste <a href="https://github.com/hoetzgit/weewx-pwsweiherhammer/blob/master/home/weewx/bin/user/sunshineduration.py" target="_blank" rel="noreferrer">Version</a>, Berechnung der Sonnenscheindauer in Sekunden pro Archiv Intervall</li>
                <li>Erweiterung <a href="https://github.com/brewster76/fuzzy-archer/tree/master/bin/user" target="_blank" rel="noreferrer">historygenerator</a>, angepasste <a href="https://github.com/hoetzgit/weewx-pwsweiherhammer/blob/master/home/weewx/bin/user/tablegenerator.py" target="_blank" rel="noreferrer">Version</a> um <a href="https://www.weiherhammer-wetter.de/reports/" target="_blank" rel="noreferrer">tabellarische Reporte</a> zu erstellen.</li>
                <li>Erweiterung <a href="https://github.com/chaunceygardiner/weewx-loopdata" target="_blank" rel="noreferrer">weewx-loopdata</a>, generiert eine JSON Datei mit vielen Werten pro LOOP. Version: 3.3.1</li>
                <li>Erweiterung <a href="https://github.com/chaunceygardiner/weewx-forecast" target="_blank" rel="noreferrer">weewx-forecast</a> um Vorhersagedaten f&uuml;r andere WeeWX Skins zur Verf&uuml;gung zu stellen. Version: 3.4.0b12</li>
                <li>Erweiterung <a href="https://github.com/matthewwall/weewx-windy" target="_blank" rel="noreferrer">weewx-windy</a>, Upload zu <a href="https://www.windy.com" target="_blank" rel="noreferrer">Windy.com</a>, Version: 0.7</li>
                <li>Erweiterung <a href="https://github.com/matthewwall/weewx-wetter" target="_blank" rel="noreferrer">weewx-wetter</a>, Upload zu <a href="https://www.wetter.com" target="_blank" rel="noreferrer">wetter.com</a>, Version: 0.7</li>
                <li>Erweiterung <a href="https://github.com/matthewwall/weewx-owm" target="_blank" rel="noreferrer">weewx-owm</a>, angepasste <a href="https://github.com/hoetzgit/weewx-owm/tree/pws-weiherhammer" target="_blank" rel="noreferrer">Version</a>, Upload zu <a href="https://openweathermap.org" target="_blank" rel="noreferrer">OpenWeatherMap</a>, Version: 0.9</li>
                <li>Erweiterung <a href="https://github.com/sbsrouteur/weewx-opensensemap" target="_blank" rel="noreferrer">weewx-opensensemap</a>, Upload zu <a href="https://opensensemap.org" target="_blank" rel="noreferrer">openSenseMap</a>, Version: 0.3</li>
                <li>Erweiterung <a href="https://github.com/hoetzgit/weewx-meteoservices/tree/master" target="_blank" rel="noreferrer">weewx-meteoservices</a>, angepasste <a href="https://github.com/hoetzgit/weewx-meteoservices/tree/enable-disable-service" target="_blank" rel="noreferrer">Version</a>, Upload zu <a href="https://meteo-services.com" target="_blank" rel="noreferrer">MeteoServices</a>, Version: 3.2 - <a href="https://stations.meteo-services.com/wxupdates/Downloads/meteoservices-3.2.zip" target="_blank" rel="noreferrer">Download</a> der originalen Erweiterung direkt beim Anbieter MeteoServices</li>
                <li>DWD Meteogramm von <a href="http://tools.wettersoftware.de" target="_blank" rel="noreferrer">wettersoftware.de</a></li>
            </ul>
        </div>
    </div>

    <!-- Externe Weiterleitungen -->
    <div class="row about-row">
        <div class="col-sm-12">
            <h2>Weiterleitung der Daten zu externen Wetterdiensten</h2>
            <ul>
                <li><a href="https://pwsweather.com/station/pws/IWEIHE1" target="_blank" rel="noreferrer">PWSWeather.com</a></li>
                <li><a href="https://www.awekas.at/de/instrument.php?id=22468" target="_blank" rel="noreferrer">AWEKAS</a></li>
                <li><a href="https://stations.meteo-services.com/wetterstation/index.php?station_id=8504" target="_blank" rel="noreferrer">MeteoServices</a></li>
                <li><a href="https://wetternetzwerk.pro/#/wetterstation/78" target="_blank" rel="noreferrer">wetternetzwerk.pro</a></li>
                <li><a href="https://netzwerk.wetter.com/wetterstation/20758/" target="_blank" rel="noreferrer">wetter.com</a></li>
                <li><a href="https://www.wunderground.com/personal-weather-station/dashboard?ID=IWEIHE1" target="_blank" rel="noreferrer">Weather Underground</a></li>
                <li><a href="https://app.weathercloud.net/d6258809966" target="_blank" rel="noreferrer">WeatherCloud.net</a></li>
                <li><a href="https://www.windy.com/station/pws-f0652fc0?49.632,12.056,10" target="_blank" rel="noreferrer">Windy.com</a></li>
                <li><a href="https://opensensemap.org/explore/5cac7a833680f2001b658be9" target="_blank" rel="noreferrer">OpenSenseMap</a></li>
                <li><a href="https://deutschland.maps.sensor.community/#13/49.6271/12.0591" target="_blank" rel="noreferrer">Sensor.Community</a></li>
                <li><a href="https://openweathermap.org/city/2812752" target="_blank" rel="noreferrer">OpenWeather</a></li>
            </ul>
        </div>
    </div>

    <!-- Links -->
    <div class="row about-row">
        <div class="col-sm-12">
            <h2>Zus&auml;tzliche Visualisierungen</h2>
            <ul>
                <li><a href="https://belchertown.weiherhammer-wetter.de" target="_blank" rel="noreferrer">Belchertown</a> (original, <a href="https://github.com/poblabs/weewx-belchertown" target="_blank" rel="noreferrer">Infos</a>)</li>
                <li><a href="https://seasons.weiherhammer-wetter.de" target="_blank" rel="noreferrer">WeeWX Seasons</a> (Skin bei WeeWX dabei, <a href="https://github.com/weewx/weewx/tree/master/skins/Seasons" target="_blank" rel="noreferrer">Infos</a>)</li>
                <li><a href="https://wdc.weiherhammer-wetter.de" target="_blank" rel="noreferrer">WDC</a> (Weather Data Center, <a href="https://github.com/Daveiano/weewx-wdc" target="_blank" rel="noreferrer">Infos</a>)</li>
                <li><a href="https://jas.weiherhammer-wetter.de" target="_blank" rel="noreferrer">JAS</a> (just another skin, <a href="https://github.com/bellrichm/weewx-jas" target="_blank" rel="noreferrer">Infos</a>)</li>
                <li><a href="https://neowx.weiherhammer-wetter.de" target="_blank" rel="noreferrer">NeoWX Material</a> (<a href="https://neoground.com/projects/neowx-material" target="_blank" rel="noreferrer">v1.11 Infos</a>/<a href="https://github.com/seehase/neowx-material" target="_blank" rel="noreferrer">v1.12 Infos</a>)</li>
                <li><a href="https://pwsd.weiherhammer-wetter.de" target="_blank" rel="noreferrer">PWS Dashboard</a> (PHP Dashboard, <a href="https://pwsdashboard.com" target="_blank" rel="noreferrer">Infos</a>)</li>
                <li><a href="https://fuzzy.weiherhammer-wetter.de" target="_blank" rel="noreferrer">Fuzzy Archer</a> (<a href="https://github.com/brewster76/fuzzy-archer" target="_blank" rel="noreferrer">Infos</a>)</li>
                <li><a href="https://rtgauges.weiherhammer-wetter.de" target="_blank" rel="noreferrer">SteelSeries Weather Gauges</a> (<a href="https://github.com/mcrossley/SteelSeries-Weather-Gauges" target="_blank" rel="noreferrer">Infos</a>/<a  href="https://github.com/gjr80/weewx-realtime_gauge-data" target="_blank" rel="noreferrer">Infos</a>)</li>
                <li><a href="https://sofa.weiherhammer-wetter.de" target="_blank" rel="noreferrer">Sofa</a> (<a href="https://neoground.com/projects/sofaskin" target="_blank" rel="noreferrer">Infos</a>)</li>
                <li><a href="https://sofa2.weiherhammer-wetter.de" target="_blank" rel="noreferrer">Sofa-CW9009</a> (<a href="https://github.com/weatherstorm/Sofaskin-CW9009" target="_blank" rel="noreferrer">Infos</a>)</li>
                <li><a href="https://mesowx.weiherhammer-wetter.de" target="_blank" rel="noreferrer">MesoWX</a> (realtime HTML frontend, <a href="https://github.com/glennmckechnie/weewx-mesowx" target="_blank" rel="noreferrer">Infos</a>)</li>
                <li><a href="https://wxobs.weiherhammer-wetter.de" target="_blank" rel="noreferrer">wxobs</a> (<a href="https://github.com/glennmckechnie/weewx-wxobs" target="_blank" rel="noreferrer">Infos</a>)</li>
            </ul>
        </div>
    </div>

    <!-- Zusatzinfos -->
    <div class="row about-row">
        <div class="col-sm-12">
            <h2>Weitere Informationen zur Wetterstation</h2>
            <ul>
                <li>Standort: <a href="https://www.weiherhammer.de" target="_blank" rel="noreferrer">Weiherhammer, Bayern, Deutschland</a>
                <li>H&ouml;he ca.: $station.altitude</li>
                <li>Konsole Software EasyWeather Version: 1.6.5</li>
                <li>Ecowitt GW1100 Gateway Software Version: 2.2.3</li>
                <li>Backend- und WebServer: Diverse virtuelle VMware ESXi basierende Rechner mit Ubuntu 22.04.2 LTS, Webseite self hosted</li>
                <li>WeeWX Server uptime: $station.os_uptime.long_form</li>
                <li>WeeWX Service uptime: $station.uptime.long_form</li>
                <li><a href="https://www.weiherhammer-wetter.de/stationmon/?monitor=$Extras.stationmon_page_default" target="_blank" rel="noreferrer">Station Monitor</a> (work in progress)</li>
            </ul>
        </div>
    </div>

    <!-- Tipps -->
    <div class="row about-row">
        <div class="col-sm-12">
            <h2>Tipps</h2>
            <p>Wer eine tolle Wetterseite im deutschsprachigen Raum sucht, kann mal die Webseite <a href="https://www.woellsdorf-wetter.de" target="_blank" rel="noreferrer">Wetterstation D&ouml;beln-W&ouml;llsdorf</a> besuchen. 
            Dort findet man sehr viele <a href="https://www.woellsdorf-wetter.de/info/" target="_blank" rel="noreferrer">hilfreiche Beitr&auml;ge</a> rund um das Wetter und die Konfiguration von WeeWX. 
            Die Betreiberinnen erstellen auch WeeWX Extensions und stellen diese auf <a href="https://github.com/roe-dl?tab=repositories" target="_blank" rel="noreferrer">GitHub</a> zur Verf&uuml;gung.</p>
            <p>Vielen Dank an dieser Stelle f&uuml;r Inspirationen und Hilfestellungen bei Fragen und Problemen.</p>
        </div>
    </div>

    <!-- GitHub -->
    <div class="row about-row">
        <div class="col-sm-12">
            <h2>GitHub</h2>
            <p>Meine Anpassungen und Konfigurationen als Sicherung bei GitHub</p>
            <ul>
                <li>GitHub <a href="https://github.com/hoetzgit/weewx-pwsweiherhammer" target="_blank" rel="noreferrer">WeeWX PWS Weiherhammer</a></li>
            </ul>
        </div>
    </div>

</div>