# telemetry — 결정 로그와 체크포인트

> 결정 레코드나 체크포인트를 쓸 때, 또는 로그를 분석할 때 읽는다. 이 로그가 다이얼 올리기를 기분이 아니라 증거로부터의 논증으로 만들고, 체크포인트가 `--resume` 을 의미 있게 만든다.

```
~/.claude/task-routine/<project-slug>/decisions.jsonl
```

`<project-slug>` 은 **repo 루트의 basename 을 32자로 자른 것 + 하이픈 + 그 루트 전체 경로의 SHA-256 앞 8자리 hex** 다 — `auto-trial-9f3a1c2e`. 루트는 실행이 호출된 경로가 아니라 `git rev-parse --show-toplevel` 에서 가져온다. 같은 repo 를 두 경로로 접근해도 로그가 둘로 갈리지 않게.

**경로 전체의 구분자를 치환한 것이 아니다.** 그러면 상태 경로 길이가 repo 깊이에 비례해 자라고, Windows 에서 `MAX_PATH` 를 넘는다: 실측으로 260자에서 셸은 `decisions.jsonl` 을 쓰는데 파이썬 리더는 그 파일이 없다고 답한다 — 로그가 디스크에 있는 프로젝트에 `report` 가 빈 스코어카드를 찍는다. 같은 내용이 157자에서는 정상으로 읽힌다. 옛 이름으로 남은 디렉터리는 옮기지도 합치지도 않는다. 거기 있다고 한 번 말해서, 증거를 조용히 처음부터 다시 쌓는 대신 의도적으로 옮겨 갈 수 있게 한다.

`TASK_ROUTINE_DIR` 로 루트를 바꾼다. 언제나 repo 밖이다 — 파일을 스테이징하는 무인 실행이 자기 로그를 커밋할 수 있으면 안 된다.

## 레코드 두 종류, 한 줄을 두 번 고치는 일은 없다

**decision** 은 선택하는 순간에 쓴다. **outcome** 은 Phase 4 에서 *새 줄*로 쓰고 `decision_id` 로 잇는다.

```jsonc
// decision — 고르는 순간에 기록
{
  "kind": "decision",
  "id": "d-20260816T0914Z-a3f-3",          // <run_id>-<n>, 로그 안에서 유일
  "ts": "2026-08-16T09:14:22+09:00",
  "run_id": "20260816T0914Z-a3f",
  "skill_version": "task-routine@1.0.0",
  "model": "<아는 경우 모델 id>",
  "source_ref": "TODO.md",
  "task_id": "cache-list-responses",  // 어댑터의 안정 id. 결정이 항목이 아니라 유닛에 속하면
                                      // id 의 배열. 아직 아무 항목도 고르기 전이면 null
  "step_id": "S2-test",
  "risk_tier": "auto-eligible",
  "level": "auto",                    // 그 시점의 다이얼
  "mode": "auto",                     // "auto"=무인 실행됨, "asked"=사람이 답함
  "options": ["unit", "integration", "unit+integration", "none"],
  "recommended_index": 2,
  "chosen_index": 2,
  "agreed": true,                     // chosen == recommended. 추천이 없었으면 null
  "rationale": "캐시 계층은 통합 표면"
}
```

```jsonc
// outcome — Phase 4 에서 append. 위 줄에 병합하지 않는다
{
  "kind": "outcome",
  "decision_id": "d-20260816T0914Z-a3f-3",
  "ts": "2026-08-16T09:31:05+09:00",
  "build_iterations": 3,
  "design_rounds": 0,
  "verification_ran": true,
  "review_ran": true,
  "review_flagged": true,
  "reverted": false,
  "manual_intervention": false,
  "capped": true,
  "claim_met": "unmet"         // S2-test outcome 줄에만: "met" · "unmet" · "unclaimed"
                               // (전략이 none). 테스트를 별도 경로로 두지 않는 repo 라
                               // 검사를 안 돌린 경우엔 아예 없다
}
```

**`claim_met` 은 `S2-test` 의 것이고 다른 줄의 것이 아니다.** 그 결정 자신의 결과이기 때문이다: 전략이 이 단위를 무엇이 검증할지 말했고, 이 단위가 쓴 경로에 테스트가 있거나 없거나 둘 중 하나다(`SKILL.md` §Step 3). `unclaimed` 는 `none` 전략이면서 반대 방향 검사도 통과한 경우다 — 아무것도 주장하지 않고 동작을 실은 단위는 다른 것과 똑같이 `unmet` 이다. 이걸 단위의 다른 결정들에 복사해 쓰면 관측 1건을 서로 다른 판단 4개에 대고 기록하는 셈이 된다. 불리언이 아니라 값 셋인 이유는 *아무것도 주장하지 않았다* 와 *주장이 미달이다* 가 다른 사실이고 둘째만 발견이기 때문이다. 아예 없는 경우는 또 다르고 단위가 아니라 **repo** 에 속한다 — Phase 1 에서 한 번 보고하지 행마다가 아니다.

