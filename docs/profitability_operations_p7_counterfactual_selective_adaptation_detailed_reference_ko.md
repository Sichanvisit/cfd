# Profitability / Operations P7 Controlled Counterfactual / Selective Adaptation Detailed Reference

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `P7 controlled counterfactual / selective adaptation`이 무엇인지, 왜 필요한지, 어떤 입력을 바탕으로 어떤 산출물을 만들어야 하는지 고정하기 위한 상세 기준 문서다.

P7이 답하려는 질문은 하나다.

`지금 보이는 운영 문제에 대해, 무엇을 다르게 했으면 나아졌을 가능성이 있고, 그중 무엇을 안전하게 다음 실험 후보로 올릴 수 있는가?`

## 2. 왜 P7이 필요한가

P1~P6까지 오면 이미 아래는 보인다.

- 어떤 lifecycle이 반복되는가
- 어떤 bucket의 expectancy가 나쁜가
- 어떤 anomaly가 상단에 쌓이는가
- 최근 창과 직전 창의 비교에서 무엇이 악화되는가
- 어떤 scene이 worst / strength candidate인가
- 어떤 symbol / setup proxy가 건강하지 않은가

하지만 아직 아래는 안 보인다.

- `한 봉 늦게 들어갔으면` 더 나았는가
- `다른 exit profile`을 썼으면 손실이 줄었는가
- `size를 줄였으면` 손실 곡선이 덜 나빴는가
- 이 해석을 바로 live에 넣는 대신 `어떤 guarded proposal`로 바꿔야 하는가

P7은 바로 이 공백을 메우는 단계다.

## 3. P7이 아닌 것

P7은 자동 self-tuning 엔진이 아니다.

- live rule weight를 즉시 바꾸지 않는다.
- threshold를 무제한 자동 변경하지 않는다.
- 검증 없이 size overlay를 자동 적용하지 않는다.
- coverage 밖 데이터를 근거로 강한 제안을 만들지 않는다.

즉 P7은 `counterfactual + guarded proposal` 단계이지, `무제한 live auto-adaptation` 단계가 아니다.

## 4. P7 입력 소스

### 4-1. P4 compare latest

- [profitability_operations_p4_compare_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p4_compare_latest.json)

주요 사용 section:

- `overall_delta_summary`
- `p3_alert_type_deltas`
- `symbol_alert_deltas`
- `worsening_signal_summary`
- `improving_signal_summary`

### 4-2. P5 casebook latest

- [profitability_operations_p5_casebook_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p5_casebook_latest.json)

주요 사용 section:

- `worst_scene_candidates`
- `strength_scene_candidates`
- `tuning_candidate_queue`
- `casebook_review_queue`

### 4-3. P6 health latest

- [profitability_operations_p6_health_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p6_health_latest.json)

주요 사용 section:

- `overall_health_summary`
- `symbol_health_summary`
- `archetype_health_summary`
- `drift_signal_summary`
- `sizing_overlay_recommendations`

### 4-4. 보조 원천

필요하면 아래를 보조 evidence로 쓸 수 있다.

- [profitability_operations_p2_expectancy_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p2_expectancy_latest.json)
- [profitability_operations_p3_anomaly_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p3_anomaly_latest.json)

단, P7 1차 canonical surface는 P4~P6 중심으로도 성립해야 한다.

## 5. P7 첫 버전의 핵심 산출물

### 5-1. counterfactual review queue

scene / symbol / setup proxy 기준으로 아래 질문을 review queue 형태로 올린다.

- entry delay가 더 나았을 가능성이 있는가
- exit profile swap을 검토할 가치가 있는가
- sizing reduction / hold_small이 더 적절했는가
- legacy identity restore가 먼저여서 다른 counterfactual이 아직 이른가

### 5-2. selective adaptation proposal queue

proposal은 live auto-apply가 아니라 guarded proposal row다.

예시 proposal type:

- `entry_delay_review`
- `exit_profile_review`
- `size_overlay_guarded_apply`
- `legacy_identity_restore_first`
- `counterfactual_hold_for_more_evidence`

### 5-3. safety gate summary

각 proposal에 대해 아래를 명시해야 한다.

- evidence count
- coverage state
- severity / health pressure
- max change suggestion
- dry-run only 여부
- rollback 필요 여부

### 5-4. operator review memo

operator가 아래를 바로 판단할 수 있어야 한다.

- 지금 당장 실험할 후보
- 더 많은 evidence가 필요해 보류할 후보
- P6 advisory를 유지한 채 아직 건드리면 안 되는 후보

## 6. proposal 설계 원칙

P7 proposal은 아래 원칙을 지켜야 한다.

1. `scene별`로 나온다.
2. `왜 이 proposal이 나왔는지` 근거가 같이 붙는다.
3. `coverage_in_scope`와 `coverage_out_of_scope`를 섞지 않는다.
4. `legacy identity 공백`이 큰 scene은 먼저 identity restore 우선으로 분류한다.
5. `critical / stressed` 상태면 공격적 expand proposal을 금지한다.

## 7. safety / guard 원칙

P7은 아래 safety를 기본 전제로 한다.

### 7-1. min evidence

근거 trade / scene 수가 너무 적으면 `proposal`이 아니라 `review_only`로 남긴다.

### 7-2. max change cap

size / timing / exit 제안은 한 번에 큰 폭 변경이 아니라 `작은 guarded step`만 허용한다.

### 7-3. coverage-aware gating

coverage 밖 evidence가 많으면 강한 proposal을 내리지 않는다.

### 7-4. identity-first gating

`legacy_bucket_identity_restore`가 top candidate면 다른 proposal보다 우선 순위를 준다.

### 7-5. no direct live auto-apply

첫 버전은 모두 review / dry-run / guarded-application 전제로 둔다.

## 8. canonical 출력 shape

### latest json

필수 section:

- `overall_counterfactual_summary`
- `counterfactual_review_queue`
- `selective_adaptation_proposal_queue`
- `safety_gate_summary`
- `guarded_application_queue`
- `quick_read_summary`

### latest csv

proposal / review queue flat export.

### latest md

operator가 바로 읽을 수 있는 controlled adaptation memo.

## 9. 완료 기준

P7 첫 버전이 완료되었다고 보려면 아래가 가능해야 한다.

1. worst scene를 `무슨 수정 후보로 읽어야 하는지` proposal type으로 바꿔낼 수 있다.
2. health / drift pressure를 반영해 공격적 제안을 제한할 수 있다.
3. coverage와 evidence가 약한 scene를 `review_only`로 남길 수 있다.
4. operator가 latest markdown만 보고 `실험 후보 / 보류 후보 / 금지 후보`를 나눌 수 있다.

## 10. 결론

P7은 `이상 징후를 더 보는 단계`가 아니라, `관찰된 문제를 안전한 다음 실험 후보로 번역하는 첫 controlled adaptation 단계`다.

중요한 점은 P7이 `자동 최적화`가 아니라 `근거 있는 제안 + 보호장치 있는 적용 후보`라는 것이다.
