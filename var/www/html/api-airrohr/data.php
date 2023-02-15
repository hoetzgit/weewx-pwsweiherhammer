<?php
  $date = new DateTime();
  $json = file_get_contents('php://input');
  $results = json_decode($json,true);

  $data_file = "airrohr_results.json";
  file_put_contents($data_file, json_encode($results));

  // copy sensor data values to values array
  $values = array();
  foreach ($results["sensordatavalues"] as $sensordatavalues)
  {
    $values[$sensordatavalues["value_type"]] = $sensordatavalues["value"];
  }

  $data_file = "airrohr_values.json";
  file_put_contents($data_file, json_encode($values));

  $data = array();
  $data["dateTime"] = intval($date->getTimestamp());

  if (isset($values["SDS_P2"]))
  {
    $data["airrohr_pm2_5"] = floatval($values["SDS_P2"]);
  }
  if (isset($values["SDS_P1"]))
  {
    $data["airrohr_pm10_0"] = floatval($values["SDS_P1"]);
  }
  if (isset($values["temperature"]))
  {
    $data["airrohr_outTemp"] = floatval($values["temperature"]);
  }
  if (isset($values["humidity"]))
  {
    $data["airrohr_outHumidity"] = floatval($values["humidity"]);
  }
  if (isset($values["signal"]))
  {
    $data["airrohr_sig"] = intval($values["signal"]);
    if ($data["airrohr_sig"] <= -100) {
      $data["airrohr_sig_percent"] = 0;
    } else if ($data["airrohr_sig"] >= -50) {
      $data["airrohr_sig_percent"] = 100;
    } else {
      $data["airrohr_sig_percent"] = 2 * ($data["airrohr_sig"] + 100);
    }
  }

  $data_file = "api_airrohr.json";
  file_put_contents($data_file, json_encode($data));
?>
ok
