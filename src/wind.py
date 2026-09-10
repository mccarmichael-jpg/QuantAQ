"""Task 2: wind lookup keyed on UTC minute, one row per (minute, wind_source).

Sources (never spliced):
  rooftop : data/raw/roof_wind_only.csv, 2025-09-29 .. 2026-03-24. Rows with
            WindSpeed > 25 m/s (sensor range) or null are dropped.
  metro   : wx_ws / wx_wd from the Metro export, 2026-03-21 14:21 UTC onward.
            Rows before that report 0.0 (sensor not reporting) and are dropped.
Overlap 2026-03-21 14:21 .. 2026-03-24 22:27 UTC keeps both rows, tagged.
Calm flag: ws < 1.0 m/s, applied per source. Calm rows are KEPT in the lookup
with calm=True so downstream code can report what it drops.
"""
from pathlib import Path
import pandas as pd
from load import load_all, METRO_WIND_START, ROOF_MAX_MS

PROC = Path(__file__).resolve().parent.parent / "data" / "processed"
CALM_MS = 1.0
LOOKUP_PATH = PROC / "wind_lookup.parquet"


def build_wind_lookup(d: dict | None = None) -> pd.DataFrame:
    d = d or load_all()
    r = d["roof"]
    roof = (r.loc[r.WindSpeed.notna() & r.WindDir.notna() & (r.WindSpeed <= ROOF_MAX_MS)]
             .assign(minute=lambda x: x.timestamp.dt.floor("min"))
             .rename(columns={"WindSpeed": "ws", "WindDir": "wd"})
             [["minute", "ws", "wd"]].drop_duplicates("minute"))
    roof["wind_source"] = "rooftop"

    m = d["metro"]
    metro = (m.loc[(m.timestamp >= METRO_WIND_START) & m.wx_ws.notna() & m.wx_wd.notna()]
              .assign(minute=lambda x: x.timestamp.dt.floor("min"))
              .rename(columns={"wx_ws": "ws", "wx_wd": "wd"})
              [["minute", "ws", "wd"]].drop_duplicates("minute"))
    metro["wind_source"] = "metro"

    w = pd.concat([roof, metro], ignore_index=True)
    w["calm"] = w.ws < CALM_MS
    return w.sort_values(["minute", "wind_source"]).reset_index(drop=True)


def attach_wind(pm: pd.DataFrame, wind: pd.DataFrame) -> pd.DataFrame:
    """Inner-join PM minutes to wind. A PM minute in the overlap yields two rows."""
    pm = pm.assign(minute=pm.timestamp.dt.floor("min")).drop_duplicates("minute")
    return pm.merge(wind, on="minute", how="inner")


def calm_loss_table(d: dict, wind: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for mon in ("metro", "lipp"):
        pm = d[mon].loc[d[mon].pm10.notna(), ["timestamp", "pm10"]]
        j = attach_wind(pm, wind)
        for src, g in j.groupby("wind_source"):
            rows.append({"monitor": mon, "wind_source": src,
                         "pm_minutes_with_wind": len(g), "calm_minutes": int(g.calm.sum()),
                         "calm_pct": round(100 * g.calm.mean(), 1),
                         "remaining": int((~g.calm).sum()),
                         "period": f"{g.minute.min():%Y-%m-%d} .. {g.minute.max():%Y-%m-%d}"})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    d = load_all()
    w = build_wind_lookup(d)
    PROC.mkdir(exist_ok=True)
    w.to_parquet(LOOKUP_PATH, index=False)
    r = d["roof"]
    print("Rooftop raw rows:", len(r), " dropped >25 m/s:", int((r.WindSpeed > ROOF_MAX_MS).sum()),
          " dropped null:", int(r.WindSpeed.isna().sum() | 0), " kept:", int((w.wind_source == "rooftop").sum()))
    m = d["metro"]
    print("Metro raw rows:", len(m), " dropped before", METRO_WIND_START, ":",
          int((m.timestamp < METRO_WIND_START).sum()), " kept minutes:", int((w.wind_source == "metro").sum()))
    ov = w.groupby("minute").wind_source.nunique()
    ov = ov[ov > 1]
    print(f"Overlap minutes with both sources: {len(ov)}  ({ov.index.min()} .. {ov.index.max()})")
    print("\nCalm (<1.0 m/s) minutes in each wind source:")
    print(w.groupby("wind_source").calm.agg(minutes="size", calm="sum", calm_pct=lambda s: round(100*s.mean(),1)).to_string())
    print("\nPM10 minutes lost to the calm cutoff, per monitor per wind source:")
    t = calm_loss_table(d, w)
    print(t.to_string(index=False))
    t.to_csv(PROC / "task2_calm_loss.csv", index=False)
    print(f"\nSaved {LOOKUP_PATH.name} ({len(w):,} rows) and task2_calm_loss.csv")
