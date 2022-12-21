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
        <td class="label">$obs.label[$x]</td>
        <td class="data">$getVar('current.%s' % $x)</td>
      </tr>
    #elif $x == 'lightning_strike_count'
      <tr>
        <td class="label">$gettext("Lightning strike sum")</td>
        <td class="data">$getVar('day.%s.%s' % ($x,'sum'))</td>
      </tr>
    #elif $x == 'lightning'
      <tr>
        <td class="label">$obs.label[$x]</td>
        <td class="data">$getVar('current.%s' % $x)</td>
      </tr>
    #elif $x == 'lightning_distance'
      <tr>
        <td class="label">$gettext("Lightning distance min")</td>
        <td class="data">$getVar('day.%s.%s' % ($x,'min'))</td>
      </tr>
      <tr>
        <td class="label">$gettext("Lightning distance avg")</td>
        <td class="data">$getVar('day.%s.%s' % ($x,'avg'))</td>
      </tr>
      <tr>
        <td class="label">$gettext("Lightning distance max")</td>
        <td class="data">$getVar('day.%s.%s' % ($x,'max'))</td>
      </tr>
    #else
      <tr>
        <td class="label">$obs.label[$x]</td>
        <td class="data">$getVar('day.%s' % $x)</td>
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
