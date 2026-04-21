> Scene-axis extension note:
> 이 문서는 path-aware checkpoint의 기본 구조 명세를 다룬다.
> 이후 그 위에 얹는 `scene axis` 확장은
> [current_checkpoint_scene_axis_design_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_scene_axis_design_v1_ko.md)
> 와
> [current_checkpoint_scene_axis_scope_lock_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_scene_axis_scope_lock_v1_ko.md)
> 를 기준으로 이어진다.
> 특히 `scene / gate / modifier / action / outcome` 경계,
> `scene_maturity`,
> `scene_transition`,
> `scene_family_alignment`,
> `scene_action_bias_strength`
> 는 scene axis v1 구현 기준으로 별도 잠근다.

# Current Path-Aware Checkpoint Decision Implementation Spec v1

## 목적

이 문서는 현재 CFD runtime을 `point decision` 중심 구조에서
`path-aware checkpoint decision` 구조로 확장하기 위한 구현 명세다.

핵심 목표는 아래 한 줄로 요약된다.

> 기존 4개 surface를 유지한 채, leg-aware / checkpoint-aware context layer를 추가해서
> 한 leg 안의 여러 checkpoint에서 `HOLD / PARTIAL_EXIT / PARTIAL_THEN_HOLD / FULL_EXIT / REBUY / WAIT`
> 를 다시 판단할 수 있게 만든다.

이 문서는 아이디어 설명이 아니라, 실제 구현 순서와 데이터 구조를 고정하기 위한 v1 명세다.

구현 순서와 phase별 완료 기준은
[current_path_aware_checkpoint_decision_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_path_aware_checkpoint_decision_implementation_roadmap_ko.md)
를 함께 본다.

PA0 범위 고정과 KPI 정의는
[current_path_aware_checkpoint_scope_lock_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_path_aware_checkpoint_scope_lock_v1_ko.md)
를 기준 문서로 본다.

---

## 1. 왜 지금 이 구조가 필요한가

현재 시스템은 아래를 이미 갖고 있다.

- `market-family` 분리
  - `NAS100`
  - `BTCUSD`
  - `XAUUSD`
- `surface` 분리
  - `initial_entry_surface`
  - `follow_through_surface`
  - `continuation_hold_surface`
  - `protective_exit_surface`
- `wrong-side active-action conflict` 감지 및 일부 차단
- failure harvest
- preview dataset / evaluation
- signoff packet / activation contract

하지만 현재 runtime row 다수는 여전히 `독립된 점`처럼 읽힌다.

즉 현재 구조는:

- `지금 살까`
- `지금 기다릴까`
- `지금 팔까`

에는 강하지만,

- 같은 leg의 몇 번째 checkpoint인가
- 지금 눌림이 건강한 pullback인가, thesis 붕괴인가
- 일부 줄이고 runner를 유지할지, 전량 청산할지, 다시 늘릴지

를 구조적으로 충분히 표현하지 못한다.

따라서 현재 gap은 signal 부족보다 `path memory / checkpoint context 부족`에 가깝다.

---

## 2. 범위와 비범위

### 이 문서의 범위

- leg detection
- checkpoint segmentation
- checkpoint context schema
- management action scoring
- best action resolver
- checkpoint harvest / eval / dataset export
- 기존 4 surface와의 연결 방식

### 이 문서의 비범위

- `P0 wrong-side active-action conflict` 자체 대체
- `MF17 initial_entry_surface` signoff / activation 절차 대체
- `CL orchestrator` 전체 구현
- 기존 broker finality / hard risk guard finality 변경

즉 이 구조는 기존 시스템을 버리는 것이 아니라, 기존 4 surface 위에 공통 context layer를 추가하는 작업이다.

---

## 3. 핵심 설계 원칙

### 3-1. 새 surface를 만들지 않는다

`checkpoint_surface` 같은 5번째 surface를 만들지 않는다.

이유:

- surface는 `무슨 종류의 판단 문제인가`를 나타낸다
- checkpoint는 `경로상 지금 어디에 있는가`를 나타낸다
- 둘을 섞으면 목적함수와 평가 축이 흐려진다

따라서 역할은 아래처럼 분리한다.

- `surface = decision purpose`
- `checkpoint = path context`

### 3-2. row는 가능하면 leg에 소속되어야 한다

