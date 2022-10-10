#errorCatcher Echo
#encoding UTF-8
<div class="row" style="margin-top:10px;">
    <div id="webcamfull" class="col-xs-12">
        <img itemprop="image" src="$relative_url/images/webcam.jpg" alt="Die Webcam der Wetterstation Weiherhammer" />
    </div>
</div>

<script type="text/javascript">
    jQuery(document).ready(function() {
        setInterval('reloadWebcamFull()', 30000);
    });

    function reloadWebcamFull() {
        jQuery('#webcamfull img').each(function() {
            new_image_url = jQuery(this).attr('src').split('?')[0] + "?" + Math.floor(Math.random() * 999999999);
            jQuery(this).attr('src', new_image_url);
        });
    }
</script>