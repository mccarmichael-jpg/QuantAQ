Read CLAUDE.md first; it holds the geometry, sector definitions, wind-source rules,
file schemas, and reporting standards for this repo. Everything below assumes you have.

Files in data/raw/:
- Metro_YYYY-MM.csv   Metro Lot South (QuantAQ 01736), PM + onboard wind, one file per month
- LIPP_YYYY-MM.csv    NW LIPP Daycare Corner (QuantAQ 01732), PM only, one file per month
- roof_wind_only.csv  rooftop ultrasonic wind, 2025-09-29 to 2026-03-24, m/s

Task 1 — Load and profile. Do not analyze yet.
Write src/load.py that globs the monthly files per monitor, parses `timestamp` as
UTC, adds a `local_ts` column via America/Chicago (do not use timestamp_local),
and returns one dataframe per monitor plus the rooftop wind. Reproduce the monthly
coverage figures in CLAUDE.md; flag any month that disagrees by more than 2 points.
Report the first Metro timestamp with wx_ws > 0, and the count of rooftop rows
> 25 m/s. Report exact start/end of every Metro PM gap longer than 6 hours.
Stop and show me the coverage tables before going further.

Task 2 — Wind assignment.
Build a wind lookup keyed on UTC minute with a `wind_source` column: rooftop for
2025-09-29 to 2026-03-24, Metro for 2026-03-21 14:21 UTC onward. For the overlap,
keep both rows tagged separately; do not average or splice. Drop rooftop rows
> 25 m/s. Drop Metro wind rows before 2026-03-21 14:21 UTC. Apply the < 1.0 m/s
calm cutoff per source and report how many minutes each monitor loses to it under
each source.

Task 3 — Sector tagging.
Using the coordinates and trimmed sectors in CLAUDE.md, tag each PM minute as
plant / not_plant for its monitor. Add a secondary tag for the ±30° cone around
the centroid bearing. For Metro, add a freeway sub-sector tag (bearings toward the
610 / I-10 interchange, east through south-east — compute from the monitor
position and state the range you used). Show me tag counts per monitor per wind
source before computing any ratios.

Task 4 — Directional test. Only after I confirm Tasks 1–3.
Per monitor, per wind source, per season (cold: Nov–Feb, warm: May–Sep, shoulder
otherwise): median PM10 in plant vs not_plant, ratio, Mann-Whitney one-sided p,
n in each group; then the same using hourly vector-mean wind instead of minute
wind. Pollution rose (PM10 median by 16 sectors) per monitor per source. Save
tables to data/processed/ and figures to figures/. Write results.md stating
observations only, with the wind source and period next to every number.

Rules that override any default you might apply:
- Never interpolate gaps. Never splice the two wind speed series.
- Local time comes from `timestamp` + America/Chicago, never from timestamp_local.
- If geometry, units, or coverage look inconsistent with CLAUDE.md, stop and ask.
- No causal language. Observations first; inferences labeled as inferences.
