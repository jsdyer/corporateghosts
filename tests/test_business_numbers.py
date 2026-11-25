import csv
import gzip
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build import COLS, collect_business_numbers, import_rows, pack_business_numbers


class BusinessNumberTests(unittest.TestCase):
    def records(self):
        # Synthetic fixture; no visitor queries or personal information.
        return [dict.fromkeys(COLS, "") | {
            "Corporation number": str(10000 + i),
            "Business number (BN)": str(100000000 + i),
            "Corporate name - form 1": f"Example corporation {i}",
            "Status": "Active",
            "Street": "Excluded source address",
        } for i in range(1000)]

    def load(self, rows, columns=None):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "active.csv"
            with path.open("w", encoding="utf-8-sig", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=columns or (*COLS, "Street"), extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
            return import_rows(path)

    def test_published_number_is_searchable_without_retaining_street(self):
        rows, _ = self.load(self.records())
        self.assertEqual(rows[0][5][5], "100000000")
        self.assertIn("100000000", rows[0][7].split())
        self.assertNotIn("Excluded source address", json.dumps(rows))
        self.assertEqual(len(rows[0]), 8)

    def test_blank_number_does_not_invent_an_identifier(self):
        raw = self.records()
        raw[0]["Business number (BN)"] = ""
        rows, _ = self.load(raw)
        index = {}
        self.assertEqual(collect_business_numbers(index, rows), 1)
        self.assertEqual(rows[0][5][5], "")
        self.assertEqual(len(index), 999)
        self.assertNotIn("", index)

    def test_nonempty_malformed_numbers_fail_instead_of_guessing(self):
        for number in ("00", "1234", "123456789RC0001", "123 456 789", "12345678A", "123456789.0"):
            with self.subTest(number=number):
                raw = self.records()
                raw[0]["Business number (BN)"] = number
                with self.assertRaisesRegex(ValueError, "Invalid published business number"):
                    self.load(raw)

    def test_official_zero_sentinel_is_unavailable_not_zero_padded(self):
        raw = self.records()
        raw[0]["Business number (BN)"] = "0"
        rows, _ = self.load(raw)
        self.assertEqual(rows[0][5][5], "")
        index = {}
        self.assertEqual(collect_business_numbers(index, rows), 1)
        self.assertNotIn("0", index)
        self.assertNotIn("000000000", index)

    def test_schema_requires_business_number_column(self):
        with self.assertRaisesRegex(ValueError, "Unexpected federal corporations CSV schema"):
            self.load(self.records(), [c for c in COLS if c != "Business number (BN)"])

    def test_repeated_corporation_with_conflicting_number_fails(self):
        raw = self.records()
        raw.append(raw[0] | {"Business number (BN)": "999999999"})
        with self.assertRaisesRegex(ValueError, "Conflicting business numbers"):
            self.load(raw)

    def test_exact_mapping_deduplicates_and_retains_ambiguity(self):
        raw = self.records()
        raw[1]["Business number (BN)"] = raw[0]["Business number (BN)"]
        rows, _ = self.load(raw)
        index = {}
        collect_business_numbers(index, rows)
        collect_business_numbers(index, rows)
        self.assertEqual(index["100000000"], ["10000", "10001"])
        self.assertNotIn("100000001", index)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "data").mkdir()
            manifest = pack_business_numbers(root, index, 3)
            self.assertEqual(manifest["count"], 999)
            self.assertEqual(manifest["missing_count"], 3)
            self.assertEqual(manifest["ambiguous_count"], 1)
            self.assertEqual(manifest["prefix_length"], 3)
            self.assertEqual(list(manifest["shards"]), ["100"])
            file = manifest["shards"]["100"]
            data = json.loads(gzip.decompress((root / "data" / file).read_bytes()))
            self.assertEqual(data["100000000"], ["10000", "10001"])
            self.assertEqual(data["100000999"], ["10999"])
            changed = pack_business_numbers(root, index | {"100001000": ["11000"]}, 3)
            self.assertNotEqual(changed["shards"]["100"], file)


if __name__ == "__main__":
    unittest.main()
