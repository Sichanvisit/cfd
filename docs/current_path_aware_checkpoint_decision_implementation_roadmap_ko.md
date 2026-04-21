> Scene-axis extension note:
> 이 로드맵은 checkpoint 엔진의 기본 뼈대(`PA0~PA9`)를 다룬다.
> 이후 scene 축 확장은 별도 `SA` 트랙으로 이어지며,
> 기준 문서는
> [current_checkpoint_scene_axis_design_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_scene_axis_design_v1_ko.md)
> 와
> [current_checkpoint_scene_axis_scope_lock_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_scene_axis_scope_lock_v1_ko.md)
> 다.
> 핵심 원칙은
> `surface -> checkpoint -> scene -> score -> action -> hindsight`
> 구조를 유지하되,
> scene은 action을 단독 결정하지 않고 hint / gate / bias로만 작동하게 만드는 것이다.
>
> `PA1~PA6`의 현재 운영 구조 재정렬 패치는
> [current_pa16_realignment_patch_plan_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_pa16_realignment_patch_plan_ko.md)
> 를 따른다.

# Current Path-Aware Checkpoint Decision Implementation Roadmap

## Roadmap Reinforcement Note

이번 보강 메모는 기존 PA 로드맵을 뒤집는 것이 아니라,
실제 구현에서 가장 흔들리기 쉬운 지점을 미리 고정하는 목적이다.

### PA0 reinforcement

`checkpoint_type`과 `scene`은 다른 축이다.

- `checkpoint_type`
  - leg 안에서의 구조적 위치
- `scene`
  - 지금 시장에 벌어진 장면

즉 같은 `FIRST_PULLBACK_CHECK`에서도
scene은 `pullback_continuation`일 수도 있고
`failed_transition`일 수도 있다.

한 줄 원칙:

> `checkpoint_type`은 위치 축,
> `scene`은 장면 축이다.
> 둘은 같은 라벨이 아니고 서로를 대체하지 않는다.

### PA1 reinforcement

Leg detector에서는 아래 3가지를 반드시 문서화하고 검증한다.

1. 62% 이상 되돌림이 같은 leg의 깊은 pullback인지, 새 leg인지
2. partial exit 후 남은 runner가 기존 leg 소속인지
3. 전량 청산 후 rebuy가 새 leg인지, 기존 thesis 연장인지

이 3개가 흔들리면 PA3 이후 row 의미가 전부 흔들린다.

### PA4 reinforcement

각 score는 이름만 정하지 말고 핵심 입력 feature도 같이 잠근다.

- `runtime_continuation_odds`
  - swing 방향 일관성
  - 되돌림 깊이 vs ATR
  - 추세 방향 볼륨 일치도
- `runtime_reversal_odds`
  - 구조 깨짐 여부
  - 반대 방향 볼륨 확대
  - 최근 push 약화 속도
- `runtime_hold_quality_score`
  - 현재 PnL vs MFE
  - `bars_since_last_push`
  - `runner_secured`
- `runtime_partial_exit_ev`
  - 중요 타겟 접근도
  - giveback 확대 여부
  - 남은 runner 기대값
- `runtime_full_exit_risk`
  - thesis break 신호
  - 구조 붕괴 강도
  - MAE 확대 속도
- `runtime_rebuy_readiness`
  - 구조 재형성 여부
  - retest/reclaim 품질
  - 이전 thesis 유효성

### PA5 reinforcement

Hindsight label은 아래 원칙을 기본으로 둔다.

- 기본 horizon: checkpoint 이후 `20 bars`
- `MFE >= 2R` 도달 후 50% 이상 반납
  - `PARTIAL_THEN_HOLD` 우세
- `MAE <= -1R`
  - `FULL_EXIT` 우세
- `MFE >= 1.5R` 유지
  - `HOLD` 우세
- `±0.3R` 안에서 횡보
  - `WAIT` 또는 `TIME_DECAY` 계열

또한 너무 엄격한 단일 정답 과적합을 막기 위해
`hindsight_acceptable_actions_json` 같은 보조 허용 정답 구조도 허용한다.

### PA8 reinforcement

Bounded adoption에는 rollout 규칙뿐 아니라 rollback 기준도 같이 있어야 한다.

최소 예시:

