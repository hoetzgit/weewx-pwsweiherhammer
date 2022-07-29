#encoding UTF-8

<!-- Start about.inc -->

<div class="entry-content about-outer" itemprop="text">

    <!-- Einleitung -->
    <div class="row"  style="padding-top:15px;">
        <div class="col-sm-12">
            <h2>Allgemein</h2>
            <p>Wie wird das Wetter in <a href="https://www.weiherhammer.de" target="_blank" rel="noreferrer">Weiherhammer</a> heute? &Uuml;blich war mein Blick aus dem Fenster und auf das analoge Thermometer. Es sollte aber eine smartere L&ouml;sung her. 
            Nach einigen Funkthermometern mit Display und diversen selbstgebastelten und selbst programmierten Wetterstationen entschied ich mich, eine fertige Station zu installieren.</p>
            <p>Seit dem 25. August 2019 betreibe ich eine private Wetterstation (PWS) in Weiherhammer. Durch die Webseite habe ich das aktuelle Wettergeschehen vor Ort jederzeit und 
            &uuml;berall im Blick. Ich bin aber kein Meteorologe, sondern nur ein technisch interessierter Mensch. Daher &uuml;bernehme ich keine Gewähr für die Richtigkeit der Angaben auf dieser 
            ausschlie&szlig;lich f&uuml;r meine privaten Zwecke ausgelegten Webseite. Die Webseite soll nur mein Fensterthermometer ersetzen ;-)</p>
        </div>
    </div>

    <div class="row" style="margin-top:10px;">
        <div class="col-sm-12">
            <h2>Sensoren und Messwerte</h2>
        </div>
    </div>

    <!-- Sainlogic WS3500 -->
    <div class="row" style="margin-top:10px;">
        <div class="col-sm-12">
            <h3>Sainlogic WS3500</h3>
            <p>Die Y-f&ouml;rmige Station <a href="https://www.amazon.de/Sainlogic-Profi-WLAN-Wetterstation-Wettervorhersage/dp/B07TVMQ2CK" target="_blank" rel="noreferrer">Sainlogic WS3500</a> 
            ist ein <a href="http://www.foshk.com" target="_blank" rel="noreferrer">Fine Offset</a>/<a href="https://www.ecowitt.com/shop/homePage" target="_blank" rel="noreferrer">Ecowitt</a> Klon. 
            Sie besteht aus einem Kombinationssensor WH65 und der Konsole WH2910. Im Januar 2022 wurde die Sation mit dem <a href="https://www.ecowitt.com/shop/goodsDetail/107" target="_blank" rel="noreferrer">Ecowitt Funkgateway GW1100</a> 
            und einem <a href="https://www.ecowitt.com/shop/goodsDetail/64" target="_blank" rel="noreferrer">Ecowitt WH57 Blitzsensor</a> erg&auml;nzt. Der WH57 Sensor befindet sich unterhalb der 
            Wetterstation und wurde in einer <a href="https://www.tfa-dostmann.de/produkt/schutzhuelle-fuer-aussensender-98-1114/" target="_blank" rel="noreferrer">TFA Dostmann Schutzh&uuml;lle</a> untergebracht.</p>
        </div>

        <div class="col-sm-4">
            <img src="$relative_url/images/Wetterstation_Sainlogic.jpg" alt="Sainlogic WS3500 Wetterstation in Weiherhammer" title="Sainlogic WS3500 Wetterstation in Weiherhammer" style="horizontal-align: middle;"/>
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
        </div>
        </div>

    <!-- Solar Station -->
    <div class="row" style="margin-top:15px;">
        <div class="col-sm-12">
            <h3>Solar Station</h3>
            <p>Im Juni 2020 installierte ich eine kleine Eigenbau Station. Dabei handelt es sich um die sogenannte "Solar Station". In den Sommermonaten kann die Stromversorgung autark mit 
            Solarstrom erfolgen. Gepuffert wird in einem 18650 Akku. Im Winter muss ich jedoch mit einem Netzteil unterst&uuml;tzen. Basierend auf einem ESP8266 Mikrocontroller (Wemos D1 Mini Pro)
            und dem <a href="https://www.bosch-sensortec.com/products/environmental-sensors/humidity-sensors-bme280/" target="_blank" rel="noreferrer">BME280 Sensor</a> werden die Messwerte per 
            MQTT alle 30 Sekunden &uuml;ber W-LAN &uuml;bertragen. Als Grundlage zum Bau war die Anleitung "<a href="https://www.instructables.com/Solar-Powered-WiFi-Weather-Station-V20/" target="_blank" rel="noreferrer">Solar Powered WiFi Weather Station V2.0</a>" sehr hilfreich.</p>
        </div>

        <div class="col-sm-4">
            <img src="$relative_url/images/Wetterstation_Solar.jpg" alt="Solar Wetterstation in Weiherhammer" title="Solar Wetterstation in Weiherhammer" style="horizontal-align: middle;"/>
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
    <div class="row" style="margin-top:15px;">
        <div class="col-sm-12">
            <h3>Nova PM Sensor SDS011 - airRohr</h3>
            <p>Seit M&auml;rz 2022 ist ein Feinstaubsensor - das sog. airRohr - installiert. Dabei habe ich mich an die 
            <a href="https://sensor.community/de/sensors/airrohr/" target="_blank" rel="noreferrer">Anleitung</a> der 
            <a href="https://sensor.community/de/" target="_blank" rel="noreferrer">Sensor.Community</a> gehalten.</p>
        </div>

        <div class="col-sm-4">
            <img src="$relative_url/images/airRohr_SDS011.jpg" alt="Nova PM Sensor SDS011 airRohr der Wetterstation in Weiherhammer" title="Nova PM Sensor SDS011 airRohr der Wetterstation in Weiherhammer" style="horizontal-align: middle;"/>
            <p><small>Feinstaubsensor am Balkon in ca. 4,5m H&ouml;he</small></p>
        </div>

        <div class="col-sm-8">
            <h4>Messwerte Nova PM Sensor SDS011</h4>
            <ul>
                <li>Feinstaub (PM<sub>2.5</sub>)</li>
                <li>Feinstaub (PM<sub>10</sub>)</li>
            </ul>
            <h4>Messwerte DHT22</h4>
            <ul>
                <li>Temperatur</li>
                <li>Luftfeuchtigkeit</li>
            </ul>
            <p>Die Messwerte k&ouml;nnen <a href="https://www.weiherhammer-wetter.de/graphs/?graph=SDS011_PM" target="_blank" rel="noreferrer">hier</a> angesehen werden. Einen Vergleich 
            des Sensors zu den geladenen Werten der Luftqualit&auml;t-APIs gibt es <a href="https://www.weiherhammer-wetter.de/graphs/?graph=APIAQ" target="_blank" rel="noreferrer">hier</a>.</p>
        </div>
    </div>

