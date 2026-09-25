#!/usr/bin/env python3
"""session-retro ledger — records and counts verdicts only. The retro (an LLM) makes the judgment call; this script never judges.

State is derived from the real world:
  rule state = file location (rules/ · rules-probation/ · rules-archive/)
  rule revision (rev) = hash of the file's contents
Only this script writes the ledger (verdicts.csv) (append-only).

All probabilities are counted from the ledger: baseline failure rate p = session-level failure ratio of loaded rules.
  isolate P = probability an average rule(p) works for k consecutive sessions in the window = (1-p)^k
  fix-or-drop P = probability an average rule(p) fails at least this many times in the window = binomial upper tail

Exit codes: 0 = pass · 3 = violation (fix the input and rerun) · anything else = tool failure (do not touch the ledger, report to the user).
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

# ---- Thresholds: this block is the single authority. SKILL.md only points to it by name ----
ISOLATE_P = 0.10           # propose isolate: window has 0 failures and the probability an average rule works that long in a row is below this
FIX_P = 0.10               # propose fix-or-drop: probability an average rule fails at least this much is below this
MIN_SESSIONS = 3           # neither isolate nor fix-or-drop is proposed if the window has fewer sessions than this
ARCHIVE_AFTER = 3          # propose archive: minimum worked-session count in the isolation window (since the last restore rejection), together with 0 failures
RARE_WINDOW = 15           # rarely-relevant: number of recent retros
RARE_MAX = 1               # rarely-relevant: max number of relevant sessions among those retros
RARE_CHARS = 1500          # rarely-relevant: minimum rule size (chars)
SUPPRESS_SESSIONS = 3      # number of new relevant sessions needed before the same card proposal can be raised again after a gate decision (accept·reject)
FAIL_NOTES = 3             # number of failure notes attached below fix-or-drop · restore rows
RECUR_COHORT = ""          # recurrence-rate cohort start date YYYY-MM-DD — nodes born before it are excluded (if the corpus started with a bulk harvest, use the day after). Empty = all
RECUR_HORIZON = 5          # recurrence-rate horizon (number of retros)

EXIT_OK, EXIT_VIOLATION = 0, 3


def optional_dir(name):
    v = os.environ.get(name)
    return Path(v).expanduser() if v else None


HOME = Path(os.environ.get("RETRO_CLAUDE_HOME", Path.home() / ".claude"))  # for test sandboxing
# stored verdict values are language-specific, so each variant keeps its own folder instead of mixing this ledger with the Korean one's
LEDGER = Path(os.environ.get("SESSION_RETRO_DIR", HOME / "session-retro")).expanduser() / "verdicts.csv"
SESSIONS = optional_dir("SESSION_SEAL_DIR")         # sealed snapshot folder — if set, coverage counts sealed sessions
CORPUS = optional_dir("SESSION_RETRO_CORPUS")       # folder of the 5-category node files — if set, recurrence rate is computed
PROJECTS = optional_dir("SESSION_RETRO_PROJECTS")   # parent folder of projects — if set, leaks also checks */CLAUDE.md
DIRS = {"loaded": HOME / "rules", "probation": HOME / "rules-probation", "archived": HOME / "rules-archive"}

FIELDS = ["seq", "kind", "date", "project", "slug", "rule", "state", "rev", "verdict", "note", "src"]
OBS = ("worked", "partly-worked", "did-not-work", "irrelevant")
FAIL = {"partly-worked", "did-not-work"}
RANK = {"did-not-work": 3, "partly-worked": 2, "worked": 1, "irrelevant": 0}
# proposal values = card labels = gate --proposal values. Proposals that move files: (required state | None=probation·archived, destination state)
PROPOSALS = ("isolate", "rarely-relevant", "fix-or-drop", "restore", "archive")
MOVES = {"isolate": ("loaded", "probation"), "rarely-relevant": ("loaded", "probation"),
         "restore": (None, "loaded"), "archive": ("probation", "archived")}
NAME_RE = re.compile(r"^[\w.-]+$")


class Violation(Exception):
    pass


# ---------- Real-world lookups ----------

def listing(state):
    d = DIRS[state]
    return {p.stem: p for p in d.glob("*.md")} if d.is_dir() else {}


def locate(rule):
    """rule stem → (state, path). Must match the filename exactly, including case. (None, None) if not found."""
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
            raise Violation(f"no such memory slug: {rule} (no project memory has {slug}.md)")
        return None, None
    if not NAME_RE.match(rule):
        raise Violation(f"not a valid rule name: {rule!r}")
    state, path = locate(rule)
    if state is None:
        raise Violation(f"no such rule file: {rule} (rules/ · rules-probation/ · rules-archive/ has no {rule}.md)")
    return state, path


def check_date(s):
    try:
        return dt.date.fromisoformat(s).isoformat()
    except ValueError:
        raise Violation(f"--date must be YYYY-MM-DD: {s!r}")


# ---------- Ledger I/O ----------

def read_ledger():
    if not LEDGER.exists() or LEDGER.stat().st_size == 0:
        return []
    with LEDGER.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        if r.fieldnames != FIELDS:
            raise RuntimeError(f"ledger header does not match the spec: {r.fieldnames}")
        rows = []
        for i, row in enumerate(r, start=2):
            if None in row or any(v is None for v in row.values()):
                raise RuntimeError(f"ledger row {i} does not have {len(FIELDS)} fields")
            row["seq"] = int(row["seq"])
            rows.append(row)
    return rows


def open_for_append():
    """(file handle, writer, last seq). Raises here if unwritable — used to check before moving a file."""
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


# ---------- Session-level aggregation ----------

def key_of(row):
    return (row["date"], row["project"], row["slug"])


def timeline(rows):
    """Retro session keys, in order of first appearance."""
    seen, out = set(), []
    for r in rows:
        if r["kind"] == "obs" and key_of(r) not in seen:
            seen.add(key_of(r))
            out.append(key_of(r))
    return out


def sessions_of(rows, rule):
    """rule's obs rows grouped by session — rows sharing (session key, state, revision) collapse to a single worst verdict. A different revision is a different observation."""
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
    """The tail of sessions, from the end, that share the current (state, rev)."""
    out = []
    for s in reversed(sess):
        if (s["state"], s["rev"]) != (state, rev):
            break
        out.append(s)
    return out[::-1]