- canary 시작 후 MDD가 기존 대비 `5%p` 이상 악화 -> rollback
- `FULL_EXIT precision`이 기존 대비 `10%p` 이상 하락 -> rollback
- `premature_full_exit_rate` 상승 -> rollback
- 최소 `50`개 checkpoint action 전까지는 확정 판정 보류

### PA-SA dependency note

두 트랙은 아래처럼 의존한다.

```text
PA0 ---------------------- SA0
PA1
PA2
PA3 ---------------------- SA1
PA4 ---------------------- SA2
                          SA2.5
PA5 ---------------------- SA3
PA6 ---------------------- SA6
PA7 ---------------------- SA4
PA8 ---------------------- SA5 / SA7
PA9 ---------------------- SA8
```

핵심 의존:

- `SA1`은 `PA3` 이후
- `SA2`는 `PA4`와 병렬 가능
- `SA6`은 `PA6` 이후
- `SA0`은 `PA0`과 병렬 가능

## 목적

이 문서는
[current_path_aware_checkpoint_decision_implementation_spec_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_path_aware_checkpoint_decision_implementation_spec_v1_ko.md)
를 실제 구현 순서로 변환한 로드맵이다.

핵심 목적은 다음 하나다.

> path-aware checkpoint 구조를 한 번에 크게 붙이지 않고,
> `instrumentation -> passive scoring -> hindsight labeling -> bounded runtime adoption`
> 순서로 안전하게 올린다.

이 로드맵은 `좋은 아이디어 정리`가 아니라,
실제 구현을 시작할 때 무엇부터 만들고 어떤 검증을 통과해야 다음 단계로 넘어갈지 고정하기 위한 문서다.

---

## 현재 위치

현재 상위 프로젝트 상태는 아래처럼 읽는 것이 맞다.

1. `P0 wrong-side active-action conflict`는 응급 수정으로 계속 진행 중
2. `MF17 initial_entry_surface`는 signoff가 끝났고 activation guard 해제 대기 중
3. 다음 핵심 구조 질문은
   `follow_through / continuation_hold / protective_exit`
   를 leg / checkpoint 중심으로 재구성하는 것이다

즉 지금 이 로드맵은:

- `initial_entry_surface`를 다시 만드는 작업이 아니라
- 기존 4 surface 위에 `checkpoint context layer`를 올리는 작업이며
- `CL orchestrator` 전에 학습 대상과 runtime row 구조를 먼저 바르게 정의하는 단계다

---

## 구현 원칙

### 1. v1은 log-only와 bounded adoption을 분리한다

처음부터 runtime action을 바꾸지 않는다.
먼저 row와 score를 쌓고, hindsight eval을 붙인 뒤, 마지막에 bounded adoption으로 간다.

### 2. entry와 management action을 섞지 않는다

v1에서 `initial_entry_surface`는 기존 진입 action 체계를 유지한다.
checkpoint layer는 주로 management action을 다룬다.

### 3. hindsight leakage를 금지한다

runtime score와 hindsight label은 계산 경로와 저장 경로를 분리한다.

### 4. checkpoint는 구조 변화가 있을 때만 생성한다

매 bar checkpoint를 만들지 않는다.
`판단이 다시 필요한 순간`만 자른다.

---

## 전체 구현 순서

이 로드맵은 아래 순서로 진행한다.

1. `PA0 Scope Lock / KPI Freeze`
2. `PA1 Leg Detector Instrumentation`
3. `PA2 Checkpoint Segmenter Instrumentation`
4. `PA3 Checkpoint Context Builder / Storage`
5. `PA4 Passive Score Calculation`
6. `PA5 Hindsight Label / Dataset / Eval`
7. `PA6 Best Action Resolver`
8. `PA7 Harvest / Manual-Exception Queue`
9. `PA8 Bounded Runtime Adoption`
10. `PA9 CL Hand-off Preparation`

---

## PA0. Scope Lock / KPI Freeze

### 목적

- 구현 범위를 v1 기준으로 고정한다
- 성공 기준 KPI를 먼저 고정한다
- entry action과 management action의 경계를 명확히 한다

### 결정할 것

- `initial_entry_surface`는 기존 taxonomy 유지
- checkpoint layer는 `follow_through / continuation_hold / protective_exit` 우선
- KPI는 아래를 v1 기준선으로 사용
  - `premature_full_exit_rate`
  - `runner_capture_rate`
  - `missed_rebuy_rate`
  - `hold_precision`
  - `partial_then_hold_quality`
  - `full_exit_precision`

