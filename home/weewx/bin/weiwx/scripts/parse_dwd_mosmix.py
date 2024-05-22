#!/usr/bin/python3
# Copyright (C) 2023 Henry Ott
# Based on the code from https://www.hackitu.de/dwd_mosmix/
"""
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.

    Parser for (possibly compressed) DWD MOSMIX KML XML files for a station into JSON.

    https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/all_stations/kml/MOSMIX_L_LATEST.kmz
    https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_S/all_stations/kml/MOSMIX_S_LATEST_240.kmz
"""
import argparse
import json
import sys
import requests
import os
import shutil
import urllib.request
import time
from datetime import datetime, timezone
from locale import setlocale, LC_ALL
from pathlib import Path
from zipfile import ZipFile, BadZipFile

from contextlib import contextmanager
from typing import Optional, List, IO, Tuple, Dict, Generator, ClassVar, Set, Iterator, Any, Iterable, Union, Literal

try:
    from lxml.etree import iterparse, _Element as Element  # nosec
except ModuleNotFoundError:
    from xml.etree.ElementTree import iterparse, Element  # type: ignore[misc] # nosec

CONVERT_DICT = {
    'FF':       lambda x: x * 3.6,      # m/s --> km/h  wind speed
    'FX1':      lambda x: x  *3.6,      # m/s --> km/h  wind gust within last hour
    'FX3':      lambda x: x * 3.6,      # m/s --> km/h  wind gust within last 3 hours
    'FXh':      lambda x: x * 3.6,      # m/s --> km/h  wind gust within last 12 hours
    'PPPP':     lambda x: x * 0.01,     # Pa  --> hPa   surface pressure, reduced
    'T5cm':     lambda x: x - 273.15,   # K   --> °C    temperature 5cm above surface
    'Td':       lambda x: x - 273.15,   # K   --> °C    dewpoint 2m above surface
    'TG':       lambda x: x - 273.15,   # K   --> °C    min surface temp 5cm 12 hours
    'TM':       lambda x: x - 273.15,   # K   --> °C    mean temp last 24 hours
    'TN':       lambda x: x - 273.15,   # K   --> °C    min temp last 12 hours
    'TTT':      lambda x: x - 273.15,   # K   --> °C    temperature 2m above surface
    'TX':       lambda x: x - 273.15,   # K   --> °C    max temp last 12 hours
    'Rad1h':    lambda x: x / 3.6,      # kJ  --> Wh    Global Irradiance
    'timestamp':lambda x: x - 3600      # MOSMIX timestamps represent the predictions for the last hour.
}                                       # However, I query the current hour.
                                        # Therefore 1 hour is subtracted from the timestamp.

URL_DICT = {
    'MOSMIX_L': 'https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/all_stations/kml/MOSMIX_L_LATEST.kmz',
    'MOSMIX_S': 'https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_S/all_stations/kml/MOSMIX_S_LATEST_240.kmz'
}

@staticmethod
def dateISOfromTimstamp(timestamp, tz='Europe/Berlin'):
    import pytz
    timezone = pytz.timezone(tz)
    datetz = datetime.fromtimestamp(timestamp, timezone)
    return datetz.isoformat()

@staticmethod
def exception_output(e, addcontent=None, debug=1, log_failure=True):
    if log_failure or debug > 0:
        exception_type, exception_object, exception_traceback = sys.exc_info()
        filename = os.path.split(exception_traceback.tb_frame.f_code.co_filename)[1]
        line = exception_traceback.tb_lineno
        print("ERROR: Exception: %s - %s File: %s Line: %s" % (e.__class__.__name__, e, str(filename), str(line)))
        if addcontent is not None:
            print("ERROR: addcontent: %s" % (str(addcontent)))

class TimezoneFinder:
    def timezone_at(self, **kwargs) -> Optional[str]:
        return None

    @classmethod
    def get_inst(cls, enabled: bool) -> "TimezoneFinder":
        if not enabled:
            return cls()
        try:
            from timezonefinder import TimezoneFinder as TF  # import only when needed at runtime due to overhead
            return TF(in_memory=True)  # type: ignore
        except ModuleNotFoundError:
            return cls()