def tally(sess):
    c = Counter(s["verdict"] for s in sess)
    return c["worked"], c["partly-worked"] + c["did-not-work"], c["irrelevant"]


def gates_of(rows, rule, proposal):
    return [r for r in rows if r["kind"] == "gate" and r["rule"] == rule and r["verdict"].split(":")[0] == proposal]


def moved_in(rows, rule, me):
    """The first gate(accept) that moved the file under this session key. If present, this session had the file loaded in its pre-move state."""
    g = [r for r in rows if r["kind"] == "gate" and r["rule"] == rule and key_of(r) == me
         and r["verdict"].split(":")[0] in MOVES and r["verdict"].endswith(":accept")]
    return g[0] if g else None


def last_move(rows, rule):
    """seq of the last gate(accept) that moved the file — the window starts right after it."""
    return max((r["seq"] for r in rows if r["kind"] == "gate" and r["rule"] == rule
                and r["verdict"].split(":")[0] in MOVES and r["verdict"].endswith(":accept")), default=0)


def suppressed(rows, sess, rule, proposal):
    """Suppressed if a gate decision (accept·reject) has already been made for the same proposal and fewer than
    SUPPRESS_SESSIONS new relevant sessions have followed it. (suppressed?, rejection count)"""
    g = gates_of(rows, rule, proposal)
    nrej = sum(1 for r in g if r["verdict"].endswith(":reject"))
    if not g:
        return False, 0
    after = [s for s in sess if s["seq"] > g[-1]["seq"] and s["verdict"] != "irrelevant"]
    return len(after) < SUPPRESS_SESSIONS, nrej