### 대상 문서

- [current_path_aware_checkpoint_decision_implementation_spec_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_path_aware_checkpoint_decision_implementation_spec_v1_ko.md)
- [current_path_aware_checkpoint_scope_lock_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_path_aware_checkpoint_scope_lock_v1_ko.md)
- 본 문서

### 산출물

- v1 scope 합의
- KPI 정의 표
- phase 진행 순서 고정
- 기존 runtime / dataset / eval과의 충돌 방지 경계 문서

### 완료 기준

- v1에서 바꾸는 것과 안 바꾸는 것이 문서에 고정됨
- 구현 중 “entry와 management를 합칠지” 같은 범위 흔들림이 사라짐

---

## PA1. Leg Detector Instrumentation

### 목적

- runtime row를 가능한 한 `leg_id`에 소속시키기 시작한다
- 아직 action은 바꾸지 않고 leg assignment만 안정화한다

### 신규 파일

- `backend/services/path_leg_runtime.py`
- `scripts/build_path_leg_snapshot.py`

### 연동 파일

- `backend/services/entry_try_open_entry.py`
- `backend/services/exit_manage_positions.py`

### 구현 내용

- `assign_leg_id(symbol, runtime_row, symbol_state)` 추가
- 최소 필드 저장
  - `leg_id`
  - `leg_direction`
  - `leg_state`
  - `leg_transition_reason`
- active leg snapshot 저장 구조 추가

### 산출물

- `data/analysis/shadow_auto/path_leg_snapshot_latest.json`

### 테스트

- `tests/unit/test_path_leg_runtime.py`
- `tests/unit/test_build_path_leg_snapshot.py`

### 검증 포인트

- 같은 leg 안의 연속 row가 같은 `leg_id`를 공유하는가
- full exit 이후의 새 impulse가 새 `leg_id`를 여는가
- shallow rebuild가 과도하게 새 leg로 끊기지 않는가

### 완료 기준

- 최근 runtime slice에서 주요 row가 `leg_id` 없이 남는 비율이 충분히 낮아진다
- `BTC / NAS / XAU` 모두 leg snapshot artifact가 생성된다

---

## PA2. Checkpoint Segmenter Instrumentation

### 목적

- 같은 leg 내부에서 `판단을 다시 해야 하는 순간`만 checkpoint로 자른다

### 신규 파일

- `backend/services/path_checkpoint_segmenter.py`

### 구현 내용

- `classify_checkpoint_type(leg_ctx, runtime_row)` 구현
- v1 checkpoint type 고정
  - `INITIAL_PUSH`
  - `FIRST_PULLBACK_CHECK`
  - `RECLAIM_CHECK`
  - `LATE_TREND_CHECK`
  - `RUNNER_CHECK`
- hybrid segmentation 적용
  - structure
  - event
  - time

### 산출물

- `data/analysis/shadow_auto/checkpoint_distribution_latest.json`

### 테스트

- `tests/unit/test_path_checkpoint_segmenter.py`

### 검증 포인트

- checkpoint가 매 bar마다 과도하게 찍히지 않는가
- `FIRST_PULLBACK_CHECK`와 `RECLAIM_CHECK`가 실제 차트 구간과 대체로 맞는가
- `RUNNER_CHECK`가 너무 이르게 열리지 않는가

### 완료 기준

- 최근 runtime 기준 checkpoint type 분포가 artifact로 남는다
- `checkpoint_rows`를 보았을 때 사람 해석과 완전히 어긋나지 않는다

---

## PA3. Checkpoint Context Builder / Storage

### 목적

- checkpoint row schema를 고정하고 runtime에 실제 저장한다

### 신규 파일

- `backend/services/path_checkpoint_context.py`

### 연동 파일

- `backend/services/trade_logger.py`
- `backend/services/trade_logger_open_snapshots.py`
- `backend/services/trade_logger_close_ops.py`

### 구현 내용

- `build_checkpoint_context(...)` 구현
- runtime row와 별도 checkpoint row 저장
- 추천 저장 파일
  - `data/runtime/checkpoint_rows.csv`
  - `data/runtime/checkpoint_rows.detail.jsonl`

### 필수 필드

