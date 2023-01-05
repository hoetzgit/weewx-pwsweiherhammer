## current module for weewx skins
## Copyright Tom Keffer, Matthew Wall
## See LICENSE.txt for your rights
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
    <div class="col-lg-6  border-right">
        #if 'observations_current' in $Extras
        <!-- Additional Weather Station Observations-->
        <div class="row observation-extras-row observation-extras-row-left">
            <div class="observation-extras-title">$gettext("Current Conditions")</div>
            <div class="observation-extras-body">
                <table cellpadding="0" cellspacing="0">
                    <tbody>
                        #for $x in $Extras.observations_current
                            #if $x == 'barometer'
                            <tr>
                                <td class="observations-extras-label">$obs.label[$x]</td>
                                ##TODO AJAX Trend
                                <td class="observations-extras-data"><span class="$x">$getVar('current.%s' % $x)</span> ($getVar('trend.%s.%s' % ($x,'formatted')))</td>
                            </tr>
                            #elif $x == 'windSpeed'
                            <tr>
                                <td class="observations-extras-label">$obs.label.wind</td>
                                <td class="observations-extras-data"><span class="$x">$getVar('current.%s' % $x)</span> (<span class="curwinddir">$getVar('current.windDir.ordinal_compass')</span>/<span class="curwinddeg">$getVar('current.windDir')</span>)</td>
                            </tr>
                            #elif $x == 'rain'
                            <tr>
                                <td class="observations-extras-label">$gettext("Rain Today")</td>
                                <td class="observations-extras-data"><span class="dayRain">$getVar('day.%s.%s' % ($x,'sum'))</span></td>
                            </tr>
                            #elif $x == 'sunshineThreshold'
                            <tr>
                                <td class="observations-extras-label">$obs.label[$x]</td>
                                ##TODO AJAX used "sunshineThresholdMin" for updates, not "sunshineThreshold"
                                <td class="observations-extras-data"><span class="TODOsunshineThreshold">$getVar('current.%s' % $x)</span></td>
                            </tr>
                            #elif $x == 'sunshine'
                            <tr>
                                <td class="observations-extras-label">$obs.label[$x]</td>
                                #if $current.sunshine is not None
                                    <td class="observations-extras-data"><span class="current-sunshine-text">$get_boolean_status($getVar('current.%s' % $x), 'yesno')</span>
                                    <br>
                                #else
                                   <td class="observations-extras-data">
                                #end if
                                ##TODO AJAX
                                $day.sunshineDur.sum.format('%(hour)d%(hour_label)s, %(minute)d%(minute_label)s')
                                </td>
                            </tr>
                            #elif $x == 'lastRain'
                            <tr>
                                ##TODO AJAX
                                <td class="observations-extras-label">$gettext("last rain")</td>
                                <td class="observations-extras-data">$last_rain<br>$time_since_last_rain</td>
                            </tr>
                            #else
                            <tr>
                                <td class="observations-extras-label">$obs.label[$x]</td>
                                <td class="observations-extras-data"><span class="$x">$getVar('current.%s' % $x)</span></td>
                            </tr>
                            #end if
                        #end for
                    </tbody>
                </table>
            </div>
        </div>
        #end if

        #if 'observations_indoor' in $Extras
        <!-- Indoor Obbservations -->
        <div class="row observation-extras-row observation-extras-row-right">
            <div class="observation-extras-title">$gettext("Indoor Conditions")</div>
            <div class="observation-extras-body">
                <table cellpadding="0" cellspacing="0">
                    <tbody>
                        #for $x in $Extras.observations_indoor
                        <tr>
                            <td class="observations-extras-label">$obs.label[$x]</td>
                            <td class="observations-extras-data"><span class="$x">$getVar('current.%s' % $x)</span></td>
                        </tr>
                        #end for
                    </tbody>
                </table>
            </div>
        </div>
        #end if
    </div>

    <div class="col-lg-6">
        #if 'observations_solar' in $Extras
        <!-- Solar Weather Station -->
        <div class="row observation-extras-row">
            <div class="observation-extras-title">$gettext("Solar Conditions")</div>
            <div class="observation-extras-body">
                <table cellpadding="0" cellspacing="0">
                    <tbody>
                        #for $x in $Extras.observations_solar
                        <tr>
                            <td class="observations-extras-label">$obs.label[$x]</td>
                            #if $x == 'solar_barometer'
                            ##TODO AJAX Trend
                            <td class="observations-extras-data"><span class="$x">$getVar('current.%s' % $x)</span> ($getVar('trend.%s.%s' % ($x,'formatted')))</td>
                            #else
                            <td class="observations-extras-data"><span class="$x">$getVar('current.%s' % $x)</td>
                            #end if
                        </tr>
                        #end for
                    </tbody>
                </table>
            </div>
        </div>
        #end if

        #if 'observations_sds011' in $Extras
        <!-- airRohr Temperatire/Humidity Observations -->
        <div class="row observation-extras-row">
            <div class="observation-extras-title">$gettext("SDS011 Conditions")</div>
            <div class="observation-extras-body">
                <table cellpadding="0" cellspacing="0">
                    <tbody>
                        #for $x in $Extras.observations_sds011
                        <tr>
                            <td class="observations-extras-label">$obs.label[$x]</td>
                            #if $x == 'sds011_barometer'
                            ##TODO AJAX Trend
                            <td class="observations-extras-data"><span class="$x">$getVar('current.%s' % $x)</span> ($getVar('trend.%s.%s' % ($x,'formatted')))</td>
                            #else
                            <td class="observations-extras-data"><span class="$x">$getVar('current.%s' % $x)</span></td>
                            #end if
                        </tr>
                        #end for
                    </tbody>
                </table>
            </div>
        </div>
        #end if

        #if 'observations_allskycam01' in $Extras
        <!-- AllSky Camera 01 Observations -->
        <div class="row observation-extras-row">
            <div class="observation-extras-title">$gettext("AllSkycam01 Conditions")</div>
            <div class="observation-extras-body">
                <table cellpadding="0" cellspacing="0">
                    <tbody>
                        #for $x in $Extras.observations_allskycam01
                        <tr>
                            <td class="observations-extras-label">$obs.label[$x]</td>
                            #if $x == 'asky_box_barometer'
                            ##TODO AJAX Trend
                            <td class="observations-extras-data"><span class="$x">$getVar('current.%s' % $x)</span> ($getVar('trend.%s.%s' % ($x,'formatted')))</td>
                            #elif $x == 'asky_dome_heater' or $x == 'asky_box_fan' or $x == 'asky_cpu_fan'
                            <td class="observations-extras-data"><span class="$x">$get_boolean_status($getVar('current.%s' % $x), 'onoff')</span></td>
                            #else
                            <td class="observations-extras-data"><span class="$x">$getVar('current.%s' % $x)</span></td>
                            #end if
                        </tr>
                        #end for
                    </tbody>
                </table>
            </div>
        </div>
        #end if

        #if 'observations_wh57' in $Extras
        <!-- WH57 Sensor -->
        <div class="row observation-extras-row">
            <div class="observation-extras-title">$gettext("WH57 Conditions")</div>
            <div class="observation-extras-body">
                <table cellpadding="0" cellspacing="0">
                    <tbody>
                    #for $x in $Extras.observations_wh57
                        #if $x == 'lightning_strike_count'
                        <tr>
                            <td class="observations-extras-label">$gettext("Lightning strike sum")</td>
                            <td class="observations-extras-data"><span class="$x">$getVar('day.%s.%s' % ($x,'sum'))</span></td>
                        </tr>
                        #elif $x == 'wh57_lightning_time'
                        <tr>
                            <td class="observations-extras-label">$obs.label[$x]</td>
                            <td class="observations-extras-data">$getVar('current.%s' % $x)</td>
                        </tr>
                        #elif $x == 'wh57_lightning_distance'
                        <tr>
                            <td class="observations-extras-label">$obs.label[$x]</td>
                            <td class="observations-extras-data"><span class="$x">$getVar('day.%s' % $x)</span></td>
                        </tr>
                        #elif $x == 'lightning_distance'
                        #if $getVar('day.%s.has_data' % $x)
                        <tr>
                            <td class="observations-extras-label">$gettext("Lightning distance min")</td>
                            <td class="observations-extras-data"><span class="$x">$getVar('day.%s.%s' % ($x,'min'))</span></td>
                        </tr>
                        <tr>
                            <td class="observations-extras-label">$gettext("Lightning distance avg")</td>
                            <td class="observations-extras-data"><span class="$x">$getVar('day.%s.%s' % ($x,'avg'))</span></td>
                        </tr>
                        <tr>
                            <td class="observations-extras-label">$gettext("Lightning distance max")</td>
                            <td class="observations-extras-data"><span class="$x">$getVar('day.%s.%s' % ($x,'max'))</span></td>
                        </tr>
                        #end if
                        #else
                        <tr>
                            <td class="observations-extras-label">$obs.label[$x]</td>
                            <td class="observations-extras-data"><span class="$x">$getVar('day.%s' % $x)</span></td>
                        </tr>
                        #end if
                    #end for
                    </tbody>
                </table>
            </div>
        </div>
        #end if
    </div>
 </div>




