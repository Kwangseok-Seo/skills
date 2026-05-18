---
name: session-seal-ko
description: "세션 스냅샷 봉인 — 현재 Claude Code 세션의 원본 transcript 를 저장하고 Why/How frontmatter (의도 + 접근) 를 사용자 합의로 확정해 미래 세션이 깔끔히 이어받을 수 있게 한다. 저장 위치: `<cwd>/.claude/sessions/`. 최근 sealed 스냅샷을 스캔해 chain 연결 (continues-why, continues-how) 후보를 제안한다. 사용 시점: 사용자가 '세션 봉인', '세션 정리', 'session-seal', '이 세션 저장', '세션 스냅샷', '세션 마무리' 라고 말할 때."
---

# Session-Seal: 이어받기를 위한 세션 봉인

`session-seal` 은 현재 Claude Code 세션의 **봉인 스냅샷** 을 기록한다. 원본 대화는 손대지 않은 채 보존되고, **Why / How** frontmatter 두 줄에 의도와 접근이 압축돼 다음 세션이 폴더의 과거 기록을 스캔할 때 즉시 맥락을 잡을 수 있다.

이 skill 은 **수동** 이다. `/session-seal` 또는 "이 세션 봉인해줘" 같이 명시 호출 시에만 실행된다.

---

## 무엇을 쓰는가

```
<cwd>/.claude/sessions/
└── YYYY-MM-DD - {짧은 why}.md
```

각 파일의 구조:

```yaml
---
id: "YYYYMMDDHHmm"
title: "YYYY-MM-DD - {짧은 why}"
type: session
session-id: "<claude-code-session-id-or-derived>"
project: "<cwd basename>"
date: YYYY-MM-DD
why: "이번 세션의 의도 한 줄"
how: "이번 세션의 접근·방법 한 줄"
continues-why: "[[이전 세션 제목]]"   # 옵션, 새 chain 시작이면 필드 생략
continues-how: "[[이전 세션 제목]]"   # 옵션, 새 chain 시작이면 필드 생략
status: sealed
tags: [kebab, case, 2~4개]
---

# 원본 대화

## user
...
## assistant
...
```

본문 (원본 대화) 은 봉인 후 **불변**. 새 해석은 새 세션에서 다룬다.

---

## 핵심 개념

- **Why** — *이번* 세션의 의도 한 줄. 프로젝트 수준 목표 ("트레이딩 봇을 만든다") 도, 단일 turn 수준 ("`config.py` 수정") 도 아닌 *그 사이*. 예: *"전략 A 와 B 의 백테스트 결과 비교"*.
- **How** — 이번 세션이 실제로 사용한 접근 한 줄. 예: *"세 repo audit → 갈림길 대화 → v0 뼈대 합의"*. 도구 이름이 아니라 *방법*.
- **Chain** — `continues-why` / `continues-how` 는 같은 저장 디렉토리 안에서 Why 또는 How 가 *연속된* 가장 최근 sealed 스냅샷에 이번 세션을 연결한다. **두 축은 독립** — 의도가 이어지면서도 접근은 바뀔 수 있고 (그 반대도). 둘 다 비어 있을 수 있고, 그 경우 여기서 새 chain 이 시작된다는 뜻.
- **Sealed = 불변** — 봉인 후 본문은 다시 쓰지 않는다.

---

## 워크플로우

### Phase 1 — 활성 transcript 찾기

Claude Code 가 이 세션을 위해 기록 중인 JSONL 파일을 찾는다. 보통 `~/.claude/projects/` 아래에서 가장 최근에 수정된 `.jsonl` 이 현재 세션의 것.

bash:
```bash
ls -t ~/.claude/projects/*/*.jsonl | head -1
```

PowerShell:
```powershell
Get-ChildItem ~/.claude/projects/*/*.jsonl |
  Sort-Object LastWriteTime -Descending | Select-Object -First 1
```

여러 세션이 동시 활성 상태일 가능성이 있으면 사용자에게 경로 확인을 요청한다.

### Phase 2 — 저장 디렉토리 결정

- Default: `<cwd>/.claude/sessions/` — `<cwd>` 는 현재 작업 디렉토리.
- Override: 환경변수 `SESSION_SEAL_DIR` 이 설정되어 있으면 그 경로를 그대로 사용.
- 디렉토리가 없으면 생성.

### Phase 3 — Transcript 를 markdown 으로 변환

이 SKILL.md 와 같은 디렉토리에 `convert_transcript.py` 헬퍼가 있다. Phase 1 에서 찾은 JSONL 에 대해 실행:

bash:
```bash
python <skill-dir>/convert_transcript.py <transcript.jsonl> > /tmp/session-seal-body.md
```

PowerShell:
```powershell
python <skill-dir>\convert_transcript.py <transcript.jsonl> |
  Out-File -Encoding utf8 $env:TEMP\session-seal-body.md
```

