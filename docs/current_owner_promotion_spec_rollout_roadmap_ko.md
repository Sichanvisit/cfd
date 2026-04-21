# Owner Promotion Spec Rollout Roadmap

## 2026-04-04 Reinforcement

### Rollout End-State Clarification

Owner promotion should now be read as:

`runtime -> replay -> seed -> baseline -> candidate -> log_only -> canary -> bounded_live`

- `log_only` is not the final stage.
- `canary` means narrow-scope live consumption with tight rollback.
- `bounded_live` means explicit symbol/stage/risk bounds, not full autonomy.

### Coverage Engineering Rule

For sparse owners such as `forecast` and `belief`, the next bottleneck is no longer philosophy but coverage.
Each owner spec should explicitly define:

- `strict rows`
- `usable rows`
- `skip rows`
- top skip reasons
- rollout stop conditions when usable coverage does not improve

### Dual Surface Rule

- flat fields: ops / dashboard / CSV observability only
- nested payload: replay / reconstruction / future-proof detail

Flat fields must remain deterministic summaries derived from nested payloads.

### Coverage-First Operating Rule

The immediate bottleneck is now:

`usable coverage + audit + wiring stability`

not:

`new philosophy + direct live override`

Every owner rollout should therefore add, before more live authority:

- coverage dashboard
- skip-reason taxonomy
- counterfactual audit surface
- actual-vs-log-only drift surface
- trace assembly hardening checklist

### Confidence / Usage Boundary

Sparse owners should separate label quality from rollout authority.

- `high` / `medium`: strict rows, compare/gate usable
- `weak_usable`: baseline/diagnostic usable, not hard-gate by default
- `low_skip`: replay-only or coverage-only

Equivalent wording such as `strict / usable / skip` is allowed, but the usage boundary
must remain explicit in each owner spec.

### Wait-Family Overlay Rule

For `Barrier` bias correction, do not widen `correct_wait` first.
Prefer adding a wait-family diagnostic layer that preserves the main barrier labels while
capturing the character of waiting:

- `timing_improvement`
- `protective_exit`
- `reversal_escape`
- `neutral_wait`
- `failed_wait`

Initial rollout rule:

- keep `correct_wait` narrow and strict
- map existing wait clusters into wait-family subtypes
- use wait-family for diagnostics / usable-only follow-up before any compare-gate promotion

Reference:

- [current_wait_family_label_structure_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_wait_family_label_structure_v1_ko.md)

### Manual Good-Wait Teacher Truth Rule

For `Barrier` bias correction, a human-marked wait truth layer may be added without widening
the heuristic `correct_wait` rule first.

Official manual truth labels:

- `good_wait_better_entry`
- `good_wait_protective_exit`
- `good_wait_reversal_escape`
- `neutral_wait_small_value`
- `bad_wait_missed_move`
- `bad_wait_no_timing_edge`

Operating rule:

- start with recent `box/range regime` samples
- keep manual truth separate from barrier main labels
- keep manual truth separate from compare/gate until reviewed

Reference:

- [current_manual_wait_teacher_truth_spec_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_manual_wait_teacher_truth_spec_v1_ko.md)

### Episode-Centric Manual Truth Rule

Manual truth should not stay `wait-only forever`.

The adopted direction is:

- storage = `episode-first`
- operations = `wait-first`

Meaning:

- the current `manual_wait_teacher` stays active
- entry / exit coordinates are preserved as first-class truth coordinates
- entry / exit labels may remain nullable until those owners open

Reference:

- [current_manual_trade_episode_truth_model_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_manual_trade_episode_truth_model_v1_ko.md)
- [current_manual_trade_episode_truth_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_manual_trade_episode_truth_implementation_roadmap_ko.md)

### Manual Answer-Key Calibration Rule

The current manual truth corpus should now be read as an `answer key` above the heuristic owner layer.

It is primarily for:

- calibration
- bias correction
- casebook review

It is not primarily for:

- replay reconstruction
- mandatory closed-history matching
- direct model training ingestion

Reference:

- [current_manual_vs_heuristic_comparison_report_template_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_manual_vs_heuristic_comparison_report_template_v1_ko.md)

### Immediate Next Program

As of 2026-04-04, the recommended next execution block is:

1. keep `forecast / belief / barrier` in `log_only`
2. improve coverage and audit before more rollout authority
3. run `Barrier coverage engineering` before `Evidence` implementation
4. continue with `Barrier bias correction` after `BCE0~BCE7` and before any readiness-threshold relaxation
5. treat wiring stability as a first-class rollout risk
6. treat manual truth as a standalone answer key and build a manual-vs-heuristic comparison layer before using it as any training seed