- `checkpoint_id`
- `leg_id`
- `checkpoint_index_in_leg`
- `checkpoint_type`
- `surface_name`
- `bars_since_last_push`
- `bars_since_last_checkpoint`
- `position_side`
- `position_size_fraction`
- `avg_entry_price`
- `realized_pnl_state`
- `unrealized_pnl_state`
- `runner_secured`
- `mfe_since_entry`
- `mae_since_entry`

### 테스트

- `tests/unit/test_path_checkpoint_context.py`

### 검증 포인트

- entry/hold/exit row 모두 checkpoint row를 남길 수 있는가
- `position state`가 누락 없이 저장되는가
- hindsight 전용 필드가 runtime row에 섞이지 않는가

### 완료 기준

- checkpoint row contract가 안정적으로 고정된다
- live runtime 이후 checkpoint row artifact를 재구성할 수 있다

---

## PA4. Passive Score Calculation

### 목적

- 행동은 아직 바꾸지 않고, checkpoint별 management score를 계산해 쌓는다

### 신규 파일

- `backend/services/path_checkpoint_scoring.py`

### 구현 내용

- 아래 runtime score 계산
  - `runtime_continuation_odds`
  - `runtime_reversal_odds`
  - `runtime_hold_quality_score`
  - `runtime_partial_exit_ev`
  - `runtime_full_exit_risk`
  - `runtime_rebuy_readiness`

### 산출물

- checkpoint row detail payload 확장

### 테스트

- `tests/unit/test_path_checkpoint_scoring.py`

### 검증 포인트

- score 값이 전부 0/1로만 몰리지 않는가
- XAU/NAS/BTC에서 symbol별 편향이 지나치지 않은가
- `position state` 변화가 score에 반영되는가

### 완료 기준

- runtime row마다 passive checkpoint score가 남는다
- 아직 actual action은 바꾸지 않는다

---

## PA5. Hindsight Label / Dataset / Eval

### 목적

- hindsight best action label을 분리 생성하고 offline dataset / eval을 붙인다

### 신규 파일

- `scripts/build_checkpoint_dataset.py`
- `scripts/build_checkpoint_eval.py`

### 구현 내용

- hindsight label row 생성
- runtime row와 hindsight row를 `checkpoint_id`로 join
- dataset export
  - `data/datasets/path_checkpoint/checkpoint_dataset.csv`
  - `data/datasets/path_checkpoint/checkpoint_dataset_resolved.csv`

### 산출물

- `data/analysis/shadow_auto/checkpoint_action_eval_latest.json`

### 테스트

- `tests/unit/test_build_checkpoint_dataset.py`
- `tests/unit/test_build_checkpoint_eval.py`

### 검증 포인트

- runtime / hindsight 분리가 유지되는가
- `HOLD / PARTIAL / FULL_EXIT / REBUY / WAIT` 분포가 지나치게 한쪽으로 치우치지 않는가
- `PARTIAL_EXIT vs HOLD`가 정말 애매한 row로 많이 남는지 확인 가능한가

### 완료 기준

- checkpoint dataset과 eval artifact가 생성된다
- v1 KPI를 checkpoint 단위로 계산할 수 있다

---

## PA6. Best Action Resolver

### 목적

- 행동 후보 간 경쟁 구조를 실제 코드로 만든다

### 신규 파일

- `backend/services/path_checkpoint_action_resolver.py`

### 구현 내용

- `resolve_management_action(scores, checkpoint_ctx)` 구현
- v1 행동 후보
  - `HOLD`
  - `PARTIAL_EXIT`
  - `PARTIAL_THEN_HOLD`
  - `FULL_EXIT`
  - `REBUY`
  - `WAIT`
- confidence / reason string 생성

### 테스트

- `tests/unit/test_path_checkpoint_action_resolver.py`

### 검증 포인트

- `FULL_EXIT`가 너무 쉽게 뜨지 않는가
- `PARTIAL_THEN_HOLD`가 runner 상황에서 실제로 분리되는가
- `REBUY`가 새 leg와 혼동되지 않는가

### 완료 기준

- checkpoint row에 `management_action_label / confidence / reason`이 추가된다
- 이 단계까지도 기본 운영 모드는 log-only다

---

## PA7. Harvest / Manual-Exception Queue

### 목적

- checkpoint decision을 학습 재료와 운영 검토 큐로 연결한다

