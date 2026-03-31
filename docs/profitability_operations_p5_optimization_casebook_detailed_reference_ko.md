# Profitability / Operations P5 Optimization Loop / Casebook Detailed Reference

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `P5 optimization loop / casebook strengthening`이 무엇인지, 왜 필요한지, 어떤 입력을 다음 개선 input으로 돌려야 하는지 고정하기 위한 상세 기준 문서다.

P5의 핵심 질문은 하나다.

`지금까지 P2/P3/P4에서 읽은 concern 중 무엇을 실제 casebook과 tuning queue로 승격할 것인가?`

## 2. 왜 P5가 필요한가

P2는 expectancy를 읽는다.
P3는 active alert를 읽는다.
P4는 최근 worsening / improving을 읽는다.

하지만 여기서 아직 한 단계가 남아 있다.

- 무엇을 다음 개선 입력으로 올릴지
- 어떤 scene을 caution casebook에 넣을지
- 어떤 scene을 strength casebook에 넣을지
- 어떤 tuning candidate를 다음 작업 순서로 둘지

P5는 바로 그 연결 단계다.

## 3. P5가 아닌 것

P5는 아직 자동 튜닝 단계가 아니다.

- 파라미터를 자동 변경하지 않는다
- blacklist를 자동 적용하지 않는다
- 모델을 자동 승격하지 않는다

즉 P5는 `운영 해석을 개선 queue로 변환하는 단계`다.

## 4. P5 입력 소스

### 4-1. P2 expectancy latest

- [profitability_operations_p2_expectancy_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p2_expectancy_latest.json)

주로 사용하는 입력:

- `symbol_setup_regime_expectancy_summary`

### 4-2. P3 anomaly latest

- [profitability_operations_p3_anomaly_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p3_anomaly_latest.json)

주로 사용하는 입력:

- `active_alerts`
- `symbol_alert_summary`

### 4-3. P4 compare latest

- [profitability_operations_p4_compare_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p4_compare_latest.json)

주로 사용하는 입력:

- `symbol_alert_deltas`
- `p3_alert_type_deltas`
- `quick_read_summary`

## 5. P5 scene key 원칙

P5 첫 버전의 canonical scene key는 아래다.

`symbol / setup_key / regime_key`

이 scene key 위에 아래 세 축을 합친다.

- expectancy
- active alert
- recent delta

## 6. P5 canonical 출력 shape

### 6-1. latest json

필수 section:

- `overall_casebook_summary`
- `worst_scene_candidates`
- `strength_scene_candidates`
- `caution_setup_summary`
- `tuning_candidate_queue`
- `casebook_review_queue`
- `quick_read_summary`

### 6-2. latest csv

worst / strength / tuning candidate를 flat row로 export.

### 6-3. latest md

operator가 바로 읽는 casebook quick memo.

## 7. 첫 버전에서 구분해야 하는 것

1. `실제 음수 expectancy` scene
2. `경제성 정보 공백` scene
3. `recent worsening`이 붙은 scene
4. `strength / preserve` 후보 scene

즉 P5는 단순 worst list가 아니라,
`무엇을 줄이고 무엇을 보존할지`를 같이 보여줘야 한다.

## 8. tuning candidate 원칙

첫 버전은 아래처럼 candidate type을 분류한다.

- `entry_exit_timing_review`
- `consumer_gate_pressure_review`
- `legacy_bucket_identity_restore`
- `pnl_lineage_attribution_audit`
- `scene_casebook_review`

## 9. 완료 기준

P5 첫 버전이 완료됐다고 보려면 아래가 가능해야 한다.

1. worst scene과 strength scene이 분리돼 나온다.
2. tuning candidate queue가 명시적 candidate type으로 나온다.
3. P4 worsening signal이 P5 review 우선순위에 반영된다.
4. operator가 latest markdown만 보고 다음 review 대상을 말할 수 있다.

## 10. 결론

P5는 `observability를 실제 개선 backlog와 casebook으로 변환하는 단계`다.
지금까지 읽은 것을 다음 행동으로 바꾸는 첫 운영 루프라고 보면 된다.