Reference docs:

- [current_barrier_coverage_engineering_design_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_coverage_engineering_design_ko.md)
- [current_barrier_coverage_engineering_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_coverage_engineering_implementation_roadmap_ko.md)
- [current_barrier_bias_correction_checklist_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_bias_correction_checklist_v1_ko.md)
- [current_barrier_bias_correction_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_bias_correction_implementation_roadmap_ko.md)
- [current_manual_vs_heuristic_comparison_report_template_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_manual_vs_heuristic_comparison_report_template_v1_ko.md)

## 목적

이 문서는 `current_trader_style_owner_rearchitecture_blueprint_ko.md`와
`current_semantic_owner_maturity_alignment_map_ko.md` 사이를 실제 구현 문서 단위로
이어 주는 로드맵이다.

핵심 목적은 아래 두 가지다.

1. 이제부터는 추상 철학 문서만 늘리지 않고, 각 owner를 `실무 명세서`로 내려쓴다.
2. 각 owner를 같은 형식으로 승격시켜 `runtime -> replay -> seed -> baseline -> candidate -> log_only`
   체인으로 닫는다.

즉 이 문서는 “다음에 무엇을 구현할지”보다 한 단계 더 내려가서,
“다음에 어떤 명세 문서를 어떤 순서와 기준으로 만들지”를 고정하는 문서다.

## 현재 상태 요약

지금 기준으로는 아래가 맞다.

- `state25 / wait_quality / economic_target / candidate-gate-AI6`는 이미 높은 maturity에 올라와 있다.
- `forecast`는 `FSB0~FSB6` scaffold까지 완료됐고, 이제는 표본과 outcome quality를 쌓는 단계다.
- 반면 `Belief / Barrier / Evidence / Response Raw`는 runtime owner로는 중요하지만
  learning owner로는 아직 덜 닫혀 있다.

따라서 다음 메인은 “새 철학 도입”이 아니라
`각 owner를 명세서 단위로 승격`시키는 일이다.

## 앞으로 필요한 문서 단위

이제부터 owner별로 아래 형식의 `승격 명세서`를 만든다.

### 공통 섹션

각 owner 명세서에는 아래 항목이 반드시 들어간다.

1. `owner 역할 정의`
   - 이 owner가 무슨 질문을 맡는지
   - 무엇을 하면 안 되는지
2. `runtime direct-use fields`
   - 현재 시점에서 바로 쓸 수 있는 필드
   - leakage 금지 경계
3. `outcome label 규칙`
   - 라벨 이름
   - 라벨 판정 규칙
   - 경계/예외 규칙
4. `실패 모드`
   - 이 owner가 어떤 방식으로 틀릴 수 있는지
5. `최소 관측 지표`
   - 승격 중 계속 봐야 할 핵심 metric
6. `승격 중단 조건`
   - 어떤 수치가 나오면 rollout을 멈추는지
7. `replay / outcome bridge`
   - 어떤 로그를 어떤 결과와 다시 붙일지
8. `closed-history seed enrichment`
   - 어떤 컬럼을 어떤 조건에서 seed로 올릴지
9. `baseline auxiliary task`
   - sparse면 어떻게 skip할지
10. `candidate compare / gate`
   - compare summary에 어떻게 반영할지
11. `log_only overlay`
   - live를 바꾸지 않고 어떤 trace를 남길지

### 명세서의 성격

중요한 점은 이 문서들이 “아이디어 목록”이 아니라는 것이다.

- 이름만 적는 문서가 아니다
- 판정 규칙이 있어야 한다
- 실패 모드가 있어야 한다
- 중단 조건이 있어야 한다

즉 다음 단계 문서는 전부 `구현 명세 문서`여야 한다.

## owner별 순서

### 1. Belief owner 승격 명세서

이유:

- 현재 음수 청산, 늦은 청산, premature exit 문제와 가장 직접 연결된다.
- 다만 `exit 전용 owner`로 좁히면 안 되고, `thesis persistence owner`로 유지해야 한다.

현재 문서:

- [current_belief_owner_promotion_spec_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_belief_owner_promotion_spec_v1_ko.md)

v1 보강 원칙:

