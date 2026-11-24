# Corporate Ghosts

A browser explorer for federal corporations, BC OrgBook registrations and Nova Scotia co-operatives. Search legal-name forms, corporation numbers, governing laws, locality and status descriptions. Use the four register subsets, reported status and anniversary-date sorting to investigate historical patterns. Inactive status alone does not indicate wrongdoing.

<!-- coolcode:guide -->
Open BC historical registrations and look for GLOBAL TELEGRAPH LIMITED (BC0401241). In Nova Scotia, ABC HOUSING CO-OPERATIVE LIMITED is registry ID 3057952. Take an NS ID to RJSC Connect for the official file.
<!-- /coolcode:guide -->

The [provincial search](https://coolcode.ca/corporateghosts/provinces.html) calls the documented [OrgBook BC v4 API](https://bcgov.github.io/orgbook-bc-api-docs/api/) on submission, with separate current and historical queries and upstream pagination. Each BC result opens the official organization profile. The Nova Scotia search runs locally against [the province's co-operative register](https://data.novascotia.ca/d/k29k-n2db), retaining name, ID, town, incorporation date, organization type and profit classification. The June 8, 2026 edition has 369 records. Refresh the bundled edition with `python3 scripts/ns_coops.py`. Contains information licensed under the [Open Government Licence – Nova Scotia](https://novascotia.ca/opendata/licence.asp).

For other NS entity types, open [RJSC Connect](https://rjsc.novascotia.ca/). For Alberta, British Columbia, Manitoba, Nova Scotia, Ontario, Québec and Saskatchewan, use [Canada’s Business Registries](https://ised-isde.canada.ca/cbr-rec/en/) directly. Its service restricts automated search and copying. Federal results remain a distinct index.

The published [Federal Corporations dataset](https://open.canada.ca/data/en/dataset/0032ce54-c5dd-4b66-99a0-320a7b5e99f2) supplies four typically daily CSVs in each official language. This build uses the four English CSVs and keeps both legal name forms where published. It omits street addresses, business numbers and director information. This is federal coverage, so provincial, territorial and financial-sector incorporations may be absent. The CSV does not provide a complete history of legal names. Follow the record's link to Corporations Canada and search its corporation number for the current official profile.

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

This is an interim mitigation, not a scheduling guarantee: GitHub does not document active-workflow renewal as a permanent exemption, and scheduled runs can be delayed or dropped. A scheduler on our own Linux server is the planned independent trigger. The guard does not collect data, create dummy commits, or change source/check timestamps; successful collection and published data freshness still need monitoring.
<!-- /schedule-reliability -->
