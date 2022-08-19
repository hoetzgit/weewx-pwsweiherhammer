## current module for weewx skins
## Copyright Tom Keffer, Matthew Wall
## See LICENSE.txt for your rights
#errorCatcher Echo
#encoding UTF-8

<div id='wh57_widget' class="widget">
  <div class="widget_title">
    $gettext("WH57 Conditions")
    <a class="widget_control"
      onclick="toggle_widget('wh57')">&diams;</a>
  </div>

  <div class="widget_contents">
  <table>
    <tbody>

#if 'observations_wh57' in $DisplayOptions
#for $x in $DisplayOptions.observations_wh57
  #if $getVar('year.%s.has_data' % $x)
    #if $x == 'lightning_last_time'
      <tr>
        <td class="label">$gettext("Lightning last time")</td>
        <td class="data">$current.lightning_last_time</td>
      </tr>
    #elif $x == 'lightning_strike_count'
      <tr>
        <td class="label">$gettext("Lightning strike sum")</td>
        <td class="data">$day.lightning_strike_count.sum</td>
      </tr>
    #elif $x == 'lightning_distance'
      <tr>
        <td class="label">$gettext("Lightning distance min")</td>
        <td class="data">$day.lightning_distance.min</td>
      </tr>
      <tr>
        <td class="label">$gettext("Lightning distance avg")</td>
        <td class="data">$day.lightning_distance.avg</td>
      </tr>
      <tr>
        <td class="label">$gettext("Lightning distance max")</td>
        <td class="data">$day.lightning_distance.max</td>
      </tr>
      <tr>
        <td class="label">$gettext("Lightning distance last")</td>
        <td class="data">$latest.lightning_distance</td>
      </tr>
    #else
      <tr>
        <td class="label">$obs.label[$x]</td>
        <td class="data">$getVar('day.' + $x)</td>
      </tr>
    #end if
  #end if
#end for
#else
    <tr><td>No observations specified</td></tr>
#end if

    </tbody>
  </table>
  </div>

</div>