- `adaptive threshold / adaptive horizon`은 v2 예약 항목으로 둔다
- `precedence margin`은 deterministic precedence를 대체하지 않고 `conflict resolver`로 둔다
- `belief_input_trace_v1 / belief_action_hint_v1`를 같이 남겨 Belief를 독립 부품이 아니라 decision-chain owner로 유지한다

핵심 라벨 초안:

- `correct_hold`
- `wrong_hold`
- `correct_flip`
- `missed_flip`
- `premature_flip`

핵심 metric 초안:

- `wrong_hold_ratio`
- `premature_flip_ratio`
- `missed_flip_ratio`
- `belief_break_to_exit_lag`

### 2. Barrier owner 승격 명세서

이유:

- 지금 barrier는 차단 owner로는 강하지만, 아직 “막아서 무엇을 지켰고 무엇을 놓쳤는가”가 없다.
- overblock과 underblock을 비용 기반으로 다뤄야 한다.

현재 문서:

- [current_barrier_owner_promotion_spec_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_owner_promotion_spec_v1_ko.md)

핵심 라벨 초안:

- `avoided_loss`
- `missed_profit`
- `correct_wait`
- `overblock`
- `relief_success`
- `relief_failure`

핵심 metric 초안:

- `overblock_ratio`
- `avoided_loss_rate`
- `missed_profit_rate`
- `false_relief_rate`

### 3. Evidence owner 승격 명세서

이유:

- 중요도는 매우 높은데, 라벨 오염 위험도 가장 크다.
- 구현 순서는 Belief/Barrier 뒤가 맞지만, 정의 작업은 엄격해야 한다.

핵심 라벨 초안:

- `true_signal`
- `fake_signal`
- `trap_signal`
- `exhaustion_signal`
- `late_signal`

핵심 metric 초안:

- `fake_signal_ratio`
- `trap_signal_ratio`
- `late_signal_ratio`
- `evidence_conflict_to_loss_ratio`

### 4. Response Raw owner 승격 명세서

이유:

- raw event inventory는 풍부하지만, 아직 owner 경계와 replay chain이 약하다.
- 범위가 커지기 쉬워 Evidence 뒤로 미루는 것이 안전하다.

핵심 축:

- raw event family
- raw motif / candle / structure subsystem
- `raw_event -> transition -> outcome`

### 5. Action Utility Shadow 명세서

이유:

- 진짜 “하나의 decision chain”으로 묶이는 마지막 단계다.
- 지금 즉시 live 전환이 아니라 반드시 shadow/log-only부터 가야 한다.

액션 후보:

- `enter`
- `wait`
- `hold`
- `reduce`
- `exit`
- `flip`

## 예외: Forecast는 별도 owner 승격 명세보다 운영 누적 우선

`forecast`는 지금 새로 spec을 열기보다,
이미 만든 `FSB0~FSB6` 체인을 실제로 강하게 작동시키는 게 우선이다.

즉 forecast의 현재 우선순위는:

1. `expected_path / realized_path / forecast_error_type`를 더 안정화
2. outcome coverage를 누적
3. auxiliary task readiness를 실제로 여는 것

따라서 `forecast`는 새 승격 명세보다 `운영 누적 + 품질 강화`가 먼저다.

## 단계별 완료 기준

### 명세서 완료

아래가 들어가면 해당 owner 명세서는 완료로 본다.

- 역할 정의
- 라벨 판정 규칙
- 실패 모드
- 최소 관측 지표
- 승격 중단 조건
- bridge / seed / baseline / compare / overlay 설계

### 구현 착수 가능

아래가 되면 실제 구현으로 넘어간다.

- 라벨 경계가 겹치지 않는다
- leakage 금지 문장이 명확하다
- sparse일 때 skip 기준이 있다
- candidate compare에 어떤 식으로 warning/blocking을 넣을지 정해졌다

### owner 승격 완료

아래가 보이면 그 owner는 현재 단계 승격이 끝난 것으로 본다.

1. `runtime bridge`
2. `replay / outcome bridge`
3. `seed enrichment`
4. `baseline auxiliary`
5. `candidate compare / gate`
6. `log_only trace`

## 권장 실행 순서

1. `Belief owner 승격 명세서`
2. `Barrier owner 승격 명세서`
3. `Evidence owner 승격 명세서`
4. `Response Raw owner 승격 명세서`
5. `Action Utility Shadow 명세서`

한 줄로 줄이면:

`이제부터는 owner마다 “좋은 철학 문서”가 아니라, 라벨 규칙과 중단 조건이 있는 승격 명세서로 내려가며 쌓는다.`