앞으로 runtime row는 아래 두 상태 중 하나여야 한다.

1. 특정 `leg_id`에 할당된 checkpoint row
2. 아직 leg에 안정적으로 소속되지 못한 raw runtime row

### 3-3. entry action과 management action을 분리한다

이 부분이 v1에서 가장 중요하다.

`initial_entry_surface`는 본질적으로 `ENTER vs WAIT` 문제다.
반면 checkpoint layer의 핵심은 `HOLD / PARTIAL / FULL_EXIT / REBUY / WAIT` 문제다.

따라서 label은 아래 두 축으로 분리한다.

- `entry_action_label`
  - `ENTER_LONG`
  - `ENTER_SHORT`
  - `WAIT`
- `management_action_label`
  - `HOLD`
  - `PARTIAL_EXIT`
  - `PARTIAL_THEN_HOLD`
  - `FULL_EXIT`
  - `REBUY`
  - `WAIT`

정리하면:

- `initial_entry_surface`는 기존 entry taxonomy를 유지한다
- checkpoint layer는 주로 `follow_through / continuation_hold / protective_exit`에서 management taxonomy를 계산한다
- `initial_entry_surface`도 checkpoint context를 읽을 수는 있지만, v1에서는 management taxonomy의 주 판단 대상이 아니다

### 3-4. runtime decision과 hindsight label을 분리한다

이 구조는 leakage에 취약할 수 있으므로,
온라인 판단과 사후 평가용 라벨을 반드시 분리한다.

- `runtime_*`
  - 그 시점에 미래 정보 없이 계산 가능한 값
- `hindsight_*`
  - 이후 leg 결과를 보고 사후 라벨링한 값

예:

- `runtime_continuation_odds`
- `runtime_reversal_odds`
- `hindsight_best_management_action_label`

이 구분이 없으면 외부 리뷰나 이후 평가에서 신뢰도가 크게 떨어진다.

---

## 4. 전체 아키텍처

```text
[Raw Runtime Rows]
    ↓
[Leg Detector]
    ↓
[Checkpoint Segmenter]
    ↓
[Checkpoint Context Builder]
    ↓
[Surface-Specific Decision Scorer]
    ↓
[Best Action Resolver]
    ↓
[Checkpoint Action Output]
    ↓
[Harvest / Eval / Dataset Export]
```

기존 surface와의 연결은 아래처럼 본다.

```text
initial_entry_surface
follow_through_surface
continuation_hold_surface
protective_exit_surface
        ↑
        │
checkpoint context layer
        ↑
        │
leg detection / checkpoint segmentation
```

---

## 5. 모듈 구조 제안

### 신규 서비스 파일

- `backend/services/path_leg_runtime.py`
- `backend/services/path_checkpoint_segmenter.py`
- `backend/services/path_checkpoint_context.py`
- `backend/services/path_checkpoint_scoring.py`
- `backend/services/path_checkpoint_action_resolver.py`
- `backend/services/path_checkpoint_harvest.py`

### 신규 배치/리포트 스크립트

- `scripts/build_path_leg_snapshot.py`
- `scripts/build_checkpoint_dataset.py`
- `scripts/build_checkpoint_eval.py`
- `scripts/build_checkpoint_harvest.py`

### 신규 산출물

- `data/analysis/shadow_auto/path_leg_snapshot_latest.json`
- `data/analysis/shadow_auto/checkpoint_distribution_latest.json`
- `data/analysis/shadow_auto/checkpoint_action_eval_latest.json`
- `data/analysis/shadow_auto/checkpoint_harvest_latest.json`

### 신규 dataset 산출 예

- `data/datasets/path_checkpoint/checkpoint_dataset.csv`
- `data/datasets/path_checkpoint/checkpoint_dataset_resolved.csv`

### 추천 저장 파일

- `data/runtime/checkpoint_rows.csv`
- `data/runtime/checkpoint_rows.detail.jsonl`

---

## 6. 용어 정의

### leg

한 방향 흐름이 의미 있게 유지되는 구간.
반드시 한 번의 진입과 1:1일 필요는 없지만,
runtime 상에서 연속된 구조와 포지션 관리 의사결정이 공유되는 구간이다.

### checkpoint

