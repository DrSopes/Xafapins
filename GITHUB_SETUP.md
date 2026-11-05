# Update your GitHub repository

## 1. Extract and commit the code

Extract `Xafapins-GitHub-source.zip` into your repository root, replacing matching files. There is **no enclosing folder** in this ZIP. The resulting root must contain:

```text
.github/workflows/ci.yml
.github/workflows/xafapins_daily.yml
config/
data/spain-regions.geojson
src/
tests/
web/index.html
requirements.txt
```

Include the hidden `.github` directory. Do not upload the ZIP itself expecting GitHub to extract it. Using a local Git checkout or GitHub Desktop is the easiest way to preserve hidden folders. If using GitHub's web upload, verify both workflow files appear under `.github/workflows` after committing.

Commit the extracted source files to the repository's **default branch**. The workflow detects that branch automatically; it does not require the branch to be named `main`.

When updating an older Xafapins repository, replace its `xafapins_daily.yml` with this one. Disable any other obsolete deployment workflows that target the same Pages site. Old tracked `web/prediction_*.geojson` files can be removed: the new viewer does not use them. They are excluded from the new deployment artifact even if they remain in the repository.

The ZIP intentionally excludes weather snapshots, generated map data, `.venv`, and build output. **Actions generates the full Spain forecast itself.** The checked-in Spain boundary file is required and included. If generating locally, follow README.md before opening the viewer.

## 2. Enable GitHub Pages once

In the repository:

1. Open **Settings → Pages**.
2. Under **Build and deployment → Source**, choose **GitHub Actions**.
3. Ensure repository Actions policy allows the official `actions/*` actions used by the workflow. Organization policies may require an administrator to enable these.

No personal access token or manually created secret is required. The workflow uses GitHub's built-in token with repository read access and Pages/OIDC permissions for deployment. GitHub Pages availability depends on your repository visibility and account plan.

Official reference: [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## 3. Run the deployment

Open **Actions → Build and deploy Xafapins → Run workflow**, selecting the default branch. Pushes to that branch also start deployment. A manual run from another branch is intentionally skipped.

The workflow:

1. Checks Pages configuration early.
2. Installs Python dependencies and runs Python/JavaScript tests.
3. Downloads weather covering all Spanish regions, islands and autonomous cities.
4. Builds 24 species and seven forecast dates at approximately 1 km display spacing.
5. Validates all 19 regional datasets and prepares a clean `dist` folder.
6. Uploads the Pages artifact and deploys it. The final deployment step supplies your website URL.

The first build takes several minutes and depends on public weather API availability. The daily refresh runs at **06:00 UTC**, which is 07:00 Madrid in winter and 08:00 in summer. GitHub may delay scheduled jobs; the website shows the actual data timestamp.

## If a run fails

- **Configure Pages / 404 / resource not accessible:** check Settings → Pages → GitHub Actions, repository plan eligibility and organization policy. Do not add a broad token as a workaround.
- **Weather API 429 or timeout:** public-service quota/rate limits or availability may be responsible. Wait for the provider limit to reset, then rerun. Repeated immediate runs consume more quota. This configuration uses Open-Meteo's eligible non-commercial public service; commercial usage requires an appropriate provider arrangement.
- **Deploy environment protection:** approve the `github-pages` deployment if your repository has deliberately configured an approval rule, or review its allowed-branch settings.
- **Missing forecast data after copying source locally:** the ZIP contains code, not generated forecasts. Run the README pipeline locally, or use the successfully deployed Pages URL.

A failed refresh does not deploy partial data; the previous Pages deployment remains available. Forest and pH maps are independent live services and may temporarily fail even when a forecast deployment succeeds.

The workflows have been prepared and checked locally. An actual GitHub-hosted run cannot be verified until this source is committed to your repository and Pages is enabled.