def base_rate(rows):
    """Session-level failure rate of loaded rules (memory excluded). (failures, total)"""
    fail = total = 0
    for rule in {r["rule"] for r in rows if r["kind"] == "obs" and not r["rule"].startswith("memory:")}:
        for s in sessions_of(rows, rule):
            if s["state"] == "loaded" and s["verdict"] != "irrelevant":
                total += 1
                fail += s["verdict"] in FAIL
    return fail, total


def upper_tail(k, f, p):
    """Probability an average rule (failure rate p) fails at least f times in k sessions."""
    return sum(math.comb(k, i) * p ** i * (1 - p) ** (k - i) for i in range(f, k + 1))


def sealed_since(date):
    """None if SESSION_SEAL_DIR is not set — counting only some of the snapshots scattered across projects would throw the retro count and the denominator out of step."""
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
        return "no observations"
    start = sess[0]["date"]
    retros = sum(1 for k in timeline(rows) if k[0] >= start)
    sealed = sealed_since(start)
    return f"{start}~ " + (f"sealed {sealed} · " if sealed is not None else "") + f"retros {retros}"


def history(rows, rule, sess):
    isolations = sum(1 for r in gates_of(rows, rule, "isolate") + gates_of(rows, rule, "rarely-relevant")
                     if r["verdict"].endswith(":accept"))
    pfail = sum(1 for s in sess if s["state"] == "probation" and s["verdict"] in FAIL)
    return f"isolated {isolations}× · failures while isolated {pfail}" if isolations else ""


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


# ---------- Commands ----------