같은 leg 내부에서 action을 다시 판단해야 하는 순간.

예:

- 첫 push 이후
- 첫 pullback
- reclaim 확인
- 늦은 추세 구간
- runner 유지 여부 재평가

### path context

현재 row가 leg 내부의 어디에 있는지 설명하는 정보.

예:

- 몇 번째 checkpoint인지
- 마지막 pivot 이후 얼마나 왔는지
- 마지막 push 이후 몇 bar가 지났는지
- 현재 포지션 상태가 어떤지

---

## 7. leg 데이터 모델

```json
{
  "leg_id": "XAUUSD_20260409_001",
  "symbol": "XAUUSD",
  "leg_direction": "UP",
  "leg_start_ts": "2026-04-09T20:10:00",
  "leg_end_ts": null,
  "leg_state": "ACTIVE",
  "leg_start_reason": "breakout_reclaim_start",
  "start_pivot_price": 2312.4,
  "current_extreme_price": 2326.8,
  "checkpoint_count": 4,
  "bars_since_leg_start": 18,
  "last_checkpoint_id": "XAUUSD_20260409_001_cp4"
}
```

### 필수 필드

- `leg_id`
- `symbol`
- `leg_direction`
- `leg_start_ts`
- `leg_end_ts`
- `leg_state`
- `leg_start_reason`
- `start_pivot_price`
- `current_extreme_price`
- `checkpoint_count`
- `bars_since_leg_start`
- `last_checkpoint_id`

### 권장 추가 필드

- `entry_anchor_ts`
- `entry_anchor_price`
- `active_position_side`
- `active_position_size_fraction`
- `leg_mfe`
- `leg_mae`

---

## 8. checkpoint row 데이터 모델

### 8-1. runtime checkpoint row

```json
{
  "checkpoint_id": "XAUUSD_20260409_001_cp3",
  "leg_id": "XAUUSD_20260409_001",
  "symbol": "XAUUSD",
  "surface_name": "continuation_hold_surface",
  "leg_direction": "UP",
  "checkpoint_index_in_leg": 3,
  "checkpoint_type": "RECLAIM_CHECK",
  "runtime_ts": "2026-04-09T20:36:48",
  "last_pivot_price": 2320.1,
  "last_pivot_distance": 4.3,
  "bars_since_last_push": 5,
  "bars_since_last_checkpoint": 3,
  "runtime_continuation_odds": 0.71,
  "runtime_reversal_odds": 0.24,
  "runtime_hold_quality_score": 0.68,
  "runtime_partial_exit_ev": 0.44,
  "runtime_full_exit_risk": 0.21,
  "runtime_rebuy_readiness": 0.58,
  "current_pnl_state": "OPEN_PROFIT",
  "position_side": "LONG",
  "position_size_fraction": 1.0,
  "avg_entry_price": 2318.2,
  "realized_pnl_state": "NONE",
  "unrealized_pnl_state": "OPEN_PROFIT",
  "runner_secured": false,
  "mfe_since_entry": 1.8,
  "mae_since_entry": 0.3,
  "continuation_persistence": 0.74,
  "reversal_failure_count": 1,
  "reclaim_attempt_count": 2,
  "trend_strength_score": 0.77,
  "management_action_label": "HOLD",
  "management_action_confidence": 0.66,
  "management_action_reason": "up_leg_reclaim_success_with_low_full_exit_risk"
}
```

### 8-2. hindsight checkpoint row

```json
{
  "checkpoint_id": "XAUUSD_20260409_001_cp3",
  "hindsight_best_management_action_label": "PARTIAL_THEN_HOLD",
  "hindsight_resolution_reason": "runner_extension_followed_by_shallow_pullback",
  "hindsight_leg_outcome": "extended_up_leg",
  "hindsight_mfe_after_checkpoint": 2.4,
  "hindsight_mae_after_checkpoint": 0.6
}
```

### 필수 분리 원칙

- runtime row와 hindsight row는 같은 `checkpoint_id`로 join 가능해야 한다
- 그러나 저장 시점과 계산 경로는 분리한다
- runtime scoring 코드에서 hindsight 필드를 읽으면 안 된다

---

## 9. action taxonomy

### 9-1. entry action taxonomy

`initial_entry_surface` 중심.

- `ENTER_LONG`
- `ENTER_SHORT`
- `WAIT`

