<!--prettier-ignore-->
#errorCatcher Echo
#encoding UTF-8
#set $forecast_source = $Extras.forecast_table_settings.source
#set $forecast_zambretti_active = True if $varExists('forecast.zambretti') and $to_bool($Extras['forecast_zambretti']['enable']) else False
#set $forecat_table_active = True if $varExists('forecast') and len($forecast.weather_periods($forecast_source)) > 0 else False

#if ($varExists('forecast') and ($forecast_zambretti_active or $forecat_table_active)) or 'radar_img' in $Extras
<!--prettier-ignore-->
#set $only_radar = True if not $varExists('forecast') and 'radar_img' in $Extras else False
#set $only_forecast = True if $varExists('forecast') and not 'radar_img' in $Extras else False

<div class="bx--row">
  <header class="bx--col section-header">
    <h2>
      <!--prettier-ignore-->
      #if $varExists('forecast')
        $gettext("Forecast")
      #end if
      #if $varExists('forecast') and 'radar_img' in $Extras
       &
      #end if
      #if 'radar_img' in $Extras
        $gettext("Recent radar")
      #end if
    </h2>
  </header>
</div>
<div class="bx--row">
  <div class="bx--col">
    <div class="bx--row">
      <!--prettier-ignore-->
      #if $varExists('forecast')
      #set forecast_tile_classes = "bx--col-sm-4 bx--col-md-8 bx--col-lg-12 bx--col-xlg-6 bx--col-max-8"
      #if $DisplayOptions.get('layout', 'alternative') == 'classic'
        #set forecast_tile_classes = "bx--col-sm-4 bx--col-md-12 bx--col-lg-12 bx--col-xlg-12 bx--col-max-12"
      #end if
      <div class="$forecast_tile_classes">
        <div class="bx--tile forecast-tile">
          <!--prettier-ignore-->
          #if $varExists('forecast.zambretti') and $to_bool($Extras['forecast_zambretti']['enable'])
          <div class="forecast">
            <h3>Zambretti</h3>
            <p>
              <!--prettier-ignore-->
              The forecast is $forecast.label('Zambretti', $forecast.zambretti.code)<br />
              <span class="issued"
                >Issued at $forecast.zambretti.issued_ts</span
              >
            </p>
          </div>
          #end if
          <div class="forecast">
            <!--prettier-ignore-->
            #include "includes/forecast-table.inc"
          </div>
        </div>
      </div>
      #end if
      <!--prettier-ignore-->
      #if 'radar_img' in $Extras
      #set radar_classes = "bx--col-sm-4 bx--col-md-8 bx--col-lg-12 bx--col-xlg-6 bx--col-max-4"
      #if $DisplayOptions.get('layout', 'alternative') == 'classic'
        #set radar_classes = "bx--col-sm-4 bx--col-md-12 bx--col-lg-12 bx--col-xlg-12 bx--col-max-12"
      #end if
      <div class="$radar_classes">
        <div class="bx--tile tile-radar-forecast">
          <!--prettier-ignore-->
          #if 'radar_url' in $Extras
          <a href="$Extras.radar_url">
            #end if
            <img src="$Extras.radar_img" alt="Radar" loading="lazy" />
            #if 'radar_url' in $Extras
          </a>
          <!--prettier-ignore-->
          #end if
        </div>
      </div>
      #end if
    </div>
  </div>
</div>
#end if