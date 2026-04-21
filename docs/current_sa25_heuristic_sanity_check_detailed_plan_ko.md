# Current SA2.5 Heuristic Sanity Check Detailed Plan

## 목적

`SA2.5`는 `SA2 heuristic scene tagger`가 실제 checkpoint row 위에서
얼마나 일관되게 찍히는지 먼저 점검하는 단계다.

이 단계의 핵심은 단순하다.

- 아직 `scene`을 실전 action에 쓰지 않는다
- 먼저 `scene 분포`, `surface-scene alignment`, `scene transition`이 정상인지 본다
- 이상하면 `SA3 dataset export`로 넘기기 전에 heuristic 기준을 다시 다듬는다

즉 `SA2.5`는

```text
scene를 잘 붙였는지 검산하는 단계
```

이다.

---

## 왜 지금 꼭 필요한가

`SA2`에서 scene seed를 붙이기 시작하면 바로 다음 유혹은 dataset export와 candidate pipeline으로 넘어가는 것이다.
그런데 여기서 분포가 깨진 상태로 넘어가면 seed가 오염된다.

대표적으로 아래 3가지가 위험하다.

1. 특정 scene이 너무 많이 찍힘
   - 예: `trend_exhaustion`이 최근 row의 80% 이상
2. surface와 scene이 너무 자주 엇갈림
   - 예: `continuation_hold_surface`인데 scene이 계속 `ENTRY_INITIATION`
3. 장면 전이쌍이 비정상적임
   - 예: `failed_transition -> breakout_retest_hold`가 과도하게 반복

그래서 `SA2.5`는 “scene를 붙였는가”보다
“붙인 scene가 sanity를 유지하는가”를 보는 단계다.

---

## 이번 단계에서 하는 것

- 기존 `checkpoint_rows.csv`를 다시 replay해서 scene를 재생성한다
- replay된 결과로 아래 3가지를 요약한다
  - `scene 분포`
  - `surface-scene alignment`
  - `transition sanity`
- 심볼별 요약과 전체 요약을 artifact로 남긴다

중요한 점:

지금 live row에 scene가 아직 많이 안 찍혀 있어도 괜찮다.
`SA2.5`는 기존 checkpoint row를 현재 heuristic 규칙으로 다시 태우는 방식으로 본다.

---

## 신규 파일

- `backend/services/path_checkpoint_scene_sanity.py`
- `scripts/build_checkpoint_scene_sanity_check.py`
- `tests/unit/test_path_checkpoint_scene_sanity.py`
- `tests/unit/test_build_checkpoint_scene_sanity_check.py`

---

## 입력

기본 입력은 아래 1개면 충분하다.

- [checkpoint_rows.csv](/C:/Users/bhs33/Desktop/project/cfd/data/runtime/checkpoint_rows.csv)

이 파일을 시간순으로 replay하면서
각 row에 `tag_runtime_scene()`를 다시 적용한다.

---

## 출력 artifact

기본 artifact:

- `data/analysis/shadow_auto/checkpoint_scene_sanity_latest.json`

구조:

- `summary`
  - 전체 row 수
  - scene coverage
  - fine/gate/coarse 분포
  - alignment 분포
  - transition pair 분포
  - unexpected transition 수
  - recommended_next_action
- `rows`
  - 심볼별 sanity summary

---

## 점검 항목

## 1. scene coverage

봐야 하는 값:

- `scene_filled_row_count`
- `fine_resolved_row_count`
- `gate_tagged_row_count`
- `unresolved_row_count`

해석:

- `unresolved`가 너무 높으면 heuristic가 너무 보수적
- 특정 scene만 과도하게 많으면 heuristic가 너무 느슨하거나 단조로움

## 2. scene distribution

봐야 하는 값:

- `fine_label_counts`
- `gate_label_counts`
- `coarse_family_counts`
- `confidence_band_counts`
- `maturity_counts`

경고 기준 예시:

- 특정 fine scene 점유율 `>= 0.80`
- `low` confidence band가 대부분
- `confirmed`가 거의 0인데 `probable`만 과도함

## 3. alignment sanity

봐야 하는 값:

- `alignment_counts`
- `aligned_count`
- `upgrade_count`
- `downgrade_count`
- `conflict_count`

해석:

- `upgrade`는 어느 정도 나올 수 있다
- `downgrade`는 많으면 위험하다
- `conflict`는 낮아야 한다

## 4. transition sanity

봐야 하는 값:

- `transition_pair_counts`
- `unexpected_transition_pair_counts`
- `same_scene_streak` 성격의 분포

v1 허용 pair:

- `trend_ignition -> breakout`
- `breakout -> breakout_retest_hold`
- `breakout -> time_decay_risk`
- `pullback_continuation -> runner_healthy`
- `runner_healthy -> trend_exhaustion`
- `trend_exhaustion -> climax_reversal`
- `runner_healthy -> protective_risk`
- `protective_risk -> failed_transition`
- `time_decay_risk -> rebuy_setup`

주의:

starter set 5개만 열려 있으므로,
지금은 허용 pair를 엄격한 validation이라기보다 “이상 조기 감지” 용도로만 쓴다.

---

## 구현 방식

## 1. replay 기반

현재 live row에 scene가 비어 있어도
기존 checkpoint row를 replay하면서 현재 heuristic scene를 다시 붙인다.

흐름:

```text
checkpoint_rows.csv 읽기
-> 시간순 정렬
-> symbol별 previous scene 상태 유지
-> tag_runtime_scene() 재호출
-> replay scene row 생성
-> 분포/정합성/전이 요약
```

## 2. previous scene 유지

transition sanity를 보려면 직전 row의 scene 상태가 필요하므로
symbol별로 아래 3개는 유지한다.

- `previous_fine_label`
- `previous_gate_label`
- `previous_transition_bars`

---

## 심볼별 summary row

심볼별 최소 row는 아래 필드를 갖는 것이 좋다.

- `symbol`
- `row_count`
- `scene_filled_row_count`
- `fine_label_counts`
- `gate_label_counts`
- `alignment_counts`
- `unexpected_transition_count`
- `top_fine_label`
- `recommended_focus`

---

## 추천 해석 규칙

### proceed 기준

- scene coverage가 충분히 있고
- `conflict` 비율이 낮고
- 특정 fine scene 쏠림이 과도하지 않으면
- `SA3`로 넘어갈 수 있다

### hold 기준

아래면 보류:

- `scene_filled_row_count = 0`
- `conflict_rate`가 높음
- 하나의 fine scene이 너무 과도함
- transition pair가 대부분 unexpected

---

## 완료 기준

- replay 기반으로 `checkpoint_scene_sanity_latest.json`이 생성된다
- 최근 row 기준 scene 분포를 한눈에 볼 수 있다
- `alignment`와 `transition` 이상 여부가 summary에 드러난다
- 다음 액션이 `SA3 진행`인지 `heuristic 조정`인지 명확히 나온다

---

## 한 줄 결론

`SA2.5`는 새 scene engine을 더 키우는 단계가 아니라, 지금 붙인 heuristic seed가 정상적인 모양인지 먼저 검산하는 단계다.
