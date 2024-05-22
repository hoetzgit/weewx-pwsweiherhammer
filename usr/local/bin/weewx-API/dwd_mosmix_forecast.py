#!/usr/bin/python3

"""
Parser for (possibly compressed) DWD MOSMIX KML XML files into JSON.
"""

import argparse
import json
import sys
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
            "desc": cls._parse_description(placemark),
            "name": name.text,
            "lat": lat,
            "lng": lng,
            "ele": ele,
        }

    def parse_placemarks(self, fp: IO[bytes], timezones: bool) -> Iterator[Dict[str, Any]]:
        """Give all stations with their properties from ``Placemark`` nodes."""
        tf: TimezoneFinder = TimezoneFinder.get_inst(timezones)
        for elem in self._iter_tag(fp, "kml:Placemark"):
            placemark: Dict[str, Any] = self._parse_placemark(elem)
            placemark["tz"] = tf.timezone_at(lng=placemark["lng"], lat=placemark["lat"])
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
    def write_list(cls, fp: IO[str], items: Iterable[Any]) -> None:
        fp.write("[")
        sep: str = "\n"
        for item in items:
            fp.write(sep)
            sep = ",\n"
            for chunk in cls._encoder.iterencode(item):
                fp.write(chunk)
        fp.write("\n]\n")

    @classmethod
    def write_dict(cls, fp: IO[str], items: Iterable[Tuple[str, Any]]) -> None:
        fp.write("{")
        sep: str = "\n"
        for key, item in items:
            fp.write(f'{sep}{cls._encoder.encode(key)}: ')
            sep = ",\n"
            for chunk in cls._encoder.iterencode(item):
                fp.write(chunk)
        fp.write("\n}\n")


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
    parser.add_argument("--in-file", metavar="MOSMIX.KMZ", type=Path, required=True,
                        help="input kmz/kml file to read")
    parser.add_argument("--out-file", metavar="FILE.JSON", type=Path, required=True,
                        help="output json file to write")
    subparsers = parser.add_subparsers(title="parser modes")
    mode_timestamps = subparsers.add_parser("timestamps", help="parse declared forecast timestamps")
    mode_timestamps.set_defaults(mode="timestamps")
    mode_stations = subparsers.add_parser("stations", help="parse station information")
    mode_stations.set_defaults(mode="stations")
    mode_stations.add_argument("--timezones", action="store_const", const=True, default=False,
                               help="determine timezones from coordinates")
    mode_forecasts = subparsers.add_parser("forecasts", help="parse per-station forecasts")
    mode_forecasts.add_argument("--limit", metavar="STATIONS", type=str, default=None,
                                help="comma-separated list of stations")
    mode_forecasts.set_defaults(mode="forecasts")
    args = parser.parse_args()

    with kml_reader(args.in_file) as ifp:
        with _TempFile(args.out_file) as ofp:
            setlocale(LC_ALL, "C")  # for strptime
            mosmix_parser: DwdMosmixParser = DwdMosmixParser()

            if args.mode == "timestamps":
                _JSONIterWriter.write_list(ofp, mosmix_parser.parse_timestamps(ifp))
            elif args.mode == "stations":
                _JSONIterWriter.write_list(ofp, mosmix_parser.parse_placemarks(
                    ifp, args.timezones
                ))
            elif args.mode == "forecasts":
                _JSONIterWriter.write_dict(ofp, mosmix_parser.parse_forecasts(
                    ifp, set(args.limit.split(",")) if args.limit is not None else None
                ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