### 9-2. management action taxonomy

`follow_through / continuation_hold / protective_exit` 중심.

- `HOLD`
- `PARTIAL_EXIT`
- `PARTIAL_THEN_HOLD`
- `FULL_EXIT`
- `REBUY`
- `WAIT`

### 9-3. 의미 구분

- `HOLD`
  - 현재 포지션 유지
- `PARTIAL_EXIT`
  - 현재 포지션 일부 축소
- `PARTIAL_THEN_HOLD`
  - 일부 익절 후 runner 유지
- `FULL_EXIT`
  - 현재 thesis 기준 포지션 종료
- `REBUY`
  - 이전 축소 또는 종료 이후 다시 늘리거나 재진입
- `WAIT`
  - 새 행동 없이 관찰

### 9-4. v1에서의 적용 범위

- `management_action_label`은 v1에서 `follow_through / continuation_hold / protective_exit`에 우선 적용한다
- `initial_entry_surface`는 checkpoint context를 읽되, 기존 `entry_action_label` 구조를 유지한다

---

## 10. leg state machine

```text
LEG_START
  ↓
INITIAL_PUSH
  ↓
FIRST_PULLBACK_CHECK
  ↓
RECLAIM_CHECK
  ↓
LATE_TREND_CHECK
  ↓
LEG_TERMINATION
```

### 선택적 확장 상태

- `FAILED_LEG`
- `LATE_EXHAUSTION_CHECK`

v1에서는 상태를 너무 세분화하지 않고 위 기본 상태를 우선 적용한다.

---

## 11. checkpoint_type taxonomy

### v1 필수 타입

- `INITIAL_PUSH`
- `FIRST_PULLBACK_CHECK`
- `RECLAIM_CHECK`
- `LATE_TREND_CHECK`
- `RUNNER_CHECK`

### v2 이후 확장 후보

- `FAILED_RECLAIM_CHECK`
- `LATE_EXHAUSTION_CHECK`
- `POST_PARTIAL_REBUILD_CHECK`

---

## 12. leg 시작과 종료 규칙

### 12-1. leg 시작 조건

아래 중 하나가 만족되면 새 leg를 연다.

- breakout/reclaim 구조가 의미 있게 시작됨
- `initial_entry_surface`가 진입 후보를 확정함
- 기존 leg가 종료된 뒤 같은 방향의 새 impulse가 발생함

### 12-2. leg 유지 조건

아래가 유지되면 같은 leg로 본다.

- 구조적으로 같은 방향 흐름이 유지됨
- full thesis break가 아직 아님
- full exit가 발생하지 않았거나, 발생해도 재진입이 짧은 cooldown 내에 같은 흐름 문맥으로 이어짐

### 12-3. leg 종료 조건

아래 중 하나면 leg를 종료한다.

- `FULL_EXIT`가 발생하고 cooldown 내 재진입이 없음
- 반대 방향 구조가 명확히 확정됨
- reclaim 실패 후 path 붕괴가 확인됨
- leg time/age가 임계치를 넘고 extension continuity가 끊김

### 12-4. rebuy와 새 leg 구분 규칙

이 규칙은 구현 중 혼동이 많을 수 있으므로 명시한다.

- 같은 leg 안의 shallow pullback 후 재확대는 `REBUY`
- full thesis break 이후 재출발은 `새 leg`
- partial exit 후 다시 size를 늘리는 것은 기본적으로 `REBUY`

---

## 13. checkpoint segmentation 규칙

checkpoint segmentation은 `pivot-only`가 아니라 `structure + event + time` hybrid로 간다.

### 13-1. evidence 3층

#### structure

- `HH / HL / LH / LL`
- reclaim success / failure
- breakout / breakdown
- reject fail / break fail

#### event

- first push
- pullback 시작
- reclaim 발생
- late extension
- runner risk 증가

#### time

- `bars_since_last_push`
- `bars_since_last_pivot`
- `bars_since_last_checkpoint`

### 13-2. 기본 분류 예시

