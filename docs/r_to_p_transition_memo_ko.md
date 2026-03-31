# R-Track to P-Track Transition Memo

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 아래 질문에 한 번에 답하기 위한 전이 메모다.

`우리가 왜 R refinement 트랙을 열었고, 그 과정에서 무엇이 구축되었으며, 왜 그 결과가 자연스럽게 P profitability/operations 트랙으로 이어졌는가?`

핵심은 세 가지다.

- R은 foundation 재설계를 위한 트랙이 아니었다.
- R 과정에서 entry / wait / exit / storage / semantic ML / acceptance의 운영 가능한 바닥이 만들어졌다.
- P는 R을 건너뛴 새 메인라인이 아니라, R이 만든 바닥 위에 수익 해석과 운영 판단 층을 올린 다음 단계다.

## 2. 한 줄 요약

가장 짧게 말하면 흐름은 아래와 같다.

```text
semantic foundation 존재
-> 실전형 refinement 필요
-> R0~R4로 해석/정합성/ML/acceptance를 닫음
-> 그 사이 S, R0-B, C 같은 현장 보강 트랙이 끼어듦
-> 이제 질문이 "구조를 어떻게 만들까"에서 "이 구조로 무엇이 실제 돈이 되나"로 바뀜
-> 그래서 P0~P7 profitability/operations 트랙으로 넘어감
```

## 3. 먼저, 왜 R을 계획했나

R을 연 이유는 foundation이 없어서가 아니었다.
이미 semantic foundation과 chart/consumer/semantic ML scaffold는 존재했다.

당시 핵심 문제는 아래에 가까웠다.

- 구조는 있는데 row와 trace를 읽었을 때 이유가 바로 안 보였다.
- symbol별 execution temperament가 아직 거칠었다.
- storage / export / replay / dataset join이 완전히 잠기지 않았다.
- semantic ML은 scaffold는 있었지만 target / split / preview / shadow 품질을 더 다듬어야 했다.
- 마지막으로 "이제 무엇을 허용하고 무엇을 아직 보류할지" acceptance가 필요했다.

즉 R의 목적은 `새 foundation을 만드는 것`이 아니라
`기존 foundation을 실전 운영 가능한 수준으로 refinement하고 acceptance까지 닫는 것`이었다.

기준 문서:

- [refinement_track_execution_plan_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\refinement_track_execution_plan_ko.md)

## 4. R에서 무엇을 freeze하고 무엇을 다듬었나

R 동안 재설계하지 않기로 한 것은 아래였다.

- Position
- Response
- State
- Evidence
- Belief
- Barrier

즉 R은 semantic owner 자체를 갈아엎는 트랙이 아니었다.
대신 아래 owner를 중심으로 refinement가 진행됐다.

- ObserveConfirm
- EntryService
- WaitEngine
- ExitProfileRouter
- ExitManagePositions
- storage / export / replay
- semantic target / split / evaluate

이 점이 중요하다.
나중에 P로 넘어갈 수 있었던 이유도,
semantic foundation의 의미를 계속 흔들지 않고 운영 가능한 표면을 먼저 만들었기 때문이다.

## 5. R0~R4에서 실제로 쌓인 것

### 5-1. R0: 정합성 최소셋

R0의 질문은 이것이었다.

- 왜 observe인가
- 왜 blocked인가
- 왜 probe가 승격되지 않았는가
- 왜 semantic runtime이 inactive인가

즉 R0는 `row 해석 기준선`을 세우는 단계였다.
이 단계에서 `observe_reason / blocked_by / action_none_reason` owner 분리,
non-action taxonomy, key linkage contract, semantic canary recent-window 안정화가 핵심이 됐다.

대표 문서:

- [refinement_r0_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_detailed_reference_ko.md)
- [refinement_r0_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_execution_roadmap_ko.md)

### 5-2. R1: Stage E micro calibration

R1의 질문은 `구조는 맞는데, 실제 execution temperament가 매끄러운가`였다.

핵심은 아래였다.

- XAU upper sell probe 흐름 조정
- BTC lower hold / duplicate suppression / hold patience 조정
- NAS clean confirm balance 조정

즉 R1은 semantic 의미를 바꾸기보다,
probe -> confirm -> hold -> exit 흐름이 심볼별로 너무 어색하지 않도록 미세조정한 단계였다.

대표 문서:

- [refinement_r1_stagee_micro_calibration_spec_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\refinement_r1_stagee_micro_calibration_spec_ko.md)
- [refinement_r1_stagee_micro_calibration_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\refinement_r1_stagee_micro_calibration_implementation_checklist_ko.md)

### 5-3. R2: 저장 / export / replay 정합성

R2의 질문은 `같은 사건이 hot row, detail row, replay, dataset에서 같은 key와 같은 해석으로 이어지는가`였다.

핵심은 아래였다.

- decision_row_key 정합성
- runtime_snapshot_key / trade_link_key / replay_row_key join 안정화
- hot/detail propagation audit
- semantic dataset builder compatibility

