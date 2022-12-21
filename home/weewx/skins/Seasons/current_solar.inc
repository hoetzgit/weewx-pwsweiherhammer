## current module for weewx skins
## Copyright Tom Keffer, Matthew Wall
## See LICENSE.txt for your rights
#errorCatcher Echo
#encoding UTF-8

<div id='solar_widget' class="widget">
  <div class="widget_title">
    $gettext("Solar Conditions")
    <a class="widget_control"
      onclick="toggle_widget('solar')">&diams;</a>
  </div>

  <div class="widget_contents">
    <table>
      <tbody>
        #if 'observations_solar' in $DisplayOptions
        #for $x in $DisplayOptions.observations_solar
        <tr>
          <td class="label">$obs.label[$x]</td>
          #if $x == 'solar_barometer'
          <td class="data">$getVar('current.%s' % $x) ($getVar('trend.%s.%s' % ($x,'formatted')))</td>
          #else
          <td class="data">$getVar('current.%s' % $x)</td>
          #end if
        </tr>
        #end for
        #end if
      </tbody>
    </table>
  </div>
</div>
