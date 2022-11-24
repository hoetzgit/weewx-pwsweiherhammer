## current module for weewx skins
## Copyright Tom Keffer, Matthew Wall
## See LICENSE.txt for your rights
#errorCatcher Echo
#encoding UTF-8

<div id='indoor_widget' class="widget">
  <div class="widget_title">
    $gettext("Indoor Conditions")
    <a class="widget_control"
      onclick="toggle_widget('indoor')">&diams;</a>
  </div>

  <div class="widget_contents">
  <table>
    <tbody>

#set $observations = $to_list($DisplayOptions.get('observations_indoor', ['inTemp', 'inHumidity']))

#if 'observations_indoor' in $DisplayOptions
#for $x in $observations
  #if $getVar('current.%s.has_data' % $x)
      <tr>
        <td class="label">$obs.label[$x]</td>
        <td class="data">$getVar('current.' + $x)</td>
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