`recommended_index` 와 `chosen_index` 는 **이 줄에 실제로 쓴 `options` 배열** 기준 인덱스다 — 문서의 번호 매긴 목록에서 옮기지 말고 배열에서 센다. 옵션은 재배열되기 마련이고, 낡은 인덱스는 없던 불일치를 조용히 기록한다.

**결정은 그것이 내려진 스코프에서 한 번 기록하고, `task_id` 가 그 스코프를 적는다.** 머지된 그룹은 일부 결정을 유닛 전체에 대해 한 번 내린다. 그것을 항목별로 풀어 쓰면 판단 하나가 나중에 다이얼을 올릴 때 쓰는 `n (asked)` 모집단에 여러 번 계상되고, 나중에는 어떤 질의로도 복제본을 구분할 수 없다.

## 체크포인트

다른 파일, 다른 규칙: 로그는 append-only 이력이고 체크포인트는 **덮어쓰는 현재 상태**다. 중단과 재개는 별개의 호출이므로, 이 스키마는 둘 사이의 계약이다 — 앞이 쓴 것을 뒤가 읽을 수 있어야 한다.

```jsonc
// ~/.claude/task-routine/<project-slug>/run-<run_id>.json — 단위마다 제자리 갱신
{
  "version": 1,
  "run_id": "20260816T0914Z-a3f",   // 실행 시작 시각(UTC) + 무작위 3글자 — 로그가 쓰는 id 와 같다
  "updated_at": "2026-08-16T09:31:05+09:00",
  "source_ref": "TODO.md",
  "level": "auto",
  "level_origin": "--auto",         // "--auto" | "--level" | "global" | "default" — "project" 은 없다
  "consecutive_failures": 1,        // 실행 단위 — 단위 경계를 넘어 살아남아야 하는 유일한 카운터
  "units": [                        // 실행 순서, 단위당 한 항목
    { "id": "g1", "task_ids": ["add-a-sort-parameter", "require-admin-role"],
      "status": "done", "start_commit": "9a8b7c6", "dirty_at_start": [], "build_iterations": 1,
      "workers": { "add-a-sort-parameter": { "branch": "tr/add-a-sort-parameter", "state": "merged" },
                   "require-admin-role":   { "branch": "tr/require-admin-role",   "state": "merged" } } },
    { "id": "t2", "task_ids": ["cache-list-responses"],
      "status": "capped", "start_commit": "a1b2c3d", "dirty_at_start": ["notes.md"],
      "build_iterations": 3 },
    { "id": "t4", "task_ids": ["report-cache-hit-rate"],
      "status": "pending", "start_commit": null, "dirty_at_start": null, "build_iterations": 0 }
  ],
  "tasks": {
    "cache-list-responses": { "status": "capped", "commit": "e4f5g6h", "design_rounds": 1,
                              "reviewer_invocations": 2,
                              "tests_claimed": "unit+int", "tests": "unit+int",
                              "tdd_behaviours": 0, "tdd_attempts": 0,
                              "consecutive_environmental": 0, "consecutive_unusable_verdicts": 0 }
  },
  "pending_completions": []         // Phase 4 반영을 기다리는 원격 완료 — 그리고 시도했다가 실패한
}                                   // 로컬은 Step 3 에서 바로 써 내려가기 때문
}
```

