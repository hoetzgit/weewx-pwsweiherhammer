#errorCatcher Echo
#encoding UTF-8
##
##    <script>        
##        jQuery(document).ready(function() {
##            var month = getURLvar("mo");
##            var year = getURLvar("yr");
##            if ( ( year !== undefined ) && ( month !== undefined ) ) {
##                url = '$relative_url/NOAA/NOAA-'+year+'-'+month+'.txt';
##            } else if ( year !== undefined ) {
##                url = '$relative_url/NOAA/NOAA-'+year+'.txt';
##            } else {
##                url = '$relative_url/NOAA/$default_noaa_file';
##            }
##            
##            // Load the file into the pre
##            //jQuery('#noaa_contents').load( url );
##            populatePre( url );
##            
##            // Change the direct href link
##            jQuery(".noaa_direct_link").attr( "href", url );
##       });
##        
##        // Change the div to the right NOAA file
##        // I normally use PHP for this, but JavaScript seems to work well for the skin
##        // Source: https://stackoverflow.com/a/18933218/1177153
##        function populatePre(url) {
##            var xhr = new XMLHttpRequest();
##            xhr.onload = function () {
##                raw_content = this.responseText;
##                updated_content = raw_content.replace('<sup>','').replace('</sup>','').replace('&deg;','');
##                document.getElementById('noaa_contents').textContent = updated_content;
##            };
##            xhr.open('GET', url);
##            xhr.send();
##        }
##    </script>
##
<div class="row">
    <div class="col-md-12 history-headline">$obs.label.history_min_temp_title</div>
    <div class="col-xs-12 history-table-container">
        $min_temp_table
    </div>
</div>
<div class="row">
    <div class="col-md-12 history-headline">$obs.label.history_avg_temp_title</div>
    <div class="col-xs-12 history-table-container">
        $avg_temp_table
    </div>
</div>
<div class="row">
    <div class="col-md-12 history-headline">$obs.label.history_max_temp_title</div>
    <div class="col-xs-12 history-table-container">
        $max_temp_table
    </div>
</div>
<div class="row">
    <div class="col-md-12 history-headline">$obs.label.history_ice_days_title <a href="$obs.label.history_ice_days_url" target="_blank" rel="noreferrer" title="$obs.label.history_info_title"><i class="fa fa-info-circle fa-1 history-info-icon"></i></a></div>
    <div class="col-xs-12 history-table-container">
        $ice_days_table
    </div>
</div>
<div class="row">
    <div class="col-md-12 history-headline">$obs.label.history_frost_days_title <a href="$obs.label.history_frost_days_url" target="_blank" rel="noreferrer" title="$obs.label.history_info_title"><i class="fa fa-info-circle fa-1 history-info-icon"></i></a></div>
    <div class="col-xs-12 history-table-container">
        $frost_days_table
    </div>
</div>
<div class="row">
    <div class="col-md-12 history-headline">$obs.label.history_summer_days_title <a href="$obs.label.history_summer_days_url" target="_blank" rel="noreferrer" title="$obs.label.history_info_title"><i class="fa fa-info-circle fa-1 history-info-icon"></i></a></div>
    <div class="col-xs-12 history-table-container">
        $summer_days_table
    </div>
</div>
<div class="row">
    <div class="col-md-12 history-headline">$obs.label.history_hot_days_title <a href="$obs.label.history_hot_days_url" target="_blank" rel="noreferrer" title="$obs.label.history_info_title"><i class="fa fa-info-circle fa-1 history-info-icon"></i></a></div>
    <div class="col-xs-12 history-table-container">
        $hot_days_table
    </div>
</div>
<div class="row">
    <div class="col-md-12 history-headline">$obs.label.history_desert_days_title <a href="$obs.label.history_desert_days_url" target="_blank" rel="noreferrer" title="$obs.label.history_info_title"><i class="fa fa-info-circle fa-1 history-info-icon"></i></a></div>
    <div class="col-xs-12 history-table-container">
        $desert_days_table
    </div>
</div>
<div class="row">
    <div class="col-md-12 history-headline">$obs.label.history_sultry_days_title <a href="$obs.label.history_sultry_days_url" target="_blank" rel="noreferrer" title="$obs.label.history_info_title"><i class="fa fa-info-circle fa-1 history-info-icon"></i></a></div>
    <div class="col-xs-12 history-table-container">
        $sultry_days_table
    </div>
</div>
<div class="row">
    <div class="col-md-12 history-headline">$obs.label.history_sultry_days2_title <a href="$obs.label.history_sultry_days2_url" target="_blank" rel="noreferrer" title="$obs.label.history_info_title"><i class="fa fa-info-circle fa-1 history-info-icon"></i></a></div>
    <div class="col-xs-12 history-table-container">
        $sultry_days2_table
    </div>
</div>
<div class="row">
    <div class="col-md-12 history-headline">$obs.label.history_tropical_nights_title <a href="$obs.label.history_tropical_nights_url" target="_blank" rel="noreferrer" title="$obs.label.history_info_title"><i class="fa fa-info-circle fa-1 history-info-icon"></i></a></div>
    <div class="col-xs-12 history-table-container">
        $tropical_nights_table
    </div>
</div>
<div class="row">
    <div class="col-md-12 history-headline">$obs.label.history_vegetation_days_title <a href="$obs.label.history_vegetation_days_url" target="_blank" rel="noreferrer" title="$obs.label.history_info_title"><i class="fa fa-info-circle fa-1 history-info-icon"></i></a></div>
    <div class="col-xs-12 history-table-container">
        $vegetation_days_table
    </div>
</div>
<div class="row">
    <div class="col-md-12 history-headline">$obs.label.history_rain_title</div>
    <div class="col-xs-12 history-table-container">
        $rain_table
    </div>
</div>
<div class="row">
    <div class="col-md-12 history-headline">$obs.label.history_rain_days_title <a href="$obs.label.history_rain_days_url" target="_blank" rel="noreferrer" title="$obs.label.history_info_title"><i class="fa fa-info-circle fa-1 history-info-icon"></i></a></div>
    <div class="col-xs-12 history-table-container">
        $rain_days_table
    </div>
</div>
<div class="row">
    <div class="col-md-12 history-headline">$obs.label.history_windgust_title</div>
    <div class="col-xs-12 history-table-container">
        $max_wind_table
    </div>
</div>
<div class="row">
    <div class="col-md-12 history-headline">$obs.label.history_lightning_days_title <a href="$obs.label.history_lightning_days_url" target="_blank" rel="noreferrer" title="$obs.label.history_info_title"><i class="fa fa-info-circle fa-1 history-info-icon"></i></a></div>
    <div class="col-xs-12 history-table-container">
        $lightning_days_table
    </div>
</div>
<div class="row">
    <div class="col-md-12 history-headline">$obs.label.history_sunshineDur_title</div>
    <div class="col-xs-12 history-table-container">
        $sunshineDur_table
    </div>
</div>
<div class="row">
    <div class="col-sm-12 noaa-headline">$obs.label.history_NOAA_title</div>
    <div class="col-xs-12 history-table-noaa-container" style="margin-top:10px;">
        $noaa_table
    </div>
</div>
##<div class="row">
##    <div class="col-sm-12" style="margin-top:10px;">
##        <a href="#" class="noaa_direct_link">$obs.label.reports_click_here_link</a> $obs.label.reports_view_more
##    </div>
##</div>
##<div class="row">
##    <div class="col-xs-12 noaa_report_container">
##        <pre id="noaa_contents"></pre>
##    </div>
##</div>