def cmd_add(a):
    date = check_date(a.date)
    if not NAME_RE.match(a.slug):
        raise Violation("--slug is letters/digits/-_. only (a short tag for the session)")
    rows = read_ledger()
    me = (date, a.project, a.slug)
    if not a.append and any(key_of(r) == me for r in rows):
        raise Violation(f"session key {me} is already in the ledger — use a different --slug, or --append if this is more rows for the same retro")
    try:
        data = json.loads(Path(a.file).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        raise Violation(f"could not read the rows file as JSON: {e}")
    if not isinstance(data, list) or not data or not all(isinstance(d, dict) for d in data):
        raise Violation("the rows file must be a non-empty JSON array of objects")
    errs, out = [], []
    for i, d in enumerate(data, start=1):
        try:
            rule, verdict, note = str(d.get("rule", "")).strip(), str(d.get("verdict", "")).strip(), one_line(d.get("note", ""))
            state, path = check_name(rule)
            if verdict not in OBS:
                raise Violation(f"verdict must be one of {'/'.join(OBS)} — got {verdict!r} (put commentary in note)")
            if path is None:
                state, rev = "loaded", ""
            elif mg := moved_in(rows, rule, me):
                state, rev = mg["state"], mg["rev"]
            else:
                rev = rev_of(path)
            if verdict == "irrelevant" and state != "probation":
                raise Violation("'irrelevant' is only for rules under isolation (loaded rules skip the row if irrelevant)")
            if not note:
                raise Violation("note (event anchor) is empty")
            out.append({"kind": "obs", "date": date, "project": a.project, "slug": a.slug, "rule": rule,
                        "state": state, "rev": rev, "verdict": verdict, "note": note, "src": "retro"})
        except Violation as e:
            errs.append(f"  row {i}: {e}")
    if errs:
        raise Violation("wrote nothing to the ledger:\n" + "\n".join(errs))
    seq = append_rows(out)
    print(f"added {len(out)} rows (last seq {seq})")


def cmd_gate(a):
    date = check_date(a.date)
    if a.proposal not in PROPOSALS:
        raise Violation(f"--proposal must be one of {'/'.join(PROPOSALS)} (the card's proposal column value, verbatim)")
    if a.decision not in ("accept", "reject"):
        raise Violation("--decision must be accept/reject")
    if not one_line(a.note):
        raise Violation("--note (decision rationale) is empty")
    state, path = check_name(a.rule)
    if path is None:
        raise Violation("gate only applies to rules files (memory is not a target)")
    dest = None
    if a.decision == "accept" and a.proposal in MOVES:
        need, to = MOVES[a.proposal]
        ok = state == need if need else state in ("probation", "archived")
        if not ok:
            raise Violation(f"{a.proposal} only applies from state {need or 'probation/archived'} — currently {state}")
        dest = DIRS[to] / path.name
        if dest.exists():
            raise Violation(f"move destination already exists: {dest}")
    row = {"kind": "gate", "date": date, "project": a.project, "slug": a.slug, "rule": a.rule, "state": state,
           "rev": rev_of(path), "verdict": f"{a.proposal}:{a.decision}", "note": one_line(a.note), "src": "retro"}
    f, w, seq = open_for_append()  # fails here, before moving anything, if the ledger is unwritable
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
        raise Violation("stats only applies to rules files")
    _, _, sess, win, older = rule_line(rows, a.rule)
    w_ok, w_fail, _ = tally(win)
    o_ok, o_fail, _ = tally(older)
    print(join(f"{a.rule}: {state}", f"{chars_of(path)} chars", f"current rev worked {w_ok}/{w_ok + w_fail}",
               f"previous rev (while loaded) worked {o_ok}/{o_ok + o_fail}", history(rows, a.rule, sess)))


def recur_rate(rows):
    """Share of single-observation corpus nodes that gained another source within the next RECUR_HORIZON retros
    (node files directly, nodes outside the horizon excluded). None if SESSION_RETRO_CORPUS is not set."""
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
        raise Violation("isolated rules have no verdict row for this session (one row even if irrelevant): " + ", ".join(missing))

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
        prev = f"previous rev worked {o_ok}/{o_ok + o_fail}"
        hist = history(rows, rule, sess)
        rel_recent = sum(1 for s in sess if s["key"] in recent and s["verdict"] != "irrelevant")
        rare = (len(recent) >= RARE_WINDOW and sess[0]["key"] not in recent
                and rel_recent <= RARE_MAX and size >= RARE_CHARS)
        rare_note = f"relevant in {rel_recent} of the last {RARE_WINDOW} retros"
        if p is not None and k >= MIN_SESSIONS:
            if w_fail == 0 and (1 - p) ** k < ISOLATE_P:
                sup, nrej = suppressed(rows, win, rule, "isolate")
                if not sup:
                    out.append((rule, "isolate", join(f"current rev worked {k}/{k}", f"P={(1 - p) ** k:.2g} for an average rule",
                                                   prev, coverage(rows, win), hist, f"rejected {nrej}×" if nrej else ""), size))
                    continue
            tail = upper_tail(k, w_fail, p)
            if w_fail and tail < FIX_P:
                sup, nrej = suppressed(rows, win, rule, "fix-or-drop")
                if not sup:
                    out.append((rule, "fix-or-drop", join(f"current rev failed {w_fail}/{k}", f"P={tail:.2g} for an average rule",
                                                       prev, rare_note if rare else "", hist,
                                                       f"rejected {nrej}×" if nrej else ""), size))
                    notes[rule] = fail_notes(win)
                    continue
        if rare:
            sup, nrej = suppressed(rows, sess, rule, "rarely-relevant")
            if not sup:
                out.append((rule, "rarely-relevant", join(rare_note, "isolate or move to a project layer", hist,
                                                  f"rejected {nrej}×" if nrej else ""), size))

    for rule in rule_files("probation"):
        state, path, sess, win, _ = rule_line(rows, rule)
        size = chars_of(path)
        rejects = [r["seq"] for r in gates_of(rows, rule, "restore") if r["verdict"].endswith(":reject")]
        fresh = [s for s in win if s["seq"] > (rejects[-1] if rejects else 0)]
        f_ok, f_fail, _ = tally(fresh)
        w_ok, w_fail, w_na = tally(win)
        before = [s for s in sess if s["state"] == "loaded" and s["rev"] == rev_of(path)]
        b_ok, b_fail, _ = tally(before)
        base = join(f"without it {w_ok}/{w_ok + w_fail}", f"while loaded {b_ok}/{b_ok + b_fail}", f"irrelevant {w_na}",
                    coverage(rows, win), history(rows, rule, sess))
        asup, anrej = suppressed(rows, win, rule, "archive")
        if f_fail:
            out.append((rule, "restore", join(f"failed while isolated {f_fail}", base), size))
            notes[rule] = fail_notes(fresh)
        elif f_ok >= ARCHIVE_AFTER and not asup:
            out.append((rule, "archive", join(base, f"rejected {anrej}×" if anrej else ""), size))
        else:
            mine = [s for s in win if s["key"] == me and s["verdict"] != "irrelevant"]
            watch.append(f"`{rule}` {base}" if mine else None)

    for rule in rule_files("archived"):
        _, path, sess, _, _ = rule_line(rows, rule)
        now = [s for s in sess if s["key"] == me and s["verdict"] in FAIL]
        if now:
            out.append((rule, "restore", "an archived rule's behaviour failed this session", chars_of(path)))
            notes[rule] = fail_notes(now)

    print("### Remove")
    print(f"Baseline: loaded-rule session failures {bf}/{bn}" + (f" (p={p:.2f})" if p is not None else " — no sample, no probability proposals"))
    if out:
        print("\n| # | rule | proposal | evidence | chars |")
        print("|---|---|---|---|---|")
        for i, (rule, prop, why, size) in enumerate(out, 1):
            print(f"| {i} | `{rule}` | {prop} | {why} | {size} |")
        lines = [f"- failure behind {i}: {n}" for i, (rule, _, _, _) in enumerate(out, 1) for n in notes.get(rule, [])]
        if lines:
            print("\n" + "\n".join(lines))
    else:
        print(f"\nNone (read {len(rows)} ledger rows · {len(timeline(rows))} retros)")
    shown = [w for w in watch if w]
    if watch:
        print(f"\n{len(watch)} isolated" + (" — relevant this session: " + " / ".join(shown) if shown else " · no change this session"))
    if unscored:
        print(f"\n{len(unscored)} rules with no verdicts yet · {sum(s for _, s in unscored)} chars total: "
              + ", ".join(f"`{r}`" for r, _ in unscored))
    recur = recur_rate(rows)
    head = "\nAdd-policy reference (not a per-candidate probability) — "
    if recur is None:
        print(head + "corpus not configured (SESSION_RETRO_CORPUS) — single-source node recurrence was not counted")
    else:
        hit, n = recur
        cohort = f", {RECUR_COHORT}~ cohort" if RECUR_COHORT else ""
        print(head + f"share of single-source nodes recorded again within the next {RECUR_HORIZON} retros: "
              + (f"{hit}/{n} ({hit / n:.2f}{cohort})" if n else "no sample"))


def cmd_leaks(a):
    state, path = check_name(a.rule)
    if path is None:
        raise Violation("leaks only applies to rules files")
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
    print(f"# {a.rule} leaks — patterns {pats}")
    if PROJECTS is None:
        print("project CLAUDE.md files were not scanned (SESSION_RETRO_PROJECTS not set) — check those yourself")
    print(f"\n## Places that carry content: {len(carrying)} (decide whether to keep or fix before isolating)")
    for x in carrying:
        print("  " + x)
    print(f"\n## Name pointers: {len(pointer)} (listing only — fix them if they are session-retro's current guidance)")
    for x in pointer:
        print("  " + x)


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="ledger.py", description="session-retro ledger")
    sub = p.add_subparsers(dest="cmd", required=True)

    def session_args(sp):
        sp.add_argument("--slug", required=True, help="short tag for this retro's session (letters/digits/-_.)")
        sp.add_argument("--date", default=dt.date.today().isoformat())
        sp.add_argument("--project", default=Path.cwd().name)

    sp = sub.add_parser("add"); session_args(sp); sp.add_argument("--file", required=True)
    sp.add_argument("--append", action="store_true", help="more rows for the same retro (allows reusing the session key)")
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
        print(f"violation: {e}", file=sys.stderr)
        return EXIT_VIOLATION
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