- **id 는 `run_id` 이고** 파일명이 그것을 담는다. 자릿수가 고정이라 "가장 최근 체크포인트" = 문자열 순으로 가장 큰 파일명이다 — 시각 파싱도, 복사하는 순간 틀어지는 파일시스템 mtime 도 필요 없다. **UTC** 인 이유: 로컬 시각은 DST 종료마다 한 시간을 되풀이해 문자열 순서가 최신을 뜻하지 않게 된다. 무작위 접미사는 같은 분에 시작한 두 실행이 파일명을 공유하고 `d-<run_id>-<n>` 결정 id 를 충돌시키는 것을 막는다 — append-only 설계가 명시적으로 허용하는 동시 실행이 바로 그 경우다.
- **단위가 시작할 때, 커밋하자마자, 그리고 끝날 때 쓴다** — 끝날 때만이 아니다. 가운데 쓰기가 Step 3 도중의 중단을 구현 루프가 아니라 완료 표시부터 재개하게 만든다(`SKILL.md` §인자). 그게 없으면 `pending` 이면서 커밋을 담은 체크포인트 상태가 아예 존재하지 않는다. 도중에 중단된 단위도 `start_commit` 과 `dirty_at_start` 가 이미 디스크에 있어야 한다. 없으면 재개가 복원할 기준선이 없어, 그 단위 자신의 작업으로 dirty 해진 트리에서 기준선을 다시 만들어 낸다.
- **`status`** 는 Phase 4 어휘에 `pending` 을 더한 것이다: `done` ✅ · `capped` ⚠️ · `skipped` ⏭️ · `unverified` ❓(끝났지만 커밋한 것을 뒷받침하는 것이 없음 — 전략이 주장한 테스트가 없거나, 커밋이 검증이 통과시킨 트리가 아니거나) · `pending`(**미완료** — 시작 안 했거나, *또는* 도중에 중단됨). `pending` 을 뺀 나머지는 다 끝난 것이다. 카운터는 `done` 에서 지워지고, `capped` 와 **`attempted: true` 인 `skipped`** 에서 올라가며, `unverified` 는 어느 쪽으로도 움직이지 않는다(`SKILL.md`). `skipped` 에 그 플래그가 필요한 이유: 이 실행이 아무것도 쓰기 전에 거절된 항목과 예산을 통째로 쓰고 포기된 항목이 같은 status 로 저장되는데 `autonomy.md` 는 둘째만 센다 — 필드가 없으면 올바르게 거절한 security 질문 둘이 아무것도 실패하지 않은 실행을 세우고, 이후 어떤 체크포인트 읽기도 그러면 안 됐다는 것을 알 수 없다. 플래그는 첫 리뷰어 디스패치 또는 첫 편집에서 켜지므로, 설계 상한에서 버려진 항목은 `build_iterations: 0` 과 함께 `attempted: true` 로 저장된다. Step 2 에 걸어 두면 그 행은 아무도 손대지 않은 항목과 구분되지 않는다. 판정을 여기 저장하고 다시 계산하지 않는 것이 재개된 실행이 ❓ 행을 다시 찍게 해 주는 것이다 — `tests` 옆의 `tests_claimed` 와 함께. *실제로 쓴* 것만 보고하는 행은 `none` 을 주장한 단위가 한 적 없는 주장을 못 지켰다고 말하게 된다. 변경 집합은 재개 시점에 이미 없으므로 문제된 경로는 다시 찍지 않는다. 남는 것은 주장과 그것을 확인해 준 것이 없다는 사실이고, 독자를 커밋으로 보내는 것이 그 둘이다. 그래서 임의 `중단`은 현재 단위를 카운터 그대로 `pending` 으로 남긴다: 재개는 그 단위를 남은 예산으로 이어서 들어가지, 예산을 새로 주며 처음부터 돌리지도 않고 상한에 닿은 것처럼 버리지도 않는다.
- **`dirty_at_start` 는 저장하지 다시 뜨지 않는다.** 이것이 단위 기준선의 나머지 절반이고, 재개 시점의 트리는 *이 단위 자신의 작업*으로 dirty 하다 — 거기서 다시 스냅샷을 뜨면 자기 편집을 남의 것으로 분류해 커밋에서 빠뜨리거나 재개할 때마다 멈추게 된다. `null` 은 아직 시작 안 함, `[]` 는 깨끗한 트리에서 시작했음을 뜻한다.
- **그룹 단위는 worker 를 기록한다.** 재개는 `state` 가 `returned`·`merged` 가 아닌 worker 만 다시 띄우고, 이미 있는 브랜치는 재사용하지 다시 만들지 않는다. 이것이 없으면 그룹 도중에 발동한 브레이크가 끝난 worker 의 브랜치를 버리거나 두 번 머지한다.
- **`SKILL.md` 스코프 표에 이름이 오른 모든 카운터가 그 표가 지정한 스코프로 여기에 있다** — 동기화할 목록이 아니라 규칙으로: `build_iterations` 와 `start_commit` 은 단위에, `design_rounds` · `reviewer_invocations` · `tdd_behaviours` · `tdd_attempts` 는 항목에, `consecutive_failures` 는 최상위에. 연속 2회 정지들도 카운터다(`BUILD-LOOP.md` §2c 의 `consecutive_environmental`, `DESIGN-LOOP.md` §1d 의 `consecutive_unusable_verdicts`) — 중단을 넘으며 0으로 돌아가는 카운터는 영원히 발동하지 않는 정지다. 카운터를 잘못된 층에 저장하는 것이 재개가 항목에 새 예산을 조용히 쥐여 주는 경로다.
- `--resume` 은 이 프로젝트의 가장 최근 체크포인트를 읽고 **status 가 `pending` 인 첫 단위**부터 잇는다. `capped`·`skipped`·`unverified` 단위는 끝난 것이지 재시도 대상이 아니다. `pending` 단위가 하나도 없는 체크포인트는 완료된 실행이다 — 그렇게 말하고 멈춘다, **`pending_completions` 가 비어 있지 않은 경우만 빼고.** 그때는 Phase 4 의 일괄 반영으로 재진입하고 그 외에는 아무것도 하지 않는다. 여기 저장된 레벨은 권한이 **아니다**: 무인 재개에는 `--auto` 를 다시 붙여야 한다. 무인은 언제나 명시적 선택이기 때문이다.
- **끝난 실행의 체크포인트는 지우지 않고 남긴다.** 다음 실행이 선행 분석으로 읽는 것이 이 파일이고(`PHASE-FORMAT.md` §Phase 1), 정렬과 그룹핑이 오직 여기에만 있다 — 성공했다고 지우면 신선도 표가 재사용하라고 추천하는 바로 그 기록을 지우는 것이다. 같은 `source_ref` 의 오래된 체크포인트는 정리해도 되고, 최신 것만 남기면 된다.
- `pending_completions` 가 비지 않은 동안에는 어떤 것도 끝난 것으로 치지 않는다.

