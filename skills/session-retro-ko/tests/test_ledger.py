"""ledger.py 불변식. 실제 원장·rule 은 건드리지 않고 tmp 샌드박스에서 subprocess 로 돌린다 (종료 코드까지 계약이다).

확률 경계는 배경 rule `gamma` (30세션 중 실패 10) 를 깔고 손으로 계산한 값이다:
  격리: 창 k 세션 무실패, 기준 p = 10/(30+k) → (1-p)^k : k=7 → 0.110 (안 걸림), k=8 → 0.087 (걸림)
  고치거나빼기: 창 3세션, 기준 p = (10+f)/33 → f=3: 0.061 (걸림), f=2: 0.30 (안 걸림)
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
    (home / "rules" / "alpha.md").write_text("# 알파 규칙을 지킨다 — 부제\n\n본문\n", encoding="utf-8")
    (home / "rules" / "beta.md").write_text("# 베타 규칙\n\n" + "가" * 1600 + "\n", encoding="utf-8")
    (home / "rules" / "gamma.md").write_text("# 감마 규칙\n\n배경\n", encoding="utf-8")
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
               "--proposal", prop, "--decision", dec, "--note", "테스트")


def sessions(sb, rule, verdicts):
    """rule 에 대해 세션을 하나씩 만들어 판정을 쌓는다. 마지막 세션 slug 를 돌려준다."""
    slug = None
    for v in verdicts:
        sb.n += 1
        slug = f"s{sb.n}"
        code, _, err = add(sb, slug, [{"rule": rule, "verdict": v, "note": f"사건{sb.n}"}])
        assert code == 0, err
    return slug


def background(sb):
    sessions(sb, "gamma", ["미작동"] * 10 + ["작동"] * 20)


def rows_of(sb):
    if not sb.ledger.exists():
        return []
    with sb.ledger.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def row_for(out, rule):
    return [line for line in out.splitlines() if line.startswith("|") and f"`{rule}`" in line]


# ---------- add: 입력 검사는 all-or-nothing ----------

@pytest.mark.parametrize("bad", [
    {"rule": "alpha", "verdict": "**작동**", "note": "꾸민 라벨"},
    {"rule": "alpha", "verdict": "작동 — 단 우연", "note": "주석 붙은 라벨"},
    {"rule": "alph", "verdict": "작동", "note": "오타 이름"},
    {"rule": "Alpha", "verdict": "작동", "note": "대소문자만 다른 이름"},
    {"rule": "alpha", "verdict": "무관", "note": "loaded 인데 무관"},
    {"rule": "alpha", "verdict": "작동", "note": "   "},
    {"rule": "memory:nope", "verdict": "작동", "note": "없는 memory"},
    {"rule": "memory:*", "verdict": "작동", "note": "glob"},
])
def test_add_rejects_and_writes_nothing(sb, bad):
    code, _, err = add(sb, "x", [{"rule": "beta", "verdict": "작동", "note": "정상 행"}, bad])
    assert code == 3, err
    assert rows_of(sb) == []


@pytest.mark.parametrize("text", ['[{"rule": "alpha", "verdict": "작동", "note": "x"},]', '["alpha"]', "[]"])
def test_bad_json_is_violation_not_tool_failure(sb, text):
    f = sb.tmp / "bad.json"
    f.write_text(text, encoding="utf-8")
    assert run(sb, "add", "--slug", "x", "--date", "2026-10-01", "--project", "t", "--file", str(f))[0] == 3


def test_bom_json_is_accepted(sb):
    f = sb.tmp / "bom.json"
    f.write_text('[{"rule": "alpha", "verdict": "작동", "note": "x"}]', encoding="utf-8-sig")
    assert run(sb, "add", "--slug", "x", "--date", "2026-10-01", "--project", "t", "--file", str(f))[0] == 0


@pytest.mark.parametrize("args", [["--slug", "a b"], ["--slug", "a|b"], ["--slug", "ok", "--date", "10/01/2026"]])
def test_bad_session_args_rejected(sb, args):
    f = sb.tmp / "r.json"
    f.write_text('[{"rule": "alpha", "verdict": "작동", "note": "x"}]', encoding="utf-8")
    base = {"--slug": "ok", "--date": "2026-10-01"}
    for i in range(0, len(args), 2):
        base[args[i]] = args[i + 1]
    flat = [x for kv in base.items() for x in kv]
    assert run(sb, "add", *flat, "--project", "t", "--file", str(f))[0] == 3


def test_session_key_reuse_needs_append(sb):
    assert add(sb, "same", [{"rule": "alpha", "verdict": "작동", "note": "오전"}])[0] == 0
    assert add(sb, "same", [{"rule": "alpha", "verdict": "작동", "note": "오후"}])[0] == 3
    assert add(sb, "same", [{"rule": "beta", "verdict": "작동", "note": "추가분"}], append=True)[0] == 0


def test_note_with_comma_and_newline_keeps_columns(sb):
    assert add(sb, "x", [{"rule": "alpha", "verdict": "작동", "note": "a, b\nc"},
                         {"rule": "memory:some-memo", "verdict": "미작동", "note": "메모"}])[0] == 0
    rows = rows_of(sb)
    assert [r["note"] for r in rows] == ["a, b c", "메모"]
    assert rows[0]["state"] == "loaded" and len(rows[0]["rev"]) == 10
    assert rows[1]["rev"] == ""


# ---------- 격리 제안: 확률 경계 양쪽, 실패, 세션 단위 ----------

def test_isolate_boundary_follows_base_rate(sb):
    background(sb)
    slug = sessions(sb, "alpha", ["작동"] * 7)
    assert row_for(cards(sb, slug)[1], "alpha") == []
    slug = sessions(sb, "alpha", ["작동"])
    out = cards(sb, slug)[1]
    rows = row_for(out, "alpha")
    assert len(rows) == 1 and "| 격리 |" in rows[0] and "8/8" in rows[0] and "P=0.087" in rows[0]
    assert "기준: 실린 rule 세션 실패 10/38" in out


def test_no_base_rate_means_no_probability_proposals(sb):
    slug = sessions(sb, "alpha", ["작동"] * 10)  # 실패가 하나도 없는 원장 — 무실패는 정보가 아니다
    code, out, _ = cards(sb, slug)
    assert code == 0 and row_for(out, "alpha") == []


def test_any_failure_in_window_blocks_isolation(sb):
    background(sb)
    slug = sessions(sb, "alpha", ["작동"] * 5 + ["부분작동"] + ["작동"] * 5)
    assert all("| 격리 |" not in r for r in row_for(cards(sb, slug)[1], "alpha"))


def test_unit_is_session_and_worst_verdict_wins(sb):
    background(sb)
    for i in range(7):  # 7 세션 × 2행 = 14행 → 7 관측 (행을 셌다면 격리가 떴다)
        assert add(sb, f"d{i}", [{"rule": "alpha", "verdict": "작동", "note": "1"},
                                 {"rule": "alpha", "verdict": "작동", "note": "2"}])[0] == 0
    assert row_for(cards(sb, "d6")[1], "alpha") == []
    assert add(sb, "d7", [{"rule": "alpha", "verdict": "작동", "note": "1"},
                          {"rule": "alpha", "verdict": "미작동", "note": "2"}])[0] == 0
    assert all("| 격리 |" not in r for r in row_for(cards(sb, "d7")[1], "alpha"))


# ---------- 고치거나빼기 ----------

@pytest.mark.parametrize("verdicts,flag", [(["미작동", "부분작동", "미작동"], True),
                                           (["미작동", "작동", "부분작동"], False)])
def test_fix_boundary_follows_base_rate(sb, verdicts, flag):
    background(sb)
    slug = sessions(sb, "alpha", verdicts)
    out = cards(sb, slug)[1]
    rows = row_for(out, "alpha")
    assert any("| 고치거나빼기 |" in r for r in rows) == flag
    if flag:
        assert "P=0.061" in rows[0]
        assert f"실패 사건: 사건{sb.n}" in out  # 결정 재료가 표 아래에 붙는다


def test_fix_rejection_waits_for_new_sessions(sb):
    background(sb)
    slug = sessions(sb, "alpha", ["미작동"] * 3)
    assert gate(sb, slug, "alpha", "고치거나빼기", "reject")[0] == 0
    slug = sessions(sb, "alpha", ["미작동"] * 2)
    assert row_for(cards(sb, slug)[1], "alpha") == []
    slug = sessions(sb, "alpha", ["미작동"])
    rows = row_for(cards(sb, slug)[1], "alpha")
    assert len(rows) == 1 and "1회 반려" in rows[0]


# ---------- 격리 → 관측 → 보관 / 복귀 ----------

def test_isolation_moves_file_and_demands_a_row_every_retro(sb):
    slug = sessions(sb, "alpha", ["작동"] * 5)
    assert gate(sb, slug, "alpha", "격리", "accept")[0] == 0
    assert not (sb.home / "rules" / "alpha.md").exists()
    assert (sb.home / "rules-probation" / "alpha.md").exists()
    for s in ("next1", "next2"):
        code, _, err = cards(sb, s)
        assert code == 3 and "alpha" in err
        assert add(sb, s, [{"rule": "alpha", "verdict": "무관", "note": "위임 없음"}])[0] == 0
        code, out, _ = cards(sb, s)
        assert code == 0 and "격리 중 1개 · 이번 세션 변화 없음" in out and row_for(out, "alpha") == []


def test_same_session_after_a_move_is_recorded_as_before_the_move(sb):
    slug = sessions(sb, "alpha", ["작동"] * 5)
    gate(sb, slug, "alpha", "격리", "accept")
    code, out, _ = cards(sb, slug)  # 이 세션엔 alpha 가 실려 있었다 — 격리 판정 행을 요구하지 않는다
    assert code == 0 and "격리 중 1개 · 이번 세션 변화 없음" in out
    assert add(sb, slug, [{"rule": "alpha", "verdict": "작동", "note": "옮기기 전 실린 채"}], append=True)[0] == 0
    last = rows_of(sb)[-1]
    assert last["state"] == "loaded" and last["rev"] == rows_of(sb)[0]["rev"]
    out = cards(sb, slug)[1]
    assert "격리 중 1개 · 이번 세션 변화 없음" in out  # 실린 채 관측은 "없이" 로 세지 않는다
    assert cards(sb, "next")[0] == 3  # 다음 세션부터는 격리 판정이 필요하다


def test_row_check_uses_the_full_session_key(sb):
    slug = sessions(sb, "alpha", ["작동"] * 5)
    gate(sb, slug, "alpha", "격리", "accept")
    assert add(sb, "k", [{"rule": "alpha", "verdict": "무관", "note": "x"}], date="2026-10-01")[0] == 0
    assert cards(sb, "k", date="2026-10-02")[0] == 3


def test_archive_proposed_after_clean_probation(sb):
    slug = sessions(sb, "alpha", ["작동"] * 5)
    gate(sb, slug, "alpha", "격리", "accept")
    slug = sessions(sb, "alpha", ["작동", "작동"])
    out = cards(sb, slug)[1]
    assert row_for(out, "alpha") == []
    assert "격리 중 1개 — 이번 세션 관련: `alpha` 없이 2/2 · 실린 채 5/5" in out
    slug = sessions(sb, "alpha", ["작동"])
    rows = row_for(cards(sb, slug)[1], "alpha")
    assert len(rows) == 1 and "| 보관 |" in rows[0] and "격리 1회 · 격리 중 실패 0" in rows[0]
    assert gate(sb, slug, "alpha", "보관", "accept")[0] == 0
    assert (sb.home / "rules-archive" / "alpha.md").exists()


def test_archive_rejection_waits_for_new_sessions(sb):
    slug = sessions(sb, "alpha", ["작동"] * 5)
    gate(sb, slug, "alpha", "격리", "accept")
    slug = sessions(sb, "alpha", ["작동"] * 3)
    gate(sb, slug, "alpha", "보관", "reject")
    slug = sessions(sb, "alpha", ["작동"] * 2)
    assert row_for(cards(sb, slug)[1], "alpha") == []
    slug = sessions(sb, "alpha", ["작동"])
    rows = row_for(cards(sb, slug)[1], "alpha")
    assert len(rows) == 1 and "| 보관 |" in rows[0] and "1회 반려" in rows[0]


def test_probation_failure_proposes_return_and_reject_waits_for_new_failure(sb):
    slug = sessions(sb, "alpha", ["작동"] * 5)
    gate(sb, slug, "alpha", "격리", "accept")
    slug = sessions(sb, "alpha", ["미작동"])
    out = cards(sb, slug)[1]
    assert any("| 복귀 |" in r for r in row_for(out, "alpha")) and f"실패 사건: 사건{sb.n}" in out
    gate(sb, slug, "alpha", "복귀", "reject")
    slug = sessions(sb, "alpha", ["무관"])
    assert row_for(cards(sb, slug)[1], "alpha") == []
    slug = sessions(sb, "alpha", ["부분작동"])
    assert any("| 복귀 |" in r for r in row_for(cards(sb, slug)[1], "alpha"))


def test_rejected_return_still_allows_archive_later(sb):
    slug = sessions(sb, "alpha", ["작동"] * 5)
    gate(sb, slug, "alpha", "격리", "accept")
    slug = sessions(sb, "alpha", ["부분작동"])
    gate(sb, slug, "alpha", "복귀", "reject")
    slug = sessions(sb, "alpha", ["작동"] * 3)
    rows = row_for(cards(sb, slug)[1], "alpha")
    assert len(rows) == 1 and "| 보관 |" in rows[0] and "격리 중 실패 1" in rows[0]


def test_return_right_after_isolation_does_not_loop(sb):
    background(sb)
    slug = sessions(sb, "alpha", ["작동"] * 8)
    gate(sb, slug, "alpha", "격리", "accept")
    assert gate(sb, slug, "alpha", "복귀", "accept")[0] == 0
    assert (sb.home / "rules" / "alpha.md").exists()
    assert row_for(cards(sb, slug)[1], "alpha") == []


def test_reisolation_card_shows_past_probation_failure(sb):
    background(sb)
    slug = sessions(sb, "alpha", ["작동"] * 5)
    gate(sb, slug, "alpha", "격리", "accept")
    slug = sessions(sb, "alpha", ["미작동"])
    gate(sb, slug, "alpha", "복귀", "accept")
    # 기준 p 의 분모엔 alpha 의 격리 전 무실패 5세션도 들어간다: 10/(30+5+10)=0.22 → 0.78^10=0.08
    slug = sessions(sb, "alpha", ["작동"] * 10)
    rows = row_for(cards(sb, slug)[1], "alpha")
    assert len(rows) == 1 and "| 격리 |" in rows[0] and "격리 1회 · 격리 중 실패 1" in rows[0]


def test_archived_rule_failure_proposes_return_only_in_that_session(sb):
    slug = sessions(sb, "alpha", ["작동"] * 5)
    gate(sb, slug, "alpha", "격리", "accept")
    slug = sessions(sb, "alpha", ["작동"] * 3)
    gate(sb, slug, "alpha", "보관", "accept")
    slug = sessions(sb, "alpha", ["미작동"])
    assert any("| 복귀 |" in r for r in row_for(cards(sb, slug)[1], "alpha"))
    slug = sessions(sb, "beta", ["작동"])
    assert row_for(cards(sb, slug)[1], "alpha") == []
    assert gate(sb, slug, "alpha", "복귀", "accept")[0] == 0
    assert (sb.home / "rules" / "alpha.md").exists()


@pytest.mark.parametrize("prop,setup", [("보관", "loaded"), ("격리", "probation"), ("복귀", "loaded")])
def test_gate_refuses_wrong_state(sb, prop, setup):
    if setup == "probation":
        slug = sessions(sb, "alpha", ["작동"] * 5)
        gate(sb, slug, "alpha", "격리", "accept")
    assert gate(sb, "g", "alpha", prop, "accept")[0] == 3


def test_gate_refuses_when_destination_exists(sb):
    (sb.home / "rules-probation").mkdir()
    (sb.home / "rules-probation" / "alpha.md").write_text("다른 판", encoding="utf-8")
    assert gate(sb, "g", "alpha", "격리", "accept")[0] == 3
    assert (sb.home / "rules" / "alpha.md").exists()


def test_gate_does_not_move_when_ledger_is_unwritable(sb):
    sessions(sb, "alpha", ["작동"])
    os.chmod(sb.ledger, stat.S_IREAD)
    try:
        code, _, _ = gate(sb, "g", "alpha", "격리", "accept")
    finally:
        os.chmod(sb.ledger, stat.S_IREAD | stat.S_IWRITE)
    assert code not in (0, 3)
    assert (sb.home / "rules" / "alpha.md").exists()
    assert not (sb.home / "rules-probation" / "alpha.md").exists()


# ---------- 창 리셋: 개정, 반려 억제 ----------

def test_revision_resets_window(sb):
    background(sb)
    slug = sessions(sb, "alpha", ["작동"] * 8)
    (sb.home / "rules" / "alpha.md").write_text("# 알파 규칙 — 보강\n\n새 행\n", encoding="utf-8")
    assert row_for(cards(sb, slug)[1], "alpha") == []


def test_stats_splits_current_and_previous_revision(sb):
    sessions(sb, "alpha", ["작동", "미작동"])
    (sb.home / "rules" / "alpha.md").write_text("# 알파 규칙 — 보강\n\n새 행\n", encoding="utf-8")
    sessions(sb, "alpha", ["작동", "작동", "부분작동"])
    code, out, _ = run(sb, "stats", "alpha")
    assert code == 0 and "현재 판 작동 2/3" in out and "이전 판(실린 채) 작동 1/2" in out


def test_stats_previous_revision_excludes_probation_sessions(sb):
    slug = sessions(sb, "alpha", ["작동", "미작동"])
    gate(sb, slug, "alpha", "격리", "accept")
    slug = sessions(sb, "alpha", ["작동", "작동"])
    gate(sb, slug, "alpha", "복귀", "accept")
    sessions(sb, "alpha", ["작동"])
    out = run(sb, "stats", "alpha")[1]
    assert "현재 판 작동 1/1" in out and "이전 판(실린 채) 작동 1/2" in out and "격리 1회" in out


def test_same_session_rows_across_a_revision_are_two_observations(sb):
    assert add(sb, "k", [{"rule": "alpha", "verdict": "미작동", "note": "보강 전"}])[0] == 0
    (sb.home / "rules" / "alpha.md").write_text("# 알파 규칙 — 보강\n\n새 행\n", encoding="utf-8")
    assert add(sb, "k", [{"rule": "alpha", "verdict": "작동", "note": "보강 뒤"}], append=True)[0] == 0
    out = run(sb, "stats", "alpha")[1]
    assert "현재 판 작동 1/1" in out and "이전 판(실린 채) 작동 0/1" in out


def test_window_is_contiguous_when_a_revision_is_reverted(sb):
    background(sb)
    original = (sb.home / "rules" / "alpha.md").read_text(encoding="utf-8")
    sessions(sb, "alpha", ["작동"] * 8)
    (sb.home / "rules" / "alpha.md").write_text("# 알파 규칙 — 잠깐 바꿈\n", encoding="utf-8")
    slug = sessions(sb, "alpha", ["미작동"])
    (sb.home / "rules" / "alpha.md").write_text(original, encoding="utf-8")  # 되돌렸어도 옛 8세션은 창이 아니다
    assert row_for(cards(sb, slug)[1], "alpha") == []


def test_return_then_new_sessions_start_a_fresh_window(sb):
    background(sb)
    slug = sessions(sb, "alpha", ["작동"] * 8)
    gate(sb, slug, "alpha", "격리", "accept")
    gate(sb, slug, "alpha", "복귀", "accept")
    slug = sessions(sb, "alpha", ["작동"] * 3)  # 억제는 풀렸고, 창은 복귀 뒤 3세션뿐 — 격리 확률에 못 미친다
    assert row_for(cards(sb, slug)[1], "alpha") == []


def test_rejected_isolation_waits_for_new_sessions(sb):
    background(sb)
    slug = sessions(sb, "alpha", ["작동"] * 8)
    gate(sb, slug, "alpha", "격리", "reject")
    slug = sessions(sb, "alpha", ["작동"] * 2)
    assert row_for(cards(sb, slug)[1], "alpha") == []
    slug = sessions(sb, "alpha", ["작동"])
    rows = row_for(cards(sb, slug)[1], "alpha")
    assert len(rows) == 1 and "1회 반려" in rows[0]


# ---------- 관련드묾 ----------

def test_rare_row_and_one_row_per_rule(sb):
    sessions(sb, "beta", ["미작동", "미작동", "작동"])
    slug = sessions(sb, "alpha", ["작동"] * 15)  # beta 는 최근 15회고에 관련 0
    rows = row_for(cards(sb, slug)[1], "beta")
    assert len(rows) == 1 and "| 고치거나빼기 |" in rows[0] and "최근 회고 15회 중 관련 0" in rows[0]


@pytest.mark.parametrize("extra_beta,flag", [(0, True), (1, True), (2, False)])
def test_rare_max_boundary(sb, extra_beta, flag):
    sessions(sb, "beta", ["작동"])
    slug = sessions(sb, "alpha", ["작동"] * (15 - extra_beta))
    if extra_beta:
        slug = sessions(sb, "beta", ["작동"] * extra_beta)
    assert any("| 관련드묾 |" in r for r in row_for(cards(sb, slug)[1], "beta")) == flag


def test_rare_needs_a_full_window_before_first_observation(sb):
    sessions(sb, "alpha", ["작동"] * 14)
    slug = sessions(sb, "beta", ["작동"])  # 처음 채점된 rule — 최근 창 안에서 태어났다
    assert row_for(cards(sb, slug)[1], "beta") == []
    sessions(sb, "beta", ["작동"])
    slug = sessions(sb, "alpha", ["작동"] * 14)  # 창 길이 16 이면 beta 첫 관측이 창 안이라 안 걸린다
    assert any("| 관련드묾 |" in r for r in row_for(cards(sb, slug)[1], "beta"))


def test_small_rule_is_not_rare(sb):
    sessions(sb, "alpha", ["작동"])
    slug = sessions(sb, "gamma", ["작동"] * 15)
    assert row_for(cards(sb, slug)[1], "alpha") == []  # alpha 는 1500 chars 미만


# ---------- 표 모양 ----------

def test_empty_ledger_says_what_it_read(sb):
    code, out, _ = cards(sb, "x")
    assert code == 0 and "없음 (원장 0행 · 회고 0회 읽음)" in out
    assert "채점 기록 없는 rule 3개" in out


def test_coverage_counts_sealed_sessions_from_window_start(sb):
    d = sb.seal / "Sessions" / "p"
    d.mkdir()
    (d / "a.md").write_text("---\ndate: 2026-10-01\nstatus: sealed\n---\n", encoding="utf-8")
    (d / "b.md").write_text("---\ndate: 2026-10-05\nstatus: sealed\n---\n", encoding="utf-8")
    (d / "c.md").write_text("---\ndate: 2026-09-01\nstatus: sealed\n---\n", encoding="utf-8")
    (d / "x-draft.md").write_text("---\ndate: 2026-10-02\nstatus: sealed\n---\n", encoding="utf-8")
    (d / "e.md").write_text("---\ndate: 2026-10-03\nstatus: draft\n---\n", encoding="utf-8")
    background(sb)
    slug = sessions(sb, "alpha", ["작동"] * 8)
    gate(sb, "gate-only", "beta", "고치거나빼기", "reject")  # gate 만 있는 세션 키는 회고가 아니다
    rows = row_for(cards(sb, slug)[1], "alpha")
    assert "2026-10-01~ sealed 2 · 회고 38" in rows[0]


def test_recur_rate_counts_single_source_nodes_within_horizon(sb):
    for i in range(7):  # 회고 타임라인 2026-07-02 ~ 07-08
        add(sb, f"r{i}", [{"rule": "alpha", "verdict": "작동", "note": "x"}], date=f"2026-07-0{i + 2}")
    nodes = "\n".join([
        "### A", "sources: [[2026-07-01 - a]]", "",                                  # 시행, 재기록 없음
        "### B", "sources: [[2026-07-01 - b]], [[2026-07-04 - b2]]", "",             # 시행, 5번째 회고(07-06) 안 재기록
        "### C", "sources: [[2026-07-01 - c]], [[2026-07-08 - c2]]", "",             # 시행, 지평 밖 재기록
        "### D", "sources: [[2026-06-01 - d]], [[2026-07-03 - d2]]", "",             # 코호트를 두면 그 전 — 제외
        "### E", "sources: [[2026-07-05 - e]]", "",                                  # 뒤 회고 3개 — 검열 제외
        "### F", "sources: [[2026-07-01 - f]], draft:[[2026-07-01 - f2]]", "",       # 같은 날 2 source 로 태어남 — 제외
    ])
    (sb.tmp / "corpus" / "a-mistakes.md").write_text(nodes, encoding="utf-8")
    out = cards(sb, "z", date="2026-07-09")[1]
    assert "2/4 (0.50)" in out  # 기본은 코호트 없음 — D 도 센다
    # 코호트는 상수라 모듈을 불러 바꾼 뒤 main 을 부른다
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import ledger; ledger.RECUR_COHORT = '2026-07-01'; "
            "sys.exit(ledger.main(sys.argv[2:]))")
    p = subprocess.run([sys.executable, "-c", code, str(LEDGER_PY.parent), "cards", "--slug", "z",
                        "--date", "2026-07-09", "--project", "t"], env=sb.env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    assert p.returncode == 0 and "1/3 (0.33, 2026-07-01~ 코호트)" in p.stdout


def test_leaks_separates_content_from_pointers(sb):
    (sb.home / "hooks").mkdir()
    (sb.home / "hooks" / "h.py").write_text("# alpha 를 강제\n", encoding="utf-8")
    (sb.home / "projects" / "p" / "memory" / "m.md").write_text("alpha 참고\n", encoding="utf-8")
    proj = sb.tmp / "projects" / "x"
    proj.mkdir(parents=True)
    (proj / "CLAUDE.md").write_text("알파 규칙을 지킨다 를 따른다\n", encoding="utf-8")
    ex = sb.home / "skills" / "session-retro" / "examples"
    ex.mkdir(parents=True)
    (ex / "run.md").write_text("alpha 실출력\n", encoding="utf-8")
    code, out, _ = run(sb, "leaks", "alpha")
    assert code == 0 and "내용을 싣는 자리 2건" in out and "이름 포인터 1건" in out and "examples" not in out


# ---------- 선택 폴더가 없을 때: "없음" 이 아니라 "안 봤다" ----------

def unset(sb, *names):
    for n in names:
        sb.env.pop(n)


def test_coverage_without_seal_dir_omits_sealed_count(sb):
    unset(sb, "SESSION_SEAL_DIR")
    background(sb)
    slug = sessions(sb, "alpha", ["작동"] * 8)
    rows = row_for(cards(sb, slug)[1], "alpha")
    assert "2026-10-01~ 회고 38" in rows[0] and "sealed" not in rows[0]


def policy_line(out):
    return [line for line in out.splitlines() if line.startswith("더하기 정책 참고")]


def test_recur_rate_without_corpus_says_so(sb):
    unset(sb, "SESSION_RETRO_CORPUS")
    code, out, _ = cards(sb, "x")
    line = policy_line(out)
    assert code == 0 and len(line) == 1 and "코퍼스 미설정" in line[0] and "표본 없음" not in line[0]


def test_recur_rate_with_empty_corpus_is_no_sample(sb):
    code, out, _ = cards(sb, "x")
    line = policy_line(out)
    assert code == 0 and len(line) == 1 and "표본 없음" in line[0] and "미설정" not in line[0]


def test_leaks_without_projects_says_what_it_skipped(sb):
    proj = sb.tmp / "projects" / "x"
    proj.mkdir(parents=True)
    (proj / "CLAUDE.md").write_text("alpha 를 따른다\n", encoding="utf-8")
    unset(sb, "SESSION_RETRO_PROJECTS")
    code, out, _ = run(sb, "leaks", "alpha")
    assert code == 0 and "SESSION_RETRO_PROJECTS 미설정" in out and "내용을 싣는 자리 0건" in out


def test_default_ledger_lives_under_claude_home(sb):
    unset(sb, "SESSION_RETRO_DIR")
    assert add(sb, "a", [{"rule": "alpha", "verdict": "작동", "note": "x"}])[0] == 0
    assert (sb.home / "session-retro-ko" / "verdicts.csv").is_file()


# ---------- 종료 코드: 도구 실패는 위반(3)과 다르다 ----------

@pytest.mark.parametrize("text", ["a,b,c\n1,2,3\n",
                                  "seq,kind,date,project,slug,rule,state,rev,verdict,note,src\n1,obs,d,p,s,alpha,loaded,r,작동,n,retro,EXTRA\n"])
def test_corrupt_ledger_is_tool_failure_not_violation(sb, text):
    sb.ledger.write_text(text, encoding="utf-8")
    code, _, _ = cards(sb, "x")
    assert code not in (0, 3)
