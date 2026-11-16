# Corporate Ghosts

A browser-only explorer for Canada's federal corporate register. Search legal-name forms, corporation numbers, governing laws, locality and status descriptions. Use the four register subsets, reported status and anniversary-date sorting to investigate historical patterns. Inactive status alone does not indicate wrongdoing.

The published [Federal Corporations dataset](https://open.canada.ca/data/en/dataset/0032ce54-c5dd-4b66-99a0-320a7b5e99f2) supplies four typically daily CSVs in each official language. This build uses the four English CSVs and keeps both legal name forms where published. It omits street addresses, business numbers and director information. This is federal coverage, so provincial, territorial and financial-sector incorporations may be absent. The CSV does not provide a complete history of legal names. Follow the record's link to Corporations Canada and search its corporation number for the current official profile.

```sh
python3 scripts/build.py
python3 -m http.server --directory dist 8000
```

Open http://127.0.0.1:8000/. Python 3.11+ is used at build time. A recent browser with worker and gzip decompression support is needed to query the published shards.

Use `--inputs` with a folder of four locally downloaded CSVs (`active-cbca.csv`, `active-non-cbca.csv`, `inactive-or-dissolved-cbca.csv`, `inactive-or-dissolved-non-cbca.csv`) to reproduce a source snapshot. Source SHA-256 hashes, downloads, and update dates are in `dist/data/manifest.json`. The GitHub Pages workflow builds and refreshes the dataset daily, on relevant source changes, and on manual runs without committing raw CSV files. Searches across all four groups require more data than a single-subset search. A failed download or invalid schema stops publication, keeping the last successful site available.

Contains information licensed under the [Open Government Licence – Canada](https://open.canada.ca/en/open-government-licence-canada/). Source: Innovation, Science and Economic Development Canada.
