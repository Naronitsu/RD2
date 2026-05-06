#!/usr/bin/env python3
"""
Clean ECU Manager %DataLog% exports into a rectangular CSV.

What it does:
- Reads the channel order from the metadata block (Channel/Type/DisplayMaxMin).
- Finds the first "Log :" line (gives the base date for timestamps).
- Parses subsequent comma-separated rows (sparse/delta style).
- Forward-fills missing fields (blank entries) per column.
- Writes a clean CSV.

Notes:
- The log stores many values as scaled integers. This script applies only a few
  conservative conversions by default:
    - BatteryVoltage: mV -> V (value * 0.001)
    - AirTemp/CoolantTemp: Kelvin*10 -> Celsius (value*0.1 - 273.15)
  All other channels are left as numeric values without scaling assumptions.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import datetime as dt
import pathlib
import sys
from typing import Callable, Iterable, Optional


@dataclasses.dataclass(frozen=True)
class ChannelDef:
    name: str
    typ: Optional[str] = None
    display_max: Optional[float] = None
    display_min: Optional[float] = None


def _parse_display_max_min(value: str) -> tuple[Optional[float], Optional[float]]:
    parts = [p.strip() for p in value.split(",")]
    if len(parts) != 2:
        return None, None
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None, None


def parse_datalog_header(lines: Iterable[str]) -> tuple[list[ChannelDef], Optional[str], list[str]]:
    """
    Returns (channels, log_date_yyyymmdd, remaining_lines_from_log).
    """
    channels: list[ChannelDef] = []
    cur_name: Optional[str] = None
    cur_type: Optional[str] = None
    cur_max: Optional[float] = None
    cur_min: Optional[float] = None

    buffered_after_log: list[str] = []
    log_date: Optional[str] = None
    in_log = False

    for raw in lines:
        line = raw.strip("\n\r")
        if not in_log and line.startswith("Log :"):
            # Example: "Log : 20180713 07:54:58"
            in_log = True
            rhs = line.split(":", 1)[1].strip() if ":" in line else ""
            # rhs begins with YYYYMMDD
            if rhs:
                log_date = rhs.split()[0].strip()
            continue

        if in_log:
            buffered_after_log.append(line)
            continue

        if line.startswith("Channel :"):
            # Commit previous channel if we have one.
            if cur_name is not None:
                channels.append(ChannelDef(cur_name, cur_type, cur_max, cur_min))
            cur_name = line.split(":", 1)[1].strip()
            cur_type = None
            cur_max = None
            cur_min = None
        elif line.startswith("Type :"):
            cur_type = line.split(":", 1)[1].strip()
        elif line.startswith("DisplayMaxMin :"):
            mx, mn = _parse_display_max_min(line.split(":", 1)[1].strip())
            cur_max, cur_min = mx, mn

    if cur_name is not None and not in_log:
        channels.append(ChannelDef(cur_name, cur_type, cur_max, cur_min))

    return channels, log_date, buffered_after_log


def _parse_numeric(s: str) -> Optional[float]:
    s = s.strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def iter_sparse_rows(
    data_lines: Iterable[str],
    n_channels: int,
) -> Iterable[tuple[str, list[Optional[float]]]]:
    """
    Yields (time_str, values) where values length == n_channels (sparse allowed).
    """
    for line in data_lines:
        if not line or line.startswith("%"):
            continue
        parts = line.split(",")
        if len(parts) == 0:
            continue
        time_str = parts[0].strip()
        raw_vals = parts[1:]
        if len(raw_vals) < n_channels:
            raw_vals = raw_vals + [""] * (n_channels - len(raw_vals))
        elif len(raw_vals) > n_channels:
            raw_vals = raw_vals[:n_channels]
        values = [_parse_numeric(v) for v in raw_vals]
        yield time_str, values


def forward_fill_rows(
    sparse_rows: Iterable[tuple[str, list[Optional[float]]]],
    n_channels: int,
) -> Iterable[tuple[str, list[Optional[float]]]]:
    last: list[Optional[float]] = [None] * n_channels
    for time_str, values in sparse_rows:
        filled = []
        for i, v in enumerate(values):
            if v is None:
                filled.append(last[i])
            else:
                filled.append(v)
                last[i] = v
        yield time_str, filled


def _parse_timestamp(log_date_yyyymmdd: str, time_str: str) -> Optional[dt.datetime]:
    # time_str example: "07:54:58.031"
    try:
        base = dt.datetime.strptime(log_date_yyyymmdd, "%Y%m%d").date()
    except ValueError:
        return None

    # Some logs may omit milliseconds.
    for fmt in ("%H:%M:%S.%f", "%H:%M:%S"):
        try:
            t = dt.datetime.strptime(time_str, fmt).time()
            return dt.datetime.combine(base, t)
        except ValueError:
            continue
    return None


def default_conversions() -> dict[str, tuple[str, Callable[[float], float]]]:
    """
    Return mapping channel_name -> (new_unit_suffix, converter).
    Only apply very safe conversions.
    """
    return {
        "BatteryVoltage": ("V", lambda x: x * 0.001),
        "AirTemp": ("C", lambda x: (x * 0.1) - 273.15),
        "CoolantTemp": ("C", lambda x: (x * 0.1) - 273.15),
    }


def clean_datalog(
    input_path: pathlib.Path,
    output_path: pathlib.Path,
    keep_raw: bool,
) -> None:
    with input_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        all_lines = list(f)

    channels, log_date, data_lines = parse_datalog_header(all_lines)
    if not channels:
        raise SystemExit("No channels found. Is this an ECU Manager %DataLog% export?")
    if not log_date:
        raise SystemExit('No "Log :" date found. File may be incomplete/corrupt.')

    n = len(channels)
    conversions = default_conversions()

    out_cols: list[str] = ["timestamp"]
    for ch in channels:
        if ch.name in conversions:
            unit, _fn = conversions[ch.name]
            out_cols.append(f"{ch.name}_{unit}")
            if keep_raw:
                out_cols.append(f"{ch.name}_raw")
        else:
            out_cols.append(ch.name)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as out_f:
        w = csv.writer(out_f)
        w.writerow(out_cols)

        sparse = iter_sparse_rows(data_lines, n_channels=n)
        filled = forward_fill_rows(sparse, n_channels=n)

        for time_str, vals in filled:
            ts = _parse_timestamp(log_date, time_str)
            if ts is None:
                # Skip malformed rows.
                continue

            row: list[object] = [ts.isoformat(timespec="milliseconds")]
            for ch, v in zip(channels, vals, strict=False):
                if ch.name in conversions:
                    unit, fn = conversions[ch.name]
                    if v is None:
                        row.append("")
                        if keep_raw:
                            row.append("")
                    else:
                        row.append(fn(v))
                        if keep_raw:
                            row.append(v)
                else:
                    row.append("" if v is None else v)
            w.writerow(row)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Clean ECU Manager %DataLog% CSV into a rectangular CSV.")
    p.add_argument("input", type=pathlib.Path, help="Path to ECU Manager %DataLog% file")
    p.add_argument(
        "-o",
        "--output",
        type=pathlib.Path,
        default=None,
        help="Output CSV path (default: <input>_clean.csv next to input)",
    )
    p.add_argument(
        "--keep-raw",
        action="store_true",
        help="Keep extra *_raw columns for converted channels",
    )
    args = p.parse_args(argv)

    in_path: pathlib.Path = args.input
    if args.output is None:
        out_path = in_path.with_name(in_path.stem + "_clean.csv")
    else:
        out_path = args.output

    clean_datalog(in_path, out_path, keep_raw=bool(args.keep_raw))
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

