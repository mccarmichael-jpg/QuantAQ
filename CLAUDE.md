# Webber batch plant — PM monitoring analysis (LIPP and Metro Lot)

## Purpose
Test whether PM10 (and PM2.5) at two near-field monitors is elevated when wind blows
from the Webber concrete batch plant (1111 W Loop N Fwy, Houston). Output is intended
for a litigation/audit/media record, so every result must be reproducible and every
assumption stated.

## Standards for this work
- Report only what the data establishes. No intensifiers, no causation claims
  unless the data directly supports them.
- Distinguish observations from inferences explicitly.
- When geometry, device mapping, or data quality is uncertain, STOP and flag it.
  Do not proceed on assumed inputs.
- Quiet, neutral framing. No persuasive language.

## Plant geometry (verified via Google Earth pins, Sep 2026)
Plant parcel corners (decimal degrees):
- NW  29.787323, -95.454927
- NE  29.787365, -95.453403
- SE  29.785800, -95.453312
- SW  29.785824, -95.455055
- Centroid 29.786578, -95.454174

Treat the entire parcel surface as an area source (fugitive dust), not a point source.

## Monitors
| Monitor | Device | Lat, Lon | Position | Bearing to centroid |
|---|---|---|---|---|
| NW LIPP Daycare Corner (01732) | QuantAQ MODULAIR-PM | 29.787369, -95.454878 | 7 m from plant NW corner, on plant property | 142° (SE), 111 m |
| Metro Lot South (01736) | QuantAQ | 29.785728, -95.453639 | 33 m from plant SE corner, just off south edge | 331° (NNW), 108 m |

The two monitors sit on opposite sides of the plant. Wind from the plant at one is
wind away from the plant at the other; this is the core of the test.

Metro Lot was offline for extended periods in prior work. Establish its uptime window
before including any period in analysis.

## Sector definitions
- LIPP full corner sector ~90°–223°; trimmed working sector ~100°–213°
- Metro full corner sector ~274° through N to ~76°; trimmed working sector ~284°–66°
- Use the trimmed full sector as headline; report ±30° centroid cone as secondary check.
- For Metro, report the freeway (610 / I-10 interchange) sub-sector separately —
  it overlaps the plant sector.

## Wind data (two sources, m/s, NOT interchangeable)
| Source | File | Period | Height/exposure | Notes |
|---|---|---|---|---|
| SmartSense rooftop ultrasonic (school Building C Roof, ~200 m W of plant) | data/raw/roof_wind_only.csv (Timestamp_UTC, WindSpeed, WindDir) | 2025-09-29 to 2026-03-24 | rooftop, unobstructed | Sensor spec 0–25 m/s, 0.1 m/s res. 11 rows >25 m/s are out-of-range: DROP. Monthly coverage 74–96%. |
| QuantAQ met head on Metro Lot pole | wx_ws / wx_wd columns in the Metro export | 2026-03-21 14:21 UTC onward | ~4 m pole, brush nearby, freeway E/S | Rows before 2026-03-21 14:21 UTC report 0.0 = sensor not reporting, NOT calm: EXCLUDE. Tree cluster ~WNW near the western edge of Metro's plant sector. |

Overlap check (2026-03-21 to 03-24, 4,578 paired minutes): direction median offset
~+1° (no orientation error); 60% of minutes agree within 30°, 85% of hourly vector
means within 30°. Metro speed ~0.5× rooftop (hourly corr 0.87). Overlap wind was
mostly S–SE; northern-sector agreement is untested.

Rules: use each source for its own period; never splice speeds into one series;
apply the calm cutoff per source; state which source covers which dates in every
output. Sector-edge minutes are noisy (±25°) — hourly aggregation is a valid
robustness check.

## Analytical conventions
- PM10 is the primary metric. PM2.5 secondary.
- Drop calm winds < 1.0 m/s (per source). Expect Metro to lose more minutes.
- Drop gaps entirely; do not interpolate.
- No operating-hours filter by default.
- Ratio of medians (plant sector / not plant sector) with Mann-Whitney one-sided p.
- Control for hour-of-day (geometric mean of hourly ratios) as a robustness check.
- Stratify by season (cold vs warm months) — SE flow dominates Houston's warm season
  and can confound directional results.
- Report data completeness (% of period) per monitor.

## Data
Raw exports in ./data/raw/. Do not edit raw files. Write cleaned outputs to
./data/processed/, figures to ./figures/, scripts to ./src/.

Monitor files are pre-split by month: data/raw/Metro_YYYY-MM.csv and
data/raw/LIPP_YYYY-MM.csv (ACTIVE rows only; id, sn, lat, lon, device_state
already dropped). Glob them.
Columns: timestamp (UTC, ISO Z — THE KEY), timestamp_local (vendor-supplied,
fixed UTC-5 all year, ignores DST — reference only, do not use for analysis),
sample_rh, sample_temp, [Metro only: wx_ws, wx_wd, wx_ws_scalar], pm1, pm25, pm10.
Derive local time from `timestamp` using America/Chicago.

Coverage (% of possible minutes, pm10):
- Metro: Sep-25 3%, Oct 79%, Nov 48%, Dec 1%, Jan–Feb 0%, Mar 75%, Apr–Aug 96–100%, Sep-26 31% (to 9/10)
- LIPP:  Oct-25 3%, Nov 7%, Dec–Aug 99–100%, Sep-26 32% (to 9/10)

roof_wind_only.csv: Timestamp_UTC (naive string, is UTC), WindSpeed (m/s), WindDir
(deg). Minute resolution.

## Open items
- Establish Metro Lot uptime windows (exact gap edges) before including any period.
- LIPP PM period 2025-09-29 to 2026-03-24 pairs with rooftop wind; 2026-03-21
  onward pairs with Metro wind. Decide and document treatment of the overlap.
