# F2. Aggregate Conviction / Flow Persistence 상세 계획

## 1. 목적

F2의 목적은 `flow_structure_gate_v1`를 통과한 뒤에만 의미를 갖는 공용 수치 층을 고정하는 것이다.

이 단계는 새로운 pass/fail 게이트를 만드는 단계가 아니다.
오히려 이미 F1이 결정한 구조 자격 위에서,

- 지금 이 장면이 얼마나 한 방향으로 정렬되어 있는지
- 그 정렬이 얼마나 누적되고 이어지고 있는지

를 분리해서 surface하는 단계다.

즉 F2는 다음 질문에 답한다.

1. 구조 자격을 받은 장면 안에서 directional conviction이 얼마나 강한가
2. 그 conviction이 순간 스파이크가 아니라 persistence를 가지는가
3. exact match 없이도 later calibration이 가능한 숫자 설명층을 만들 수 있는가

---

## 2. 왜 F2가 필요한가

지금까지의 흐름은 다음과 같았다.

1. `CA2 / should-have-done / canonical / runtime audit`
   여기서는 "무엇을 보고 있는가"와 "비교가 가능한가"를 정리했다.

2. `state_strength / local_structure / dominance`
   여기서는 "continuation / reversal / friction / caution"을 분리했다.

3. `decomposition`
   여기서는 continuation 내부를 `intent / stage / texture / location / tempo / ambiguity`로 더 잘게 쪼갰다.

4. `XAU pilot / canary / refined gate`
   여기서는 exact pilot match가 너무 강하면 구조가 충분히 맞는 장면도 계속 보류시킬 수 있다는 점이 드러났다.

그래서 이제는 질문이 바뀌었다.

과거 질문:

- "pilot이랑 정확히 같은 장면인가?"

지금 질문:

- "구조가 directional flow 후보 자격을 가졌다면, 그 안에서 얼마나 강하게 정렬되고 얼마나 지속되는가?"

F2는 바로 이 질문을 읽는 층이다.

---

## 3. F2의 권한

F2는 권한상 `F1 structure gate` 아래에 있어야 한다.

권한 순서는 다음과 같이 고정한다.

1. `flow_structure_gate_v1`
   directional flow 후보 자격 판단

2. `aggregate_conviction_v1`
   방향 정렬 강도 판단

3. `flow_persistence_v1`
   누적 / 지속 / recency 판단

4. 이후 단계의 `flow_support_state`
   conviction과 persistence를 함께 사용한 상태 분류

중요:

- F2 숫자는 F1을 대체하지 않는다.
- 숫자가 높더라도 F1이 `INELIGIBLE`이면 구조 자격은 여전히 없다.
- F2는 지금 단계에서 read-only다.
- execution/state25를 직접 바꾸지 않는다.

---

## 4. F2의 두 축

### 4-1. `aggregate_conviction_v1`

의미:

- 구조적으로 directional candidate인 장면 안에서
- 현재 얼마나 강하게 한 방향으로 정렬되어 있는가

최소 구성축:

1. `dominance_support`
2. `structure_support`
3. `decomposition_alignment`

추가 penalty:

- `ambiguity_penalty`
- `veto_penalty`

핵심 원칙:

- conviction은 단일 패턴 점수가 아니다
- dominance / local structure / decomposition을 종합한 합성값이어야 한다
- threshold는 여기서 pass/fail이 아니라 bucket 분류에만 사용한다

### 4-2. `flow_persistence_v1`

의미:

- 현재 보이는 directional alignment가 순간적인지
- 아니면 실제로 유지 / 반복 / 축적되고 있는지

구성 재료:

- `tempo profile`
- `breakout hold quality`
- `relevant swing intact state`
- `body drive support`
- `recency / decay weighting`

핵심 원칙:

- persistence는 누적만 보면 안 된다
- 오래된 흐름보다 최근 N-bar persistence에 더 큰 가중치를 둔다
- `EXTENSION`은 persistence가 남아 있을 수 있어도 fresh continuation으로 취급하지 않는다

---

## 5. 세부 계산 철학

## 5-1. `dominance_support`

입력 예:

- `dominance_shadow_gap_v1`
- `dominance_shadow_dominant_side_v1`
- `dominance_shadow_dominant_mode_v1`
- `state_strength_continuation_integrity_v1`
- `state_strength_reversal_evidence_v1`

철학:

- gap이 같은 방향으로 충분히 열려 있고
- dominant side가 slot polarity와 맞으며
- dominant mode가 continuation 계열일수록 가산
- reversal evidence는 penalty로 반영

## 5-2. `structure_support`

입력 예:

- `breakout_hold_quality_v1`
- `few_candle_structure_bias_v1`
- `few_candle_higher_low_state_v1` / `few_candle_lower_high_state_v1`
- `body_drive_state_v1`