`<skill-dir>` 는 이 SKILL.md 가 있는 디렉토리. 경로를 모르면 Glob 으로 Claude plugins 루트 아래에서 `**/session-seal-ko/convert_transcript.py` 를 찾는다.

헬퍼는 user/assistant turn 을 `## role` 헤더로 묶고, tool use / tool result 는 코드 블록에 접는다. 4000 자 초과 tool output 은 truncate 마커와 함께 잘린다.

### Phase 4 — 최근 sealed 스냅샷 스캔 (chain 후보 발굴)

저장 디렉토리의 최근 sealed 스냅샷 **최대 3개의 frontmatter 만** 읽는다:

bash:
```bash
ls -t <save-dir>/*.md | head -3
```

PowerShell:
```powershell
Get-ChildItem <save-dir>/*.md |
  Sort-Object LastWriteTime -Descending | Select-Object -First 3
```

각 파일의 첫 `---` ~ 다음 `---` 사이만 읽는다. 본문 read 금지 — frontmatter 만으로 충분.

스캔 결과로 **Why-chain 후보 (최대 1개)** 와 **How-chain 후보 (최대 1개)** 를 도출. 동일 스냅샷일 수도, 다른 스냅샷일 수도, 없을 수도 있다.

연속성 판정은 단순 키워드 매칭이 아닌 *의미 판단*. 질문: *"이번 세션의 의도가 그 스냅샷의 의도의 직접적 연장인가?"*

### Phase 5 — Why/How/chain/파일명/태그 단일 라운드 합의

다음을 **한 번에** 사용자에게 제시:

```
저장 위치: `<save-dir>/{파일명}.md`

제안:
- Why: {한 줄}
- How: {한 줄}
- continues-why: [[<제목>]] | (new chain start)
- continues-how: [[<제목>]] | (new chain start)
- 파일명: `YYYY-MM-DD - {짧은 why}.md`
- tags: [tag1, tag2, ...]

이대로 확정하시겠어요? 수정할 항목만 짚어 주시면 그것만 반영합니다.
```

응답 처리:
- 수락 / "그대로" / "y" / 빈 응답 → 제안 전체 채택, Phase 6 진행.
- 부분 수정 → 지목된 필드만 사용자 문안으로 대체, **나머지는 제안 유지**, Phase 6 진행. 추가 확인 turn 없음.
- 거부 / 연기 → 저장하지 않고 종료.

**같은 필드를 두 번 묻지 않는다.** 응답이 모호하면 한 번 더 단일 라운드로 묶어 제시 (총 turn ≤ 2).

### Phase 6 — sealed 스냅샷 작성

최종 파일 구성:
1. Frontmatter 블록 (Phase 5 결과, `status: sealed`).
2. `# 원본 대화` 헤더.
3. Phase 3 의 변환된 markdown.

파일명에서 파일시스템 제약 문자 제거: `:`, `/`, `\`, `?`, `*`, `"`, `<`, `>`, `|`.

파일을 쓴다. **변환된 본문은 절대 수정 금지**.

### Phase 7 — 보고

사용자에게:

```
✓ Sealed: <save-dir>/{파일명}.md

Why: {확정 why}
How: {확정 how}
Continues-why: [[이전 제목]] | (new chain start)
Continues-how: [[이전 제목]] | (new chain start)
```

---

## 금기

- **sealed 스냅샷 본문 read 금지** — chain 스캔은 frontmatter 만. 본문은 크다.
- **허위 chain 링크 금지** — `continues-why` / `continues-how` 의 wikilink 는 *실제로 저장 디렉토리에 존재하는* 스냅샷만.
- **본문 재작성 금지** — 새 해석이 필요하면 새 세션에서 다룬다.
- **자동 트리거 금지** — 사용자 명시 호출 시에만 실행.
- **사용자 미확인 Why/How 로 봉인 금지** — skill 단독 추상은 봉인이 아니다.

---

## 커스터마이즈

기본값은 단순함을 위해 고정. 필요하면 이 SKILL.md 를 직접 수정:

- **저장 디렉토리** — `<cwd>/.claude/sessions/` 가 안 맞으면 Phase 2 default 변경. 흔한 대안: 개인 위키 `~/wiki/Sessions/<project>/`.
- **Chain 스캔 깊이** — Phase 4 는 최근 3개를 본다. 낮추면 빠르고, 높이면 장기 프로젝트에서 chain 매칭률이 올라간다.
- **Tool output truncate 길이** — `convert_transcript.py` 의 `MAX_TOOL_OUTPUT` 수정 (default 4000).
- **새 세션 시작 시 자동 주입** — 본 skill 에 포함하지 않음 (단순함 유지). 원하면 `~/.claude/settings.json` 에 SessionStart hook 을 직접 추가해 최근 sealed 스냅샷의 frontmatter 를 출력하게 할 것.
