#encoding UTF-8
<div class="wx-stn-info-container">
    <div class="row">
        <div class="col-sm-1 wx-stn-info-current-obs">
            <div class="obs-header-icon">
                #if $Extras.has_key("forecast_enabled") and $Extras.forecast_enabled == '1' and $current_obs_icon != ""
                <img id="wxicon" src="$relative_url/images/$current_obs_icon" alt="Wettersymbol $current_obs_icon">
                #end if
            </div>
            <div class="obs-header-outtemp">$current.outTemp</div>
        </div>
        <div class="col-sm-8">
            <div class="wx-stn-name">
        #if $page == "forecast"
                <h1>$obs.label.page_header_forecast</h1>
        #else if $page == "graphs"
                <h1>$obs.label.page_header_graphs</h1>
        #else if $page == "records"
                <h1>$obs.label.page_header_records</h1>
        #else if $page == "reports"
                <h1>$obs.label.page_header_reports</h1>
        #else if $page == "about"
                <h1>$obs.label.page_header_about</h1>
        #else if $page == "webcam"
                <h1>$obs.label.page_header_webcam</h1>
        #else if $page == "imprint"
                <h1>$obs.label.page_header_imprint</h1>
        #else if $page == "privacy"
                <h1>$obs.label.page_header_privacy</h1>
        #else if $page == "extreme"
                <h1>$obs.label.page_header_extreme</h1>
        #end if
        </div>
        </div>
        <div class="col-sm-3" style="float:right;">
            <div class="wx-stn-info">
                $obs.label.powered_by
            </div>
            #if $social_html != ""
            <div class="col-sm-10 wx-stn-info-social" style="float:right;">
                $social_html
            </div>
            #end if
        </div>
    </div>
    <div class="clear"></div>
</div>

