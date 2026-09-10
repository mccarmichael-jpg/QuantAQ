"""Task 1: load and profile raw monitor + wind exports. No analysis.

Usage: python src/load.py   (prints coverage tables and QA flags)
Import: from load import load_all -> dict(metro=df, lipp=df, roof=df)
"""
from pathlib import Path
import glob
import pandas as pd

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
TZ = "America/Chicago"
METRO_WIND_START = pd.Timestamp("2026-03-21 14:21:00", tz="UTC")
ROOF_MAX_MS = 25.0

# Coverage figures stated in CLAUDE.md (pm10, % of possible minutes)
CLAUDE_COVERAGE = {
    "metro": {"2025-09": 3, "2025-10": 79, "2025-11": 48, "2025-12": 1, "2026-01": 0,
              "2026-02": 0, "2026-03": 75, "2026-04": 96, "2026-05": 96, "2026-06": 96,
              "2026-07": 96, "2026-08": 96, "2026-09": 31},
    "lipp":  {"2025-10": 3, "2025-11": 7, "2025-12": 99, "2026-01": 99, "2026-02": 99,
              "2026-03": 99, "2026-04": 99, "2026-05": 99, "2026-06": 99, "2026-07": 99,
              "2026-08": 99, "2026-09": 32},
}
# CLAUDE.md gives ranges "96-100" and "99-100" for Apr-Aug / Dec-Aug; treat those as
# lower bounds when comparing (flag only if below range-2 or above 100).
RANGE_MONTHS = {"metro": {"2026-04", "2026-05", "2026-06", "2026-07", "2026-08"},
                "lipp": {"2025-12", "2026-01", "2026-02", "2026-03", "2026-04",
                         "2026-05", "2026-06", "2026-07", "2026-08"}}
PERIOD_END = pd.Timestamp("2026-09-10 15:50:25", tz="UTC")  # last export row


def _load_monitor(prefix: str) -> pd.DataFrame:
    files = sorted(glob.glob(str(RAW / f"{prefix}_????-??.csv")))
    if not files:
        raise FileNotFoundError(f"no {prefix} files in {RAW}")
    df = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    df["local_ts"] = df["timestamp"].dt.tz_convert(TZ)
    return df


def load_roof() -> pd.DataFrame:
    df = pd.read_csv(RAW / "roof_wind_only.csv")
    df["timestamp"] = pd.to_datetime(df["Timestamp_UTC"], utc=True)
    df = df.drop(columns="Timestamp_UTC").sort_values("timestamp").reset_index(drop=True)
    df["local_ts"] = df["timestamp"].dt.tz_convert(TZ)
    return df


def load_all() -> dict:
    return {"metro": _load_monitor("Metro"), "lipp": _load_monitor("LIPP"), "roof": load_roof()}


def monthly_coverage(df: pd.DataFrame, col: str = "pm10") -> pd.DataFrame:
    """% of possible UTC minutes in each calendar month with a non-null `col`.
    Denominator is the FULL calendar month, including the final partial month
    (this is the convention used for the CLAUDE.md figures; Sep-26 is 'to 9/10').
    `elapsed_pct` uses the elapsed period to PERIOD_END instead."""
    valid = df.loc[df[col].notna(), "timestamp"].dt.floor("min").drop_duplicates()
    counts = valid.dt.tz_localize(None).dt.to_period("M").value_counts().sort_index()
    rows = []
    for period, n in counts.items():
        start = period.start_time.tz_localize("UTC")
        full = int((period.end_time.tz_localize("UTC") - start).total_seconds() // 60) + 1
        elapsed = int((min(period.end_time.tz_localize("UTC"), PERIOD_END) - start)
                      .total_seconds() // 60) + 1
        rows.append({"month": str(period), "valid_minutes": int(n), "possible": full,
                     "coverage_pct": round(100 * n / full, 1),
                     "elapsed_pct": round(100 * n / elapsed, 1)})
    return pd.DataFrame(rows).set_index("month")


def compare_coverage(name: str, cov: pd.DataFrame) -> pd.DataFrame:
    ref = CLAUDE_COVERAGE[name]
    out = cov.copy()
    out["claude_md"] = [ref.get(m) for m in out.index]
    flags = []
    for m, row in out.iterrows():
        exp = ref.get(m)
        if exp is None:
            flags.append("not in CLAUDE.md"); continue
        lo = exp - 2
        hi = 100 if m in RANGE_MONTHS[name] else exp + 2
        flags.append("" if lo <= row.coverage_pct <= hi else "MISMATCH")
    out["flag"] = flags
    for m in ref:
        if m not in out.index:
            out.loc[m] = [0, None, 0.0, 0.0, ref[m], "" if ref[m] <= 2 else "MISMATCH (no file)"]
    return out.sort_index()


def gaps(df: pd.DataFrame, col: str, min_hours: float = 6) -> pd.DataFrame:
    t = df.loc[df[col].notna(), "timestamp"].sort_values()
    d = t.diff()
    idx = d[d > pd.Timedelta(hours=min_hours)].index
    return pd.DataFrame({
        "gap_start": t.shift(1)[idx].values, "gap_end": t[idx].values,
        "hours": (d[idx] / pd.Timedelta(hours=1)).round(1).values})


if __name__ == "__main__":
    pd.set_option("display.width", 160)
    d = load_all()
    for name in ("metro", "lipp"):
        df = d[name]
        print(f"\n=== {name.upper()}  rows={len(df):,}  "
              f"{df.timestamp.min()} -> {df.timestamp.max()}")
        print(compare_coverage(name, monthly_coverage(df)).to_string())

    m = d["metro"]
    first_wind = m.loc[m.wx_ws > 0, "timestamp"].min()
    print(f"\nFirst Metro timestamp with wx_ws > 0: {first_wind}"
          f"   (CLAUDE.md: {METRO_WIND_START})")
    n_zero_before = int(((m.timestamp < METRO_WIND_START) & (m.wx_ws == 0)).sum())
    n_before = int((m.timestamp < METRO_WIND_START).sum())
    print(f"Metro rows before that cutoff: {n_before:,}; of which wx_ws == 0: {n_zero_before:,}")

    r = d["roof"]
    print(f"\nRooftop rows: {len(r):,}  {r.timestamp.min()} -> {r.timestamp.max()}")
    print(f"Rooftop rows with WindSpeed > {ROOF_MAX_MS} m/s: {int((r.WindSpeed > ROOF_MAX_MS).sum())}"
          f"   (CLAUDE.md: 11)")
    print(f"Rooftop rows with null WindSpeed: {int(r.WindSpeed.isna().sum()):,}")

    print("\nMetro PM10 gaps > 6 h:")
    print(gaps(m, "pm10").to_string(index=False))
    print("\nLIPP PM10 gaps > 6 h:")
    print(gaps(d["lipp"], "pm10").to_string(index=False))
