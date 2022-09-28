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
<!-- Start noaa.inc -->
<div class="row" style="margin-top:25px;">
    <div class="col-md-12 history-headline">
        $obs.label.history_NOAA_title
    </div>  
    <div class="col-md-12 table-responsive" style="margin-top:10px;">
        $NOAA_table
    </div>
</div>
##<div class="row">
##    <div class="col-md-12" style="margin-top:10px;">
##        <a href="#" class="noaa_direct_link">$obs.label.reports_click_here_link</a> $obs.label.reports_view_more
##    </div>
##</div>
##<div class="row">
##    <div class="col-md-12 noaa_report_container">
##        <pre id="noaa_contents"></pre>
##    </div>
##</div>
<!-- Ende noaa_reports -->