```python
def classify_checkpoint_type(ctx):
    if ctx.leg_age_bars <= 2 and ctx.first_push_detected:
        return "INITIAL_PUSH"

    if ctx.pullback_detected and not ctx.reclaim_confirmed:
        return "FIRST_PULLBACK_CHECK"

    if ctx.reclaim_confirmed:
        return "RECLAIM_CHECK"

    if ctx.runner_active and ctx.leg_age_bars > ctx.late_trend_threshold:
        return "RUNNER_CHECK"

    return "LATE_TREND_CHECK"
```

### 13-3. v1 운영 원칙

- online에서 너무 많은 checkpoint를 만들지 않는다
- 의미 있는 구조 변화가 있을 때만 새 checkpoint를 만든다
- 단순 매 bar row 증식이 아니라 `판단이 다시 필요한 순간`을 자르는 것이 목적이다

---

## 14. evidence layer 설계

checkpoint action은 최소 4층 evidence를 사용한다.

### structure evidence

- higher high / lower low
- higher low / lower high
- reclaim success / failure
- break fail / reject fail

### time evidence

- bars since last push
- bars since last checkpoint
- continuation persistence duration

### position evidence

- 포지션 보유 여부
- position side
- position size fraction
- avg entry price
- realized / unrealized pnl state
- runner already secured 여부
- `mfe / mae`

### path pressure evidence

- continuation pressure
- reversal pressure
- exhaustion pressure
- reclaim durability pressure

---

## 15. 점수 계산 구조

각 checkpoint row에서 최소 아래 runtime score를 계산한다.

- `runtime_continuation_odds`
- `runtime_reversal_odds`
- `runtime_hold_quality_score`
- `runtime_partial_exit_ev`
- `runtime_full_exit_risk`
- `runtime_rebuy_readiness`

### score 의미

#### continuation_odds

현재 leg가 같은 방향으로 더 이어질 가능성.

#### reversal_odds

현재 leg가 의미 있게 반전될 가능성.

#### hold_quality_score

현재 포지션 크기를 유지할 품질.

#### partial_exit_ev

일부 잠그고 runner를 유지하는 것이 유리한 정도.

#### full_exit_risk

지금 유지할 경우 thesis 붕괴 또는 급한 되돌림 위험이 큰 정도.

#### rebuy_readiness

pullback / reclaim 이후 다시 늘리거나 재진입할 가치.

---

## 16. best action resolver

핵심은 `규칙 한두 개`로 찍는 것이 아니라,
행동 후보 간 상대 우위를 비교하는 구조다.

### 후보 행동

- `HOLD`
- `PARTIAL_EXIT`
- `PARTIAL_THEN_HOLD`
- `FULL_EXIT`
- `REBUY`
- `WAIT`

### 예시 resolver

```python
def resolve_management_action(scores, ctx):
    if scores["runtime_full_exit_risk"] >= 0.78 and scores["runtime_reversal_odds"] >= 0.72:
        return "FULL_EXIT"

    if scores["runtime_partial_exit_ev"] >= 0.63 and scores["runtime_hold_quality_score"] >= 0.55:
        return "PARTIAL_THEN_HOLD"

    if scores["runtime_hold_quality_score"] >= 0.67 and scores["runtime_continuation_odds"] > scores["runtime_reversal_odds"]:
        return "HOLD"

    if scores["runtime_rebuy_readiness"] >= 0.70 and ctx.checkpoint_type in {"FIRST_PULLBACK_CHECK", "RECLAIM_CHECK"}:
        return "REBUY"

    if scores["runtime_continuation_odds"] < 0.45 and scores["runtime_reversal_odds"] < 0.45:
        return "WAIT"

    return "PARTIAL_EXIT"
```

### resolver 원칙

- `FULL_EXIT`는 thesis break 쪽 강한 신호에서만 허용한다
- `PARTIAL_THEN_HOLD`는 runner 관리가 핵심일 때 우선 사용한다
- `REBUY`는 same-leg rebuild 상황에만 허용한다
- `WAIT`는 확신이 약한 환경에서만 사용한다

---

## 17. surface와 checkpoint 연결 규칙

### initial_entry_surface

역할:

- leg 시작 직전/직후 entry decision

checkpoint 연계:

- `INITIAL_PUSH` context는 읽을 수 있음
- 하지만 v1 주 action은 여전히 `entry_action_label`

핵심 질문:

- 처음 들어갈 가치가 있는가

### follow_through_surface

역할:

- 진입 직후 첫 pullback / 첫 reclaim 품질 평가

