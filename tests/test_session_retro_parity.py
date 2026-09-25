"""session-retro en/ko parity: the two variants may differ in text, never in code.

The plugin installs each skill folder on its own, so both variants carry their own ledger.py and
tests — two copies of one piece of logic, and nothing else notices when only one is edited.

Text is every string constant, blanked before comparing. In ledger.py an f-string is also reduced
to its formatted values, sorted, because a translation may reorder them. A value's format spec
(`:.2g`) and conversion (`!r`) are code and are compared as written.
Not caught: a string that acts as code (a dict key, a stored token) changed on one side only, and
two values swapped inside one f-string.
"""
import ast
from pathlib import Path

import pytest

SKILLS = Path(__file__).resolve().parents[1] / "skills"
EN, KO = SKILLS / "session-retro", SKILLS / "session-retro-ko"


class Blank(ast.NodeTransformer):
    """Blank every string constant, except inside a format spec."""

    def visit_Constant(self, node):
        return ast.Constant("") if isinstance(node.value, str) else node

    def visit_FormattedValue(self, node):
        node.value = self.visit(node.value)
        return node


class BlankUnordered(Blank):
    """Also reduce each f-string to its formatted values, sorted."""

    def visit_JoinedStr(self, node):
        values = [self.visit(v) for v in node.values if isinstance(v, ast.FormattedValue)]
        return ast.JoinedStr(sorted(values, key=ast.dump))


def first_divergence(a, b):
    """Lines (en, ko) of the innermost statement whose normalized code differs."""
    for field in a._fields:
        xs, ys = getattr(a, field), getattr(b, field, None)
        if isinstance(xs, list) and isinstance(ys, list):
            for x, y in zip(xs, ys):
                if isinstance(x, ast.stmt) and ast.dump(x) != ast.dump(y):
                    return first_divergence(x, y)
    return getattr(a, "lineno", None), getattr(b, "lineno", None)


def assert_same_code(rel, normalizer):
    en_src, ko_src = ((d / rel).read_text(encoding="utf-8") for d in (EN, KO))
    assert en_src != ko_src, f"{rel}: both variants have identical text, so the Korean one is not translated"
    en, ko = (normalizer().visit(ast.parse(s)) for s in (en_src, ko_src))
    if ast.dump(en) != ast.dump(ko):
        en_line, ko_line = first_divergence(en, ko)
        pytest.fail(f"{rel}: code differs between variants at en line {en_line}, ko line {ko_line}")


def test_ledger_py_differs_only_in_text():
    assert_same_code("ledger.py", BlankUnordered)


def test_ledger_tests_differ_only_in_text():
    assert_same_code("tests/test_ledger.py", Blank)


@pytest.mark.parametrize("en, ko, same", [
    ('x = "worked"', 'x = "works"', True),
    ('f"a {x} b {y}"', 'f"{y} c {x}"', True),
    ("x = 1", "x = 2", False),
    ("x < y", "x <= y", False),
    ('f"{x:.2g}"', 'f"{x:.3g}"', False),
    ('f"{x!r}"', 'f"{x}"', False),
])
def test_normalizer_blanks_text_and_keeps_code(en, ko, same):
    a, b = (ast.dump(BlankUnordered().visit(ast.parse(s))) for s in (en, ko))
    assert (a == b) is same
