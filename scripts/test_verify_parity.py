import csv
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("verify_parity", Path(__file__).with_name("verify-parity.py"))
PARITY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PARITY)


class ParityVerificationTests(unittest.TestCase):
    def setUp(self):
        temporary_root = PARITY.ROOT / '.local'
        temporary_root.mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix='parity-test-', dir=temporary_root)
        self.assertTrue(Path(temporary.name).resolve().is_relative_to(temporary_root.resolve()))
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "docs").mkdir()
        (self.root / "evidence.py").write_text("", encoding="utf-8")
        self.markdown = self.root / "docs/ODOO-PARITY-MATRIX.md"
        self.csv = self.root / "docs/ODOO-PARITY-MATRIX.csv"
        self.markdown.write_text(
            '**Selected checklist totals:** 1 rows: 1 Implemented, 0 Partial, 0 Missing, 0 Defect.\n'
            '## Platform and access\n'
            '| PL-01 | A "quoted", capability | Implemented | [T1] | Bounded workflow. | P1 | S0 |\n'
            '- [T1]: [Tests](../evidence.py#L1).\n'
            '- S0: [Official docs](https://www.odoo.com/documentation/19.0/).\n',
            encoding="utf-8",
        )
        self.record = dict(zip(PARITY.COLUMNS, (
            "PL-01", "Platform and access", 'A "quoted", capability', "Implemented",
            "[T1]", "Bounded workflow.", "P1", "S0",
        )))
        self.write_csv([self.record])

    def write_csv(self, rows):
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=PARITY.COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
        self.csv.write_text(output.getvalue(), encoding="utf-8")

    def change_markdown(self, old, new):
        self.markdown.write_text(self.markdown.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")

    def test_matching_records_with_csv_quotes_pass(self):
        self.assertEqual(PARITY.verify(self.root)["counts"]["Implemented"], 1)

    def test_changed_acceptance_text_is_rejected(self):
        self.write_csv([{**self.record, "Current boundary / next acceptance condition": "Unverified claim."}])
        with self.assertRaisesRegex(ValueError, "CSV/Markdown mismatch"):
            PARITY.verify(self.root)

    def test_duplicate_ids_are_rejected(self):
        self.write_csv([self.record, self.record])
        with self.assertRaisesRegex(ValueError, "Duplicate CSV ID"):
            PARITY.verify(self.root)

    def test_stale_counts_are_rejected(self):
        self.change_markdown("1 rows", "74 rows")
        with self.assertRaisesRegex(ValueError, "totals"):
            PARITY.verify(self.root)

    def test_missing_evidence_file_is_rejected(self):
        (self.root / "evidence.py").unlink()
        with self.assertRaisesRegex(ValueError, "evidence file"):
            PARITY.verify(self.root)

    def test_implemented_claim_without_test_evidence_is_rejected(self):
        self.change_markdown("[T1]", "[B1]")
        self.write_csv([{**self.record, "Repository evidence": "[B1]"}])
        with self.assertRaisesRegex(ValueError, "automated-test evidence"):
            PARITY.verify(self.root)

    def test_undefined_evidence_and_reference_are_rejected(self):
        self.change_markdown("- [T1]:", "- [T2]:")
        self.change_markdown("- S0:", "- S1:")
        with self.assertRaisesRegex(ValueError, "Undefined evidence T1"):
            PARITY.verify(self.root)
        self.change_markdown("- [T2]:", "- [T1]:")
        with self.assertRaisesRegex(ValueError, "Undefined Odoo reference S0"):
            PARITY.verify(self.root)


if __name__ == "__main__":
    unittest.main()
