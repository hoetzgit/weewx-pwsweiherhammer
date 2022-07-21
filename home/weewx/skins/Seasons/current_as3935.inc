## current module for weewx skins
## Copyright Tom Keffer, Matthew Wall
## See LICENSE.txt for your rights
#errorCatcher Echo
#encoding UTF-8

<div id='as3935_widget' class="widget">
  <div class="widget_title">
    $gettext("AS3935 Conditions")
    <a class="widget_control"
      onclick="toggle_widget('as3935')">&diams;</a>
  </div>

  <div class="widget_contents">
  <table>
    <tbody>

#if 'observations_as3935' in $DisplayOptions
#for $x in $DisplayOptions.observations_as3935
  #if $getVar('year.%s.has_data' % $x)
    #if $x == 'as3935_lightning_last_time'
      <tr>
        <td class="label">$gettext("AS3935 Lightning last time")</td>
        <td class="data">$alltime.as3935_lightning_last_time.max</td>
      </tr>
    #elif $x == 'as3935_lightning_strike_count'
      <tr>
        <td class="label">$gettext("AS3935 Lightning strike sum")</td>
        <td class="data">$day.as3935_lightning_strike_count.sum</td>
      </tr>
    #elif $x == 'as3935_lightning_distance'
      <tr>
        <td class="label">$gettext("AS3935 Lightning distance min")</td>
        <td class="data">$day.as3935_lightning_distance.min</td>
      </tr>
      <tr>
        <td class="label">$gettext("AS3935 Lightning distance max")</td>
        <td class="data">$day.as3935_lightning_distance.max</td>
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