class DwdMosmixParser:
    """
    Parsing methods for DWD MOSMIX KML XML files, namely either:
      * list of timestamps from ``ForecastTimeSteps``
      * properties of stations in ``Placemark``
      * value series in ``Forecast``
    Note that all methods iteratively consume from an i/o stream, such that it cannot be reused without rewinding it.
    """

    _ns: ClassVar[Dict[str, str]] = {  # abbreviations for used XML namespaces for readability
        "kml": r"http://www.opengis.net/kml/2.2",
        "dwd": r"https://opendata.dwd.de/weather/lib/pointforecast_dwd_extension_V1_0.xsd",
    }
    _undef_sign: ClassVar[str] = "-"  # dwd:FormatCfg/dwd:DefaultUndefSign

    @classmethod
    def _iter_tag(cls, fp: IO[bytes], tag: str) -> Iterator[Element]:
        if ":" in tag:
            ns, tag = tag.split(":", maxsplit=1)
            tag = f"{{{cls._ns[ns]}}}{tag}"
        for _evt, elem in iterparse(fp, events=["end"]):  # type: str, Element
            if elem.tag == tag:
                yield elem
                elem.clear()

    def parse_product(self, fp: IO[bytes]) -> Iterator[Dict[str, Any]]:
        """Give product with the properties from ``ProductDefinition`` nodes."""
        for elem in self._iter_tag(fp, "dwd:ProductDefinition"):
            issuer: Optional[Element] = elem.find("dwd:Issuer", self._ns)
            if issuer is None or not issuer.text:
                raise ValueError("No 'ProductDefinition.Issuer' found")
            genProcess: Optional[Element] = elem.find("dwd:GeneratingProcess", self._ns)
            if genProcess is None or not genProcess.text:
                raise ValueError("No 'ProductDefinition.dwd:GeneratingProcess' found")
            issueTime: Optional[Element] = elem.find("dwd:IssueTime", self._ns)
            if issueTime is None or not issueTime.text:
                raise ValueError("No 'ProductDefinition.IssueTime' found")
            timestamp = self._parse_timestamp(issueTime.text)
            timestampISO = dateISOfromTimstamp(timestamp)
            break
        product: Dict[str, Any] = {"provider": issuer.text, "generator": genProcess.text, "generated": timestamp, "generatedISO": timestampISO}
        yield product

    @classmethod
    def _parse_timestamp(cls, value: Optional[str]) -> int:
        if not value:
            raise ValueError("Undefined timestamp")
        try:
            return int(datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc).timestamp())
        except ValueError as e:
            raise ValueError(f"Cannot parse timestamp '{value}'") from e

    def parse_timestamps(self, fp: IO[bytes]) -> Iterator[int]:
        """Give all ``ForecastTimeSteps`` as integer timestamps."""
        for elem in self._iter_tag(fp, "dwd:ForecastTimeSteps"):
            yield from (self._parse_timestamp(_.text) for _ in elem.iterfind("dwd:TimeStep", self._ns))
            break

    @classmethod
    def _parse_coordinates(cls, value: str) -> Tuple[float, float, float]:
        values: List[str] = value.split(",")
        if len(values) != 3:
            raise ValueError(f"Cannot parse coordinates '{value}'")
        try:
            return float(values[0]), float(values[1]), float(values[2])
        except ValueError as e:
            raise ValueError(f"Cannot parse coordinates '{value}'") from e

    @classmethod
    def _parse_description(cls, placemark: Element) -> str:
        description: Optional[Element] = placemark.find("kml:description", cls._ns)
        if description is None or not description.text:
            raise ValueError("No 'Placemark.description' found")
        return description.text

    @classmethod
    def _parse_placemark(cls, placemark: Element) -> Dict[str, Any]:
        name: Optional[Element] = placemark.find("kml:name", cls._ns)
        if name is None or not name.text:
            raise ValueError("No 'Placemark.name' found")

        coordinates: Optional[Element] = placemark.find("kml:Point/kml:coordinates", cls._ns)
        if coordinates is None or not coordinates.text:
            raise ValueError("No 'Placemark.Point.coordinates' found")
        lng, lat, ele = cls._parse_coordinates(coordinates.text)

        return {
                    "name": cls._parse_description(placemark),
                    "wmo_code": name.text,
                    "latitude": lat,
                    "longitude": lng,
                    "elevation": ele,
               }

    def parse_placemarks(self, fp: IO[bytes], timezones: bool, stations: Optional[Set[str]]) -> Iterator[Dict[str, Any]]:
        """Give all stations with their properties from ``Placemark`` nodes."""
        tf: TimezoneFinder = TimezoneFinder.get_inst(timezones)
        for elem in self._iter_tag(fp, "kml:Placemark"):
            station: str = self._parse_description(elem)
            if stations is None or station in stations:
                placemark: Dict[str, Any] = self._parse_placemark(elem)
                placemark["timezone"] = tf.timezone_at(lng=placemark["longitude"], lat=placemark["latitude"])
                yield placemark

    @classmethod
    def _parse_values(cls, values: str) -> List[Optional[float]]:
        try:
            return [float(_) if _ != cls._undef_sign else None for _ in values.split()]
        except ValueError as e:
            raise ValueError(f"Cannot parse forecast values '{values}'") from e

    @classmethod
    def _parse_forecast(cls, placemark: Element) -> Dict[str, List[Optional[float]]]:
        forecasts: Dict[str, List[Optional[float]]] = {}
        for forecast in placemark.iterfind("kml:ExtendedData/dwd:Forecast", cls._ns):
            name: Optional[Union[str, bytes]] = forecast.attrib.get(f"{{{cls._ns['dwd']}}}elementName")
            if not isinstance(name, str) or not name:
                raise ValueError("No 'Forecast.elementName' found")

            value: Optional[Element] = forecast.find("dwd:value", cls._ns)
            if value is None or not value.text:
                raise ValueError("No 'Forecast.value' found")

            forecasts[name] = cls._parse_values(value.text)
        return forecasts

    def parse_forecasts(self, fp: IO[bytes],
                        stations: Optional[Set[str]]) -> Iterator[Tuple[str, Dict[str, List[Optional[float]]]]]:
        """Give all value series in ``Forecast``, optionally limited to certain stations."""
        for elem in self._iter_tag(fp, "kml:Placemark"):
            station: str = self._parse_description(elem)
            if stations is None or station in stations:
                yield station, self._parse_forecast(elem)


