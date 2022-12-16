## current module for weewx skins
## Copyright Tom Keffer, Matthew Wall
## See LICENSE.txt for your rights
#errorCatcher Echo
#encoding UTF-8

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
  #if $getVar('year.%s.has_data' % $x)
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
        $day.sunshineDur.sum.format('%(hour)d%(hour_label)s, %(minute)d%(minute_label)s')
        </td>
      </tr>
    #else
      <tr>
        <td class="label">$obs.label[$x]</td>
        <td class="data">$getVar('current.' + $x)</td>
      </tr>
    #end if
  #end if

  #if $getVar('current.%s.has_data' % $x)
    #if $x == 'sunshineThreshold'
      <tr>
        <td class="label">$obs.label[$x]</td>
        <td class="data">$getVar('current.' + $x)</td>
      </tr>
    #end if
  #end if

  #if $x == 'lastRain'
    <tr>
      <td class="label">$gettext("Last rain")</td>
      <td class="data">$last_rain<br>$time_since_last_rain</td>
    </tr>
  #end if

#end for

    </tbody>
  </table>
  </div>

</div>
