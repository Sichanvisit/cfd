# Current Execution Authority Integration Design

## 목적

이 문서는 현재 CFD 실행 계층의 `authority split`을 명시하고,
다음 단계에서 어떤 식으로 authority integration을 시작할지 설계 수준에서 고정한다.

핵심 문제는 모델이나 shadow가 없어서가 아니다.

> 경제적 / semantic / state25 계산 계층은 이미 충분히 올라와 있지만,
> 실제 live execution authority는 아직 rule-policy orchestrator 쪽에 남아 있다.

즉 지금 필요한 것은 새 owner를 더 만드는 일이 아니라,
`누가 실제로 진입/청산을 결정하는지`를 bounded하게 재배치하는 일이다.

---

## 현재 Authority Map

### Entry

현재 entry authority는 대략 아래 순서로 분해된다.

1. baseline 점수 흐름이 먼저 기본 action을 만든다
2. `dynamic_threshold`가 stage / session / ATR / context / pyramid relief로 조정된다
3. semantic live guard는 여기서 `threshold_after`만 바꾼다
4. utility gate가 준비되어 있으면 hard skip authority를 가진다
5. utility가 없거나 fallback일 때만 legacy/hybrid score threshold가 마지막 점수 문턱이 된다
6. 그 이후에도 cluster / box-middle / pyramid / probe / consumer / order-block guard가 다시 veto를 가진다
7. 최종 실행은 broker order send가 결정한다

정리:

- semantic은 `action creator`가 아니라 `threshold modifier`
- baseline이 `no_action`이면 semantic은 현재 개입권이 없다
- utility gate와 post-entry guards가 semantic보다 더 높은 authority를 가진다

### Exit

현재 exit authority는 utility winner가 아니라 orchestrator 순서가 지배한다.

1. exit utility / wait utility는 계산된다
2. 하지만 실제 실행권은 hard risk guard가 우선한다
3. 그 다음 recovery plan이 들어간다
4. `recovery_wait_hold`는 강한 hold veto가 된다
5. partial exit / break-even / stop-up은 관리 authority다
6. managed exit plan은 `emergency -> protect -> adverse -> mid-stage`의 순차 정책이 우선한다
7. 그 다음에야 scalp / reversal exit이 들어온다

정리:

- utility는 입력 계층이다
- 실권은 risk / recovery / managed-exit policy orchestrator가 가진다

### Semantic / State25 / Shadow / Breakout

- semantic promotion guard owner는 현재 명시적으로 `rule_baseline`
- semantic live는 `disabled / log_only / alert_only / threshold_only / partial_live`
  모드뿐이며 action synthesis owner가 아니다
- exit semantic rollout은 더 보수적이고 entry-first baseline owner 전제를 유지한다
- state25 candidate는 여전히 `log_only`
- state25 threshold/size surface도 live writeback이 아니라 hint surface다
- breakout은 live runtime에서 이미 감지되지만, 아직 detail-only / log-only semantic owner다
- breakout은 offline에서 manual/replay alignment, canonical seed promotion, preview dataset export까지 닫혀 있다

정리:

- semantic = threshold/alert 보조 authority
- state25 = log-only 관측 authority
- shadow = bounded candidate 평가 authority
- breakout = offline 검증이 끝난 candidate source

---

## Breakout Line의 현재 의미

breakout 라인은 별도 연구 트랙이 아니라, authority integration 다음 단계에서 재사용할 수 있는
`검증된 candidate source`다.

현재 breakout 구조는 다음 한 문장으로 정리된다.

> live runtime에서는 breakout을 행동 전환 이벤트로 감지만 하고,
> offline replay/manual 라인에서 그 이벤트를 검증하고,
> 검증된 것만 canonical seed로 승격해서,
> 마지막에 breakout 전용 preview training set으로 내보내는 구조다.

흐름은 아래와 같다.

- `runtime detect`
- `detail-only 저장`
- `manual/replay alignment`
- `recovery/backfill`
- `canonical seed promotion`
- `preview dataset export`

여기서 중요한 점은 두 가지다.

1. no-leakage 경계가 이미 있다
   - live runtime breakout 감지는 future/manual truth를 직접 쓰지 않는다
