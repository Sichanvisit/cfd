# F11. candidate evaluation / rollback dashboard

## 1. 목적

F11의 목적은 F10 bounded apply 결과를 candidate 단위로 집계해서,

**이 candidate가 실제로 도움이 됐는지, 더 봐야 하는지, 종료해야 하는지, 되돌려야 하는지**

를 운영 규칙으로 판정하는 것이다.

즉 F11은 단순 시각화 대시보드가 아니라,

**candidate lifecycle을 결정하는 evaluation / governance layer**

다.

---

## 2. 왜 필요한가

F10까지 있으면 시험은 가능하다.
하지만 시험만 하고 판단 규칙이 없으면 운영은 다시 사람 감으로 돌아간다.

예를 들어:

- over-veto는 줄었다
- under-veto는 약간 늘었다
- widening은 조금 증가했다
- sample은 아직 적다

이런 상황에서 기준이 없으면
사람이 임의로

- 승격할지
- 더 볼지
- 종료할지
- 되돌릴지

판단하게 된다.

F11은 이걸 막기 위해 필요하다.

---

## 3. 상위 원칙

### 3-1. F11은 운영 판정기이지 새 해석기가 아니다

F11은 새로운 directional interpretation을 만들지 않는다.
F11은 F10의 before / after 실험 결과를 집계해
candidate의 생애주기를 판정하는 층이다.

### 3-2. 핵심은 before / after 비교다

F11은 반드시

- candidate 적용 전
- candidate 적용 후

를 같은 기준에서 비교해야 한다.

단순히 after 상태만 보고 좋다/나쁘다를 판단하면 안 된다.

### 3-3. rollback만이 아니라 promote / neutral 종료까지 포함한다

candidate의 outcome은 아래 네 가지로 본다.

- `PROMOTE`
- `KEEP_OBSERVING`
- `EXPIRE_WITHOUT_PROMOTION`
- `ROLLBACK`

이 네 가지가 있어야

- 좋은 후보는 졸업시키고
- 애매한 후보는 더 관찰하고
- 효과 없는 후보는 조용히 종료하고
- 나쁜 후보는 빠르게 격리

할 수 있다.

---

## 4. 핵심 평가 지표

### 4-1. 필수 핵심 지표

#### `over_veto_rate`

좋은 continuation / recovery를 과하게 막은 비율

→ 줄어야 한다

#### `under_veto_rate`

막아야 할 장면을 너무 통과시킨 비율

→ 늘어나면 위험

#### `unverified_widening_rate`

truth로 충분히 검증되지 않은 widening이 증가한 비율

→ 급증하면 위험

#### `cross_symbol_drift`

공용 또는 shared parameter 변경이 다른 symbol 분포를 흔든 정도

→ shared key일수록 중요

### 4-2. 보조 지표

- `same_symbol_cross_window_stability`
- `candidate_hit_count`
- `promoted_like_transition_count`
- `harmful_transition_count`
- `sample_coverage`

즉 F11은

**한 row가 좋아졌는가** 가 아니라,
**candidate가 실제 운영 기준으로 유의미하게 개선했는가**

를 본다.

---

## 5. candidate evaluation summary 구조

F11은 candidate 단위로 아래 요약을 남기는 편이 좋다.

- `candidate_id`
- `apply_session_id`
- `evaluation_window_start`
- `evaluation_window_end`
- `affected_row_count`
- `over_veto_rate_before`
- `over_veto_rate_after`
- `under_veto_rate_before`
- `under_veto_rate_after`
- `unverified_widening_before`
- `unverified_widening_after`
- `same_symbol_cross_window_stability`
- `cross_symbol_drift_score`
- `sample_coverage`
- `evaluation_outcome`

derived delta:

- `over_veto_delta_pct`
- `under_veto_delta_pct`
- `unverified_widening_delta_pct`
- `cross_symbol_drift_delta_pct`

---

## 6. outcome 판정 규칙

### 6-1. `PROMOTE`

아래를 모두 또는 대부분 만족할 때:

- minimum shadow observation window 충족
- same-symbol cross-window에서 일관된 개선
- `over_veto_rate` 감소
- `under_veto_rate` 유의미한 악화 없음
- `unverified_widening_rate` 급증 없음
- shared/common parameter라면 cross-symbol drift 허용 범위 내

즉

**bounded apply -> cross-window validation -> harmful widening 없음 -> 안정적 개선**

을 통과했을 때만 승격한다.

### 6-2. `KEEP_OBSERVING`

- 개선 신호는 있으나
- sample 수 부족
- window coverage 부족
- drift 판단이 아직 애매함

즉 "좋을 가능성은 있지만 아직 승격은 이르다"는 상태다.

### 6-3. `EXPIRE_WITHOUT_PROMOTION`

- 유의미한 개선도 악화도 없음
- neutral outcome
- effect는 있었지만 승격 가치가 낮음

이 outcome은 zombie candidate를 막기 위해 필요하다.

### 6-4. `ROLLBACK`

다음 경우 즉시 또는 우선 rollback 후보로 본다.

- `under_veto_rate` 유의미한 악화
- `unverified_widening_rate` 급증
- `cross_symbol_drift` 증가
- `confirmed accuracy` 악화
- conflict apply 또는 unexpected widening 발견

즉 rollback은 막연한 불만이 아니라,
명시된 부작용 지표 기반으로 작동해야 한다.

---

## 7. dashboard 층 구조

### 7-1. summary dashboard

운영 전체를 한눈에 보는 표면이다.

권장 항목:

- `active_apply_session_count`
- `candidate_outcome_count_summary`
- `promote_count`
- `keep_observing_count`
- `expire_count`
- `rollback_count`
- `symbol_apply_count_summary`
- `learning_key_apply_count_summary`
- `shared_parameter_apply_count`
- `cross_symbol_warning_count`

### 7-2. detailed candidate dashboard

candidate별 상세 표면이다.

권장 항목:

- candidate id
- symbol / key
- current vs proposed
- apply scope
- active duration
- affected rows
- before / after metrics
- current outcome
- rollback trigger hit 여부
- next review due time

---

## 8. F9 / F10 / F11 역할 분리

### F9

- 설명을 후보로 변환
- candidate 생성 및 필터링
- 아직 적용 안 함

### F10

- candidate를 좁은 범위에서 시험
- before / after diff 생성
- live 판단은 기본적으로 안 바꿈

### F11

- 시험 결과를 집계
- 부작용과 개선을 수치로 평가
- `PROMOTE / KEEP_OBSERVING / EXPIRE_WITHOUT_PROMOTION / ROLLBACK` 판정

이 분리가 필요한 이유는
후보 생성, 후보 적용, 후보 판정이 섞이면
운영이 다시 불안정해지기 때문이다.

---

## 9. 완료 기준

- candidate마다 before / after가 숫자로 비교된다
- outcome이 명시 규칙으로 결정된다
- rollback trigger가 문서화되어 있다
- promote / expire / rollback 이력이 catalog에 남는다
- 사람 감이 아니라 운영 규칙으로 candidate를 관리할 수 있다

---

## 10. 다음 단계 연결

F11이 끝나면 그 다음은 실제 운영 정책이다.

즉 충분히 검증된 candidate만

- calibration patch 승격
- bounded live 고려

로 이어지게 되고,
그 전까지는 계속

- shadow
- observe
- expire
- rollback

의 운영 루프 안에 머문다.
