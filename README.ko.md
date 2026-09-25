# skills

> 다국어 Claude Code skills 모음. 메모리 통합용 `dream`, 이어받기 가능한 세션 봉인용 `session-seal`, GATE 기반 세션 회고용 `session-retro`, 가치 판정 후 HTML 시각화 변환용 `to-html`, 자율성 다이얼로 체크리스트를 커밋까지 몰고 가는 `task-routine`.

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
cp -r skills/skills/task-routine     ~/.claude/skills/task-routine
cp -r skills/skills/task-routine-ko  ~/.claude/skills/task-routine-ko
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
Copy-Item -Recurse skills/skills/task-routine     ~/.claude/skills/task-routine
Copy-Item -Recurse skills/skills/task-routine-ko  ~/.claude/skills/task-routine-ko
```

## 제공 Skills

| Skill              | 언어 | 설명                                                                                |
|--------------------|:----:|-------------------------------------------------------------------------------------|
| `dream`            | en   | `~/.claude/memory/` 에 대한 메모리 통합 pass                                        |
| `dream-ko`         | ko   | `dream` 의 한국어 변형                                                              |
| `session-seal`     | en   | 현재 세션을 `<cwd>/.claude/sessions/<제목>.md` 로 Why/How frontmatter 와 함께 봉인  |
| `session-seal-ko`  | ko   | `session-seal` 의 한국어 변형                                                       |
| `session-retro`    | en   | GATE 기반 세션 회고 — 원장 근거로 rule 을 덜어내고, accept 된 것만 발행            |
| `session-retro-ko` | ko   | `session-retro` 의 한국어 변형                                                      |
| `to-html`          | en   | 가치 판정 후 HTML 시각화 변환 (Compare / Tune / Learn 패턴, 토큰 비용 경고 포함)   |
| `to-html-ko`       | ko   | `to-html` 의 한국어 변형                                                            |
| `task-routine`     | en   | 작업 체크리스트를 하나씩 커밋까지 몰고 가는 개발 루프 (자율성 다이얼 포함)          |
| `task-routine-ko`  | ko   | `task-routine` 의 한국어 변형                                                       |

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

`session-retro` 는 세션을 닫기 전에 도는 **수동** 패스다. 세션 봉인도 함께 쓴다면 `/session-seal` **전**에 돈다. rule 은 매 세션 컨텍스트를 먹으므로, 무엇을 *덜어낼지*를 더할 것만큼 신중하게 정한다. 실행하면 에이전트가:

1. **rule 마다 판정을 기록한다** — 이번 세션에 관련된 rule 과 격리 중인 rule 전부를 작동 / 부분작동 / 미작동(격리 rule 은 무관 포함)으로, 구체 사건과 함께. 동봉된 `ledger.py` 가 CSV 원장에 덧붙인다.
2. **4축 × 2렌즈로 분석하고 이진으로 판정한다** — 잘한 것 / 실수한 것 / 어려웠던 것 / 배운 것, 모두 관찰 가능한 사건에 앵커(**실수 축은 비울 수 없다**). 각 노드는 🟢 후보 아니면 사유가 적힌 `미분류`. 여기까지는 읽지 않아도 되는 작업 텍스트다.
3. **표 두 개를 보인다, 빼기가 먼저** — 빼기 행은 에이전트의 짐작이 아니라 `ledger.py cards` 에서 나온다: 계속 작동하는 rule 은 *격리*(컨텍스트에서 빼고 rule 없이 행동이 유지되는지 관측), 계속 실패하는 rule 은 *고치거나빼기*, 격리 중 실패한 rule 은 *복귀*, 격리를 버틴 rule 은 *보관*, 회고가 거의 건드리지 않는 rule 은 *관련드묾*. 격리·고치거나빼기 행에는 원장에서 평균 rule 대비로 센 확률이 붙는다. 그다음이 더하기 — 신규 rule 과 보강.
4. **사람 GATE 에서 멈춘다** — 번호별로 답한다. 반려·문구 수정도 명시적으로 정당한 결과이고, 반려는 기록돼 같은 제안이 매 회고 다시 올라오지 않는다.
5. **accept 된 것만 실행한다** — rule 파일을 `~/.claude/rules/` · `rules-probation/` · `rules-archive/` 사이에서 옮기고(위치가 곧 상태), rule 은 동봉된 `RULE-FORMAT.md` 를 따라 발행한다(목표 1.5~3K chars).

동봉 파일: `RETRO-FORMAT.md`(출력 형태), `RULE-FORMAT.md`(rule 파일 형태), `ledger.py` 와 테스트(Python 3.8+), `examples/worked-example.md`(실제 회고 1패스 전문). `~/.claude/rules/` 아래 rule 하나 = 파일 하나를 전제로 한다. 원장이 비어 있는 동안은 기준이 없어 확률 제안이 나오지 않고, 판정이 쌓이면서 생긴다. 원장은 영어판이 `~/.claude/session-retro/`, 한국어판이 `~/.claude/session-retro-ko/` 로 따로다 — 판정값이 각 언어로 저장되기 때문이다. 선택: `SESSION_RETRO_DIR` 는 원장 위치, `SESSION_SEAL_DIR` 는 봉인 세션 수, `SESSION_RETRO_CORPUS` 는 세션을 가로지르는 회고 코퍼스(8단계, 기본은 건너뜀).

### `to-html` 이 무엇을 하는가

`to-html` 은 콘텐츠를 **단일 self-contained HTML 파일** 로 변환한다 — 단, *시각화가 실제로 가치를 더할 때만*. 실행하면 에이전트가:

1. **입력 식별** — 파일 경로, 직전 assistant 응답, 붙여 넣은 텍스트를 받는다. 아무것도 주어지지 않으면 한 번만 묻는다.
2. **분류 + 추산** — 콘텐츠를 세 패턴 중 하나로 분류(**Compare** 그리드 비교 / **Tune** 슬라이더로 값 조정 / **Learn** 다이어그램+코드+주의사항 한 페이지), 토큰 크기를 추산하고, HTML 출력이 보통 마크다운 대비 ~5배(Pascal Filiteri 측정) 라는 경고를 띄운다.
3. **Gate** — 가치가 낮거나 어떤 패턴에도 안 맞으면 대안(마크다운 요약 / ASCII 표 / Mermaid 만 / 그대로 진행) 을 제시하고 **사용자 결정을 기다린다.** 조용히 fallback 하지 않는다.
4. **도구 선호 한 번만 묻기** — 기본은 Tailwind CDN (+ 필요 시 Mermaid / Chart.js); 사용자가 명시한 도구셋(예: 오프라인용 inline-only) 우선.
5. **HTML 파일 하나 쓰기** — `<cwd>/.claude/to-html/YYYY-MM-DD-HHmm-{슬러그}.html`. CDN 의존성만, 더블클릭으로 열림. **자동으로 열지 않는다.**

저장 디렉토리는 환경변수 `TO_HTML_DIR` 로 override. 세 패턴과 5배 비용 경고 framing 은 Anthropic / Tariq Sipha 의 공개 가이드에서 직접 가져옴 — 스킬의 "출처" 섹션 참조.

### `task-routine` 이 무엇을 하는가

`task-routine` 은 체크리스트를 받아 각 항목을 **설계 루프 → 구현 루프 → 커밋** 으로 몰고 간다. 첫 실행에서 질문 넷을 하고 config 를 쓴 뒤로는:

1. **프로브** — 실제로 설치된 것(CLI·스킬·에이전트·플러그인)을 매 실행 확인한다. 저장된 능력 목록은 사용자가 뭘 깔거나 지운 순간 썩기 때문이다.
2. **작업 해석** — 교체 가능한 소스 어댑터로: 로컬 마크다운 체크리스트 또는 GitHub 이슈. 어댑터의 `locality`(`local`/`remote`)가 완료 표시를 파일 편집으로 볼지 트래커 쓰기로 볼지를 결정한다.
3. **검토 루프가 붙은 설계** — *독립* 검토자(다른 벤더 CLI → 다른 모델 → 새 컨텍스트)가 plan 을 받되 설계 대화는 절대 받지 않는다. 설계자의 논증을 받아 든 검토자는 검토가 아니라 동의를 돌려준다.
4. **한 루프로 구현** — 구현 → 검증 → 리뷰가 예산 3을 공유하고, 리뷰는 검증이 통과한 뒤에만 돈다. 정리는 출구에, 루프를 2회 이상 돈 경우에만 나타난다.
5. **커밋하고 거기서 멈춘다.** push·PR·머지·회고는 하지 않는다.

핵심은 **자율성 다이얼** 이다: `manual` / `assisted`(기본) / `auto`. 무인 실행은 *레벨이 허용* **∧** *위험 등급이 auto-eligible* 일 때만 성립한다. 네 부류는 `auto` 를 포함한 모든 레벨에서 묻는다 — 밖으로 나가는 행위, 파괴적 로컬 작업, 트래커 쓰기, 그리고 security 5신호. 그리고 **검사 자체를 돌릴 수 없으면 통과가 아니라 정지다.**

모든 추천·선택·결과는 결정 로그에 각각 한 줄로 append 된다(제자리 수정 없음). `task-routine report` 가 그 로그를 결정 지점별 성적표로 바꾸는데, 동의율은 **사람이 답한 결정만** 세고 계산한다 — 무인 실행된 것을 넣으면 "자동화했으니 자동화해도 됐다" 를 증명하는 분석이 된다. 다이얼을 올리는 것은 언제나 사용자의 몫이다.

상태 디렉토리는 `TASK_ROUTINE_DIR` 로 override. 상태를 repo 밖에 두는 것은 의도다 — 무인 실행이 자기 로그를 커밋할 수 있으면 안 된다.

## 왜 ko / en 을 따로 분리했나?

skill 은 `description` 키워드로 트리거된다. 한 SKILL.md 에 두 언어를 같이 넣으면 prompt 비용이 두 배가 되고 매칭도 흐려진다. description 이 분리된 두 skill 로 두면 각 언어에서 깔끔하게 트리거되고 유지보수도 쉽다. 영어판 (`dream`) 이 **ground truth** 이고, 한국어판 (`dream-ko`) 은 그 미러다. 양쪽은 항상 동기화되어야 한다 — [docs/adding-a-skill.md](docs/adding-a-skill.md#kken-sync-rules) 참조.

## Contributing

[CONTRIBUTING.md](CONTRIBUTING.md), [docs/adding-a-skill.md](docs/adding-a-skill.md) 참조.

## License

[MIT](LICENSE) © Kwangseok-Seo
