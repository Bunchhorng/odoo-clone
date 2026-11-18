"""Check parity record consistency. This does not execute Odoo or certify parity."""

import csv
import io
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATUSES = ("Implemented", "Partial", "Missing", "Defect")
COLUMNS = (
    "ID", "Area", "Capability", "Status", "Repository evidence",
    "Current boundary / next acceptance condition", "Priority", "Odoo reference",
)


def verify(root=ROOT):
    root = Path(root).resolve()
    markdown_path = root / "docs/ODOO-PARITY-MATRIX.md"
    markdown = markdown_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(
        (root / "docs/ODOO-PARITY-MATRIX.csv").read_text(encoding="utf-8-sig")
    ))
    if tuple(reader.fieldnames or ()) != COLUMNS:
        raise ValueError("Parity CSV columns do not match the documented schema.")
    rows = list(reader)
    errors = []
    markdown_rows = {}
    area = ""
    for line in markdown.splitlines():
        if line.startswith("## "):
            area = line[3:].strip()
        if not re.match(r"\| [A-Z]{2}-\d{2} \|", line):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 7:
            errors.append(f"Malformed Markdown row: {line}")
            continue
        record = dict(zip(COLUMNS, (cells[0], area, *cells[1:])))
        if record["ID"] in markdown_rows:
            errors.append(f"Duplicate Markdown ID: {record['ID']}")
        markdown_rows[record["ID"]] = record

    evidence = dict(re.findall(r"^- \[([A-Z]\d+)\]: (.+)$", markdown, re.MULTILINE))
    references = set(re.findall(r"^- (S\d+):", markdown, re.MULTILINE))
    seen = set()
    counts = Counter()
    for row in rows:
        record_id = row.get("ID", "")
        if not re.fullmatch(r"[A-Z]{2}-\d{2}", record_id or ""):
            errors.append(f"Invalid CSV ID: {record_id!r}")
        if record_id in seen:
            errors.append(f"Duplicate CSV ID: {record_id}")
        seen.add(record_id)
        if row != markdown_rows.get(record_id):
            errors.append(f"CSV/Markdown mismatch: {record_id}")
        if row.get("Status") not in STATUSES:
            errors.append(f"Invalid status: {record_id}")
        counts[row.get("Status")] += 1
        if row.get("Priority") not in ("P1", "P2", "P3"):
            errors.append(f"Invalid priority: {record_id}")
        if any(not row.get(column) for column in COLUMNS):
            errors.append(f"Empty required cell: {record_id}")
        keys = re.findall(r"\[([A-Z]\d+)\]", row.get("Repository evidence") or "")
        if not keys:
            errors.append(f"Missing repository evidence: {record_id}")
        for key in keys:
            if key not in evidence:
                errors.append(f"Undefined evidence {key}: {record_id}")
        if row.get("Status") == "Implemented" and not any(key.startswith("T") for key in keys):
            errors.append(f"Implemented row lacks automated-test evidence: {record_id}")
        for key in re.split(r",\s*", row.get("Odoo reference") or ""):
            if key not in references:
                errors.append(f"Undefined Odoo reference {key}: {record_id}")

    if seen != set(markdown_rows):
        errors.append("CSV and Markdown have different capability ID sets.")
    declared = re.search(
        r"Selected checklist totals:\*\* (\d+) rows: (\d+) Implemented, "
        r"(\d+) Partial, (\d+) Missing, (\d+) Defect\.", markdown,
    )
    actual = (len(rows), *(counts[status] for status in STATUSES))
    if not declared or tuple(map(int, declared.groups())) != actual:
        errors.append("Declared checklist totals do not match the actual rows.")
    local_links = set()
    for target in re.findall(r"\]\(([^)]+)\)", markdown):
        if re.match(r"[a-z]+://", target) or target.startswith("#"):
            continue
        relative_path = target.split("#", 1)[0]
        resolved = (markdown_path.parent / relative_path).resolve()
        if not resolved.is_relative_to(root) or not resolved.is_file():
            errors.append(f"Missing or out-of-repository evidence file: {target}")
        local_links.add(relative_path)
    if errors:
        raise ValueError("\n".join(errors))
    return {
        "status": "passed", "capabilities": len(rows),
        "counts": {status: counts[status] for status in STATUSES},
        "evidenceFiles": len(local_links),
        "scope": "Checklist consistency and evidence-file presence; functional results are recorded in VERIFICATION.md.",
    }


if __name__ == "__main__":
    try:
        print(json.dumps(verify(), indent=2))
    except (ValueError, OSError) as error:
        raise SystemExit(str(error)) from error