checkpoint 연계:

- `FIRST_PULLBACK_CHECK`
- 초기 `RECLAIM_CHECK`

가능 action:

- `HOLD`
- `REBUY`
- `WAIT`
- 제한적 `FULL_EXIT`

### continuation_hold_surface

역할:

- 중반 이후 leg 유지와 runner 관리

checkpoint 연계:

- 중반 이후 `RECLAIM_CHECK`
- `LATE_TREND_CHECK`
- `RUNNER_CHECK`

가능 action:

- `HOLD`
- `PARTIAL_EXIT`
- `PARTIAL_THEN_HOLD`

### protective_exit_surface

역할:

- thesis break와 급한 손상 방지

checkpoint 연계:

- reversal odds 급증
- failed reclaim
- path 붕괴

가능 action:

- `FULL_EXIT`
- `PARTIAL_EXIT`
- 제한적 `WAIT`

---

## 18. auto-apply / manual-exception / diagnostic-only

### auto-apply

명백한 것만 자동 적용한다.

예:

- `premature_full_exit`
- `obvious_missed_rebuy`
- `runner_cut_too_early`
- `full_exit_after_reclaim_success`
- `thesis_break_exit_correct`

### manual-exception

애매하거나 사람 판단 개입이 필요한 것.

예:

- `PARTIAL_EXIT vs HOLD`
- `PARTIAL_THEN_HOLD vs HOLD`
- late trend 구간의 rebuy 적절성
- shallow pullback에서의 runner 보존 강도

### diagnostic-only

샘플이 적거나 구조가 아직 불안정한 것.

예:

- 새로운 checkpoint family
- 특정 symbol에서만 드문 late trend variation
- segmentation rule이 아직 고정되지 않은 case

---

## 19. 평가 지표

이 구조는 예쁜 설계가 아니라 성과 개선으로 평가되어야 한다.

### 필수 KPI

- `premature_full_exit_rate`
- `runner_capture_rate`
- `missed_rebuy_rate`
- `hold_precision`
- `partial_then_hold_quality`
- `full_exit_precision`
- `reentry_after_reclaim_success_rate`
- `checkpoint_action_coverage`

### 안정성 KPI

- max drawdown 악화 여부
- false full exit 증가 여부
- 과도한 checkpoint 생성 여부
- symbol별 action skew

### v1 성공 기준

- premature full exit가 baseline보다 유의미하게 감소
- runner capture가 baseline보다 증가
- missed rebuy가 감소
- drawdown이 의미 있게 악화되지 않음

---

## 20. 런타임 연결 방식

### entry 경로

`backend/services/entry_try_open_entry.py` 근처에서:

- raw row 생성
- leg assignment
- checkpoint assignment
- initial / early follow-through scoring

### hold / exit 경로

`backend/services/exit_manage_positions.py` 근처에서:

- active position 기준 checkpoint row 생성
- hold / partial / full / rebuy candidate 계산

### storage

runtime flat row와 별도로 checkpoint row를 저장한다.

추천 파일:

- `checkpoint_rows.csv`
- `checkpoint_rows.detail.jsonl`

---

## 21. public function 제안

### `path_leg_runtime.py`

```python
def assign_leg_id(symbol: str, runtime_row: dict, symbol_state: dict) -> dict:
    ...
```

출력:

- `leg_id`
- `leg_direction`
- `leg_state`
- `leg_transition_reason`

### `path_checkpoint_segmenter.py`

```python
def classify_checkpoint_type(leg_ctx: dict, runtime_row: dict) -> str:
    ...
```

### `path_checkpoint_context.py`

```python
def build_checkpoint_context(
    runtime_row: dict,
    leg_ctx: dict,
    position_ctx: dict,
    checkpoint_history: list[dict],
) -> dict:
    ...
```

### `path_checkpoint_scoring.py`

```python
def compute_management_scores(checkpoint_ctx: dict) -> dict:
    ...
```

출력:

- continuation odds
- reversal odds
- hold quality
- partial exit EV
- full exit risk
- rebuy readiness

### `path_checkpoint_action_resolver.py`

```python
def resolve_management_action(scores: dict, checkpoint_ctx: dict) -> dict:
    ...
```

출력:

- `management_action_label`
- `management_action_confidence`
- `management_action_reason`

