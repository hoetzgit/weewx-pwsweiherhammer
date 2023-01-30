#errorCatcher Echo
#encoding UTF-8

#def get_boolean_status($val, $mode)
#if $val is None
$gettext('unknown')
#elif $val == '1'
#if $mode == 'onoff'
$gettext('on')
#elif $mode == 'yesno'
$gettext('yes')
#end if
#else
#if $mode == 'onoff'
$gettext('off')
#elif $mode == 'yesno'
$gettext('no')
#end if
#end if
#end def

<div class="row">
#if $Extras.has_key("station_observations_extras_enabled") and $Extras.station_observations_extras_enabled == '1'
    <div class="col-lg-6  border-right">
        #if "station" in $station_observations_extras
        <!-- Additional Weather Station Observations-->
        <div class="row station-observations-extras-row station-observations-extras-row-left">
            <div class="station-observations-extras-title">$gettext("current conditions")</div>
            #if "obs" in $station_observations_extras.station
            <div class="station-observations-extras-body">
                <table class="station-observations-extras-table flexible-obs-extras-table" cellpadding="0" cellspacing="0">
                    <tbody>
                        #for $x in $station_observations_extras.station.obs
                            #if $x == 'barometer'
                            <tr>
                                #set $class_trend_symbol = 'trend_%s_symbol' % $x
                                #set $class_trend_value = 'trend_%s_formatted' % $x
                                <td class="station-observations-extras-label">$obs.label[$x]</td>
                                <td class="station-observations-extras-data"><span class="$x" rel="tooltip" title="">$getVar('current.%s' % $x)</span> (<span class="$class_trend_value" rel="tooltip" title="">$getVar('trend.%s.%s' % ($x,'formatted'))</span> <span class="$class_trend_symbol" rel="tooltip" title=""></span>)</td><!-- AJAX -->
                            </tr>
                            #elif $x == 'windSpeed'
                            <tr>
                                <td class="station-observations-extras-label">$obs.label.wind</td>
                                <td class="station-observations-extras-data"><span class="$x" rel="tooltip" title="">$getVar('current.%s' % $x)</span> (<span class="curwinddir">$getVar('current.windDir.ordinal_compass')</span>/<span class="curwinddeg">$getVar('current.windDir')</span>)</td><!-- AJAX -->
                            </tr>
                            #elif $x == 'rain'
                            <tr>
                                <td class="station-observations-extras-label">$obs.label[$x]</td>
                                <td class="station-observations-extras-data"><span class="dayRain" rel="tooltip" title="">$getVar('day.%s.%s' % ($x,'sum'))</span></td><!-- AJAX -->
                            </tr>
                            #elif $x == 'sunshine'
                            <tr>
                                <td class="station-observations-extras-label">$obs.label[$x]</td>
                                #if $current.sunshine is not None
                                <td class="station-observations-extras-data"><span class="current-sunshine-text" rel="tooltip" title="">$get_boolean_status($getVar('current.%s' % $x), 'yesno')</span><br>
                                #else
                                <td class="station-observations-extras-data">
                                #end if
                                ##TODO AJAX
                                <span class="day_sunshineDur_sum">$day.sunshineDur.sum.format('%(hour)d%(hour_label)s, %(minute)d%(minute_label)s')</span>
                                </td>
                            </tr>
                            #elif $x == 'lastRain'
                            <tr>
                                ##TODO AJAX
                                <td class="station-observations-extras-label">$gettext("last rain")</td>
                                <td class="station-observations-extras-data">$last_rain<br>$time_since_last_rain</td>
                            </tr>
                            #else
                            <tr>
                                <td class="station-observations-extras-label">$obs.label[$x]</td>
                                <td class="station-observations-extras-data"><span class="$x" rel="tooltip" title="">$getVar('current.%s' % $x)</span></td><!-- AJAX -->
                            </tr>
                            #end if
                        #end for
                    </tbody>
                </table>
            </div>
            #end if
        </div>
        #end if

        #if "indoor" in $station_observations_extras
        <!-- Indoor Obbservations -->
        <div class="row station-observations-extras-row station-observations-extras-row-right">
            <div class="station-observations-extras-title">$gettext("indoor conditions")</div>
            #if "obs" in $station_observations_extras.indoor
            <div class="station-observations-extras-body">
                <table class="station-observations-extras-table flexible-obs-indoor-table" cellpadding="0" cellspacing="0">
                    <tbody>
                        #for $x in $station_observations_extras.indoor.obs
                        <tr>
                            <td class="station-observations-extras-label">$obs.label[$x]</td>
                            <td class="station-observations-extras-data"><span class="$x" rel="tooltip" title="">$getVar('current.%s' % $x)</span></td><!-- AJAX -->
                        </tr>
                        #end for
                    </tbody>
                </table>
            </div>
            #end if
        </div>
        #end if
    </div>

    <div class="col-lg-6">
        #if "solar" in $station_observations_extras
        <!-- Solar Weather Station -->
        <div class="row station-observations-extras-row">
            <div class="station-observations-extras-title">$gettext("solar conditions")</div>
            #if "obs" in $station_observations_extras.solar
            <div class="station-observations-extras-body">
                <table class="station-observations-extras-table flexible-obs-solar-table" cellpadding="0" cellspacing="0">
                    <tbody>
                        #for $x in $station_observations_extras.solar.obs
                        <tr>
                            <td class="station-observations-extras-label">$obs.label[$x]</td>
                            #if $x == 'solar_barometer'
                            #set $class_trend_symbol = 'trend_%s_symbol' % $x
                            #set $class_trend_value = 'trend_%s_formatted' % $x
                            <td class="station-observations-extras-data"><span class="$x" rel="tooltip" title="">$getVar('current.%s' % $x)</span> (<span class="$class_trend_value" rel="tooltip" title="">$getVar('trend.%s.%s' % ($x,'formatted'))</span> <span class="$class_trend_symbol" rel="tooltip" title=""></span>)</td><!-- AJAX -->
                            #else
                            <td class="station-observations-extras-data"><span class="$x" rel="tooltip" title="">$getVar('current.%s' % $x)</td><!-- AJAX -->
                            #end if
                        </tr>
                        #end for
                    </tbody>
                </table>
            </div>
            #end if
        </div>
        #end if

        #if "airrohr" in $station_observations_extras
        <!-- airRohr Temperatire/Humidity Observations -->
        <div class="row station-observations-extras-row">
            <div class="station-observations-extras-title">$gettext("airrohr conditions")</div>
            #if "obs" in $station_observations_extras.airrohr
            <div class="station-observations-extras-body">
                <table class="station-observations-extras-table flexible-obs-airrohr-table" cellpadding="0" cellspacing="0">
                    <tbody>
                        #for $x in $station_observations_extras.airrohr.obs
                        <tr>
                            <td class="station-observations-extras-label">$obs.label[$x]</td>
                            #if $x == 'sds011_barometer'
                            #set $class_trend_symbol = 'trend_%s_symbol' % $x
                            #set $class_trend_value = 'trend_%s_formatted' % $x
                            <td class="station-observations-extras-data"><span class="$x" rel="tooltip" title="">$getVar('current.%s' % $x)</span> (<span class="$class_trend_value" rel="tooltip" title="">$getVar('trend.%s.%s' % ($x,'formatted'))</span> <span class="$class_trend_symbol" rel="tooltip" title=""></span>)</td><!-- AJAX -->
                            #else
                            <td class="station-observations-extras-data"><span class="$x" rel="tooltip" title="">$getVar('current.%s' % $x)</span></td><!-- AJAX -->
                            #end if
                        </tr>
                        #end for
                    </tbody>
                </table>
            </div>
            #end if
        </div>
        #end if

        #if "allsky" in $station_observations_extras
        <!-- AllSky Camera 01 Observations -->
        <div class="row station-observations-extras-row">
            <div class="station-observations-extras-title">$gettext("allsky conditions")</div>
            #if "obs" in $station_observations_extras.allsky
            <div class="station-observations-extras-body">
                <table class="station-observations-extras-table flexible-obs-allsky-table" cellpadding="0" cellspacing="0">
                    <tbody>
                        #for $x in $station_observations_extras.allsky.obs
                        <tr>
                            <td class="station-observations-extras-label">$obs.label[$x]</td>
                            #if $x == 'asky_box_barometer'
                            #set $class_trend_symbol = 'trend_%s_symbol' % $x
                            #set $class_trend_value = 'trend_%s_formatted' % $x
                            <td class="station-observations-extras-data"><span class="$x" rel="tooltip" title="">$getVar('current.%s' % $x)</span> (<span class="$class_trend_value" rel="tooltip" title="">$getVar('trend.%s.%s' % ($x,'formatted'))</span> <span class="$class_trend_symbol" rel="tooltip" title=""></span>)</td><!-- AJAX -->
                            #elif $x == 'asky_dome_heater' or $x == 'asky_box_fan' or $x == 'asky_cpu_fan'
                            #set $class_text = '%s_text' % $x
                            <td class="station-observations-extras-data"><span class="$class_text" rel="tooltip" title="">$get_boolean_status($getVar('current.%s' % $x), 'onoff')</span></td><!-- AJAX -->
                            #else
                            <td class="station-observations-extras-data"><span class="$x" rel="tooltip" title="">$getVar('current.%s' % $x)</span></td><!-- AJAX -->
                            #end if
                        </tr>
                        #end for
                    </tbody>
                </table>
            </div>
            #end if
        </div>
        #end if

        #if "wh57" in $station_observations_extras
        <!-- WH57 Sensor -->
        <div class="row station-observations-extras-row">
            <div class="station-observations-extras-title">$gettext("WH57 conditions")</div>
            #if "obs" in $station_observations_extras.wh57
            <div class="station-observations-extras-body">
                <table class="station-observations-extras-table flexible-obs-wh57-table" cellpadding="0" cellspacing="0">
                    <tbody>
                    #for $x in $station_observations_extras.wh57.obs
                        #if $x == 'lightning_strike_count'
                        <tr>
                            <td class="station-observations-extras-label">$gettext("lightning strike sum")</td>
                            <td class="station-observations-extras-data"><span class="$x" rel="tooltip" title="">$getVar('day.%s.%s' % ($x,'sum'))</span></td><!-- AJAX -->
                        </tr>
                        #elif $x == 'wh57_lightning_time'
                        <tr>
                            ##TODO AJAX date format
                            <td class="station-observations-extras-label">$obs.label[$x]</td>
                            <td class="station-observations-extras-data"><span class="bla" rel="tooltip" title="">$getVar('current.%s' % $x)</span></td><!-- AJAX -->
                        </tr>
                        #elif $x == 'wh57_lightning_distance'
                        <tr>
                            <td class="station-observations-extras-label">$obs.label[$x]</td>
                            <td class="station-observations-extras-data"><span class="$x" rel="tooltip" title="">$getVar('current.%s' % $x)</span></td><!-- AJAX -->
                        </tr>
                        #elif $x == 'lightning_distance'
                        #if $getVar('day.%s.has_data' % $x)
                        <tr>
                            <td class="station-observations-extras-label">$gettext("lightning distance min")</td>
                            <td class="station-observations-extras-data"><span class="$x" rel="tooltip" title="">$getVar('day.%s.%s' % ($x,'min'))</span></td><!-- AJAX -->
                        </tr>
                        <tr>
                            <td class="station-observations-extras-label">$gettext("lightning distance avg")</td>
                            <td class="station-observations-extras-data"><span class="$x" rel="tooltip" title="">$getVar('day.%s.%s' % ($x,'avg'))</span></td><!-- AJAX -->
                        </tr>
                        <tr>
                            <td class="station-observations-extras-label">$gettext("lightning distance max")</td>
                            <td class="station-observations-extras-data"><span class="$x" rel="tooltip" title="">$getVar('day.%s.%s' % ($x,'max'))</span></td><!-- AJAX -->
                        </tr>
                        #end if
                        #else
                        <tr>
                            <td class="station-observations-extras-label">$obs.label[$x]</td>
                            <td class="station-observations-extras-data"><span class="$x" rel="tooltip" title="">$getVar('day.%s' % $x)</span></td><!-- AJAX -->
                        </tr>
                        #end if
                    #end for
                    </tbody>
                </table>
            </div>
            #end if
        </div>
        #end if
    </div>
#end if
</div>
