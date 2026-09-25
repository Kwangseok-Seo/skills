#!/usr/bin/env python3
"""session-retro 원장 — 판정을 기록하고 세기만 한다. 판정은 회고(LLM)가 하고, 이 스크립트는 판단하지 않는다.

상태는 실물에서 도출한다:
  rule 상태 = 파일 위치 (rules/ · rules-probation/ · rules-archive/)
  rule 판(rev) = 파일 내용 해시
원장(verdicts.csv)은 이 스크립트만 쓴다 (append-only).

확률은 전부 원장에서 센다: 기준 실패율 p = 실린 rule 들의 세션 단위 실패 비율.
  격리 P = 평균 rule(p)이 창 길이만큼 연속 작동할 확률 = (1-p)^k
  고치거나빼기 P = 평균 rule(p)이 창에서 이만큼 이상 실패할 확률 = 이항 상측 꼬리

종료 코드: 0 = 통과 · 3 = 위반(입력을 고쳐 다시 실행) · 그 외 = 도구 실패(원장을 고치지 말고 사용자에게 보고).
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

# ---- 임계값: 이 블록이 단일 권위다. SKILL.md 는 이름으로만 가리킨다 ----
ISOLATE_P = 0.10           # 격리 제안: 창 실패 0 이고 평균 rule 이 그만큼 연속 작동할 확률이 이보다 작을 때
FIX_P = 0.10               # 고치거나빼기 제안: 평균 rule 이 그만큼 이상 실패할 확률이 이보다 작을 때
MIN_SESSIONS = 3           # 격리·고치거나빼기 모두 창 세션 수가 이보다 적으면 제안하지 않는다
ARCHIVE_AFTER = 3          # 보관 제안: 격리 창(마지막 복귀 반려 이후)의 작동 세션 수 하한, 실패 0 과 함께
RARE_WINDOW = 15           # 관련드묾: 최근 회고 수
RARE_MAX = 1               # 관련드묾: 그 회고들 중 관련 세션 수 상한
RARE_CHARS = 1500          # 관련드묾: rule 크기 하한 (chars)
SUPPRESS_SESSIONS = 3      # 빼기 제안에 gate 결정(accept·reject)이 난 뒤, 같은 제안을 다시 내기까지 필요한 새 관련 세션 수
FAIL_NOTES = 3             # 고치거나빼기·복귀 행 아래 붙이는 실패 사건 수
RECUR_COHORT = ""          # 재기록률 코호트 시작일 YYYY-MM-DD — 그 전에 태어난 노드는 뺀다 (코퍼스를 일괄 수확으로 시작했다면 그 다음 날). 빈 값 = 전부
RECUR_HORIZON = 5          # 재기록률 지평 (회고 수)

EXIT_OK, EXIT_VIOLATION = 0, 3


def optional_dir(name):
    v = os.environ.get(name)
    return Path(v).expanduser() if v else None


HOME = Path(os.environ.get("RETRO_CLAUDE_HOME", Path.home() / ".claude"))  # 테스트 샌드박스용
# 판정값이 한국어로 저장되므로 영어판과 원장을 나누지 않도록 변형별 폴더를 쓴다
LEDGER = Path(os.environ.get("SESSION_RETRO_DIR", HOME / "session-retro-ko")).expanduser() / "verdicts.csv"
SESSIONS = optional_dir("SESSION_SEAL_DIR")         # sealed 스냅샷 폴더 — 있으면 coverage 가 sealed 수를 센다
CORPUS = optional_dir("SESSION_RETRO_CORPUS")       # 5범주 노드 파일 폴더 — 있으면 재기록률을 낸다
PROJECTS = optional_dir("SESSION_RETRO_PROJECTS")   # 프로젝트들의 부모 폴더 — 있으면 leaks 가 */CLAUDE.md 를 본다
DIRS = {"loaded": HOME / "rules", "probation": HOME / "rules-probation", "archived": HOME / "rules-archive"}

FIELDS = ["seq", "kind", "date", "project", "slug", "rule", "state", "rev", "verdict", "note", "src"]
OBS = ("작동", "부분작동", "미작동", "무관")
FAIL = {"부분작동", "미작동"}
RANK = {"미작동": 3, "부분작동": 2, "작동": 1, "무관": 0}
# 제안 값 = 카드 라벨 = gate --proposal 값. 이동하는 제안: (필요 상태 | None=probation·archived, 목적 상태)
PROPOSALS = ("격리", "관련드묾", "고치거나빼기", "복귀", "보관")
MOVES = {"격리": ("loaded", "probation"), "관련드묾": ("loaded", "probation"),
         "복귀": (None, "loaded"), "보관": ("probation", "archived")}
NAME_RE = re.compile(r"^[\w.-]+$")


class Violation(Exception):
    pass


# ---------- 실물 조회 ----------

def listing(state):
    d = DIRS[state]
    return {p.stem: p for p in d.glob("*.md")} if d.is_dir() else {}


def locate(rule):
    """rule stem → (state, path). 대소문자까지 파일 이름과 같아야 한다. 없으면 (None, None)."""
    for state in DIRS:
        p = listing(state).get(rule)
        if p is not None:
            return state, p
    return None, None


def memory_exists(slug):
    return any(p.stem == slug for p in (HOME / "projects").glob("*/memory/*.md"))


def rev_of(path):
    return hashlib.sha1(path.read_bytes()).hexdigest()[:10]


def chars_of(path):
    return len(path.read_text(encoding="utf-8"))


def rule_files(state):
    return sorted(listing(state))


def check_name(rule):
    if rule.startswith("memory:"):
        slug = rule[7:]
        if not NAME_RE.match(slug) or not memory_exists(slug):
            raise Violation(f"memory slug 없음: {rule} (어느 프로젝트 memory 에도 {slug}.md 가 없다)")
        return None, None
    if not NAME_RE.match(rule):
        raise Violation(f"rule 이름 형식이 아니다: {rule!r}")
    state, path = locate(rule)
    if state is None:
        raise Violation(f"rule 파일 없음: {rule} (rules/ · rules-probation/ · rules-archive/ 에 정확히 {rule}.md 가 없다)")
    return state, path


def check_date(s):
    try:
        return dt.date.fromisoformat(s).isoformat()
    except ValueError:
        raise Violation(f"--date 는 YYYY-MM-DD: {s!r}")


# ---------- 원장 입출력 ----------

def read_ledger():
    if not LEDGER.exists() or LEDGER.stat().st_size == 0:
        return []
    with LEDGER.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        if r.fieldnames != FIELDS:
            raise RuntimeError(f"원장 헤더가 규격과 다르다: {r.fieldnames}")
        rows = []
        for i, row in enumerate(r, start=2):
            if None in row or any(v is None for v in row.values()):
                raise RuntimeError(f"원장 {i}행 필드 수가 {len(FIELDS)} 가 아니다")
            row["seq"] = int(row["seq"])
            rows.append(row)
    return rows


def open_for_append():
    """(파일 핸들, writer, 마지막 seq). 쓸 수 없으면 여기서 예외 — 파일을 옮기기 전에 확인하는 용도."""
    old = read_ledger()
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    fresh = not LEDGER.exists() or LEDGER.stat().st_size == 0
    f = LEDGER.open("a", encoding="utf-8", newline="")
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if fresh:
        w.writeheader()
    return f, w, max((r["seq"] for r in old), default=0)


def append_rows(new):
    f, w, seq = open_for_append()
    with f:
        for row in new:
            seq += 1
            w.writerow({**row, "seq": seq})
    return seq


def one_line(s):
    return " ".join(str(s).split())


# ---------- 세션 단위 집계 ----------

def key_of(row):
    return (row["date"], row["project"], row["slug"])


def timeline(rows):
    """회고 세션 키를 처음 등장한 순서대로."""
    seen, out = set(), []
    for r in rows:
        if r["kind"] == "obs" and key_of(r) not in seen:
            seen.add(key_of(r))
            out.append(key_of(r))
    return out


def sessions_of(rows, rule):
    """rule 의 obs 를 세션 단위로 — (세션 키, 상태, 판)이 같은 행은 최악값 하나. 판이 다르면 다른 관측이다."""
    by, order = {}, []
    for r in rows:
        if r["kind"] != "obs" or r["rule"] != rule:
            continue
        k = key_of(r) + (r["state"], r["rev"])
        if k not in by:
            by[k] = {"key": key_of(r), "date": r["date"], "verdict": r["verdict"], "note": r["note"],
                     "state": r["state"], "rev": r["rev"], "seq": r["seq"]}
            order.append(k)
        else:
            s = by[k]
            if RANK[r["verdict"]] > RANK[s["verdict"]]:
                s["verdict"], s["note"] = r["verdict"], r["note"]
            s["seq"] = r["seq"]
    return [by[k] for k in order]


def window(sess, state, rev):
    """현재 (state, rev) 와 같은 세션이 끝에서부터 연속되는 꼬리."""
    out = []
    for s in reversed(sess):
        if (s["state"], s["rev"]) != (state, rev):
            break
        out.append(s)
    return out[::-1]


def tally(sess):
    c = Counter(s["verdict"] for s in sess)
    return c["작동"], c["부분작동"] + c["미작동"], c["무관"]


def gates_of(rows, rule, proposal):
    return [r for r in rows if r["kind"] == "gate" and r["rule"] == rule and r["verdict"].split(":")[0] == proposal]


def moved_in(rows, rule, me):
    """이번 세션 키에서 파일을 옮긴 첫 gate(accept). 있으면 이 세션엔 옮기기 전 상태로 실려 있었다."""
    g = [r for r in rows if r["kind"] == "gate" and r["rule"] == rule and key_of(r) == me
         and r["verdict"].split(":")[0] in MOVES and r["verdict"].endswith(":accept")]
    return g[0] if g else None


def last_move(rows, rule):
    """마지막으로 파일을 옮긴 gate(accept)의 seq — 창은 그 뒤부터."""
    return max((r["seq"] for r in rows if r["kind"] == "gate" and r["rule"] == rule
                and r["verdict"].split(":")[0] in MOVES and r["verdict"].endswith(":accept")), default=0)


def suppressed(rows, sess, rule, proposal):
    """같은 제안에 gate 결정(accept·reject)이 난 뒤 새 관련 세션이 SUPPRESS_SESSIONS 개 미만이면 억제.
    (억제 여부, 반려 횟수)"""
    g = gates_of(rows, rule, proposal)
    nrej = sum(1 for r in g if r["verdict"].endswith(":reject"))
    if not g:
        return False, 0
    after = [s for s in sess if s["seq"] > g[-1]["seq"] and s["verdict"] != "무관"]
    return len(after) < SUPPRESS_SESSIONS, nrej


def base_rate(rows):
    """실린 rule 들의 세션 단위 실패율 (memory 제외). (실패, 전체)"""
    fail = total = 0
    for rule in {r["rule"] for r in rows if r["kind"] == "obs" and not r["rule"].startswith("memory:")}:
        for s in sessions_of(rows, rule):
            if s["state"] == "loaded" and s["verdict"] != "무관":
                total += 1
                fail += s["verdict"] in FAIL
    return fail, total


def upper_tail(k, f, p):
    """평균 rule(실패율 p)이 k 세션에서 f 번 이상 실패할 확률."""
    return sum(math.comb(k, i) * p ** i * (1 - p) ** (k - i) for i in range(f, k + 1))


def sealed_since(date):
    """SESSION_SEAL_DIR 이 없으면 None — 프로젝트마다 흩어진 스냅샷을 일부만 세면 회고 수와 분모가 어긋난다."""
    if SESSIONS is None:
        return None
    n = 0
    for p in SESSIONS.rglob("*.md"):
        if p.name.endswith("-draft.md"):
            continue
        try:
            with p.open(encoding="utf-8", errors="replace") as f:
                head = f.read(1500)
        except OSError:
            continue
        m = re.search(r"^date:\s*(\d{4}-\d{2}-\d{2})", head, re.M)
        if "status: sealed" in head and m and m.group(1) >= date:
            n += 1
    return n


def coverage(rows, sess):
    if not sess:
        return "관측 없음"
    start = sess[0]["date"]
    retros = sum(1 for k in timeline(rows) if k[0] >= start)
    sealed = sealed_since(start)
    return f"{start}~ " + (f"sealed {sealed} · " if sealed is not None else "") + f"회고 {retros}"


def history(rows, rule, sess):
    isolations = sum(1 for r in gates_of(rows, rule, "격리") + gates_of(rows, rule, "관련드묾")
                     if r["verdict"].endswith(":accept"))
    pfail = sum(1 for s in sess if s["state"] == "probation" and s["verdict"] in FAIL)
    return f"격리 {isolations}회 · 격리 중 실패 {pfail}" if isolations else ""


def rule_line(rows, rule):
    state, path = locate(rule)
    sess = sessions_of(rows, rule)
    since = last_move(rows, rule)
    win = [s for s in window(sess, state, rev_of(path)) if s["seq"] > since]
    older = [s for s in sess if s not in win and s["state"] == "loaded"]
    return state, path, sess, win, older


def fail_notes(sess):
    return [one_line(s["note"].replace("**", ""))[:80] for s in sess if s["verdict"] in FAIL][-FAIL_NOTES:]


def join(*parts):
    return " · ".join(p for p in parts if p)


# ---------- 명령 ----------

def cmd_add(a):
    date = check_date(a.date)
    if not NAME_RE.match(a.slug):
        raise Violation("--slug 는 영문·숫자·-_. 만 (세션을 구분하는 가제)")
    rows = read_ledger()
    me = (date, a.project, a.slug)
    if not a.append and any(key_of(r) == me for r in rows):
        raise Violation(f"세션 키 {me} 가 원장에 이미 있다 — 다른 --slug 를 쓰거나, 같은 회고의 추가분이면 --append")
    try:
        data = json.loads(Path(a.file).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        raise Violation(f"rows 파일을 JSON 으로 읽지 못했다: {e}")
    if not isinstance(data, list) or not data or not all(isinstance(d, dict) for d in data):
        raise Violation("rows 파일은 객체들의 비어 있지 않은 JSON 배열이어야 한다")
    errs, out = [], []
    for i, d in enumerate(data, start=1):
        try:
            rule, verdict, note = str(d.get("rule", "")).strip(), str(d.get("verdict", "")).strip(), one_line(d.get("note", ""))
            state, path = check_name(rule)
            if verdict not in OBS:
                raise Violation(f"verdict 는 {'/'.join(OBS)} 중 하나 — 받은 값 {verdict!r} (주석은 note 에)")
            if path is None:
                state, rev = "loaded", ""
            elif mg := moved_in(rows, rule, me):
                state, rev = mg["state"], mg["rev"]
            else:
                rev = rev_of(path)
            if verdict == "무관" and state != "probation":
                raise Violation("'무관' 은 격리 중 rule 에만 쓴다 (실린 rule 은 무관이면 행을 쓰지 않는다)")
            if not note:
                raise Violation("note(사건 앵커)가 비었다")
            out.append({"kind": "obs", "date": date, "project": a.project, "slug": a.slug, "rule": rule,
                        "state": state, "rev": rev, "verdict": verdict, "note": note, "src": "retro"})
        except Violation as e:
            errs.append(f"  행 {i}: {e}")
    if errs:
        raise Violation("원장에 아무것도 쓰지 않았다:\n" + "\n".join(errs))
    seq = append_rows(out)
    print(f"{len(out)}행 추가 (마지막 seq {seq})")


def cmd_gate(a):
    date = check_date(a.date)
    if a.proposal not in PROPOSALS:
        raise Violation(f"--proposal 은 {'/'.join(PROPOSALS)} 중 하나 (카드의 제안 열 값 그대로)")
    if a.decision not in ("accept", "reject"):
        raise Violation("--decision 은 accept/reject")
    if not one_line(a.note):
        raise Violation("--note(결정 사유)가 비었다")
    state, path = check_name(a.rule)
    if path is None:
        raise Violation("gate 는 rules 파일에만 쓴다 (memory 는 대상 아님)")
    dest = None
    if a.decision == "accept" and a.proposal in MOVES:
        need, to = MOVES[a.proposal]
        ok = state == need if need else state in ("probation", "archived")
        if not ok:
            raise Violation(f"{a.proposal} 은 {need or 'probation/archived'} 상태에서만 — 지금 {state}")
        dest = DIRS[to] / path.name
        if dest.exists():
            raise Violation(f"이동 대상이 이미 있다: {dest}")
    row = {"kind": "gate", "date": date, "project": a.project, "slug": a.slug, "rule": a.rule, "state": state,
           "rev": rev_of(path), "verdict": f"{a.proposal}:{a.decision}", "note": one_line(a.note), "src": "retro"}
    f, w, seq = open_for_append()  # 쓸 수 없으면 옮기기 전에 여기서 실패한다
    with f:
        if dest is not None:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(dest))
        try:
            w.writerow({**row, "seq": seq + 1})
            f.flush()
        except BaseException:
            if dest is not None:
                shutil.move(str(dest), str(path))
            raise
    print(f"{a.rule}: {a.proposal}:{a.decision}" + (f" → {dest}" if dest else ""))


def cmd_stats(a):
    rows = read_ledger()
    state, path = check_name(a.rule)
    if path is None:
        raise Violation("stats 는 rules 파일에만")
    _, _, sess, win, older = rule_line(rows, a.rule)
    w_ok, w_fail, _ = tally(win)
    o_ok, o_fail, _ = tally(older)
    print(join(f"{a.rule}: {state}", f"{chars_of(path)} chars", f"현재 판 작동 {w_ok}/{w_ok + w_fail}",
               f"이전 판(실린 채) 작동 {o_ok}/{o_ok + o_fail}", history(rows, a.rule, sess)))


def recur_rate(rows):
    """1회 관측 코퍼스 노드가 다음 RECUR_HORIZON 회고 안에 source 를 하나 더 얻은 비율 (노드 파일 직접, 지평 밖은 제외).
    SESSION_RETRO_CORPUS 가 없으면 None."""
    if CORPUS is None:
        return None
    rdates = sorted(k[0] for k in timeline(rows))
    hit = n = 0
    for f in ("a-mistakes.md", "b-insights.md", "c-improvements.md", "d-deferred.md", "e-recurring.md"):
        p = CORPUS / f
        if not p.is_file():
            continue
        lines = p.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if not line.startswith("### "):
                continue
            src = None
            for j in range(i + 1, min(i + 12, len(lines))):
                if lines[j].startswith("### "):
                    break
                if lines[j].startswith("sources:"):
                    src = sorted(m.group(1) for m in re.finditer(r"\[\[(20\d\d-\d\d-\d\d)", lines[j]))
                    break
            if not src or src[0] < RECUR_COHORT or src.count(src[0]) > 1:
                continue
            later = [d for d in rdates if d > src[0]]
            if len(later) < RECUR_HORIZON:
                continue
            n += 1
            nxt = [d for d in src[1:] if d > src[0]]
            hit += bool(nxt) and nxt[0] <= later[RECUR_HORIZON - 1]
    return hit, n


def cmd_cards(a):
    date = check_date(a.date)
    rows = read_ledger()
    me = (date, a.project, a.slug)
    missing = [r for r in rule_files("probation") if not moved_in(rows, r, me)
               and not any(x["kind"] == "obs" and x["rule"] == r and key_of(x) == me for x in rows)]
    if missing:
        raise Violation("격리 중 rule 에 이번 세션 판정 행이 없다 (무관이어도 한 행): " + ", ".join(missing))

    bf, bn = base_rate(rows)
    p = bf / bn if bn else None
    out, notes, watch, unscored = [], {}, [], []
    recent = timeline(rows)[-RARE_WINDOW:]

    for rule in rule_files("loaded"):
        state, path, sess, win, older = rule_line(rows, rule)
        size = chars_of(path)
        if not sess:
            unscored.append((rule, size))
            continue
        w_ok, w_fail, _ = tally(win)
        k = w_ok + w_fail
        o_ok, o_fail, _ = tally(older)
        prev = f"이전 판 작동 {o_ok}/{o_ok + o_fail}"
        hist = history(rows, rule, sess)
        rel_recent = sum(1 for s in sess if s["key"] in recent and s["verdict"] != "무관")
        rare = (len(recent) >= RARE_WINDOW and sess[0]["key"] not in recent
                and rel_recent <= RARE_MAX and size >= RARE_CHARS)
        rare_note = f"최근 회고 {RARE_WINDOW}회 중 관련 {rel_recent}"
        if p is not None and k >= MIN_SESSIONS:
            if w_fail == 0 and (1 - p) ** k < ISOLATE_P:
                sup, nrej = suppressed(rows, win, rule, "격리")
                if not sup:
                    out.append((rule, "격리", join(f"현재 판 {k}/{k} 작동", f"평균 rule 이면 P={(1 - p) ** k:.2g}",
                                                   prev, coverage(rows, win), hist, f"{nrej}회 반려" if nrej else ""), size))
                    continue
            tail = upper_tail(k, w_fail, p)
            if w_fail and tail < FIX_P:
                sup, nrej = suppressed(rows, win, rule, "고치거나빼기")
                if not sup:
                    out.append((rule, "고치거나빼기", join(f"현재 판 실패 {w_fail}/{k}", f"평균 rule 이면 P={tail:.2g}",
                                                       prev, rare_note if rare else "", hist,
                                                       f"{nrej}회 반려" if nrej else ""), size))
                    notes[rule] = fail_notes(win)
                    continue
        if rare:
            sup, nrej = suppressed(rows, sess, rule, "관련드묾")
            if not sup:
                out.append((rule, "관련드묾", join(rare_note, "격리 또는 프로젝트 층 이전", hist,
                                                  f"{nrej}회 반려" if nrej else ""), size))

    for rule in rule_files("probation"):
        state, path, sess, win, _ = rule_line(rows, rule)
        size = chars_of(path)
        rejects = [r["seq"] for r in gates_of(rows, rule, "복귀") if r["verdict"].endswith(":reject")]
        fresh = [s for s in win if s["seq"] > (rejects[-1] if rejects else 0)]
        f_ok, f_fail, _ = tally(fresh)
        w_ok, w_fail, w_na = tally(win)
        before = [s for s in sess if s["state"] == "loaded" and s["rev"] == rev_of(path)]
        b_ok, b_fail, _ = tally(before)
        base = join(f"없이 {w_ok}/{w_ok + w_fail}", f"실린 채 {b_ok}/{b_ok + b_fail}", f"무관 {w_na}",
                    coverage(rows, win), history(rows, rule, sess))
        asup, anrej = suppressed(rows, win, rule, "보관")
        if f_fail:
            out.append((rule, "복귀", join(f"격리 중 실패 {f_fail}", base), size))
            notes[rule] = fail_notes(fresh)
        elif f_ok >= ARCHIVE_AFTER and not asup:
            out.append((rule, "보관", join(base, f"{anrej}회 반려" if anrej else ""), size))
        else:
            mine = [s for s in win if s["key"] == me and s["verdict"] != "무관"]
            watch.append(f"`{rule}` {base}" if mine else None)

    for rule in rule_files("archived"):
        _, path, sess, _, _ = rule_line(rows, rule)
        now = [s for s in sess if s["key"] == me and s["verdict"] in FAIL]
        if now:
            out.append((rule, "복귀", "보관 중 rule 의 행동이 이번 세션에 실패", chars_of(path)))
            notes[rule] = fail_notes(now)

    print("### 빼기")
    print(f"기준: 실린 rule 세션 실패 {bf}/{bn}" + (f" (p={p:.2f})" if p is not None else " — 표본 없음, 확률 제안 없음"))
    if out:
        print("\n| # | rule | 제안 | 근거 | chars |")
        print("|---|---|---|---|---|")
        for i, (rule, prop, why, size) in enumerate(out, 1):
            print(f"| {i} | `{rule}` | {prop} | {why} | {size} |")
        lines = [f"- {i}의 실패 사건: {n}" for i, (rule, _, _, _) in enumerate(out, 1) for n in notes.get(rule, [])]
        if lines:
            print("\n" + "\n".join(lines))
    else:
        print(f"\n없음 (원장 {len(rows)}행 · 회고 {len(timeline(rows))}회 읽음)")
    shown = [w for w in watch if w]
    if watch:
        print(f"\n격리 중 {len(watch)}개" + (" — 이번 세션 관련: " + " / ".join(shown) if shown else " · 이번 세션 변화 없음"))
    if unscored:
        print(f"\n채점 기록 없는 rule {len(unscored)}개 · 합계 {sum(s for _, s in unscored)} chars: "
              + ", ".join(f"`{r}`" for r, _ in unscored))
    recur = recur_rate(rows)
    head = "\n더하기 정책 참고 (후보별 확률 아님) — "
    if recur is None:
        print(head + "코퍼스 미설정 (SESSION_RETRO_CORPUS) — 1회 관측 노드의 재기록률을 세지 않았다")
    else:
        hit, n = recur
        cohort = f", {RECUR_COHORT}~ 코호트" if RECUR_COHORT else ""
        print(head + f"1회 관측 노드가 다음 {RECUR_HORIZON}회 회고 안에 다시 기록된 비율: "
              + (f"{hit}/{n} ({hit / n:.2f}{cohort})" if n else "표본 없음"))


def cmd_leaks(a):
    state, path = check_name(a.rule)
    if path is None:
        raise Violation("leaks 는 rules 파일에만")
    text = path.read_text(encoding="utf-8")
    first = text.splitlines()[0] if text else ""
    title = first.lstrip("# ").split(" — ")[0].strip()
    pats = [a.rule] + ([title] if len(title) >= 6 else [])
    roots = [HOME / "rules", HOME / "rules-probation", HOME / "hooks", HOME / "skills", HOME / "commands", HOME / "agents"]
    files = [p for r in roots if r.is_dir() for p in r.rglob("*") if p.is_file() and p.suffix in (".md", ".py", ".sh", ".json")]
    files += list((HOME / "projects").glob("*/memory/*.md")) + list(HOME.glob("*.md"))
    files += list(PROJECTS.glob("*/CLAUDE.md")) if PROJECTS else []
    carrying, pointer = [], []
    for p in files:
        if p.resolve() == path.resolve() or "examples" in p.parts:
            continue
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for n, line in enumerate(lines, 1):
            if any(x in line for x in pats):
                loc = f"{p}:{n}: {line.strip()[:120]}"
                heavy = "hooks" in p.parts or p.name in ("CLAUDE.md", "MEMORY.md")
                (carrying if heavy else pointer).append(loc)
    print(f"# {a.rule} 누수 — 패턴 {pats}")
    if PROJECTS is None:
        print("프로젝트 CLAUDE.md 는 보지 않았다 (SESSION_RETRO_PROJECTS 미설정) — 거기 실린 내용은 직접 확인한다")
    print(f"\n## 내용을 싣는 자리 {len(carrying)}건 (격리 전에 남길지/고칠지 결정)")
    for x in carrying:
        print("  " + x)
    print(f"\n## 이름 포인터 {len(pointer)}건 (목록만 — session-retro 의 현재 안내면 고친다)")
    for x in pointer:
        print("  " + x)


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="ledger.py", description="session-retro 원장")
    sub = p.add_subparsers(dest="cmd", required=True)

    def session_args(sp):
        sp.add_argument("--slug", required=True, help="이 회고의 세션 가제 (영문·숫자·-_.)")
        sp.add_argument("--date", default=dt.date.today().isoformat())
        sp.add_argument("--project", default=Path.cwd().name)

    sp = sub.add_parser("add"); session_args(sp); sp.add_argument("--file", required=True)
    sp.add_argument("--append", action="store_true", help="같은 회고의 추가분 (세션 키 재사용 허용)")
    sp.set_defaults(fn=cmd_add)
    sp = sub.add_parser("cards"); session_args(sp); sp.set_defaults(fn=cmd_cards)
    sp = sub.add_parser("gate"); session_args(sp)
    for x in ("--rule", "--proposal", "--decision", "--note"):
        sp.add_argument(x, required=True)
    sp.set_defaults(fn=cmd_gate)
    sp = sub.add_parser("stats"); sp.add_argument("rule"); sp.set_defaults(fn=cmd_stats)
    sp = sub.add_parser("leaks"); sp.add_argument("rule"); sp.set_defaults(fn=cmd_leaks)

    a = p.parse_args(argv)
    try:
        a.fn(a)
    except Violation as e:
        print(f"위반: {e}", file=sys.stderr)
        return EXIT_VIOLATION
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
