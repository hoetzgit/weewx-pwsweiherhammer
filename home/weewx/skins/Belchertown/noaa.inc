#encoding UTF-8

<!-- Start noaa.inc -->
<div class="row" style="margin-top:10px;">
    <div class="col-md-12 noaa-headline">
        $obs.label.reports_title
    </div>  
</div>
<div class="row">
    <div class="col-md-12 wx-year-row">
        $noaa_header_html
    </div>
</div>
<div class="row">
    <div class="col-md-12">
        <a href="#" class="noaa_direct_link">$obs.label.reports_click_here_link</a> $obs.label.reports_view_more
    </div>
</div>
<div class="row">
    <div class="col-md-12 noaa_report_container">
        <pre id="noaa_contents"></pre>
    </div>
</div>
<!-- Ende noaa_reports -->