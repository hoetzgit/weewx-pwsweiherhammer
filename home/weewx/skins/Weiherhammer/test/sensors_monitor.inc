#errorCatcher Echo
#encoding UTF-8
## sensors module for weewx skins
## Copyright Tom Keffer, Matthew Wall
## See LICENSE.txt for your rights
##
## this is a conditional display of sensor data, including connectivity,
## battery status, and various voltages. If there are no data available,
## then this degenerates to nothing displayed.
##
## To include GW1000 sensor battery state information in the Seasons skin
## Sensor Panel list the sensor battery states to display in the
## $sensor_batt_data list. Sensors will be displayed in the order listed. Each
## entry is in the format:
##      (WeeWX sensor battery state field name, decode function name)
## where 'WeeWX sensor battery state field name' is the WeeWX field holding the
## battery state data and 'decode function name' is set as follows depending on
## the sensor type:
##      WH31: 'get_binary_battery_status'
##      WH51: 'get_volt_battery_status'
##      WH57: 'get_level6_battery_status'
##      WH65: 'get_binary_battery_status'
##

##
## This template is only for testing
##

#set $sensor_name = (
     $gettext('sensor_wh65')
    ,$gettext('sensor_wh31_ch1')
    ,$gettext('sensor_wh31_ch2')
    ,$gettext('sensor_wh31_ch3')
    ,$gettext('sensor_wh57')
    ,$gettext('sensor_wh51_ch1')
    ,$gettext('sensor_solar')
    ,$gettext('sensor_airrohr')
    ,$gettext('sensor_allsky')
)

#set $sensor_sig_data = [
     {'obs': 'wh65_sig',     'func': 'get_transmit_signal'}
    ,{'obs': 'wh31_ch1_sig', 'func': 'get_transmit_signal'}
    ,{'obs': 'wh31_ch2_sig', 'func': 'get_transmit_signal'}
    ,{'obs': 'wh31_ch3_sig', 'func': 'get_transmit_signal'}
    ,{'obs': 'wh57_sig',     'func': 'get_transmit_signal'}
    ,{'obs': 'wh51_ch1_sig', 'func': 'get_transmit_signal'}
    ,{'obs': 'solar_sig',    'func': 'get_transmit_signal'}
    ,{'obs': 'airrohr_sig',  'func': 'get_transmit_signal'}
    ,{'obs': 'asky_sig',     'func': 'get_transmit_signal'}
]

#set $sensor_batt_data = [
     {'obs': 'wh65_batt',     'func': 'get_binary_battery_status'}
    ,{'obs': 'wh31_ch1_batt', 'func': 'get_binary_battery_status'}
    ,{'obs': 'wh31_ch2_batt', 'func': 'get_binary_battery_status'}
    ,{'obs': 'wh31_ch3_batt', 'func': 'get_binary_battery_status'}
    ,{'obs': 'wh57_batt',     'func': 'get_level6_battery_status'}
    ,{'obs': 'wh51_ch1_batt', 'func': 'get_volt_battery_status'}
    ,{'obs': 'solar_batt',    'func': 'get_accu_4v_status'}
    ,{'obs': 'na',            'func': 'get_na'}
    ,{'obs': 'na',            'func': 'get_na'}
]

#def get_na($x)
    <span class="status_ok">$x</span>
#end def

#def get_binary_battery_status($x)
    #if $x == 0
    <span class="battery_full"><i class="bi bi-battery-full"></i></span>
    #else
    <span class="battery_low"><i class="bi bi-battery"></i></span>
    #end if
#end def

#def get_volt_battery_status($x)
    #set $val = '%.1fV' % $x
    #if $x <= 1.2
    <span class="battery_alarm">$gettext('empty')</span>
    #elif $x <= 1.3
    <span class="battery_low">$val</span>
    #elif $x <= 1.4
    <span class="battery_half">$val</span>
    #else
    <span class="battery_full">$val</span>
    #end if
#end def

#def get_level6_battery_status($x)
    #if $x <= 1
    <span class="battery_alarm"><i class="bi bi-battery"></i></span>
    #elif $x == 2
    <span class="battery_low"><i class="bi bi-battery"></i></span>
    #elif $x == 3
    <span class="battery_low"><i class="bi bi-battery-half"></i></span>
    #elif $x == 4
    <span class="battery_half"><i class="bi bi-battery-full"></i></span>
    #elif $x == 5
    <span class="battery_full"><i class="bi bi-battery-full"></i></span>
    #elif $x == 6
    <span class="battery_charging"><i class="bi bi-battery-charging"></i></span>
    #end if
#end def

#def get_accu_4v_status($x)
    #set $val = '%.1fV' % $x
    #if $x <= 3.0
    <span class="battery_low">$val</span>
    #else
    <span class="battery_full">$val</span>
    #end if
#end def

#def get_transmit_signal($x)
    #set $class_icon = 'bi bi-reception-%.0f' % $x
    #if $x < 1.0
      #set $class_status = 'signal_alarm'
    #elif $x == 1.0
      #set $class_status = 'signal_poor'
    #elif $x == 2.0
      #set $class_status = 'signal_sufficient'
    #elif $x == 3.0
      #set $class_status = 'signal_good'
    #else 
      #set $class_status = 'signal_very_good'
    #end if
    <span class="$class_status"><i class="$class_icon"></i></span>
#end def

<!-- Start sensors_monitor.inc -->
#set $count = 0
<div class="row sensors-monitor-row">
    <div class="sensors-monitor-table-container">
        <table class="table table-striped table-sm sensors-monitor-table">
            <thead class="thead-light sensors-monitor-table-head">
                <tr>
                    <th scope="col" class="sensors-monitor-table-head-headline">$gettext('sensors')</th>
                    <th scope="col" class="sensors-monitor-table-head-headline">$gettext('signal')</th>
                    <th scope="col" class="sensors-monitor-table-head-headline">$gettext('battery')</th>
                </tr>
            </thead>
            <tbody class="table-group-divider sensors-monitor-table-body sensors-monitor-data">
#for $sensor in $sensor_name
                <tr>
                    <th scope="row" class="sensors-monitor-table-body-sensor">$sensor</th>
    #try
        #set $sig_data = $sensor_sig_data[$count]
        #if $sig_data['obs'] != 'na'
            #set $sig = getattr(self, $sig_data['func'])(getattr($current, $sig_data['obs']).raw)
        #else 
            #set $sig = getattr(self, $sig_data['func'])('---')
        #end if
                    <td class="sensors-monitor-table-body-sig">$sig</td>

    #except (AttributeError, TypeError)
                    <td class="sensors-monitor-table-body-sig"><span class="status_alarm">$gettext('not avalable')</span></td>
        ## there is no data for that sensor
        #pass
    #end try

    #try
        #set $batt_data = $sensor_batt_data[$count]
        #if $batt_data['obs'] != 'na'
            #set $batt = getattr(self, $batt_data['func'])(getattr($current, $batt_data['obs']).raw)
        #else
            #set $batt = getattr(self, $batt_data['func'])('---')
        #end if
                    <td class="sensors-monitor-table-body-batt">$batt</td>
    #except (AttributeError, TypeError)
                    <td class="sensors-monitor-table-body-batt"><span class="status_alarm">$gettext('not avalable')</span></td>
        #pass
    #end try

    #set $count += 1
                </tr>
#end for
            </tbody>
        </table>
    </div>
</div>
<!-- End sensors_monitor.inc -->
