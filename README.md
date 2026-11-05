# Xafapins · Spain

App feta per **Dr.Sopes**.

A static mushroom-weather explorer with **24 species**, **all 19 Spanish regions**, **official forest formations**, and **modelled soil pH**. Includes mainland Spain, the Balearic Islands, the Canary Islands, Ceuta and Melilla. The interface remains in Catalan.

## Use the map

- The national overview colours regions by their average weather-suitability index. The selected region loads its approximately **1 km cells**. Click another region or choose it in the selector to load its detailed forecast. Regional averages are simple cell means, not occurrence probabilities.
- Select a species, forecast date and weather layer. The **Tot Espanya** and **Canàries** buttons navigate between national and island views.
- **Tipus de bosc** uses a simplified classification: conifers, broadleaf and mixed forest, through the official MITECO `ff_tipo_bosque` layer. The overlay can also be hidden. Detailed formation and tree information remains available by clicking the map.
- **pH del sòl** displays SoilGrids estimates for 0–5, 5–15 or 15–30 cm depth. Click the map to query the pH, an approximate acidity class and, where available, the model's 5th–95th percentile interval. These are **250 m model estimates, not local measurements**.
- Every land click queries the forest formation, dominant tree species and canopy cover where supplied by MITECO, plus soil pH. Empty/error responses remain unknown; they never become zero or neutral pH. Point queries can be retried by clicking again.
- Forest and pH overlays are mutually exclusive so their original provider legends remain readable. Selecting either hides weather colours; selecting a weather layer hides the environmental overlay. Point details can show both independently.
- Search Spanish place names or `latitude, longitude`. Click a region to load its forecast after navigating.

## Run locally

Requires Python 3.12+ and internet for map services and fresh weather. The large preview ZIP includes a generated snapshot. The **GitHub source ZIP contains code only**: run the commands below or deploy through Actions to generate data.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python src/download_meteo.py --grid-step 0.16 --forecast-days 7
python src/predict_engine.py --cell-km 1 --all-spain
python src/validate_output.py --all-spain
python -m http.server 8000 --bind 127.0.0.1 --directory web
```

Open http://localhost:8000. On Windows, `./preview.ps1` starts the existing local environment. Do not open index.html with file://. Node is only needed for JavaScript tests, not serving the map.

```sh
python -m unittest discover -s tests -v
node --check web/app.js
node --test tests/environment.test.cjs tests/app-state.test.cjs
# Optional live provider checks, requires network:
python src/check_services.py
```

## GitHub and GitHub Actions

The generated national preview is about 506 MB uncompressed. Commit the source, not `web/data` or the weather snapshots; `.gitignore` excludes those outputs. GitHub Actions builds them for the Pages artifact. The browser loads only the selected region and species rather than downloading the complete national dataset.

1. Upload the **contents of this folder** to your repository root, including `.github`.
2. Set Settings → Pages → Build and deployment → **GitHub Actions**.
3. Push to your repository's default branch or run **Build and deploy Xafapins** manually on that branch. The workflow detects its name automatically. See [GITHUB_SETUP.md](GITHUB_SETUP.md) for update instructions and troubleshooting.

Actions runs offline tests, downloads weather, generates every species for all 19 regions, validates all output, and deploys the `web` artifact. Daily schedule: **06:00 UTC**, or 07:00 Madrid in winter / 08:00 in summer. Schedules may be delayed or disabled by GitHub. Failed downloads/builds stop deployment and preserve the previously published version. Generated data is ignored by Git and regenerated in CI; no daily commits or repository-write permission are needed.

Open-Meteo's public service requires no key for eligible non-commercial usage. Check current rate limits and commercial terms before production. National downloads are substantially larger than Catalonia-only downloads. `--grid-step` controls sampling; denser sampling increases API usage and does not change native model resolution. Forest and pH layers are queried directly by visitors and can be temporarily unavailable independently of forecasts.

## Resolution and interpretation

| Layer | Resolution / interpretation |
| --- | --- |
| Forecast display | Nominal 1 km cells, clipped to each region; regional latitude controls longitude spacing. Boundaries are generalized GISCO 1:1M geometry, not parcel surveys. |
| National overview | Simple average of each region's cells for the selected species/date. Select a region for detailed cells. |
| Weather sampling | Default **0.16°**, approximately 12–16 km east–west and 18 km north–south. This is coarser than the previous Catalonia-only 0.08° sampling to keep national API usage manageable. Source models have their own variable native resolutions. Four-neighbour inverse-distance interpolation. |
| Forest formations | MITECO's Mapa Forestal de España / foto fija service, independently rendered at the source map scale; zoom does not create new survey detail. |
| Soil pH | ISRIC SoilGrids, 250 m modelled pH in water. Raw `pH×10` point values are divided by 10. Surface and subsurface depths are selectable. |
| Terrain elevation | Interpolated weather-query elevation; not a local terrain DEM. |
| Water balance | Rain minus reference evapotranspiration over 21 days; not measured soil moisture. |

The weather index is **uncalibrated**, not a probability of finding mushrooms. Each species uses a provisional rain window, mean-temperature response, frost penalty, season and elevation range. Species profiles need expert review and independent field calibration, especially outside their expected distribution. Nationwide coverage does not assert that every catalogue species occurs on every island or region.

**Forest and pH are real reference layers and point queries, but they do not yet modify the precomputed weather index.** This is stated in the UI. No fabricated ecological weighting is applied. Classification labels use simple display bins: pH <5.5 acidic, 5.5–<6.5 slightly acidic, 6.5–7.5 near-neutral, >7.5 alkaline.

Weather includes 28 historical days and 7 forecast days by default. Antecedent rain excludes the target day; later forecast dates include earlier predicted rain. Temperature and frost use the preceding 7 days; daily wind, humidity and rain use the selected day. All weather dates use **Europe/Madrid**, including Canary Island locations (not Canary local-midnight aggregation). Stale data is flagged after 48 hours. Missing distant weather coverage is rejected rather than extrapolated across Spain.

## Sources and attribution

- [MITECO official forest formations directory](https://www.miteco.gob.es/es/cartografia-y-sig/ide/directorio_datos_servicios/biodiversidad/wms-formaciones-arboladas.html), service `https://iepnb.gob.es/geoserver/foto_fija_mfe/wms`; © MITECO.
- [ISRIC SoilGrids documentation](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html), service `https://maps.isric.org/mapserv?map=/map/phh2o.map`; CC BY 4.0.
- [Open-Meteo Forecast API](https://open-meteo.com/en/docs); CC BY 4.0. Archived forecast/model output, not station observations.
- [OpenStreetMap](https://www.openstreetmap.org/copyright) is the only basemap; © OpenStreetMap contributors.
- [ICGC](https://www.icgc.cat/ca/Geoinformacio-i-mapes/Servei-de-Mapa-Base) land cover overlays remain available for Catalonia.
- [Eurostat GISCO NUTS 2024](https://gisco-services.ec.europa.eu/distribution/v2/nuts/), 19 Spanish NUTS-2 boundaries at 1:1M; © EuroGeographics for administrative boundaries. Checked-in `data/spain-regions.geojson` is the Spanish subset.
- [Sporas.io](https://sporas.io/) supplied the original feature reference; no proprietary algorithm or assets copied.

No account, cross-device synchronization, station-rainfall integration, access/fire restrictions, or cloud alerts are implemented. The map does not identify mushrooms or certify edibility.