2. breakout은 이미 offline 검증과 preview dataset export까지 닫혔다
   - 즉 live authority에 바로 올리면 안 되지만,
     `AI2 candidate bridge`에 편입할 수 있는 충분한 근거가 있다

---

## 지금 왜 막히는가

최근 bounded observation의 결론은 이미 분명하다.

- `threshold_applied_total = 0`
- `partial_live_total = 0`
- counterfactual `recent_threshold_would_apply_count = 0`
- counterfactual `recent_partial_live_would_apply_count = 0`
- `rollout_promotion_readiness = blocked_no_eligible_rows`

즉 지금은 단순히 semantic rollout mode를 더 올린다고 해결되지 않는다.

실제 blocker는 아래 두 층이 동시에 있다.

1. authority split
   - semantic/state25/shadow가 live action owner가 아니어서 `baseline_no_action` 구간에 개입하지 못한다
2. eligibility scarcity
   - baseline action coverage, symbol allowlist, semantic timing quality 문제 때문에
     threshold / partial-live candidate 자체가 잘 안 생긴다

이 둘 중 첫 번째를 건드리지 않으면 두 번째를 아무리 개선해도
semantic은 계속 보조 계층에 머물 가능성이 높다.

---

## 설계 원칙

### 원칙 1. Hard Risk / Broker Finality는 유지

authority integration은 `무조건 모델이 최종 결정`을 뜻하지 않는다.

아래는 계속 최종 veto / finality를 유지한다.

- hard risk guard
- mandatory recovery safety path
- broker order send 성공 여부

### 원칙 2. Entry Candidate Authority를 먼저 통합

현재 가장 큰 손실은 `baseline_no_action`일 때 semantic/state25가 무력하다는 점이다.

따라서 첫 통합 대상은 entry다.

목표는:

- semantic/state25/shadow/breakout이 bounded 조건에서 `candidate action`을 제안할 수 있게 하고
- utility gate와 후단 guard는 그 candidate를 검사하는 쪽으로 내려오게 만드는 것

즉:

- 지금: `baseline action -> semantic threshold tweak`
- 다음: `baseline or semantic/state25/shadow/breakout candidate action -> unified authority gate`

### 원칙 3. Utility Gate는 Hard Stop이 아니라 Authority Consumer가 되어야 한다

현재 utility gate는 준비되면 semantic보다 먼저 skip authority를 가진다.

다음 단계에서는 utility gate가

- semantic/state25 candidate action을 받아
- hard skip만 하는 것이 아니라
- `approve / reject / down-rank / partial-size` 중 하나를 내는 consumer가 되어야 한다

### 원칙 4. Exit는 Orchestrator Contract를 먼저 드러내고 나중에 통합

exit는 entry보다 복잡하고 risk-sensitive하다.

따라서 다음 단계에서 바로 exit owner를 뒤집지 않는다.

먼저 필요한 것은:

- recovery / managed_exit / utility / semantic 입력을 하나의 contract로 정리
- 어떤 층이 어떤 이유로 exit를 결정했는지 일관된 authority trace를 남기는 것

즉 exit는 `authority rewrite`보다 `authority normalization`이 먼저다.

### 원칙 5. State25는 Hint에서 Bounded Runtime Consumer로 승격

state25 candidate의 threshold/size hint는 이미 잘 만들어져 있다.

문제는 그것이 live에서 소비되지 않는다는 점이다.

다음 단계에서 state25는:

- 여전히 full owner는 아니지만
- bounded runtime에서
  - `entry_threshold`
  - `size_multiplier`
  - `stage_bias`
  같은 실행 surface에 실제로 반영되는 첫 consumer를 가져야 한다

### 원칙 6. Breakout은 먼저 Candidate Source로 편입하고, Owner 승격은 나중에 본다

breakout은 이미 runtime detect, manual/replay alignment, canonical seed promotion,
preview dataset export까지 닫혀 있다.

하지만 현재는:

- live execution owner가 아니고
- detail-only / log-only 계층이며
- no-leakage 경계를 유지해야 한다

따라서 다음 단계에서 breakout을 바로 live owner로 올리면 안 된다.

먼저 해야 할 일은:

- breakout runtime / overlay / preview-trained output을
  `AI2 unified candidate surface`에 `breakout_candidate`로 편입하는 것
