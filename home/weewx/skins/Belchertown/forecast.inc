#encoding UTF-8

<!-- Start forecast.inc -->

<div class="entry-content about-outer">
    <!-- Start AerisWeather-->

    <script type="text/javascript">
        var moment_locale = "$system_locale_js";
        moment.locale(moment_locale);

        function autoRefreshPage() {
            window.location = window.location.href;
        }
        
        ajaxweewx().then(function(weewx_data) { // This call will make sure json/weewx_data.json is loaded before anything else
            update_weewx_data(weewx_data); // Initial call to update (date, daily high, low, etc)
            belchertown_debug(weewx_data); // Make weewx_data.json available in debugging console
            #if $Extras.has_key("forecast_enabled") and $Extras.forecast_enabled == '1'
            // Load forecast
            ajaxforecast(); // Initial call to load forecast data like 8 day outlook, weather icon and observation text
            #end if
        
            jQuery(document).ready(function() {
                // Update the Last Updated timestamp with moment.js,
                updated = tzAdjustedMoment( $current.dateTime.raw ).format("$obs.label.time_last_updated");
                updated_text = "$obs.label.header_last_updated " + updated;
                jQuery(".updated").html( updated_text );

                #if $Extras.has_key("show_last_updated_alert") and $Extras.show_last_updated_alert == '1'
                // Check if we need to alert on old information - if time now, minus the last update is greater than the threshold, show an alert.
                if ( ( Math.floor(new Date().getTime()/1000.0) - $Extras.last_updated_alert_threshold ) > $current.dateTime.raw ) {
                    belchertown_debug("Last Updated Alert: The weewx report timestamp is "+$current.dateTime.raw+". The current timestamp is "+Math.floor(new Date().getTime()/1000.0)+". The threshold is "+$Extras.last_updated_alert_threshold+". Report timestamp is greater than threshold of current time, showing no update alert.");
                    last_updated_alert_text = "<i class='fa fa-exclamation-triangle' style='color:red;'></i> $obs.label.header_last_updated_alert";
                    jQuery(".last-updated-alert").html( last_updated_alert_text );
                    jQuery(".last-updated-alert").show();
                }
                #end if
                        
                // Update the Last Updated timestamp with moment.js,
                updated = tzAdjustedMoment( $current.dateTime.raw ).format("$obs.label.time_last_updated");
                updated_text = "$obs.label.header_last_updated " + updated;
                jQuery(".updated").html( updated_text );

                //  display the relevant forecast; a new session will display the default forecast, a reloaded session the currently displayed forecast
                if ( sessionStorage.getItem ("forecastInterval")  ) {
                    interval = sessionStorage.getItem("forecastInterval");
                    sessionStorage.setItem ( "forecastInterval" , null );
                    forecast_select( interval );
                } else {
                    sessionStorage.setItem ( "forecastInterval" , null );
                    forecast_select( sessionStorage.getItem( "defaultInterval") );
                }
            });
        }).catch(function(e) {
            console.log(e);
        });
        
    </script>

    <!-- DWD Vorhersage -->

    #if $Extras.has_key("forecast_enabled") and $Extras.forecast_enabled == '1' and (($Extras.has_key("forecast_interval_hours") and $Extras.forecast_interval_hours != '0') or not ($Extras.has_key("forecast_interval_hours")))
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

    ###if os.path.exists("dwd/forecast-10688.inc")
    ##<div class="row index-hook-after-forecast border-bottom" style="margin-top:15px;">
    ##    <div class="col-md-12 forecast-title">
    ##        Wettervorhersage der Station Weiden i.d. OPf
    ##    </div>
    ##    <div class="col-md-12">
    ##        #include raw "dwd/forecast-10688.inc"
    ##    </div>
    ##</div>
    ###end if

    ###if os.path.exists("dwd/forecast-10688-hourly.inc")
    ##<!-- Wettervorhersage Stündlich DWD Station 10688 -->
    ##<div class="row index-hook-after-forecast border-bottom" style="margin-top:15px;">
    ##    <div class="col-md-12 forecast-title">
    ##        Wettervorhersage st&uuml;ndlich der Station Weiden i.d. OPf
    ##    </div>
    ##    <div class="col-md-12">
    ##        #include raw "dwd/forecast-10688-hourly.inc"
    ##    </div>
    ##</div>
    ###end if

    <!-- DWD Meteogramm weewx-DWD -->
    <script type='text/javascript'>showChart("DWD");</script>

    <div class="row" style="margin-top:15px;">
        <div class="col-md-12" id="meteogramm1"></div>
        <div class="col-md-12" id="meteogramm2"></div>
        <div class="col-md-12" id="meteogramm3"></div>
    </div>
    ##<div class="row border-bottom" style="margin-top:5px;margin-bottom:5px;">
    ##    <div class="col-md-12 forecast-source">$obs.label.forecast_issueTime_dwd <span class="forecast-issueTime-dwd"></span><!-- moment.js --></div>
    ##    <div class="col-md-12 forecast-source">$obs.label.forecast_source_dwd</div>
    ##</div>
    #end if

    #if os.path.exists("dwd/SchilderMS.jpg")
    <div class="row index-hook-after-forecast" style="margin-top:15px;">
        <div class="col-md-12 forecast-headline">
            $obs.label.forecast_header_warnings_by
        </div>
        <div class="col-sm-12 forecast-content" style="margin-top:5px;">
            <a id="warnlage_bay" name="warnlage_bay" href="https://www.dwd.de/DE/wetter/warnungen_gemeinden/warnWetter_node.html?ort=Weiherhammer&bundesland=bay" target="_blank"><img itemprop="image" src="$relative_url/dwd/SchilderMS.jpg" alt="Die Warnlage in Bayern"></a>
        </div>
    </div>
    #end if

    #if os.path.exists("dwd/warn-NEW.inc")
    <div class="row index-hook-after-forecast" style="margin-top:15px;">
        <div class="col-md-12 forecast-headline">
            $obs.label.forecast_header_warnings_new
        </div>  
        <div class="col-md-12">
            #include "dwd/warn-NEW.inc"
        </div>
    </div>
    #end if

    #if os.path.exists("dwd/warn-WEIHERHAMMER.inc")
    ##<div class="row index-hook-after-forecast border-bottom" style="margin-top:15px;">
    <div class="row index-hook-after-forecast" style="margin-top:15px;">
        <div class="col-md-12 forecast-headline">
            $obs.label.forecast_header_warnings_whm
        </div>
        <div class="col-md-12">
            #include raw "dwd/warn-WEIHERHAMMER.inc"
        </div>
    </div>
    #end if

    #if os.path.exists("dwd/wbx_tab_BY.inc")
    <div class="row index-hook-after-forecast" style="margin-top:15px;">
        #include "dwd/wbx_tab_BY.inc"
    </div>
    #end if

    #if os.path.exists("dwd/VHDL54_DWMG_LATEST.html")
    <div class="row index-hook-after-forecast" style="margin-top:15px;">
        <div class="col-md-12 forecast-headline">
            $obs.label.forecast_header_bavaria
        </div>
        <div class="col-md-12 forecast-content">
            #include raw "dwd/VHDL54_DWMG_LATEST.html"
        </div>
    </div>
    #end if

    #if os.path.exists("dwd/VHDL50_DWMG_LATEST.html")
    <div class="row index-hook-after-forecast" style="margin-top:15px;">
        <div class="col-md-12 forecast-headline">
            $obs.label.forecast_header_today
        </div>
        <div class="col-md-12 forecast-content">
            #include raw "dwd/VHDL50_DWMG_LATEST.html"
        </div>
    </div>
    #end if

    #if os.path.exists("dwd/VHDL51_DWMG_LATEST.html")
    <div class="row index-hook-after-forecast" style="margin-top:15px;">
        <div class="col-md-12 forecast-headline">
            $obs.label.forecast_header_tomorrow
        </div>
        <div class="col-md-12 forecast-content">
            #include raw "dwd/VHDL51_DWMG_LATEST.html"
        </div>
    </div>
    #end if

    #if os.path.exists("dwd/VHDL52_DWMG_LATEST.html")
    <div class="row index-hook-after-forecast" style="margin-top:15px;">
        <div class="col-md-12 forecast-headline">
            $obs.label.forecast_header_da_tomorrow
        </div>
        <div class="col-md-12 forecast-content">
            #include raw "dwd/VHDL52_DWMG_LATEST.html"
        </div>
    </div>
    #end if

    #if os.path.exists("dwd/VHDL53_DWMG_LATEST.html")
    <div class="row index-hook-after-forecast" style="margin-top:15px;">
        <div class="col-md-12 forecast-headline">
            $obs.label.forecast_header_fourth_day
        </div>
        <div class="col-md-12 forecast-content">
            #include raw "dwd/VHDL53_DWMG_LATEST.html"
        </div>
    </div>
    #end if

    #if os.path.exists("dwd/bwk_bodendruck_na_ana.png")
    <div class="row index-hook-after-forecast" style="margin-top:15px;">
        <div class="col-md-12 forecast-headline">
            $obs.label.forecast_header_current_map
        </div>
        <div class="col-md-12 forecast-content" style="margin-top:5px;>
            <a id="wetterkarte_nae" name="wetterkarte_nae" href="https://www.dwd.de/DE/leistungen/hobbymet_wk_europa/hobbyeuropakarten.html" target="_blank"><img itemprop="image" src="$relative_url/dwd/bwk_bodendruck_na_ana.png" alt="Wetterkarte (Luftdruck am Boden)"></a>
        </div>
    </div>
    #end if

    ##<!-- DWD Meteogramm wettersoftware.de -->
    ##<script src="$relative_url/meteogram.v2.0.min.js"></script>
    ##<script>new Meteogram('#meteogram', '10688');</script>

    ##<div class="row index-hook-after-forecast border-bottom" style="margin-top:15px;">
    ##    <div class="col-md-12 forecast-headline">
    ##        $obs.label.forecast_header_dwd_meteo <span class="forecast-subtitle"></span><!-- moment.js -->
    ##    </div>
    ##    <div class="col-md-12 mtg-meteogram" id="meteogram"</div>
    ##</div>

</div>

<!-- End forecast.inc -->
