#!/usr/bin/env python3
"""
Calculate benchmark statistics from resultCollection session outputs.

Expected input layout (from run-all-benchmarks.ps1):
  <session_dir>/
    baseline/benchmark-runs.csv
    abnormal/benchmark-runs.csv

Outputs:
  - stats-summary.json
  - stats-summary.txt

Statistics reported (for elapsedMs and rows/sec):
  count, mean, stddev (sample), median, min, max, p95, p99

Overhead:
  overhead_pct = (mean_on_ms - mean_off_ms) / mean_off_ms * 100
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import mean, median, stdev
from typing import Dict, List


def percentile(values: List[float], p: float) -> float:
    if not values:
        return float("nan")
    if len(values) == 1:
        return values[0]
    s = sorted(values)
    rank = (p / 100.0) * (len(s) - 1)
    lower = int(math.floor(rank))
    upper = int(math.ceil(rank))
    if lower == upper:
        return s[lower]
    w = rank - lower
    return s[lower] + (s[upper] - s[lower]) * w


def describe(values: List[float]) -> Dict[str, float]:
    if not values:
        return {
            "count": 0,
            "mean": float("nan"),
            "stddev": float("nan"),
            "median": float("nan"),
            "min": float("nan"),
            "max": float("nan"),
            "p95": float("nan"),
            "p99": float("nan"),
        }
    return {
        "count": len(values),
        "mean": mean(values),
        "stddev": stdev(values) if len(values) > 1 else 0.0,
        "median": median(values),
        "min": min(values),
        "max": max(values),
        "p95": percentile(values, 95.0),
        "p99": percentile(values, 99.0),
    }


def load_runs(csv_path: Path) -> Dict[str, List[float]]:
    on_ms: List[float] = []
    off_ms: List[float] = []
    on_rps: List[float] = []
    off_rps: List[float] = []
    on_cpu_ms: List[float] = []
    off_cpu_ms: List[float] = []
    on_heap_delta_bytes: List[float] = []
    off_heap_delta_bytes: List[float] = []

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            on_ms.append(float(row["onElapsedMs"]))
            off_ms.append(float(row["offElapsedMs"]))
            on_rps.append(float(row["onRowsPerSec"]))
            off_rps.append(float(row["offRowsPerSec"]))
            if "onCpuMs" in row and row["onCpuMs"]:
                on_cpu_ms.append(float(row["onCpuMs"]))
            if "offCpuMs" in row and row["offCpuMs"]:
                off_cpu_ms.append(float(row["offCpuMs"]))
            if "onHeapDeltaBytes" in row and row["onHeapDeltaBytes"]:
                on_heap_delta_bytes.append(float(row["onHeapDeltaBytes"]))
            if "offHeapDeltaBytes" in row and row["offHeapDeltaBytes"]:
                off_heap_delta_bytes.append(float(row["offHeapDeltaBytes"]))

    return {
        "onElapsedMs": on_ms,
        "offElapsedMs": off_ms,
        "onRowsPerSec": on_rps,
        "offRowsPerSec": off_rps,
        "onCpuMs": on_cpu_ms,
        "offCpuMs": off_cpu_ms,
        "onHeapDeltaBytes": on_heap_delta_bytes,
        "offHeapDeltaBytes": off_heap_delta_bytes,
    }


def analyze_mode(mode_name: str, csv_path: Path) -> Dict[str, object]:
    runs = load_runs(csv_path)
    on_ms_stats = describe(runs["onElapsedMs"])
    off_ms_stats = describe(runs["offElapsedMs"])
    on_rps_stats = describe(runs["onRowsPerSec"])
    off_rps_stats = describe(runs["offRowsPerSec"])
    on_cpu_stats = describe(runs["onCpuMs"]) if runs["onCpuMs"] else None
    off_cpu_stats = describe(runs["offCpuMs"]) if runs["offCpuMs"] else None
    on_heap_delta_stats = describe(runs["onHeapDeltaBytes"]) if runs["onHeapDeltaBytes"] else None
    off_heap_delta_stats = describe(runs["offHeapDeltaBytes"]) if runs["offHeapDeltaBytes"] else None

    overhead_pct = (
        (on_ms_stats["mean"] - off_ms_stats["mean"]) / off_ms_stats["mean"] * 100.0
        if off_ms_stats["mean"] and not math.isnan(off_ms_stats["mean"])
        else float("nan")
    )

    return {
        "mode": mode_name,
        "sourceCsv": str(csv_path),
        "rvOn": {
            "elapsedMs": on_ms_stats,
            "rowsPerSec": on_rps_stats,
            "cpuMs": on_cpu_stats,
            "heapDeltaBytes": on_heap_delta_stats,
        },
        "rvOff": {
            "elapsedMs": off_ms_stats,
            "rowsPerSec": off_rps_stats,
            "cpuMs": off_cpu_stats,
            "heapDeltaBytes": off_heap_delta_stats,
        },
        "overheadPct": overhead_pct,
    }


def format_stats_block(title: str, stats: Dict[str, float], unit: str) -> List[str]:
    return [
        title,
        f"  mean={stats['mean']:.4f}{unit} stddev={stats['stddev']:.4f}{unit} median={stats['median']:.4f}{unit}",
        f"  min={stats['min']:.4f}{unit} max={stats['max']:.4f}{unit} p95={stats['p95']:.4f}{unit} p99={stats['p99']:.4f}{unit}",
    ]


def latest_session_dir(runs_dir: Path) -> Path:
    sessions = sorted([p for p in runs_dir.glob("session-*") if p.is_dir()])
    if not sessions:
        raise SystemExit(f"No session-* folders found in: {runs_dir}")
    return sessions[-1]


def main() -> int:
    ap = argparse.ArgumentParser(description="Calculate statistics from benchmark resultCollection runs.")
    ap.add_argument(
        "--session-dir",
        type=Path,
        default=None,
        help="Path to a specific session-* directory. Defaults to latest in src/resultCollection/runs.",
    )
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to write stats-summary.{json,txt}. Defaults to session directory.",
    )
    args = ap.parse_args()

    script_dir = Path(__file__).resolve().parent
    runs_dir = script_dir / "runs"

    session_dir = args.session_dir.resolve() if args.session_dir else latest_session_dir(runs_dir)
    baseline_csv = session_dir / "baseline" / "benchmark-runs.csv"
    abnormal_csv = session_dir / "abnormal" / "benchmark-runs.csv"

    if not baseline_csv.exists():
        raise SystemExit(f"Missing baseline benchmark CSV: {baseline_csv}")
    if not abnormal_csv.exists():
        raise SystemExit(f"Missing abnormal benchmark CSV: {abnormal_csv}")

    out_dir = args.output_dir.resolve() if args.output_dir else session_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    baseline = analyze_mode("baseline", baseline_csv)
    abnormal = analyze_mode("abnormal", abnormal_csv)

    report = {
        "sessionDir": str(session_dir),
        "baseline": baseline,
        "abnormal": abnormal,
    }

    json_out = out_dir / "stats-summary.json"
    txt_out = out_dir / "stats-summary.txt"

    json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines: List[str] = []
    lines.append("Benchmark Statistics Summary")
    lines.append(f"session={session_dir}")
    lines.append("")

    for label, section in [("BASELINE", baseline), ("ABNORMAL", abnormal)]:
        lines.append(f"[{label}]")
        lines.append(f"source={section['sourceCsv']}")
        lines.append(f"overheadPct={section['overheadPct']:.4f}")
        lines.extend(format_stats_block("rvOn.elapsedMs", section["rvOn"]["elapsedMs"], "ms"))
        lines.extend(format_stats_block("rvOff.elapsedMs", section["rvOff"]["elapsedMs"], "ms"))
        lines.extend(format_stats_block("rvOn.rowsPerSec", section["rvOn"]["rowsPerSec"], ""))
        lines.extend(format_stats_block("rvOff.rowsPerSec", section["rvOff"]["rowsPerSec"], ""))
        if section["rvOn"]["cpuMs"] and section["rvOff"]["cpuMs"]:
            lines.extend(format_stats_block("rvOn.cpuMs", section["rvOn"]["cpuMs"], "ms"))
            lines.extend(format_stats_block("rvOff.cpuMs", section["rvOff"]["cpuMs"], "ms"))
        if section["rvOn"]["heapDeltaBytes"] and section["rvOff"]["heapDeltaBytes"]:
            lines.extend(format_stats_block("rvOn.heapDeltaBytes", section["rvOn"]["heapDeltaBytes"], "B"))
            lines.extend(format_stats_block("rvOff.heapDeltaBytes", section["rvOff"]["heapDeltaBytes"], "B"))
        lines.append("")

    txt_out.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote: {json_out}")
    print(f"Wrote: {txt_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

