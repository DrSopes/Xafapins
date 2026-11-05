# Verification of this update

Checked locally on 5 November 2026:

- Syntax checks passed for both JavaScript application files.
- All 7 JavaScript tests passed, including regional switching, stale-response protection, forest/soil/weather overlays and environmental data parsing.
- OpenStreetMap is the fixed basemap with contributor attribution.
- Forest display uses the official ff_tipo_bosque classification: conifers, broadleaf and mixed forest. Detailed point queries remain available.
- Saved-place controls, storage access, markers and GPX export were removed.
- The app footer credits Dr.Sopes.

Tests use stubbed map and DOM adapters. No real-browser visual check or live provider check was performed for this update. Python was unavailable in the local shell, so Python tests and the national forecast build were not rerun. Existing GitHub workflows retain those checks and generate forecast data before deployment. GitHub Actions and Pages have not been run remotely for this update.

The source ZIP includes .github and the required Spain boundary data. It excludes generated forecasts, historical snapshots and obsolete prediction files. See GITHUB_SETUP.md for deployment instructions.
