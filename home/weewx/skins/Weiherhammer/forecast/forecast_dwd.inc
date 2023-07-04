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