즉 R2는 "운영 로그"와 "오프라인 재현" 사이의 바닥을 고정한 단계였다.

대표 문서:

- [refinement_r2_storage_export_replay_integrity_spec_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_storage_export_replay_integrity_spec_ko.md)
- [refinement_r2_join_coverage_casebook_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_join_coverage_casebook_ko.md)

### 5-4. R3: Semantic ML refinement

R3의 질문은 `semantic ML v1이 구조만 있는 상태를 넘어, 품질을 설명 가능한 상태인가`였다.

핵심은 아래였다.

- timing target refinement
- split health refinement
- entry_quality target refinement
- legacy feature tier refinement
- preview / audit refinement
- shadow compare / runtime provenance cleanup

즉 R3는 ML을 semantic owner로 승격한 것이 아니라,
보조 계층으로서 평가와 shadow compare를 믿고 읽을 수 있게 만든 단계였다.

대표 문서:

- [refinement_r3_semantic_ml_refinement_spec_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_semantic_ml_refinement_spec_ko.md)
- [refinement_r3_post_step7_slice_sparsity_reconfirm_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_post_step7_slice_sparsity_reconfirm_memo_ko.md)

### 5-5. R4: Acceptance / promotion-ready

R4의 질문은 `지금 무엇을 허용하고 무엇을 아직 보류하는가`였다.

여기서 매우 중요한 점은:
R4 완료가 곧바로 partial_live 진입을 뜻하지는 않는다는 점이다.

R4의 실제 결론은 아래에 가까웠다.

- semantic preview / shadow는 healthy
- chart rollout은 hold
- semantic canary는 hold
- 운영 action은 stay_threshold_only
- allowlist 확장은 제한적으로 가능
- partial_live는 아직 hold

대표 문서:

- [refinement_r4_final_acceptance_summary_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_final_acceptance_summary_memo_ko.md)
- [refinement_r4_allowlist_expansion_reconfirm_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_allowlist_expansion_reconfirm_memo_ko.md)

즉 R4는 `모든 것을 더 열자`가 아니라
`지금 허용 범위를 보수적으로 닫자`는 acceptance 단계였다.

## 6. R 과정에서 더 크게 구축된 것

R을 거치면서 단순 세부 튜닝만 쌓인 것이 아니었다.
실제로는 아래 바닥이 만들어졌다.

- entry / wait / exit 의미 계약
- branch truth logging
- recent runtime summary
- continuity test
- handoff / read guide / operator 문서

이게 [current_architecture_completed_work_summary_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_architecture_completed_work_summary_ko.md)의 핵심 메시지다.

즉 R의 실질 결과는
`로직을 조금 고쳤다`가 아니라
`엔진을 운영 가능한 구조로 읽고 설명할 수 있게 만들었다`는 데 있다.

## 7. R과 P 사이에 추가로 끼어든 보강 트랙

사용자 체감상 "R 다음 곧바로 P"가 아니라고 느껴지는 이유는 맞다.
실제로 사이에 몇 개의 중요한 보강 트랙이 있었다.

### 7-1. S0~S6: consumer-coupled check / entry scene refinement

이 트랙은 chart/check/entry를 같은 consumer chain에 묶는 작업이었다.

핵심은 아래였다.

- painter 독자 해석 제거
- consumer_check_state_v1 도입
- 7-stage display 체계 정리
- must-show / must-hide / visually-similar casebook
- BTC / NAS / XAU symbol balance tuning

즉 이 트랙은 `보여주는 표면`과 `실제 entry chain`을 붙이는 중간 보강 축이었다.

대표 문서:

- [consumer_coupled_check_entry_scene_refinement_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\consumer_coupled_check_entry_scene_refinement_roadmap_ko.md)

### 7-2. R0-B: actual entry forensic

scene display가 안정화된 뒤에도
`실제 들어간 직후 반대로 가는 진입` 문제가 남았다.

그래서 이미 닫힌 R0 기준선을 실제 adverse entry 사례에 다시 연결하는
R0-B forensic 트랙이 생겼다.

핵심은 아래였다.

- 최근 adverse entry sample 추출
- decision row matching
- forensic truth table 정규화
- family clustering
- action candidate derivation

즉 R0-B는 새로운 phase가 아니라,
이미 만든 R0 해석 언어를 실제 손실 진입 문제에 다시 적용한 실전 하위 단계였다.

대표 문서:

- [refinement_r0_b_actual_entry_forensic_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_b_actual_entry_forensic_detailed_reference_ko.md)
- [refinement_r0_b6_close_out_handoff_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_b6_close_out_handoff_ko.md)

### 7-3. C0~C6: decision log coverage gap

R0-B를 하면서 `reader 문제`와 `실제 historical source 부재`를 구분해야 할 필요가 생겼다.
그래서 coverage 트랙이 별도로 열렸다.

핵심은 아래였다.

- baseline freeze
- source inventory / retention matrix
- coverage audit
- archive generation hardening
- targeted backfill
- rerun + delta review
- close-out

