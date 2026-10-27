# Smart Address, PIN Code & DIGIPIN Finder

Search the Local Government Directory village list, find source-listed PIN mappings, look up villages by PIN, and calculate DIGIPIN from a coordinate.

Repository: https://github.com/93477ngr/digipincodes

## Features
- Two-character minimum village autocomplete.
- Village record: LGD code, state, district and subdistrict.
- Six-digit PIN search lists village entries in the selected source feed.
- India Post reference encoder/decoder, user-triggered live location and map click.
- Clipboard copy with fallback.
- Prefix-sharded national data files.

## Accuracy matters
- An LGD village is an administrative entity. It is not necessarily every hamlet, ward, settlement, colony, or street.
- The application displays PIN values provided by the official LGD-with-PIN feed; missing values are not guessed.
- A PIN can cover multiple villages or offices; a village may have several PIN mappings or none in a given release.
- DIGIPIN is coordinate-based and distinct from postal PIN. The app does not infer a PIN from the nearest post office.
- Village coordinates are not fabricated.

## Data source
Official OGD resource: **Local Government Directory (LGD) - Villages with PIN Codes**
Resource ID: f17a1608-5f10-4610-bb50-a63c80d83974
API: https://api.data.gov.in/resource/f17a1608-5f10-4610-bb50-a63c80d83974
LGD: https://lgdirectory.gov.in/
India Post DIGIPIN reference: https://github.com/INDIAPOST-gov/digipin

## Generate nationwide data
1. Register at https://data.gov.in/ and obtain an API key.
2. Set it locally (never commit or expose the key):
   - PowerShell: $env:DATA_GOV_KEY="YOUR_KEY"
   - macOS/Linux: export DATA_GOV_KEY="YOUR_KEY"
3. Install Python 3.10+ and Requests: python -m pip install requests
4. Run: python scripts/build_directory.py
5. Review printed counts and inspect known villages and postal mappings before publishing.

The builder requests all configured LGD state codes with pagination and stops if an API response is incomplete. Check current API schema, quota and coverage before release. A successful download alone is not proof of accuracy.

## Run locally
Use Node.js 20+ and serve over HTTP (do not open the page with file://).
- npm install
- npm test
- Generate data as above.
- npm run serve
- Visit http://localhost:4173

## Deployment
Publish repository root on a static host after building data. For GitHub Pages, select main/root after generated data is available. Map tiles use OpenStreetMap online services and their terms.

## Refresh and smoke checks
Review record count deltas, schema changes and sample PIN links before publishing new data.
Test: Edurugatla; same-named villages in different districts; known PIN; unknown query; unmapped PIN; GPS allowed/denied; clipboard on HTTPS and fallback.
