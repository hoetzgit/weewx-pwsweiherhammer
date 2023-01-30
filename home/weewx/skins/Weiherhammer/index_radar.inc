#encoding UTF-8

<!-- Start index_radar.inc -->

<div id="tabs-container">
     <!-- Nav tabs -->
    <ul class="nav nav-tabs tabs-menu" role="tablist">
        <li role="presentation" class="active"><a href="#radar" aria-controls="radar" role="tab" data-toggle="tab">$obs.label.radar_tab_windy</a></li>
        <li role="presentation"><a href="#dwdradar" aria-controls="dwdradar" role="tab" data-toggle="tab">$obs.label.radar_tab_dwd</a></li>
##        <li role="presentation"><a href="#meteosat" aria-controls="meteosat" role="tab" data-toggle="tab">$obs.label.radar_tab_meteosat</a></li>
##        <li role="presentation"><a href="#precipitation" aria-controls="precipitation" role="tab" data-toggle="tab">$obs.label.radar_tab_precipitation</a></li>
##        <li role="presentation"><a href="#webcamrpi" aria-controls="webcamrpi" role="tab" data-toggle="tab">RPi</a></li>
        <li role="presentation"><a href="#webcam" aria-controls="webcam" role="tab" data-toggle="tab">Webcam</a></li>
        #if os.path.exists("allsky/allskycam01.up")
        <li role="presentation"><a href="#allsky01" aria-controls="allsky01" role="tab" data-toggle="tab">$obs.label.radar_tab_allskycam01</a></li>
        #end if
        #if os.path.exists("allsky/allskycam02.up")
        <li role="presentation"><a href="#allsky02" aria-controls="allsky02" role="tab" data-toggle="tab">$obs.label.radar_tab_allskycam02</a></li>
        #end if
    </ul>

    <!-- Tabs contents -->
    <div class="tab">
        <div id="radar" class="tab-content">
            <div class="radar_image">$radar_html</div>
        </div>
        <div id="dwdradar" class="tab-content">
            <div class="dwdradar_image">
                <a href="https://www.dwd.de/DE/leistungen/radarbild_film/radarbild_film.html?cl2Categories_Bundesland=rdbf_bay&cl2Categories_Darstellung=rdbf_akt&cl2Categories_Format=radarbild" target="_blank" rel="noreferrer"><img src="https://www.dwd.de/DWD/wetter/radar/radfilm_bay_akt.gif" alt="DWD Radar" width="420px" rel="tooltip" title="$obs.label.radar_content_ttt"></a>
            </div>
        </div>
##        <div id="meteosat" class="tab-content">
##            <div class="meteosat_image">
####                <a href="https://www.dwd.de/DE/leistungen/satellit_metsat/satellit_metsat.html" target="_blank" rel="noreferrer"><img src="https://www.dwd.de/DWD/wetter/sat/bilder/meteosat/satbild_hrvir_akt.png" alt="Meteosat" width="488px" rel="tooltip" title="$obs.label.radar_content_ttt"></a>
##                <a href="http://de.sat24.com/de" target="_blank" rel="noreferrer"><img src="https://api.sat24.com/animated/DE/infraPolair/1/W_dot_%20Europe%20Standard%20Time/4277781" alt="Meteosat" width="488px" rel="tooltip" title="$obs.label.radar_content_ttt"></a>
##            </div>
##        </div>
##        <div id="precipitation" class="tab-content">
##            <div class="precipitation_image">
##                <a href="https://www.dwd.de/DE/leistungen/wolken_niederschlagsart/wolken_niederschlagsart.html" target="_blank" rel="noreferrer"><img src="https://www.dwd.de/DWD/wetter/sat/satwetter/njob_satrad.png" alt="DWD Niederschlagsdaten" width="420px" rel="tooltip" title="$obs.label.radar_content_ttt"></a>
##            </div>
##        </div>
        <div id="webcam" class="tab-content">
            <div class="webcam_image">
                <a href="$relative_url/webcam"><img src="$relative_url/images/webcam_small.jpg" alt="Die Webcam der Wetterstation Weiherhammer" rel="tooltip" title="$obs.label.radar_content_ttt"></a>
            </div>
            <div style="text-align:center"><small>$obs.label.radar_content_webcam</small></div>
        </div>
##        <div id="webcamrpi" class="tab-content">
##            <div class="webcamrpi_image">
##                <a href="https://wcam.ott24.net" target="_blank" rel="noreferrer"><img src="https://wcam.ott24.net/image.jpg" alt="Die RPi Webcam der Wetterstation Weiherhammer" rel="tooltip" title="$obs.label.radar_content_ttt"></a>
##            </div>
##            <div style="text-align:center"><small>Test Wetterkamera Raspberry Pi</small></div>
##        </div>
        #if os.path.exists("allsky/allskycam01.up")
        <div id="allsky01" class="tab-content">
            <div class="allsky01_image">
                <a href="https://allsky.ott24.net" target="_blank" rel="noreferrer"><img src="https://allsky.ott24.net/image.jpg" alt="Die AllSky Kamera 1 der PWS Weiherhammer" rel="tooltip" title="$obs.label.radar_content_ttt"></a>
            </div>
        </div>
        #end if
        #if os.path.exists("allsky/allskycam02.up")
        <div id="allsky02" class="tab-content">
            <div class="allsky02_image">
                <a href="https://allsky02.ott24.net" target="_blank" rel="noreferrer"><img src="https://allsky02.ott24.net/image.jpg" alt="Die AllSky Kamera 2 der PWS Weiherhammer" rel="tooltip" title="$obs.label.radar_content_ttt"></a>
            </div>
        </div>
        #end if
    </div>
</div>

<script type="text/javascript">
    jQuery(document).ready(function() {
        // All additional images according to standard Windy Radar
        setInterval('reloadRadarTabImages("dwdradar_image")', 300000);
##        setInterval('reloadRadarTabImages("meteosat_image")', 300000);
##        setInterval('reloadRadarTabImages("precipitation_image")', 300000);
        setInterval('reloadRadarTabImages("webcam_image")', 60000);
##        setInterval('reloadRadarTabImages("webcamrpi_image")', 60000);
        #if os.path.exists("allsky/allskycam01.up")
        setInterval('reloadRadarTabImages("allsky01_image")', 60000);
        #end if
        #if os.path.exists("allsky/allskycam02.up")
        setInterval('reloadRadarTabImages("allsky02_image")', 60000);
        #end if
    });

    jQuery('.tabs-menu a').click(function(event) {
        event.preventDefault();

        // Toggle active class on tab buttons
        jQuery(this).parent().addClass("active");
        jQuery(this).parent().siblings().removeClass("active");

        // display only active tab content
        var activeTab = jQuery(this).attr("href");
        jQuery('.tab-content').not(activeTab).css("display","none");
        jQuery(activeTab).fadeIn();
    });

    // All additional images according to standard Windy Radar
    function reloadRadarTabImages(section = "dummy") {
        jQuery('.' + section + ' img').each(function() {
            new_image_url = jQuery(this).attr('src').split('?')[0] + "?" + Math.floor(Math.random() * 999999999);
            jQuery(this).attr('src', new_image_url);
        });
    }
</script>

<!-- Ende index_radar.inc -->
