---
name: dream-ko
description: "메모리 통합 pass — `~/.claude/memory/` 파일들에 대한 reflective reorganize. 최근 transcripts·기존 메모리를 종합해 새 신호를 topic 파일에 병합하고, 모순/노후 항목을 정리하고, MEMORY.md 인덱스를 다듬는다. Args: (없음) = 현재 프로젝트 메모리; `user` = `~/.claude/memory/` user-scope 메모리; `all` = user-scope + 모든 프로젝트 메모리. 사용 시점: 사용자가 '메모리 정리해줘', 'dream', '메모리 통합', '메모리 재정리', '인덱스 정돈' 이라고 말할 때."
---

# Dream: 메모리 통합

당신은 **dream** — 메모리 파일들에 대한 reflective pass — 을 수행한다. 최근 학습한 것을 미래 세션이 빠르게 orient 할 수 있도록 **내구성 있고 잘 조직된 메모리** 로 합성한다.

이 skill 은 표준 Claude Code 메모리 레이아웃 (user-scope = `~/.claude/memory/`, project-scope = `~/.claude/projects/<project-id>/memory/`) 과 아래 정의된 4 가지 메모리 타입을 가정한다. 대상 메모리 디렉토리가 없으면 작성 전에 생성한다.

---

## 메모리 스키마 (전 phase 공통 참조)

메모리 파일은 frontmatter 가 있는 markdown. 4 타입:

| 타입        | 저장 대상                                                              | 본문 규약                                                       |
|-------------|------------------------------------------------------------------------|-----------------------------------------------------------------|
| `user`      | 사용자의 역할·목표·지식·선호                                          | 자유 산문                                                       |
| `feedback`  | 작업 방식에 대한 사용자 가이드 — 정정 + 검증된 접근 모두                | 규칙 한 줄 → **Why:** + **How to apply:** 라인                  |
| `project`   | 이 프로젝트 고유 이니셔티브·마감·동기                                  | 사실 한 줄 → **Why:** + **How to apply:** 라인                  |
| `reference` | 외부 시스템 포인터 (Linear 프로젝트, Slack 채널, 대시보드 등)          | 자유 산문                                                       |

각 메모리 파일:

```markdown
---
name: {짧은 슬러그}
description: {한 줄 — 후속 세션에서 관련성 lookup 에 쓰임. 구체적으로}
type: user | feedback | project | reference
---

{본문}
```

해당 디렉토리의 `MEMORY.md` 는 frontmatter 없는 **flat 인덱스**, 메모리 파일 1개당 1줄:

```markdown
- [Title](file.md) — 한 줄 hook
```

`MEMORY.md` 는 ~200 줄 / ~25 KB 미만 유지. 메모리 본문 내용을 인덱스에 직접 쓰지 말 것.

---

## Args 분기 (호출 모드)

| Args     | 대상 MEMORY_DIR                                                | 대상 TRANSCRIPTS_DIR                                                  |
|----------|----------------------------------------------------------------|-----------------------------------------------------------------------|
| (없음)   | 현재 프로젝트의 메모리 디렉토리                                | 현재 프로젝트의 transcripts                                           |
| `user`   | `~/.claude/memory/` (없으면 생성)                              | 모든 프로젝트의 transcripts (cross-project 신호만)                    |
| `all`    | 위 `user` + 모든 프로젝트 메모리 디렉토리 각각 1회씩            | 각 모드의 자체 transcripts                                            |

**경로 규약**

- 프로젝트 transcript 디렉토리: `~/.claude/projects/<project-id>/*.jsonl`
- 프로젝트 메모리 디렉토리: `~/.claude/projects/<project-id>/memory/`
- `<project-id>` 는 Claude Code 가 세션을 기록할 때 작성한 식별자. `ls ~/.claude/projects/` 로 목록 확인.

**모드별 진입 규칙**

- **(없음)**: 현재 세션 cwd 에 해당하는 project-id 만 처리.
- **`user`**: `~/.claude/memory/` 가 없으면 빈 `MEMORY.md` 인덱스로 생성하고 시작. 이 모드에선 **프로젝트에 종속되지 않는 일반 신호** (사용자 정체성, 전역 선호, 도구 자산화 패턴 등) 만 user-scope 에 저장. 프로젝트 고유 사실은 user-scope 로 끌어올리지 말 것.
- **`all`**: 먼저 `user` 모드 1회 실행, 이어서 `~/.claude/projects/` 의 각 프로젝트에 대해 (없음) 모드와 동일 흐름을 1회씩 반복. 각 반복은 Phase 1~4 를 독립적으로 처리하고 자체 보고를 남긴다. 마지막에 합산 요약.

---

## Phase 1 — Orient (지향)

각 대상 MEMORY_DIR 에 대해:

- `ls <MEMORY_DIR>` 로 무엇이 이미 존재하는지 확인.
- `<MEMORY_DIR>/MEMORY.md` 를 읽어 현재 인덱스 파악.
- 기존 topic 파일들의 **frontmatter** (name / description / type) 만 빠르게 스캔. **본문 전수 읽기 금지** — 중복 작성 방지가 목적이지 재해석이 아님.

## Phase 2 — Gather recent signal (신호 수집)

저장할 가치가 있는 새 정보를 찾는다. 우선순위:

1. **최근 transcripts** — 대상 TRANSCRIPTS_DIR 의 `*.jsonl` 중 **수정시각이 가장 최근인 1~3 개** 만. JSONL 은 큰 파일이므로 grep 으로 좁게 — 전수 read 금지.

   bash:
   ```bash
   ls -t ~/.claude/projects/<project-id>/*.jsonl | head -3
   ```

   PowerShell:
   ```powershell
   Get-ChildItem ~/.claude/projects/<project-id>/*.jsonl |
     Sort-Object LastWriteTime -Descending | Select-Object -First 3
   ```

2. **drift 한 기존 메모리** — 코드/현실과 모순되는 사실. 가능하면 grep / Read 로 spot-check.

3. **좁은 키워드 grep** — 특정 사건이 떠오르면 그 키워드만 transcripts 에서 검색.
   ```bash
   grep -rn "<narrow term>" ~/.claude/projects/<project-id>/ --include="*.jsonl" | tail -50
   ```

전사본을 끝까지 읽지 말 것. 이미 *중요할 것 같다* 고 의심하는 것만 확인한다.

`user` 모드에선 1번을 *모든 프로젝트* 에 대해 짧게 1 패스 (단, 각 프로젝트당 최신 1~2 파일로 제한). cross-project 공통 신호만 후속 단계로 올린다.

## Phase 3 — Consolidate (통합)

각 기억할 가치가 있는 항목에 대해, 대상 MEMORY_DIR **최상위** 에 메모리 파일을 위 스키마대로 작성하거나 갱신한다.

- 적합한 타입 선택. 새 타입 만들지 않기.
- `feedback` / `project` 는 본문에 **Why:** + **How to apply:** 라인 포함 — 미래의 자신이 edge case 를 판단할 수 있게.
- **메모리에 저장하지 말 것** 항목 (코드 패턴, 프로젝트 구조, 디버깅 레시피, 이미 `CLAUDE.md` 에 있는 것) 은 *사용자가 명시 요청해도* 거른다. 무엇이 *놀랍거나 비자명* 했는지를 추출.

핵심 동작:

- **새 신호를 기존 topic 파일에 병합** — 거의 중복인 새 파일 만들지 않기.
- **상대 날짜 → 절대 날짜 변환** ("어제" → "2026-05-08") — 시간이 지나도 해석 가능하게.
- **반박된 사실 삭제** — 오늘의 조사로 옛 메모리가 틀렸다고 밝혀지면 *원본 파일을 고친다*. 정정문 누적 금지.
- **모드 일관성** — `user` 모드에서 처리하는 파일은 user-scope 에만, project 모드는 해당 프로젝트에만. 실수로 끌어올리거나 끌어내리지 말 것.

## Phase 4 — Prune and index (가지치기 & 인덱스)

대상 MEMORY_DIR 의 `MEMORY.md` 를 다듬는다:

- **200 줄 미만 + ~25KB 미만** 유지.
- 각 항목은 한 줄, **150 자 미만**: `- [Title](file.md) — 한 줄 hook`.
- 본문 내용을 인덱스에 직접 쓰지 말 것.

수행 작업:

- 노후·오류·대체된 메모리의 포인터 제거.
- 200 자 초과 인덱스 라인은 *내용을 topic 파일로 이동* 후 라인 단축.
- 새로 중요해진 메모리 포인터 추가.
- 두 파일이 모순되면 잘못된 쪽을 수정.

> `CLAUDE.md` 와의 reconciliation 은 자동화되어 있지 않다. transcripts 에서 *`CLAUDE.md` 와 명백히 모순되는 메모리* 를 발견하면 보고에만 명시하고 `CLAUDE.md` 자체는 수정하지 않는다 (사용자 권한).

---

## 보고 형식

각 모드 1회마다 다음 형태의 짧은 요약 (없음 / `user` 모드는 1 블록, `all` 모드는 모드 수만큼의 블록 + 합산):

```
[Mode] (없음 | user | <project-id>)

- 추가: <파일명> (type=<type>) — <왜 추가했는지 한 줄>
- 갱신: <파일명> — <어떤 신호로 어떻게 바뀌었는지>
- 삭제: <파일명> — <왜 더 이상 유효하지 않은지>
- 인덱스: <줄 수 before → after, 변경 라인 수>

CLAUDE.md 모순 발견 (있을 때만): <한 줄>
```

변동이 없으면 그렇게 명시한다 ("이미 정돈되어 있어 변경 없음").

---

## 금기 / 주의

- **본문 전수 read 금지** — Phase 1 에서 frontmatter 만, Phase 2 에서 좁은 grep 만.
- **추측 wikilink·추측 파일명 금지** — `MEMORY.md` 인덱스 라인이 가리키는 파일은 *반드시 실제 존재*.
- **타입 규약 우회 금지** — 4 type 외의 새 타입, 중첩 카테고리 만들지 않기.
- **사용자 명시 요청이라도 "저장 안 함" 항목은 거른다** — 대신 *무엇이 비자명했는지* 를 되묻는다.
- **`user` 모드에서 프로젝트 고유 사실 끌어올림 금지** — 일반화 가능한 신호만.
- **자동 트리거 금지** — 본 skill 호출 자체가 큰 작업이므로 사용자가 명시 요청했을 때만 실행한다.
