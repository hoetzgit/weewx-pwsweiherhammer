## current module for weewx skins
## Copyright Tom Keffer, Matthew Wall
## See LICENSE.txt for your rights
#errorCatcher Echo
#encoding UTF-8

<div id='sds011_widget' class="widget">
  <div class="widget_title">
    $gettext("SDS011 Conditions")
    <a class="widget_control"
      onclick="toggle_widget('sds011')">&diams;</a>
  </div>

  <div class="widget_contents">
  <table>
    <tbody>

#if 'observations_sds011' in $DisplayOptions
#for $x in $DisplayOptions.observations_sds011
  #if $getVar('year.%s.has_data' % $x)
    #if $x == 'barometer'
      <tr>
        <td class="label">$obs.label.barometer</td>
        <td class="data">$current.barometer ($trend.barometer.formatted)</td>
      </tr>
    #else
      <tr>
        <td class="label">$obs.label[$x]</td>
        <td class="data">$getVar('current.%s' % $x)</td>
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
