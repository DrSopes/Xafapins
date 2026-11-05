# Verification

The Spain expansion adds tests for all 19 regions, Canary/Balearic and Ceuta/Melilla coverage, weather samples for tiny territories, and refusal to extrapolate weather across a >60 km gap. Existing date, missing-data, atomic-write, clipping, season and weather-index tests remain in place.

All **12 Python tests and 7 JavaScript tests** passed. JavaScript tests cover pH×10 conversion, unknown/nodata handling, acidity categories, forest-response parsing, WMS axis order/URL construction, national app initialization, regional switching, stale-response protection, and forest/pH/weather overlay switching. Controller tests use stubbed map/DOM adapters in Node, not a real browser, and make no network calls.

Live API smoke tests on 5 November 2026 successfully retrieved PNG map tiles from MITECO forest formations, ISRIC pH and IGN national topography. Point queries at 2.4°E, 41.8°N returned:

- Forest: **Hayedos (Fagus sylvatica)**.
- Estimated surface pH: **6.2**, with modelled 5th–95th percentile interval **4.4–8.0**.
- Forest and soil point endpoints returned `Access-Control-Allow-Origin: *`.

The machine-readable live service report is in `data/service-check.json`. Run `python src/check_services.py` to repeat it; provider availability can change.

The complete national build passed `python src/validate_output.py --all-spain`: **518,800 cells, 19 regions, 24 species and seven forecast dates (5–11 November 2026)**. Region IDs, cell counts, species arrays, environmental arrays, regional overview values and forecast dates align. The live national weather fetch completed for **2,748 locations**. Generated regional web data totals approximately **506 MB uncompressed**, loaded one region and species at a time.

Browser visual and interaction verification remains unavailable because a saved permission setting blocks local browser access. No alternative browser route was attempted. GitHub Actions and Pages are prepared but have not been run remotely or deployed; delivery remains local.
