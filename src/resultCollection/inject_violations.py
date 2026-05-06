#!/usr/bin/env python3
"""
Inject controlled violations into the cleaned ECU CSV (rectangular).

Requirements implemented:
- Keep same file size (modify existing records only; no add/remove rows).
- Convert about ~20% of dataset into violation rows (default target).
- Inject at least one violation per flag used by the Spring server:
    - voltageOutOfRange    (RPM > 900 and BatteryVoltage_V outside [11.5, 15.5])
    - coolantTooHigh       (CoolantTemp_C > 110)
    - throttleSpike        (dt in (0, 0.2] and |Δthrottle| > 25)
    - loadMapMismatch      (|Load - MAPSource| > 30)
- Target one violation *type* at a time with spacing between injected indices.
- "Leave space between records" by enforcing a minimum row gap between injected
  violations, and also ensuring injected conditions do not persist into adjacent
  rows (especially for throttleSpike, which depends on previous row).
- Generate a text summary with totals for testing.

Default assumptions:
- Input is produced by tools/clean_ecu_datalog.py and contains the columns used
  by the server: ThrottlePosition, EngineRunningTime, Load, MAPSource, RPM,
  BatteryVoltage_V, CoolantTemp_C.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import math
import os
import pathlib
import random
from collections import Counter
from typing import Dict, List, Tuple


FLAGS = [
    "voltageOutOfRange",
    "coolantTooHigh",
    "throttleSpike",
    "loadMapMismatch",
]


@dataclasses.dataclass
class InjectionPlan:
    target_fraction: float = 0.20
    # For 20% injection, the average spacing is ~4 rows. A small gap still
    # provides separation while keeping the target feasible.
    min_gap_rows: int = 3
    seed: int = 1337


def _idx(header: List[str], col: str) -> int:
    try:
        return header.index(col)
    except ValueError:
        raise SystemExit(f"Missing required column: {col}")


def _parse_float(v: str) -> float:
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except ValueError:
        return 0.0


def _format_float(x: float) -> str:
    # Preserve reasonable CSV readability; avoid scientific notation.
    if math.isfinite(x):
        s = f"{x:.6f}".rstrip("0").rstrip(".")
        return s if s else "0"
    return ""


def _choose_indices(n_rows: int, n_target: int, min_gap: int, rng: random.Random) -> List[int]:
    """
    Choose indices in [1, n_rows-2] with at least min_gap apart.
    We avoid index 0 (header) and edges to allow neighbor adjustments.
    """
    if n_rows < 3:
        return []

    candidates = list(range(1, n_rows - 1))
    rng.shuffle(candidates)
    chosen: List[int] = []
    blocked = [False] * n_rows

    def block(i: int):
        lo = max(0, i - min_gap)
        hi = min(n_rows - 1, i + min_gap)
        for j in range(lo, hi + 1):
            blocked[j] = True

    for i in candidates:
        if len(chosen) >= n_target:
            break
        if blocked[i]:
            continue
        chosen.append(i)
        block(i)

    chosen.sort()
    return chosen


def inject_voltage_out_of_range(rows: List[List[str]], h: List[str], i: int) -> None:
    rpm = _idx(h, "RPM")
    v = _idx(h, "BatteryVoltage_V")
    # Ensure RPM > 900 on injected row.
    rows[i][rpm] = _format_float(max(_parse_float(rows[i][rpm]), 1200.0))
    # Force voltage outside [11.5, 15.5] but keep plausible-ish (e.g., 10.5V).
    rows[i][v] = _format_float(10.5)


def inject_coolant_too_high(rows: List[List[str]], h: List[str], i: int) -> None:
    ct = _idx(h, "CoolantTemp_C")
    rows[i][ct] = _format_float(120.0)


def inject_load_map_mismatch(rows: List[List[str]], h: List[str], i: int) -> None:
    load = _idx(h, "Load")
    map_src = _idx(h, "MAPSource")
    base = _parse_float(rows[i][load])
    rows[i][map_src] = _format_float(base + 80.0)  # |Δ| > 30 guaranteed


def inject_throttle_spike(rows: List[List[str]], h: List[str], i: int) -> None:
    """
    Trigger throttleSpike exactly once.

    Server condition:
      dt = EngineRunningTime - prevRunTime
      if 0 < dt <= 0.2 and |ThrottlePosition - prevThrottle| > 25 => flag

    To avoid creating a second spike on (i+1), we also set ThrottlePosition at (i+1)
    to match the injected spike value, so |Δ| ~ 0 on next step.
    """
    thr = _idx(h, "ThrottlePosition")
    rt = _idx(h, "EngineRunningTime")

    prev_thr = _parse_float(rows[i - 1][thr])
    prev_rt = _parse_float(rows[i - 1][rt])
    cur_rt = _parse_float(rows[i][rt])

    # Ensure dt in (0, 0.2]
    # If dt too large/small, adjust current runtime slightly while keeping monotonic overall.
    desired_dt = 0.1
    if cur_rt <= prev_rt:
        cur_rt = prev_rt + desired_dt
        rows[i][rt] = _format_float(cur_rt)
    else:
        dt_val = cur_rt - prev_rt
        if dt_val > 0.2:
            cur_rt = prev_rt + desired_dt
            rows[i][rt] = _format_float(cur_rt)

    spike_thr = prev_thr + 30.0
    rows[i][thr] = _format_float(spike_thr)

    # Prevent reverse spike on the next row by aligning i+1 throttle to spike value.
    if i + 1 < len(rows):
        rows[i + 1][thr] = _format_float(spike_thr)
        # Also keep i+1 runtime >= i runtime to avoid cross-flag side effects.
        next_rt = _parse_float(rows[i + 1][rt])
        if next_rt <= cur_rt:
            rows[i + 1][rt] = _format_float(cur_rt + desired_dt)


INJECTORS = {
    "voltageOutOfRange": inject_voltage_out_of_range,
    "coolantTooHigh": inject_coolant_too_high,
    "throttleSpike": inject_throttle_spike,
    "loadMapMismatch": inject_load_map_mismatch,
}


def inject(
    input_csv: pathlib.Path,
    output_csv: pathlib.Path,
    summary_txt: pathlib.Path,
    plan: InjectionPlan,
) -> None:
    rng = random.Random(plan.seed)

    with input_csv.open("r", encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        header = next(r, None)
        if header is None:
            raise SystemExit("Input CSV is empty")
        rows = [row for row in r]

    # Validate required columns exist.
    required = [
        "ThrottlePosition",
        "EngineRunningTime",
        "Load",
        "MAPSource",
        "RPM",
        "BatteryVoltage_V",
        "CoolantTemp_C",
    ]
    for col in required:
        _idx(header, col)

    n_rows = len(rows)
    if n_rows < 10:
        raise SystemExit("Not enough rows to inject violations safely.")

    target_total = int(n_rows * plan.target_fraction)
    # Ensure at least one per flag.
    base_per_flag = max(1, target_total // len(FLAGS))
    counts_target = {flag: base_per_flag for flag in FLAGS}
    # Distribute remainder.
    remainder = max(0, target_total - (base_per_flag * len(FLAGS)))
    for flag in rng.sample(FLAGS, k=min(remainder, len(FLAGS))):
        counts_target[flag] += 1

    # Choose indices with spacing for all injections, then assign flags.
    all_needed = sum(counts_target.values())
    indices = _choose_indices(n_rows=n_rows, n_target=all_needed, min_gap=plan.min_gap_rows, rng=rng)
    if len(indices) < all_needed:
        raise SystemExit(
            f"Could only schedule {len(indices)} injections with min_gap_rows={plan.min_gap_rows}, "
            f"but need {all_needed}. Reduce --min-gap-rows or --target-fraction."
        )

    assignments: List[Tuple[int, str]] = []
    idx_cursor = 0
    # Inject one flag type at a time (grouped) to satisfy "target one violation at a time".
    for flag in FLAGS:
        for _ in range(counts_target[flag]):
            assignments.append((indices[idx_cursor], flag))
            idx_cursor += 1

    injected_counts = Counter()
    injected_rows = set()

    # Apply injections.
    for i, flag in assignments:
        # Ensure we don't double-inject same row.
        if i in injected_rows:
            continue
        INJECTORS[flag](rows, header, i)
        injected_counts[flag] += 1
        injected_rows.add(i)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

    summary_txt.parent.mkdir(parents=True, exist_ok=True)
    total = sum(injected_counts.values())
    with summary_txt.open("w", encoding="utf-8") as f:
        f.write("Injected violations summary\n")
        f.write(f"input={input_csv}\n")
        f.write(f"output={output_csv}\n")
        f.write(f"seed={plan.seed}\n")
        f.write(f"target_fraction={plan.target_fraction}\n")
        f.write(f"min_gap_rows={plan.min_gap_rows}\n")
        f.write(f"rows_total={n_rows}\n")
        f.write(f"violations_injected_total={total}\n")
        f.write("\nBy flag:\n")
        for flag in FLAGS:
            f.write(f"- {flag}: {injected_counts.get(flag, 0)}\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Inject controlled violations into cleaned ECU CSV.")
    ap.add_argument(
        "--input",
        type=pathlib.Path,
        default=None,
        help="Input CSV (default: ../../dataset/20180713-home2mimos_clean.csv relative to this script)",
    )
    ap.add_argument(
        "--output",
        type=pathlib.Path,
        default=None,
        help="Output CSV (default: <input>_abnormal.csv)",
    )
    ap.add_argument(
        "--summary",
        type=pathlib.Path,
        default=None,
        help="Summary TXT path (default: alongside output as violations_summary.txt)",
    )
    ap.add_argument("--target-fraction", type=float, default=0.20, help="Fraction of rows to inject (default 0.20).")
    ap.add_argument("--min-gap-rows", type=int, default=3, help="Minimum gap between injected violations (default 3).")
    ap.add_argument("--seed", type=int, default=1337, help="RNG seed (default 1337).")
    args = ap.parse_args()

    script_dir = pathlib.Path(__file__).resolve().parent
    default_in = (script_dir / ".." / ".." / "dataset" / "20180713-home2mimos_clean.csv").resolve()
    input_csv = args.input.resolve() if args.input is not None else default_in
    if not input_csv.exists():
        raise SystemExit(f"Input CSV not found: {input_csv}")

    output_csv = args.output.resolve() if args.output is not None else input_csv.with_name(input_csv.stem + "_abnormal.csv")
    summary_txt = (
        args.summary.resolve()
        if args.summary is not None
        else output_csv.with_name("violations_summary.txt")
    )

    plan = InjectionPlan(
        target_fraction=float(args.target_fraction),
        min_gap_rows=int(args.min_gap_rows),
        seed=int(args.seed),
    )
    inject(input_csv=input_csv, output_csv=output_csv, summary_txt=summary_txt, plan=plan)
    print(f"Wrote abnormal CSV: {output_csv}")
    print(f"Wrote summary: {summary_txt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

