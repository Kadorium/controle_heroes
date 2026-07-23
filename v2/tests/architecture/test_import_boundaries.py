"""Architectural import boundary tests (Blueprint §13.5 / ADR-14)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.foundation.module_graph import (
    ALLOWED_DEPS,
    FOUNDATION_ALLOWED_FILENAMES,
    INTERNAL_SUFFIXES,
    MODULE_PACKAGES,
)

V2_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = V2_ROOT / "app"
REPO_ROOT = V2_ROOT.parent


def _iter_py_files(root: Path):
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def _module_of(path: Path) -> str | None:
    try:
        rel = path.relative_to(APP_ROOT)
    except ValueError:
        return None
    if not rel.parts:
        return None
    top = rel.parts[0]
    if top in MODULE_PACKAGES:
        return top
    if top == "foundation":
        return "foundation"
    return None


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module)
    return names


def test_no_v2_imports_v1():
    violations = []
    for path in _iter_py_files(V2_ROOT):
        for name in _imports(path):
            if name == "v1" or name.startswith("v1.") or "/v1/" in name.replace("\\", "/"):
                violations.append(f"{path}:{name}")
            # also catch relative escapes attempting repo v1 package
            if name.startswith("..") and "v1" in name:
                violations.append(f"{path}:{name}")
    assert not violations, "V2 must not import V1:\n" + "\n".join(violations)


def test_module_deps_respect_graph():
    violations = []
    for path in _iter_py_files(APP_ROOT):
        importer = _module_of(path)
        if importer not in MODULE_PACKAGES:
            continue
        allowed = ALLOWED_DEPS.get(importer, frozenset())
        for name in _imports(path):
            if not name.startswith("app."):
                continue
            parts = name.split(".")
            if len(parts) < 2:
                continue
            callee = parts[1]
            if callee == importer:
                # same package — check internals from outside later
                continue
            if callee == "foundation":
                # ORM Base compartilhado é exceção (*models.py → database);
                # routes.py pode orquestrar UoW/deps/errors (HTTP composition).
                if name == "app.foundation.database" and path.name.endswith("models.py"):
                    continue
                if path.name in FOUNDATION_ALLOWED_FILENAMES:
                    continue
                violations.append(f"{path}: {importer} -> foundation (forbidden)")
                continue
            if callee in MODULE_PACKAGES and callee not in allowed:
                violations.append(f"{path}: {importer} -> {callee} not in ALLOWED_DEPS")
            # routes may import audit.public even if not in ALLOWED_DEPS domain graph
            # — handled: add audit to allowed for routes only via special case below
    assert not violations, "\n".join(violations)


def test_no_cross_module_internals():
    violations = []
    for path in _iter_py_files(APP_ROOT):
        importer = _module_of(path)
        # Foundation is composition root and may wire internals; domain packages may not.
        if importer is None or importer == "foundation":
            continue
        for name in _imports(path):
            if not name.startswith("app."):
                continue
            parts = name.split(".")
            if len(parts) < 3:
                continue
            callee_mod = parts[1]
            if callee_mod == importer or callee_mod not in MODULE_PACKAGES:
                continue
            # importing app.other.models etc.
            suffix = "." + ".".join(parts[2:])
            for internal in INTERNAL_SUFFIXES:
                if suffix == internal or suffix.startswith(internal + "."):
                    # only public/api allowed across modules
                    if parts[2] not in ("public", "api"):
                        violations.append(f"{path}: imports internal {name}")
    assert not violations, "\n".join(violations)


def test_no_cycles_in_allowed_graph():
    # DFS cycle detection on ALLOWED_DEPS
    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node: str) -> None:
        if node in visited:
            return
        assert node not in visiting, f"cycle at {node}"
        visiting.add(node)
        for nxt in ALLOWED_DEPS.get(node, frozenset()):
            dfs(nxt)
        visiting.remove(node)
        visited.add(node)

    for n in ALLOWED_DEPS:
        dfs(n)
