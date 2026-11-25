# Corporate Ghosts

A browser explorer for federal corporations, BC OrgBook registrations and Nova Scotia co-operatives. Retrieve current federal status, directors, filing history and published significant-control person statements by corporation number, then save dated captures to compare later. Search legal-name forms, corporation numbers, governing laws, locality and status descriptions. Use the four register subsets, reported status and anniversary-date sorting to investigate historical patterns. Inactive status alone does not indicate wrongdoing.

<!-- coolcode:guide -->
Search the dated name index, open a result and choose Get current federal API record. Compare status details, annual returns, directors and dated filings; save a capture on this device to compare it with a later lookup. Legal registration does not verify a website’s ownership or honesty. BC historical search includes GLOBAL TELEGRAPH LIMITED (BC0401241); the Nova Scotia co-operative list includes ABC HOUSING CO-OPERATIVE LIMITED, registry ID 3057952.
<!-- /coolcode:guide -->

The [provincial search](https://coolcode.ca/corporateghosts/provinces.html) calls the documented [OrgBook BC v4 API](https://bcgov.github.io/orgbook-bc-api-docs/api/) on submission, with separate current and historical queries and upstream pagination. Each BC result opens the official organization profile. The Nova Scotia search runs locally against [the province's co-operative register](https://data.novascotia.ca/d/k29k-n2db), retaining name, ID, town, incorporation date, organization type and profit classification. The June 8, 2026 edition has 369 records. Refresh the bundled edition with `python3 scripts/ns_coops.py`. Contains information licensed under the [Open Government Licence – Nova Scotia](https://novascotia.ca/opendata/licence.asp).

For other NS entity types, open [RJSC Connect](https://rjsc.novascotia.ca/). For Alberta, British Columbia, Manitoba, Nova Scotia, Ontario, Québec and Saskatchewan, use [Canada’s Business Registries](https://ised-isde.canada.ca/cbr-rec/en/) directly. Its service restricts automated search and copying. Federal results remain a distinct index.

The published [Federal Corporations dataset](https://open.canada.ca/data/en/dataset/0032ce54-c5dd-4b66-99a0-320a7b5e99f2) supplies four typically daily CSVs in each official language. This build uses the four English CSVs and keeps both legal name forms where published. The name-search snapshot omits street addresses, business numbers and director information. The separate current-record API lookup adds directors’ names, annual-return compliance, filing events and significant-control person statements when available; residential addresses and birth dates are not forwarded. This is federal coverage, so provincial, territorial and financial-sector incorporations may be absent. The CSV does not provide a complete history of legal names. Follow the record's link to Corporations Canada and search its corporation number for the current official profile.

```sh
python3 scripts/build.py
python3 -m http.server --directory dist 8000
```

Open http://127.0.0.1:8000/. Python 3.11+ is used at build time. A recent browser with worker and gzip decompression support is needed to query the published shards.

Use `--inputs` with a folder of four locally downloaded CSVs (`active-cbca.csv`, `active-non-cbca.csv`, `inactive-or-dissolved-cbca.csv`, `inactive-or-dissolved-non-cbca.csv`) to reproduce a source snapshot. Source SHA-256 hashes, downloads, and update dates are in `dist/data/manifest.json`. The GitHub Pages workflow builds and refreshes the dataset daily, on relevant source changes, and on manual runs without committing raw CSV files. Searches across all four groups require more data than a single-subset search. A failed download or invalid schema stops publication, keeping the last successful site available.

Contains information licensed under the [Open Government Licence – Canada](https://open.canada.ca/en/open-government-licence-canada/). Source: Innovation, Science and Economic Development Canada.

<!-- schedule-reliability -->
## Schedule reliability

Public GitHub repositories can have scheduled workflows disabled after 60 days of inactivity. A separate weekly [schedule guard](.github/workflows/schedule-guard.yml) calls GitHub's enable-workflow API for an explicit list of refresh workflows and itself. It can restore workflows disabled for inactivity, preserves manually disabled workflows, and runs independently of collection failures.

This is an interim mitigation, not a scheduling guarantee: GitHub does not document active-workflow renewal as a permanent exemption, and scheduled runs can be delayed or dropped. The GitHub-managed CoolCode watchdog on our Linux server is the independent trigger; it reads the generated operations inventory. The guard does not collect data, create dummy commits, or change source/check timestamps; successful collection and published data freshness still need monitoring.
<!-- /schedule-reliability -->

## Current federal record and saved comparisons

The current [ISED Federal Corporation API](https://api.ised-isde.canada.ca/en/docs?api=corporation) is called by federal corporation number. Its API does not offer a name-search parameter, so the existing daily CSV index remains the name-search source. BC and Nova Scotia searches keep their existing, separate coverage. An absent federal match does not prove a business is fictitious: provincial, territorial and financial-sector registers are distinct. Active legal status does not establish that a business is currently trading or that a website belongs to it.

The gateway uses the current JSON endpoint `/cc/api/v1/corporations/{id}` with `include=directors`, `include=filings` and `include=isc`. Set **`ISED_CORPORATIONS_API_KEY`** in the shared CoolCode Cloudflare Worker to the API `user_key`; never put it in this public repo or browser config. The header is attached server-side. Existing `DB` supplies caching and request limits; no new binding is needed. The API retrieval timestamp is distinct from the CSV edition and index build timestamp. Detailed API fields may be up to 15 minutes old at the source, with an additional maximum five-minute gateway cache. Missing optional details are labeled not returned, not silently interpreted as empty or compliant.

Filing events show received and effective dates separately; the anniversary date is not automatically the incorporation date. Significant-control output consists of dated BODS person statements, retaining lifecycle status such as closed, rather than making a claim about current ownership. The public adapter returns names but omits personal addresses, birth dates and tax information. It bounds output to 500 filings, 500 control statements and 200 directors; truncated filing/statement results are labeled. Consult the official register for full evidence.

Save explicitly records the normalized federal record and original retrieval time under `coolcode:corporateghosts:captures` in device storage. Refreshing keeps it. Later lookups compare legal names, status/detail, legislation/type, locality, anniversary, directors, annual returns and person statements with the latest older saved capture of the same corporation. This is a comparison of returned fields, not proof that no other change occurred. Export a current capture or all saved captures as JSON; Clear removes local copies. No cookies, account, background monitoring or cloud-saved watchlist are used. Shared browsers share saved records. The corporation number is sent through CoolCode’s gateway to ISED on lookup; application logs contain no credentials or query values.

## Expand or customize

Edit `web/config.js` to change name-search examples, API gateway or `maxSavedCaptures` (default 30, hard cap 100). Example terms are starting points: arbitrary names and federal IDs remain searchable, and any valid federal corporation number can be requested without appearing in the snapshot. Existing captures retain their original retrieval date when settings change. Source group definitions and schema are in `scripts/build.py`; changing their coverage requires reviewing the collector validation and manifest. Keep the four official datasets complete rather than substituting a small list. Provincial sources remain in `web/provinces.mjs` and `scripts/ns_coops.py`.

After edits run `node --test tests/*.test.mjs`, `python3 -m unittest discover -s tests -v`, then `python3 scripts/build.py`. The last command refreshes all four official CSVs unless `--inputs` is supplied. It preserves the previous deployment on failure. Modules/styles/manifests/provincial data use one content version; federal shards have content hashes in filenames so a new manifest cannot load old cached records. Source changes and the daily schedule deploy through GitHub Pages. Update the hub guide, catalogue, operations inventory and watchdog freshness checks under its lifecycle procedure. The current-record API is on demand and adds no collector schedule.
