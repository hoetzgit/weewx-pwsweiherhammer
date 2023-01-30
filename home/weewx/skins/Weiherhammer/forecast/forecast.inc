#errorCatcher Echo
#encoding UTF-8
#import datetime

    #if $Extras.has_key("forecast_enabled") and $Extras.forecast_enabled == '1' and (($Extras.has_key("forecast_interval_hours") and $Extras.forecast_interval_hours != '0') or not ($Extras.has_key("forecast_interval_hours")))
    <!-- DWD Vorhersage -->
    <script type='text/javascript'>
        setInterval(ajaxforecast, 60000); // Update forecast data
    </script>
    <div class="row border-bottom forecast-source-container">
        <div class="row col-sm-12 forecast-source">$obs.label.forecast_issueTime_dwd <span class="forecast-issueTime-dwd"></span><!-- moment.js --></div>
        <div class="rom col-sm-12 forecast-source">$obs.label.forecast_source_dwd</div>
    </div>

    <div class="row forecastrow">
        <!-- Forecast -->
        <div class="forecast-container">
            <div class="col-sm-8 forecast-title">
                $obs.label.forecast_header_dwd <span class="forecast-subtitle"></span><!-- moment.js -->
            </div>
            <div class="col-sm-4 forecast-menu">
                $obs.label.forecast_interval_caption <div class="forecast-button" onclick="forecast_select(1);" id="button1">1</div>
                <div class="forecast-button" onclick="forecast_select(3);" id="button3">3</div>
                <div class="forecast-button" onclick="forecast_select(24);" id="button24">24</div>
            </div>
        </div>

        <div id="1hour-selected-forecast" style="display: none;">
            <!-- 1hour Forecast -->
            <div class="col-lg-12 row 1hr_forecasts row-no-padding"></div><!-- JS -->
        </div>
        <div id="3hour-selected-forecast" style="display: none;">
            <!-- 3hour-Forecast -->
            <div class="col-lg-12 row 3hr_forecasts row-no-padding"></div><!-- JS -->
        </div>        
        <div id="24hour-selected-forecast" style="display: none;">
            <!-- 24hour-Forecast -->
            <div class="col-lg-12 row 24hr_forecasts row-no-padding"></div><!-- JS -->
        </div>
    </div>
    #end if

    #if os.path.exists("dwd/forecast-10688.inc")
    <!-- DWD Vorhersage weewx-DWD-->
    <div class="row border-bottom" style="margin-top:15px;">
        <div class="col-md-12 forecast-title">
            Wettervorhersage der Station Weiden i.d. OPf
        </div>
        <div class="col-md-12">
            #include raw "dwd/forecast-10688.inc"
        </div>
    </div>
    #end if

    #if os.path.exists("dwd/forecast-10688-hourly.inc")
    <!-- Wettervorhersage Stündlich DWD Station 10688 -->
    <div class="row border-bottom" style="margin-top:15px;">
        <div class="col-md-12 forecast-title">
            Wettervorhersage st&uuml;ndlich der Station Weiden i.d. OPf
        </div>
        <div class="col-md-12">
            #include raw "dwd/forecast-10688-hourly.inc"
        </div>
    </div>
    #end if

    <!-- DWD Meteogramm -->
    <script type='text/javascript'>
        showChart("DWD");
        setInterval(showChart, 60000, "DWD"); // Load updated charts.
    </script>

    <div class="row" style="margin-top:15px;">
        <div class="col-md-12" id="meteogramm1"></div>
        <div class="col-md-12" id="meteogramm2"></div>
        <div class="col-md-12" id="meteogramm3"></div>
    </div>

    #if os.path.exists("dwd/SchilderMS.jpg")
    <!-- DWD Warnungen -->
    <div class="row">
        <div class="col-md-12 forecast-headline">
            $obs.label.forecast_header_warnings_by
            <span class="issued-DWD"> $obs.label.forecast_issuedWarnings_dwd</span>
        </div>
        <div class="col-sm-12 forecast-content dwdwarningsbay" style="margin-top:5px;">
            <a href="https://www.dwd.de/DE/wetter/warnungen_gemeinden/warnWetter_node.html?ort=Weiherhammer&bundesland=bay" target="_blank" rel="noreferrer"><img itemprop="image" src="$relative_url/dwd/SchilderMS.jpg" alt="Die Warnlage in Bayern"></a>
        </div>
    </div>
    #end if

    #if os.path.exists("dwd/warn-NEW.inc")
    <div class="row">
        <div class="col-md-12 forecast-headline">
            $obs.label.forecast_header_warnings_new
        </div>  
        <div class="col-md-12 forecast-content">
            #include "dwd/warn-NEW.inc"
        </div>
    </div>
    #end if

    #if os.path.exists("dwd/warn-WEIHERHAMMER.inc")
    <div class="row">
        <div class="col-md-12 forecast-headline">
            $obs.label.forecast_header_warnings_whm
        </div>
        <div class="col-md-12 forecast-content">
            #include raw "dwd/warn-WEIHERHAMMER.inc"
        </div>
    </div>
    #end if

    #if os.path.exists("dwd/wbx_tab_BY.inc")
    <div class="row">
    #set $start = 300
    #set $end = 1105
    #set $act = int(datetime.date.today().strftime("%m%d"))
    ## DWD Waldbrandgefahrenindex only in the period March to October
    #if $act > $start and $act < $end
        #include "dwd/wbx_tab_BY.inc"
    #else
        <!-- DWD Waldbrandgefahrenindex -->
        <div class="col-xs-12 wbx-headline">$obs.label.forecast_header_wbx <span class="issued-DWD">$obs.label.forecast_issuedWBX_dwd_paused</span></div>
        <div class="col-md-12 forecast-content"><p>zur Zeit keine Warnungen (Daten werden vom DWD im Zeitraum <b>M&auml;rz</b> bis <b>Oktober</b> zur Verf&uuml;gung gestellt.)</p></div>
    </div>
    #end if
    #end if

    ## Die Idee mit Schleife und Wochentagen: https://github.com/Daveiano/weewx-wdc/blob/2.x/skins/weewx-wdc/dwd.html.tmpl
    <div class="row">
        <div class="col-md-12 forecast-headline" style="margin-top:30px;">
            $obs.label.forecast_header_bavaria
            <span class="issued-DWD"> $obs.label.forecast_issuedText_dwd</span>
        </div>
    </div>

    #set $VHDL = "DWMG"
    #set $today = datetime.date.today()
    #set $headings = {54: $obs.label.forecast_header_current, 50: $obs.label.forecast_header_today, 51: $obs.label.forecast_header_tomorrow, 52: $obs.label.forecast_header_weekday + " " + ($today + datetime.timedelta(days=2)).strftime("%A"), 53: $obs.label.forecast_header_weekday + " " + ($today + datetime.timedelta(days=3)).strftime("%A")}
    #for $filenumber in [54, 50, 51, 52, 53]
    #if os.path.exists("dwd/VHDL" + str($filenumber) + "_" + $VHDL + "_LATEST.html")
    <div class="row">
        <div class="col-md-12 forecast-subheadline">
            $headings[$filenumber]
        </div>
        <div class="col-md-12 forecast-content">
            <p>
            #include raw "dwd/VHDL" + str($filenumber) + "_" + $VHDL + "_LATEST.html"
            </p>
        </div>
    </div>
    #end if
    #end for

    #if os.path.exists("dwd/bwk_bodendruck_na_ana.png")
    <!-- DWD Luftdruck am Boden -->
    <div class="row">
        <div class="col-md-12 forecast-headline">
            $obs.label.forecast_header_current_map
            <span class="issued-DWD"> $obs.label.forecast_issuedMaps_dwd</span>
        </div>
        <div class="col-md-12 forecast-content dwdmapeu" style="margin-top:5px;">
            <a href="https://www.dwd.de/DE/leistungen/hobbymet_wk_europa/hobbyeuropakarten.html" target="_blank" rel="noreferrer"><img itemprop="image" src="$relative_url/dwd/bwk_bodendruck_na_ana.png" alt="Wetterkarte (Luftdruck am Boden)"></a>
        </div>
    </div>
    #end if

    #if os.path.exists("forecast/wettersoftware-meteogramm.yes")
    <!-- DWD Meteogramm wettersoftware.de -->
    <link rel="stylesheet" href="$relative_url/libs/meteogram/css/meteogram.v2.0.min.css" type="text/css" media="all"/>
    #if os.path.exists("libs/meteogram/css/custom.css")
    <link rel="stylesheet" href="$relative_url/libs/meteogram/css/custom.css" type="text/css" media="all"/>
    #end if
    <script type="text/javascript" src="$relative_url/libs/meteogram/js/meteogram.v2.0.min.js"></script>
    <script>new Meteogram('#meteogram', '10688');</script>
    <div class="row" style="margin-top:15px;">
        <div class="col-md-12 forecast-headline">
            $obs.label.forecast_header_dwd_meteo
            <span class="forecast-subtitle"></span><!-- moment.js -->
        </div>
    </div>
    <div class="row">
        <div class="mtg-meteogram" id="meteogram"</div>
    </div>
    #end if