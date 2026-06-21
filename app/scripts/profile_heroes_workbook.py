"""CLI: profiling da planilha legada Heroes (read-only, sem banco)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.services.heroes_workbook_paths import HEROES_WORKBOOK_FILENAME, resolve_heroes_workbook_path
from app.services.heroes_workbook_profiler import profile_workbook_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Profile Heroes workbook (read-only)")
    parser.add_argument(
        "workbook",
        nargs="?",
        default=None,
        help=f"Caminho do XLSX (default: procura {HEROES_WORKBOOK_FILENAME} na raiz ou data/raw)",
    )
    parser.add_argument("--json", action="store_true", help="Saída JSON compacta")
    args = parser.parse_args(argv)

    path = resolve_heroes_workbook_path(args.workbook)
    if path is None:
        print("ERRO: planilha não encontrada.", file=sys.stderr)
        return 1

    report = profile_workbook_file(path)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(f"Arquivo: {report.get('resolved_path')}")
    print(f"Checksum: {report['file_checksum'][:16]}…")
    print(f"Sheets: {report['sheet_count']} | DB writes: {report['database_writes']}")
    print()
    for sh in report["sheets"]:
        div = " SIM" if sh.get("order_number_divergence") else " não"
        print(
            f"- {sh['sheet_name']}: {sh['sheet_type']} | conf={sh['parser_confidence']} | "
            f"ordem nome={sh.get('order_number_from_sheet_name')} conteudo={sh.get('order_number_from_content')} | "
            f"divergencia={div} | merges={sh.get('merged_cell_count')} | -> {sh['recommendation']}"
        )
        for w in sh.get("warnings") or []:
            print(f"    ⚠ {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
