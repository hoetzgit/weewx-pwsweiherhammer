<?php
  $date = new DateTime();
  $json = file_get_contents('php://input');
  $results = json_decode($json,true);

  // debug
  $data_file = "airrohr_results.json";
  file_put_contents($data_file, json_encode($results, JSON_PRETTY_PRINT));

  // copy sensor data values to values array
  $values = array();
  foreach ($results["sensordatavalues"] as $sensordatavalues)
  {
    $values[$sensordatavalues["value_type"]] = $sensordatavalues["value"];
  }

  // debug
  $data_file = "airrohr_values.json";
  file_put_contents($data_file, json_encode($values, JSON_PRETTY_PRINT));

  $data = array();
  $data["dateTime"] = intval($date->getTimestamp());
  $data["dateTimeISO"] = date("d.m.Y H:i:s", $data["dateTime"]);

  // SDS011

  if (isset($values["SDS_P2"])) {
    $data["airrohr_pm2_5"] = floatval($values["SDS_P2"]);
  }
  if (isset($values["SDS_P1"])) {
    $data["airrohr_pm10_0"] = floatval($values["SDS_P1"]);
  }

  // DHT22

  if (isset($values["temperature"])) {
    $data["airrohr_dht22_outTemp"] = floatval($values["temperature"]);
  }
  if (isset($values["humidity"])) {
    $data["airrohr_dht22_outHumidity"] = floatval($values["humidity"]);
  }

  // BME280

  if (isset($values["BME280_temperature"])) {
    $data["airrohr_bme280_outTemp"] = floatval($values["BME280_temperature"]);
  }
  if (isset($values["BME280_humidity"])) {
    $data["airrohr_bme280_outHumidity"] = floatval($values["BME280_humidity"]);
  }
  if (isset($values["BME280_pressure"])) {
	if (floatval($values["BME280_pressure"]) >= 1080) {
      $data["airrohr_pressure"] = floatval($values["BME280_pressure"] / 100.0);
	} else {
      $data["airrohr_pressure"] = floatval($values["BME280_pressure"]);
    }
  }

  if (isset($values["signal"])) {
    $data["airrohr_signal_level"] = intval($values["signal"]);
    if ($data["airrohr_signal_level"] <= -100) {
      $data["airrohr_signal_percent"] = 0;
    } else if ($data["airrohr_signal_level"] >= -50) {
      $data["airrohr_signal_percent"] = 100;
    } else {
      $data["airrohr_signal_percent"] = 2 * ($data["airrohr_signal_level"] + 100);
    }
    // Ecowitt compatible Signal Level
    if ($data["airrohr_signal_percent"] == 0) {
      $data["airrohr_signal_ecowitt"] = 0;
    } else if ($data["airrohr_signal_percent"] <= 25) {
      $data["airrohr_signal_ecowitt"] = 1;
    } else if ($data["airrohr_signal_percent"] <= 50) {
      $data["airrohr_signal_ecowitt"] = 2;
    } else if ($data["airrohr_signal_percent"] <= 75) {
      $data["airrohr_signal_ecowitt"] = 3;
    } else if ($data["airrohr_signal_percent"] <= 100) {
      $data["airrohr_signal_ecowitt"] = 4;
    }
  }

  $data_file = "api_airrohr.json";
  file_put_contents($data_file, json_encode($data, JSON_PRETTY_PRINT));
  
  $data_file = "/home/weewx/public_html/data/json/current_airrohr.json";
  file_put_contents($data_file, json_encode($data, JSON_PRETTY_PRINT));
  
?>
ok
