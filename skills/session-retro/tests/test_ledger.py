"""ledger.py invariants. Runs in a tmp sandbox via subprocess without touching the real ledger/rules (the exit code is part of the contract).

Probability boundaries are hand-computed against a background rule `gamma` (10 failures out of 30 sessions):
  isolate: window of k sessions with 0 failures, baseline p = 10/(30+k) → (1-p)^k : k=7 → 0.110 (misses), k=8 → 0.087 (hits)
  fix-or-drop: window of 3 sessions, baseline p = (10+f)/33 → f=3: 0.061 (hits), f=2: 0.30 (misses)
"""
import csv
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

LEDGER_PY = Path(__file__).resolve().parents[1] / "ledger.py"
OPTIONAL = ("SESSION_SEAL_DIR", "SESSION_RETRO_CORPUS", "SESSION_RETRO_PROJECTS")


@pytest.fixture
def sb(tmp_path):
    home = tmp_path / "home"
    (home / "rules").mkdir(parents=True)
    mem = home / "projects" / "p" / "memory"
    mem.mkdir(parents=True)
    (mem / "some-memo.md").write_text("m", encoding="utf-8")
    (home / "rules" / "alpha.md").write_text("# Keep the alpha rule — subtitle\n\nbody\n", encoding="utf-8")
    (home / "rules" / "beta.md").write_text("# Beta rule\n\n" + "a" * 1600 + "\n", encoding="utf-8")
    (home / "rules" / "gamma.md").write_text("# Gamma rule\n\nbackground\n", encoding="utf-8")
    seal = tmp_path / "seal"
    (seal / "Sessions").mkdir(parents=True)
    (tmp_path / "corpus").mkdir()
    (tmp_path / "state").mkdir()
    env = {k: v for k, v in os.environ.items() if k not in OPTIONAL}
    env.update({"RETRO_CLAUDE_HOME": str(home), "SESSION_RETRO_DIR": str(tmp_path / "state"),
                "SESSION_SEAL_DIR": str(seal / "Sessions"), "SESSION_RETRO_CORPUS": str(tmp_path / "corpus"),
                "SESSION_RETRO_PROJECTS": str(tmp_path / "projects"), "PYTHONIOENCODING": "utf-8"})
    return SimpleNamespace(home=home, seal=seal, env=env, tmp=tmp_path, ledger=tmp_path / "state" / "verdicts.csv", n=0)


