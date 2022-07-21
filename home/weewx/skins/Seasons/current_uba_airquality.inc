## current module for weewx skins
## Copyright Tom Keffer, Matthew Wall
## See LICENSE.txt for your rights
#errorCatcher Echo
#encoding UTF-8

<div id='uba_airquality_widget' class="widget">
  <div class="widget_title">
    $gettext("UBA Airquality Conditions")
    <a class="widget_control"
      onclick="toggle_widget('uba_airquality')">&diams;</a>
  </div>

  <div class="widget_contents">
  <table>
    <tbody>

#if 'observations_uba_airquality' in $DisplayOptions
#for $x in $DisplayOptions.observations_uba_airquality
  #if $getVar('year.%s.has_data' % $x)
    #if $x == 'uba_aqi_category'
      <tr>
        <td class="label">$obs.label[$x]</td>
        #if $current.uba_aqi_category.raw == 0.0
          <td class="data">$obs.label.pws_aqi_very_good</td>
        #else if $current.uba_aqi_category.raw == 1.0
          <td class="data">$obs.label.pws_aqi_good</td>
        #else if $current.uba_aqi_category.raw == 2.0
          <td class="data">$obs.label.pws_aqi_moderate</td>
        #else if $current.uba_aqi_category.raw == 3.0
          <td class="data">$obs.label.pws_aqi_poor</td>
        #else if $current.uba_aqi_category.raw == 4.0
          <td class="data">$obs.label.pws_aqi_very_poor</td>
        #else
          <td class="data">$obs.label.pws_aqi_unknown</td>
        #end if
      </tr>
    #else
      <tr>
        <td class="label">$obs.label[$x]</td>
        <td class="data">$getVar('current.' + $x)</td>
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