- utility gate와 후단 guard가 그 candidate를 동일 계약으로 소비하게 만드는 것

즉 breakout의 1차 승격 목표는 `owner replacement`가 아니라
`bounded candidate source integration`이다

### 원칙 7. Breakout 문제는 Threshold보다 Input Contract를 먼저 고친다

최근 raw audit 결과는 breakout 쪽 병목을 더 좁혀서 보여준다.

- `breakout_up_nonzero_count = 0`
- `breakout_down_nonzero_count = 0`
- `direction_none_count = 145`
- `state_pre_breakout_count = 145`
- `raw_blocker_family = missing_breakout_response_axis`

즉 지금 문제는 breakout이 단지 너무 보수적인 것이 아니라,
현재 runtime response surface가 breakout runtime이 기대하는 언어로 번역되지 않고 있다는 점이다.

한 줄로 말하면:

> 지금은 breakout이 없는 것이 아니라,
> `breakout`이라는 언어로 번역이 안 된 상태다.

따라서 현 단계에서 threshold나 overlay 문턱을 먼저 조정하면 안 된다.
지금은 `0 입력 위에서 threshold를 만지는 것`에 가깝기 때문이다.

### 원칙 8. Breakout Recovery는 `bridge + upstream` 두 단계로 본다

breakout 축 복구는 한 번에 끝나는 일이 아니다.

1. runtime bridge
   - 기존 response axis를 bounded proxy breakout axis로 임시 연결
   - 목적은 현재 AI2 / runtime 관측을 살리는 응급처치
2. upstream axis materialization
   - response surface 쪽에서 진짜 `breakout_up/down` 축을 정식으로 만들기
   - 목적은 장기적 semantic consistency와 학습 정합성 확보

즉:

- `bridge = 응급처치`
- `upstream = 정식 수선`

authority integration은 이 둘을 함께 바라보되,
실제 구현 순서는 bridge가 먼저다.

### 원칙 9. Readiness와 Breakout Type을 먼저 세우고, Threshold는 나중에 본다

현재 recent payload에서는 `micro_breakout_readiness_state`도 거의 비어 있다.

따라서 breakout candidate를 AI2에 제대로 연결하려면,
단순 `UP/DOWN` 방향만이 아니라 아래 두 층을 먼저 세워야 한다.

1. readiness surrogate
   - response axis
   - confirm / continuation score
   - volatility / structure proximity
   를 이용해 최소한의 `PRE / READY` 상태를 유도
2. breakout type taxonomy
   - `initial_breakout`
   - `reclaim_breakout`
   - `continuation_breakout`

중요한 점:

- `upper_break_up`
- `mid_reclaim_up`
- `lower_break_down`
- `mid_lose_down`

을 모두 같은 breakout으로 뭉개면 semantic이 붕괴할 수 있다.
처음 runtime bridge는 상단/하단 대칭 proxy로 시작할 수 있지만,
type은 분리해서 기록하고 이후 audit로 비대칭을 다시 확인해야 한다.

### 원칙 10. 다음 병목은 Direction Resolver와 Confirm Conflict Resolver다

axis bridge와 readiness surrogate 이후 현재 breakout 병목은 더 좁혀졌다.

- `breakout_up/down`은 이제 recent row에서 nonzero가 나온다
- readiness surrogate도 일부 row에서 `COILED / BUILDING`을 만든다
- 하지만 대부분 row는 아직 `direction = NONE`
- 겨우 살아난 `initial_breakout` 1건도 `forecast confirm`과 충돌해 `confirm_conflict_hold`로 보류된다

즉 지금 질문은 더 이상:

- breakout을 읽을 수 있는가?

가 아니라,

- direction을 어떻게 더 잘 만들 것인가?
- breakout과 forecast confirm이 충돌할 때 누가 owner이고 누가 adjuster인가?

로 이동했다.

### 원칙 11. Forecast Confirm은 Owner가 아니라 Adjuster로 둔다

현재 단계에서 breakout event와 forecast confirm은 같은 owner로 보면 안 된다.

- breakout owner
  - 이벤트 발생 여부
  - 방향
  - breakout state
- forecast owner
  - 방향 확인
  - 지속 가능성
  - 실패 위험 보정

