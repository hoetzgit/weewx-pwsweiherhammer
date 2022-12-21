## current module for weewx skins
## Copyright Tom Keffer, Matthew Wall
## See LICENSE.txt for your rights
#errorCatcher Echo
#encoding UTF-8

<div class="row">
    <div class="col-lg-6 border-right">
        #if 'observations_current' in $Extras
        <!-- Additional Weather Station Observations-->
        <div class="row observation-extras-row">
            <div class="observation-extras-title">$gettext("Current Conditions")</div>
            <div class="observation-extras-body">
                <table cellpadding="0" cellspacing="0">
                    <tbody>
                        #for $x in $Extras.observations_current
                            #if $x == 'barometer'
                            <tr>
                                <td class="observations-extras-label">$obs.label[$x]</td>
                                <td class="data"><span class="$x">$getVar('current.%s' % $x)</span> ($getVar('trend.%s.%s' % ($x,'formatted')))</td>
                            </tr>
                            #elif $x == 'windSpeed'
                            <tr>
                                <td class="observations-extras-label">$obs.label.wind</td>
                                <td class="data"><span class="$x">$getVar('current.%s' % $x)</span> $getVar('current.windDir.ordinal_compass') ($getVar('current.windDir'))</td>
                            </tr>
                            #elif $x == 'rain'
                            <tr>
                                <td class="observations-extras-label">$gettext("Rain Today")</td>
                                <td class="data"><span class="$x">$getVar('day.%s.%s' % ($x,'sum'))</span></td>
                            </tr>
                            #elif $x == 'sunshine'
                            <tr>
                                <td class="observations-extras-label">$obs.label[$x]</td>
                                #if $current.sunshine.raw is not None
                                    #if $current.sunshine.raw > 0.0
                                    <td class="data">$gettext("YES")
                                    #else
                                    <td class="data">$gettext("NO")
                                    #end if
                                    <br>
                                #else
                                   <td class="data">
                                #end if
                                $day.sunshineDur.sum.format('%(hour)d%(hour_label)s, %(minute)d%(minute_label)s')
                                </td>
                            </tr>
                            #elif $x == 'lastRain'
                            <tr>
                                <td class="observations-extras-label">$gettext("last rain")</td>
                                <td class="data">$last_rain<br>$time_since_last_rain</td>
                            </tr>
                            #else
                            <tr>
                                <td class="observations-extras-label">$obs.label[$x]</td>
                                <td class="data"><span class="$x">$getVar('current.%s' % $x)</span></td>
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
        <div class="row observation-extras-row">
            <div class="observation-extras-title">$gettext("Indoor Conditions")</div>
            <div class="observation-extras-body">
                <table cellpadding="0" cellspacing="0">
                    <tbody>
                        #for $x in $Extras.observations_indoor
                        <tr>
                            <td class="observations-extras-label">$obs.label[$x]</td>
                            <td class="data"><span class="$x">$getVar('current.%s' % $x)</span></td>
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
                            <td class="data"><span class="$x">$getVar('current.%s' % $x)</span> ($getVar('trend.%s.%s' % ($x,'formatted')))</td>
                            #else
                            <td class="data"><span class="$x">$getVar('current.%s' % $x)</span></td>
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
                        #if $x == 'lightning_last_time'
                        <tr>
                            <td class="observations-extras-label">$obs.label[$x]</td>
                            <td class="data">$getVar('current.%s' % $x)</td>
                            ##TODO AJAX <td class="data"><span class="$x">$getVar('current.%s' % $x)</span></td>
                        </tr>
                        #elif $x == 'lightning_strike_count'
                        <tr>
                            <td class="observations-extras-label">$gettext("Lightning strike sum")</td>
                            <td class="data"><span class="$x">$getVar('day.%s.%s' % ($x,'sum'))</span></td>
                        </tr>
                        #elif $x == 'lightning'
                        <tr>
                            <td class="observations-extras-label">$obs.label[$x]</td>
                            ##TODO AJAX  <td class="data"><span class="$x">$getVar('current.%s' % $x)</span></td>
                            <td class="data">$getVar('current.%s' % $x)</td>
                        </tr>
                        #elif $x == 'lightning_distance'
                        <tr>
                            <td class="observations-extras-label">$gettext("Lightning distance min")</td>
                            <td class="data"><span class="$x">$getVar('day.%s.%s' % ($x,'min'))</span></td>
                        </tr>
                        <tr>
                            <td class="observations-extras-label">$gettext("Lightning distance avg")</td>
                            <td class="data"><span class="$x">$getVar('day.%s.%s' % ($x,'avg'))</span></td>
                        </tr>
                        <tr>
                            <td class="observations-extras-label">$gettext("Lightning distance max")</td>
                            <td class="data"><span class="$x">$getVar('day.%s.%s' % ($x,'max'))</span></td>
                        </tr>
                        #else
                        <tr>
                            <td class="observations-extras-label">$obs.label[$x]</td>
                            <td class="data"><span class="$x">$getVar('day.%s' % $x)</span></td>
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




