# R3 Step 5 Entry Quality Casebook

## 1. 목적

이 문서는 `R3 Step 5. entry_quality target refinement`의 1차 casebook이다.

이번 Step 5의 목표는 `entry_quality`를 단순 수익 라벨이 아니라
"들어간 진입이 구조적으로 괜찮았는가"를 설명 가능한 형태로 다시 묶는 것이다.

핵심은 두 가지다.

- `timing`과 `entry_quality`를 분리해서 본다.
- `bad entry`와 `ambiguous entry`를 같은 negative로 뭉개지 않는다.

## 2. 이번 1차 변경 요약

기존 `entry_quality` fold는 아래 두 축만 썼다.

- `support_delta = transition_same_side_positive_count - transition_adverse_positive_count`
- `quality = transition_quality_score`

기존 규칙은:

- `support_delta >= 1` and `quality >= threshold` -> positive
- `support_delta < 0` and `quality <= 0` -> negative
- `support_delta <= 0` and `quality <= negative_threshold` -> negative
- 그 외 -> `None`

이번 1차에서는 위 baseline을 유지하되, 아래 두 경우를 `ambiguous veto`로 분리했다.

- `hold-best conflict`
- `fallback-heavy`

즉, count/quality만 보면 positive 또는 negative여도
`hold가 더 낫다는 근거` 또는 `fallback-heavy 흔적`이 강하면
그 row를 억지로 정답으로 밀지 않고 `None`으로 남긴다.

## 3. case 분류

### A. clear positive

예시:

- `same_side=2`
- `adverse=0`
- `quality=0.0035`

해석:

- same-side progress가 분명하고
- quality도 positive threshold를 넘는다
- hold conflict나 fallback heavy도 없다

판정:

- reason = `support_positive`
- target = `1`

### B. clear negative

예시:

- `same_side=0`
- `adverse=1`
- `quality=-0.0001`

해석:

- adverse support가 더 크고
- quality도 0 이하라서 entry quality를 negative로 볼 근거가 충분하다

판정:

- reason = `support_negative`
- target = `0`

### C. quality negative only

예시:

- `same_side=0`
- `adverse=0`
- `quality=-0.0012`

해석:

- support delta는 비어 있지만
- quality가 negative threshold 아래로 충분히 내려간다

판정:

- reason = `quality_negative_only`
- target = `0`

메모:

- 현재 legacy baseline entry_quality dataset의 negative 다수는 이 케이스다.
- 실데이터 기준 `support_delta == 0`이면서 negative quality인 row가 많다.

### D. quality positive without support

예시:

- `same_side=0`
- `adverse=0`
- `quality=0.002268`

해석:

- quality만 보면 좋아 보이지만
- same-side support가 없어서 "좋은 진입"으로 단정하기 어렵다

판정:

- reason = `ambiguous`
- target = `None`

### E. support positive but quality short

예시:

- `preflight_regime=TREND`
- `same_side=2`
- `adverse=0`
- `quality=0.0075`

해석:

- support는 positive지만
- TREND에서는 stricter positive threshold를 넘지 못했다

판정:

- reason = `support_positive_quality_short`
- target = `None`

### F. positive hold-conflict veto

예시:

- `same_side=2`
- `adverse=0`
- `quality=0.0042`
- `management_hold_favor_positive_count=2`
- `management_exit_favor_positive_count=0`

해석:

- baseline만 보면 positive다
- 하지만 management 쪽에선 hold-best signal이 더 강하다
- 즉 "진입 자체가 나빴다"기보다 "이 row를 positive로 고정하기엔 애매하다"

판정:

- reason = `support_positive_hold_conflict_veto`
- target = `None`

### G. positive fallback-heavy veto

예시:

- `same_side=2`
- `adverse=0`
- `quality=0.0042`
- `compatibility_mode=hybrid`

해석:

- baseline만 보면 positive지만
- fallback-heavy row는 target을 공격적으로 확정하지 않는다

판정:

- reason = `support_positive_fallback_veto`
- target = `None`

### H. negative hold-conflict veto

예시:

- `same_side=0`
- `adverse=0`
- `quality=-0.0012`
- `management_hold_favor_positive_count=2`
- `management_exit_favor_positive_count=0`

해석:

- quality-only negative row라도
- management 쪽에 hold-best conflict가 있으면
- `bad entry`보다 `ambiguous`로 남기는 편이 더 안전하다

판정:

- reason = `quality_negative_hold_conflict_veto`
- target = `None`

## 4. current legacy baseline에서의 실제 영향

이번 1차 규칙은 mixed/modern row를 대비한 ambiguity safety를 넣은 것이다.

하지만 current preview baseline은 아래 특성이 있었다.

- `source_generation = legacy`
- `compatibility_mode` 거의 비어 있음
- `management_hold_favor_positive_count` / `management_exit_favor_positive_count`가 실질적으로 모두 0
- `used_fallback_count`, `missing_feature_count`는 current selected feature set에서 의미 있게 살아 있지 않음

그래서 실제 Step 5 preview rebuild 기준으로는:

- `entry_quality` dataset rows: `11457 -> 11457`
- `target_entry_quality` 분포: 변화 없음
- `entry_quality` preview metrics: 변화 없음

즉 이번 1차는 `current legacy baseline을 흔들지 않으면서`
`mixed/modern row에서 future ambiguity handling을 설명 가능하게 만든` 변화로 보는 게 맞다.

## 5. 코드 / 테스트 근거

코드:

- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py)
  - `_entry_quality_hold_conflict`
  - `_entry_quality_fallback_heavy`
  - `_resolve_entry_quality_target_reason`
  - `_resolve_entry_quality_target`

테스트:

- [test_semantic_v1_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_builder.py)
  - clear positive
  - clear negative
  - ambiguous quality-only
  - trend threshold short
  - fallback-heavy veto
  - hold-conflict veto
  - `pd.NA` guard

## 6. 현재 판단

현재 상태는 이렇게 보는 게 맞다.

- Step 5 1차 target refinement: 완료
- Step 5 casebook: 완료
- current legacy preview에 대한 safe/no-regression 확인: 완료

즉 이제 Step 5는 current baseline 기준으로 닫고,
다음 active step인 `Step 6 legacy feature tier refinement`로 넘어갈 수 있다.
