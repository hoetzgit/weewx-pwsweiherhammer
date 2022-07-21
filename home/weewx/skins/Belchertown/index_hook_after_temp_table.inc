#encoding UTF-8
                                #if $Extras.has_key("pws_aqi_enabled") and $Extras.pws_aqi_enabled == '1'
                                <!-- Air Quality Index -->
                                <div class="obs-aqi-divider"></div>
                                <div class="row">
                                    <div class="col-sm-12">
                                        <div class="pws_aqi_outer">
                                        #if $current.pws_aqi_category.has_data
                                          #if $current.pws_aqi_category.raw == 0.0
                                            $obs.label.pws_aqi_long: <span class="pws-aqi-category" title="$obs.label.ttt_pws_aqi_very_good">$obs.label.pws_aqi_very_good</span>
                                          #else if $current.pws_aqi_category.raw == 1.0
                                            $obs.label.pws_aqi_long: <span class="pws-aqi-category" title="$obs.label.ttt_pws_aqi_good">$obs.label.pws_aqi_good</span>
                                          #else if $current.pws_aqi_category.raw == 2.0
                                            $obs.label.pws_aqi_long: <span class="pws-aqi-category" title="$obs.label.ttt_pws_aqi_moderate">$obs.label.pws_aqi_moderate</span>
                                          #else if $current.pws_aqi_category.raw == 3.0
                                            $obs.label.pws_aqi_long: <span class="pws-aqi-category" title="$obs.label.ttt_pws_aqi_poor">$obs.label.pws_aqi_poor</span>
                                          #else if $current.pws_aqi_category.raw == 4.0
                                            $obs.label.pws_aqi_long: <span class="pws-aqi-category" title="$obs.label.ttt_pws_aqi_very_poor">$obs.label.pws_aqi_very_poor</span>
                                          #else
                                            $obs.label.pws_aqi_long: <span class="pws-aqi-category">$obs.label.pws_aqi_unknown</span>
                                          #end if
                                        #else
                                            $obs.label.pws_aqi_long: <span class="pws-aqi-category">$obs.label.pws_aqi_unknown</span>
                                        #end if
                                        </div>
                                    </div>
                                    <div class="col-sm-12 obs-aqi-container">
                                        <div class="col-sm-6 obs-aqi-table-container">
                                            <table class="obs-aqi-table">
                                                <tbody>
                                                    <tr>
                                                        <td class="obs-aqi-table-title" title="$obs.label.ttt_pm2_5_short"><span class="pws_aqi_pm2_5_dot"></span> $obs.label.sds011_pm2_5_short</td>
                                                        <td class="obs-aqi-table-title border-left" title="$obs.label.ttt_pm10_0_short"><span class="pws_aqi_pm10_0_dot"></span> $obs.label.sds011_pm10_0_short</td>
                                                    </tr>
                                                    <tr>
                                                        <td class="obs-aqi-table-value sds011-pm2_5" title="$obs.label.ttt_pm2_5_short">$current.sds011_pm2_5</td>
                                                        <td class="obs-aqi-table-value border-left sds011-pm10_0" title="$obs.label.ttt_pm10_0_short">$current.sds011_pm10_0</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div>
                                        <div class="col-sm-6 obs-aqi-table-container">
                                            <table class="obs-aqi-table">
                                                <tbody>
                                                    <tr>
                                                        <td class="obs-aqi-table-title border-left" title="$obs.label.ttt_o3_short"><span class="pws_aqi_o3_dot"></span> $obs.label.uba_o3_short</td>
                                                        <td class="obs-aqi-table-title border-left" title="$obs.label.ttt_no2_short"><span class="pws_aqi_no2_dot"></span> $obs.label.uba_no2_short</td>
                                                    </tr>
                                                    <tr>
                                                        <td class="obs-aqi-table-value border-left uba-o3" title="$obs.label.ttt_o3_short">$current.uba_o3</td>
                                                        <td class="obs-aqi-table-value border-left uba-no2" title="$obs.label.ttt_no2_short">$current.uba_no2</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                    ##<div class="col-sm-12 center"><a href="#almanac" data-toggle="modal" data-target="#almanac">$obs.label.almanac_more_details</a></div>
                                </div>
                                #end if