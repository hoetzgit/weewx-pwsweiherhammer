## current module for weewx skins
## Copyright Tom Keffer, Matthew Wall
## See LICENSE.txt for your rights
#errorCatcher Echo
#encoding UTF-8

## use this span to determine whether there are any data to consider.
#set $recent=$span($day_delta=30, boundary='midnight')

#def get_boolean_status($x)
#if $x is None
<span class="status_unknown">$gettext('UNKNOWN')</span>
#elif $x > 0.0
<span class="status_low">$gettext('ON')</span>
#else
<span class="status_ok">$gettext('OFF')</span>
#end if
#end def

#set $climate_controls = $to_list($DisplayOptions.get('observations_allskycam01_climatecontrol', ['asky_dome_heater', 'asky_box_fan', 'asky_cpu_fan']))

#set $have_climate_controls = 0
#for $x in $climate_controls
  #if $getattr($recent, $x).has_data
    #set $have_climate_controls = 1
  #end if
#end for


<div id='allskycam01_widget' class="widget">
  <div class="widget_title">
    $gettext("Allskycam01 Conditions")
    <a class="widget_control"
      onclick="toggle_widget('allskycam01')">&diams;</a>
  </div>

  <div class="widget_contents">
  <table>
    <tbody>

#if 'observations_allskycam01' in $DisplayOptions
#for $x in $DisplayOptions.observations_allskycam01
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

#if $have_climate_controls
  <table>
    <tbody>
    <tr><th>$gettext("Climate control")</th><th></th></tr>
#for $x in $climate_controls
  #if $getattr($recent, $x).has_data
    <tr>
      <td class="label">$obs.label[$x]</td>
      <td class="data">$get_boolean_status($getVar('current.%s.raw' % $x))</td>
    </tr>
  #end if
#end for
    </tbody>
  </table>
#end if

  </div>

</div>
