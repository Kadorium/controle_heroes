#!/usr/bin/env python3
"""Exporta goldens de caracterização a partir da V1 (processo separado).

Uso (CWD = v1/ ou PYTHONPATH=v1):
  python scripts/export_characterization_goldens.py --out-dir ../v2/tests/characterization/goldens
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Garante imports app.* quando executado de v1/
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.parse_it import parse_it_date, parse_it_number  # noqa: E402

SCHEMA_VERSION = 1

NUMBER_CASES = [
    "1.234,56",
    "10.000,00 €",
    "1,5",
    "1000",
    "1,234.56",
    "",
    None,
    "—",
    "(1.000,50)",
    "R$ 2.500,00",
]

DATE_CASES = [
    "15/03/2024",
    "2024-03-15",
    "01/02/24",
    "",
    None,
    "32/01/2024",
]


def _git_commit() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ROOT),
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _input_hash(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_number_golden() -> dict:
    cases = []
    for raw in NUMBER_CASES:
        parsed = parse_it_number(raw)
        cases.append(
            {
                "input": raw,
                "output": str(parsed) if parsed is not None else None,
            }
        )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "scenario": "parse_it_number",
        "v1_function": "app.core.parse_it.parse_it_number",
        "currency_context": "IT/EUR/BRL symbols stripped; Decimal string",
        "rounding": "none — Decimal exact from string",
        "origin": "v1 characterization export",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator_commit": _git_commit(),
        "cases": cases,
    }
    payload["input_hash"] = _input_hash({"cases": [{"input": c["input"]} for c in cases]})
    return payload


def build_date_golden() -> dict:
    cases = []
    for raw in DATE_CASES:
        iso, needs_review = parse_it_date(raw)
        cases.append(
            {
                "input": raw,
                "output": {"iso_date": iso, "needs_review": needs_review},
            }
        )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "scenario": "parse_it_date",
        "v1_function": "app.core.parse_it.parse_it_date",
        "currency_context": "n/a",
        "rounding": "n/a",
        "origin": "v1 characterization export",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator_commit": _git_commit(),
        "cases": cases,
    }
    payload["input_hash"] = _input_hash({"cases": [{"input": c["input"]} for c in cases]})
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Export V1 characterization goldens")
    parser.add_argument(
        "--out-dir",
        required=True,
        type=Path,
        help="Directory to write golden JSON files (required; no hardcoded v2 path)",
    )
    args = parser.parse_args()
    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    goldens = {
        "parse_it_number.v1.json": build_number_golden(),
        "parse_it_date.v1.json": build_date_golden(),
    }
    for name, body in goldens.items():
        path = out_dir / name
        path.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
