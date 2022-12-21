## current module for weewx skins
## Copyright Tom Keffer, Matthew Wall
## See LICENSE.txt for your rights
#errorCatcher Echo
#encoding UTF-8

#def get_boolean_status($val)
#if $val is None
<span class="status_unknown">$gettext('unknown')</span>
#elif $val > 0.0
<span class="status_ok_on">$gettext('on')</span>
#else
<span class="status_ok_off">$gettext('off')</span>
#end if
#end def

#def get_voltage_status($rawval, $val)
#if $rawval is None
<span class="status_unknown">$gettext('unknown')</span>
#elif rawval > 3.8
<span class="status_ok">$val</span>
#else
<span class="status_low">$val</span>
#end if
#end def

#def get_indoor_temp_status($rawval, $val, $room)
#if $rawval is None
<span class="status_unknown">$gettext('unknown')</span>
#else
#if $room == 'livingroom' or $room == 'office'
  #if rawval <= 12.0
  <span class="indoor_temp_very_cold" title="$gettext('very cold')">$val</span>
  #elif rawval <= 20.0
  <span class="indoor_temp_cold" title="$gettext('cold')">$val</span>
  #elif rawval <= 22.0
  <span class="indoor_temp_optimal" title="$gettext('optimal')">$val</span>
  #elif rawval <= 30.0
  <span class="indoor_temp_warm" title="$gettext('warm')">$val</span>
  #else
  <span class="indoor_temp_very_warm" title="$gettext('very warm')">$val</span>
  #end if
#elif $room == 'bedroom'
  #if rawval <= 10.0
  <span class="indoor_temp_very_cold" title="$gettext('very cold')">$val</span>
  #elif rawval <= 16.0
  <span class="indoor_temp_cold" title="$gettext('cold')">$val</span>
  #elif rawval <= 18.0
  <span class="indoor_temp_optimal" title="$gettext('optimal')">$val</span>
  #elif rawval <= 25.0
  <span class="indoor_temp_warm" title="$gettext('warm')">$val</span>
  #else
  <span class="indoor_temp_very_warm" title="$gettext('very warm')">$val</span>
  #end if
#elif $room == 'bathroom'
  #if rawval <= 15.0
  <span class="indoor_temp_very_cold" title="$gettext('very cold')">$val</span>
  #elif rawval <= 20.0
  <span class="indoor_temp_cold" title="$gettext('cold')">$val</span>
  #elif rawval <= 23.0
  <span class="indoor_temp_optimal" title="$gettext('optimal')">$val</span>
  #elif rawval <= 30.0
  <span class="indoor_temp_warm" title="$gettext('warm')">$val</span>
  #else
  <span class="indoor_temp_very_warm" title="$gettext('very warm')">$val</span>
  #end if
#else
<span class="status_unknown">$gettext('unknown')</span>
#end if
#end if
#end def

#def get_indoor_humidity_status($rawval, $val, $room)
#if $rawval is None
<span class="status_unknown">$gettext('unknown')</span>
#else
#if $room == 'livingroom' or $room == 'office' or $room == 'bedroom'
  #if rawval <= 35.0
  <span class="indoor_humidity_very_dry" title="$gettext('very dry')">$val</span>
  #elif rawval <= 40.0
  <span class="indoor_humidity_dry" title="$gettext('dry')">$val</span>
  #elif rawval <= 60.0
  <span class="indoor_humidity_optimal" title="$gettext('optimal')">$val</span>
  #elif rawval <= 65.0
  <span class="indoor_humidity_moist" title="$gettext('moist')">$val</span>
  #else
  <span class="indoor_humidity_very_moist" title="$gettext('very moist')">$val</span>
  #end if
#elif $room == 'bathroom'
  #if rawval <= 40.0
  <span class="indoor_humidity_very_dry" title="$gettext('very dry')">$val</span>
  #elif rawval <= 50.0
  <span class="indoor_humidity_dry" title="$gettext('dry')">$val</span>
  #elif rawval <= 70.0
  <span class="indoor_humidity_optimal" title="$gettext('optimal')">$val</span>
  #elif rawval <= 80.0
  <span class="indoor_humidity_moist" title="$gettext('moist')">$val</span>
  #else
  <span class="indoor_humidity_very_moist" title="$gettext('very moist')">$val</span>
  #end if
#else
<span class="status_unknown">$gettext('unknown')</span>
#end if
#end if
#end def

<div class="row">
    <div class="col-lg-6">
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
                            ##TODO AJAX
                            #if $x == 'inTemp'
                            <td class="data">$get_indoor_temp_status($getVar('current.%s.raw' % $x), $getVar('current.%s' % $x), 'livingroom')</td>
                            #elif $x == 'extraTemp1'
                            <td class="data">$get_indoor_temp_status($getVar('current.%s.raw' % $x), $getVar('current.%s' % $x), 'office')</td>
                            #elif $x == 'extraTemp2'
                            <td class="data">$get_indoor_temp_status($getVar('current.%s.raw' % $x), $getVar('current.%s' % $x), 'bathroom')</td>
                            #elif $x == 'extraTemp3'
                            <td class="data">$get_indoor_temp_status($getVar('current.%s.raw' % $x), $getVar('current.%s' % $x), 'bedroom')</td>
                            #elif $x == 'inHumidity'
                            <td class="data">$get_indoor_humidity_status($getVar('current.%s.raw' % $x), $getVar('current.%s' % $x), 'livingroom')</td>
                            #elif $x == 'extraHumid1'
                            <td class="data">$get_indoor_humidity_status($getVar('current.%s.raw' % $x), $getVar('current.%s' % $x), 'office')</td>
                            #elif $x == 'extraHumid2'
                            <td class="data">$get_indoor_humidity_status($getVar('current.%s.raw' % $x), $getVar('current.%s' % $x), 'bathroom')</td>
                            #elif $x == 'extraHumid3'
                            <td class="data">$get_indoor_humidity_status($getVar('current.%s.raw' % $x), $getVar('current.%s' % $x), 'bedroom')</td>
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
    </div>

    <div class="col-lg-6 border-left">
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
                            #elif $x == 'solar_voltage'
                            ##TODO AJAX
                            <td class="data">$get_voltage_status($getVar('current.%s.raw' % $x), $getVar('current.%s' % $x))</td>
                            #else
                            <td class="data"><span class="$x">$getVar('current.%s' % $x)</td>
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
                            <td class="data"><span class="$x">$getVar('current.%s' % $x)</span> ($getVar('trend.%s.%s' % ($x,'formatted')))</td>
                            #elif $x == 'asky_dome_heater' or $x == 'asky_box_fan' or $x == 'asky_cpu_fan'
                            ##TODO AJAX
                            <td class="data">$get_boolean_status($getVar('current.%s.raw' % $x))</td>
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