따라서 forecast confirm은 breakout owner를 직접 대체하는 주인이 아니라,
`veto or confidence adjuster`로 두는 것이 맞다.

중요한 점:

- conflict가 있다고 해서 breakout 후보를 바로 0으로 죽이면 안 된다
- 그렇다고 conflict를 무시하고 바로 `ENTER_NOW`로 올려도 안 된다

즉 구조는:

- `즉시 무효`보다
- `강등(demotion)`

에 가깝게 가야 한다.

### 원칙 12. Conflict는 Hold 일변도가 아니라 Action 강등으로 처리한다

현재 bounded/log-only 단계에서는 conflict 시 hold가 기본값인 것은 맞다.

하지만 지금처럼 `confirm_conflict_hold`만 남기면 breakout candidate surface가 지나치게 빈약해진다.
다음 단계에서는 최소한 아래와 같은 중간 상태를 두는 것이 맞다.

- `WATCH_BREAKOUT`
- `PROBE_BREAKOUT`

즉:

- breakout 강함 + forecast 동의 -> `ENTER_NOW`
- breakout 강함 + forecast 약한 반대 -> `WATCH_BREAKOUT` 또는 `PROBE_BREAKOUT`
- breakout 약함 + forecast 강한 반대 -> `WAIT_MORE`
- breakout 없음 -> `WAIT_MORE`

이렇게 가야 breakout owner가 완전히 죽지 않으면서도 live authority를 건드리지 않을 수 있다.

### 원칙 13. Direction Resolver는 Type별로 분리한다

direction resolver가 모든 breakout 장면을 하나의 규칙으로 처리하면,
지금처럼 `NONE` 비율이 비정상적으로 높게 남을 수 있다.

따라서 다음 단계에서는 최소한 아래처럼 나눠야 한다.

- `initial_breakout` resolver
  - `upper_break_up`
  - `lower_break_down`
  비중을 더 높게
- `reclaim_breakout / continuation_breakout` resolver
  - `mid_reclaim_up`
  - `mid_lose_down`
  - `continuation_score`
  - confirm 관련 보정
  비중을 더 높게

이 원칙 아래에서 confirm fallback은 direction의 주인이 아니라,
애매한 동률을 깨는 마지막 단계 정도로만 써야 한다.

### 원칙 14. Breakout과 Forecast Confirm은 서로 다른 Owner로 본다

다음 단계에서 breakout owner와 forecast confirm owner를 한 함수 안에 섞어 처리하면,
더 보수적인 쪽이 다른 쪽을 영구적으로 눌러버릴 가능성이 높다.

따라서 두 입력은 아래처럼 분리해서 보는 것이 맞다.

- breakout owner
  - 이벤트 발생 여부
  - 방향
  - state 생성
- forecast owner
  - 방향 확인
  - 지속 가능성 보정
  - 실패 위험 보정

이 둘이 충돌할 때는

- `즉시 무효`

보다

- `action demotion`

구조가 더 적합하다.

### 원칙 15. `WAIT_MORE`와 `ENTER_NOW` 사이 중간 상태를 둔다

bounded candidate 단계에서는 action surface가 너무 거칠면 안 된다.

특히 breakout 쪽은 현재:

- `ENTER_NOW`
- `WAIT_MORE`

사이의 표현력이 부족해서, conflict가 생기면 대부분 hold 한 가지로 눌릴 가능성이 있다.

따라서 다음 단계에서는 최소한 아래 중간 상태를 두는 것이 맞다.

- `WATCH_BREAKOUT`
- `PROBE_BREAKOUT`

즉 다음 action surface는 단순 2분법이 아니라,
`enter / watch / probe / wait` 구조로 보는 것이 맞다.

---

## Authority Integration 시작점 4개

### 1. Entry Candidate Synthesis Bridge

파일 중심:

- `backend/services/entry_try_open_entry.py`
- `ml/semantic_v1/promotion_guard.py`

해야 할 일:

- baseline action이 없더라도 bounded semantic/state25 candidate action을 생성할 수 있는 bridge 추가
- semantic/state25/shadow/breakout candidate를 unified input surface로 모으기
- utility gate 이전에 `candidate_action_source`를 결정하기

핵심 효과:

- `baseline_no_action`이 semantic 무력화 이유가 되지 않음