@contextmanager
def kmz_reader(fp: IO[bytes]) -> Generator[IO[bytes], None, None]:
    """
    Wrap reading from *.kmz files, which are merely compressed *.kml (XML) files.
    """

    try:
        with ZipFile(fp) as zf:
            if len(zf.filelist) != 1:
                raise OSError(f"Unexpected archive contents: {' '.join(zf.namelist())}")
            with zf.open(zf.filelist[0]) as zp:
                yield zp
    except BadZipFile as e:
        raise OSError(str(e)) from None


@contextmanager
def kml_reader(filename: Path, compressed: Optional[bool] = None) -> Generator[IO[bytes], None, None]:
    """
    Read access for *.kml or compressed *.kmz files.
    """

    with open(filename, "rb") as fp:
        if compressed is True or (compressed is None and filename.suffix == ".kmz"):
            with kmz_reader(fp) as zp:
                yield zp
        else:
            yield fp


class _JSONIterWriter:
    """
    Write JSON incrementally from an iterator, i.e., without needing to buffer all objects and their string
    representations before eventually writing out everything at once.
    Also, parsers might opt for reading line-wise for a cheap incremental JSON decoder implementation.
    """

    _encoder: ClassVar[json.JSONEncoder] = json.JSONEncoder(indent=None, sort_keys=True, ensure_ascii=False,
                                                            allow_nan=False, check_circular=False)

    @classmethod
    def writeJSON(cls, ifp: IO[str], ofp: IO[str], args, url) -> None:
        setlocale(LC_ALL, "C")  # for strptime
        mosmix_parser: DwdMosmixParser = DwdMosmixParser()
        data = dict()
        data['source'] = args.in_file
        data['sourceUrl'] = url
        now = int(time.time())
        data['dateTime'] = now
        data['dateTimeISO'] = dateISOfromTimstamp(now)

        # parse data
        product: Iterable[Any] = mosmix_parser.parse_product(ifp)
        for item in product:
            data.update(item)

        ifp.seek(0)
        station: Iterable[Any] = mosmix_parser.parse_placemarks(ifp, args.timezones, args.station)
        data['station'] = dict()
        for item in station:
            data['station'].update(item)

        ifp.seek(0)
        timestamps: Iterable[Any] = mosmix_parser.parse_timestamps(ifp)
        data['hourly'] = dict()
        data['hourly']['time'] = list()
        for item in timestamps:
            if 'timestamp' in CONVERT_DICT:
                item = CONVERT_DICT['timestamp'](int(item))
            data['hourly']['time'].append(item)

        ifp.seek(0)
        values: Iterable[Tuple[str, Any]] = mosmix_parser.parse_forecasts(ifp, args.station)
        for key, item in values:
            for obs in item:
                if str(obs) in CONVERT_DICT:
                    for i, val in enumerate(item[obs]):
                        if val is not None:
                            item[obs][i] = round(CONVERT_DICT[str(obs)](float(item[obs][i])), 5)
                # else:
                    # for i, val in enumerate(item[obs]):
                        # if val is not None:
                            # item[obs][i] = round(float(item[obs][i]), 5)
                data['hourly'][str(obs)] = item[obs]
        ofp.write(json.dumps(data, indent=4))