### 신규 파일

- `backend/services/path_checkpoint_harvest.py`
- `scripts/build_checkpoint_harvest.py`

### 구현 내용

- auto-apply / manual-exception / diagnostic-only 분류
- checkpoint harvest artifact 생성

### 산출물

- `data/analysis/shadow_auto/checkpoint_harvest_latest.json`

### 테스트

- `tests/unit/test_path_checkpoint_harvest.py`

### 검증 포인트

- obvious label만 auto-apply로 들어가는가
- `PARTIAL_EXIT vs HOLD` 같은 애매한 row는 manual-exception으로 남는가
- 샘플 부족 family는 diagnostic-only로 내려가는가

### 완료 기준

- checkpoint 구조가 dataset / eval / review queue까지 닫힌다

---

## PA8. Bounded Runtime Adoption

### 목적

- checkpoint action을 실제 runtime에 제한적으로 연결한다

### 연결 순서

1. `follow_through_surface`
2. `continuation_hold_surface`
3. `protective_exit_surface`

### 연동 파일

- `backend/services/entry_service.py`
- `backend/services/entry_try_open_entry.py`
- `backend/services/exit_manage_positions.py`
- 필요 시 `backend/services/exit_service.py`

### 구현 방식

- 1차는 log-only shadow compare
- 2차는 bounded watch / advisory
- 3차는 limited canary action

### 테스트

- `tests/integration/test_path_checkpoint_runtime_adoption.py`

### 검증 포인트

- premature full exit가 감소하는가
- runner capture가 올라가는가
- drawdown이 급격히 악화되지 않는가
- symbol별 왜곡이 없는가

### 완료 기준

- 최소 1개 surface에서 bounded canary가 가능하다
- 관리 action이 실제 운영 결정을 일부 개선하는 증거가 나온다

---

## PA9. CL Hand-off Preparation

### 목적

- checkpoint layer를 CL operating layer가 사용할 수 있는 형태로 넘긴다

### 연결 포인트

- candidate package
- harvest artifact
- preview eval refresh
- manual-exception queue
- canary monitoring

### 결과

- path-aware checkpoint 구조는 CL이 학습하고 운영할 샘플 정의가 된다
- 즉 `CL 이전에 정의하고, CL에서 소비`하는 구조로 자리 잡는다

### 완료 기준

- CL 문서에서 checkpoint dataset / eval / harvest를 직접 참조할 수 있다

---

## 현재 권장 착수 순서

지금 바로 구현을 시작한다면 아래가 맞다.

1. `PA0 Scope Lock / KPI Freeze`
2. `PA1 Leg Detector Instrumentation`
3. `PA2 Checkpoint Segmenter Instrumentation`
4. `PA3 Checkpoint Context Builder / Storage`

이 4개가 끝나기 전에는:

- score 튜닝
- runtime action 적용
- canary 연결

로 먼저 가지 않는 것이 맞다.

이유는 아직 무엇을 한 샘플로 볼지, 무엇을 같은 leg와 같은 checkpoint로 볼지가 고정되지 않았기 때문이다.

---

## 쉬운 말로 다시 설명하면

이 로드맵은 바로 “언제 팔지”를 고치는 작업부터 하자는 게 아니다.

먼저 해야 하는 일은:

- 지금 row가 어떤 큰 흐름에 속하는지
- 그 흐름 안의 몇 번째 체크포인트인지
- 지금은 눌림인지, 추세 붕괴인지

를 시스템이 기록하게 만드는 것이다.

그걸 먼저 해야만 그 다음에:

- 그냥 홀드가 맞았는지
- 조금 팔고 계속 가는 게 맞았는지
- 전량 정리가 맞았는지
- 다시 사는 게 맞았는지

를 학습하고 평가할 수 있다.

즉 순서는:

> 구조를 먼저 기록하고, 점수를 나중에 붙이고, 그 다음에 실제 행동을 조금씩 바꾼다

가 맞다.

---

## 최종 한 줄 요약

> path-aware checkpoint 구현은 `신호 하나 더 추가`가 아니라,
> `같은 흐름 안의 체크포인트를 먼저 구조적으로 기록한 뒤,
> 그 위에 hold / partial / full exit / rebuy를 올리는 단계형 구현`
> 으로 진행하는 것이 가장 안전하다.