최종 결론은:
internal scope는 충분히 닫혔고,
현재 남은 큰 gap은 workspace 밖 historical source availability 문제라는 것이었다.

대표 문서:

- [decision_log_coverage_gap_c6_close_out_handoff_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\decision_log_coverage_gap_c6_close_out_handoff_ko.md)

## 8. 그래서 왜 P로 흘러들어왔나

R과 그 사이 보강 트랙들을 지나고 나면,
질문이 더 이상 아래가 아니게 된다.

- 구조를 어떻게 다시 쪼갤까
- trace를 어떻게 더 남길까
- join을 어떻게 맞출까

대신 질문이 아래로 바뀐다.

- 어떤 lifecycle이 실제 손실로 이어지나
- 어떤 setup / regime / symbol이 기대값을 만드나
- 어디에서 alert를 먼저 띄워야 하나
- 최근 변화가 개선인가 악화인가
- 어떤 조정만 guarded apply로 허용할 수 있나

즉 P는 `구조 개선` 트랙이 아니라
`이미 만든 구조를 수익 해석과 운영 판단으로 연결하는` 트랙으로 열리게 된다.

대표 기준 문서:

- [current_profitability_operations_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_profitability_operations_roadmap_ko.md)

## 9. P에서는 무엇이 구축됐나

P는 아래 순서로 올라갔다.

- P0: trace / ownership / coverage-aware foundation
- P1: lifecycle correlation observability
- P2: expectancy / attribution observability
- P3: alerting / anomaly detection
- P4: time-series comparison
- P5: optimization loop / casebook strengthening
- P6: meta-cognition / health / drift / sizing advisory
- P7: controlled counterfactual / selective adaptation

즉 P는 semantic foundation을 새로 만든 트랙이 아니라,
R이 만든 운영 가능한 구조 위에
`관찰 -> 해석 -> 경보 -> 비교 -> 튜닝 큐 -> health advisory -> guarded proposal`
층을 올린 트랙이다.

대표 문서:

- [profitability_operations_p_track_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p_track_detailed_reference_ko.md)
- [profitability_operations_p_track_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p_track_execution_roadmap_ko.md)
- [profitability_operations_p0_to_p7_master_close_out_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p0_to_p7_master_close_out_ko.md)

## 10. 현재 상태를 가장 정확히 읽는 법

현재 상태를 한 줄로 줄이면 아래가 가장 정확하다.

```text
R은 refinement + acceptance를 닫았고,
그 사이 S / R0-B / C 보강 트랙이 들어왔고,
그 위에 P가 수익/운영 관측 레이어를 올렸으며,
지금은 P7 결과를 이용한 guarded size overlay 실험이 active 상태다.
```

즉 지금은 `R이 미완료라서 P로 잘못 넘어온 상태`가 아니다.
오히려 `R을 보수적으로 닫았기 때문에 P가 가능해진 상태`에 가깝다.

## 11. 아직 원래 계획에서 남아 있는 것

다만 옛 refinement 문서 기준으로 완전히 사라지지 않은 backlog도 있다.

대표적인 것은 아래다.

- probe lot / confirm add 완성형 주문 구조
- edge-to-edge hold / exit 완성형 실행 구조
- semantic ML bounded live 확장
- API 운영 안정성 마무리

즉 P가 열렸다고 해서 옛 backlog가 없어진 것은 아니다.
다만 순서가 바뀐 것이다.

현재는:

- 먼저 P7 guarded overlay를 매우 보수적으로 검증하고
- 그 다음에야 옛 backlog를 다시 우선순위에 올리는 편이 자연스럽다

## 12. 이름 충돌 주의

혼동이 자주 생기는 지점이 하나 있다.

옛 [refinement_track_execution_plan_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\refinement_track_execution_plan_ko.md) 안의
`P0 / P1 / P2`는
`R0~R4를 묶어 본 우선순위 버킷`이었다.

지금의 `P0~P7`은 완전히 다른 뜻이다.

- 옛 문서의 `P0 / P1 / P2` = refinement 우선순위 묶음
- 현재 문서의 `P0~P7` = profitability / operations 본선 phase

따라서 현재 대화에서 `P`라고 할 때는 거의 항상 후자,
즉 profitability / operations P-track을 뜻한다고 보면 된다.

## 13. 결론

우리가 걸어온 흐름은 아래 한 줄로 정리된다.

```text
semantic foundation이 이미 있던 시스템을
R로 운영 가능한 구조로 다듬고 acceptance까지 닫은 뒤,
S / R0-B / C 같은 현장 보강 트랙을 거쳐,
그 위에 P로 수익 해석과 운영 판단 레이어를 올린 것이다.
```

이 문서는 이후 새 스레드나 handoff에서
`왜 R 다음에 P가 나왔는지`,
`중간에 왜 S / R0-B / C가 끼었는지`,
`지금 상태를 무엇으로 불러야 하는지`
를 한 번에 설명하는 기준 문서로 사용한다.
