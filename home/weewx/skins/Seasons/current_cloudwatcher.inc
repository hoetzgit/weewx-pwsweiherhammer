## current module for weewx skins
## Copyright Tom Keffer, Matthew Wall
## See LICENSE.txt for your rights
#errorCatcher Echo
#encoding UTF-8

<div id='cloudwatcher_widget' class="widget">
  <div class="widget_title">
    $gettext("Cloudwatcher Conditions")
    <a class="widget_control"
      onclick="toggle_widget('cloudwatcher')">&diams;</a>
  </div>

  <div class="widget_contents">
  <table>
    <tbody>

#if 'observations_cloudwatcher' in $DisplayOptions
#for $x in $DisplayOptions.observations_cloudwatcher
  #if $getVar('year.%s.has_data' % $x)
    #if $x == 'cloudwatcher_weathercode'
      <tr>
        <td class="label">$obs.label[$x]</td>
        #if $current.cloudwatcher_weathercode.raw == 0.0
          <td class="data">$obs.label.cloudwatcher_weathercode_0</td>
        #else if $current.cloudwatcher_weathercode.raw == 1.0
          <td class="data">$obs.label.cloudwatcher_weathercode_1</td>
        #else if $current.cloudwatcher_weathercode.raw == 2.0
          <td class="data">$obs.label.cloudwatcher_weathercode_2</td>
        #else if $current.cloudwatcher_weathercode.raw == 3.0
          <td class="data">$obs.label.cloudwatcher_weathercode_3</td>
        #else if $current.cloudwatcher_weathercode.raw == 4.0
          <td class="data">$obs.label.cloudwatcher_weathercode_4</td>
        #else if $current.cloudwatcher_weathercode.raw == 63.0
          <td class="data">$obs.label.cloudwatcher_weathercode_63</td>
        #else if $current.cloudwatcher_weathercode.raw == 95.0
          <td class="data">$obs.label.cloudwatcher_weathercode_95</td>
        #else if $current.cloudwatcher_weathercode.raw == 96.0
          <td class="data">$obs.label.cloudwatcher_weathercode_96</td>
        #else
          <td class="data">$obs.label.cloudwatcher_weathercode_unknown</td>
        #end if
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