class _TempFile:
    """
    Instead of updating files in-place, write to a temporary file and atomically move when done via context manager.
    This should prevent dirty/partial reads and leaving behind replaced but corrupt output files upon error.
    """

    def __init__(self, target_filename: Path) -> None:
        self._fn: Path = target_filename
        self._fn_tmp: Path = target_filename.with_suffix(target_filename.suffix + ".tmp")
        self._fp: Optional[IO[str]] = None

    def __enter__(self) -> IO[str]:
        if self._fp is None:
            self._fp = self._fn_tmp.open("w", encoding="utf-8", newline="")
        return self._fp

    def __exit__(self, exc_type, exc_val, traceback) -> Literal[False]:
        if self._fp is not None:
            self._fp.close()
            self._fp = None

            if exc_type:
                self._fn_tmp.unlink(missing_ok=True)
            else:
                self._fn_tmp.replace(self._fn)
        return False  # passing through exceptions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip())
    parser.add_argument("--in-file", metavar="MOSMIX.KMZ", type=str, default='MOSMIX_S', required=True,
                        help="input MOSMIX_L/MOSMIX_S file to read")
    parser.add_argument("--out-file", metavar="FILE.JSON", type=Path, required=True,
                        help="output json file to write")
    parser.add_argument("--timezones", action="store_const", const=True, default=False,
                        help="determine timezones from coordinates")
    parser.add_argument("--station", metavar="STATIONS", type=str, default="WEIDEN", required=True,
                        help="For which station should the values be loaded")

    args = parser.parse_args()

    url = URL_DICT[args.in_file]
    in_file: Path = Path('/tmp/' + args.in_file + '.kmz')
    urllib.request.urlretrieve(url, in_file)

    with kml_reader(in_file) as ifp:
        with _TempFile(args.out_file) as ofp:
            _JSONIterWriter.writeJSON(ifp, ofp, args, url)
    return 0


if __name__ == "__main__":
    sys.exit(main())