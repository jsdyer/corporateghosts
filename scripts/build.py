#!/usr/bin/env python3
"""Build a browser search index from the four official federal corporation CSVs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from pathlib import Path
import re
import tempfile

from packing import clean, day, digest, download, finish, normalize, output_path, pack, prepare

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = "https://d4bf66bykfyaf.cloudfront.net/corporations-"
GROUPS = (
    ("inactive-or-dissolved-cbca", "Inactive business corporations"),
    ("inactive-or-dissolved-non-cbca", "Other inactive corporations"),
    ("active-cbca", "Active business corporations"),
    ("active-non-cbca", "Other active corporations"),
)
COLS = (
    "Corporation number", "Corporate name - form 1", "Corporate name - form 2",
    "Governing legislation", "Status", "Status Detail", "Anniversary date", "Year of last annual filing",
    "Date of last annual meeting", "City/town", "Province/territory", "Country",
)


def import_rows(path):
    rows = []
    types = set()
    seen = set()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or set(COLS).difference(reader.fieldnames):
            raise ValueError(f"Unexpected federal corporations CSV schema: {path.name}")
        for raw in reader:
            if None in raw or any(raw.get(field) is None for field in COLS):
                raise ValueError(f"Incomplete record in {path.name} at line {reader.line_num}.")
            ref, name, alt, law, status, reason, date, filing, meeting, city, province, country = (
                clean(raw[field]) for field in COLS
            )
            if not re.fullmatch(r"[0-9]{1,12}", ref) or not (name or alt):
                continue
            if ref in seen:
                continue
            seen.add(ref)
            if not name:
                name, alt = alt, ""
            status = status or "Status unavailable"
            types.add(status)
            location = ", ".join(part for part in (city, province, country if country not in ("CA", "Canada") else "") if part)
            date = day(date)
            details = [alt if alt != name else "", law, reason if reason != status else "", filing, day(meeting)]
            lookup = normalize(name, alt, ref, law, status, reason, date, location)
            rows.append([name, location, ref, status, date, details, None, lookup])
    if len(rows) < 1000:
        raise ValueError(f"{path.name} appears incomplete ({len(rows):,} corporations).")
    return rows, types


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, help="Use saved official CSV files, e.g. active-cbca.csv.")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    try:
        output = output_path(args.output, ROOT)
        if args.inputs and args.inputs.resolve().is_relative_to(output):
            raise ValueError("Keep input CSV files outside the output directory.")
        with tempfile.TemporaryDirectory(prefix="federal-corporations-", dir=output.parent) as work:
            root = Path(work)
            staging = root / "site"
            prepare(ROOT, staging)
            sources = []
            packed = []
            combined_types = set()
            with ThreadPoolExecutor(max_workers=4) as pool:
                jobs = {
                    group: pool.submit(download, f"{PUBLISHER}{group}-en.csv", root / f"{group}.csv", args.inputs)
                    for group, label in GROUPS
                }
                for group, label in GROUPS:
                    source, updated = jobs[group].result()
                    rows, types = import_rows(source)
                    packed.append(pack(staging, group, label, rows))
                    combined_types.update(types)
                    sources.append({"label": label, "url": f"{PUBLISHER}{group}-en.csv", "updated": updated,
                                    "sha256": digest(source)})
                    print(f"{label}: {len(rows):,}", flush=True)
                    del rows
            finish(output, staging, packed, combined_types, sources)
    except (RuntimeError, OSError, ValueError, csv.Error) as error:
        parser.exit(1, f"Build failed: {error}\n")


if __name__ == "__main__":
    main()