### `path_checkpoint_harvest.py`

```python
def harvest_checkpoint_labels(runtime_rows: list[dict], hindsight_rows: list[dict]) -> dict:
    ...
```

---

## 22. 구현 단계

### Phase 1. Instrumentation

목표:

- leg detector
- checkpoint segmenter
- checkpoint schema 고정
- checkpoint row 저장

완료 기준:

- runtime에서 `checkpoint_rows.csv`가 생성됨
- `leg_id / checkpoint_id / checkpoint_type`가 안정적으로 남음

### Phase 2. Passive Scoring

목표:

- `runtime_continuation_odds`
- `runtime_reversal_odds`
- `runtime_hold_quality_score`
- `runtime_partial_exit_ev`
- `runtime_full_exit_risk`
- `runtime_rebuy_readiness`

계산 및 저장

완료 기준:

- live runtime에는 아직 행동을 강제하지 않더라도 checkpoint score가 누적됨

### Phase 3. Resolver + Offline Eval

목표:

- best action resolver
- hindsight label join
- checkpoint eval / harvest / dataset export

완료 기준:

- `checkpoint_action_eval_latest.json`
- `checkpoint_harvest_latest.json`
- `checkpoint_dataset.csv`

생성

### Phase 4. Bounded Runtime Adoption

목표:

- `follow_through_surface`
- `continuation_hold_surface`
- `protective_exit_surface`

에 checkpoint management action을 bounded하게 연결

완료 기준:

- log-only -> bounded canary -> stable 순으로 승격 가능

---

## 23. 현재 로드맵 안에서의 위치

권장 순서는 아래다.

1. `P0 wrong-side conflict` 응급 수정 계속
2. `MF17 initial_entry_surface` signoff / bounded activation 유지
3. path-aware checkpoint layer 설계 및 instrumentation 시작
4. `follow_through / continuation_hold / protective_exit`에 checkpoint scoring 연결
5. 이후 `CL orchestrator`와 연결

즉 이 구조는 `CL 이후의 옵션`이 아니라,
CL이 학습하고 운영할 샘플 정의를 먼저 올바르게 만드는 선행 계층이다.

---

## 24. 구현 시 주의사항

### 24-1. checkpoint row 폭증 금지

매 bar마다 checkpoint를 만들지 않는다.
구조 변화가 있을 때만 만든다.

### 24-2. entry와 management를 억지로 합치지 않는다

`ENTER_LONG`과 `HOLD`를 같은 resolver로 바로 통합하지 않는다.
v1은 분리한다.

### 24-3. hindsight leakage 금지

runtime scoring 함수는 hindsight 필드를 읽지 않는다.

### 24-4. REBUY 남용 금지

같은 leg의 shallow rebuild에만 우선 허용한다.
새 leg인지 같은 leg인지 먼저 결정한다.

### 24-5. PARTIAL action은 초반에 보수적으로

`PARTIAL_EXIT`와 `PARTIAL_THEN_HOLD`는 설명력이 높지만 모호성도 높다.
v1 초반에는 manual-exception 비중이 높아도 괜찮다.

---

## 25. 쉬운 말로 다시 설명하면

이 구조는 새로운 진입 신호를 하나 더 만드는 작업이 아니다.

쉽게 말하면:

- 예전 방식은 `지금 사? 지금 팔아?`만 자꾸 묻는 구조였다
- 앞으로는 `지금 이 큰 흐름의 몇 번째 체크포인트야?`
- `이 눌림은 건강한 쉬어감이야, 아니면 진짜 꺾인 거야?`
- `그래서 지금은 계속 들고 가야 해? 조금 줄여야 해? 다 팔아야 해? 다시 사야 해?`

를 묻는 구조로 바꾸는 것이다

즉 이 문서의 핵심은:

> 차트를 점으로 읽지 말고, 한 방향 흐름 안의 체크포인트들로 읽자

이다.

---

## 26. 최종 한 줄 결론

> 이 구조는 `새로운 BUY/SELL 신호`를 추가하는 작업이 아니라,
> 기존 포지션과 leg를 경로 단위로 계속 다시 읽어
> 각 checkpoint에서 가장 맞는 행동을 고르는 `path-aware position management engine`을 만드는 작업이다.
