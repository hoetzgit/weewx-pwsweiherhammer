## current module for weewx skins
## Copyright Tom Keffer, Matthew Wall
## See LICENSE.txt for your rights
#errorCatcher Echo
#encoding UTF-8

<div id='aeris_airquality_widget' class="widget">
  <div class="widget_title">
    $gettext("Aeris Airquality Conditions")
    <a class="widget_control"
      onclick="toggle_widget('aeris_airquality')">&diams;</a>
  </div>

  <div class="widget_contents">
  <table>
    <tbody>

#if 'observations_aeris_airquality' in $DisplayOptions
#for $x in $DisplayOptions.observations_aeris_airquality
  #if $getVar('year.%s.has_data' % $x)
      <tr>
        <td class="label">$obs.label[$x]</td>
        <td class="data">$getVar('current.%s' % $x)</td>
      </tr>
  #end if
#end for
#else
    <tr><td>No observations specified</td></tr>
#end if

    </tbody>
  </table>
  </div>

</div>
