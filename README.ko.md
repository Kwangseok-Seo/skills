# skills

> 다국어 Claude Code skills 모음. 메모리 통합용 `dream`, 이어받기 가능한 세션 봉인용 `session-seal`, GATE 기반 세션 회고용 `session-retro`, 가치 판정 후 HTML 시각화 변환용 `to-html`.

[Claude Code](https://docs.claude.com/en/docs/claude-code) 용 skills 모음을 단일 plugin 으로 publish 한 저장소. 각 skill 은 영어판과 한국어판 두 변형으로 제공되어, 실제로 에이전트에게 말하는 언어에 맞춰 깔끔하게 트리거된다.

[English README](README.md)

## 빠른 시작

Claude Code 안에서 이 repo 를 plugin marketplace 로 추가하고 install:

```text
/plugin marketplace add Kwangseok-Seo/skills
/plugin install kwangseok-seo-skills@Kwangseok-Seo/skills
```

또는 skills 디렉토리를 수동 복사:

bash (macOS / Linux / Git Bash):

```bash
git clone https://github.com/Kwangseok-Seo/skills.git
cp -r skills/skills/dream            ~/.claude/skills/dream
cp -r skills/skills/dream-ko         ~/.claude/skills/dream-ko
cp -r skills/skills/session-seal     ~/.claude/skills/session-seal
cp -r skills/skills/session-seal-ko  ~/.claude/skills/session-seal-ko
cp -r skills/skills/session-retro    ~/.claude/skills/session-retro
cp -r skills/skills/session-retro-ko ~/.claude/skills/session-retro-ko
cp -r skills/skills/to-html          ~/.claude/skills/to-html
cp -r skills/skills/to-html-ko       ~/.claude/skills/to-html-ko
```

PowerShell (Windows):

```powershell
git clone https://github.com/Kwangseok-Seo/skills.git
Copy-Item -Recurse skills/skills/dream            ~/.claude/skills/dream
Copy-Item -Recurse skills/skills/dream-ko         ~/.claude/skills/dream-ko
Copy-Item -Recurse skills/skills/session-seal     ~/.claude/skills/session-seal
Copy-Item -Recurse skills/skills/session-seal-ko  ~/.claude/skills/session-seal-ko
Copy-Item -Recurse skills/skills/session-retro    ~/.claude/skills/session-retro
Copy-Item -Recurse skills/skills/session-retro-ko ~/.claude/skills/session-retro-ko
Copy-Item -Recurse skills/skills/to-html          ~/.claude/skills/to-html
Copy-Item -Recurse skills/skills/to-html-ko       ~/.claude/skills/to-html-ko
```

## 제공 Skills

| Skill              | 언어 | 설명                                                                                |
|--------------------|:----:|-------------------------------------------------------------------------------------|
| `dream`            | en   | `~/.claude/memory/` 에 대한 메모리 통합 pass                                        |
| `dream-ko`         | ko   | `dream` 의 한국어 변형                                                              |
| `session-seal`     | en   | 현재 세션을 `<cwd>/.claude/sessions/<제목>.md` 로 Why/How frontmatter 와 함께 봉인  |
| `session-seal-ko`  | ko   | `session-seal` 의 한국어 변형                                                       |
| `session-retro`    | en   | GATE 기반 세션 회고 — rule 재사용 성적을 먼저 매기고 accept 된 것만 발행           |
| `session-retro-ko` | ko   | `session-retro` 의 한국어 변형                                                      |
| `to-html`          | en   | 가치 판정 후 HTML 시각화 변환 (Compare / Tune / Learn 패턴, 토큰 비용 경고 포함)   |
| `to-html-ko`       | ko   | `to-html` 의 한국어 변형                                                            |

### `dream` 이 무엇을 하는가

`dream` 은 **수동** reflective pass 다. 실행하면 에이전트가:

1. **Orient** — 기존 `MEMORY.md` 인덱스와 topic 파일들의 frontmatter 만 스캔 (본문 전수 read 금지).
2. **Gather signal** — 최근 수정된 1~3 개 transcript 에서 저장 가치 있는 새 정보를 찾는다.
3. **Consolidate** — 새 신호를 기존 topic 파일에 병합, 상대 날짜를 절대 날짜로 변환, 반박된 사실 삭제.
4. **Prune & index** — `MEMORY.md` 를 200 줄 미만으로 유지, 노후 파일 포인터 제거.

세 모드:

| Args     | 범위                                                              |
|----------|-------------------------------------------------------------------|
| (없음)   | 현재 프로젝트 메모리 디렉토리                                     |
| `user`   | `~/.claude/memory/` (cross-project 신호만)                        |
| `all`    | `user` 패스 + 모든 프로젝트 메모리 디렉토리 각각 1회씩            |

### `session-seal` 이 무엇을 하는가

`session-seal` 도 **수동** 이다. 호출하면 (예: `/session-seal`, "이 세션 봉인해줘") 에이전트가:

1. **Locate** — `~/.claude/projects/` 에서 현재 세션의 활성 JSONL transcript 를 찾는다.
2. **Convert** — 동봉된 `convert_transcript.py` 로 읽기 좋은 markdown 으로 변환.
3. **Scan** — 저장 디렉토리의 최근 sealed 스냅샷 3개의 frontmatter 만 스캔해 chain 후보를 본다.
4. **Propose** — Why / How / 파일명 / tags / chain 링크를 한 번의 라운드에 제시하고 사용자 확인을 기다린다.
5. **Write** — `<cwd>/.claude/sessions/YYYY-MM-DD - {짧은 why}.md` 로 봉인 파일을 쓴다. 본문은 원본 대화 그대로.

Why / How 는 미래 세션이 즉시 이어받게 해주는 두 줄 abstraction — `Why` 는 세션의 의도, `How` 는 접근. `continues-why` / `continues-how` 는 그 의도/접근이 이어지는 직전 sealed 스냅샷으로의 옵션 wikilink.

스냅샷을 다른 곳 (예: 개인 위키) 에 두려면 환경변수 `SESSION_SEAL_DIR` 을 설정. 새 세션 시작 시 자동 주입은 단순함을 위해 포함하지 않음 — 원하면 skill 의 "커스터마이즈" 섹션 참조.

### `session-retro` 가 무엇을 하는가

`session-retro` 는 세션을 닫기 전에 도는 **수동** 패스다. 세션 봉인도 함께 쓴다면 `/session-seal` **전**에 돈다. 실행하면 에이전트가:

1. **재사용 성적을 먼저 매긴다** — 이번 세션에 적용됐을 rule 각각에 대해 *어디서 어떻게* 쓰였는지를 구체 사건으로 적고 작동/부분작동/미작동을 판정한다. 이 섹션이 첫 번째인 것은 의도적이다 — "또 rule 하나 늘리기"에 제동이 걸린다. 발행한 게 없는 첫 실행이면 한 줄로 그렇게 적고 넘어간다.
2. **4축 × 2렌즈로 분석한다** — 잘한 것 / 실수한 것 / 어려웠던 것 / 배운 것을 엔지니어링·비즈니스 두 렌즈로. 모든 항목은 세션의 관찰 가능한 사건에 앵커해야 하고, **실수 축은 비울 수 없다.**
3. **이진으로 판정한다** — 각 노드는 🟢 후보(rule / skill / guardrail) 아니면 **사유가 적힌** `미분류`. 강도 등급을 두지 않는다 — 낮게 매긴 항목이 "검토 완료" 착각과 함께 영구 매장되기 때문.
4. **사람 GATE 에서 멈춘다** — 후보는 선택지 버튼이 아니라 **산문으로** 제시된다. 읽기가 강제돼야 거수기가 안 된다. 반려·문구 수정도 명시적으로 정당한 결과이고, 과거에 거절한 영역이면 그 사실을 후보 옆에 밝힌다.
5. **accept 된 것만 발행한다** — rule 은 동봉된 `RULE-FORMAT.md` 를 따라 `~/.claude/rules/*.md` 로. 이 포맷은 *매 세션 컨텍스트에 실리는* 파일에 맞춰져 있다(목표 1.5~3K chars).

동봉 파일: `RETRO-FORMAT.md`(출력 형태), `RULE-FORMAT.md`(rule 파일 형태), `examples/worked-example.md`(비식별화한 실제 회고 1패스 전문).

`~/.claude/rules/` 를 자동으로 읽지 않는 환경이면 `~/.claude/CLAUDE.md` 등 상시 적재되는 자리에 발행한다 — 목적지만 바뀐다. 세션을 가로지르는 회고 코퍼스에 노드를 남기는 6단계는 선택이며 기본은 건너뛴다.

### `to-html` 이 무엇을 하는가

`to-html` 은 콘텐츠를 **단일 self-contained HTML 파일** 로 변환한다 — 단, *시각화가 실제로 가치를 더할 때만*. 실행하면 에이전트가:

1. **입력 식별** — 파일 경로, 직전 assistant 응답, 붙여 넣은 텍스트를 받는다. 아무것도 주어지지 않으면 한 번만 묻는다.
2. **분류 + 추산** — 콘텐츠를 세 패턴 중 하나로 분류(**Compare** 그리드 비교 / **Tune** 슬라이더로 값 조정 / **Learn** 다이어그램+코드+주의사항 한 페이지), 토큰 크기를 추산하고, HTML 출력이 보통 마크다운 대비 ~5배(Pascal Filiteri 측정) 라는 경고를 띄운다.
3. **Gate** — 가치가 낮거나 어떤 패턴에도 안 맞으면 대안(마크다운 요약 / ASCII 표 / Mermaid 만 / 그대로 진행) 을 제시하고 **사용자 결정을 기다린다.** 조용히 fallback 하지 않는다.
4. **도구 선호 한 번만 묻기** — 기본은 Tailwind CDN (+ 필요 시 Mermaid / Chart.js); 사용자가 명시한 도구셋(예: 오프라인용 inline-only) 우선.
5. **HTML 파일 하나 쓰기** — `<cwd>/.claude/to-html/YYYY-MM-DD-HHmm-{슬러그}.html`. CDN 의존성만, 더블클릭으로 열림. **자동으로 열지 않는다.**

저장 디렉토리는 환경변수 `TO_HTML_DIR` 로 override. 세 패턴과 5배 비용 경고 framing 은 Anthropic / Tariq Sipha 의 공개 가이드에서 직접 가져옴 — 스킬의 "출처" 섹션 참조.

## 왜 ko / en 을 따로 분리했나?

skill 은 `description` 키워드로 트리거된다. 한 SKILL.md 에 두 언어를 같이 넣으면 prompt 비용이 두 배가 되고 매칭도 흐려진다. description 이 분리된 두 skill 로 두면 각 언어에서 깔끔하게 트리거되고 유지보수도 쉽다. 영어판 (`dream`) 이 **ground truth** 이고, 한국어판 (`dream-ko`) 은 그 미러다. 양쪽은 항상 동기화되어야 한다 — [docs/adding-a-skill.md](docs/adding-a-skill.md#kken-sync-rules) 참조.

## Contributing

[CONTRIBUTING.md](CONTRIBUTING.md), [docs/adding-a-skill.md](docs/adding-a-skill.md) 참조.

## License

[MIT](LICENSE) © Kwangseok-Seo
