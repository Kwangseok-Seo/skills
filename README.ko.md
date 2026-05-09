# skills

> 다국어 Claude Code skills 모음. 첫 스킬은 `dream` — 메모리 통합 pass.

[Claude Code](https://docs.claude.com/en/docs/claude-code) 용 skills 모음을 단일 plugin 으로 publish 한 저장소. 각 skill 은 영어판과 한국어판 두 변형으로 제공되어, 실제로 에이전트에게 말하는 언어에 맞춰 깔끔하게 트리거된다.

[English README](README.md)

## 빠른 시작

Claude Code 안에서 이 repo 를 plugin marketplace 로 추가하고 install:

```text
/plugin marketplace add Kwangseok-Seo/skills
/plugin install kwangseok-seo-skills@Kwangseok-Seo/skills
```

또는 skills 디렉토리를 수동 복사:

```bash
git clone https://github.com/Kwangseok-Seo/skills.git
cp -r skills/skills/dream     ~/.claude/skills/dream
cp -r skills/skills/dream-ko  ~/.claude/skills/dream-ko
```

## 제공 Skills

| Skill       | 언어 | 설명                                                          |
|-------------|:----:|---------------------------------------------------------------|
| `dream`     | en   | `~/.claude/memory/` 에 대한 메모리 통합 pass                  |
| `dream-ko`  | ko   | `dream` 의 한국어 변형                                        |

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

## 왜 ko / en 을 따로 분리했나?

skill 은 `description` 키워드로 트리거된다. 한 SKILL.md 에 두 언어를 같이 넣으면 prompt 비용이 두 배가 되고 매칭도 흐려진다. description 이 분리된 두 skill 로 두면 각 언어에서 깔끔하게 트리거되고 유지보수도 쉽다. 영어판 (`dream`) 이 **ground truth** 이고, 한국어판 (`dream-ko`) 은 그 미러다. 양쪽은 항상 동기화되어야 한다 — [docs/adding-a-skill.md](docs/adding-a-skill.md#kken-sync-rules) 참조.

## Contributing

[CONTRIBUTING.md](CONTRIBUTING.md), [docs/adding-a-skill.md](docs/adding-a-skill.md) 참조.

## License

[MIT](LICENSE) © Kwangseok-Seo