## 왜 append-only 인가

자연스러운 설계는 결정당 레코드 하나를 두고 결과가 나오면 제자리에서 갱신하는 것이다. 그건 구체적이고 실제로 관측된 방식으로 실패한다 — 갱신할 레코드를 찾으려면 키가 필요하고, 키는 세션을 넘으며 어긋나고, 지나치게 넓은 매칭은 *다른 세션의 레코드*를 덮어쓴다. 그렇게 되면 로그는 비어 있는 것보다 나쁘다. 완전해 보이기 때문이다.

append-only 는 그 실패를 방어하는 대신 없앤다. 찾아서 다시 쓰는 일이 아예 없으니 과대매칭할 대상이 없다. outcome 줄이 없다는 것은 그 실행이 끝나지 않았다는 뜻이고, 그건 사실이며 알 가치가 있다.

따라오는 결과는 전부 이득이다:

- 백업 파일도, 복구 절차도, "필터가 너무 넓으면 exit 2" 게이트도 필요 없다.
- 같은 repo 의 동시 실행이 안전하게 append 한다. 모든 줄이 자기완결적이라 순서가 무관하다.
- 중단된 실행은 outcome 없는 decision 을 남긴다. 그건 아래 쿼리에서 제외되지 복구되지 않는다.

## 무엇을 남기고 무엇을 안 남기나

`autonomy.md` §등급 의 모든 결정을 남긴다 — **물어본 것도**, **수동 실행도** 포함해서. 무인 결정만 담긴 로그는 "이걸 자동화했다면 옳았을까?" 에 답할 수 없다. 비교군이 없기 때문이다.

`P0-verify` 레코드는 필드 둘을 더 갖는다: 승인된 텍스트를 **그대로** 담는 `"command"`, 그리고 그 텍스트가 repo 파일을 가리킬 때 그 파일의 해시인 `"command_source_hash"`. 나중 실행은 "여기서 이미 승인됐나?" 를 이렇게 답한다 — `step_id: "P0-verify"` · `mode: "asked"` · `chosen_index` 가 승인 선택지를 가리키고 · `command` 가 해석된 문자열과 같고 · **그리고** 해시가 여전히 일치하는 가장 최근 줄. 비슷함이 아니라 같음이다.

해시가 있어야 승인이 한 겹 얕지 않게 된다. `npm test` · `make test` · `./scripts/verify.sh` · `./gradlew test` 는 전부 포인터다: `git pull` 이 실제로 도는 것을 바꿔도 승인된 *텍스트*는 그대로다. 텍스트와 함께 `package.json`·`Makefile`·지목된 스크립트를 해시해 두면 내용이 바뀔 때 다시 묻는다 — 사용자가 승인한다고 생각했던 것이 바로 그것이다.