철학:

- hold 품질
- few-candle swing intact 여부
- structure bias
- body drive

를 함께 보며, pure threshold가 아니라 structure 상태를 숫자로 환산하는 보조층으로 쓴다.

## 5-3. `decomposition_alignment`

입력 예:

- `intent`
- `stage`
- `texture`
- `location`

철학:

- `CONTINUATION` / `RECOVERY`는 높은 alignment
- `REJECTION`은 friction rejection인지 reversal rejection인지에 따라 다르게 반영
- `ACCEPTANCE`가 가장 높은 fresh alignment
- `EXTENSION`은 방향은 맞아도 late alignment로 낮게 반영
- `POST_BREAKOUT`는 가산, `EXTENDED`는 감산

## 5-4. `ambiguity_penalty`

원칙:

- ambiguity는 side를 바꾸지 않는다
- 대신 conviction을 약화시키고 later flow classification에서 caution을 높이는 용도로만 쓴다

예시:

- `LOW -> 0.0`
- `MEDIUM -> small penalty`
- `HIGH -> large penalty`

## 5-5. `veto_penalty`

원칙:

- `REVERSAL_OVERRIDE`는 원칙적으로 F1 hard disqualifier다
- F2에서는 설명과 관찰을 위해 penalty 값도 남길 수 있지만, 권한은 여전히 F1이 가진다
- `FRICTION_ONLY`와 `BOUNDARY_WARNING`는 conviction을 다르게 깎는다

---

## 6. Persistence의 recency / decay 원칙

이 부분은 F2에서 꼭 고정해야 한다.

동일한 persistence라도:

- 최근 3봉에서 이어지는 hold / swing / drive
- 10봉 전에 한 번 좋았던 persistence

는 같은 의미가 아니다.

그래서 F2에서는 다음 원칙을 둔다.

1. 최근 N-bar persistence에 더 큰 가중치를 둔다
2. `INITIATION + EARLY`는 persistence가 아직 약할 수 있으므로 capped building 성격을 띤다
3. `ACCEPTANCE + PERSISTING`은 가장 높은 recency weight를 가진다
4. `EXTENSION`은 persistence가 남아 있어도 decay를 반영해 fresh score로 과대평가하지 않는다

즉 persistence는 단순 누적이 아니라 "최근에 계속 이어지는가"를 반영하는 값이어야 한다.

---

## 7. Row-level surface

F2에서 남길 공용 필드는 다음과 같이 제안한다.

- `aggregate_directional_flow_metrics_profile_v1`
- `aggregate_flow_structure_gate_v1`
- `aggregate_flow_structure_primary_reason_v1`
- `aggregate_conviction_v1`
- `aggregate_conviction_bucket_v1`
- `aggregate_dominance_support_v1`
- `aggregate_structure_support_v1`
- `aggregate_decomposition_alignment_v1`
- `aggregate_ambiguity_penalty_v1`
- `aggregate_veto_penalty_v1`
- `flow_persistence_v1`
- `flow_persistence_state_v1`
- `flow_persistence_recency_weight_v1`
- `aggregate_flow_reason_summary_v1`

중요:

- 아직 `FLOW_CONFIRMED / BUILDING / UNCONFIRMED / OPPOSED` 최종 분류는 F2의 책임이 아니다
- F2는 conviction과 persistence를 분리 surface하는 데 집중한다

---

## 8. Summary artifact

F2 summary는 최소 아래를 남긴다.

- `avg_aggregate_conviction_v1`
- `avg_flow_persistence_v1`
- `aggregate_conviction_bucket_count_summary`
- `flow_persistence_state_count_summary`
- `aggregate_flow_structure_gate_count_summary`

이 summary는 이후 F3/F4 calibration에서

- 어떤 심볼이 conviction은 높은데 persistence가 약한가
- 어떤 심볼이 structure gate에서는 탈락하는가
- 어떤 분포에서 provisional threshold band를 잡아야 하는가

를 보는 기준이 된다.

---

## 9. 완료 기준

- F2 contract와 summary가 runtime detail에 export된다
- NAS/XAU/BTC 3심볼 모두에서 row-level conviction/persistence가 계산된다
- F1 결과와 충돌하지 않고, F1 위에서 read-only로 설명 가능하다
- conviction의 최소 구성축과 persistence decay 원칙이 코드와 문서에서 일치한다

상태 기준:

- `READY`
  - row surface, summary, artifact 모두 생성 가능
- `HOLD`
  - 일부 upstream field가 없어 component 계산이 빈약함
- `BLOCKED`
  - F2 숫자가 F1 권한 구조를 침범하거나 runtime export가 깨짐
