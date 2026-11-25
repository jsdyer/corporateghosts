#!/usr/bin/env python3
"""Build a browser search index from the four official federal corporation CSVs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import gzip
import hashlib
import json
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
    "Business number (BN)",
)


def import_rows(path):
    rows = []
    types = set()
    seen = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or set(COLS).difference(reader.fieldnames):
            raise ValueError(f"Unexpected federal corporations CSV schema: {path.name}")
        for raw in reader:
            if None in raw or any(raw.get(field) is None for field in COLS):
                raise ValueError(f"Incomplete record in {path.name} at line {reader.line_num}.")
            ref, name, alt, law, status, reason, date, filing, meeting, city, province, country, business_number = (
                clean(raw[field]) for field in COLS
            )
            # The official 2026-11-24 non-CBCA export uses a literal zero for
            # an unavailable BN. It is not a business number and must not be
            # padded, guessed, searched or sent to the current-record API.
            if business_number == "0":
                business_number = ""
            if business_number and not re.fullmatch(r"[0-9]{9}", business_number):
                raise ValueError(f"Invalid published business number in {path.name} at line {reader.line_num}.")
            if not re.fullmatch(r"[0-9]{1,12}", ref) or not (name or alt):
                continue
            if ref in seen:
                if seen[ref] != business_number:
                    raise ValueError(f"Conflicting business numbers for a repeated corporation in {path.name}.")
                continue
            seen[ref] = business_number
            if not name:
                name, alt = alt, ""
            status = status or "Status unavailable"
            types.add(status)
            location = ", ".join(part for part in (city, province, country if country not in ("CA", "Canada") else "") if part)
            date = day(date)
            details = [alt if alt != name else "", law, reason if reason != status else "", filing, day(meeting), business_number]
            lookup = normalize(name, alt, ref, business_number, law, status, reason, date, location)
            rows.append([name, location, ref, status, date, details, None, lookup])
    if len(rows) < 1000:
        raise ValueError(f"{path.name} appears incomplete ({len(rows):,} corporations).")
    return rows, types


def collect_business_numbers(index, rows):
    """Retain every published BN-to-corporation match, including ambiguity."""
    missing = 0
    for row in rows:
        number = row[5][5]
        if not number:
            missing += 1
            continue
        matches = index.setdefault(number, [])
        if row[2] not in matches:
            matches.append(row[2])
    return missing


def pack_business_numbers(staging, index, missing_count):
    """An exact BN lookup downloads only its content-addressed three-digit shard."""
    buckets = {}
    for number, references in sorted(index.items()):
        buckets.setdefault(number[:3], {})[number] = sorted(references)
    shards = {}
    for prefix, records in buckets.items():
        payload = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        version = hashlib.sha256(payload).hexdigest()[:16]
        name = f"business-numbers-{prefix}-{version}.json.gz"
        (staging / "data" / name).write_bytes(gzip.compress(payload, compresslevel=5, mtime=0))
        shards[prefix] = name
    return {
        "version": 1, "prefix_length": 3, "count": len(index),
        "missing_count": missing_count,
        "ambiguous_count": sum(len(matches) > 1 for matches in index.values()),
        "shards": shards,
    }


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
            business_numbers = {}
            missing_business_numbers = 0
            with ThreadPoolExecutor(max_workers=4) as pool:
                jobs = {
                    group: pool.submit(download, f"{PUBLISHER}{group}-en.csv", root / f"{group}.csv", args.inputs)
                    for group, label in GROUPS
                }
                for group, label in GROUPS:
                    source, updated = jobs[group].result()
                    rows, types = import_rows(source)
                    missing_business_numbers += collect_business_numbers(business_numbers, rows)
                    packed.append(pack(staging, group, label, rows))
                    combined_types.update(types)
                    sources.append({"label": label, "url": f"{PUBLISHER}{group}-en.csv", "updated": updated,
                                    "sha256": digest(source)})
                    print(f"{label}: {len(rows):,}", flush=True)
                    del rows
            number_index = pack_business_numbers(staging, business_numbers, missing_business_numbers)
            finish(output, staging, packed, combined_types, sources, {"business_numbers": number_index})
    except (RuntimeError, OSError, ValueError, csv.Error) as error:
        parser.exit(1, f"Build failed: {error}\n")


if __name__ == "__main__":
    main()
