## current module for weewx skins
## Copyright Tom Keffer, Matthew Wall
## See LICENSE.txt for your rights
#errorCatcher Echo
#encoding UTF-8

#if $almanac.hasExtras
  ## Pick a "None string" on the basis of whether the sun is above or below the horizon
  #set $sun_altitude = $almanac.sun.alt
  #if $sun_altitude < 0
    #set $sun_None='<i>%s</i>' % $gettext("Always down")
  #else
    #set $sun_None='<i>%s</i>' % $gettext("Always up")
  #end if

  ## For the change in daylight, pick a string to indicate whether it is more or
  ## less than yesterday:
  #set $sun_visible_change = $almanac.sun.visible_change
  #if $sun_visible_change.raw < 0
    #set $change_str = $gettext("less than yesterday")
  #else
    #set $change_str = $gettext("more than yesterday")
  #end if
#end if

<div id='current_widget' class="widget">
  <div class="widget_title">
    $gettext("Current Conditions")
    <a class="widget_control"
      onclick="toggle_widget('current')">&diams;</a>
  </div>

  <div class="widget_contents">
  <table>
    <tbody>

#set $observations = $to_list($DisplayOptions.get('observations_current', ['outTemp', 'barometer']))

#for $x in $observations
  ##if $getVar('year.%s.has_data' % $x)
    #if $x == 'barometer'
      <tr>
        <td class="label">$obs.label.barometer</td>
        <td class="data">$current.barometer ($trend.barometer.formatted)</td>
      </tr>
    #elif $x == 'windSpeed'
      <tr>
        <td class="label">$obs.label.wind</td>
        <td class="data">$current.windSpeed $current.windDir.ordinal_compass ($current.windDir)</td>
      </tr>
    #elif $x == 'rain'
      <tr>
        <td class="label">$gettext("Rain Today")</td>
        <td class="data">$day.rain.sum</td>
      </tr>
    #elif $x == 'outHumAbs'
      <tr>
        <td class="label">$obs.label.outHumAbs</td>
        <td class="data">$current.outHumAbs.gram_per_meter_cubed</td>
      </tr>
    #elif $x == 'sunshine'
      <tr>
        <td class="label">$obs.label[$x]</td>
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
        $day.sunshineDur.sum.long_form
        </td>
      </tr>
    #elif $x == 'sunshineThreshold'
      <tr>
        <td class="label">$obs.label[$x]</td>
        <td class="data">$getVar('current.%s' % $x)</td>
      </tr>
    #elif $x == 'lastRain'
      <tr>
        <td class="label">$gettext("Last rain")</td>
        <td class="data">$time_at('rain>0')<br>$time_since('rain>0').long_form</td>
      </tr>
    #else
      <tr>
        <td class="label">$obs.label[$x]</td>
        <td class="data">$getVar('current.' + $x)</td>
      </tr>
    #end if
  ##end if
#end for
#if $almanac.hasExtras
     <tr>
       <td class="label">$gettext("Total daylight")</td>
       <td class="data">$almanac.sun.visible.long_form<br/>$sun_visible_change.long_form $change_str</td>
     </tr>
#end if
    </tbody>
  </table>
  </div>

</div>
