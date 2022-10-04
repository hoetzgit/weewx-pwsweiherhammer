#encoding UTF-8
<div class="row" style="margin-top:10px;">
    <div id="webcamrpifull" class="col-xs-12">
        <img itemprop="image" src="$relative_url/images/webcamrpi.jpg" alt="Die RPi Webcam der Wetterstation Weiherhammer" />
    </div>
</div>

<script type="text/javascript">
    jQuery(document).ready(function() {
        setInterval('reloadWebcamRPiFull()', 30000);
    });

    function reloadWebcamRPiFull() {
        jQuery('#webcamrpifull img').each(function() {
            new_image_url = jQuery(this).attr('src').split('?')[0] + "?" + Math.floor(Math.random() * 999999999);
            jQuery(this).attr('src', new_image_url);
        });
    }
</script>