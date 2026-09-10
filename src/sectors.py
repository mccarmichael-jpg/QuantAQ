"""Task 3: tag each PM minute (per monitor, per wind source) by wind direction.

Tags (all based on the direction the wind blows FROM, i.e. wd):
  sector_plant   : wd inside the trimmed plant sector for that monitor (headline)
  sector_cone    : wd within ±30° of the bearing monitor -> parcel centroid
  sector_freeway : Metro only; wd inside the 'freeway_ese' arc (see geo.py).
                   Also 'freeway_610_north' reported separately. Both arcs derive
                   from ASSUMED coordinates flagged in geo.py.
Calm minutes (ws < 1.0 m/s) are excluded from all tag counts and from the saved
tagged table, per CLAUDE.md.
"""
from pathlib import Path
import pandas as pd
import geo
from load import load_all
from wind import build_wind_lookup, attach_wind, PROC, LOOKUP_PATH

TAGGED_PATH = PROC / "pm_wind_tagged.parquet"


def tag(mon: str, pm: pd.DataFrame, wind: pd.DataFrame) -> pd.DataFrame:
    j = attach_wind(pm, wind)
    j = j[~j.calm].copy()
    j["monitor"] = mon
    j["sector_plant"] = geo.in_sector(j.wd, *geo.PLANT_SECTOR[mon])
    j["sector_cone"] = geo.in_sector(j.wd, *geo.cone(mon))
    if mon == "metro":
        f = geo.freeway_sectors()
        j["sector_freeway"] = geo.in_sector(j.wd, *f["freeway_ese"])
        j["sector_freeway_610_north"] = geo.in_sector(j.wd, *f["freeway_610_north"])
    else:
        j["sector_freeway"] = False
        j["sector_freeway_610_north"] = False
    j["local_ts"] = j.minute.dt.tz_convert("America/Chicago")
    return j


def build_tagged(d: dict | None = None, wind: pd.DataFrame | None = None) -> pd.DataFrame:
    d = d or load_all()
    wind = wind if wind is not None else build_wind_lookup(d)
    cols = ["timestamp", "pm1", "pm25", "pm10", "sample_rh", "sample_temp"]
    out = [tag(mon, d[mon].loc[d[mon].pm10.notna(), cols], wind) for mon in ("metro", "lipp")]
    return pd.concat(out, ignore_index=True)


def tag_counts(t: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (mon, src), g in t.groupby(["monitor", "wind_source"]):
        n = len(g)
        row = {"monitor": mon, "wind_source": src, "n_minutes": n,
               "period": f"{g.minute.min():%Y-%m-%d} .. {g.minute.max():%Y-%m-%d}",
               "plant": int(g.sector_plant.sum()), "plant_pct": round(100 * g.sector_plant.mean(), 1),
               "not_plant": int((~g.sector_plant).sum()),
               "cone": int(g.sector_cone.sum()), "cone_pct": round(100 * g.sector_cone.mean(), 1)}
        if mon == "metro":
            row["freeway_ese"] = int(g.sector_freeway.sum())
            row["freeway_ese_pct"] = round(100 * g.sector_freeway.mean(), 1)
            row["freeway_610N"] = int(g.sector_freeway_610_north.sum())
            row["freeway_610N_pct"] = round(100 * g.sector_freeway_610_north.mean(), 1)
            row["plant_and_610N"] = int((g.sector_plant & g.sector_freeway_610_north).sum())
        rows.append(row)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    d = load_all()
    w = pd.read_parquet(LOOKUP_PATH) if LOOKUP_PATH.exists() else build_wind_lookup(d)
    t = build_tagged(d, w)
    t.to_parquet(TAGGED_PATH, index=False)
    print("Sector definitions used (degrees, wind FROM):")
    for mon in ("lipp", "metro"):
        c = geo.cone(mon)
        print(f"  {mon:5s} plant {geo.PLANT_SECTOR[mon]}  cone ({c[0]:.1f}, {c[1]:.1f})")
    f = geo.freeway_sectors()
    print(f"  metro freeway_ese {tuple(round(x,1) for x in f['freeway_ese'])}  "
          f"freeway_610_north {tuple(round(x,1) for x in f['freeway_610_north'])}"
          f"  [ASSUMED geometry: {geo.FWY_ASSUMED}]")
    print("\nTag counts per monitor per wind source (calm minutes excluded):")
    tc = tag_counts(t)
    print(tc.to_string(index=False))
    tc.to_csv(PROC / "task3_tag_counts.csv", index=False)
    print("\nPM10 minutes by 16-point wind sector (calm excluded), % of each monitor/source:")
    t["sector16"] = ((t.wd + 11.25) // 22.5 % 16).astype(int)
    names = "N NNE NE ENE E ESE SE SSE S SSW SW WSW W WNW NW NNW".split()
    piv = (t.groupby(["monitor", "wind_source", "sector16"]).size()
             .unstack("sector16").fillna(0).astype(int))
    piv.columns = [names[i] for i in piv.columns]
    print((100 * piv.div(piv.sum(axis=1), axis=0)).round(1).to_string())
    print(f"\nSaved {TAGGED_PATH.name} ({len(t):,} rows) and task3_tag_counts.csv")
