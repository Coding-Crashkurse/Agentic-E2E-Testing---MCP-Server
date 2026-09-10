from __future__ import annotations

import ast
import io
import tokenize
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "e2e_verifier"


def python_files() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


def test_source_tree_is_not_empty() -> None:
    assert len(python_files()) > 20


def test_no_hash_comments_in_source() -> None:
    offenders: list[str] = []
    for path in python_files():
        text = path.read_text(encoding="utf-8")
        offenders.extend(
            f"{path.relative_to(SRC)}:{token.start[0]}: {token.string}"
            for token in tokenize.generate_tokens(io.StringIO(text).readline)
            if token.type == tokenize.COMMENT
        )
    assert offenders == []


def test_no_docstrings_in_source() -> None:
    offenders: list[str] = []
    for path in python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        nodes = [tree, *ast.walk(tree)]
        for node in nodes:
            if (
                isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
                and ast.get_docstring(node, clean=False) is not None
            ):
                name = getattr(node, "name", "<module>")
                offenders.append(f"{path.relative_to(SRC)}: {name}")
    assert offenders == []


def test_no_comments_in_javascript_assets() -> None:
    offenders: list[str] = []
    for path in sorted((SRC / "assets").glob("*.js")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith(("//", "/*")):
                offenders.append(f"{path.name}:{number}")
    assert offenders == []