def run(sb, *args):
    p = subprocess.run([sys.executable, str(LEDGER_PY), *args], env=sb.env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout, p.stderr


def add(sb, slug, rows, date="2026-10-01", append=False):
    f = sb.tmp / f"rows-{slug}-{sb.n}.json"
    f.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return run(sb, "add", "--slug", slug, "--date", date, "--project", "t", "--file", str(f),
               *(["--append"] if append else []))


def cards(sb, slug, date="2026-10-01"):
    return run(sb, "cards", "--slug", slug, "--date", date, "--project", "t")


def gate(sb, slug, rule, prop, dec):
    return run(sb, "gate", "--slug", slug, "--date", "2026-10-01", "--project", "t", "--rule", rule,
               "--proposal", prop, "--decision", dec, "--note", "test")


def sessions(sb, rule, verdicts):
    """Build one session per verdict for rule, stacking them up. Returns the last session's slug."""
    slug = None
    for v in verdicts:
        sb.n += 1
        slug = f"s{sb.n}"
        code, _, err = add(sb, slug, [{"rule": rule, "verdict": v, "note": f"event{sb.n}"}])
        assert code == 0, err
    return slug


def background(sb):
    sessions(sb, "gamma", ["did-not-work"] * 10 + ["worked"] * 20)


def rows_of(sb):
    if not sb.ledger.exists():
        return []
    with sb.ledger.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def row_for(out, rule):
    return [line for line in out.splitlines() if line.startswith("|") and f"`{rule}`" in line]


# ---------- add: input checks are all-or-nothing ----------

@pytest.mark.parametrize("bad", [
    {"rule": "alpha", "verdict": "**worked**", "note": "decorated label"},
    {"rule": "alpha", "verdict": "worked — but by luck", "note": "label with commentary"},
    {"rule": "alph", "verdict": "worked", "note": "misspelled name"},
    {"rule": "Alpha", "verdict": "worked", "note": "name differs only in case"},
    {"rule": "alpha", "verdict": "irrelevant", "note": "loaded but irrelevant"},
    {"rule": "alpha", "verdict": "worked", "note": "   "},
    {"rule": "memory:nope", "verdict": "worked", "note": "no such memory"},
    {"rule": "memory:*", "verdict": "worked", "note": "glob"},
])
def test_add_rejects_and_writes_nothing(sb, bad):
    code, _, err = add(sb, "x", [{"rule": "beta", "verdict": "worked", "note": "normal row"}, bad])
    assert code == 3, err
    assert rows_of(sb) == []


@pytest.mark.parametrize("text", ['[{"rule": "alpha", "verdict": "worked", "note": "x"},]', '["alpha"]', "[]"])
def test_bad_json_is_violation_not_tool_failure(sb, text):
    f = sb.tmp / "bad.json"
    f.write_text(text, encoding="utf-8")
    assert run(sb, "add", "--slug", "x", "--date", "2026-10-01", "--project", "t", "--file", str(f))[0] == 3


def test_bom_json_is_accepted(sb):
    f = sb.tmp / "bom.json"
    f.write_text('[{"rule": "alpha", "verdict": "worked", "note": "x"}]', encoding="utf-8-sig")
    assert run(sb, "add", "--slug", "x", "--date", "2026-10-01", "--project", "t", "--file", str(f))[0] == 0


@pytest.mark.parametrize("args", [["--slug", "a b"], ["--slug", "a|b"], ["--slug", "ok", "--date", "10/01/2026"]])
def test_bad_session_args_rejected(sb, args):
    f = sb.tmp / "r.json"
    f.write_text('[{"rule": "alpha", "verdict": "worked", "note": "x"}]', encoding="utf-8")
    base = {"--slug": "ok", "--date": "2026-10-01"}
    for i in range(0, len(args), 2):
        base[args[i]] = args[i + 1]
    flat = [x for kv in base.items() for x in kv]
    assert run(sb, "add", *flat, "--project", "t", "--file", str(f))[0] == 3


def test_session_key_reuse_needs_append(sb):
    assert add(sb, "same", [{"rule": "alpha", "verdict": "worked", "note": "morning"}])[0] == 0
    assert add(sb, "same", [{"rule": "alpha", "verdict": "worked", "note": "afternoon"}])[0] == 3
    assert add(sb, "same", [{"rule": "beta", "verdict": "worked", "note": "addendum"}], append=True)[0] == 0


def test_note_with_comma_and_newline_keeps_columns(sb):
    assert add(sb, "x", [{"rule": "alpha", "verdict": "worked", "note": "a, b\nc"},
                         {"rule": "memory:some-memo", "verdict": "did-not-work", "note": "memo"}])[0] == 0
    rows = rows_of(sb)
    assert [r["note"] for r in rows] == ["a, b c", "memo"]
    assert rows[0]["state"] == "loaded" and len(rows[0]["rev"]) == 10
    assert rows[1]["rev"] == ""


# ---------- isolate proposal: both sides of the probability boundary, failure, session as the unit ----------

def test_isolate_boundary_follows_base_rate(sb):
    background(sb)
    slug = sessions(sb, "alpha", ["worked"] * 7)
    assert row_for(cards(sb, slug)[1], "alpha") == []
    slug = sessions(sb, "alpha", ["worked"])
    out = cards(sb, slug)[1]
    rows = row_for(out, "alpha")
    assert len(rows) == 1 and "| isolate |" in rows[0] and "8/8" in rows[0] and "P=0.087" in rows[0]
    assert "Baseline: loaded-rule session failures 10/38" in out


def test_no_base_rate_means_no_probability_proposals(sb):
    slug = sessions(sb, "alpha", ["worked"] * 10)  # ledger with zero failures — zero failures is not information
    code, out, _ = cards(sb, slug)
    assert code == 0 and row_for(out, "alpha") == []


def test_any_failure_in_window_blocks_isolation(sb):
    background(sb)
    slug = sessions(sb, "alpha", ["worked"] * 5 + ["partly-worked"] + ["worked"] * 5)
    assert all("| isolate |" not in r for r in row_for(cards(sb, slug)[1], "alpha"))


def test_unit_is_session_and_worst_verdict_wins(sb):
    background(sb)
    for i in range(7):  # 7 sessions × 2 rows = 14 rows → 7 observations (if rows were counted, isolate would fire)
        assert add(sb, f"d{i}", [{"rule": "alpha", "verdict": "worked", "note": "1"},
                                 {"rule": "alpha", "verdict": "worked", "note": "2"}])[0] == 0
    assert row_for(cards(sb, "d6")[1], "alpha") == []
    assert add(sb, "d7", [{"rule": "alpha", "verdict": "worked", "note": "1"},
                          {"rule": "alpha", "verdict": "did-not-work", "note": "2"}])[0] == 0
    assert all("| isolate |" not in r for r in row_for(cards(sb, "d7")[1], "alpha"))


# ---------- fix-or-drop ----------

@pytest.mark.parametrize("verdicts,flag", [(["did-not-work", "partly-worked", "did-not-work"], True),
                                           (["did-not-work", "worked", "partly-worked"], False)])
def test_fix_boundary_follows_base_rate(sb, verdicts, flag):
    background(sb)
    slug = sessions(sb, "alpha", verdicts)
    out = cards(sb, slug)[1]
    rows = row_for(out, "alpha")
    assert any("| fix-or-drop |" in r for r in rows) == flag
    if flag:
        assert "P=0.061" in rows[0]
        assert f"- failure behind 1: event{sb.n}" in out  # decision material attached below the table


def test_fix_rejection_waits_for_new_sessions(sb):
    background(sb)
    slug = sessions(sb, "alpha", ["did-not-work"] * 3)
    assert gate(sb, slug, "alpha", "fix-or-drop", "reject")[0] == 0
    slug = sessions(sb, "alpha", ["did-not-work"] * 2)
    assert row_for(cards(sb, slug)[1], "alpha") == []
    slug = sessions(sb, "alpha", ["did-not-work"])
    rows = row_for(cards(sb, slug)[1], "alpha")
    assert len(rows) == 1 and "rejected 1×" in rows[0]


# ---------- isolate → observe → archive / restore ----------

def test_isolation_moves_file_and_demands_a_row_every_retro(sb):
    slug = sessions(sb, "alpha", ["worked"] * 5)
    assert gate(sb, slug, "alpha", "isolate", "accept")[0] == 0
    assert not (sb.home / "rules" / "alpha.md").exists()
    assert (sb.home / "rules-probation" / "alpha.md").exists()
    for s in ("next1", "next2"):
        code, _, err = cards(sb, s)
        assert code == 3 and "alpha" in err
        assert add(sb, s, [{"rule": "alpha", "verdict": "irrelevant", "note": "not delegated"}])[0] == 0
        code, out, _ = cards(sb, s)
        assert code == 0 and "1 isolated · no change this session" in out and row_for(out, "alpha") == []


def test_same_session_after_a_move_is_recorded_as_before_the_move(sb):
    slug = sessions(sb, "alpha", ["worked"] * 5)
    gate(sb, slug, "alpha", "isolate", "accept")
    code, out, _ = cards(sb, slug)  # this session had alpha loaded — it does not require an isolate verdict row
    assert code == 0 and "1 isolated · no change this session" in out
    assert add(sb, slug, [{"rule": "alpha", "verdict": "worked", "note": "still loaded, before the move"}], append=True)[0] == 0
    last = rows_of(sb)[-1]
    assert last["state"] == "loaded" and last["rev"] == rows_of(sb)[0]["rev"]
    out = cards(sb, slug)[1]
    assert "1 isolated · no change this session" in out  # a still-loaded observation does not count toward "without it"
    assert cards(sb, "next")[0] == 3  # from the next session on, an isolate verdict is required


def test_row_check_uses_the_full_session_key(sb):
    slug = sessions(sb, "alpha", ["worked"] * 5)
    gate(sb, slug, "alpha", "isolate", "accept")
    assert add(sb, "k", [{"rule": "alpha", "verdict": "irrelevant", "note": "x"}], date="2026-10-01")[0] == 0
    assert cards(sb, "k", date="2026-10-02")[0] == 3


def test_archive_proposed_after_clean_probation(sb):
    slug = sessions(sb, "alpha", ["worked"] * 5)
    gate(sb, slug, "alpha", "isolate", "accept")
    slug = sessions(sb, "alpha", ["worked", "worked"])
    out = cards(sb, slug)[1]
    assert row_for(out, "alpha") == []
    assert "1 isolated — relevant this session: `alpha` without it 2/2 · while loaded 5/5" in out
    slug = sessions(sb, "alpha", ["worked"])
    rows = row_for(cards(sb, slug)[1], "alpha")
    assert len(rows) == 1 and "| archive |" in rows[0] and "isolated 1× · failures while isolated 0" in rows[0]
    assert gate(sb, slug, "alpha", "archive", "accept")[0] == 0
    assert (sb.home / "rules-archive" / "alpha.md").exists()


def test_archive_rejection_waits_for_new_sessions(sb):
    slug = sessions(sb, "alpha", ["worked"] * 5)
    gate(sb, slug, "alpha", "isolate", "accept")
    slug = sessions(sb, "alpha", ["worked"] * 3)
    gate(sb, slug, "alpha", "archive", "reject")
    slug = sessions(sb, "alpha", ["worked"] * 2)
    assert row_for(cards(sb, slug)[1], "alpha") == []
    slug = sessions(sb, "alpha", ["worked"])
    rows = row_for(cards(sb, slug)[1], "alpha")
    assert len(rows) == 1 and "| archive |" in rows[0] and "rejected 1×" in rows[0]


def test_probation_failure_proposes_return_and_reject_waits_for_new_failure(sb):
    slug = sessions(sb, "alpha", ["worked"] * 5)
    gate(sb, slug, "alpha", "isolate", "accept")
    slug = sessions(sb, "alpha", ["did-not-work"])
    out = cards(sb, slug)[1]
    assert any("| restore |" in r for r in row_for(out, "alpha")) and f"- failure behind 1: event{sb.n}" in out
    gate(sb, slug, "alpha", "restore", "reject")
    slug = sessions(sb, "alpha", ["irrelevant"])
    assert row_for(cards(sb, slug)[1], "alpha") == []
    slug = sessions(sb, "alpha", ["partly-worked"])
    assert any("| restore |" in r for r in row_for(cards(sb, slug)[1], "alpha"))


def test_rejected_return_still_allows_archive_later(sb):
    slug = sessions(sb, "alpha", ["worked"] * 5)
    gate(sb, slug, "alpha", "isolate", "accept")
    slug = sessions(sb, "alpha", ["partly-worked"])
    gate(sb, slug, "alpha", "restore", "reject")
    slug = sessions(sb, "alpha", ["worked"] * 3)
    rows = row_for(cards(sb, slug)[1], "alpha")
    assert len(rows) == 1 and "| archive |" in rows[0] and "failures while isolated 1" in rows[0]


def test_return_right_after_isolation_does_not_loop(sb):
    background(sb)
    slug = sessions(sb, "alpha", ["worked"] * 8)
    gate(sb, slug, "alpha", "isolate", "accept")
    assert gate(sb, slug, "alpha", "restore", "accept")[0] == 0
    assert (sb.home / "rules" / "alpha.md").exists()
    assert row_for(cards(sb, slug)[1], "alpha") == []


def test_reisolation_card_shows_past_probation_failure(sb):
    background(sb)
    slug = sessions(sb, "alpha", ["worked"] * 5)
    gate(sb, slug, "alpha", "isolate", "accept")
    slug = sessions(sb, "alpha", ["did-not-work"])
    gate(sb, slug, "alpha", "restore", "accept")
    # the baseline p's denominator also includes alpha's 5 failure-free sessions before isolation: 10/(30+5+10)=0.22 → 0.78^10=0.08
    slug = sessions(sb, "alpha", ["worked"] * 10)
    rows = row_for(cards(sb, slug)[1], "alpha")
    assert len(rows) == 1 and "| isolate |" in rows[0] and "isolated 1× · failures while isolated 1" in rows[0]


def test_archived_rule_failure_proposes_return_only_in_that_session(sb):
    slug = sessions(sb, "alpha", ["worked"] * 5)
    gate(sb, slug, "alpha", "isolate", "accept")
    slug = sessions(sb, "alpha", ["worked"] * 3)
    gate(sb, slug, "alpha", "archive", "accept")
    slug = sessions(sb, "alpha", ["did-not-work"])
    assert any("| restore |" in r for r in row_for(cards(sb, slug)[1], "alpha"))
    slug = sessions(sb, "beta", ["worked"])
    assert row_for(cards(sb, slug)[1], "alpha") == []
    assert gate(sb, slug, "alpha", "restore", "accept")[0] == 0
    assert (sb.home / "rules" / "alpha.md").exists()


@pytest.mark.parametrize("prop,setup", [("archive", "loaded"), ("isolate", "probation"), ("restore", "loaded")])
def test_gate_refuses_wrong_state(sb, prop, setup):
    if setup == "probation":
        slug = sessions(sb, "alpha", ["worked"] * 5)
        gate(sb, slug, "alpha", "isolate", "accept")
    assert gate(sb, "g", "alpha", prop, "accept")[0] == 3


def test_gate_refuses_when_destination_exists(sb):
    (sb.home / "rules-probation").mkdir()
    (sb.home / "rules-probation" / "alpha.md").write_text("a different revision", encoding="utf-8")
    assert gate(sb, "g", "alpha", "isolate", "accept")[0] == 3
    assert (sb.home / "rules" / "alpha.md").exists()


def test_gate_does_not_move_when_ledger_is_unwritable(sb):
    sessions(sb, "alpha", ["worked"])
    os.chmod(sb.ledger, stat.S_IREAD)
    try:
        code, _, _ = gate(sb, "g", "alpha", "isolate", "accept")
    finally:
        os.chmod(sb.ledger, stat.S_IREAD | stat.S_IWRITE)
    assert code not in (0, 3)
    assert (sb.home / "rules" / "alpha.md").exists()
    assert not (sb.home / "rules-probation" / "alpha.md").exists()


# ---------- window reset: revisions, rejection suppression ----------

def test_revision_resets_window(sb):
    background(sb)
    slug = sessions(sb, "alpha", ["worked"] * 8)
    (sb.home / "rules" / "alpha.md").write_text("# Alpha rule — reinforced\n\nnew line\n", encoding="utf-8")
    assert row_for(cards(sb, slug)[1], "alpha") == []


def test_stats_splits_current_and_previous_revision(sb):
    sessions(sb, "alpha", ["worked", "did-not-work"])
    (sb.home / "rules" / "alpha.md").write_text("# Alpha rule — reinforced\n\nnew line\n", encoding="utf-8")
    sessions(sb, "alpha", ["worked", "worked", "partly-worked"])
    code, out, _ = run(sb, "stats", "alpha")
    assert code == 0 and "current rev worked 2/3" in out and "previous rev (while loaded) worked 1/2" in out


def test_stats_previous_revision_excludes_probation_sessions(sb):
    slug = sessions(sb, "alpha", ["worked", "did-not-work"])
    gate(sb, slug, "alpha", "isolate", "accept")
    slug = sessions(sb, "alpha", ["worked", "worked"])
    gate(sb, slug, "alpha", "restore", "accept")
    sessions(sb, "alpha", ["worked"])
    out = run(sb, "stats", "alpha")[1]
    assert "current rev worked 1/1" in out and "previous rev (while loaded) worked 1/2" in out and "isolated 1×" in out


def test_same_session_rows_across_a_revision_are_two_observations(sb):
    assert add(sb, "k", [{"rule": "alpha", "verdict": "did-not-work", "note": "before reinforcement"}])[0] == 0
    (sb.home / "rules" / "alpha.md").write_text("# Alpha rule — reinforced\n\nnew line\n", encoding="utf-8")
    assert add(sb, "k", [{"rule": "alpha", "verdict": "worked", "note": "after reinforcement"}], append=True)[0] == 0
    out = run(sb, "stats", "alpha")[1]
    assert "current rev worked 1/1" in out and "previous rev (while loaded) worked 0/1" in out


def test_window_is_contiguous_when_a_revision_is_reverted(sb):
    background(sb)
    original = (sb.home / "rules" / "alpha.md").read_text(encoding="utf-8")
    sessions(sb, "alpha", ["worked"] * 8)
    (sb.home / "rules" / "alpha.md").write_text("# Alpha rule — temporary change\n", encoding="utf-8")
    slug = sessions(sb, "alpha", ["did-not-work"])
    (sb.home / "rules" / "alpha.md").write_text(original, encoding="utf-8")  # reverted, but the old 8 sessions are still not in the window
    assert row_for(cards(sb, slug)[1], "alpha") == []


def test_return_then_new_sessions_start_a_fresh_window(sb):
    background(sb)
    slug = sessions(sb, "alpha", ["worked"] * 8)
    gate(sb, slug, "alpha", "isolate", "accept")
    gate(sb, slug, "alpha", "restore", "accept")
    slug = sessions(sb, "alpha", ["worked"] * 3)  # suppression is lifted, but the window is only the 3 sessions after restore — short of the isolate threshold
    assert row_for(cards(sb, slug)[1], "alpha") == []


def test_rejected_isolation_waits_for_new_sessions(sb):
    background(sb)
    slug = sessions(sb, "alpha", ["worked"] * 8)
    gate(sb, slug, "alpha", "isolate", "reject")
    slug = sessions(sb, "alpha", ["worked"] * 2)
    assert row_for(cards(sb, slug)[1], "alpha") == []
    slug = sessions(sb, "alpha", ["worked"])
    rows = row_for(cards(sb, slug)[1], "alpha")
    assert len(rows) == 1 and "rejected 1×" in rows[0]


# ---------- rarely-relevant ----------

def test_rare_row_and_one_row_per_rule(sb):
    sessions(sb, "beta", ["did-not-work", "did-not-work", "worked"])
    slug = sessions(sb, "alpha", ["worked"] * 15)  # beta has 0 relevant sessions in the last 15 retros
    rows = row_for(cards(sb, slug)[1], "beta")
    assert len(rows) == 1 and "| fix-or-drop |" in rows[0] and "relevant in 0 of the last 15 retros" in rows[0]


@pytest.mark.parametrize("extra_beta,flag", [(0, True), (1, True), (2, False)])
def test_rare_max_boundary(sb, extra_beta, flag):
    sessions(sb, "beta", ["worked"])
    slug = sessions(sb, "alpha", ["worked"] * (15 - extra_beta))
    if extra_beta:
        slug = sessions(sb, "beta", ["worked"] * extra_beta)
    assert any("| rarely-relevant |" in r for r in row_for(cards(sb, slug)[1], "beta")) == flag


def test_rare_needs_a_full_window_before_first_observation(sb):
    sessions(sb, "alpha", ["worked"] * 14)
    slug = sessions(sb, "beta", ["worked"])  # first-scored rule — born inside the recent window
    assert row_for(cards(sb, slug)[1], "beta") == []
    sessions(sb, "beta", ["worked"])
    slug = sessions(sb, "alpha", ["worked"] * 14)  # with a window of 16, beta's first observation is inside it, so it does not fire
    assert any("| rarely-relevant |" in r for r in row_for(cards(sb, slug)[1], "beta"))


def test_small_rule_is_not_rare(sb):
    sessions(sb, "alpha", ["worked"])
    slug = sessions(sb, "gamma", ["worked"] * 15)
    assert row_for(cards(sb, slug)[1], "alpha") == []  # alpha is under 1500 chars


# ---------- table shape ----------

def test_empty_ledger_says_what_it_read(sb):
    code, out, _ = cards(sb, "x")
    assert code == 0 and "None (read 0 ledger rows · 0 retros)" in out
    assert "3 rules with no verdicts yet" in out


def test_coverage_counts_sealed_sessions_from_window_start(sb):
    d = sb.seal / "Sessions" / "p"
    d.mkdir()
    (d / "a.md").write_text("---\ndate: 2026-10-01\nstatus: sealed\n---\n", encoding="utf-8")
    (d / "b.md").write_text("---\ndate: 2026-10-05\nstatus: sealed\n---\n", encoding="utf-8")
    (d / "c.md").write_text("---\ndate: 2026-09-01\nstatus: sealed\n---\n", encoding="utf-8")
    (d / "x-draft.md").write_text("---\ndate: 2026-10-02\nstatus: sealed\n---\n", encoding="utf-8")
    (d / "e.md").write_text("---\ndate: 2026-10-03\nstatus: draft\n---\n", encoding="utf-8")
    background(sb)
    slug = sessions(sb, "alpha", ["worked"] * 8)
    gate(sb, "gate-only", "beta", "fix-or-drop", "reject")  # a session key that only has a gate is not a retro
    rows = row_for(cards(sb, slug)[1], "alpha")
    assert "2026-10-01~ sealed 2 · retros 38" in rows[0]


def test_recur_rate_counts_single_source_nodes_within_horizon(sb):
    for i in range(7):  # retro timeline 2026-07-02 .. 07-08
        add(sb, f"r{i}", [{"rule": "alpha", "verdict": "worked", "note": "x"}], date=f"2026-07-0{i + 2}")
    nodes = "\n".join([
        "### A", "sources: [[2026-07-01 - a]]", "",                                  # single, never recorded again
        "### B", "sources: [[2026-07-01 - b]], [[2026-07-04 - b2]]", "",             # single, not recorded again by the 5th retro (07-06)
        "### C", "sources: [[2026-07-01 - c]], [[2026-07-08 - c2]]", "",             # single, recorded again outside the horizon
        "### D", "sources: [[2026-06-01 - d]], [[2026-07-03 - d2]]", "",             # before the cohort start, if one is set — excluded then
        "### E", "sources: [[2026-07-05 - e]]", "",                                  # only 3 retros follow — censored, excluded
        "### F", "sources: [[2026-07-01 - f]], draft:[[2026-07-01 - f2]]", "",       # born with 2 sources the same day — excluded
    ])
    (sb.tmp / "corpus" / "a-mistakes.md").write_text(nodes, encoding="utf-8")
    out = cards(sb, "z", date="2026-07-09")[1]
    assert "2/4 (0.50)" in out  # default is no cohort — D counts too
    # the cohort is a constant, so import the module, change it, then call main
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import ledger; ledger.RECUR_COHORT = '2026-07-01'; "
            "sys.exit(ledger.main(sys.argv[2:]))")
    p = subprocess.run([sys.executable, "-c", code, str(LEDGER_PY.parent), "cards", "--slug", "z",
                        "--date", "2026-07-09", "--project", "t"], env=sb.env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    assert p.returncode == 0 and "1/3 (0.33, 2026-07-01~ cohort)" in p.stdout


def test_leaks_separates_content_from_pointers(sb):
    (sb.home / "hooks").mkdir()
    (sb.home / "hooks" / "h.py").write_text("# enforces alpha\n", encoding="utf-8")
    (sb.home / "projects" / "p" / "memory" / "m.md").write_text("see alpha\n", encoding="utf-8")
    proj = sb.tmp / "projects" / "x"
    proj.mkdir(parents=True)
    (proj / "CLAUDE.md").write_text("follows Keep the alpha rule\n", encoding="utf-8")
    ex = sb.home / "skills" / "session-retro" / "examples"
    ex.mkdir(parents=True)
    (ex / "run.md").write_text("alpha sample output\n", encoding="utf-8")
    code, out, _ = run(sb, "leaks", "alpha")
    assert code == 0 and "Places that carry content: 2" in out and "Name pointers: 1" in out and "examples" not in out


# ---------- optional folders missing: "not found" vs. "not scanned" ----------

def unset(sb, *names):
    for n in names:
        sb.env.pop(n)


def test_coverage_without_seal_dir_omits_sealed_count(sb):
    unset(sb, "SESSION_SEAL_DIR")
    background(sb)
    slug = sessions(sb, "alpha", ["worked"] * 8)
    rows = row_for(cards(sb, slug)[1], "alpha")
    assert "2026-10-01~ retros 38" in rows[0] and "sealed" not in rows[0]


def policy_line(out):
    return [line for line in out.splitlines() if line.startswith("Add-policy reference")]


def test_recur_rate_without_corpus_says_so(sb):
    unset(sb, "SESSION_RETRO_CORPUS")
    code, out, _ = cards(sb, "x")
    line = policy_line(out)
    assert code == 0 and len(line) == 1 and "corpus not configured" in line[0] and "no sample" not in line[0]


def test_recur_rate_with_empty_corpus_is_no_sample(sb):
    code, out, _ = cards(sb, "x")
    line = policy_line(out)
    assert code == 0 and len(line) == 1 and "no sample" in line[0] and "not configured" not in line[0]


def test_leaks_without_projects_says_what_it_skipped(sb):
    proj = sb.tmp / "projects" / "x"
    proj.mkdir(parents=True)
    (proj / "CLAUDE.md").write_text("follows alpha\n", encoding="utf-8")
    unset(sb, "SESSION_RETRO_PROJECTS")
    code, out, _ = run(sb, "leaks", "alpha")
    assert code == 0 and "SESSION_RETRO_PROJECTS not set" in out and "Places that carry content: 0" in out


def test_default_ledger_lives_under_claude_home(sb):
    unset(sb, "SESSION_RETRO_DIR")
    assert add(sb, "a", [{"rule": "alpha", "verdict": "worked", "note": "x"}])[0] == 0
    assert (sb.home / "session-retro" / "verdicts.csv").is_file()


# ---------- exit codes: tool failure differs from violation (3) ----------

@pytest.mark.parametrize("text", ["a,b,c\n1,2,3\n",
                                  "seq,kind,date,project,slug,rule,state,rev,verdict,note,src\n1,obs,d,p,s,alpha,loaded,r,worked,n,retro,EXTRA\n"])
def test_corrupt_ledger_is_tool_failure_not_violation(sb, text):
    sb.ledger.write_text(text, encoding="utf-8")
    code, _, _ = cards(sb, "x")
    assert code not in (0, 3)
