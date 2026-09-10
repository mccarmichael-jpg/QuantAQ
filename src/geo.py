"""Geometry: plant parcel, monitor positions, bearings, sector definitions.

All bearings are degrees clockwise from true north, computed on a local
equirectangular projection (errors < 0.1° at these distances).
"""
import math
import numpy as np

# Plant parcel corners (CLAUDE.md, Google Earth pins Sep 2026)
PARCEL = {"NW": (29.787323, -95.454927), "NE": (29.787365, -95.453403),
          "SE": (29.785800, -95.453312), "SW": (29.785824, -95.455055)}
CENTROID = (29.786578, -95.454174)

MONITORS = {
    "lipp":  {"name": "NW LIPP Daycare Corner (01732)", "lat": 29.787369, "lon": -95.454878},
    "metro": {"name": "Metro Lot South (01736)",        "lat": 29.785728, "lon": -95.453639},
}

# Trimmed working sectors from CLAUDE.md (headline). (start, end) clockwise, may wrap.
PLANT_SECTOR = {"lipp": (100.0, 213.0), "metro": (284.0, 66.0)}
CONE_HALF_WIDTH = 30.0  # secondary check: ±30° about centroid bearing

# ---- Freeway geometry: ASSUMED, NOT VERIFIED -------------------------------------
# OSM access is blocked in this environment. These two numbers define where the
# freeway mainlanes are relative to Metro and MUST be replaced with Google Earth
# pins before the freeway sub-sector is used in any reported result.
#   FWY_610_LON : longitude of the 610 (West Loop) mainlane centerline abreast of
#                 the plant. Assumed ~75 m east of the plant's east edge (-95.4533).
#   FWY_I10_LAT : latitude of the I-10 (Katy Fwy) mainlane centerline south of the
#                 plant. Assumed ~215 m south of Metro.
FWY_610_LON = -95.4525   # ASSUMED
FWY_I10_LAT = 29.7838    # ASSUMED
FWY_ASSUMED = True
# ----------------------------------------------------------------------------------


def _m_per_deg(lat):
    return 111_195.0, 111_195.0 * math.cos(math.radians(lat))


def bearing_dist(from_lat, from_lon, to_lat, to_lon):
    """Bearing (deg, 0-360) and distance (m) from -> to."""
    mlat, mlon = _m_per_deg((from_lat + to_lat) / 2)
    dy = (to_lat - from_lat) * mlat
    dx = (to_lon - from_lon) * mlon
    return (math.degrees(math.atan2(dx, dy)) % 360.0), math.hypot(dx, dy)


def in_sector(deg, start, end):
    """Vectorised: is bearing `deg` within the clockwise arc start->end (inclusive)?"""
    deg = np.asarray(deg, dtype=float) % 360.0
    if start <= end:
        return (deg >= start) & (deg <= end)
    return (deg >= start) | (deg <= end)


def cone(mon):
    b, _ = bearing_dist(MONITORS[mon]["lat"], MONITORS[mon]["lon"], *CENTROID)
    return ((b - CONE_HALF_WIDTH) % 360.0, (b + CONE_HALF_WIDTH) % 360.0)


def freeway_sectors():
    """Bearing ranges from Metro toward the freeway, computed from the ASSUMED
    coordinates above. Returns dict of (start, end) arcs:
      'freeway_ese'     : 610 abreast of Metro (east) clockwise to the 610/I-10
                          interchange centre (south-east). This is the sub-sector
                          the kickoff prompt asks for ("east through south-east").
      'freeway_610_north': 610 mainlanes north of abreast, i.e. the stretch that
                          lies BEHIND the plant's east edge as seen from Metro. This
                          is the portion that overlaps Metro's plant sector.
    """
    m = MONITORS["metro"]
    b_abreast, _ = bearing_dist(m["lat"], m["lon"], m["lat"], FWY_610_LON)          # 90°
    b_interchange, _ = bearing_dist(m["lat"], m["lon"], FWY_I10_LAT, FWY_610_LON)
    # 610 northward: from abreast up to a point 400 m north along the mainlanes
    b_north, _ = bearing_dist(m["lat"], m["lon"], m["lat"] + 400 / 111_195.0, FWY_610_LON)
    return {"freeway_ese": (b_abreast, b_interchange),
            "freeway_610_north": (b_north, b_abreast)}


def report():
    print("Bearings / distances from each monitor to parcel corners and centroid:")
    for mon, p in MONITORS.items():
        print(f"\n{p['name']}  ({p['lat']}, {p['lon']})")
        for k, (la, lo) in {**PARCEL, "centroid": CENTROID}.items():
            b, d = bearing_dist(p["lat"], p["lon"], la, lo)
            print(f"  {k:9s} bearing {b:6.1f}°  dist {d:6.1f} m")
        cs = [bearing_dist(p["lat"], p["lon"], la, lo)[0] for la, lo in PARCEL.values()]
        print(f"  trimmed plant sector (CLAUDE.md): {PLANT_SECTOR[mon]}")
        c = cone(mon); print(f"  ±30° centroid cone: ({c[0]:.1f}, {c[1]:.1f})")
    f = freeway_sectors()
    print("\nMetro freeway sub-sectors (from ASSUMED coordinates "
          f"610 lon={FWY_610_LON}, I-10 lat={FWY_I10_LAT}):")
    for k, (a, b) in f.items():
        print(f"  {k:18s} {a:6.1f}° -> {b:6.1f}°")


if __name__ == "__main__":
    report()
