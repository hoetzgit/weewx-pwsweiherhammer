#errorCatcher Echo
#encoding UTF-8
#import datetime
#from datetime import timedelta

<script type="text/javascript">
    var moment_locale = "$system_locale_js";
    moment.locale(moment_locale);
    
    jQuery(document).ready(function() {
        jQuery("#year-outtemp-max-ts").text( tzAdjustedMoment($year.outTemp.maxtime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        jQuery("#at-outtemp-max-ts").text( tzAdjustedMoment($alltime.outTemp.maxtime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        
        jQuery("#year-outtemp-min-ts").text( tzAdjustedMoment($year.outTemp.mintime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        jQuery("#at-outtemp-min-ts").text( tzAdjustedMoment($alltime.outTemp.mintime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        
        jQuery("#year-dewpoint-max-ts").text( tzAdjustedMoment($year.dewpoint.maxtime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        jQuery("#at-dewpoint-max-ts").text( tzAdjustedMoment($alltime.dewpoint.maxtime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        
        jQuery("#year-dewpoint-min-ts").text( tzAdjustedMoment($year.dewpoint.mintime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        jQuery("#at-dewpoint-min-ts").text( tzAdjustedMoment($alltime.dewpoint.mintime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        
        #if $year.appTemp.has_data
        jQuery("#year-apptemp-max-ts").text( tzAdjustedMoment($year.appTemp.maxtime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        jQuery("#year-apptemp-min-ts").text( tzAdjustedMoment($year.appTemp.mintime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        #end if
        #if $alltime.appTemp.has_data
        jQuery("#at-apptemp-max-ts").text( tzAdjustedMoment($alltime.appTemp.maxtime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        jQuery("#at-apptemp-min-ts").text( tzAdjustedMoment($alltime.appTemp.mintime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        #end if
        
        jQuery("#year-heatindex-max-ts").text( tzAdjustedMoment($year.heatindex.maxtime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        jQuery("#at-heatindex-max-ts").text( tzAdjustedMoment($alltime.heatindex.maxtime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        
        jQuery("#year-windchill-min-ts").text( tzAdjustedMoment($year.windchill.mintime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        jQuery("#at-windchill-min-ts").text( tzAdjustedMoment($alltime.windchill.mintime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        
        jQuery("#year-outtemp-range-max-ts").text( tzAdjustedMoment($year_outTemp_range_max[0]).format( "$obs.label.time_extreme_page_month_day_year" ) );
        jQuery("#at-outtemp-range-max-ts").text( tzAdjustedMoment($at_outTemp_range_max[0]).format( "$obs.label.time_extreme_page_month_day_year" ) );
        
        jQuery("#year-outtemp-range-min-ts").text( tzAdjustedMoment($year_outTemp_range_min[0]).format( "$obs.label.time_extreme_page_month_day_year" ) );
        jQuery("#at-outtemp-range-min-ts").text( tzAdjustedMoment($at_outTemp_range_min[0]).format( "$obs.label.time_extreme_page_month_day_year" ) );
        
        jQuery("#year-windGust-max-ts").text( tzAdjustedMoment($year.windGust.maxtime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        jQuery("#at-windGust-max-ts").text( tzAdjustedMoment($alltime.windGust.maxtime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        
        #if $year.windrun.has_data
        jQuery("#year-windrun-max-ts").text( tzAdjustedMoment($year.windrun.maxsumtime.raw).format( "$obs.label.time_extreme_page_month_day_year" ) );
        #end if
        #if $alltime.windrun.has_data
        jQuery("#at-windrun-max-ts").text( tzAdjustedMoment($alltime.windrun.maxsumtime.raw).format( "$obs.label.time_extreme_page_month_day_year" ) );
        #end if
        
        
        jQuery("#year-outHumidity-max-ts").text( tzAdjustedMoment($year.outHumidity.maxtime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        jQuery("#at-outHumidity-max-ts").text( tzAdjustedMoment($alltime.outHumidity.maxtime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        
        jQuery("#year-outHumidity-min-ts").text( tzAdjustedMoment($year.outHumidity.mintime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        jQuery("#at-outHumidity-min-ts").text( tzAdjustedMoment($alltime.outHumidity.mintime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        
        jQuery("#year-outHumAbs-max-ts").text( tzAdjustedMoment($year.outHumAbs.maxtime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        jQuery("#at-outHumAbs-max-ts").text( tzAdjustedMoment($alltime.outHumAbs.maxtime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        
        jQuery("#year-outHumAbs-min-ts").text( tzAdjustedMoment($year.outHumAbs.mintime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        jQuery("#at-outHumAbs-min-ts").text( tzAdjustedMoment($alltime.outHumAbs.mintime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        
        jQuery("#year-barometer-max-ts").text( tzAdjustedMoment($year.barometer.maxtime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        jQuery("#at-barometer-max-ts").text( tzAdjustedMoment($alltime.barometer.maxtime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        
        jQuery("#year-barometer-min-ts").text( tzAdjustedMoment($year.barometer.mintime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        jQuery("#at-barometer-min-ts").text( tzAdjustedMoment($alltime.barometer.mintime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        
        #if $year.radiation.has_data
        jQuery("#year-radiation-max-ts").text( tzAdjustedMoment($year.radiation.maxtime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        jQuery("#at-radiation-max-ts").text( tzAdjustedMoment($alltime.radiation.maxtime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        #end if
        
        #if $year.UV.has_data
        jQuery("#year-UV-max-ts").text( tzAdjustedMoment($year.UV.maxtime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        jQuery("#at-UV-max-ts").text( tzAdjustedMoment($alltime.UV.maxtime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        #end if
        
        // indoor
        jQuery("#year-inTemp-max-ts").text( moment.unix($year.inTemp.maxtime.raw).format( "$obs.label.time_records_page_full_date" ) );
        jQuery("#at-inTemp-max-ts").text( moment.unix($alltime.inTemp.maxtime.raw).format( "$obs.label.time_records_page_full_date" ) );
        
        jQuery("#year-inTemp-min-ts").text( moment.unix($year.inTemp.mintime.raw).format( "$obs.label.time_records_page_full_date" ) );
        jQuery("#at-inTemp-min-ts").text( moment.unix($alltime.inTemp.mintime.raw).format( "$obs.label.time_records_page_full_date" ) );
        
        jQuery("#year-extraTemp1-max-ts").text( moment.unix($year.extraTemp1.maxtime.raw).format( "$obs.label.time_records_page_full_date" ) );
        jQuery("#at-extraTemp1-max-ts").text( moment.unix($alltime.extraTemp1.maxtime.raw).format( "$obs.label.time_records_page_full_date" ) );
        
        jQuery("#year-extraTemp1-min-ts").text( moment.unix($year.extraTemp1.mintime.raw).format( "$obs.label.time_records_page_full_date" ) );
        jQuery("#at-extraTemp1-min-ts").text( moment.unix($alltime.extraTemp1.mintime.raw).format( "$obs.label.time_records_page_full_date" ) );
        
        jQuery("#year-extraTemp2-max-ts").text( moment.unix($year.extraTemp2.maxtime.raw).format( "$obs.label.time_records_page_full_date" ) );
        jQuery("#at-extraTemp2-max-ts").text( moment.unix($alltime.extraTemp2.maxtime.raw).format( "$obs.label.time_records_page_full_date" ) );
        
        jQuery("#year-extraTemp2-min-ts").text( moment.unix($year.extraTemp2.mintime.raw).format( "$obs.label.time_records_page_full_date" ) );
        jQuery("#at-extraTemp2-min-ts").text( moment.unix($alltime.extraTemp2.mintime.raw).format( "$obs.label.time_records_page_full_date" ) );
        
        jQuery("#year-extraTemp3-max-ts").text( moment.unix($year.extraTemp3.maxtime.raw).format( "$obs.label.time_records_page_full_date" ) );
        jQuery("#at-extraTemp3-max-ts").text( moment.unix($alltime.extraTemp3.maxtime.raw).format( "$obs.label.time_records_page_full_date" ) );
        
        jQuery("#year-extraTemp3-min-ts").text( moment.unix($year.extraTemp3.mintime.raw).format( "$obs.label.time_records_page_full_date" ) );
        jQuery("#at-extraTemp3-min-ts").text( moment.unix($alltime.extraTemp3.mintime.raw).format( "$obs.label.time_records_page_full_date" ) );
        
        // Rain
        jQuery("#year-rainiest-day-ts").text( tzAdjustedMoment($rainiest_day[0]).format( "$obs.label.time_extreme_page_month_day_year" ) );
        jQuery("#at-rainiest-day-ts").text( tzAdjustedMoment($at_rainiest_day[0]).format( "$obs.label.time_extreme_page_month_day_year" ) );
        
        jQuery("#year-rainRate-max-ts").text( tzAdjustedMoment($year.rainRate.maxtime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        jQuery("#at-rainRate-max-ts").text( tzAdjustedMoment($alltime.rainRate.maxtime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        
        jQuery("#year-days-with-rainfall-ts").text( tzAdjustedMoment($year_days_with_rain[1]).format( "$obs.label.time_extreme_page_month_day_year" ) );
        
        if ($year_days_with_rain[1] > 0) {
            var start_day_epoch = $year_days_with_rain[1] - (($year_days_with_rain[0] - 1) * 86400);
            jQuery("#year-days-with-rainfall-range-ts").text( tzAdjustedMoment(start_day_epoch).format('$obs.label.time_extreme_page_rainfall_range_begin') + " " + '$obs.label.extreme_range_to' + " " + tzAdjustedMoment($year_days_with_rain[1]).format('$obs.label.time_extreme_page_rainfall_range_end') );
        } else {
            jQuery("#year-days-with-rainfall-range-ts").text("---");
        }
        
        if ($at_days_with_rain[1] > 0) {
            var start_day_epoch = $at_days_with_rain[1] - (($at_days_with_rain[0] - 1) * 86400);
            jQuery("#at-days-with-rainfall-range-ts").text( tzAdjustedMoment(start_day_epoch).format('$obs.label.time_extreme_page_rainfall_range_begin') + " " + '$obs.label.extreme_range_to' + " " + tzAdjustedMoment($at_days_with_rain[1]).format('$obs.label.time_extreme_page_rainfall_range_end') );
        } else {
            jQuery("#at-days-with-rainfall-range-ts").text("---");
        }
        
        jQuery("#year-days-without-rainfall-ts").text( tzAdjustedMoment($year_days_without_rain[1]).format( "$obs.label.time_extreme_page_month_day_year" ) );
        
        if ($year_days_without_rain[1] > 0) {
            var start_day_epoch = $year_days_without_rain[1] - (($year_days_without_rain[0] - 1) * 86400);
            jQuery("#year-days-without-rainfall-range-ts").text( tzAdjustedMoment(start_day_epoch).format('$obs.label.time_extreme_page_rainfall_range_begin') + " " + '$obs.label.extreme_range_to' + " " + tzAdjustedMoment($year_days_without_rain[1]).format('$obs.label.time_extreme_page_rainfall_range_end') );
        } else {
            jQuery("#year-days-without-rainfall-range-ts").text("---");
        }
        
        if ($at_days_without_rain[1] > 0) {
            var start_day_epoch = $at_days_without_rain[1] - (($at_days_without_rain[0] - 1) * 86400);
            jQuery("#at-days-without-rainfall-range-ts").text( tzAdjustedMoment(start_day_epoch).format('$obs.label.time_extreme_page_rainfall_range_begin') + " " + '$obs.label.extreme_range_to' + " " + tzAdjustedMoment($at_days_without_rain[1]).format('$obs.label.time_extreme_page_rainfall_range_end') );
        } else {
            jQuery("#at-days-without-rainfall-range-ts").text("---");
        }
        
        // thunderstorm
        jQuery("#year-thunderstormiest-day-ts").text( tzAdjustedMoment($thunderstormiest_day[0]).format( "$obs.label.time_extreme_page_month_day_year" ) );
        jQuery("#at-thunderstormiest-day-ts").text( tzAdjustedMoment($at_thunderstormiest_day[0]).format( "$obs.label.time_extreme_page_month_day_year" ) );
        
        #if $year.lightning_strike_count.has_data
        jQuery("#year-lightning_strike_count-max-ts").text( tzAdjustedMoment($year.lightning_strike_count.maxtime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        jQuery("#at-lightning_strike_count-max-ts").text( tzAdjustedMoment($alltime.lightning_strike_count.maxtime.raw).format( "$obs.label.time_extreme_page_full_date" ) );
        #end if
        
        // sunshine
        jQuery("#year-sunniest-day-ts").text( tzAdjustedMoment($sunniest_day[0]).format( "$obs.label.time_extreme_page_month_day_year" ) );
        jQuery("#at-sunniest-day-ts").text( tzAdjustedMoment($at_sunniest_day[0]).format( "$obs.label.time_extreme_page_month_day_year" ) );
        
        jQuery("#year-days-with-sunshine-ts").text( tzAdjustedMoment($year_days_with_rain[1]).format( "$obs.label.time_extreme_page_month_day_year" ) );
        
        if ($year_days_with_sunshine[1] > 0) {
            var start_day_epoch = $year_days_with_sunshine[1] - (($year_days_with_sunshine[0] - 1) * 86400);
            jQuery("#year-days-with-sunshine-range-ts").text( tzAdjustedMoment(start_day_epoch).format('$obs.label.time_extreme_page_sunshine_range_begin') + " " + '$obs.label.extreme_range_to' + " " + tzAdjustedMoment($year_days_with_sunshine[1]).format('$obs.label.time_extreme_page_sunshine_range_end') );
        } else {
            jQuery("#year-days-with-sunshine-range-ts").text("---");
        }
        
        if ($at_days_with_sunshine[1] > 0) {
            var start_day_epoch = $at_days_with_sunshine[1] - (($at_days_with_sunshine[0] - 1) * 86400);
            jQuery("#at-days-with-sunshine-range-ts").text( tzAdjustedMoment(start_day_epoch).format('$obs.label.time_extreme_page_sunshine_range_begin') + " " + '$obs.label.extreme_range_to' + " " + tzAdjustedMoment($at_days_with_sunshine[1]).format('$obs.label.time_extreme_page_sunshine_range_end') );
        } else {
            jQuery("#at-days-with-sunshine-range-ts").text("---");
        }
        
        jQuery("#year-days-without-sunshine-ts").text( tzAdjustedMoment($year_days_without_sunshine[1]).format( "$obs.label.time_extreme_page_month_day_year" ) );
        
        if ($year_days_without_sunshine[1] > 0) {
            var start_day_epoch = $year_days_without_sunshine[1] - (($year_days_without_sunshine[0] - 1) * 86400);
            jQuery("#year-days-without-sunshine-range-ts").text( tzAdjustedMoment(start_day_epoch).format('$obs.label.time_extreme_page_sunshine_range_begin') + " " + '$obs.label.extreme_range_to' + " " + tzAdjustedMoment($year_days_without_sunshine[1]).format('$obs.label.time_extreme_page_sunshine_range_end') );
        } else {
            jQuery("#year-days-without-sunshine-range-ts").text("---");
        }
        
        if ($at_days_without_sunshine[1] > 0) {
            var start_day_epoch = $at_days_without_sunshine[1] - (($at_days_without_sunshine[0] - 1) * 86400);
            jQuery("#at-days-without-sunshine-range-ts").text( tzAdjustedMoment(start_day_epoch).format('$obs.label.time_extreme_page_sunshine_range_begin') + " " + '$obs.label.extreme_range_to' + " " + tzAdjustedMoment($at_days_without_sunshine[1]).format('$obs.label.time_extreme_page_sunshine_range_end') );
        } else {
            jQuery("#at-days-without-sunshine-range-ts").text("---");
        }
    });
</script>

<div class="row">
    <div class="col-xs-12 extreme-table-container">
        <table class="table table-striped extreme-table">

            <!-- Temperaturen -->
            <thead class="table-light extreme-table-head">
                <tr>
                    <th scope="col" class="extreme-table-head-headline" colspan=5>$obs.label.extreme_temperature_records</th>
                </tr>
                <tr>
                    <th></th>
                    <th scope="col" class="extreme-table-head-year" colspan=2>$current.dateTime.format("%Y")</th>
                    <th scope="col" class="extreme-table-head-alltime" colspan=2>$obs.label.extreme_all_time</th>
                </tr>
            </thead>
            <tbody class="table-group-divider extreme-table-body">
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_high_temp</th>
                    <td class="extreme-table-body-obs-val-year">$year.outTemp.max</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-outtemp-max-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.outTemp.max</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-outtemp-max-ts"></td><!-- moment.js -->
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_low_temp</th>
                    <td class="extreme-table-body-obs-val-year">$year.outTemp.min</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-outtemp-min-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.outTemp.min</td><!-- moment.js -->
                    <td class="extreme-table-body-obs-ts-alltime" id="at-outtemp-min-ts"></td><!-- moment.js -->
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_highest_dewpoint</th>
                    <td class="extreme-table-body-obs-val-year">$year.dewpoint.max</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-dewpoint-max-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.dewpoint.max</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-dewpoint-max-ts"></td><!-- moment.js -->
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_lowest_dewpoint</th>
                    <td class="extreme-table-body-obs-val-year">$year.dewpoint.min</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-dewpoint-min-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.dewpoint.min</td><!-- moment.js -->
                    <td class="extreme-table-body-obs-ts-alltime" id="at-dewpoint-min-ts"></td><!-- moment.js -->
                </tr>
                #if $year.appTemp.has_data and $alltime.appTemp.has_data
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_high_apptemp</th>
                    <td class="extreme-table-body-obs-val-year">$year.appTemp.max</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-apptemp-max-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.appTemp.max</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-apptemp-max-ts"></td><!-- moment.js -->
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_low_apptemp</th>
                    <td class="extreme-table-body-obs-val-year">$year.appTemp.min</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-apptemp-min-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.appTemp.min</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-apptemp-min-ts"></td><!-- moment.js -->
                </tr>
                #end if
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_high_heatindex</th>
                    <td class="extreme-table-body-obs-val-year">$year.heatindex.max</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-heatindex-max-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.heatindex.max</br>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-heatindex-max-ts"></td><!-- moment.js -->
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_low_windchill</th>
                    <td class="extreme-table-body-obs-val-year">$year.windchill.min</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-windchill-min-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.windchill.min</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-windchill-min-ts"></td><!-- moment.js -->
                </tr>
            </tbody>

            <!-- Temperaturdifferenzen -->
            <thead class="table-light extreme-table-head">
                <tr>
                    <th scope="col" class="extreme-table-head-headline" colspan=5>$obs.label.extreme_temp_range</th>
                </tr>
                <tr>
                    <th></th>
                    <th scope="col" class="extreme-table-head-year" colspan=2>$current.dateTime.format("%Y")</th>
                    <th scope="col" class="extreme-table-head-alltime" colspan=2>$obs.label.extreme_all_time</th>
                </tr>
            </thead>
            <tbody class="table-group-divider extreme-table-body">
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_largest_temp_range</th>
                    <td class="extreme-table-body-obs-val-year">$year_outTemp_range_max[1] $unit.label.outTemp</td>
                    <td class="extreme-table-body-obs-ts-year">
                        <span id="year-outtemp-range-max-ts"></span><br><!-- moment.js -->
                        <span class="extreme-table-body-obs-descr-year">$year_outTemp_range_max[2] $unit.label.outTemp $obs.label.extreme_range_to $year_outTemp_range_max[3] $unit.label.outTemp</span>
                    </td>
                    <td class="extreme-table-body-obs-val-alltime">$at_outTemp_range_max[1] $unit.label.outTemp</td>
                    <td class="extreme-table-body-obs-ts-alltime">
                        <span id="at-outtemp-range-max-ts"></span><br><!-- moment.js -->
                        <span class="extreme-table-body-obs-descr-alltime">$at_outTemp_range_max[2] $unit.label.outTemp $obs.label.extreme_range_to $at_outTemp_range_max[3] $unit.label.outTemp</span>
                    </td>
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_smallest_temp_range</th>
                    <td class="extreme-table-body-obs-val-year">$year_outTemp_range_min[1] $unit.label.outTemp</td>
                    <td class="extreme-table-body-obs-ts-year">
                        <span id="year-outtemp-range-min-ts"></span><br><!-- moment.js -->
                        <span class="extreme-table-body-obs-descr-year">$year_outTemp_range_min[2] $unit.label.outTemp $obs.label.extreme_range_to $year_outTemp_range_min[3] $unit.label.outTemp</span>
                    </td>
                    <td class="extreme-table-body-obs-val-alltime">$at_outTemp_range_min[1] $unit.label.outTemp</td>
                    <td class="extreme-table-body-obs-ts-alltime">
                        <span id="at-outtemp-range-min-ts"></span><br><!-- moment.js -->
                        <span class="extreme-table-body-obs-descr-alltime">$at_outTemp_range_min[2] $unit.label.outTemp $obs.label.extreme_range_to $at_outTemp_range_min[3] $unit.label.outTemp</span>
                    </td>
                </tr>
            </tbody>

            <!-- rel. Luftdruck -->
            <thead class="table-light extreme-table-head">
                <tr>
                    <th scope="col" class="extreme-table-head-headline" colspan=5>$obs.label.extreme_barometer_records</th>
                </tr>
                <tr>
                    <th></th>
                    <th scope="col" class="extreme-table-head-year" colspan=2>$current.dateTime.format("%Y")</th>
                    <th scope="col" class="extreme-table-head-alltime" colspan=2>$obs.label.extreme_all_time</th>
                </tr>
            </thead>
            <tbody class="table-group-divider extreme-table-body">
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_high_barometer</th>
                    <td class="extreme-table-body-obs-val-year">$year.barometer.max</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-barometer-max-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.barometer.max</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-barometer-max-ts"></td><!-- moment.js -->
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_low_barometer</th>
                    <td class="extreme-table-body-obs-val-year">$year.barometer.min</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-barometer-min-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.barometer.min</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-barometer-min-ts"></td><!-- moment.js -->
                </tr>
            </tbody>

            <!-- Luftfeuchte -->
            <thead class="table-light extreme-table-head">
                <tr>
                    <th scope="col" class="extreme-table-head-headline" colspan=5>$obs.label.extreme_humidity_records</th>
                </tr>
                <tr>
                    <th></th>
                    <th scope="col" class="extreme-table-head-year" colspan=2>$current.dateTime.format("%Y")</th>
                    <th scope="col" class="extreme-table-head-alltime" colspan=2>$obs.label.extreme_all_time</th>
                </tr>
            </thead>
            <tbody class="table-group-divider extreme-table-body">
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_high_humidity</th>
                    <td class="extreme-table-body-obs-val-year">$year.outHumidity.max</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-outHumidity-max-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.outHumidity.max</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-outHumidity-max-ts"></td><!-- moment.js -->
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_lowest_humidity</th>
                    <td class="extreme-table-body-obs-val-year">$year.outHumidity.min</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-outHumidity-min-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.outHumidity.min</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-outHumidity-min-ts"></td><!-- moment.js -->
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_high_outhumabs</th>
                    <td class="extreme-table-body-obs-val-year">$year.outHumAbs.max.gram_per_meter_cubed</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-outHumAbs-max-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.outHumAbs.max.gram_per_meter_cubed</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-outHumAbs-max-ts"></td><!-- moment.js -->
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_lowest_outhumabs</th>
                    <td class="extreme-table-body-obs-val-year">$year.outHumAbs.min.gram_per_meter_cubed</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-outHumAbs-min-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.outHumAbs.min.gram_per_meter_cubed</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-outHumAbs-min-ts"></td><!-- moment.js -->
                </tr>
            </tbody>

            <!-- Wind -->
            <thead class="table-light extreme-table-head">
                <tr>
                    <th scope="col" class="extreme-table-head-headline" colspan=5>$obs.label.extreme_wind_records</th>
                </tr>
                <tr>
                    <th></th>
                    <th scope="col" class="extreme-table-head-year" colspan=2>$current.dateTime.format("%Y")</th>
                    <th scope="col" class="extreme-table-head-alltime" colspan=2>$obs.label.extreme_all_time</th>
                </tr>
            </thead>
            <tbody class="table-group-divider extreme-table-body">
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_strongest_wind</th>
                    <td class="extreme-table-body-obs-val-year">$year.windGust.max</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-windGust-max-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.windGust.max</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-windGust-max-ts"></td><!-- moment.js -->
                </tr>
                #if $year.windrun.has_data and $alltime.windrun.has_data
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_daily_windrun</th>
                    <td class="extreme-table-body-obs-val-year">$year.windrun.maxsum</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-windrun-max-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.windrun.maxsum</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-windrun-max-ts"></td><!-- moment.js -->
                </tr>
                #end if
            </tbody>

            <!-- Regen -->
            <thead class="table-light extreme-table-head">
                <tr>
                    <th scope="col" class="extreme-table-head-headline" colspan=5>$obs.label.extreme_rain_records</th>
                </tr>
                <tr>
                    <th></th>
                    <th scope="col" class="extreme-table-head-year" colspan=2>$current.dateTime.format("%Y")</th>
                    <th scope="col" class="extreme-table-head-alltime" colspan=2>$obs.label.extreme_all_time</th>
                </tr>
            </thead>
            <tbody class="table-group-divider extreme-table-body">
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_highest_daily_rain</th>
                    <td class="extreme-table-body-obs-val-year">$rainiest_day[1] $unit.label.rain</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-rainiest-day-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$at_rainiest_day[1] $unit.label.rain</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-rainiest-day-ts"></td><!-- moment.js -->
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_highest_daily_rainrate</th>
                    <td class="extreme-table-body-obs-val-year">$year.rainRate.max</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-rainRate-max-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.rainRate.max</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-rainRate-max-ts"></td><!-- moment.js -->
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_highest_monthly_rain</th>
                    <td class="extreme-table-body-obs-val-year">$year_rainiest_month[1] $unit.label.rain</td>
                    <td class="extreme-table-body-obs-ts-year">$year_rainiest_month[0]</td>
                    <td class="extreme-table-body-obs-val-alltime">$at_rainiest_month[1] $unit.label.rain</td>
                    <td class="extreme-table-body-obs-ts-alltime">$at_rainiest_month[0]</td>
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_highest_yearly_rain</th>
                    <td class="extreme-table-body-obs-val-year">$year.rain.sum</td>
                    <td class="extreme-table-body-obs-ts-year">$current.dateTime.format("%Y")</td>
                    <td class="extreme-table-body-obs-val-alltime">$at_rain_highest_year[1] $unit.label.rain</td>
                    <td class="extreme-table-body-obs-ts-alltime">$at_rain_highest_year[0]</td>
                </tr>
            </tbody>

            <!-- Regen - Aufeinanderfolgende Tage -->
            <thead class="table-light extreme-table-subhead">
                <tr>
                    <th scope="col" class="extreme-table-head-subheadline" colspan=5>$obs.label.extreme_consec_days</th>
                </tr>
##                <tr>
##                    <th></th>
##                    <th scope="col" class="extreme-table-head-year" colspan=2>$current.dateTime.format("%Y")</th>
##                    <th scope="col" class="extreme-table-head-alltime" colspan=2>$obs.label.extreme_all_time</th>
##                </tr>
            </thead>
            <tbody class="table-group-divider extreme-table-body">
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_consec_days_with_rain</th>
                    <td class="extreme-table-body-obs-val-year">$year_days_with_rain[0] $obs.label.extreme_days_text</td>
                    ##<td class="extreme-table-body-obs-ts-year">$obs.label.extreme_ending <span id="year-days-with-rainfall-ts"></span></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-ts-alltime" id="year-days-with-rainfall-range-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$at_days_with_rain[0] $obs.label.extreme_days_text</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-days-with-rainfall-range-ts"></td><!-- moment.js -->
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_consec_days_without_rain</th>
                    <td class="extreme-table-body-obs-val-year">$year_days_without_rain[0] $obs.label.extreme_days_text</td>
                    ##<td class="extreme-table-body-obs-ts-year">$obs.label.extreme_ending <span id="year-days-without-rainfall-ts"></span></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-ts-alltime" id="year-days-without-rainfall-range-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$at_days_without_rain[0] $obs.label.extreme_days_text</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-days-without-rainfall-range-ts"></td><!-- moment.js -->
                </tr>
            </tbody>

            <!-- Anzahl Gewitterblitze -->
            <thead class="table-light extreme-table-head">
                <tr>
                    <th scope="col" class="extreme-table-head-headline" colspan=5>$obs.label.extreme_records_lsc</th>
                </tr>
                <tr>
                    <th></th>
                    <th scope="col" class="extreme-table-head-year" colspan=2>$current.dateTime.format("%Y")</th>
                    <th scope="col" class="extreme-table-head-alltime" colspan=2>$obs.label.extreme_all_time_lsc</th>
                </tr>
            </thead>
            <tbody class="table-group-divider extreme-table-body">
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_highest_daily_lsc</th>
                    <td class="extreme-table-body-obs-val-year">$thunderstormiest_day[1] $unit.label.lightning_strike_count</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-thunderstormiest-day-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$at_thunderstormiest_day[1] $unit.label.lightning_strike_count</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-thunderstormiest-day-ts"></td><!-- moment.js -->
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_highest_monthly_lsc</th>
                    <td class="extreme-table-body-obs-val-year">$year_thunderstormiest_month[1] $unit.label.lightning_strike_count</td>
                    <td class="extreme-table-body-obs-ts-year">$year_thunderstormiest_month[0]</td>
                    <td class="extreme-table-body-obs-val-alltime">$at_thunderstormiest_month[1] $unit.label.lightning_strike_count</td>
                    <td class="extreme-table-body-obs-ts-alltime">$at_thunderstormiest_month[0]</td>
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_highest_yearly_lsc</th>
                    <td class="extreme-table-body-obs-val-year">$year.lightning_strike_count.sum</td>
                    <td class="extreme-table-body-obs-ts-year">$current.dateTime.format("%Y")</td>
                    <td class="extreme-table-body-obs-val-alltime">$at_thunderstormiest_year[1] $unit.label.lightning_strike_count</td>
                    <td class="extreme-table-body-obs-ts-alltime">$at_thunderstormiest_year[0]</td>
                </tr>
            </tbody>

            <!-- Sonnenstrahlung -->
            <thead class="table-light extreme-table-head">
                <tr>
                    <th scope="col" class="extreme-table-head-headline" colspan=5>$obs.label.extreme_sun_records</th>
                </tr>
                <tr>
                    <th></th>
                    <th scope="col" class="extreme-table-head-year" colspan=2>$current.dateTime.format("%Y")</th>
                    <th scope="col" class="extreme-table-head-alltime" colspan=2>$obs.label.extreme_all_time</th>
                </tr>
            </thead>
            <tbody class="table-group-divider extreme-table-body">
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_high_solar_rad</th>
                    <td class="extreme-table-body-obs-val-year">$year.radiation.max</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-radiation-max-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.radiation.max</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-radiation-max-ts"></td><!-- moment.js -->
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_high_uv</th>
                    <td class="extreme-table-body-obs-val-year">$year.UV.max</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-UV-max-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.UV.max</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-UV-max-ts"></td><!-- moment.js -->
                </tr>
            </tbody>

            <!-- Sonnenschein -->
            <thead class="table-light extreme-table-head">
                <tr>
                    <th scope="col" class="extreme-table-head-subheadline" colspan=5>$obs.label.extreme_sunshine_records</th>
                </tr>
##                <tr>
##                    <th></th>
##                    <th scope="col" class="extreme-table-head-year" colspan=2>$current.dateTime.format("%Y")</th>
##                    <th scope="col" class="extreme-table-head-alltime" colspan=2>$obs.label.extreme_all_time</th>
##                </tr>
            </thead>
            <tbody class="table-group-divider extreme-table-body">
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_highest_daily_sunshine</th>
                    <td class="extreme-table-body-obs-val-year">$sunniest_day[1] $gettext('hours')</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-sunniest-day-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$at_sunniest_day[1] $gettext('hours')</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-sunniest-day-ts"></td><!-- moment.js -->
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_highest_monthly_sunshine</th>
                    <td class="extreme-table-body-obs-val-year">$year_sunniest_month[1] $gettext('hours')</td>
                    <td class="extreme-table-body-obs-ts-year">$year_sunniest_month[0]</td>
                    <td class="extreme-table-body-obs-val-alltime">$at_sunniest_month[1] $gettext('hours')</td>
                    <td class="extreme-table-body-obs-ts-alltime">$at_sunniest_month[0]</td>
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_highest_yearly_sunshine</th>
                    <td class="extreme-table-body-obs-val-year">$sunshine_sum_year[0] $gettext('hours')</td>
                    <td class="extreme-table-body-obs-ts-year">$current.dateTime.format("%Y")</td>
                    <td class="extreme-table-body-obs-val-alltime">$at_sunniest_year[1] $gettext('hours')</td>
                    <td class="extreme-table-body-obs-ts-alltime">$at_sunniest_year[0]</td>
                </tr>
            </tbody>

            <!-- Sonnenschein - Aufeinanderfolgende Tage -->
            <thead class="table-light extreme-table-subhead">
                <tr>
                    <th scope="col" class="extreme-table-head-subheadline" colspan=5>$obs.label.extreme_consec_sunshine_days</th>
                </tr>
##                <tr>
##                    <th></th>
##                    <th scope="col" class="extreme-table-head-year" colspan=2>$current.dateTime.format("%Y")</th>
##                    <th scope="col" class="extreme-table-head-alltime" colspan=2>$obs.label.extreme_all_time</th>
##                </tr>
            </thead>
            <tbody class="table-group-divider extreme-table-body">
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_consec_days_with_sunshine</th>
                    <td class="extreme-table-body-obs-val-year">$year_days_with_sunshine[0] $obs.label.extreme_days_text</td>
                    ##<td class="extreme-table-body-obs-ts-year">$obs.label.extreme_ending <span id="year-days-with-sunshine-ts"></span></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-ts-alltime" id="year-days-with-sunshine-range-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$at_days_with_sunshine[0] $obs.label.extreme_days_text</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-days-with-sunshine-range-ts"></td><!-- moment.js -->
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_consec_days_without_sunshine</th>
                    <td class="extreme-table-body-obs-val-year">$year_days_without_sunshine[0] $obs.label.extreme_days_text</td>
                    ##<td class="extreme-table-body-obs-ts-year">$obs.label.extreme_ending <span id="year-days-without-sunshine-ts"></span></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-ts-alltime" id="year-days-without-sunshine-range-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$at_days_without_sunshine[0] $obs.label.extreme_days_text</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-days-without-sunshine-range-ts"></td><!-- moment.js -->
                </tr>
            </tbody>





            <!-- Innentemperaturen -->
            <thead class="table-light extreme-table-head">
                <tr>
                    <th scope="col" class="extreme-table-head-headline" colspan=5>$obs.label.extreme_inTemp_records</th>
                </tr>
                <tr>
                    <th></th>
                    <th scope="col" class="extreme-table-head-year" colspan=2>$current.dateTime.format("%Y")</th>
                    <th scope="col" class="extreme-table-head-alltime" colspan=2>$obs.label.extreme_all_time</th>
                </tr>
            </thead>
            <tbody class="table-group-divider extreme-table-body">
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_high_inTemp</th>
                    <td class="extreme-table-body-obs-val-year">$year.inTemp.max</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-inTemp-max-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.inTemp.max</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-inTemp-max-ts"></td><!-- moment.js -->
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_low_inTemp</th>
                    <td class="extreme-table-body-obs-val-year">$year.inTemp.min</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-inTemp-min-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.inTemp.min</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-inTemp-min-ts"></td><!-- moment.js -->
                </tr>
                <tr>
                    <th></th>
##                    <th scope="col" class="extreme-table-head-year" colspan=2>$current.dateTime.format("%Y")</th>
                    <th scope="col" colspan=2></th>
                    <th scope="col" class="extreme-table-head-alltime" colspan=2>$obs.label.extreme_all_time_extraTemp</th>
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_high_extraTemp1</th>
                    <td class="extreme-table-body-obs-val-year">$year.extraTemp1.max</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-extraTemp1-max-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.extraTemp1.max</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-extraTemp1-max-ts"></td><!-- moment.js -->
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_low_extraTemp1</th>
                    <td class="extreme-table-body-obs-val-year">$year.extraTemp1.min</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-extraTemp1-min-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.extraTemp1.min</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-extraTemp1-min-ts"></td><!-- moment.js -->
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_high_extraTemp2</th>
                    <td class="extreme-table-body-obs-val-year">$year.extraTemp2.max</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-extraTemp2-max-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.extraTemp2.max</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-extraTemp2-max-ts"></td><!-- moment.js -->
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_low_extraTemp2</th>
                    <td class="extreme-table-body-obs-val-year">$year.extraTemp2.min</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-extraTemp2-min-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.extraTemp2.min</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-extraTemp2-min-ts"></td><!-- moment.js -->
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_high_extraTemp3</th>
                    <td class="extreme-table-body-obs-val-year">$year.extraTemp3.max</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-extraTemp3-max-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.extraTemp3.max</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-extraTemp3-max-ts"></td><!-- moment.js -->
                </tr>
                <tr>
                    <th scope="row" class="extreme-table-body-obs">$obs.label.extreme_low_extraTemp3</th>
                    <td class="extreme-table-body-obs-val-year">$year.extraTemp3.min</td>
                    <td class="extreme-table-body-obs-ts-year" id="year-extraTemp3-min-ts"></td><!-- moment.js -->
                    <td class="extreme-table-body-obs-val-alltime">$alltime.extraTemp3.min</td>
                    <td class="extreme-table-body-obs-ts-alltime" id="at-extraTemp3-min-ts"></td><!-- moment.js -->
                </tr>
            </tbody>
        </table>
    </div>
</div>