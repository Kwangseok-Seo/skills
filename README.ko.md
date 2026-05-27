# skills

> 다국어 Claude Code skills 모음. 메모리 통합용 `dream`, 이어받기 가능한 세션 봉인용 `session-seal`, 가치 판정 후 HTML 시각화 변환용 `to-html`.

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
