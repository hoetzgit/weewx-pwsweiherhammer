#encoding UTF-8

<!-- Start index_radar.inc -->

<div id="tabs-container">
     <!-- Nav tabs -->
    <ul class="nav nav-tabs tabs-menu" role="tablist">
        <li role="presentation" class="active"><a href="#radar" aria-controls="radar" role="tab" data-toggle="tab">$obs.label.radar_tab_windy</a></li>
        <li role="presentation"><a href="#dwdradar" aria-controls="dwdradar" role="tab" data-toggle="tab">$obs.label.radar_tab_dwd</a></li>
        <li role="presentation"><a href="#webcam" aria-controls="webcam" role="tab" data-toggle="tab">$obs.label.radar_tab_webcam</a></li>
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
            <a id="radardwd" name="radardwd" href="https://www.dwd.de/DE/leistungen/radarbild_film/radarbild_film.html"><img src="https://www.dwd.de/DWD/wetter/radar/radfilm_bay_akt.gif" alt="DWD Radar" width="420px"></a>
        </div>
        <div id="webcam" class="tab-content">
            <a id="weathercam" name="weathercam" href="$relative_url/webcam"><img src="$relative_url/images/webcam_small.jpg" alt="Die Webcam der Wetterstation Weiherhammer"></a>
            <div style="text-align:center"><small>$obs.label.radar_content_webcam</small></div>
        </div>
        #if os.path.exists("allsky/allskycam01.up")
        <div id="allsky01" class="tab-content">
            <a id="allskycam01" name="allskycam01" href="https://allsky.ott24.net" target="_blank" rel="noreferrer"><img src="https://allsky.ott24.net/image.jpg" alt="Die AllSky Kamera 1 der PWS Weiherhammer"></a>
        </div>
        #end if
        #if os.path.exists("allsky/allskycam02.up")
        <div id="allsky02" class="tab-content">
            <a id="allskycam02" name="allskycam02" href="https://allsky02.ott24.net" target="_blank" rel="noreferrer"><img src="https://allsky02.ott24.net/image.jpg" alt="Die AllSky Kamera 2 der PWS Weiherhammer"></a>
        </div>
        #end if
    </div>
</div>

<script type="text/javascript">
    jQuery(document).ready(function() {
        setInterval('reloadWebcam()', 30000);
        #if os.path.exists("allsky/allskycam01.up")
        setInterval('reloadAllsky01()', 60000);
        #end if
        #if os.path.exists("allsky/allskycam02.up")
        setInterval('reloadAllsky02()', 60000);
        #end if
    });

    function reloadWebcam() {
        jQuery('#webcam img').each(function() {
            new_image_url = jQuery(this).attr('src').split('?')[0] + "?" + Math.floor(Math.random() * 999999999);
            jQuery(this).attr('src', new_image_url);
        });
    }

    #if os.path.exists("allsky/allskycam01.up")
    function reloadAllsky01() {
        jQuery('#allsky01 img').each(function() {
            new_image_url = jQuery(this).attr('src').split('?')[0] + "?" + Math.floor(Math.random() * 999999999);
            jQuery(this).attr('src', new_image_url);
        });
    }
    #end if
    
    #if os.path.exists("allsky/allskycam02.up")
    function reloadAllsky02() {
        jQuery('#allsky02 img').each(function() {
            new_image_url = jQuery(this).attr('src').split('?')[0] + "?" + Math.floor(Math.random() * 999999999);
            jQuery(this).attr('src', new_image_url);
        });
    }
    #end if
    
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
</script>

<!-- Ende index_radar.inc -->