##    <!-- AS3935 Franklin Lightning sensor -->
##    <div class="row" style="margin-top:10px;">
##        <div class="col-sm-12">
##            <h3>AS3935 Franklin Blitzsensor</h3>
##            <p>Seit Januar 2022 ...</p>
##        </div>

##        <div class="col-sm-4">
##            <img src="$relative_url/images/as3935.jpg" alt="AS3935 Franklin Blitzsensor der Wetterstation in Weiherhammer" title="AS3935 Franklin Blitzsensor der Wetterstation in Weiherhammer" style="horizontal-align: middle;"/>
##            <p><small>Testweiser Aufbau des AS3935 Blitzsensors</small></p>
##        </div>

##        <div class="col-sm-8">
##            <h4>Messwerte AS3935 Franklin Blitzsensor</h4>
##            <ul>
##                <li>Anzahl Gewitterblitze</li>
##                <li>Entfernung des Blitzes (40 km Reichweite mit einer Genauigkeit von 1 km)</li>
##                <li>Einen Energiewert des Blitzes</li>
##            </ul>
##            <p>Die Ergebnisse k&ouml;nnen <a href="https://www.weiherhammer-wetter.de/graphs/?graph=AS3935" target="_blank" rel="noreferrer">hier</a> angesehen werden.</p>
##        </div>
##    </div>
##
    <!-- AllSky Kamera -->
    <div class="row" style="margin-top:10px;">
        <div class="col-sm-12">
            <h3>AllSky Kamera 360&deg</h3>
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
            <p>Die Kameras dienen hauts&auml;chlich der Himmelsbeobachtung in der Nacht, um z.B. den Verlauf der Sterne oder Meteoriten zu sehen. Durch die 360&deg Ansicht sind sie ebenfalls  
            sehr gut zur Beobachtung der aktuellen Wetterbedingungen geeignet. Im Inneren der Kamera 1 arbeitet ein Raspberry Pi 4 mit einer Raspberry HQ Kamera und einem Fischaugenobjektiv. 
            Es werden nacheinander jeweils 60 Sekunden lang belichtete Fotos aufgenommen. Am Ende der Nacht werden diese zu einem Timelaps Video und zu sogenannten Startrail und Keogram Bildern 
            zusammengef&uuml;gt. Um eine &Uuml;berhitzung an sehr warmen Tagen zu verhindern, wird die Temperatur im Geh&auml;use mit L&uuml;ftern heruntergek&uuml;hlt. Im Winter hingegen wird 
            die Kuppel beheizt. Dies habe ich mit einer selbstgebauten Widerstandsheizung (<a href="https://www.dewbuster.com/heater-resistors.html" target="_blank" rel="noreferrer">Anleitung</a>) 
            umgesetzt. Damit wird Tau innerhalb und Reif au&szlig;erhalb des Kameradomes wirksam verhindert und die Kamera hat eine klare Sicht. Um dies per Software sinnvoll zu steuern, sind 
            Sensoren verbaut. Die Messwerte der Sensoren werden zus&auml;tzlich an die Station gesendet und visualisiert.</p>
            <p>Die Kamera 2 ist ein Testsystem und liefert keine Sensordaten.</p>
        </div>

        <div class="col-sm-4">
            <img src="$relative_url/images/Allsky_Kamera_1.jpg" alt="360&deg; AllSky Himmelskamera in Weiherhammer, Kamera 1" title="360&deg; AllSky Himmelskamera in Weiherhammer, Kamera 1" style="horizontal-align: middle;"/>
            <p><small>AllSky Kamera 1</small></p>
        </div>

        <div class="col-sm-2">
            <img src="$relative_url/images/Allsky_Kamera_2.jpg" alt="360&deg; AllSky Himmelskamera in Weiherhammer, Kamera 2" title="360&deg; AllSky Himmelskamera in Weiherhammer, Kamera 2" style="horizontal-align: middle;"/>
            <p><small>AllSky Kamera 2</small></p>
        </div>

        <div class="col-sm-6">
            <h4>Messwerte BME280 im Geh&auml;use Kamera 1</h4>
            <ul>
                <li>Temperatur</li>
                <li>Luftfeuchtigkeit</li>
                <li>Luftdruck</li>
            </ul>
            <h4>Messwerte DS18B20 in der Kuppel Kamera 1</h4>
            <ul>
                <li>Temperatur</li>
            </ul>
            <p>Die Messwerte k&ouml;nnen <a href="https://www.weiherhammer-wetter.de/graphs/?graph=AllSky" target="_blank" rel="noreferrer">hier</a> angesehen werden.</p>
            <p>Als AllSky Backend und zur Darstellung der AllSky Webseite verwende ich das Projekt von <a href="https://github.com/thomasjacquin/allsky" target="_blank" rel="noreferrer">Thomas Jacquin</a>.</p>
        </div>
    </div>

    <!-- Webcam -->
    <div class="row" style="margin-top:10px;">
        <div class="col-sm-12">
            <h3>Foscam FI9900P IP Camera</h3>
            <p>Im Mai 2020 kam eine Webcam hinzu (<a href="$relative_url/webcam/">Anzeige des aktuellen Bildes</a>). Die Blickrichtung ist ungef&auml;hr SSW.</p>
        </div>

        <div class="col-sm-4">
            <img src="$relative_url/images/Wetterstation_Webcam.jpg" alt="Webcam Wetterstation Weiherhammer" title="Webcam Wetterstation Weiherhammer" style="horizontal-align: middle;"/>
            <p><small>Webcam Foscam FI9900P</small></p>
        </div>

        <div class="col-sm-8">
        </div>
    </div>

    <!-- Externe Datenquellen -->
    <div class="row" style="margin-top:10px;">
        <div class="col-sm-12">
            <h2>Zus&auml;tzliche Daten externer Datenquellen</h2>
            <p>Nicht alle auf der Webseite angezeigten Daten werden durch die eigene Station gemessen. Um z.B. eine Wettervorhersage anzubieten, werden zus&auml;tzliche Daten von externen
            Quellen verwendet. Diverse Anbieter stellen - meist kostenfrei - eine API zur Verf&uuml;gung. Auch der Deutsche Wetterdienst (DWD) stellt eine Vielzahl von Daten auf 
            den <a href="https://opendata.dwd.de" target="_blank" rel="noreferrer">Open Data Servern</a> bereit.</p>
        </div>
    </div>

    <!-- Wetternetzwerke und Wetterdienste -->
    <div class="row" style="margin-top:10px;">
        <div class="col-sm-12">
            <h3>Wetternetzwerke und Wetterdienste</h3>
            <ul>
                <li><a href="https://www.windy.com/de/-Widget-auf-Seite-einbetten/widgets?49.676,12.154,5" target="_blank" rel="noreferrer">Windy Widget</a> zur Anzeige von Wetterdaten auf der Startseite</li>
                <li>Vorhersagen und Warnmeldungen vom <a href="https://www.dwd.de" target="_blank" rel="noreferrer">Deutscher Wetterdienst (DWD)</a>, abgefragt wird die Station Weiden i.d.OPf (10688)</li>
                <li>Einige Vorhersageelemente basieren auf Daten der <a href="https://www.aerisweather.com" target="_blank" rel="noreferrer">AerisWeather API</a>, abgefragt wird der Flughafen in Grafenw&ouml;hr</li>
                <li>Anzeige von Erdbeben mit Daten der <a href="http://earthquake.usgs.gov/fdsnws/event/1/" target="_blank" rel="noreferrer">USGS.gov Earthquake Catalog Developer API</a></li>
            </ul>
            <h3>Luftqualit&auml;t</h3>
            <p>Erg&auml;nzend zu meinen airRohr-Feinstaubdaten (PM<sub>10</sub>) werden zur Berechnung des Luftqualit&auml;tslevels weitere Daten - Ozon (O<sub>3</sub>) und Stickstoffdioxid (NO<sub>2</sub>) - der Station Weiden i.d. OPf, Nikolaistra&szlig;e (DEBY075) geladen.
            Die Berechnung und Einteilung der Luftqualit&auml;t erfolgt nach den <a href="https://www.umweltbundesamt.de/berechnungsgrundlagen-luftqualitaetsindex" target="_blank" rel="noreferrer">Berechnungsgrundlagen Luftqualit&auml;tsindex</a> des Umweltbundesamtes.</p>
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
    <div class="row" style="margin-top:10px;">
        <div class="col-sm-12">
            <h2>Aufbereitung der Daten</h2>
            <p>Um die Sensordaten sowie die externen Daten aufzubereiten, verwende ich die Open Source Software <a href="https://weewx.com" target="_blank" rel="noreferrer">WeeWX</a>. 
            Der Leistungsumfang von WeeWX wird durch eingebundene Zusatzsoftware noch erheblich erweitert.<p>
        </div>
    </div>

    <!-- Software -->
    <div class="row" style="margin-top:10px;">
        <div class="col-sm-12">
            <h3>Eine &Uuml;bersicht der intern verwendeten Software</h3>
            <ul>
                <li>Wettersoftware <a href="https://github.com/weewx/weewx" target="_blank" rel="noreferrer">WeeWX</a>, Version: $station.version</li>
                <li>MQTT Broker <a href="https://obrienlabs.net/go/mqttbroker" target="_blank" rel="noreferrer">Mosquitto</a> zur Aufnahme von Nachrichten per MQTT</li>
                <li>Visualisierung dieser Webseite mit der <a href="https://github.com/poblabs/weewx-belchertown" target="_blank" rel="noreferrer">Belchertown skin</a>, Version: $belchertown_version (angepasst)</li>
                <li>Erweiterung <a href="https://www.highcharts.com" target="_blank" rel="noreferrer">HighCharts</a> zur Erstellung von Charts auf dieser Webseite</li>
                <li>generic <a href="https://loxwiki.atlassian.net/wiki/spaces/LOXBERRY/pages/1252524456/FOSHKplugin+-+generic+version" target="_blank" rel="noreferrer">FOSHKplugin</a> zum Empfang der GW1100 Daten und deren Weiterleitung per HTTP zu WeeWX und anderen Rechnern, Version: 0.0.9</li>
                <li>WeeWX Treiber <a href="https://github.com/matthewwall/weewx-interceptor" target="_blank" rel="noreferrer">WeeWX-Interceptor</a> (ecowitt-client) zum Empfang der Daten von FOSHKplugin per HTTP, Version: 0.53, an eigene Sensoren angepasst</li>
                <li>WeeWX Service <a href="https://github.com/bellrichm/WeeWX-MQTTSubscribe" target="_blank" rel="noreferrer">WeeWX-MQTTSubscribe</a> zum Empfang von zusätzlichen Daten (Solar Station, Wetter API's u.s.w.) per MQTT, Version: 2.1.0</li>
                <li>Erweiterungen <a href="https://github.com/roe-dl/weewx-DWD" target="_blank" rel="noreferrer">weewx-DWD</a>, um Daten des Deutschen Wetterdienstes und des Umweltbundesamtes herunterzuladen und aufzubereiten (angepasst)</li>
                ##<li>Die Meteogramm-Visualisierung der DWD Vorhersage erfolgt mit dem Meteogramm von <a href="http://tools.wettersoftware.de" target="_blank" rel="noreferrer">wettersoftware.de</a></li>
                <li>Erweiterung <a href="https://github.com/jonathankoren/weewx-aqi" target="_blank" rel="noreferrer">weewx-aqi</a>, angepasste <a href="https://github.com/hoetzgit/weewx-aqi/tree/CustomAirQualityIndex" target="_blank" rel="noreferrer">Version</a> (Klassifizierung Luftqualit&auml;t Umweltbundesamt)</li>
                <li>Erweiterung <a href="https://github.com/Jterrettaz/sunduration" target="_blank" rel="noreferrer">sunduration</a>, angepasste <a href="https://github.com/hoetzgit/sunduration/tree/sunshineDur_seconds" target="_blank" rel="noreferrer">Version</a> (Berechnet die Sonnenscheindauer in Sekunden)</li>
                <li>Erweiterung <a href="https://github.com/matthewwall/weewx-mqtt" target="_blank" rel="noreferrer">weewx-mqtt</a>, angepasste <a href="https://github.com/roe-dl/weewx-mqtt/tree/aggregate_values" target="_blank" rel="noreferrer">Version</a> zum MQTT Upload, Version: 0.25 (PR#31)</li>
                <li>Erweiterung <a href="https://github.com/matthewwall/weewx-windy" target="_blank" rel="noreferrer">weewx-windy</a>, Upload zu Windy.com, Version: 0.7</li>
                <li>Erweiterung <a href="https://github.com/matthewwall/weewx-wetter" target="_blank" rel="noreferrer">weewx-wetter</a>, Upload zu wetter.com, Version: 0.7</li>
                <li>Erweiterung <a href="https://github.com/matthewwall/weewx-owm" target="_blank" rel="noreferrer">weewx-owm</a>, Upload zu OpenWeatherMap, Version: 0.9</li>
                <li>Erweiterung <a href="https://github.com/sbsrouteur/weewx-opensensemap" target="_blank" rel="noreferrer">weewx-opensensemap</a>, Upload zu OpenSenseMap, Version: 0.3</li>
                <li>Erweiterung meteoservices, Upload zu MeteoServices, Version: 3.2 - <a href="https://stations.meteo-services.com/wxupdates/Downloads/meteoservices-3.2.zip" target="_blank" rel="noreferrer">Download</a> der Erweiterung</li>
            </ul>
        </div>
    </div>

    <!-- Externe Weiterleitungen -->
    <div class="row" style="margin-top:10px;">
        <div class="col-sm-12">
            <h2>Messwerte der Station werden zu folgenden externen Wetterdiensten weitergeleitet</h2>
            <ul>
                <li><a href="https://www.wunderground.com/personal-weather-station/dashboard?ID=IWEIHE1" target="_blank" rel="noreferrer">Weather Underground</a></li>
                <li><a href="https://pwsweather.com/station/pws/IWEIHE1" target="_blank" rel="noreferrer">PWSWeather.com</a></li>
                <li><a href="https://app.weathercloud.net/d6258809966" target="_blank" rel="noreferrer">WeatherCloud.net</a></li>
                <li><a href="https://www.windy.com/station/pws-f0652fc0?49.632,12.056,10" target="_blank" rel="noreferrer">Windy.com</a></li>
                <li><a href="https://netzwerk.wetter.com/wetterstation/20758/" target="_blank" rel="noreferrer">wetter.com</a></li>
                <li><a href="https://wetternetzwerk.pro/#/wetterstation/78" target="_blank" rel="noreferrer">wetternetzwerk.pro</a></li>
                <li><a href="https://opensensemap.org/explore/5cac7a833680f2001b658be9" target="_blank" rel="noreferrer">OpenSenseMap</a></li>
                <li><a href="https://openweathermap.org/city/2812752" target="_blank" rel="noreferrer">OpenWeather</a></li>
                <li><a href="https://stations.meteo-services.com/wetterstation/index.php?station_id=8504" target="_blank" rel="noreferrer">MeteoServices</a> (vormals Weather365)</li>
                <li><a href="https://www.awekas.at/de/instrument.php?id=22468" target="_blank" rel="noreferrer">AWEKAS</a></li>
                <li><a href="https://deutschland.maps.sensor.community/#13/49.6271/12.0591" target="_blank" rel="noreferrer">Sensor.Community</a> (vormals Luftdaten.info)</li>
            </ul>
        </div>
    </div>

    <!-- Links -->
    <div class="row" style="margin-top:10px;">
        <div class="col-sm-12">
            <h2>Links zu Visualisierungen der Wetterdaten mit anderen Templates</h2>
            <ul>
                <li><a href="https://seasons.weiherhammer-wetter.de" target="_blank" rel="noreferrer">WeeWX Seasons</a> (Skin bei WeeWX dabei)</li>
                <li><a href="https://wdc.weiherhammer-wetter.de" target="_blank" rel="noreferrer">WDC</a> (Weather Data Center, Skin <a href="https://github.com/Daveiano/weewx-wdc" target="_blank" rel="noreferrer">Infos</a>)</li>
                <li><a href="https://fuzzy.weiherhammer-wetter.de" target="_blank" rel="noreferrer">Fuzzy Archer</a> (Skin <a href="https://github.com/brewster76/fuzzy-archer" target="_blank" rel="noreferrer">Infos</a>)</li>
                <li><a href="https://neowx.weiherhammer-wetter.de" target="_blank" rel="noreferrer">NeoWX Material</a> (Skin <a href="https://neoground.com/projects/neowx-material" target="_blank" rel="noreferrer">Infos</a>)</li>
                <li><a href="https://sofa.weiherhammer-wetter.de" target="_blank" rel="noreferrer">Sofa Skin</a> (Skin  <a href="https://blauesledersofa.de" target="_blank" rel="noreferrer">Infos</a>)</li>
            </ul>
        </div>
    </div>

    <!-- Zusatzinfos -->
    <div class="row" style="margin-top:10px;">
        <div class="col-sm-12">
            <h2>Weitere Informationen zur Wetterstation</h2>
            <ul>
                <li>Standort: Weiherhammer, Bayern, Deutschland <a href="https://www.google.com/maps/@?api=1&map_action=map&center=$station.stn_info.latitude_f,$station.stn_info.longitude_f&zoom=17" target="_blank" ><i class="fa fa-map-marker" ></i> Auf der Karte anzeigen</a>
                <li>Latitude: $station.latitude[0]&deg; $station.latitude[1]' $station.latitude[2]</li>
                <li>Longitude: $station.longitude[0]&deg; $station.longitude[1]' $station.longitude[2]</li>
                <li>H&ouml;he ca.: $station.altitude</li>
                <li>Konsole Software EasyWeather Version: 1.6.4</li>
                <li>Ecowitt GW1100 Gateway Software Version: 2.1.7</li>
                <li>Backend- und WebServer: Diverse virtuelle VMware ESXi basierende Rechner mit Ubuntu 22.04 LTS, Webseite self hosted</li>
                <li>WeeWX Server uptime: $station.os_uptime</li>
                <li>WeeWX Service uptime: $station.uptime</li>
                #if $current.wh65_batt.has_data and $current.wh65_batt.raw < 1.0
                <li>Batteriestatus Sainlogic Station: <span style="color:green;">OK</span> (Wert: $current.wh65_batt)</li>
                #else if $current.wh65_batt.has_data and $current.wh65_batt.raw > 0.0  
                <li>Batteriestatus Sainlogic Station: <span style="color:red;">NIEDRIG</span> (Wert: $current.wh65_batt)</li>
                #else
                <li>Batteriestatus Sainlogic Station: UNBEKANNT</li>
                #end if
                #if $current.wh57_batt.has_data and $current.wh57_batt.raw > 3.0
                <li>Batteriestatus Blitzsensor: <span style="color:green;">OK</span> (Wert: $current.wh57_batt)</li>
                #else if $current.wh57_batt.has_data and $current.wh57_batt.raw > 1.0
                <li>Batteriestatus Blitzsensor: <span style="color:orange;">MITTEL</span> (Wert: $current.wh57_batt)</li>
                #else if $current.wh57_batt.has_data and $current.wh57_batt.raw >= 0.0
                <li>Batteriestatus Blitzsensor: <span style="color:red;">NIEDRIG</span> (Wert: $current.wh57_batt)</li>
                #else
                <li>Batteriestatus Blitzsensor: <span style="color:red;">UNBEKANNT</span></li>
                #end if
                #if $current.solar_voltage.has_data and $current.solar_voltage.raw > 3.8
                <li>Batteriestatus Solar Station: <span style="color:green;">$current.solar_voltage</span></li>
                #else if $current.solar_voltage.has_data and $current.solar_voltage.raw <= 3.8
                <li>Batteriestatus Solar Station: <span style="color:red;">$current.solar_voltage</span></li>
                #else
                <li>Batteriestatus Solar Station: <span style="color:red;">UNBEKANNT</span></li>
                #end if
            </ul>
        </div>
    </div>

    <!-- Impressum und Datenschutz -->
    <div class="row" style="margin-top:10px;">
        <div class="col-sm-12">
            <h2>Impressum und Datenschutzerkl&auml;rung</h2>
            <ul>
                <li><a href="$relative_url/impressum/">Impressum</a></li>
                <li><a href="$relative_url/datenschutz/">Datenschutzerkl&auml;rung</a></li>
            </ul>
        </div>
    </div>

</div>

<!-- Ende about.inc -->