### 2. Breakout Candidate Bridge

파일 중심:

- `backend/services/entry_try_open_entry.py`
- `backend/services/breakout_event_runtime.py`
- `backend/services/breakout_event_overlay.py`
- `backend/services/breakout_shadow_preview_training_set.py`

해야 할 일:

- breakout runtime / overlay / preview line을 authority integration 쪽 candidate surface와 연결
- 먼저 기존 response axis를 proxy breakout axis로 bridge
  - 상단:
    - `upper_break_up`
    - `mid_reclaim_up`
  - 하단:
    - `lower_break_down`
    - `mid_lose_down`
- direction/state가 실제로 살아나는지 raw audit로 재검증
- `micro_breakout_readiness_state`가 비어 있을 때 surrogate readiness를 추가
- `initial / reclaim / continuation` breakout type을 분리 기록
- 그 다음에야 overlay와 candidate bridge에서 `WAIT_MORE -> ENTER_NOW` 일부가 생기는지 확인
- `breakout_candidate_action`
- `breakout_candidate_confidence`
- `breakout_candidate_reason`
- `breakout_candidate_source`
  같은 bounded candidate 필드를 만들기
- 이 candidate는 live manual truth를 직접 쓰지 않고
  runtime breakout 감지 + preview-trained output만 사용하도록 고정하기

핵심 효과:

- breakout 라인이 별도 분석 자산으로만 남지 않고
  `baseline_no_action` 구간의 실전 candidate source로 재사용된다
- threshold를 먼저 낮추지 않고도 breakout이 실제 runtime 언어로 번역되기 시작한다

### 3. Utility Gate Recast

파일 중심:

- `backend/services/entry_try_open_entry.py`
- `backend/core/config.py`

해야 할 일:

- `utility_only` hard skip 구조를 authority-aware decision contract로 바꾸기
- 기존 `skip`만 있는 구조를:
  - `reject`
  - `approve`
  - `partial_size`
  - `shadow_only`
  등으로 세분화하기

핵심 효과:

- utility가 semantic/state25 candidate를 무조건 죽이는 구조에서 벗어남

### 4. State25 Live Consumer Bridge

파일 중심:

- `backend/services/teacher_pattern_active_candidate_runtime.py`
- `backend/services/entry_try_open_entry.py`

해야 할 일:

- `candidate_log_only_entry_threshold_hint`
- `candidate_log_only_size hint`
를 bounded runtime flag 하에서 실제 entry surface에 반영하기

핵심 효과:

- state25가 진짜 live-adjacent authority를 일부 갖기 시작함

---

## 다음 단계의 성공 기준

authority integration의 첫 성공은 아래처럼 정의한다.

1. `baseline_no_action`인데도 bounded candidate action이 생성되는 case가 생긴다
2. breakout raw audit에서 `breakout_up/down nonzero`와 `direction != NONE`가 실제 생긴다
3. breakout readiness/type이 빈 값이 아니라 bounded surrogate 분포를 갖는다
4. utility gate가 그 candidate를 무조건 skip하지 않고 decision trace를 남긴다
5. breakout candidate도 같은 trace 안에서 source별 성능 비교가 가능해진다
6. state25 threshold/size hint 중 일부가 bounded runtime에 실제 반영된다
7. log-only observation에서 `would_apply_count > 0`가 아니라
   실제 bounded `threshold_applied` 또는 `partial_live` 사례가 생긴다
8. approval / SA9 knowledge base에 authority source가 기록된다

---

## 하지 말아야 할 것

- semantic을 바로 full action owner로 승격
- breakout을 검증 없이 직접 live owner로 승격
- breakout input contract가 비어 있는 상태에서 threshold만 먼저 낮추기
- exit orchestrator를 한 번에 뒤집기
- state25 hint를 검증 없이 full live threshold/lot에 전면 반영
- utility gate를 제거하고 semantic에 바로 final authority 부여

---

## 한 줄 결론

다음 단계의 본질은 모델 성능 미세조정이 아니라 authority 재배치다.

> `semantic / state25 / shadow / breakout`을 계속 advisory layer로 둘 것인지,
> 아니면 bounded candidate authority를 실제 execution path에 연결할 것인지

이 질문에 답하는 첫 구현이 이제 필요하다.
