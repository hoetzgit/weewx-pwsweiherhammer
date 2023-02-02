<?php
  $date = new DateTime();
  $json = file_get_contents('php://input');
  $results = json_decode($json,true);

  // copy sensor data values to values array
  $values = array();
  foreach ($results["sensordatavalues"] as $sensordatavalues)
  {
    $values[$sensordatavalues["value_type"]] = $sensordatavalues["value"];
  }

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

  $data_file = "api_airrohr.json";
  file_put_contents($data_file, json_encode($data));
?>
ok