hard stop 도 남긴다(`H1-outward` · `H2-destructive` · `H3-tracker` · `H4-security`), repo 가 준 명령의 승인(`P0-verify`)도. 이것들은 언제나 `mode: "asked"` 이고 다이얼 이동을 채점하지 않는다 — 하지만 열 번 멈춘 실행과 한 번 멈춘 실행이 나중에 똑같이 읽혀서는 안 된다.

`skill_version` 은 `<스킬 이름>@<플러그인 매니페스트의 버전>` 이다. 매니페스트 없이 단독 설치돼 읽을 것이 없으면 `<이름>@unknown` 이라고 쓴다 — 지어낸 번호는 정직한 공백보다 나쁘다. 서로 다른 두 버전을 비교 가능한 것처럼 보이게 만들기 때문이다.

남기지 않는 것: 파일 내용, diff, 자격증명, 검토자의 지적 전문. `rationale` 은 한 줄이다. 이 로그는 *결정*에 관한 증거이고, 페이로드가 쌓이는 로그는 아무도 보관하고 싶지 않은 것이 된다.

## 한 단계를 채점하기

두 비율을 **서로 다른 모집단**에서 센다. 모집단을 틀리는 것이, 이 분석을 엄밀해 보이면서 아무 뜻도 없게 만드는 원인이다.

```
agreed 율   mode == "asked" 인 결정들에 대해            ≥ 0.9
clean 율    outcome 줄이 있는 결정들에 대해              ≥ 0.9
            clean = manual_intervention=false ∧ reverted=false ∧ capped=false
                      ∧ claim_met != "unmet"
n (asked)   ≥ 20
```

마지막 연언지는 그 필드를 지닌 유일한 단계인 `S2-test` 에만 문다. 이게 없으면 ❓ 단위가 줄줄이 나온 실행이 — Phase 4 가 전부 수동 확인 대상으로 표시한 그 단위들이 — 주장이 미달이었던 바로 그 결정을 자동화하라는 깨끗한 근거로 채점된다. 검사를 안 돌린 repo 는 `claim_met` 자체가 없고, 없는 필드는 이 연언지를 통과한다 — 그래서 그 결정들은 이 축에서 **clean 으로 집계된다**. 이건 덮을 구멍이 아니라 정직하게 밝힐 한계다: `report` 가 비율 옆에 `검사 안 함` 개수를 찍고, 근거가 대부분 `검사 안 함` 인 단계는 숫자가 시사하는 깨끗한 실행이 아니다.

**`agreed` 는 사람이 답한 결정만 센다.** 무인 실행된 것은 `chosen == recommended` 가 구조상 참이라, 그걸 넣으면 비율이 1.0 쪽으로 부풀고 분석이 "자동화했으니 자동화해도 됐다" 로 변한다. 질문의 전부는 추천이 사람이 *골랐을* 것과 같은가이고, 그 증거는 물어본 결정에만 있다.

하나가 아니라 **둘 다**. 동의율은 높은데 결과가 나쁘면 사람과 스킬이 **함께** 틀린 것이다 — 이 로그가 드러낼 수 있는 가장 위험한 양상이고, 동의율만 보면 안 보인다.

`manual_intervention` 이 하중을 받는 필드이자 가장 속이기 쉬운 필드다. 결정 이후 사용자가 방향을 틀거나 고치거나 넘겨받았으면 참이다 — 아주 조금이어도, 도움이 됐어도. **개입 없이 깔끔하게 성공한 것만 증거다.** 도움받은 성공을 무개입으로 적는다고 다이얼이 안전해지지 않는다. 안전하다고 말하는 숫자가 무의미해질 뿐이다.

## 로그를 쓰는 법

로그를 읽는 순간은 정확히 둘이고, 둘 다 사용자의 결정으로 끝난다.

### 1 · `task-routine report` — 성적표

로그를 읽어 표를 출력하고 아무것도 바꾸지 않는다. 이것이 주 용도다.

