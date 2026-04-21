# Current SA3 Scene Dataset Export Detailed Plan

## 목적

`SA3`의 목적은 `SA2`에서 붙인 runtime scene seed를
실제 학습 가능한 dataset과 eval artifact로 내리는 것이다.

이번 단계에서 하는 일은 두 가지다.

1. resolved checkpoint dataset에 `hindsight scene`을 실제로 채운다.
2. scene만 따로 보는 dataset / eval 산출물을 연다.

즉 이번 단계는

```text
runtime_scene -> hindsight_scene -> scene_dataset -> scene_eval
```

흐름을 닫는 단계다.

---

## 왜 지금 필요한가

지금까지는 scene이 runtime row에 붙고, sanity check까지는 가능해졌다.
하지만 아직 아래가 부족했다.

- 어떤 runtime scene이 hindsight로도 맞았는지
- 어떤 scene이 unresolved로 많이 남는지
- symbol별로 어떤 scene이 sparse한지

이게 없으면 `SA4 Scene Candidate Pipeline`으로 넘길 학습 입력이 약하다.

---

## 이번 단계의 구현 원칙

## 1. scene은 action과 분리한다

scene은 action과 다른 축이다.

- `trend_exhaustion`은 장면
- `PARTIAL_THEN_HOLD`는 행동

이번 단계에서도 action을 scene으로 바꾸지 않고,
action hindsight와 runtime scene을 같이 참고해서
`hindsight_scene_fine_label`을 보수적으로 확정한다.

## 2. runtime scene을 뒤집기보다 “확정” 위주로 간다

이번 v1 bootstrap은 runtime scene을 완전히 새로 다시 추론하는 게 아니다.

대신 아래처럼 간다.

- runtime scene이 이미 붙어 있고
- hindsight action과 row 구조가 그 장면을 지지하면
- hindsight scene으로 확정한다

즉 “runtime scene이 나중에 봐도 맞았는가”를 보는 방식이다.

## 3. gate는 이번 단계에서 따로 분리해 본다

`low_edge_state` 같은 gate는 scene fine label과 다르다.
그래서 이번 단계에서는

- runtime gate는 그대로 export
- hindsight scene은 fine label 위주로 확정

으로 간다.

---

## 대상 파일

핵심 구현:

- [path_checkpoint_dataset.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_dataset.py)

신규 스크립트:

- [build_checkpoint_scene_dataset.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/build_checkpoint_scene_dataset.py)
- [build_checkpoint_scene_eval.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/build_checkpoint_scene_eval.py)

테스트:

- [test_path_checkpoint_dataset.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_path_checkpoint_dataset.py)
- [test_build_checkpoint_scene_dataset.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_build_checkpoint_scene_dataset.py)
- [test_build_checkpoint_scene_eval.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_build_checkpoint_scene_eval.py)

---

## 이번 단계에서 추가하는 산출물

### 1. scene dataset csv

- `data/datasets/path_checkpoint/checkpoint_scene_dataset.csv`

용도:

- scene 학습 입력
- scene 분포 확인
- symbol / surface / checkpoint_type별 scene sparse 여부 확인

### 2. scene eval json

- `data/analysis/shadow_auto/checkpoint_scene_eval_latest.json`

용도:

- runtime scene coverage
- hindsight scene coverage
- runtime vs hindsight scene match rate
- symbol별 scene 품질 확인

---

## hindsight scene bootstrap 규칙

이번 v1은 starter scene 4개를 우선 다룬다.

### 1. breakout_retest_hold

확정 조건:

- `checkpoint_type in {INITIAL_PUSH, FIRST_PULLBACK_CHECK, RECLAIM_CHECK}`
- `continuation` 우세
- `reversal`이 continuation보다 충분히 약함
- hindsight action이 `REBUY / HOLD / PARTIAL_THEN_HOLD`

### 2. liquidity_sweep_reclaim

확정 조건:

- entry 계열 checkpoint
- hindsight action이 `REBUY / HOLD / PARTIAL_THEN_HOLD`
- `continuation` 우세
- reason blob에 `sweep / reclaim / wrong_side` 계열 힌트 존재

### 3. trend_exhaustion

확정 조건:

- late checkpoint
- hindsight action이 `PARTIAL_THEN_HOLD / PARTIAL_EXIT / FULL_EXIT`
- `partial_exit`가 충분히 높음
- `giveback_ratio` 또는 `reversal`이 exhaustion 쪽을 지지

### 4. time_decay_risk

확정 조건:

- late checkpoint
- hindsight action이 `WAIT / PARTIAL_EXIT / FULL_EXIT`
- 현재 수익이 매우 작음
- MFE/MAE도 작음
- `hold_quality`가 낮음

### 5. 그 외

- `hindsight_scene_fine_label = unresolved`
- `hindsight_scene_quality_tier = unresolved`

즉 이번 단계는 무리하게 모든 scene을 확정하지 않는다.

---

## 추가 컬럼

resolved dataset에 아래 컬럼을 추가한다.

- `hindsight_scene_label_source`
- `hindsight_scene_confidence`
- `hindsight_scene_reason`
- `hindsight_scene_resolution_state`
- `runtime_hindsight_scene_match`

의미:

- scene이 어떤 bootstrap 규칙으로 확정됐는지
- 얼마나 자신 있는지
- runtime scene과 hindsight scene이 같은지

---

## eval에서 보는 것

scene eval은 최소 아래를 본다.

- `runtime_scene_filled_row_count`
- `hindsight_scene_resolved_row_count`
- `runtime_scene_counts`
- `hindsight_scene_counts`
- `gate_label_counts`
- `scene_quality_tier_counts`
- `runtime_hindsight_scene_match_rate`

symbol별로도 같은 값을 요약한다.

---

## 완료 기준

- resolved dataset에 `hindsight_scene_*` 값이 실제로 채워진다
- `checkpoint_scene_dataset.csv`가 생성된다
- `checkpoint_scene_eval_latest.json`이 생성된다
- symbol별 scene coverage / sparse 상태를 볼 수 있다
- 다음 단계 `SA4 Scene Candidate Pipeline`으로 넘길 최소 입력이 생긴다

---

## 한 줄 결론

`SA3`는 scene을 “붙여보기”에서 끝내지 않고,
scene이 실제 dataset과 eval에 들어가서
다음 학습 단계로 넘어갈 수 있게 만드는 연결 단계다.
