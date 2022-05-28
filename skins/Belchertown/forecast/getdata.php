<?php

/**
 * Copyright 2018 Meteoware.com
 * http://tools.wettersoftware.de
 *
 * You are free to use and copy the material free of charge in
 * any medium or format as long the following conditions are met:
 *
 * - You must give appropriate credit, provide a link to the author.
 * You may do so in any reasonable manner, but not in any way that suggests the
 * licensor endorses you or your use.
 *
 * You may not use the material for commercial purposes or on commercial sites.
 *
 * If you remix, transform, or build upon the material, you may not distribute
 * the modified material.
 *
 *
 * THIS SOFTWARE IS PROVIDED BY METEOWARE.COM ''AS IS'' AND ANY
 * EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL METEOWARE.COM BE LIABLE FOR ANY
 * DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */


/**
 * version 2.0.0
 *
 */

error_reporting(0);


// calculate relative humidity (TTT(K), Td(K))
function getHumidity($T, $TD) {
  if (is_numeric($T) && is_numeric($TD)) {
    $T = round($T - 273.15, 1);
    $TD = round($TD - 273.15, 1);
    $RH=round(100*(exp((17.625*$TD)/(243.04+$TD)) / exp((17.625*$T)/(243.04+$T))));
  } else {
    $RH = '---';
  }
  return $RH;
}


function xml2array ( $xmlObject, $out = array () ) {
  foreach ( (array) $xmlObject as $index => $node )
  $out[$index] = ( is_object ( $node ) ) ? xml2array ( $node ) : $node;
  return $out;
}


function getParamArray($rootObj, $id) {
  foreach ($rootObj as $param) {
    if ((string) $param['elementName'] == $id) {
      $output = preg_replace('!\s+!', ';', (string) $param->value);
      $output = explode(';', $output);
      array_shift($output);
      return $output;
    }
  }
}


// check id
$id = substr($_GET['id'].'_',0,5);
$re = '/^([A-Z]{1}[0-9_]{4})$|^([0-9]{5})$/';
if (!preg_match($re, $id, $matches, PREG_OFFSET_CAPTURE, 0)) {
    die('Bitte richtige ID der Station eingeben!');
}


// download source data
$dir = sys_get_temp_dir().'/';
$fileName = 'mtg-v2-tmp.zip';
$fn = $dir.$fileName;


$url = 'http://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/single_stations/'.$id.'/kml/MOSMIX_L_LATEST_'.$id.'.kmz';

file_put_contents($fn, fopen($url, 'r'));
register_shutdown_function(function() use($fn) {
    unlink($fn);
});


$za = new ZipArchive();
$res = $za->open($fn);
for($i=0; $i<$za->numFiles; $i++) {
    $stat = $za->statIndex($i);
    $data = file_get_contents('zip://' . realpath($fn) . '#' . $stat['name']);

    $data = str_replace(
      array("kml:", "dwd:"),
      array("", ""),
      $data
    );

    $MAX_COUNT = 24*7+3;
    $xml = simplexml_load_string($data);
    $timeSteps = xml2array($xml->Document->ExtendedData->ProductDefinition->ForecastTimeSteps->TimeStep);

    $lines = array_fill(0, count($timeSteps), array());


    foreach ($timeSteps as $key => $value) {
        $date = new DateTime($value);
        array_push($lines[$key], $date->format('d.m.y'));
        array_push($lines[$key], $date->format('H:i'));
    } // $timeSteps


    $alias = array(
      'TN' => 'Tn',       // Minimum temperature - within the last 12 hours
      'TX' => 'Tx',       // Maximum temperature - within the last 12 hours
      'TTT' => 'TT',      // Temperature 2m above surface
      'SunD1' => 'SS1',
      'Nh' => 'NH',       // High cloud cover (>7 km)
      'Nm' => 'NM',       // Midlevel cloud cover (2-7 km) (%)
      'Nl' => 'NL',       // Low cloud cover (lower than 2 km) (%)
      'RR3c' => 'RR%6',   // Total precipitation during the last hour (kg/m2),
      'R130' => 'RR6',    // Probability of precipitation > 3.0 mm during the last hour
      'DD' => 'dd',       // 0°..360°, Wind direction
      'FF' => 'ff',       // Wind speed (m/s)
      'FX1' => 'fx',      // Maximum wind gust within the last hour (m/s)
      'FXh25' => 'fx6',   // Probability of wind gusts >= 25kn within the last 12 hours (% 0..100)
      'FXh40' => 'fx9',   // Probability of wind gusts >= 40kn within the last 12 hours
      'FXh55' => 'fx11',  // Probability of wind gusts >= 55kn within the last 12 hours
      'PPPP' => 'PPPP',   // Surface pressure, reduced (Pa)
      'N' => 'N',
      'Td' => 'Td',
      'SS24'=> 'SS24',
    );
    $ids = array_keys($alias);


    $fnode = $xml->Document->Placemark->ExtendedData->Forecast;
    foreach ($ids as $id) {
        $param = getParamArray($fnode, $id);
        if (count($param) === 0) {
          $param = array_fill(0, count($timeSteps), '---');
        }

        foreach ($param as $key => $value) {

            $v = $value;

            if (in_array($id, array('TN', 'TX', 'TTT', 'Td'))) {
                $v = round($value - 273.15, 1);
            }

            if ($id == 'PPPP') {
                $v = round($value / 100, 1);
            }

            if ($id == 'SunD1') {
                $v = round($value);
            }

            if (in_array($id, array('N', 'Nh', 'Nm', 'Nl'))) {
                $v = round($value * 8 / 100);
            }

            if ($value == '-') {
                $v = '---';
            }

            array_push($lines[$key], $v);
        }
    }// foreach $ids


    // calculate humidity
    $t = getParamArray($fnode, 'TTT');
    $d = getParamArray($fnode, 'Td');
    foreach ($t as $key => $value) {
        array_push($lines[$key], getHumidity($value, $d[$key]));
    }

    // output header
    echo str_replace(
      array_keys($alias),
      array_values($alias),
      '"forecast","parameter","'.implode('","', $ids).'","hu",'."\r\n"
    );

    // slice & output content
    $lines = array_slice($lines, 0, $MAX_COUNT);
    foreach ($lines as $line) {
        echo '"'.implode('","', $line).'",'."\r\n";
    }

} // foreach

?>