```
다이얼 근거 — 31회 실행 · 결정 214건 · outcome 있는 것 198건
214건 중 83건이 asked 였고, 나머지는 무인 실행이라 동의 증거를 갖지 않는다.
S2-test 주장 — met 18 · unmet 3 · unclaimed 2 · 검사 안 함 1

단계          asked   agreed   clean   영향받는 이동
S2-test          22     0.95    0.91   manual → assisted    ✓ 뒷받침됨
S1-design        14     0.86    1.00   manual → assisted    — n 부족 (20 필요)
P2-order         25     0.68    0.79   manual → assisted    ✗ 반대
S2-review        22     1.00    0.95   assisted → auto      ✓ 뒷받침됨

manual → assisted   뒷받침 1 · 데이터 부족 1 · 반대 1
assisted → auto     뒷받침 1

P2-order 는 25건 중 8건이 뒤집혔다. 이건 자율성에 대한 결과가 아니라 — 이 repo 에서 정렬 추천이
잘못 보정돼 있다는 뜻이다. 다이얼을 건드리기 전에 뒤집힌 결정들의 rationale 을 읽어라.
```

헤더 두 번째 줄도 장식이 아니다: `asked` 합계가 총계와 맞아떨어져야 읽는 사람이 표본 25건짜리 판정과 실행 25회짜리 판정을 구분할 수 있다. asked 결정이 하나도 없는 단계는 표에 아예 안 나오고, 그 부재는 근거가 아니다.

**hard stop 과 `P0-verify` 는 행으로 나오지 않는다.** 추천이 없는 `mode: "asked"` 라 `agreed` 가 구조상 `null` 이고, 채점하면 빈 모집단 위에서 비율을 계산하게 된다. 이들은 헤더 카운트와 자기 줄에 속한다 — *"hard stop 14건: H4-security 9 · H1-outward 3 · H2-destructive 2"* — 열네 번 멈춘 실행과 한 번 멈춘 실행이 똑같이 읽혀서는 안 되기 때문이다.

`영향받는 이동` 컬럼이 있는 이유: 근거는 단계별인데 다이얼은 전역이다. `auto` 에서만 무인이 되는 단계는 `manual → assisted` 에 대해 아무 말도 하지 않는다. 단계를 그것이 걸린 **이동**으로 묶고, 단계가 아니라 이동에 답한다.

### 2 · Phase 4 의 한 줄 — 새로 자격을 얻었을 때

한 단계가 두 문턱을 넘으면 정보로서 한 번만 말한다:

```
S2-test 가 asked 22건에서 agreed 0.95 / clean 0.91 에 도달했습니다 — 나머지는 `task-routine report`.
```

권유도, 프롬프트도 아니고, 절대 행동이 아니다. 자기 자율성을 스스로 채점하고 스스로 넓히는 스킬에는 게이트가 없는 것과 같다.

### 3 · 추천을 진단하기 — 사실 이쪽이 더 쓸모 있다

낮은 agreed 율은 대개 자동화에 대한 판정이 **아니다**. 이 repo 에서 추천 로직이 틀렸다는 뜻이다 — 변경 형태표가 이 코드베이스의 테스트 방식과 안 맞거나, 정렬 휴리스틱이 의존성을 잘못 읽고 있다. 이건 어느 레벨에서든 지금 당장 고칠 수 있고, 고치면 `auto` 사용자만큼 `manual` 사용자에게도 도움이 된다.

로그가 `<project-slug>` 아래 있으므로 범위는 구조상 프로젝트별이다. 한 단계가 어떤 repo 에서는 자율성을 얻고 다른 repo 에서는 못 얻을 수 있고, 프로젝트별 config 파일이 정확히 그걸 위해 있다.

## 로그가 말해줄 수 없는 것

- **n 이전엔 아무것도.** asked 20건 미만이면 건수만 보고하고 멈춘다. 3전 3승은 증거가 아니다.
- **한 번도 제시되지 않은 결정에 대해선 아무것도.** 추천이 억제된 단계는 아예 등장하지 않으므로, 그 부재는 좋은 성적이 아니다.
- **심각도에 대해선 아무것도.** 모든 줄의 무게가 같다. 되돌린 커밋 하나와 취향 불일치 하나가 똑같이 unclean 1건이고, 비율은 그 차이를 못 본다 — 비율만이 아니라 outcome 을 읽어라.

둘 중 하나라도 문턱을 못 넘는 단계는 그 자리에 둔다. 판정이 아니라 숫자를 보고한다 — 다이얼은 사용자가 올리고, 이 분석은 근거만 댄다.

## Never

- ❌ 로그의 줄을 고치거나 지우기
- ❌ `recommended_index` 를 배열에서 세지 않고 문서에서 옮겨 적기
- ❌ 무인 결정만 남기기
- ❌ 사용자가 개입했는데 `manual_intervention: false` 로 보고하기
- ❌ 이 분석만으로 묻지 않고 다이얼 올리기
